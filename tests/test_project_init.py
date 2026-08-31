from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "scripts/project_init.py"
STATE = Path(".workflow/project.json")


class ProjectInitializationTest(unittest.TestCase):
    def run_tool(self, project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *arguments, "--project", str(project)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def project(self, root: Path) -> Path:
        project = root / "project"
        project.mkdir()
        (project / "AGENTS.md").write_text("# AI entry\n", encoding="utf-8")
        return project

    def test_missing_state_requests_initialization_without_scanning_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(Path(temp))
            (project / "large-unrelated-file.bin").write_bytes(b"x" * 1024)
            result = self.run_tool(project, "check")
            self.assertEqual(result.returncode, 10, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "needs-initialization")
            self.assertEqual(payload["read_scope"], [".workflow/project.json"])

    def test_recorded_generation_short_circuits_even_when_workflow_patch_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(Path(temp))
            evidence = project / "plans/init/work.md"
            evidence.parent.mkdir(parents=True)
            evidence.write_text("# accepted evidence\n", encoding="utf-8")
            recorded = self.run_tool(
                project,
                "record",
                "--entrypoint",
                "AGENTS.md",
                "--evidence",
                "plans/init/work.md",
            )
            self.assertEqual(recorded.returncode, 0, recorded.stdout)
            state = json.loads((project / STATE).read_text(encoding="utf-8"))
            self.assertEqual(state["reviewed_with"], "3.6.0")
            state["reviewed_with"] = "3.6.1"
            (project / STATE).write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            checked = self.run_tool(project, "check")
            self.assertEqual(checked.returncode, 0, checked.stdout)
            payload = json.loads(checked.stdout)
            self.assertEqual(payload["status"], "current")
            self.assertEqual(
                payload["read_scope"],
                [".workflow/project.json", "AGENTS.md", "plans/init/work.md"],
            )

    def test_old_generation_and_missing_owner_require_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(Path(temp))
            state_path = project / STATE
            state_path.parent.mkdir()
            state_path.write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "compatibility_generation": 0,
                        "reviewed_with": "3.0.0",
                        "entrypoint": "AGENTS.md",
                        "evidence": "AGENTS.md",
                    }
                ),
                encoding="utf-8",
            )
            old = self.run_tool(project, "check")
            self.assertEqual(old.returncode, 10, old.stdout)
            self.assertEqual(json.loads(old.stdout)["status"], "needs-upgrade")

            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["compatibility_generation"] = 1
            state["entrypoint"] = "missing.md"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            missing = self.run_tool(project, "check")
            self.assertEqual(missing.returncode, 10, missing.stdout)
            self.assertEqual(json.loads(missing.stdout)["status"], "needs-review")

    def test_inventory_is_bounded_and_surfaces_ai_project_owners(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(Path(temp))
            for relative in (
                "TRUTH.md",
                "README.md",
                "package.json",
                ".github/workflows/ci.yml",
                "tests/test_smoke.py",
                "prompts/system.md",
                "evals/cases.json",
                "deploy/release.sh",
                "plans/index.md",
            ):
                path = project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}\n" if path.suffix == ".json" else "x\n", encoding="utf-8")
            ignored = project / "node_modules/noise/deep/file.js"
            ignored.parent.mkdir(parents=True)
            ignored.write_text("noise\n", encoding="utf-8")

            result = self.run_tool(project, "inventory")
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertIn("AGENTS.md", payload["instructions"])
            self.assertIn("TRUTH.md", payload["truth_candidates"])
            self.assertIn("tests/test_smoke.py", payload["validation_candidates"])
            self.assertIn("prompts/system.md", payload["ai_candidates"])
            self.assertIn("evals/cases.json", payload["ai_candidates"])
            self.assertIn("deploy/release.sh", payload["delivery_candidates"])
            self.assertNotIn("node_modules/noise/deep/file.js", json.dumps(payload))

    def test_record_rejects_absolute_or_missing_project_owners(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(Path(temp))
            absolute = self.run_tool(project, "record", "--entrypoint", str(project / "AGENTS.md"))
            self.assertEqual(absolute.returncode, 2, absolute.stdout)
            missing = self.run_tool(project, "record", "--entrypoint", "missing.md")
            self.assertEqual(missing.returncode, 2, missing.stdout)
            self.assertFalse((project / STATE).exists())

    def test_state_symlink_fails_closed_without_writing_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = self.project(root)
            outside = root / "outside"
            outside.mkdir()
            (project / ".workflow").symlink_to(outside, target_is_directory=True)

            checked = self.run_tool(project, "check")
            self.assertEqual(checked.returncode, 2, checked.stdout)
            self.assertEqual(json.loads(checked.stdout)["status"], "invalid")
            recorded = self.run_tool(
                project,
                "record",
                "--entrypoint",
                "AGENTS.md",
                "--evidence",
                "AGENTS.md",
            )
            self.assertEqual(recorded.returncode, 2, recorded.stdout)
            self.assertFalse((outside / "project.json").exists())


if __name__ == "__main__":
    unittest.main()
