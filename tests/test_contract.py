from __future__ import annotations

import ast
import html
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


PACKAGE = Path(__file__).resolve().parents[1]
SCRIPTS = PACKAGE / "scripts"
CHECK = SCRIPTS / "check.py"
INSTALL = SCRIPTS / "install.py"
SCENARIOS = PACKAGE / "tests" / "scenarios.md"
RUNTIME_DIRECTORIES = ("references", "templates")
GARBAGE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def load_check_module():
    spec = importlib.util.spec_from_file_location("workflow_runtime_check", CHECK)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load workflow runtime checker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    blocks = text.split("---", 2)
    if len(blocks) < 3:
        return {}
    values: dict[str, str] = {}
    for line in blocks[1].splitlines():
        if re.match(r"^[A-Za-z][A-Za-z0-9_-]*\s*:", line):
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip("'\"")
    return values


def run_script(
    script: Path,
    *arguments: str,
    cwd: Optional[Path] = None,
    env: Optional[dict[str, str]] = None,
    isolated: bool = False,
) -> subprocess.CompletedProcess[str]:
    flags = ["-I"] if isolated else []
    return subprocess.run(
        [sys.executable, *flags, "-B", str(script), *arguments],
        cwd=cwd or script.parent,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def copy_runtime(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    shutil.copy2(source / "SKILL.md", destination / "SKILL.md")
    for name in RUNTIME_DIRECTORIES:
        shutil.copytree(source / name, destination / name)


def copy_clean_room(source: Path, destination: Path) -> None:
    copy_runtime(source, destination)
    scripts = destination / "scripts"
    scripts.mkdir()
    shutil.copy2(source / "scripts" / "check.py", scripts / "check.py")
    shutil.copy2(source / "scripts" / "install.py", scripts / "install.py")


class ProgressiveProtocolContractTest(unittest.TestCase):
    def test_runtime_graph_is_mechanically_valid_and_closed(self) -> None:
        result = run_script(CHECK, str(PACKAGE), isolated=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("runtime check: OK", result.stdout)

    def test_every_runtime_markdown_is_reachable_from_the_root_graph(self) -> None:
        checker = load_check_module()
        files, errors = checker.runtime_files(PACKAGE)
        self.assertEqual(errors, [])
        markdown = {path.resolve() for path in files if path.suffix.casefold() == ".md"}
        graph = {path: set() for path in markdown}
        for source in markdown:
            text = source.read_text(encoding="utf-8")
            for raw in checker.destinations(text):
                target = checker.resolve_local(PACKAGE, source, raw)
                if target in markdown:
                    graph[source].add(target)
        visited: set[Path] = set()
        pending = [(PACKAGE / "SKILL.md").resolve()]
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            pending.extend(graph.get(current, ()))
        self.assertEqual(visited, markdown)

    def test_stage_references_declare_progressive_context_contracts(self) -> None:
        stages: list[int] = []
        conditionals: list[int] = []
        for path in sorted((PACKAGE / "references").rglob("*.md")):
            meta = frontmatter(path)
            self.assertIn(meta.get("kind"), {"stage", "conditional"}, path.name)
            self.assertRegex(meta.get("stage", ""), r"^\d{2}$", path.name)
            number = int(meta["stage"])
            if meta["kind"] == "stage":
                stages.append(number)
                text = path.read_text(encoding="utf-8")
                for heading in ("## 最小上下文", "## 责任角色", "## 输出", "## 退出与路由"):
                    self.assertIn(heading, text, path.name)
            else:
                conditionals.append(number)
        self.assertTrue(stages)
        self.assertEqual(stages, sorted(set(stages)))
        self.assertEqual(stages, list(range(1, max(stages) + 1)))
        self.assertTrue(set(conditionals).issubset(stages))

    def test_templates_have_one_owner_and_explicit_persistence(self) -> None:
        for path in (PACKAGE / "templates").rglob("*.md"):
            meta = frontmatter(path)
            for key in ("scope", "owner", "persistence"):
                self.assertTrue(meta.get(key), f"{path.name}: missing {key}")

    def test_templates_separate_contracts_from_runtime_state(self) -> None:
        scopes: dict[str, Path] = {}
        for path in (PACKAGE / "templates").glob("*.md"):
            meta = frontmatter(path)
            scope = meta.get("scope", "")
            self.assertTrue(scope, path.name)
            self.assertNotIn(scope, scopes, f"duplicate template scope: {scope}")
            scopes[scope] = path
            if scope != "runtime-control-plane":
                self.assertNotIn("stage", meta, path.name)
                self.assertNotIn("status", meta, path.name)

        self.assertIn("runtime-control-plane", scopes)
        self.assertIn("task-contract", scopes)

    def test_task_contract_is_versioned_and_progress_is_the_only_live_state_owner(self) -> None:
        scoped = {
            frontmatter(path).get("scope"): path
            for path in (PACKAGE / "templates").glob("*.md")
        }
        task = scoped["task-contract"].read_text(encoding="utf-8")
        for field in (
            "request_baseline:",
            "plan_version:",
            "contract_version:",
            "source_fingerprint:",
        ):
            self.assertIn(field, task)

        progress = scoped["runtime-control-plane"].read_text(encoding="utf-8")
        self.assertIn("Object State", progress)
        self.assertIn("Evidence Index", progress)
        self.assertIn("Feedback Queue", progress)
        self.assertIn("快照预算", progress)

    def test_python_surface_is_two_mechanical_tools_without_semantic_registries(self) -> None:
        self.assertEqual({path.name for path in SCRIPTS.glob("*.py")}, {"install.py", "check.py"})
        forbidden = (
            "CANONICAL_STAGES",
            "REQUIRED_REFERENCES",
            "PRIMARY_OWNER_FILES",
            "HARNESS_FILES",
            "ACTION_STORIES",
            "PUBLIC_TARGETS",
        )
        for path in SCRIPTS.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"semantic registry in {path.name}")

    def test_agent_native_prompt_installs_or_updates_without_python(self) -> None:
        readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
        install_section = re.search(
            r"^## [^\n]*安装[^\n]*更新[^\n]*\n(?P<body>.*?)(?=^## |\Z)",
            readme,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(install_section)
        section = install_section.group("body")
        prompts = re.findall(r"^> (.+)$", section, re.MULTILINE)
        self.assertEqual(len(prompts), 1, section)
        prompt = prompts[0]
        self.assertEqual(prompt.count("。"), 1, prompt)
        for token in (
            "https://github.com/qzl0215/workflow",
            "安装或更新",
            "最新 main",
            "备份",
            "SKILL.md",
            "references",
            "templates",
            "校验",
            "恢复",
        ):
            self.assertIn(token, prompt)
        self.assertNotIn("python", prompt.casefold())
        self.assertRegex(readme, r"Python[^。\n]*可选")

        page = (PACKAGE / "docs" / "index.html").read_text(encoding="utf-8")
        match = re.search(
            r'<pre class="install-prompt" id="install-prompt">(.*?)</pre>',
            page,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        page_prompt = html.unescape(match.group(1)).strip()
        self.assertEqual(page_prompt, prompt.replace("`", ""))

    def test_behavior_scenarios_have_unique_ids(self) -> None:
        text = SCENARIOS.read_text(encoding="utf-8")
        identifiers = re.findall(r"^## (S\d+)｜", text, re.MULTILINE)
        self.assertTrue(identifiers)
        self.assertEqual(len(identifiers), len(set(identifiers)))


class RuntimeCheckTest(unittest.TestCase):
    def run_copied_check(self, mutate=None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "runtime package"
            copy_runtime(PACKAGE, package)
            if mutate:
                mutate(package)
            return run_script(CHECK, str(package), isolated=True)

    def test_space_containing_local_links_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "package with spaces"
            references = package / "references"
            templates = package / "templates"
            references.mkdir(parents=True)
            templates.mkdir()
            (package / "SKILL.md").write_text(
                "---\nname: workflow\ndescription: fixture\n---\n\n[stage](<references/stage one.md>)\n",
                encoding="utf-8",
            )
            (references / "stage one.md").write_text(
                "---\nkind: stage\n---\n\n[template](<../templates/task capsule.md>)\n",
                encoding="utf-8",
            )
            (templates / "task capsule.md").write_text(
                "---\nscope: task\n---\n\n# Capsule\n",
                encoding="utf-8",
            )
            result = run_script(CHECK, str(package), isolated=True)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_check_rejects_broken_links_and_orphans(self) -> None:
        def broken(package: Path) -> None:
            with (package / "SKILL.md").open("a", encoding="utf-8") as handle:
                handle.write("\n[broken](references/missing.md)\n")

        result = self.run_copied_check(broken)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("broken or non-runtime local link", result.stdout)

        def orphan(package: Path) -> None:
            (package / "references" / "orphan.md").write_text(
                "---\nkind: conditional\n---\n\n# Orphan\n", encoding="utf-8"
            )

        result = self.run_copied_check(orphan)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unreachable from SKILL.md", result.stdout)

    def test_check_rejects_malformed_frontmatter_and_unsafe_text(self) -> None:
        cases = {
            "frontmatter": ("# no frontmatter\n", "missing frontmatter"),
            "machine path": ("\n/Users/alice/private-project\n", "machine-specific absolute path"),
            "credential": ("\npassword = example-secret-value\n", "credential assignment"),
            "conflict": ("\n<<<<<<< HEAD\n", "conflict marker"),
        }
        for name, (addition, expected) in cases.items():
            with self.subTest(name=name):
                def mutate(package: Path, value: str = addition, case: str = name) -> None:
                    path = package / "SKILL.md"
                    if case == "frontmatter":
                        path.write_text(value, encoding="utf-8")
                    else:
                        with path.open("a", encoding="utf-8") as handle:
                            handle.write(value)

                result = self.run_copied_check(mutate)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout)

    def test_check_rejects_invalid_frontmatter_lines_and_non_markdown_runtime_files(self) -> None:
        def invalid_frontmatter(package: Path) -> None:
            path = package / "SKILL.md"
            text = path.read_text(encoding="utf-8").replace(
                "description:", "description without colon", 1
            )
            path.write_text(text, encoding="utf-8")

        result = self.run_copied_check(invalid_frontmatter)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid frontmatter line", result.stdout)

        def non_markdown(package: Path) -> None:
            (package / "templates" / "hidden.env").write_text(
                "password=example-secret-value\n", encoding="utf-8"
            )

        result = self.run_copied_check(non_markdown)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported non-Markdown runtime file", result.stdout)

    def test_check_rejects_runtime_symlinks(self) -> None:
        def mutate(package: Path) -> None:
            target = next((package / "templates").rglob("*.md"))
            (package / "templates" / "linked.md").symlink_to(target)

        try:
            result = self.run_copied_check(mutate)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlinks are not allowed", result.stdout)


class InstallerRoundTripTest(unittest.TestCase):
    def test_detect_uses_an_explicit_environment_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "skills parent with spaces"
            target.mkdir()
            environment = {**os.environ, "AGENT_SKILLS_DIR": str(target)}
            result = run_script(INSTALL, "detect", env=environment, isolated=True)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn(str(target), result.stdout)

    def test_clean_room_install_update_check_and_recoverable_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            package = base / "source package with spaces"
            target = base / "skills parent with spaces"
            copy_clean_room(PACKAGE, package)

            # Environmental debris is ignored by both checking and copying.
            (package / "references" / ".DS_Store").write_bytes(b"finder")
            cache = package / "references" / "__pycache__"
            cache.mkdir()
            (cache / "cache.pyc").write_bytes(b"cache")
            (package / "templates" / "Thumbs.db").write_bytes(b"windows")

            install_script = package / "scripts" / "install.py"
            result = run_script(
                install_script, "install", "--target", str(target), cwd=package, isolated=True
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            installed = target / "workflow"
            self.assertTrue((installed / "SKILL.md").is_file())
            self.assertEqual(
                {path.name for path in installed.iterdir()},
                {"SKILL.md", "references", "templates"},
            )
            for garbage in GARBAGE_NAMES:
                self.assertEqual(list(installed.rglob(garbage)), [])
            self.assertEqual(list(installed.rglob("*.pyc")), [])

            result = run_script(
                install_script, "check", "--target", str(target), cwd=package, isolated=True
            )
            self.assertEqual(result.returncode, 0, result.stdout)

            marker = "<!-- clean-room update marker -->"
            with (package / "SKILL.md").open("a", encoding="utf-8") as handle:
                handle.write(f"\n{marker}\n")
            result = run_script(
                install_script, "update", "--target", str(target), cwd=package, isolated=True
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn(marker, (installed / "SKILL.md").read_text(encoding="utf-8"))
            backups = list(target.glob("workflow.backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertNotIn(marker, (backups[0] / "SKILL.md").read_text(encoding="utf-8"))

            denied = run_script(
                install_script, "uninstall", "--target", str(target), cwd=package, isolated=True
            )
            self.assertNotEqual(denied.returncode, 0)
            self.assertTrue(installed.is_dir())
            removed = run_script(
                install_script,
                "uninstall",
                "--target",
                str(target),
                "--yes",
                cwd=package,
                isolated=True,
            )
            self.assertEqual(removed.returncode, 0, removed.stdout)
            self.assertFalse(installed.exists())
            self.assertEqual(len(list(target.glob("workflow.removed-*"))), 1)

    def test_mutations_reject_source_overlap_and_unrecognized_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            package = base / "workflow"
            copy_clean_room(PACKAGE, package)
            install_script = package / "scripts" / "install.py"

            overlap = run_script(
                install_script,
                "uninstall",
                "--target",
                str(base),
                "--yes",
                cwd=package,
                isolated=True,
            )
            self.assertNotEqual(overlap.returncode, 0)
            self.assertIn("不能与源码包相同或重叠", overlap.stdout)
            self.assertTrue(package.is_dir())

            target = base / "other skills"
            unrelated = target / "workflow"
            unrelated.mkdir(parents=True)
            (unrelated / "keep.txt").write_text("user data\n", encoding="utf-8")
            for action in ("update", "uninstall"):
                arguments = [action, "--target", str(target)]
                if action == "uninstall":
                    arguments.append("--yes")
                result = run_script(
                    install_script, *arguments, cwd=package, isolated=True
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("不是可识别的 workflow 安装", result.stdout)
                self.assertEqual(
                    (unrelated / "keep.txt").read_text(encoding="utf-8"), "user data\n"
                )

    def test_tools_use_only_the_python_standard_library(self) -> None:
        standard = set(getattr(sys, "stdlib_module_names", ()))
        for path in (CHECK, INSTALL):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imports: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".", 1)[0])
            if standard:
                self.assertTrue(
                    imports.issubset(standard),
                    f"{path.name}: non-stdlib {imports - standard}",
                )
            arguments = ("detect",) if path == INSTALL else (str(PACKAGE),)
            result = run_script(path, *arguments, isolated=True)
            self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
