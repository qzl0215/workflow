#!/usr/bin/env python3
"""Safely rebase, verify, and optionally fast-forward a target branch."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


EXIT_PRECONDITION = 2
EXIT_CONFLICT = 3
EXIT_VERIFY = 4
EXIT_BUSY = 5


def command(*parts: str, check: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        parts,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=env,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(parts)}")
    return result


def git_output(*parts: str) -> str:
    result = subprocess.run(
        ("git", *parts),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(parts)} failed")
    return result.stdout.strip()


def rebase_in_progress() -> bool:
    for name in ("rebase-merge", "rebase-apply"):
        path = Path(git_output("rev-parse", "--git-path", name))
        if path.exists():
            return True
    return False


def conflict_files() -> list[str]:
    output = git_output("diff", "--name-only", "--diff-filter=U")
    return [line for line in output.splitlines() if line]


def report_conflict() -> int:
    files = conflict_files()
    print("safe_merge: conflict preserved for AI resolution; rebase was not aborted.", file=sys.stderr)
    for path in files:
        print(f"  - {path}", file=sys.stderr)
    print(
        "safe_merge: resolve both intents, git add the files, then rerun with --continue.",
        file=sys.stderr,
    )
    return EXIT_CONFLICT


class MergeLock:
    def __init__(self) -> None:
        common_dir = Path(git_output("rev-parse", "--git-common-dir")).resolve()
        self.path = common_dir / "workflow-merge.lock"
        self.acquired = False

    def __enter__(self) -> "MergeLock":
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            owner = self.path.read_text(encoding="utf-8", errors="replace").strip()
            raise RuntimeError(f"merge queue busy: {owner or self.path}") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(f"pid={os.getpid()} branch={git_output('branch', '--show-current')}\n")
        self.acquired = True
        return self

    def __exit__(self, *_: object) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)


def verify(command_text: str) -> int:
    if not command_text:
        print("safe_merge: verification skipped; no --verify command supplied.")
        return 0
    print(f"safe_merge: running verification: {command_text}")
    result = subprocess.run(command_text, shell=True, check=False)
    if result.returncode:
        print(f"safe_merge: verification failed ({result.returncode}).", file=sys.stderr)
        return EXIT_VERIFY
    print("safe_merge: verification passed.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="main")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--verify", default="")
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--continue", dest="continue_rebase", action="store_true")
    parser.add_argument("--push", action="store_true", help="push HEAD to the target after verification")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_retries < 1:
        print("safe_merge: --max-retries must be positive.", file=sys.stderr)
        return EXIT_PRECONDITION
    try:
        if git_output("rev-parse", "--is-inside-work-tree") != "true":
            raise RuntimeError("not inside a git worktree")
        in_progress = rebase_in_progress()
        branch = git_output("branch", "--show-current")
        if not branch and not (args.continue_rebase and in_progress):
            raise RuntimeError("detached HEAD is not supported")
        if branch == args.target:
            raise RuntimeError(f"run from a feature branch, not target branch {args.target}")
        if args.continue_rebase:
            if not in_progress:
                raise RuntimeError("--continue requires an in-progress rebase")
            if conflict_files():
                return report_conflict()
            environment = {**os.environ, "GIT_EDITOR": "true", "GIT_SEQUENCE_EDITOR": "true"}
            continued = command("git", "rebase", "--continue", env=environment)
            if continued.returncode:
                return report_conflict() if rebase_in_progress() else EXIT_PRECONDITION
        elif in_progress:
            raise RuntimeError("rebase already in progress; resolve it and use --continue")
        elif git_output("status", "--porcelain"):
            raise RuntimeError("worktree has uncommitted changes")

        remote_ref = f"{args.remote}/{args.target}"
        with MergeLock():
            for attempt in range(1, args.max_retries + 1):
                fetched = command("git", "fetch", args.remote, args.target)
                if fetched.returncode:
                    return EXIT_PRECONDITION
                ancestor = command("git", "merge-base", "--is-ancestor", remote_ref, "HEAD")
                if ancestor.returncode:
                    print(f"safe_merge: rebase onto {remote_ref} (attempt {attempt}).")
                    rebased = command("git", "rebase", remote_ref)
                    if rebased.returncode:
                        return report_conflict() if rebase_in_progress() else EXIT_PRECONDITION

                verified = verify(args.verify)
                if verified:
                    return verified
                if not args.push:
                    print("safe_merge: candidate is rebased and verified; push not requested.")
                    return 0

                fetched = command("git", "fetch", args.remote, args.target)
                if fetched.returncode:
                    return EXIT_PRECONDITION
                ff_ready = command("git", "merge-base", "--is-ancestor", remote_ref, "HEAD")
                if ff_ready.returncode:
                    print("safe_merge: target advanced before push; retrying.")
                    continue
                pushed = command("git", "push", args.remote, f"HEAD:{args.target}")
                if pushed.returncode == 0:
                    print(f"safe_merge: pushed fast-forward update to {remote_ref}.")
                    return 0
                print("safe_merge: push was overtaken; retrying.")
        print("safe_merge: merge queue remained busy after retry limit.", file=sys.stderr)
        return EXIT_BUSY
    except RuntimeError as exc:
        message = str(exc)
        print(f"safe_merge: {message}", file=sys.stderr)
        return EXIT_BUSY if message.startswith("merge queue busy:") else EXIT_PRECONDITION


if __name__ == "__main__":
    raise SystemExit(main())
