from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import json


PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "scripts/safe_merge.py"


def run(*parts: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(parts),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
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
