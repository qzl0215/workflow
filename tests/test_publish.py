from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "scripts/publish.py"


def run(*parts: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(parts),
        cwd=PACKAGE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


class WorkflowPublisherContractTest(unittest.TestCase):
    def test_publisher_requires_explicit_yes_and_exact_package_version(self) -> None:
        missing_yes = run(sys.executable, "-B", str(SCRIPT), "--version", "3.9.0")
        mismatch = run(
            sys.executable,
            "-B",
            str(SCRIPT),
            "--version",
            "3.7.1",
            "--yes",
        )

        self.assertEqual(missing_yes.returncode, 2, missing_yes.stdout)
        self.assertIn("--yes", missing_yes.stdout)
        self.assertEqual(mismatch.returncode, 2, mismatch.stdout)
        self.assertIn("does not match", mismatch.stdout)

    def test_resumed_release_syncs_the_already_confirmed_target_without_merging_again(self) -> None:
        spec = importlib.util.spec_from_file_location("workflow_publish_resume", SCRIPT)
        publish = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(PACKAGE / "scripts"))
        try:
            spec.loader.exec_module(publish)
        finally:
            sys.path.remove(str(PACKAGE / "scripts"))
        tag_sha, target_sha = "a" * 40, "b" * 40
        success = subprocess.CompletedProcess([], 0)
        with patch.object(publish, "remote_ref", side_effect=[tag_sha, target_sha]), \
                patch.object(publish, "command", return_value=success), \
                patch.object(publish, "checked", return_value=success) as checked:
            self.assertEqual(publish.integration_for("3.9.0", "c" * 40, ["unused-merge"]), tag_sha)
        checked.assert_called_once_with(
            sys.executable, "-B", str(PACKAGE / "scripts/safe_merge.py"),
            "--remote", publish.REMOTE, "--target", publish.TARGET,
            "--sync-baseline", "--confirmed-target", target_sha,
        )

    def test_release_plan_reuses_existing_owners_and_one_complete_gate(self) -> None:
        spec = importlib.util.spec_from_file_location("workflow_publish", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec else None)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        sys.path.insert(0, str(PACKAGE / "scripts"))
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        finally:
            sys.path.remove(str(PACKAGE / "scripts"))

        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "workflow.zip"
            commands = module.release_commands("3.9.0", "a" * 40, asset)

        flattened = [tuple(command) for command in commands]
        merge = next(command for command in flattened if "safe_merge.py" in " ".join(command))
        self.assertIn("--push", merge)
        self.assertIn("--tag", merge)
        self.assertIn("3.9.0", merge)
        verify = merge[merge.index("--verify") + 1]
        self.assertEqual(verify.count("unittest discover"), 1)
        self.assertEqual(verify.count("release_check.py"), 1)
        self.assertTrue(any("--build-runtime" in command for command in flattened))
        self.assertTrue(any(command[:3] == ("gh", "release", "create") for command in flattened))
        self.assertTrue(any("install.py" in " ".join(command) and "sync" in command for command in flattened))


if __name__ == "__main__":
    unittest.main()
