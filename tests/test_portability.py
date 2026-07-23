from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
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
    "http",
    "importlib",
    "json",
    "os",
    "pathlib",
    "plistlib",
    "platform",
    "re",
    "shlex",
    "shutil",
    "subprocess",
    "sys",
    "tempfile",
    "typing",
    "unittest",
    "urllib",
    "workflow_doctor",
    "zipfile",
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

    def test_public_docs_define_single_latest_release_update_contract(self) -> None:
        readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
        for token in (
            "GitHub 最新正式、immutable Release",
            "enable-auto-update",
            "每 24 小时",
            "workflow.zip",
            "SHA-256",
            "不保留 backup、failed 或 removed 副本",
        ):
            self.assertIn(token, readme)
        security = (PACKAGE / "SECURITY.md").read_text(encoding="utf-8")
        for token in ("single active package", "immutable GitHub Release", "SHA-256"):
            self.assertIn(token, security)

    def test_installer_install_check_update_and_uninstall_leave_one_or_zero_copies(self) -> None:
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
            self.assertEqual(sorted(path.name for path in target.iterdir()), ["workflow"])
            result = run("uninstall", "--yes")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(list(target.iterdir()), [])

    def test_installer_check_rejects_a_second_discoverable_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Agent Skills"
            script = PACKAGE / "scripts/install.py"
            installed = subprocess.run(
                [sys.executable, "-B", str(script), "install", "--target", str(target)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(installed.returncode, 0, installed.stdout)
            duplicate = target / "workflow-copy"
            duplicate.mkdir()
            (duplicate / "SKILL.md").write_text(
                "---\nname: workflow\nversion: duplicate\n---\n",
                encoding="utf-8",
            )

            checked = subprocess.run(
                [sys.executable, "-B", str(script), "check", "--target", str(target)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            self.assertNotEqual(checked.returncode, 0, checked.stdout)
            self.assertIn("多个 workflow", checked.stdout)

    def test_installer_sync_replaces_stale_copy_from_verified_latest_release(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Agent Skills"
            script = PACKAGE / "scripts/install.py"

            installed = subprocess.run(
                [sys.executable, "-B", str(script), "install", "--target", str(target)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(installed.returncode, 0, installed.stdout)
            skill = target / "workflow/SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace(
                    self.package_version(),
                    "0.0.0-test",
                    1,
                ),
                encoding="utf-8",
            )
            manifest = self.local_latest_release(root)

            synced = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(script),
                    "sync",
                    "--target",
                    str(target),
                    "--release-api",
                    manifest.as_uri(),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            self.assertEqual(synced.returncode, 0, synced.stdout)
            self.assertIn(f"version: {self.package_version()}", skill.read_text(encoding="utf-8"))
            self.assertEqual(sorted(path.name for path in target.iterdir()), ["workflow"])

    def test_installer_sync_digest_failure_keeps_current_copy_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Agent Skills"
            script = PACKAGE / "scripts/install.py"
            installed = subprocess.run(
                [sys.executable, "-B", str(script), "install", "--target", str(target)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(installed.returncode, 0, installed.stdout)
            skill = target / "workflow/SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace(
                    self.package_version(),
                    "0.0.0-test",
                    1,
                ),
                encoding="utf-8",
            )
            before = skill.read_bytes()
            manifest = self.local_latest_release(root, digest="sha256:" + ("0" * 64))

            synced = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(script),
                    "sync",
                    "--target",
                    str(target),
                    "--release-api",
                    manifest.as_uri(),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            self.assertNotEqual(synced.returncode, 0, synced.stdout)
            self.assertIn("SHA-256", synced.stdout)
            self.assertEqual(skill.read_bytes(), before)
            self.assertEqual(sorted(path.name for path in target.iterdir()), ["workflow"])

    def test_installer_sync_repairs_same_version_payload_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Agent Skills"
            script = PACKAGE / "scripts/install.py"
            installed = subprocess.run(
                [sys.executable, "-B", str(script), "install", "--target", str(target)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(installed.returncode, 0, installed.stdout)
            readme = target / "workflow/README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8") + "\n<!-- local drift -->\n",
                encoding="utf-8",
            )
            manifest = self.local_latest_release(root)

            synced = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(script),
                    "sync",
                    "--target",
                    str(target),
                    "--release-api",
                    manifest.as_uri(),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            self.assertEqual(synced.returncode, 0, synced.stdout)
            self.assertEqual(readme.read_bytes(), (PACKAGE / "README.md").read_bytes())
            self.assertEqual(sorted(path.name for path in target.iterdir()), ["workflow"])

    def test_installer_sync_rejects_untrusted_release_metadata_without_replacement(self) -> None:
        cases = (
            ("mutable", {"immutable": False}, "immutable"),
            ("version-mismatch", {"tag": "9.9.9"}, "包版本不一致"),
        )
        for label, options, expected in cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                target = root / "Agent Skills"
                script = PACKAGE / "scripts/install.py"
                installed = subprocess.run(
                    [sys.executable, "-B", str(script), "install", "--target", str(target)],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
                self.assertEqual(installed.returncode, 0, installed.stdout)
                skill = target / "workflow/SKILL.md"
                before = skill.read_bytes()
                manifest = self.local_latest_release(root, **options)

                synced = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(script),
                        "sync",
                        "--target",
                        str(target),
                        "--release-api",
                        manifest.as_uri(),
                    ],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                )

                self.assertNotEqual(synced.returncode, 0, synced.stdout)
                self.assertIn(expected, synced.stdout)
                self.assertEqual(skill.read_bytes(), before)
                self.assertEqual(sorted(path.name for path in target.iterdir()), ["workflow"])

    def test_auto_update_schedule_dry_run_covers_supported_platforms_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Agent Skills"
            fake_home = root / "home"
            fake_home.mkdir()
            script = PACKAGE / "scripts/install.py"
            environment = {**os.environ, "HOME": str(fake_home)}
            installed = subprocess.run(
                [sys.executable, "-B", str(script), "install", "--target", str(target)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                env=environment,
            )
            self.assertEqual(installed.returncode, 0, installed.stdout)

            expectations = {
                "darwin": ("RunAtLoad", "86400"),
                "linux": ("OnBootSec=2min", "OnUnitActiveSec=1d"),
                "win32": ("Workflow Sync Daily", "Workflow Sync Logon"),
            }
            for platform_name, tokens in expectations.items():
                with self.subTest(platform=platform_name):
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(script),
                            "enable-auto-update",
                            "--target",
                            str(target),
                            "--dry-run",
                            "--scheduler-platform",
                            platform_name,
                        ],
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        check=False,
                        env=environment,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout)
                    for token in tokens:
                        self.assertIn(token, result.stdout)
            self.assertEqual(list(fake_home.iterdir()), [])

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

    def package_version(self) -> str:
        for line in (PACKAGE / "SKILL.md").read_text(encoding="utf-8").splitlines():
            if line.startswith("version:"):
                return line.split(":", 1)[1].strip()
        self.fail("package version missing")

    def local_latest_release(
        self,
        root: Path,
        *,
        digest: str | None = None,
        immutable: bool = True,
        tag: str | None = None,
    ) -> Path:
        asset = root / "workflow.zip"
        with zipfile.ZipFile(asset, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(PACKAGE.rglob("*")):
                if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                    continue
                archive.write(path, path.relative_to(PACKAGE).as_posix())
        actual_digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        manifest = root / "latest.json"
        manifest.write_text(
            json.dumps(
                {
                    "tag_name": tag or self.package_version(),
                    "draft": False,
                    "prerelease": False,
                    "immutable": immutable,
                    "assets": [
                        {
                            "name": "workflow.zip",
                            "browser_download_url": asset.as_uri(),
                            "digest": digest or f"sha256:{actual_digest}",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return manifest


if __name__ == "__main__":
    unittest.main()
