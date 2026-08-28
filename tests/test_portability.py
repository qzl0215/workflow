from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


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
    "install",
    "json",
    "os",
    "pathlib",
    "plistlib",
    "platform",
    "re",
    "shlex",
    "shutil",
    "stat",
    "subprocess",
    "sys",
    "tempfile",
    "time",
    "typing",
    "unittest",
    "urllib",
    "workflow_doctor",
    "zipfile",
}


def load_installer_module():
    script = PACKAGE / "scripts/install.py"
    scripts = str(script.parent)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location("workflow_install_for_test", script)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load workflow installer")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


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

    def test_work_context_works_without_git_browser_memory_or_subagents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task = Path(temp) / "project/plans/demo"
            task.mkdir(parents=True)
            (task / "work.md").write_text(
                """# 工作真源

## 当前状态
- 状态：active
- 当前动作：任务执行

## 目标契约
- 目标：完成可验证的结果

## 结果计划
### P01｜结果
#### P01-T01｜任务
- 任务状态：active
- 验收：返回有界上下文
"""
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(PACKAGE / "scripts/work_context.py"),
                    "--task-dir",
                    str(task),
                    "--plan",
                    "P01",
                    "--task",
                    "P01-T01",
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
            self.assertEqual(payload["source"], "work.md")
            self.assertEqual(payload["status"], "active")
            self.assertEqual(payload["action_hint"], "任务执行")

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
            frame = target / "workflow/references/frame.md"
            frame.write_text(
                frame.read_text(encoding="utf-8") + "\n<!-- local drift -->\n",
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
            self.assertEqual(frame.read_bytes(), (PACKAGE / "references/frame.md").read_bytes())
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

    def test_bridge_keeps_legacy_payload_and_rejects_unsafe_runtime_manifests(self) -> None:
        installer = load_installer_module()
        manifest = json.loads((PACKAGE / "workflow-package.json").read_text(encoding="utf-8"))
        expected_runtime = frozenset(manifest["runtime"]["files"]) | {"workflow-package.json"}
        self.assertEqual(installer.payload_targets(PACKAGE), expected_runtime)
        legacy_paths = "\n".join(sorted(installer.PUBLIC_TARGETS)).encode()
        self.assertEqual(len(installer.PUBLIC_TARGETS), 45)
        self.assertEqual(
            hashlib.sha256(legacy_paths).hexdigest(),
            "a8dfe36194565a120bf23489a41fed06345769dd737ad648dc42d01d3c8b8855",
        )
        for unsafe in ("references/x.md:stream", "CON.md", "references/name. "):
            with self.subTest(unsafe=unsafe):
                with self.assertRaisesRegex(ValueError, "不安全路径"):
                    installer.normalize_manifest_path(unsafe)
                with self.assertRaisesRegex(ValueError, "不安全路径"):
                    installer.normalized_archive_parts(zipfile.ZipInfo(unsafe))

        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "runtime"
            (package / "scripts").mkdir(parents=True)
            (package / "SKILL.md").write_text(
                "---\nname: workflow\nversion: 3.0.0\n---\n",
                encoding="utf-8",
            )
            shutil.copy2(PACKAGE / "scripts/install.py", package / "scripts/install.py")
            (package / "scripts/workflow_doctor.py").write_text(
                "PUBLIC_TARGETS = set()\n",
                encoding="utf-8",
            )
            manifest = package / "workflow-package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "name": "workflow",
                        "version": "3.0.0",
                        "entrypoint": "SKILL.md",
                        "runtime": {
                            "files": {
                                "../escape": "sha256:" + ("0" * 64),
                                "SKILL.md": "sha256:" + ("0" * 64),
                                "scripts/install.py": "sha256:" + ("0" * 64),
                                "scripts/workflow_doctor.py": "sha256:" + ("0" * 64),
                            }
                        },
                        "source_only": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "路径"):
                installer.payload_targets(package)

            manifest.write_text(
                '{"schema":1,"schema":1,"name":"workflow",'
                '"version":"3.0.0","entrypoint":"SKILL.md",'
                '"runtime":{"files":{}},"source_only":[]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "重复字段"):
                installer.payload_targets(package)

            valid_paths = {
                "SKILL.md",
                "scripts/install.py",
                "scripts/workflow_doctor.py",
            }
            manifest.write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "name": "workflow",
                        "version": "3.0.0",
                        "entrypoint": "SKILL.md",
                        "runtime": {
                            "files": {
                                relative: "sha256:" + ("0" * 64)
                                for relative in sorted(valid_paths)
                            }
                        },
                        "source_only": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                installer.payload_targets(package)

            manifest.write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "name": "workflow",
                        "version": "3.0.0",
                        "entrypoint": "SKILL.md",
                        "runtime": {
                            "files": {
                                **{
                                    relative: "sha256:" + ("0" * 64)
                                    for relative in sorted(valid_paths)
                                },
                                "A.md": "sha256:" + ("0" * 64),
                                "a.md": "sha256:" + ("0" * 64),
                            }
                        },
                        "source_only": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "大小写冲突"):
                installer.payload_targets(package)

            invalid_schema = {
                "schema": True,
                "name": "workflow",
                "version": "3.0.0",
                "entrypoint": "SKILL.md",
                "runtime": {
                    "files": {
                        relative: "sha256:"
                        + hashlib.sha256((package / relative).read_bytes()).hexdigest()
                        for relative in sorted(valid_paths)
                    }
                },
                "source_only": [],
            }
            manifest.write_text(json.dumps(invalid_schema), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "schema"):
                installer.payload_targets(package)

            with mock.patch.object(Path, "stat", side_effect=OSError("denied")):
                with self.assertRaisesRegex(ValueError, "无法读取"):
                    installer.read_runtime_manifest(manifest)

    def test_bridge_installs_exact_slim_runtime_and_checks_it_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Agent Skills"
            legacy_source = self.synthetic_legacy_bridge(root)
            source_script = legacy_source / "scripts/install.py"
            installed = subprocess.run(
                [sys.executable, "-B", str(source_script), "install", "--target", str(target)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(installed.returncode, 0, installed.stdout)
            self.assertIn("version: 2.26.0", (target / "workflow/SKILL.md").read_text())
            before = {
                path.relative_to(target / "workflow").as_posix(): path.read_bytes()
                for path in (target / "workflow").rglob("*")
                if path.is_file()
            }

            runtime = root / "runtime"
            (runtime / "scripts").mkdir(parents=True)
            (runtime / "references").mkdir()
            (runtime / "SKILL.md").write_text(
                "---\nname: workflow\nversion: 3.0.0\n---\n# workflow\n",
                encoding="utf-8",
            )
            shutil.copy2(PACKAGE / "scripts/install.py", runtime / "scripts/install.py")
            (runtime / "scripts/workflow_doctor.py").write_text(
                "from pathlib import Path\n"
                "if __name__ == '__main__':\n"
                "    Path('unexpected').mkdir(exist_ok=True)\n"
                "    print('runtime_doctor: MUTATED')\n",
                encoding="utf-8",
            )
            (runtime / "references/frame.md").write_text("# 目标框定\n", encoding="utf-8")
            runtime_files = {
                "SKILL.md",
                "references/frame.md",
                "scripts/install.py",
                "scripts/workflow_doctor.py",
            }
            def write_runtime_manifest() -> None:
                runtime_hashes = {
                    relative: "sha256:"
                    + hashlib.sha256((runtime / relative).read_bytes()).hexdigest()
                    for relative in sorted(runtime_files)
                }
                (runtime / "workflow-package.json").write_text(
                    json.dumps(
                        {
                            "schema": 1,
                            "name": "workflow",
                            "version": "3.0.0",
                            "entrypoint": "SKILL.md",
                            "runtime": {"files": runtime_hashes},
                            "source_only": [],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

            write_runtime_manifest()
            files = runtime_files | {"workflow-package.json"}
            release = self.local_release_for_package(root, runtime, tag="3.0.0")
            bridge = target / "workflow/scripts/install.py"
            rejected = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(bridge),
                    "sync",
                    "--target",
                    str(target),
                    "--release-api",
                    release.as_uri(),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
            after_rejection = {
                path.relative_to(target / "workflow").as_posix(): path.read_bytes()
                for path in (target / "workflow").rglob("*")
                if path.is_file()
            }
            self.assertEqual(after_rejection, before)
            self.assertEqual([path.name for path in target.iterdir()], ["workflow"])

            (runtime / "scripts/workflow_doctor.py").write_text(
                "if __name__ == '__main__':\n"
                "    print('runtime_doctor: OK')\n",
                encoding="utf-8",
            )
            write_runtime_manifest()
            release = self.local_release_for_package(root, runtime, tag="3.0.0")
            synced = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(bridge),
                    "sync",
                    "--target",
                    str(target),
                    "--release-api",
                    release.as_uri(),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(synced.returncode, 0, synced.stdout)
            self.assertEqual(synced.stdout.count("runtime_doctor: OK"), 1, synced.stdout)
            actual = {
                path.relative_to(target / "workflow").as_posix()
                for path in (target / "workflow").rglob("*")
                if path.is_file()
            }
            self.assertEqual(actual, files)

            checked = subprocess.run(
                [sys.executable, "-B", str(bridge), "check", "--target", str(target)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout)

            (target / "workflow/workflow-package.json").unlink()
            missing_manifest = subprocess.run(
                [sys.executable, "-B", str(bridge), "check", "--target", str(target)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertNotEqual(missing_manifest.returncode, 0, missing_manifest.stdout)
            self.assertIn("workflow 3.x+ 必须包含普通 workflow-package.json", missing_manifest.stdout)
            remaining = {
                path.relative_to(target / "workflow").as_posix()
                for path in (target / "workflow").rglob("*")
                if path.is_file()
            }
            self.assertEqual(remaining, files - {"workflow-package.json"})

    def test_bridge_allows_declared_source_only_files_but_never_installs_them(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            (source / "scripts").mkdir(parents=True)
            (source / "tests").mkdir()
            (source / "SKILL.md").write_text(
                "---\nname: workflow\nversion: 3.0.0\n---\n# workflow\n",
                encoding="utf-8",
            )
            shutil.copy2(PACKAGE / "scripts/install.py", source / "scripts/install.py")
            (source / "scripts/workflow_doctor.py").write_text(
                "if __name__ == '__main__':\n    print('runtime_doctor: OK')\n",
                encoding="utf-8",
            )
            (source / "tests/test_source_only.py").write_text("# source only\n", encoding="utf-8")
            runtime_files = {
                "SKILL.md",
                "scripts/install.py",
                "scripts/workflow_doctor.py",
            }
            hashes = {
                relative: "sha256:" + hashlib.sha256((source / relative).read_bytes()).hexdigest()
                for relative in sorted(runtime_files)
            }
            (source / "workflow-package.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "name": "workflow",
                        "version": "3.0.0",
                        "entrypoint": "SKILL.md",
                        "runtime": {"files": hashes},
                        "source_only": ["tests/test_source_only.py"],
                    }
                ),
                encoding="utf-8",
            )

            targets = installer.payload_targets(source)
            self.assertNotIn("tests/test_source_only.py", targets)
            parent = root / "Agent Skills"
            self.assertEqual(installer.install(parent, update=False, source_root=source), 0)
            self.assertFalse((parent / "workflow/tests/test_source_only.py").exists())
            checked = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(parent / "workflow/scripts/install.py"),
                    "check",
                    "--target",
                    str(parent),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout)

            if sys.platform != "win32":
                linked_parent = root / "Linked Agent Skills"
                linked_parent.mkdir()
                (linked_parent / "workflow").symlink_to(source, target_is_directory=True)
                linked = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(source / "scripts/install.py"),
                        "update",
                        "--target",
                        str(linked_parent),
                    ],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
                self.assertEqual(linked.returncode, 0, linked.stdout)
                self.assertTrue((linked_parent / "workflow").is_symlink())

    def test_release_extractor_rejects_duplicate_and_non_regular_members(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            duplicate = root / "duplicate.zip"
            with zipfile.ZipFile(duplicate, "w") as archive:
                archive.writestr("SKILL.md", "first")
                with self.assertWarns(UserWarning):
                    archive.writestr("SKILL.md", "second")
            with self.assertRaisesRegex(ValueError, "重复"):
                installer.extract_release(duplicate, root / "duplicate-out")

            symlink = root / "symlink.zip"
            with zipfile.ZipFile(symlink, "w") as archive:
                archive.writestr("SKILL.md", "entry")
                info = zipfile.ZipInfo("references/link.md")
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, "../SKILL.md")
            with self.assertRaisesRegex(ValueError, "普通文件"):
                installer.extract_release(symlink, root / "symlink-out")

            traversal = root / "traversal.zip"
            with zipfile.ZipFile(traversal, "w") as archive:
                archive.writestr("SKILL.md", "entry")
                archive.writestr("../escape", "outside")
            traversal_out = root / "traversal-out"
            with self.assertRaisesRegex(ValueError, "不安全路径"):
                installer.extract_release(traversal, traversal_out)
            self.assertFalse(traversal_out.exists())
            self.assertFalse((root / "escape").exists())

    def test_runtime_tree_rejects_extra_directories_and_symlinks(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "runtime"
            root.mkdir()
            (root / "SKILL.md").write_text("entry\n", encoding="utf-8")
            (root / "unexpected").mkdir()
            errors = installer.runtime_tree_errors(root, frozenset({"SKILL.md"}))
            self.assertTrue(any("未声明目录" in error for error in errors), errors)
            (root / "unexpected").rmdir()
            try:
                (root / "runtime-link").symlink_to(Path(temp), target_is_directory=True)
            except OSError:
                return
            errors = installer.runtime_tree_errors(root, frozenset({"SKILL.md"}))
            self.assertTrue(any("符号链接" in error for error in errors), errors)
            (root / "runtime-link").unlink()
            (root / "__pycache__").mkdir()
            try:
                (root / "__pycache__/escape").symlink_to(Path(temp), target_is_directory=True)
            except OSError:
                return
            errors = installer.runtime_tree_errors(root, frozenset({"SKILL.md"}))
            self.assertTrue(any("符号链接" in error for error in errors), errors)

    def test_atomic_activation_restores_previous_install_after_post_swap_failure(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "Agent Skills"
            destination = parent / "workflow"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("old\n", encoding="utf-8")
            source = Path(temp) / "candidate"
            source.mkdir()
            (source / "SKILL.md").write_text("new\n", encoding="utf-8")
            stage = Path(tempfile.mkdtemp(prefix=".workflow-stage-", dir=parent))
            (stage / "SKILL.md").write_text("new\n", encoding="utf-8")

            with mock.patch.object(installer, "verify_activated_install", return_value=2):
                result = installer.activate_stage(
                    parent,
                    stage,
                    update=True,
                    source_root=source,
                    targets=frozenset({"SKILL.md"}),
                )

            self.assertEqual(result, 2)
            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "old\n")
            self.assertEqual(
                [path.name for path in parent.iterdir() if path.name != "workflow"],
                [],
            )

    def test_atomic_activation_never_restores_a_partially_deleted_backup(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "Agent Skills"
            destination = parent / "workflow"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("old\n", encoding="utf-8")
            source = Path(temp) / "candidate"
            source.mkdir()
            (source / "SKILL.md").write_text("new\n", encoding="utf-8")
            stage = Path(tempfile.mkdtemp(prefix=".workflow-stage-", dir=parent))
            (stage / "SKILL.md").write_text("new\n", encoding="utf-8")
            original_rmtree = shutil.rmtree

            def fail_partial_backup_cleanup(path: Path, *args: object, **kwargs: object) -> None:
                candidate = Path(path)
                if candidate.name.startswith(".workflow-rollback-"):
                    (candidate / "workflow/SKILL.md").unlink()
                    raise OSError("simulated partial cleanup failure")
                original_rmtree(candidate, *args, **kwargs)

            with (
                mock.patch.object(installer, "verify_activated_install", return_value=0),
                mock.patch.object(installer.shutil, "rmtree", side_effect=fail_partial_backup_cleanup),
            ):
                result = installer.activate_stage(
                    parent,
                    stage,
                    update=True,
                    source_root=source,
                    targets=frozenset({"SKILL.md"}),
                )

            self.assertEqual(result, 2)
            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "new\n")
            rollback_roots = list(parent.glob(".workflow-rollback-*"))
            self.assertEqual(len(rollback_roots), 1)
            original_rmtree(rollback_roots[0])

    def test_atomic_activation_cleans_empty_transaction_when_first_rename_fails(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "Agent Skills"
            destination = parent / "workflow"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("old\n", encoding="utf-8")
            source = Path(temp) / "candidate"
            source.mkdir()
            (source / "SKILL.md").write_text("new\n", encoding="utf-8")
            stage = Path(tempfile.mkdtemp(prefix=".workflow-stage-", dir=parent))
            (stage / "SKILL.md").write_text("new\n", encoding="utf-8")

            with mock.patch.object(Path, "rename", side_effect=OSError("simulated rename failure")):
                result = installer.activate_stage(
                    parent,
                    stage,
                    update=True,
                    source_root=source,
                    targets=frozenset({"SKILL.md"}),
                )

            self.assertEqual(result, 2)
            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "old\n")
            self.assertEqual(list(parent.glob(".workflow-rollback-*")), [])

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

    def synthetic_legacy_bridge(self, root: Path) -> Path:
        """Build the frozen 2.26 projection around the real bridge installer."""

        installer = load_installer_module()
        source = root / "legacy-2.26"
        for relative in sorted(installer.PUBLIC_TARGETS):
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if relative == "SKILL.md":
                path.write_text(
                    "---\nname: workflow\nversion: 2.26.0\n---\n# legacy bridge\n",
                    encoding="utf-8",
                )
            elif relative == "scripts/install.py":
                shutil.copy2(PACKAGE / relative, path)
            elif relative == "scripts/release_check.py":
                path.write_text(
                    "if __name__ == '__main__':\n    print('legacy_release_check: OK')\n",
                    encoding="utf-8",
                )
            else:
                path.write_text(f"# legacy fixture: {relative}\n", encoding="utf-8")
        return source

    def local_latest_release(
        self,
        root: Path,
        *,
        digest: str | None = None,
        immutable: bool = True,
        tag: str | None = None,
    ) -> Path:
        asset = root / "workflow.zip"
        package_manifest = json.loads(
            (PACKAGE / "workflow-package.json").read_text(encoding="utf-8")
        )
        runtime_paths = sorted(
            {*package_manifest["runtime"]["files"], "workflow-package.json"}
        )
        with zipfile.ZipFile(asset, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative in runtime_paths:
                archive.write(PACKAGE / relative, relative)
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

    def local_release_for_package(self, root: Path, package: Path, *, tag: str) -> Path:
        asset = root / f"workflow-{tag}.zip"
        with zipfile.ZipFile(asset, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(package.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(package).as_posix())
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        release = root / f"latest-{tag}.json"
        release.write_text(
            json.dumps(
                {
                    "tag_name": tag,
                    "draft": False,
                    "prerelease": False,
                    "immutable": True,
                    "assets": [
                        {
                            "name": "workflow.zip",
                            "browser_download_url": asset.as_uri(),
                            "digest": f"sha256:{digest}",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return release


if __name__ == "__main__":
    unittest.main()
