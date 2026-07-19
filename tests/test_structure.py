from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]


class WorkflowDoctorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.package = Path(self.temp.name) / "workflow"
        shutil.copytree(PACKAGE, self.package, ignore=shutil.ignore_patterns(".git"))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_doctor(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(self.package / "scripts/workflow_doctor.py"), str(self.package)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def test_clean_package_passes(self) -> None:
        result = self.run_doctor()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("workflow_doctor: OK", result.stdout)

    def test_nested_skill_fails_closed(self) -> None:
        nested = self.package / "references/nested/SKILL.md"
        nested.parent.mkdir()
        shutil.copy2(self.package / "SKILL.md", nested)
        result = self.run_doctor()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected exactly one root SKILL.md", result.stdout)

    def test_external_capability_invocation_fails_closed(self) -> None:
        skill = self.package / "SKILL.md"
        skill.write_text(skill.read_text() + "\n$external-skill\n")
        result = self.run_doctor()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("external skill invocation remains", result.stdout)

    def test_broken_reference_link_fails_closed(self) -> None:
        reference = self.package / "references/context-discovery.md"
        reference.write_text(reference.read_text() + "\nreferences/missing.md\n")
        result = self.run_doctor()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("broken reference link", result.stdout)

    def test_reference_to_reference_deep_link_fails_closed(self) -> None:
        reference = self.package / "references/context-discovery.md"
        reference.write_text(reference.read_text() + "\nreferences/verification.md\n")
        result = self.run_doctor()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reference-to-reference deep link", result.stdout)

    def test_unowned_file_fails_closed(self) -> None:
        (self.package / "notes.md").write_text("orphan")
        result = self.run_doctor()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not owned by the public target manifest", result.stdout)

    def test_duplicate_protocol_owner_fails_closed(self) -> None:
        reference = self.package / "references/context-discovery.md"
        reference.write_text(reference.read_text() + "\n## 根因循环\n")
        result = self.run_doctor()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("protocol `## 根因循环` owner mismatch", result.stdout)

    def test_templates_have_one_status_owner_and_no_legacy_tools(self) -> None:
        expected = {
            "index.md",
            "findings.md",
            "task_plan.md",
            "implementation-plan.md",
            "progress.md",
            "task-owner-prompt.md",
            "pre-plan-contract.md",
        }
        templates = self.package / "templates"
        self.assertEqual({path.name for path in templates.glob("*.md")}, expected)
        registry = "pending / in_progress / completed / blocked"
        self.assertIn(registry, (templates / "task_plan.md").read_text())
        for path in templates.glob("*.md"):
            if path.name != "task_plan.md":
                self.assertNotIn(registry, path.read_text(), path.name)
        for legacy in ("acceptance_test.py", "test_context_capsule.py", "safe-push.sh"):
            self.assertFalse((self.package / "scripts" / legacy).exists(), legacy)


if __name__ == "__main__":
    unittest.main()
