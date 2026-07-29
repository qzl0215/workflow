#!/usr/bin/env python3
"""Safely merge parallel work, verify it, and manage its locked worktrees."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


EXIT_PRECONDITION = 2
EXIT_CONFLICT = 3
EXIT_VERIFY = 4
EXIT_BUSY = 5
RETRY = 6
STATE_NAME = "workflow-integration-state.json"
LOCK_NAME = "workflow-merge.lock"


def command(
    *parts: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        parts,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=env,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    return result


def git_output(*parts: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ("git", *parts),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(parts)} failed")
    return result.stdout.strip()


def git_path(name: str, *, cwd: Path | None = None) -> Path:
    return Path(git_output("rev-parse", "--path-format=absolute", "--git-path", name, cwd=cwd))


def merge_in_progress(*, cwd: Path | None = None) -> bool:
    return git_path("MERGE_HEAD", cwd=cwd).exists()


def other_git_operation_in_progress(worktree: Path) -> bool:
    names = (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "BISECT_LOG",
        "rebase-merge",
        "rebase-apply",
    )
    return any(git_path(name, cwd=worktree).exists() for name in names)


def conflict_files() -> list[str]:
    output = git_output("diff", "--name-only", "--diff-filter=U")
    return [line for line in output.splitlines() if line]


def report_conflict() -> int:
    files = conflict_files()
    print("safe_merge: merge conflict preserved for AI resolution.", file=sys.stderr)
    for path in files:
        print(f"  - {path}", file=sys.stderr)
    print(
        "safe_merge: resolve both intents, git add the files, then rerun with --continue.",
        file=sys.stderr,
    )
    return EXIT_CONFLICT


class IntegrationLease:
    def __init__(self, owner: str) -> None:
        common_dir = Path(git_output("rev-parse", "--git-common-dir")).resolve()
        self.path = common_dir / LOCK_NAME
        self.owner = owner
        self.acquired = False

    def acquire(self) -> None:
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            existing = self.path.read_text(encoding="utf-8", errors="replace").strip()
            raise RuntimeError(f"merge queue busy: {existing or self.path}") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(self.owner)
        self.acquired = True

    def release(self) -> None:
        if not self.acquired:
            return
        existing = self.path.read_text(encoding="utf-8", errors="replace").strip()
        if existing == self.owner:
            self.path.unlink(missing_ok=True)
        self.acquired = False


def verify(command_text: str) -> int:
    print(f"safe_merge: running verification: {command_text}")
    result = subprocess.run(command_text, shell=True, check=False)
    if result.returncode:
        print(f"safe_merge: verification failed ({result.returncode}).", file=sys.stderr)
        return EXIT_VERIFY
    print("safe_merge: verification passed.")
    return 0


def state_path() -> Path:
    return git_path(STATE_NAME)


def save_state(state: dict[str, Any]) -> None:
    state_path().write_text(json.dumps(state, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        raise RuntimeError("--continue requires a preserved merge integration")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("invalid merge integration state")
    return payload


def clear_state() -> None:
    state_path().unlink(missing_ok=True)


def integration_owner() -> str:
    return f"worktree={git_output('rev-parse', '--show-toplevel')} state={state_path()}"


def restore_candidate(state: dict[str, Any], *, delete_integration: bool) -> None:
    original_branch = str(state["original_branch"])
    integration_branch = str(state["integration_branch"])
    switched = command("git", "switch", original_branch)
    if switched.returncode:
        raise RuntimeError(f"could not restore candidate branch {original_branch}")
    if delete_integration:
        deleted = command("git", "branch", "-D", integration_branch)
        if deleted.returncode:
            raise RuntimeError(f"could not remove temporary integration branch {integration_branch}")
    clear_state()


def fetch_target(remote: str, target: str) -> int:
    return command("git", "fetch", remote, target).returncode


def start_merge_attempt(args: argparse.Namespace, candidate_branch: str, candidate_sha: str, attempt: int) -> int:
    remote_ref = f"{args.remote}/{args.target}"
    if fetch_target(args.remote, args.target):
        return EXIT_PRECONDITION
    base_target_sha = git_output("rev-parse", remote_ref)
    if command("git", "merge-base", "--is-ancestor", candidate_sha, remote_ref).returncode == 0:
        print(f"safe_merge: candidate {candidate_branch} is already contained in {remote_ref}.")
        return verify(args.verify)

    integration_branch = f"workflow/integrate/{candidate_sha[:12]}-{os.getpid()}-{attempt}"
    switched = command("git", "switch", "--create", integration_branch, "--no-track", remote_ref)
    if switched.returncode:
        return EXIT_PRECONDITION
    state = {
        "base_target_sha": base_target_sha,
        "candidate_sha": candidate_sha,
        "integration_branch": integration_branch,
        "original_branch": candidate_branch,
        "remote": args.remote,
        "target": args.target,
    }
    save_state(state)
    print(
        f"safe_merge: target-first merge candidate {candidate_branch} into {remote_ref} "
        f"(attempt {attempt})."
    )
    merged = command(
        "git",
        "merge",
        "--no-ff",
        "-m",
        f"Merge {candidate_branch} into {args.target}",
        candidate_sha,
    )
    if merged.returncode:
        return report_conflict() if merge_in_progress() else EXIT_PRECONDITION
    return finalize_integration(args, state, preserve_on_retry=False)


def finalize_integration(
    args: argparse.Namespace,
    state: dict[str, Any],
    *,
    preserve_on_retry: bool,
) -> int:
    verified = verify(args.verify)
    if verified:
        return verified

    integration_branch = str(state["integration_branch"])
    if not args.push:
        restore_candidate(state, delete_integration=False)
        print(f"safe_merge: verified integration retained as {integration_branch}; push not requested.")
        return 0

    remote = str(state["remote"])
    target = str(state["target"])
    remote_ref = f"{remote}/{target}"
    if fetch_target(remote, target):
        return EXIT_PRECONDITION
    current_target_sha = git_output("rev-parse", remote_ref)
    if current_target_sha != str(state["base_target_sha"]):
        print("safe_merge: target advanced before push; rebuilding from the latest target.")
        restore_candidate(state, delete_integration=not preserve_on_retry)
        return RETRY
    pushed = command("git", "push", remote, f"HEAD:{target}")
    if pushed.returncode:
        print("safe_merge: push was overtaken; rebuilding from the latest target.")
        restore_candidate(state, delete_integration=not preserve_on_retry)
        return RETRY
    restore_candidate(state, delete_integration=True)
    print(f"safe_merge: pushed target-first merge to {remote_ref}.")
    return 0


def continue_merge(args: argparse.Namespace) -> int:
    state = load_state()
    if args.remote != state.get("remote") or args.target != state.get("target"):
        raise RuntimeError("--continue remote/target does not match the preserved integration")
    if git_output("branch", "--show-current") != state.get("integration_branch"):
        raise RuntimeError("--continue must run from the preserved integration branch")
    lease = IntegrationLease(integration_owner())
    lease.acquire()
    try:
        if conflict_files():
            return report_conflict()
        if merge_in_progress():
            environment = {**os.environ, "GIT_EDITOR": "true"}
            continued = command("git", "merge", "--continue", env=environment)
            if continued.returncode:
                return report_conflict() if merge_in_progress() else EXIT_PRECONDITION
        result = finalize_integration(args, state, preserve_on_retry=True)
        if result == RETRY:
            print(
                f"safe_merge: resolved integration retained as {state['integration_branch']}; "
                "rerun from the candidate branch against the latest target.",
                file=sys.stderr,
            )
            return EXIT_BUSY
        return result
    finally:
        lease.release()


def worktree_records() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in git_output("worktree", "list", "--porcelain").splitlines():
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    if current:
        records.append(current)
    return records


def create_worktree(args: argparse.Namespace) -> int:
    if not args.task_id or not args.branch:
        raise RuntimeError("--create-worktree requires --task-id and --branch")
    target_path = Path(args.create_worktree).expanduser().resolve()
    if target_path.exists():
        raise RuntimeError(f"worktree path already exists: {target_path}")
    if fetch_target(args.remote, args.target):
        return EXIT_PRECONDITION
    reason = f"workflow:{args.task_id}"
    created = command(
        "git",
        "worktree",
        "add",
        "--lock",
        "--reason",
        reason,
        "-b",
        args.branch,
        str(target_path),
        f"{args.remote}/{args.target}",
    )
    if created.returncode:
        return EXIT_PRECONDITION
    print(f"safe_merge: created locked worktree {target_path} for {reason}.")
    return 0


def cleanup_worktree(args: argparse.Namespace) -> int:
    if not args.task_id or not args.yes:
        raise RuntimeError("--cleanup-worktree requires --task-id and explicit --yes authorization")
    target_path = Path(args.cleanup_worktree).expanduser().resolve()
    records = worktree_records()
    record = next((item for item in records if Path(item["worktree"]).resolve() == target_path), None)
    if record is None:
        raise RuntimeError(f"worktree is not registered: {target_path}")
    if Path(records[0]["worktree"]).resolve() == target_path:
        raise RuntimeError("primary worktree cannot be removed by lifecycle cleanup")
    expected_reason = f"workflow:{args.task_id}"
    if record.get("locked") != expected_reason:
        raise RuntimeError(
            f"worktree lock does not match {expected_reason}; active ownership cannot be proven"
        )
    if git_output("status", "--porcelain", cwd=target_path):
        raise RuntimeError("worktree has uncommitted changes")
    if other_git_operation_in_progress(target_path):
        raise RuntimeError("worktree has an in-progress Git operation")
    if fetch_target(args.remote, args.target):
        return EXIT_PRECONDITION
    head = git_output("rev-parse", "HEAD", cwd=target_path)
    remote_ref = f"{args.remote}/{args.target}"
    if command("git", "merge-base", "--is-ancestor", head, remote_ref).returncode:
        raise RuntimeError(f"worktree HEAD has not been absorbed by {remote_ref}")

    unlocked = command("git", "worktree", "unlock", str(target_path))
    if unlocked.returncode:
        return EXIT_PRECONDITION
    removed = command("git", "worktree", "remove", str(target_path))
    if removed.returncode:
        command("git", "worktree", "lock", "--reason", expected_reason, str(target_path))
        return EXIT_PRECONDITION
    command("git", "worktree", "prune")
    print(f"safe_merge: removed completed worktree {target_path}; local branch retained.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="main")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--verify", default="")
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--continue", dest="continue_merge", action="store_true")
    parser.add_argument("--push", action="store_true", help="push the verified merge to the target")
    lifecycle = parser.add_mutually_exclusive_group()
    lifecycle.add_argument("--create-worktree")
    lifecycle.add_argument("--cleanup-worktree")
    parser.add_argument("--branch", default="")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--yes", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_retries < 1:
        print("safe_merge: --max-retries must be positive.", file=sys.stderr)
        return EXIT_PRECONDITION
    try:
        if git_output("rev-parse", "--is-inside-work-tree") != "true":
            raise RuntimeError("not inside a git worktree")
        if args.create_worktree:
            return create_worktree(args)
        if args.cleanup_worktree:
            return cleanup_worktree(args)
        if args.push and not args.verify:
            raise RuntimeError("--verify is required with --push")
        if not args.verify:
            raise RuntimeError("integration requires --verify")
        if args.continue_merge:
            return continue_merge(args)
        if state_path().exists() or merge_in_progress():
            raise RuntimeError("merge integration already in progress; resolve it and use --continue")
        if git_output("status", "--porcelain"):
            raise RuntimeError("worktree has uncommitted changes")
        candidate_branch = git_output("branch", "--show-current")
        if not candidate_branch:
            raise RuntimeError("detached HEAD is not supported")
        if candidate_branch == args.target:
            raise RuntimeError(f"run from a feature branch, not target branch {args.target}")
        candidate_sha = git_output("rev-parse", "HEAD")
        lease = IntegrationLease(integration_owner())
        lease.acquire()
        try:
            for attempt in range(1, args.max_retries + 1):
                result = start_merge_attempt(args, candidate_branch, candidate_sha, attempt)
                if result == RETRY:
                    continue
                return result
            print("safe_merge: target kept advancing after the retry limit.", file=sys.stderr)
            return EXIT_BUSY
        finally:
            lease.release()
    except (RuntimeError, json.JSONDecodeError) as exc:
        message = str(exc)
        print(f"safe_merge: {message}", file=sys.stderr)
        return EXIT_BUSY if message.startswith("merge queue busy:") else EXIT_PRECONDITION


if __name__ == "__main__":
    raise SystemExit(main())
