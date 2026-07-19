from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]


class DocumentationContractTest(unittest.TestCase):
    def run_script(self, name: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(PACKAGE / "scripts" / name), *args],
            cwd=PACKAGE,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def test_visual_map_is_fresh(self) -> None:
        result = self.run_script("generate_visual_map.py", "--check")
        self.assertEqual(result.returncode, 0, result.stdout)
        source = (PACKAGE / "SKILL.md").read_text()
        digest = hashlib.sha256(source.encode()).hexdigest()[:12]
        generated = (PACKAGE / "docs/workflow-visual-map.html").read_text()
        self.assertIn(f"source sha256 {digest}", generated)

    def test_visual_map_contains_all_states_and_routes(self) -> None:
        source = (PACKAGE / "SKILL.md").read_text()
        generated = (PACKAGE / "docs/workflow-visual-map.html").read_text()
        states = re.findall(r"^\| (Intake|Clarify|Readiness|Solution|Experience|Write|Act|Debug|Verify|Finish) \|", source, re.M)
        routes = re.findall(r"`(references/[A-Za-z0-9_-]+\.md)`", source)
        self.assertEqual(len(states), 10)
        self.assertEqual(len(routes), 14)
        for token in [*states, *routes]:
            self.assertIn(token, generated)

    def test_visual_map_is_a_chinese_product_introduction(self) -> None:
        generated = (PACKAGE / "docs/workflow-visual-map.html").read_text()
        for token in (
            "复杂任务总导演",
            "复制给 Agent 安装",
            "三步开始",
            "什么时候用",
            "十阶段闭环",
            "按需能力库",
            "prefers-reduced-motion",
        ):
            self.assertIn(token, generated)
        self.assertIn('lang="zh-CN"', generated)
        self.assertIn('aria-live="polite"', generated)
        self.assertNotIn("<script src=", generated)
        self.assertNotIn("@import url", generated)

    def test_package_release_gate_passes(self) -> None:
        result = self.run_script("release_check.py", "--package")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("files outside public manifest", result.stdout)

    def test_full_release_gate_passes(self) -> None:
        result = self.run_script("release_check.py")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("workflow_release_check: OK (release, files=39)", result.stdout)

    def test_public_docs_cover_install_safety_and_provenance(self) -> None:
        readme = (PACKAGE / "README.md").read_text()
        for token in (
            "qzl0215/workflow",
            "复制给你的 Agent",
            "不需要先知道 skills 目录",
            "install.py install",
            "install.py detect",
            "install.py update",
            "install.py uninstall",
            "English",
        ):
            self.assertIn(token, readme)
        notice = (PACKAGE / "NOTICE.md").read_text()
        for token in ("Attribution", "Clean-room", "Excluded"):
            self.assertIn(token, notice)

    def run_copied_release(self, mutate) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "workflow"
            shutil.copytree(PACKAGE, package, ignore=shutil.ignore_patterns(".git"))
            mutate(package)
            return subprocess.run(
                [sys.executable, "-B", str(package / "scripts/release_check.py")],
                cwd=package,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

    def test_release_gate_fails_when_target_file_is_missing(self) -> None:
        result = self.run_copied_release(lambda package: (package / "references/verification.md").unlink())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing target files: references/verification.md", result.stdout)

    def test_release_gate_fails_on_sensitive_assignment(self) -> None:
        def mutate(package: Path) -> None:
            path = package / "references/context-discovery.md"
            path.write_text(path.read_text() + "\npassword = example-secret-value\n")

        result = self.run_copied_release(mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive-looking credential assignment", result.stdout)

    def test_release_gate_fails_when_visual_map_is_stale(self) -> None:
        def mutate(package: Path) -> None:
            path = package / "SKILL.md"
            path.write_text(path.read_text() + "\n<!-- changed -->\n")

        result = self.run_copied_release(mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale visual map", result.stdout)

    def test_release_gate_ignores_git_checkout_metadata(self) -> None:
        def mutate(package: Path) -> None:
            metadata = package / ".git" / "objects"
            metadata.mkdir(parents=True)
            (package / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
            (metadata / "sample").write_bytes(b"git metadata")

        result = self.run_copied_release(mutate)
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
