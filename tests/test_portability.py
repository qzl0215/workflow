from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
STDLIB_OR_LOCAL = {
    "__future__",
    "argparse",
    "ast",
    "dataclasses",
    "datetime",
    "hashlib",
    "html",
    "importlib",
    "json",
    "os",
    "pathlib",
    "re",
    "shutil",
    "subprocess",
    "sys",
    "tempfile",
    "typing",
    "unittest",
    "workflow_doctor",
}


class PortabilityContractTest(unittest.TestCase):
    def test_python_scripts_use_only_standard_library_or_local_module(self) -> None:
        unexpected = set()
        for path in [*(PACKAGE / "scripts").glob("*.py"), *(PACKAGE / "tests").glob("*.py")]:
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    unexpected.update(alias.name.split(".")[0] for alias in node.names if alias.name.split(".")[0] not in STDLIB_OR_LOCAL)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    name = node.module.split(".")[0]
                    if name not in STDLIB_OR_LOCAL and node.level == 0:
                        unexpected.add(name)
        self.assertEqual(unexpected, set())

    def test_clean_room_copy_with_spaces_passes_static_gates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Empty Agent Skills/workflow"
            target.parent.mkdir(parents=True)
            shutil.copytree(PACKAGE, target, ignore=shutil.ignore_patterns(".git"))
            for script, args in (
                ("workflow_doctor.py", []),
                ("release_check.py", []),
                ("generate_visual_map.py", ["--check"]),
            ):
                result = subprocess.run(
                    [sys.executable, "-B", str(target / "scripts" / script), *args],
                    cwd=target,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout)

    def test_context_capsule_works_without_git_browser_memory_or_subagents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task = Path(temp) / "project/plans/demo"
            task.mkdir(parents=True)
            (task / "task_plan.md").write_text(
                """# Demo
### Current Snapshot
- 当前阶段：Act
## Plan
#### P01｜Result
- DONE: yes
#### P01-T01｜Task
- DONE: yes
"""
            )
            (task / "progress.md").write_text("# Progress\n## Handoff checkpoint\n- 下一步：验收交付\n")
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(PACKAGE / "scripts/build_context_capsule.py"),
                    "--task-dir",
                    str(task),
                    "--plan",
                    "P01",
                    "--task",
                    "P01-T01",
                    "--stage",
                    "Act Plan",
                    "--format",
                    "json",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["fail_closed"])
            self.assertEqual(payload["stage"], "执行任务")
            self.assertNotIn("Act Plan", result.stdout)

    def test_package_has_no_symlinks_or_shell_runtime(self) -> None:
        self.assertEqual([path for path in PACKAGE.rglob("*") if path.is_symlink()], [])
        self.assertEqual(list((PACKAGE / "scripts").glob("*.sh")), [])

    def test_installer_install_check_update_and_recoverable_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Agent Skills"
            script = PACKAGE / "scripts/install.py"

            def run(*args: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, "-B", str(script), *args, "--target", str(target)],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                )

            for action in ("install", "check", "update"):
                result = run(action)
                self.assertEqual(result.returncode, 0, result.stdout)
            backups = list(target.glob("workflow.backup-*"))
            self.assertEqual(len(backups), 1)
            result = run("uninstall", "--yes")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertFalse((target / "workflow").exists())
            self.assertEqual(len(list(target.glob("workflow.removed-*"))), 1)

    def test_installer_update_preserves_managed_symlink_and_fails_on_drift(self) -> None:
        if sys.platform == "win32":
            self.skipTest("Windows symlink creation requires environment-specific privileges")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Agent Skills"
            target.mkdir()
            managed_source = root / "managed-workflow"
            shutil.copytree(PACKAGE, managed_source, ignore=shutil.ignore_patterns(".git"))
            destination = target / "workflow"
            destination.symlink_to(managed_source, target_is_directory=True)
            script = PACKAGE / "scripts/install.py"

            def run_update() -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, "-B", str(script), "update", "--target", str(target)],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                )

            matching = run_update()
            self.assertEqual(matching.returncode, 0, matching.stdout)
            self.assertTrue(destination.is_symlink())
            self.assertEqual(destination.resolve(), managed_source.resolve())
            self.assertEqual(list(target.glob("workflow.backup-*")), [])

            skill = managed_source / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\n<!-- drift -->\n", encoding="utf-8")
            drifted = run_update()
            self.assertEqual(drifted.returncode, 2, drifted.stdout)
            self.assertIn("符号链接", drifted.stdout)
            self.assertTrue(destination.is_symlink())
            self.assertEqual(destination.resolve(), managed_source.resolve())
            self.assertEqual(list(target.glob("workflow.backup-*")), [])

    def test_installer_auto_detects_an_existing_agent_skills_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fake_home = Path(temp) / "home"
            target = fake_home / ".codex" / "skills"
            target.mkdir(parents=True)
            script = PACKAGE / "scripts/install.py"
            environment = {**os.environ, "HOME": str(fake_home)}
            environment.pop("AGENT_SKILLS_DIR", None)

            detect = subprocess.run(
                [sys.executable, "-B", str(script), "detect"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                env=environment,
            )
            self.assertEqual(detect.returncode, 0, detect.stdout)
            self.assertIn(str(target), detect.stdout)

            install = subprocess.run(
                [sys.executable, "-B", str(script), "install"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                env=environment,
            )
            self.assertEqual(install.returncode, 0, install.stdout)
            self.assertTrue((target / "workflow" / "SKILL.md").is_file())

    def test_installer_auto_detection_fails_closed_when_target_is_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fake_home = Path(temp) / "home"
            for relative in (".codex/skills", ".claude/skills"):
                (fake_home / relative).mkdir(parents=True)
            script = PACKAGE / "scripts/install.py"
            environment = {**os.environ, "HOME": str(fake_home)}
            environment.pop("AGENT_SKILLS_DIR", None)
            result = subprocess.run(
                [sys.executable, "-B", str(script), "install"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                env=environment,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("发现多个 skills 目录", result.stdout)
            self.assertIn("--target", result.stdout)

            environment["AGENT_SKILLS_DIR"] = str(fake_home / ".claude" / "skills")
            configured = subprocess.run(
                [sys.executable, "-B", str(script), "install"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                env=environment,
            )
            self.assertEqual(configured.returncode, 0, configured.stdout)
            self.assertTrue((fake_home / ".claude" / "skills" / "workflow" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
