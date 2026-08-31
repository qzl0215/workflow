from __future__ import annotations

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
MANIFEST = "workflow-package.json"
REFERENCES = {
    "frame.md",
    "research.md",
    "experience.md",
    "grill.md",
    "plan.md",
    "orchestrate.md",
    "execute.md",
    "recover.md",
    "prove.md",
    "deliver.md",
    "learn.md",
}
RUNTIME_FILES = {
    "SKILL.md",
    "LICENSE",
    "NOTICE.md",
    *(f"references/{name}" for name in REFERENCES),
    "templates/work.md",
    "scripts/install.py",
    "scripts/safe_merge.py",
    "scripts/work_context.py",
    "scripts/workflow_doctor.py",
}
SOURCE_ONLY_FILES = {
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "docs/workflow-visual-map.html",
    "scripts/generate_visual_map.py",
    "scripts/release_check.py",
    "tests/test_portability.py",
    "tests/test_protocol_v3.py",
    "tests/test_release_v3.py",
    "tests/test_safe_merge.py",
    "tests/test_work_context.py",
}


def run(*parts: str, cwd: Path, check: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(parts),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if check and result.returncode:
        raise AssertionError(f"command failed ({result.returncode}): {' '.join(parts)}\n{result.stdout}")
    return result


def copy_source(destination: Path) -> None:
    shutil.copytree(
        PACKAGE,
        destination,
        ignore=shutil.ignore_patterns(".git", ".DS_Store", "__pycache__", "*.pyc", ".pytest_cache"),
    )


def manifest(path: Path) -> dict[str, object]:
    return json.loads((path / MANIFEST).read_text(encoding="utf-8"))


def write_manifest(path: Path, value: dict[str, object]) -> None:
    (path / MANIFEST).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def refresh_hash(path: Path, relative: str) -> None:
    value = manifest(path)
    files = value["runtime"]["files"]
    files[relative] = "sha256:" + hashlib.sha256((path / relative).read_bytes()).hexdigest()
    write_manifest(path, value)


def copy_runtime(destination: Path) -> None:
    value = manifest(PACKAGE)
    files = set(value["runtime"]["files"]) | {MANIFEST}
    destination.mkdir(parents=True)
    for relative in files:
        source = PACKAGE / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def doctor(package: Path) -> subprocess.CompletedProcess[str]:
    return run(sys.executable, "-B", str(package / "scripts/workflow_doctor.py"), cwd=package)


class WorkflowV3ReleaseContractTest(unittest.TestCase):
    def test_manifest_is_exact_and_every_runtime_hash_matches(self) -> None:
        value = manifest(PACKAGE)
        self.assertEqual(set(value), {"schema", "name", "version", "entrypoint", "runtime", "source_only"})
        self.assertEqual(value["schema"], 1)
        self.assertEqual(value["name"], "workflow")
        self.assertEqual(value["version"], "3.4.0")
        self.assertEqual(value["entrypoint"], "SKILL.md")
        self.assertEqual(set(value["runtime"]), {"files"})
        files = value["runtime"]["files"]
        self.assertEqual(set(files), RUNTIME_FILES)
        self.assertEqual(set(value["source_only"]), SOURCE_ONLY_FILES)
        for relative, expected in files.items():
            actual = "sha256:" + hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()
            self.assertEqual(expected, actual, relative)

    def test_doctor_accepts_full_source_and_slim_runtime(self) -> None:
        source = doctor(PACKAGE)
        self.assertEqual(source.returncode, 0, source.stdout)
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / "workflow"
            copy_runtime(runtime)
            slim = doctor(runtime)
            self.assertEqual(slim.returncode, 0, slim.stdout)
            actual = {
                path.relative_to(runtime).as_posix()
                for path in runtime.rglob("*")
                if path.is_file()
            }
            self.assertEqual(actual, RUNTIME_FILES | {MANIFEST})
            help_result = run(
                sys.executable,
                "-B",
                str(runtime / "scripts/safe_merge.py"),
                "--help",
                cwd=runtime,
            )
            self.assertEqual(help_result.returncode, 0, help_result.stdout)
            self.assertIn("--sync-baseline", help_result.stdout)

    def test_doctor_fails_on_missing_extra_hash_and_partial_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            missing = root / "missing"
            copy_runtime(missing)
            (missing / "references/frame.md").unlink()
            result = doctor(missing)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("声明的文件不存在", result.stdout)

            extra = root / "extra"
            copy_runtime(extra)
            (extra / "surprise.txt").write_text("unexpected\n", encoding="utf-8")
            result = doctor(extra)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("未声明", result.stdout)

            changed = root / "changed"
            copy_runtime(changed)
            with (changed / "references/frame.md").open("a", encoding="utf-8") as output:
                output.write("\n变化\n")
            result = doctor(changed)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA-256 不匹配", result.stdout)

            partial = root / "partial"
            copy_source(partial)
            (partial / "README.md").unlink()
            result = doctor(partial)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("source_only 不完整", result.stdout)

    def test_doctor_fails_on_broken_link_conflict_marker_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            broken = root / "broken"
            copy_runtime(broken)
            with (broken / "references/frame.md").open("a", encoding="utf-8") as output:
                output.write("\n[断链](not-there.md)\n")
            refresh_hash(broken, "references/frame.md")
            result = doctor(broken)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("本地链接不存在", result.stdout)

            conflict = root / "conflict"
            copy_runtime(conflict)
            with (conflict / "references/frame.md").open("a", encoding="utf-8") as output:
                output.write("\n<<<<<<< ours\n=======\n>>>>>>> theirs\n")
            refresh_hash(conflict, "references/frame.md")
            result = doctor(conflict)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("冲突标记", result.stdout)

            credential = root / "credential"
            copy_runtime(credential)
            with (credential / "references/frame.md").open("a", encoding="utf-8") as output:
                output.write("\napi_key=definitely-not-safe\n")
            refresh_hash(credential, "references/frame.md")
            result = doctor(credential)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("疑似包含凭据", result.stdout)

            linked = root / "linked"
            copy_runtime(linked)
            (linked / "unsafe-link").symlink_to("SKILL.md")
            result = doctor(linked)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("符号链接", result.stdout)

    def test_write_manifest_repairs_hashes_without_blessing_extra_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            copy_source(source)
            value = manifest(source)
            value["runtime"]["files"]["SKILL.md"] = "sha256:" + ("0" * 64)
            write_manifest(source, value)
            result = run(
                sys.executable,
                "-B",
                str(source / "scripts/release_check.py"),
                "--write-manifest",
                cwd=source,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            repaired = manifest(source)["runtime"]["files"]["SKILL.md"]
            self.assertEqual(repaired, "sha256:" + hashlib.sha256((source / "SKILL.md").read_bytes()).hexdigest())

            (source / "unowned.txt").write_text("extra\n", encoding="utf-8")
            rejected = run(
                sys.executable,
                "-B",
                str(source / "scripts/release_check.py"),
                "--write-manifest",
                cwd=source,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("未声明", rejected.stdout)

    def test_runtime_asset_comes_only_from_an_immutable_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            copy_source(source)
            run("git", "init", cwd=source, check=True)
            run("git", "config", "user.name", "Workflow Test", cwd=source, check=True)
            run("git", "config", "user.email", "workflow@example.test", cwd=source, check=True)
            run("git", "add", ".", cwd=source, check=True)
            run("git", "commit", "-m", "release", cwd=source, check=True)
            commit = run("git", "rev-parse", "HEAD", cwd=source, check=True).stdout.strip()

            first = root / "workflow-a.zip"
            built = run(
                sys.executable,
                "-B",
                str(source / "scripts/release_check.py"),
                "--build-runtime",
                str(first),
                "--git-ref",
                commit,
                cwd=source,
            )
            self.assertEqual(built.returncode, 0, built.stdout)
            self.assertIn(f"commit={commit}", built.stdout)
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(set(archive.namelist()), RUNTIME_FILES | {MANIFEST})
                self.assertTrue(SOURCE_ONLY_FILES.isdisjoint(archive.namelist()))

            second = root / "workflow-b.zip"
            rebuilt = run(
                sys.executable,
                "-B",
                str(source / "scripts/release_check.py"),
                "--build-runtime",
                str(second),
                "--git-ref",
                commit,
                cwd=source,
            )
            self.assertEqual(rebuilt.returncode, 0, rebuilt.stdout)
            self.assertEqual(first.read_bytes(), second.read_bytes())

            mutable = root / "mutable.zip"
            rejected = run(
                sys.executable,
                "-B",
                str(source / "scripts/release_check.py"),
                "--build-runtime",
                str(mutable),
                "--git-ref",
                "HEAD",
                cwd=source,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("完整小写 commit SHA", rejected.stdout)
            self.assertFalse(mutable.exists())

    def test_default_release_gate_is_one_composite_entrypoint(self) -> None:
        result = run(sys.executable, "-B", str(PACKAGE / "scripts/release_check.py"), cwd=PACKAGE)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("workflow_release_check: OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
