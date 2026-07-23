from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
EXPECTED_REFERENCES = {
    "understand-goal.md",
    "decide-solution.md",
    "plan-tasks.md",
    "execute-tasks.md",
    "verify-deliver.md",
    "learn-review.md",
    "evolve-system.md",
    "challenge-decisions.md",
    "shape-experience.md",
    "maintain-design.md",
    "coordinate-agents.md",
    "merge-parallel-work.md",
    "fix-failures.md",
    "handoff-context.md",
}
LEGACY_STAGES = (
    "看清目标",
    "Intake",
    "Clarify",
    "Readiness",
    "Solution",
    "Strategic Planning",
    "Experience",
    "Write",
    "Write Plan",
    "Act",
    "Act Plan",
    "Debug",
    "Verify",
    "Finish",
)


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

    def test_repository_ignores_generated_python_and_desktop_cache(self) -> None:
        ignore = (self.package / ".gitignore").read_text()
        for generated in ("__pycache__/", "*.py[cod]", ".DS_Store"):
            self.assertIn(generated, ignore)
        result = self.run_doctor()
        self.assertEqual(result.returncode, 0, result.stdout)

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

    def test_every_legacy_stage_word_fails_closed_in_formal_source(self) -> None:
        skill = self.package / "SKILL.md"
        original = skill.read_text()
        for legacy in LEGACY_STAGES:
            with self.subTest(legacy=legacy):
                skill.write_text(original + f"\n{legacy}\n")
                result = self.run_doctor()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("legacy stage words escaped read-boundary compatibility", result.stdout)
        skill.write_text(original)

    def test_broken_reference_link_fails_closed(self) -> None:
        reference = self.package / "references/understand-goal.md"
        reference.write_text(reference.read_text() + "\nreferences/missing.md\n")
        result = self.run_doctor()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("broken reference link", result.stdout)

    def test_reference_to_reference_deep_link_fails_closed(self) -> None:
        reference = self.package / "references/understand-goal.md"
        reference.write_text(reference.read_text() + "\nreferences/verify-deliver.md\n")
        result = self.run_doctor()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reference-to-reference deep link", result.stdout)

    def test_unowned_file_fails_closed(self) -> None:
        (self.package / "notes.md").write_text("orphan")
        result = self.run_doctor()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not owned by the public target manifest", result.stdout)

    def test_duplicate_protocol_owner_fails_closed(self) -> None:
        reference = self.package / "references/understand-goal.md"
        reference.write_text(reference.read_text() + "\n# 修复失败\n")
        result = self.run_doctor()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("protocol `# 修复失败", result.stdout)

    def test_reference_registry_has_seven_owners_and_seven_harnesses(self) -> None:
        references = self.package / "references"
        self.assertEqual({path.name for path in references.glob("*.md")}, EXPECTED_REFERENCES)
        skill = (self.package / "SKILL.md").read_text()
        self.assertEqual(skill.count("| 主 owner |"), 7)
        self.assertEqual(skill.count("| harness |"), 7)

    def test_templates_have_one_status_owner_and_no_duplicate_legacy_tools(self) -> None:
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
