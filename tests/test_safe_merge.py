from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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

    def test_non_conflicting_late_merger_rebases_verifies_and_pushes(self) -> None:
        first = self.clone("first")
        second = self.clone("second")
        self.branch(first, "feature-first")
        self.branch(second, "feature-second")

        (first / "a.txt").write_text("first\n")
        run("git", "add", "a.txt", cwd=first)
        run("git", "commit", "-m", "first", cwd=first)
        run("git", "push", "origin", "HEAD:main", cwd=first)

        (second / "b.txt").write_text("second\n")
        run("git", "add", "b.txt", cwd=second)
        run("git", "commit", "-m", "second", cwd=second)
        result = self.safe_merge(second, "--push")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("rebase", result.stdout)
        self.assertIn("verification passed", result.stdout)
        audit = self.clone("audit-non-conflict")
        self.assertEqual((audit / "a.txt").read_text(), "first\n")
        self.assertEqual((audit / "b.txt").read_text(), "second\n")

    def test_conflict_is_preserved_for_ai_resolution_and_continue(self) -> None:
        first = self.clone("conflict-first")
        second = self.clone("conflict-second")
        self.branch(first, "feature-conflict-first")
        self.branch(second, "feature-conflict-second")

        (first / "shared.txt").write_text("first intent\n")
        run("git", "add", "shared.txt", cwd=first)
        run("git", "commit", "-m", "first intent", cwd=first)
        run("git", "push", "origin", "HEAD:main", cwd=first)

        (second / "shared.txt").write_text("second intent\n")
        run("git", "add", "shared.txt", cwd=second)
        run("git", "commit", "-m", "second intent", cwd=second)
        conflict = self.safe_merge(second, "--push")

        self.assertEqual(conflict.returncode, 3, conflict.stdout)
        self.assertIn("conflict preserved", conflict.stdout)
        self.assertTrue((second / ".git" / "rebase-merge").exists() or (second / ".git" / "rebase-apply").exists())
        unmerged = run("git", "diff", "--name-only", "--diff-filter=U", cwd=second)
        self.assertIn("shared.txt", unmerged.stdout)

        (second / "shared.txt").write_text("first intent\nsecond intent\n")
        run("git", "add", "shared.txt", cwd=second)
        continued = self.safe_merge(second, "--continue", "--push")
        self.assertEqual(continued.returncode, 0, continued.stdout)
        audit = self.clone("audit-conflict")
        self.assertEqual((audit / "shared.txt").read_text(), "first intent\nsecond intent\n")


if __name__ == "__main__":
    unittest.main()
