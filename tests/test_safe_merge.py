from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import json
import os
import shutil


PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "scripts/safe_merge.py"


def run(
    *parts: str,
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(parts),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=env,
    )
    if check and result.returncode:
        raise AssertionError(f"command failed ({result.returncode}): {' '.join(parts)}\n{result.stdout}")
    return result


class SafeMergeIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        run("git", "init", "--bare", str(self.remote), cwd=self.root)
        self.seed = self.clone("seed")
        (self.seed / "shared.txt").write_text("base\n")
        (self.seed / "a.txt").write_text("base\n")
        (self.seed / "b.txt").write_text("base\n")
        run("git", "add", ".", cwd=self.seed)
        run("git", "commit", "-m", "seed", cwd=self.seed)
        run("git", "branch", "-M", "main", cwd=self.seed)
        run("git", "push", "-u", "origin", "main", cwd=self.seed)
        run("git", "symbolic-ref", "HEAD", "refs/heads/main", cwd=self.remote)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def clone(self, name: str) -> Path:
        target = self.root / name
        run("git", "clone", str(self.remote), str(target), cwd=self.root)
        run("git", "config", "user.name", "Workflow Test", cwd=target)
        run("git", "config", "user.email", "workflow@example.test", cwd=target)
        return target

    def branch(self, clone: Path, name: str) -> None:
        run("git", "checkout", "-b", name, "origin/main", cwd=clone)

    def safe_merge(self, clone: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return run(
            sys.executable,
            "-B",
            str(SCRIPT),
            "--target",
            "main",
            "--remote",
            "origin",
            "--verify",
            f"{sys.executable} -c \"from pathlib import Path; assert Path('shared.txt').exists()\"",
            *extra,
            cwd=clone,
            check=False,
        )

    def lifecycle(self, clone: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return run(
            sys.executable,
            "-B",
            str(SCRIPT),
            "--target",
            "main",
            "--remote",
            "origin",
            *extra,
            cwd=clone,
            check=False,
        )

    def test_non_conflicting_late_merger_preserves_candidate_and_target_first_parent(self) -> None:
        first = self.clone("first")
        second = self.clone("second")
        self.branch(first, "feature-first")
        self.branch(second, "feature-second")

        (first / "a.txt").write_text("first\n")
        run("git", "add", "a.txt", cwd=first)
        run("git", "commit", "-m", "first", cwd=first)
        run("git", "push", "origin", "HEAD:main", cwd=first)
        target_sha = run("git", "rev-parse", "HEAD", cwd=first).stdout.strip()

        (second / "b.txt").write_text("second\n")
        run("git", "add", "b.txt", cwd=second)
        run("git", "commit", "-m", "second", cwd=second)
        candidate_sha = run("git", "rev-parse", "HEAD", cwd=second).stdout.strip()
        result = self.safe_merge(second, "--push")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("merge candidate", result.stdout)
        self.assertIn("verification passed", result.stdout)
        self.assertEqual(run("git", "branch", "--show-current", cwd=second).stdout.strip(), "feature-second")
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=second).stdout.strip(), candidate_sha)
        audit = self.clone("audit-non-conflict")
        self.assertEqual((audit / "a.txt").read_text(), "first\n")
        self.assertEqual((audit / "b.txt").read_text(), "second\n")
        parents = run("git", "rev-list", "--parents", "-n", "1", "HEAD", cwd=audit).stdout.split()
        self.assertEqual(parents[1:], [target_sha, candidate_sha])

    def test_sync_baseline_fast_forwards_a_clean_unstarted_worktree(self) -> None:
        stale = self.clone("stale-baseline")
        self.branch(stale, "feature-stale-baseline")
        old_sha = run("git", "rev-parse", "HEAD", cwd=stale).stdout.strip()

        updater = self.clone("baseline-updater")
        self.branch(updater, "feature-baseline-updater")
        (updater / "a.txt").write_text("latest baseline\n")
        run("git", "add", "a.txt", cwd=updater)
        run("git", "commit", "-m", "advance baseline", cwd=updater)
        run("git", "push", "origin", "HEAD:main", cwd=updater)
        latest_sha = run("git", "rev-parse", "HEAD", cwd=updater).stdout.strip()

        synced = self.lifecycle(stale, "--sync-baseline")

        self.assertEqual(synced.returncode, 0, synced.stdout)
        self.assertIn("baseline fast-forwarded", synced.stdout)
        self.assertEqual(run("git", "branch", "--show-current", cwd=stale).stdout.strip(), "feature-stale-baseline")
        self.assertNotEqual(old_sha, latest_sha)
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=stale).stdout.strip(), latest_sha)
        self.assertEqual((stale / "a.txt").read_text(), "latest baseline\n")

    def test_sync_baseline_refuses_dirty_or_diverged_work(self) -> None:
        dirty = self.clone("dirty-baseline")
        self.branch(dirty, "feature-dirty-baseline")
        (dirty / "a.txt").write_text("uncommitted intent\n")
        refused_dirty = self.lifecycle(dirty, "--sync-baseline")
        self.assertEqual(refused_dirty.returncode, 2, refused_dirty.stdout)
        self.assertIn("worktree has uncommitted changes", refused_dirty.stdout)

        diverged = self.clone("diverged-baseline")
        self.branch(diverged, "feature-diverged-baseline")
        (diverged / "b.txt").write_text("local candidate\n")
        run("git", "add", "b.txt", cwd=diverged)
        run("git", "commit", "-m", "local candidate", cwd=diverged)
        refused_diverged = self.lifecycle(diverged, "--sync-baseline")
        self.assertEqual(refused_diverged.returncode, 2, refused_diverged.stdout)
        self.assertIn("cannot fast-forward baseline", refused_diverged.stdout)

    def test_sync_baseline_refuses_preserved_integration_state_and_mixed_modes(self) -> None:
        stale = self.clone("stateful-baseline")
        self.branch(stale, "feature-stateful-baseline")
        old_sha = run("git", "rev-parse", "HEAD", cwd=stale).stdout.strip()

        updater = self.clone("stateful-baseline-updater")
        self.branch(updater, "feature-stateful-baseline-updater")
        (updater / "a.txt").write_text("latest baseline\n")
        run("git", "add", "a.txt", cwd=updater)
        run("git", "commit", "-m", "advance baseline", cwd=updater)
        run("git", "push", "origin", "HEAD:main", cwd=updater)

        state = Path(
            run(
                "git",
                "rev-parse",
                "--path-format=absolute",
                "--git-path",
                "workflow-integration-state.json",
                cwd=stale,
            ).stdout.strip()
        )
        state.write_text("{}", encoding="utf-8")
        refused_state = self.lifecycle(stale, "--sync-baseline")
        self.assertEqual(refused_state.returncode, 2, refused_state.stdout)
        self.assertIn("integration state", refused_state.stdout)
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=stale).stdout.strip(), old_sha)

        state.unlink()
        refused_mode = self.lifecycle(stale, "--sync-baseline", "--push")
        self.assertEqual(refused_mode.returncode, 2, refused_mode.stdout)
        self.assertIn("cannot be combined", refused_mode.stdout)
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=stale).stdout.strip(), old_sha)

    def test_sync_baseline_checks_the_exact_fetched_sha_and_clean_postcondition(self) -> None:
        stale = self.clone("hooked-baseline")
        self.branch(stale, "feature-hooked-baseline")

        updater = self.clone("hooked-baseline-updater")
        self.branch(updater, "feature-hooked-baseline-updater")
        (updater / "a.txt").write_text("latest baseline\n")
        run("git", "add", "a.txt", cwd=updater)
        run("git", "commit", "-m", "advance baseline", cwd=updater)
        run("git", "push", "origin", "HEAD:main", cwd=updater)
        latest_sha = run("git", "rev-parse", "HEAD", cwd=updater).stdout.strip()

        hook = stale / ".git" / "hooks" / "post-merge"
        hook.write_text("#!/bin/sh\nprintf 'hook side effect\\n' > shared.txt\n", encoding="utf-8")
        hook.chmod(0o755)
        result = self.lifecycle(stale, "--sync-baseline")

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("baseline postcondition failed", result.stdout)
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=stale).stdout.strip(), latest_sha)
        self.assertIn("shared.txt", run("git", "status", "--short", cwd=stale).stdout)

    def test_already_integrated_candidate_is_a_noop_without_revalidating_old_tree(self) -> None:
        candidate = self.clone("already-integrated")
        self.branch(candidate, "feature-already-integrated")
        (candidate / "a.txt").write_text("already integrated\n")
        run("git", "add", "a.txt", cwd=candidate)
        run("git", "commit", "-m", "already integrated", cwd=candidate)
        run("git", "push", "origin", "HEAD:main", cwd=candidate)

        marker = self.root / "stale-tree-verify-ran"
        verify_command = (
            f"{sys.executable} -c \"from pathlib import Path; "
            f"Path(r'{marker}').write_text('ran'); raise SystemExit(9)\""
        )
        result = run(
            sys.executable,
            "-B",
            str(SCRIPT),
            "--target",
            "main",
            "--remote",
            "origin",
            "--verify",
            verify_command,
            "--push",
            cwd=candidate,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("already_integrated", result.stdout)
        self.assertFalse(marker.exists())

    def test_verification_must_leave_the_exact_integration_tree_clean(self) -> None:
        candidate = self.clone("dirty-verifier")
        self.branch(candidate, "feature-dirty-verifier")
        (candidate / "a.txt").write_text("candidate change\n")
        run("git", "add", "a.txt", cwd=candidate)
        run("git", "commit", "-m", "candidate change", cwd=candidate)
        remote_before = run("git", "rev-parse", "origin/main", cwd=candidate).stdout.strip()

        verify_command = (
            f"{sys.executable} -c \"from pathlib import Path; "
            "Path('shared.txt').write_text('verification side effect\\n')\""
        )
        result = run(
            sys.executable,
            "-B",
            str(SCRIPT),
            "--target",
            "main",
            "--remote",
            "origin",
            "--verify",
            verify_command,
            "--push",
            cwd=candidate,
            check=False,
        )

        self.assertEqual(result.returncode, 4, result.stdout)
        self.assertIn("verification changed the integration worktree", result.stdout)
        run("git", "fetch", "origin", "main", cwd=candidate)
        self.assertEqual(run("git", "rev-parse", "origin/main", cwd=candidate).stdout.strip(), remote_before)

    def test_verification_cannot_replace_the_integration_commit(self) -> None:
        candidate = self.clone("commit-verifier")
        self.branch(candidate, "feature-commit-verifier")
        (candidate / "a.txt").write_text("candidate change\n")
        run("git", "add", "a.txt", cwd=candidate)
        run("git", "commit", "-m", "candidate change", cwd=candidate)
        remote_before = run("git", "rev-parse", "origin/main", cwd=candidate).stdout.strip()

        verify_command = (
            f"{sys.executable} -c \"from pathlib import Path; "
            "Path('shared.txt').write_text('committed verification side effect\\n')\" "
            "&& git add shared.txt && git commit -m 'verifier mutation'"
        )
        result = run(
            sys.executable,
            "-B",
            str(SCRIPT),
            "--target",
            "main",
            "--remote",
            "origin",
            "--verify",
            verify_command,
            "--push",
            cwd=candidate,
            check=False,
        )

        self.assertEqual(result.returncode, 4, result.stdout)
        self.assertIn("verification changed the integration worktree", result.stdout)
        run("git", "fetch", "origin", "main", cwd=candidate)
        self.assertEqual(run("git", "rev-parse", "origin/main", cwd=candidate).stdout.strip(), remote_before)

    def test_failed_verifier_cannot_rebind_continue_to_its_own_commit(self) -> None:
        candidate = self.clone("failed-commit-verifier")
        self.branch(candidate, "feature-failed-commit-verifier")
        (candidate / "a.txt").write_text("candidate change\n")
        run("git", "add", "a.txt", cwd=candidate)
        run("git", "commit", "-m", "candidate change", cwd=candidate)
        remote_before = run("git", "rev-parse", "origin/main", cwd=candidate).stdout.strip()

        mutating_failure = (
            f"{sys.executable} -c \"from pathlib import Path; "
            "Path('shared.txt').write_text('failed verifier mutation\\n')\" "
            "&& git add shared.txt && git commit -m 'failed verifier mutation' && exit 9"
        )
        first = run(
            sys.executable,
            "-B",
            str(SCRIPT),
            "--target",
            "main",
            "--remote",
            "origin",
            "--verify",
            mutating_failure,
            "--push",
            cwd=candidate,
            check=False,
        )
        self.assertEqual(first.returncode, 4, first.stdout)
        self.assertIn("verification changed the integration worktree", first.stdout)

        second = run(
            sys.executable,
            "-B",
            str(SCRIPT),
            "--target",
            "main",
            "--remote",
            "origin",
            "--verify",
            f"{sys.executable} -c \"raise SystemExit(0)\"",
            "--continue",
            "--push",
            cwd=candidate,
            check=False,
        )

        self.assertEqual(second.returncode, 2, second.stdout)
        self.assertIn("integration HEAD changed", second.stdout)
        run("git", "fetch", "origin", "main", cwd=candidate)
        self.assertEqual(run("git", "rev-parse", "origin/main", cwd=candidate).stdout.strip(), remote_before)

    def test_worktree_movement_after_verification_never_pushes_the_moved_head(self) -> None:
        candidate = self.clone("late-head-movement")
        self.branch(candidate, "feature-late-head-movement")
        (candidate / "a.txt").write_text("candidate change\n")
        run("git", "add", "a.txt", cwd=candidate)
        run("git", "commit", "-m", "candidate change", cwd=candidate)
        remote_before = run("git", "rev-parse", "origin/main", cwd=candidate).stdout.strip()

        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        wrapper_dir = self.root / "git-wrapper"
        wrapper_dir.mkdir()
        marker = self.root / "verification-finished"
        done = self.root / "late-mutation-done"
        wrapper = wrapper_dir / "git"
        wrapper.write_text(
            "#!/usr/bin/env python3\n"
            "import os, subprocess, sys\n"
            "from pathlib import Path\n"
            "real = os.environ['REAL_GIT']\n"
            "args = sys.argv[1:]\n"
            "result = subprocess.run([real, *args], check=False)\n"
            "marker = Path(os.environ['MUTATION_MARKER'])\n"
            "done = Path(os.environ['MUTATION_DONE'])\n"
            "if result.returncode == 0 and args and args[0] == 'fetch' and marker.exists() and not done.exists():\n"
            "    done.touch()\n"
            "    Path('shared.txt').write_text('late unverified mutation\\n')\n"
            "    subprocess.run([real, 'add', 'shared.txt'], check=True)\n"
            "    subprocess.run([real, 'commit', '-m', 'late unverified mutation'], check=True)\n"
            "raise SystemExit(result.returncode)\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        environment = {
            **os.environ,
            "PATH": f"{wrapper_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "REAL_GIT": str(real_git),
            "MUTATION_MARKER": str(marker),
            "MUTATION_DONE": str(done),
        }
        verify_command = f"{sys.executable} -c \"from pathlib import Path; Path(r'{marker}').touch()\""
        result = run(
            sys.executable,
            "-B",
            str(SCRIPT),
            "--target",
            "main",
            "--remote",
            "origin",
            "--verify",
            verify_command,
            "--push",
            cwd=candidate,
            check=False,
            env=environment,
        )

        self.assertEqual(result.returncode, 4, result.stdout)
        self.assertIn("integration changed after verification", result.stdout)
        run("git", "fetch", "origin", "main", cwd=candidate)
        self.assertEqual(run("git", "rev-parse", "origin/main", cwd=candidate).stdout.strip(), remote_before)

    def test_continue_refuses_unrelated_dirty_changes_before_verification(self) -> None:
        first = self.clone("continue-dirty-first")
        candidate = self.clone("continue-dirty-candidate")
        self.branch(first, "feature-continue-dirty-first")
        self.branch(candidate, "feature-continue-dirty-candidate")

        (first / "shared.txt").write_text("target intent\n")
        run("git", "add", "shared.txt", cwd=first)
        run("git", "commit", "-m", "target intent", cwd=first)
        run("git", "push", "origin", "HEAD:main", cwd=first)
        remote_before = run("git", "rev-parse", "HEAD", cwd=first).stdout.strip()

        (candidate / "shared.txt").write_text("candidate intent\n")
        run("git", "add", "shared.txt", cwd=candidate)
        run("git", "commit", "-m", "candidate intent", cwd=candidate)
        conflict = self.safe_merge(candidate, "--push")
        self.assertEqual(conflict.returncode, 3, conflict.stdout)

        (candidate / "shared.txt").write_text("target intent\ncandidate intent\n")
        run("git", "add", "shared.txt", cwd=candidate)
        (candidate / "a.txt").write_text("unrelated unstaged change\n")
        marker = self.root / "dirty-continue-verifier-ran"
        verify_command = f"{sys.executable} -c \"from pathlib import Path; Path(r'{marker}').touch()\""
        continued = run(
            sys.executable,
            "-B",
            str(SCRIPT),
            "--target",
            "main",
            "--remote",
            "origin",
            "--verify",
            verify_command,
            "--continue",
            "--push",
            cwd=candidate,
            check=False,
        )

        self.assertEqual(continued.returncode, 2, continued.stdout)
        self.assertIn("not clean before verification", continued.stdout)
        self.assertFalse(marker.exists())
        run("git", "fetch", "origin", "main", cwd=candidate)
        self.assertEqual(run("git", "rev-parse", "origin/main", cwd=candidate).stdout.strip(), remote_before)

    def test_project_supplied_remote_and_target_use_forced_target_first_merge(self) -> None:
        run("git", "push", "origin", "main:release/stable", cwd=self.seed)
        base_sha = run("git", "rev-parse", "HEAD", cwd=self.seed).stdout.strip()
        candidate = self.root / "custom-repository-contract"
        run(
            "git",
            "clone",
            "--single-branch",
            "--branch",
            "main",
            str(self.remote),
            str(candidate),
            cwd=self.root,
        )
        run("git", "config", "user.name", "Workflow Test", cwd=candidate)
        run("git", "config", "user.email", "workflow@example.test", cwd=candidate)
        run("git", "remote", "rename", "origin", "upstream", cwd=candidate)
        run("git", "checkout", "-b", "feature-custom-contract", cwd=candidate)
        (candidate / "b.txt").write_text("custom target candidate\n")
        run("git", "add", "b.txt", cwd=candidate)
        run("git", "commit", "-m", "custom target candidate", cwd=candidate)
        candidate_sha = run("git", "rev-parse", "HEAD", cwd=candidate).stdout.strip()

        result = run(
            sys.executable,
            "-B",
            str(SCRIPT),
            "--target",
            "release/stable",
            "--remote",
            "upstream",
            "--verify",
            f"{sys.executable} -c \"from pathlib import Path; assert Path('b.txt').exists()\"",
            "--push",
            cwd=candidate,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        audit = self.root / "custom-contract-audit"
        run(
            "git",
            "clone",
            "--branch",
            "release/stable",
            str(self.remote),
            str(audit),
            cwd=self.root,
        )
        parents = run("git", "rev-list", "--parents", "-n", "1", "HEAD", cwd=audit).stdout.split()
        self.assertEqual(parents[1:], [base_sha, candidate_sha])
        remote_main = run(
            "git",
            "ls-remote",
            str(self.remote),
            "refs/heads/main",
            cwd=self.root,
        ).stdout.split()[0]
        self.assertEqual(remote_main, base_sha)

    def test_transport_retry_reuses_verified_sha_without_rerunning_verification(self) -> None:
        candidate = self.clone("transport-retry")
        self.branch(candidate, "feature-transport-retry")
        (candidate / "a.txt").write_text("transport retry\n")
        run("git", "add", "a.txt", cwd=candidate)
        run("git", "commit", "-m", "transport retry", cwd=candidate)

        reject_marker = self.remote / "first-push-rejected"
        hook = self.remote / "hooks" / "pre-receive"
        hook.write_text(
            "#!/bin/sh\n"
            f"if [ ! -f '{reject_marker}' ]; then\n"
            f"  : > '{reject_marker}'\n"
            "  echo transient transport failure >&2\n"
            "  exit 1\n"
            "fi\n"
            "exit 0\n"
        )
        hook.chmod(0o755)

        verify_counter = self.root / "verify-count.txt"
        verify_command = (
            f"{sys.executable} -c \"from pathlib import Path; "
            f"p=Path(r'{verify_counter}'); p.write_text(p.read_text()+'1' if p.exists() else '1'); "
            "print('VERY_VERBOSE_SUCCESS_OUTPUT')\""
        )
        result = run(
            sys.executable,
            "-B",
            str(SCRIPT),
            "--target",
            "main",
            "--remote",
            "origin",
            "--verify",
            verify_command,
            "--max-retries",
            "2",
            "--push",
            cwd=candidate,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(verify_counter.read_text(), "1")
        self.assertNotIn("VERY_VERBOSE_SUCCESS_OUTPUT", result.stdout)
        self.assertIn("retrying the same verified integration", result.stdout)
        common_dir = Path(run("git", "rev-parse", "--git-common-dir", cwd=candidate).stdout.strip())
        if not common_dir.is_absolute():
            common_dir = (candidate / common_dir).resolve()
        receipts = list((common_dir / "codex" / "workflow-merge-receipts").glob("*.json"))
        self.assertEqual(len(receipts), 1)
        receipt = json.loads(receipts[0].read_text())
        self.assertEqual(receipt["status"], "pushed")
        self.assertEqual(receipt["transport_attempts"], 2)

    def test_atomic_publish_moves_target_and_new_tag_to_same_verified_sha(self) -> None:
        candidate = self.clone("atomic-publish")
        self.branch(candidate, "feature-atomic-publish")
        (candidate / "a.txt").write_text("atomic publish\n")
        run("git", "add", "a.txt", cwd=candidate)
        run("git", "commit", "-m", "atomic publish", cwd=candidate)

        result = self.safe_merge(candidate, "--push", "--tag", "3.7.0")

        self.assertEqual(result.returncode, 0, result.stdout)
        refs = run(
            "git",
            "ls-remote",
            str(self.remote),
            "refs/heads/main",
            "refs/tags/3.7.0",
            cwd=self.root,
        ).stdout.splitlines()
        resolved = {line.split()[1]: line.split()[0] for line in refs}
        self.assertEqual(resolved["refs/heads/main"], resolved["refs/tags/3.7.0"])
        self.assertIn("atomically pushed", result.stdout)

    def test_existing_release_tag_fails_closed_without_moving_target(self) -> None:
        run("git", "tag", "3.7.0", cwd=self.seed)
        run("git", "push", "origin", "refs/tags/3.7.0", cwd=self.seed)
        remote_before = run(
            "git", "ls-remote", str(self.remote), "refs/heads/main", cwd=self.root
        ).stdout.split()[0]
        candidate = self.clone("tag-collision")
        self.branch(candidate, "feature-tag-collision")
        (candidate / "a.txt").write_text("must not publish\n")
        run("git", "add", "a.txt", cwd=candidate)
        run("git", "commit", "-m", "tag collision", cwd=candidate)

        result = self.safe_merge(candidate, "--push", "--tag", "3.7.0")

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("tag already exists", result.stdout)
        remote_after = run(
            "git", "ls-remote", str(self.remote), "refs/heads/main", cwd=self.root
        ).stdout.split()[0]
        self.assertEqual(remote_after, remote_before)

    def test_losing_same_tag_race_restores_candidate_for_replanning(self) -> None:
        candidate = self.clone("tag-race")
        self.branch(candidate, "feature-tag-race")
        (candidate / "a.txt").write_text("tag race\n")
        run("git", "add", "a.txt", cwd=candidate)
        run("git", "commit", "-m", "tag race", cwd=candidate)
        candidate_sha = run("git", "rev-parse", "HEAD", cwd=candidate).stdout.strip()
        base_sha = run(
            "git", "ls-remote", str(self.remote), "refs/heads/main", cwd=self.root
        ).stdout.split()[0]
        hook = candidate / ".git" / "hooks" / "pre-push"
        marker = self.root / "race-created"
        hook.write_text(
            "#!/bin/sh\n"
            f"if [ ! -f '{marker}' ]; then\n"
            f"  : > '{marker}'\n"
            f"  git --git-dir='{self.remote}' update-ref refs/tags/3.7.0 {base_sha}\n"
            "fi\n"
            "exit 0\n"
        )
        hook.chmod(0o755)

        result = self.safe_merge(candidate, "--push", "--tag", "3.7.0", "--max-retries", "2")

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("tag already exists", result.stdout)
        self.assertEqual(
            run("git", "branch", "--show-current", cwd=candidate).stdout.strip(),
            "feature-tag-race",
        )
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=candidate).stdout.strip(), candidate_sha)
        self.assertFalse((candidate / ".git" / "workflow-integration-state.json").exists())
        remote_main = run(
            "git", "ls-remote", str(self.remote), "refs/heads/main", cwd=self.root
        ).stdout.split()[0]
        self.assertEqual(remote_main, base_sha)

    def test_tag_requires_push_and_valid_tag_name(self) -> None:
        candidate = self.clone("invalid-tag")
        self.branch(candidate, "feature-invalid-tag")
        (candidate / "a.txt").write_text("invalid tag\n")
        run("git", "add", "a.txt", cwd=candidate)
        run("git", "commit", "-m", "invalid tag", cwd=candidate)

        missing_push = self.safe_merge(candidate, "--tag", "3.7.0")
        invalid_name = self.safe_merge(candidate, "--push", "--tag", "bad tag")

        self.assertEqual(missing_push.returncode, 2, missing_push.stdout)
        self.assertIn("--tag requires --push", missing_push.stdout)
        self.assertEqual(invalid_name.returncode, 2, invalid_name.stdout)
        self.assertIn("valid Git tag", invalid_name.stdout)

    def test_multi_commit_conflict_is_resolved_once_without_rewriting_candidate(self) -> None:
        first = self.clone("conflict-first")
        second = self.clone("conflict-second")
        self.branch(first, "feature-conflict-first")
        self.branch(second, "feature-conflict-second")

        (first / "shared.txt").write_text("first intent\n")
        run("git", "add", "shared.txt", cwd=first)
        run("git", "commit", "-m", "first intent", cwd=first)
        run("git", "push", "origin", "HEAD:main", cwd=first)

        (second / "shared.txt").write_text("second step one\n")
        run("git", "add", "shared.txt", cwd=second)
        run("git", "commit", "-m", "second step one", cwd=second)
        (second / "shared.txt").write_text("second final intent\n")
        run("git", "add", "shared.txt", cwd=second)
        run("git", "commit", "-m", "second final intent", cwd=second)
        candidate_sha = run("git", "rev-parse", "HEAD", cwd=second).stdout.strip()
        conflict = self.safe_merge(second, "--push")

        self.assertEqual(conflict.returncode, 3, conflict.stdout)
        self.assertIn("conflict preserved", conflict.stdout)
        self.assertTrue((second / ".git" / "MERGE_HEAD").exists())
        self.assertTrue(
            run("git", "branch", "--show-current", cwd=second).stdout.strip().startswith("workflow/integrate/")
        )
        self.assertFalse((second / ".git" / "workflow-merge.lock").exists())
        unmerged = run("git", "diff", "--name-only", "--diff-filter=U", cwd=second)
        self.assertIn("shared.txt", unmerged.stdout)

        (second / "shared.txt").write_text("first intent\nsecond final intent\n")
        run("git", "add", "shared.txt", cwd=second)
        continued = self.safe_merge(second, "--continue", "--push")
        self.assertEqual(continued.returncode, 0, continued.stdout)
        self.assertEqual(
            run("git", "branch", "--show-current", cwd=second).stdout.strip(),
            "feature-conflict-second",
        )
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=second).stdout.strip(), candidate_sha)
        audit = self.clone("audit-conflict")
        self.assertEqual(
            (audit / "shared.txt").read_text(),
            "first intent\nsecond final intent\n",
        )

    def test_push_requires_verification_evidence(self) -> None:
        candidate = self.clone("unverified")
        self.branch(candidate, "feature-unverified")
        (candidate / "a.txt").write_text("unverified\n")
        run("git", "add", "a.txt", cwd=candidate)
        run("git", "commit", "-m", "unverified", cwd=candidate)
        result = self.lifecycle(candidate, "--push")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("--verify is required with --push", result.stdout)

    def test_locked_worktree_is_removed_only_after_clean_integrated_completion(self) -> None:
        managed = self.root / "managed"
        created = self.lifecycle(
            self.seed,
            "--create-worktree",
            str(managed),
            "--branch",
            "feature-managed",
            "--task-id",
            "T-managed",
        )
        self.assertEqual(created.returncode, 0, created.stdout)
        listing = run("git", "worktree", "list", "--porcelain", cwd=self.seed).stdout
        self.assertIn(str(managed), listing)
        self.assertIn("locked workflow:T-managed", listing)

        (managed / "a.txt").write_text("managed\n")
        run("git", "add", "a.txt", cwd=managed)
        run("git", "commit", "-m", "managed", cwd=managed)
        run("git", "push", "origin", "HEAD:main", cwd=managed)
        cleaned = self.lifecycle(
            self.seed,
            "--cleanup-worktree",
            str(managed),
            "--task-id",
            "T-managed",
            "--yes",
        )
        self.assertEqual(cleaned.returncode, 0, cleaned.stdout)
        self.assertFalse(managed.exists())
        branch = run(
            "git",
            "show-ref",
            "--verify",
            "refs/heads/feature-managed",
            cwd=self.seed,
            check=False,
        )
        self.assertEqual(branch.returncode, 0, branch.stdout)

    def test_dirty_worktree_is_preserved_during_cleanup(self) -> None:
        managed = self.root / "dirty-managed"
        created = self.lifecycle(
            self.seed,
            "--create-worktree",
            str(managed),
            "--branch",
            "feature-dirty-managed",
            "--task-id",
            "T-dirty",
        )
        self.assertEqual(created.returncode, 0, created.stdout)
        wrong_owner = self.lifecycle(
            self.seed,
            "--cleanup-worktree",
            str(managed),
            "--task-id",
            "T-someone-else",
            "--yes",
        )
        self.assertEqual(wrong_owner.returncode, 2, wrong_owner.stdout)
        self.assertIn("active ownership cannot be proven", wrong_owner.stdout)
        self.assertTrue(managed.exists())
        (managed / "dirty.txt").write_text("do not delete\n")
        cleaned = self.lifecycle(
            self.seed,
            "--cleanup-worktree",
            str(managed),
            "--task-id",
            "T-dirty",
            "--yes",
        )
        self.assertEqual(cleaned.returncode, 2, cleaned.stdout)
        self.assertIn("worktree has uncommitted changes", cleaned.stdout)
        self.assertTrue(managed.exists())


if __name__ == "__main__":
    unittest.main()
