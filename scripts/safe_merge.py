#!/usr/bin/env python3
"""Safely merge parallel work, verify it, and manage its locked worktrees."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
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


def verification_identity(command_text: str) -> str:
    return hashlib.sha256(command_text.encode("utf-8")).hexdigest()


def verification_log_path(integration_sha: str) -> Path:
    common_dir = Path(git_output("rev-parse", "--git-common-dir")).resolve()
    log_dir = common_dir / "codex" / "safe-merge-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{integration_sha}.log"


def verify(
    command_text: str,
    integration_sha: str,
) -> tuple[int, float]:
    started = time.monotonic()
    result = subprocess.run(
        command_text,
        shell=True,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    duration = round(time.monotonic() - started, 3)
    if result.returncode:
        log_path = verification_log_path(integration_sha)
        log_path.write_text(result.stdout or "", encoding="utf-8")
        os.chmod(log_path, 0o600)
        print(f"safe_merge: verification failed ({result.returncode}).", file=sys.stderr)
        lines = (result.stdout or "").splitlines()
        for line in lines[-80:]:
            print(line, file=sys.stderr)
        print(f"safe_merge: full failure log: {log_path}", file=sys.stderr)
        return EXIT_VERIFY, duration
    print(f"safe_merge: verification passed ({duration:.3f}s).")
    return 0, duration


def state_path() -> Path:
    return git_path(STATE_NAME)


def save_state(state: dict[str, Any]) -> None:
    state_path().write_text(json.dumps(state, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def write_receipt(state: dict[str, Any], *, status: str, transport_attempts: int) -> Path:
    common_dir = Path(git_output("rev-parse", "--git-common-dir")).resolve()
    receipt_dir = common_dir / "codex" / "workflow-merge-receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    verified_sha = str(state["verified_integration_sha"])
    receipt_path = receipt_dir / f"{verified_sha}.json"
    payload = {
        "schema_version": 1,
        "status": status,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.time() - float(state["integration_started_epoch"]), 3),
        "remote": state["remote"],
        "target": state["target"],
        "tag": state.get("tag") or None,
        "base_target_sha": state["base_target_sha"],
        "candidate_sha": state["candidate_sha"],
        "verified_integration_sha": verified_sha,
        "verification_command_sha256": state["verification_command_sha256"],
        "verification_duration_seconds": state["verification_duration_seconds"],
        "transport_attempts": transport_attempts,
    }
    temporary = receipt_path.with_name(f".{receipt_path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, receipt_path)
    return receipt_path


def bind_integration_sha(state: dict[str, Any]) -> str:
    current_sha = git_output("rev-parse", "HEAD")
    expected_sha = state.get("integration_sha")
    if expected_sha:
        if current_sha != expected_sha:
            raise RuntimeError(
                "integration HEAD changed from the preserved immutable integration "
                f"{str(expected_sha)[:12]}"
            )
        return current_sha

    commit = git_output("rev-list", "--parents", "-n", "1", "HEAD").split()
    expected_parents = [str(state["base_target_sha"]), str(state["candidate_sha"])]
    if commit[1:] != expected_parents:
        raise RuntimeError("integration HEAD does not have the expected target-first parents")
    state["integration_sha"] = current_sha
    save_state(state)
    return current_sha


def verify_integration(args: argparse.Namespace, state: dict[str, Any]) -> int:
    integration_sha = bind_integration_sha(state)
    if git_output("status", "--porcelain"):
        print(
            "safe_merge: integration worktree is not clean before verification.",
            file=sys.stderr,
        )
        return EXIT_PRECONDITION
    identity = verification_identity(args.verify)
    if (
        state.get("verified_integration_sha") == integration_sha
        and state.get("verification_command_sha256") == identity
    ):
        print(f"safe_merge: reusing verification for immutable integration {integration_sha[:12]}.")
        return 0
    verified, duration = verify(args.verify, integration_sha)
    if git_output("rev-parse", "HEAD") != integration_sha or git_output("status", "--porcelain"):
        print(
            "safe_merge: verification changed the integration worktree; push refused.",
            file=sys.stderr,
        )
        return EXIT_VERIFY
    if verified:
        return verified
    state["verified_integration_sha"] = integration_sha
    state["verification_command_sha256"] = identity
    state["verification_duration_seconds"] = duration
    state["verified_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    return 0


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


def fetch_target(remote: str, target: str) -> str | None:
    fetched = command("git", "fetch", "--no-tags", remote, f"refs/heads/{target}")
    if fetched.returncode:
        return None
    return git_output("rev-parse", "--verify", "FETCH_HEAD^{commit}")


def remote_ref_sha(remote: str, ref: str) -> str | None:
    result = subprocess.run(
        ("git", "ls-remote", "--refs", remote, ref),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"could not read remote ref {ref}")
    records = [line.split() for line in result.stdout.splitlines() if line.strip()]
    if not records:
        return None
    if len(records) != 1 or len(records[0]) != 2 or records[0][1] != ref:
        raise RuntimeError(f"remote ref lookup was ambiguous for {ref}")
    return records[0][0]


def validate_repository_parameters(remote: str, target: str) -> None:
    if not remote or remote.startswith("-"):
        raise RuntimeError("remote must be a configured Git remote name")
    if not target or target.startswith("-"):
        raise RuntimeError("target must be a valid branch name")
    git_output("remote", "get-url", remote)
    git_output("check-ref-format", "--branch", target)


def validate_tag(tag: str) -> None:
    if not tag:
        return
    result = subprocess.run(
        ("git", "check-ref-format", f"refs/tags/{tag}"),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("--tag must be a valid Git tag name")


def sync_baseline(args: argparse.Namespace) -> int:
    if state_path().exists():
        raise RuntimeError("preserved integration state must be resolved before baseline sync")
    if git_output("status", "--porcelain"):
        raise RuntimeError("worktree has uncommitted changes")
    worktree = Path(git_output("rev-parse", "--show-toplevel"))
    if other_git_operation_in_progress(worktree):
        raise RuntimeError("worktree has an in-progress Git operation")
    target_sha = fetch_target(args.remote, args.target)
    if target_sha is None:
        return EXIT_PRECONDITION

    remote_ref = f"{args.remote}/{args.target}"
    current_sha = git_output("rev-parse", "HEAD")
    if current_sha == target_sha:
        print(f"safe_merge: baseline already current at {target_sha[:12]}.")
        return 0
    if command("git", "merge-base", "--is-ancestor", current_sha, target_sha).returncode:
        raise RuntimeError(
            f"cannot fast-forward baseline: HEAD {current_sha[:12]} has work not in {remote_ref}"
        )
    advanced = command("git", "merge", "--ff-only", target_sha)
    if advanced.returncode:
        return EXIT_PRECONDITION
    if git_output("rev-parse", "HEAD") != target_sha or git_output("status", "--porcelain"):
        print(
            "safe_merge: baseline postcondition failed; moved state was preserved for inspection.",
            file=sys.stderr,
        )
        return EXIT_PRECONDITION
    print(
        f"safe_merge: baseline fast-forwarded from {current_sha[:12]} "
        f"to {target_sha[:12]} using {remote_ref}."
    )
    return 0


def start_merge_attempt(args: argparse.Namespace, candidate_branch: str, candidate_sha: str, attempt: int) -> int:
    remote_ref = f"{args.remote}/{args.target}"
    if args.tag and remote_ref_sha(args.remote, f"refs/tags/{args.tag}") is not None:
        print(f"safe_merge: tag already exists: {args.tag}", file=sys.stderr)
        return EXIT_PRECONDITION
    base_target_sha = fetch_target(args.remote, args.target)
    if base_target_sha is None:
        return EXIT_PRECONDITION
    if command("git", "merge-base", "--is-ancestor", candidate_sha, base_target_sha).returncode == 0:
        print(
            "safe_merge: status=already_integrated "
            f"candidate_sha={candidate_sha} target_sha={base_target_sha} remote_ref={remote_ref}."
        )
        return 0
    if not args.verify:
        if args.push:
            raise RuntimeError("--verify is required with --push")
        raise RuntimeError("integration requires --verify")

    integration_branch = f"workflow/integrate/{candidate_sha[:12]}-{os.getpid()}-{attempt}"
    switched = command("git", "switch", "--create", integration_branch, "--no-track", base_target_sha)
    if switched.returncode:
        return EXIT_PRECONDITION
    state = {
        "base_target_sha": base_target_sha,
        "candidate_sha": candidate_sha,
        "integration_branch": integration_branch,
        "original_branch": candidate_branch,
        "remote": args.remote,
        "target": args.target,
        "tag": args.tag,
        "integration_started_epoch": time.time(),
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
    verified = verify_integration(args, state)
    if verified:
        integration_branch = str(state["integration_branch"])
        integration_sha = str(state.get("integration_sha") or "")
        worktree = Path(git_output("rev-parse", "--show-toplevel"))
        clean_failure = (
            verified == EXIT_VERIFY
            and not merge_in_progress()
            and not other_git_operation_in_progress(worktree)
            and not conflict_files()
            and not git_output("status", "--porcelain")
            and git_output("branch", "--show-current") == integration_branch
            and git_output("rev-parse", "HEAD") == integration_sha
        )
        if clean_failure:
            candidate_branch = str(state["original_branch"])
            restore_candidate(state, delete_integration=False)
            print(
                f"safe_merge: restored candidate {candidate_branch}; "
                f"failed integration retained as {integration_branch}."
            )
        return verified

    integration_branch = str(state["integration_branch"])
    if not args.push:
        receipt = write_receipt(state, status="verified", transport_attempts=0)
        restore_candidate(state, delete_integration=False)
        print(
            f"safe_merge: verified integration retained as {integration_branch}; "
            f"push not requested; receipt {receipt}."
        )
        return 0

    remote = str(state["remote"])
    target = str(state["target"])
    remote_ref = f"{remote}/{target}"
    verified_sha = str(state["verified_integration_sha"])
    for transport_attempt in range(1, args.max_retries + 1):
        tag = str(state.get("tag") or "")
        remote_tag_sha = remote_ref_sha(remote, f"refs/tags/{tag}") if tag else None
        if remote_tag_sha is not None and remote_tag_sha != verified_sha:
            print(f"safe_merge: tag already exists: {tag}", file=sys.stderr)
            restore_candidate(state, delete_integration=True)
            return EXIT_PRECONDITION
        current_target_sha = fetch_target(remote, target)
        if current_target_sha is None:
            if transport_attempt < args.max_retries:
                print("safe_merge: transport check failed; retrying the same verified integration.")
                continue
            print("safe_merge: transport unavailable; verified integration retained for --continue.")
            return EXIT_BUSY
        if current_target_sha == verified_sha:
            if tag and remote_tag_sha != verified_sha:
                print(
                    "safe_merge: target contains the verified integration but the requested tag is absent.",
                    file=sys.stderr,
                )
                return EXIT_PRECONDITION
            receipt = write_receipt(
                state, status="pushed", transport_attempts=transport_attempt - 1
            )
            restore_candidate(state, delete_integration=True)
            print(f"safe_merge: remote already contains the verified integration; receipt {receipt}.")
            return 0
        if current_target_sha != str(state["base_target_sha"]):
            print("safe_merge: target advanced before push; rebuilding from the latest target.")
            restore_candidate(state, delete_integration=not preserve_on_retry)
            return RETRY
        if git_output("rev-parse", "HEAD") != verified_sha or git_output("status", "--porcelain"):
            print(
                "safe_merge: integration changed after verification; push refused.",
                file=sys.stderr,
            )
            return EXIT_VERIFY
        push_parts = ["git", "push"]
        if tag:
            push_parts.append("--atomic")
        push_parts.extend((remote, f"{verified_sha}:refs/heads/{target}"))
        if tag:
            push_parts.append(f"{verified_sha}:refs/tags/{tag}")
        pushed = command(*push_parts)
        if pushed.returncode == 0:
            receipt = write_receipt(
                state, status="pushed", transport_attempts=transport_attempt
            )
            restore_candidate(state, delete_integration=True)
            action = "atomically pushed target and tag" if tag else "pushed target-first merge"
            print(f"safe_merge: {action} to {remote_ref}; receipt {receipt}.")
            return 0
        if transport_attempt < args.max_retries:
            print("safe_merge: push failed; retrying the same verified integration.")
            continue
        print("safe_merge: push transport failed; verified integration retained for --continue.")
        return EXIT_BUSY


def continue_merge(args: argparse.Namespace) -> int:
    if not args.verify:
        raise RuntimeError("integration requires --verify")
    state = load_state()
    if args.remote != state.get("remote") or args.target != state.get("target"):
        raise RuntimeError("--continue remote/target does not match the preserved integration")
    if args.tag != str(state.get("tag") or ""):
        raise RuntimeError("--continue tag does not match the preserved integration")
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
    target_sha = fetch_target(args.remote, args.target)
    if target_sha is None:
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
        target_sha,
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
    target_sha = fetch_target(args.remote, args.target)
    if target_sha is None:
        return EXIT_PRECONDITION
    head = git_output("rev-parse", "HEAD", cwd=target_path)
    remote_ref = f"{args.remote}/{args.target}"
    if command("git", "merge-base", "--is-ancestor", head, target_sha).returncode:
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
    parser.add_argument("--tag", default="", help="atomically create this tag with the target push")
    lifecycle = parser.add_mutually_exclusive_group()
    lifecycle.add_argument("--sync-baseline", action="store_true")
    lifecycle.add_argument("--create-worktree")
    lifecycle.add_argument("--cleanup-worktree")
    parser.add_argument("--branch", default="")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--yes", action="store_true")
    return parser.parse_args()


def validate_mode(args: argparse.Namespace) -> None:
    if args.tag and not args.push:
        raise RuntimeError("--tag requires --push")
    if args.sync_baseline and (
        args.continue_merge
        or args.push
        or args.verify
        or args.branch
        or args.task_id
        or args.yes
        or args.tag
    ):
        raise RuntimeError("--sync-baseline cannot be combined with integration or worktree options")
    if args.create_worktree and (args.continue_merge or args.push or args.verify or args.yes or args.tag):
        raise RuntimeError("--create-worktree cannot be combined with integration options")
    if args.cleanup_worktree and (
        args.continue_merge or args.push or args.verify or args.branch
        or args.tag
    ):
        raise RuntimeError("--cleanup-worktree cannot be combined with integration options")
    if not (args.sync_baseline or args.create_worktree or args.cleanup_worktree) and (
        args.branch or args.task_id or args.yes
    ):
        raise RuntimeError("worktree lifecycle options require a lifecycle action")


def main() -> int:
    args = parse_args()
    if args.max_retries < 1:
        print("safe_merge: --max-retries must be positive.", file=sys.stderr)
        return EXIT_PRECONDITION
    try:
        validate_mode(args)
        if git_output("rev-parse", "--is-inside-work-tree") != "true":
            raise RuntimeError("not inside a git worktree")
        validate_repository_parameters(args.remote, args.target)
        validate_tag(args.tag)
        if args.sync_baseline:
            return sync_baseline(args)
        if args.create_worktree:
            return create_worktree(args)
        if args.cleanup_worktree:
            return cleanup_worktree(args)
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
