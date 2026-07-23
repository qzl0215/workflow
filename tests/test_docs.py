from __future__ import annotations

import hashlib
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
STAGES = ("需求澄清", "选定方案", "拆成任务", "执行任务", "验收交付", "提炼经验", "回灌改进")
UNKNOWN_ROUTES = ("事实可查", "取舍待定", "假设待验", "外部待解")
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
LEGACY_STAGE_WORDS = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    + "|".join(re.escape(value) for value in sorted(LEGACY_STAGES, key=len, reverse=True))
    + r")(?![A-Za-z0-9_])"
)


def public_target_count() -> int:
    path = PACKAGE / "scripts/workflow_doctor.py"
    spec = importlib.util.spec_from_file_location("workflow_doctor_for_docs_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load workflow_doctor manifest")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return len(module.PUBLIC_TARGETS)


def legacy_stage_registry() -> tuple[str, ...]:
    path = PACKAGE / "scripts/workflow_doctor.py"
    spec = importlib.util.spec_from_file_location("workflow_doctor_for_legacy_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load workflow_doctor legacy registry")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LEGACY_STAGE_NAMES


def visual_generator_module():
    path = PACKAGE / "scripts/generate_visual_map.py"
    spec = importlib.util.spec_from_file_location("workflow_visual_generator_for_docs_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load workflow visual generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def visual_source_digest(package: Path) -> str:
    paths = [
        package / "SKILL.md",
        package / "CHANGELOG.md",
        *sorted((package / "references").glob("*.md")),
    ]
    paths.extend(
        package / "templates" / name
        for name in (
            "index.md",
            "findings.md",
            "pre-plan-contract.md",
            "task_plan.md",
            "implementation-plan.md",
            "progress.md",
            "task-owner-prompt.md",
        )
    )
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(package).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:12]


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

    def test_first_public_stage_is_requirement_clarification(self) -> None:
        skill = (PACKAGE / "SKILL.md").read_text()
        self.assertIn("计划：需求澄清 → 选定方案 → 拆成任务", skill)
        self.assertEqual(next(iter(visual_generator_module().STAGE_QUESTIONS)), "需求澄清")
        self.assertIn('data-stage="需求澄清"', (PACKAGE / "docs/workflow-visual-map.html").read_text())

    def test_github_release_metadata_carries_forward_the_previous_public_version(self) -> None:
        skill = (PACKAGE / "SKILL.md").read_text()
        readme = (PACKAGE / "README.md").read_text()
        changelog = (PACKAGE / "CHANGELOG.md").read_text()
        version = re.search(r"^version:\s*(\S+)$", skill, re.M)
        self.assertIsNotNone(version)
        current = version.group(1)
        self.assertIn(f"当前协议版本：`{current}`", readme)
        self.assertIn(f"## [{current}] - 2026-07-24", changelog)
        self.assertIn("### Migration from 2.1.0-beta.3", changelog)
        self.assertIn("## [2.1.0-beta.3] - 2026-07-21", changelog)

    def test_visual_map_uses_the_current_skill_version(self) -> None:
        skill = (PACKAGE / "SKILL.md").read_text()
        generated = (PACKAGE / "docs/workflow-visual-map.html").read_text()
        version = re.search(
            r"^version:\s*(\d+)\.(\d+)\.\d+(?:-([A-Za-z]+)(?:\.\d+)?)?$",
            skill,
            re.M,
        )
        self.assertIsNotNone(version)
        label = f"V{version.group(1)}.{version.group(2)}"
        if version.group(3):
            label += f" {version.group(3).upper()}"
        self.assertIn(label, generated)

    def test_visual_map_is_fresh(self) -> None:
        result = self.run_script("generate_visual_map.py", "--check")
        self.assertEqual(result.returncode, 0, result.stdout)
        digest = visual_source_digest(PACKAGE)
        generated = (PACKAGE / "docs/workflow-visual-map.html").read_text()
        self.assertIn(f"source sha256 {digest}", generated)

    def test_visual_map_contains_all_states_and_routes(self) -> None:
        source = (PACKAGE / "SKILL.md").read_text()
        generated = (PACKAGE / "docs/workflow-visual-map.html").read_text()
        stages = re.findall(rf"^\| ({'|'.join(STAGES)}) \|", source, re.M)
        routes = re.findall(r"`(references/[A-Za-z0-9_-]+\.md)`", source)
        self.assertEqual(stages, list(STAGES))
        self.assertEqual(len(routes), 14)
        for token in [*stages, *UNKNOWN_ROUTES, *routes]:
            self.assertIn(token, generated)

    def test_stage_questions_are_a_small_user_facing_content_model(self) -> None:
        module = visual_generator_module()
        questions = module.STAGE_QUESTIONS
        self.assertEqual(tuple(questions), STAGES)
        for name, question in questions.items():
            with self.subTest(stage=name):
                self.assertLessEqual(len(question), 18)
                self.assertTrue(question.endswith("？"))

    def test_visual_model_covers_all_capabilities_and_document_templates(self) -> None:
        module = visual_generator_module()
        self.assertEqual(len(module.PRIMARY_OWNER_FILES), 7)
        self.assertEqual(len(module.HARNESS_FILES), 7)
        self.assertEqual(len(module.VISUAL_TEMPLATE_NAMES), 7)

    def test_visual_build_uses_the_current_release_without_publishing_release_noise(self) -> None:
        def mutate(package: Path) -> None:
            skill = (package / "SKILL.md").read_text()
            version = re.search(r"^version:\s*(\S+)$", skill, re.M)
            self.assertIsNotNone(version)
            changelog = package / "CHANGELOG.md"
            source = changelog.read_text()
            release = re.search(
                rf"^## \[{re.escape(version.group(1))}\].*?(?=^## \[|\Z)",
                source,
                re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(release)
            updated = (
                f"## [{version.group(1)}] - test\n\n"
                "### Changed\n\n"
                "- 需求澄清\n\n"
            )
            changelog.write_text(source[: release.start()] + updated + source[release.end() :])

        result, generated = self.run_copied_visual(mutate)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("需求澄清", generated)
        self.assertNotIn("本版强化", generated)
        self.assertNotIn("保持稳定", generated)

    def test_visual_build_still_rejects_a_missing_current_release(self) -> None:
        def mutate(package: Path) -> None:
            skill = (package / "SKILL.md").read_text()
            version = re.search(r"^version:\s*(\S+)$", skill, re.M)
            self.assertIsNotNone(version)
            changelog = package / "CHANGELOG.md"
            source = changelog.read_text()
            release = re.search(
                rf"^## \[{re.escape(version.group(1))}\].*?(?=^## \[|\Z)",
                source,
                re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(release)
            changelog.write_text(source[: release.start()] + source[release.end() :])

        result, _ = self.run_copied_visual(mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "visual map source error: current changelog does not support the visual self-introduction",
            result.stdout,
        )

    def test_changelog_is_part_of_visual_freshness(self) -> None:
        def mutate(package: Path) -> None:
            path = package / "CHANGELOG.md"
            path.write_text(path.read_text() + "\n<!-- visual change evidence -->\n")

        result = self.run_copied_release(mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale visual map", result.stdout)

    def test_visual_map_is_a_concise_self_description(self) -> None:
        generated = (PACKAGE / "docs/workflow-visual-map.html").read_text()
        for token in (
            "我是 workflow",
            "我只有一条主链",
            "大多数时候，我会自己往前走",
            "这些节点，我一定等你",
            "遇到不确定，我不会一股脑问你",
            "我是单包协议",
        ):
            self.assertIn(token, generated)
        self.assertNotIn('id="workflow-actions"', generated)
        self.assertLess(len(generated), 40000)

    def test_visual_map_leads_with_the_user_result_and_main_path(self) -> None:
        generated = (PACKAGE / "docs/workflow-visual-map.html").read_text()
        for token in (
            "复杂工作，交给我推进到真的完成。",
            "你给我目标",
            "不确定 → 承诺",
            "承诺 → 证据",
            "结果 → 能力",
            'id="intro"',
            'id="path"',
            'id="install"',
            'data-user-layer',
            "prefers-reduced-motion",
        ):
            self.assertIn(token, generated)
        self.assertIn('lang="zh-CN"', generated)
        self.assertIn('aria-live="polite"', generated)
        self.assertIn('name="color-scheme" content="dark"', generated)
        self.assertNotIn("<script src=", generated)
        self.assertNotIn("@import url", generated)

    def test_visual_map_is_a_fluid_responsive_document(self) -> None:
        generated = (PACKAGE / "docs/workflow-visual-map.html").read_text()
        for token in (
            'class="page-shell"',
            'class="stage-grid"',
            'data-stage="需求澄清"',
            'data-stage="回灌改进"',
            'id="install"',
            'data-copy-target="agent-prompt"',
            'aria-label="页面导航"',
            "安装我",
            "prefers-reduced-motion",
        ):
            self.assertIn(token, generated)
        self.assertEqual(generated.count('data-stage="'), 7)
        self.assertIn("width:calc(100% - (2 * var(--gutter)))", generated)
        self.assertIn("@media(min-width:1800px)", generated)
        self.assertIn("min-height:44px", generated)
        self.assertNotIn("scroll-snap-type:y mandatory", generated)
        self.assertNotIn('class="slide ', generated)
        generator = (PACKAGE / "scripts/generate_visual_map.py").read_text()
        self.assertNotIn("LEGACY_HTML_TEMPLATE", generator)
        self.assertNotIn("REFERENCE_STORIES", generator)
        script_index = generated.index("<script>")
        for static_token in ("复杂工作，交给我推进到真的完成。", 'data-stage="需求澄清"', 'id="install"'):
            self.assertLess(generated.index(static_token), script_index)
        for removed in (
            'class="deck"',
            'data-deck-prev',
            'data-deck-next',
            "IntersectionObserver",
            "scrollIntoView",
            "PageDown",
            'id="workbench"',
            'class="action-button"',
            'class="stats"',
            'id="router"',
            'id="case"',
            'id="forest"',
            'id="references"',
            "Plan 总 DAG",
            "单 Plan · Task DAG",
            "五份工作真源，两个辅助模板",
        ):
            self.assertNotIn(removed, generated)
        for legacy in (
            "v1.2",
            "context-reset-handoff.md",
            "delegation-orchestration.md",
            "十阶段",
            "接住任务",
            "Intake",
        ):
            self.assertNotIn(legacy, generated)

    def test_each_stage_card_answers_one_business_question(self) -> None:
        module = visual_generator_module()
        generated = (PACKAGE / "docs/workflow-visual-map.html").read_text()
        for name, question in module.STAGE_QUESTIONS.items():
            with self.subTest(stage=name):
                card = re.search(
                    rf'<article[^>]+data-stage="{re.escape(name)}".*?</article>',
                    generated,
                    re.S,
                )
                self.assertIsNotNone(card)
                self.assertIn(question, card.group(0))

    def test_user_layer_does_not_expose_maintenance_vocabulary(self) -> None:
        generated = (PACKAGE / "docs/workflow-visual-map.html").read_text()
        user_layers = re.findall(r'<[^>]+data-user-layer[^>]*>(.*?)</(?:section|div)>', generated, re.S)
        self.assertTrue(user_layers)
        visible_source = " ".join(re.sub(r"<[^>]+>", " ", block) for block in user_layers)
        for word in ("owner", "harness", "reference", "DAG", "L0–L4", "digest", "fresh", "blocker"):
            self.assertNotIn(word, visible_source)

    def test_visual_map_keeps_all_capabilities_in_the_maintenance_layer(self) -> None:
        generated = (PACKAGE / "docs/workflow-visual-map.html").read_text()
        for filename in (*visual_generator_module().PRIMARY_OWNER_FILES, *visual_generator_module().HARNESS_FILES):
            self.assertIn(f"references/{filename}", generated)
        for filename in visual_generator_module().VISUAL_TEMPLATE_NAMES:
            self.assertIn(filename, generated)

    def test_package_release_gate_passes(self) -> None:
        result = self.run_script("release_check.py", "--package")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("files outside public manifest", result.stdout)

    def test_full_release_gate_passes(self) -> None:
        result = self.run_script("release_check.py")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            f"workflow_release_check: OK (release, files={public_target_count()})",
            result.stdout,
        )

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
            "作者：zhonglin",
            "需求澄清",
            "专家圆桌",
            "完整森林图景",
            "计划、执行、复盘",
            "三段七动作",
            "四路未知",
            "14 项按需能力",
            "发现小改进时，先提案再动手",
            "小改动、大价值",
            "正确归属地",
        ):
            self.assertIn(token, readme)
        notice = (PACKAGE / "NOTICE.md").read_text()
        for token in ("Attribution", "Clean-room", "Excluded"):
            self.assertIn(token, notice)
        skill = (PACKAGE / "SKILL.md").read_text()
        self.assertIn("version: 2.4.0", skill)
        self.assertIn("author: zhonglin", skill)

    def test_workflow_has_project_scoped_standing_release_authorization(self) -> None:
        contributing = (PACKAGE / "CONTRIBUTING.md").read_text()
        for token in (
            "## 持续发布授权",
            "2026-07-24",
            "`qzl0215/workflow`",
            "commit、push、合并到主版本和发布",
            "不再重复请求授权",
            "仅限本仓库",
            "fresh",
            "P0",
            "禁止 force",
            "默认发布正式版本",
            "递增 minor 版本",
            "只有项目 owner 明确要求时才创建预发布",
        ):
            self.assertIn(token, contributing)

    def test_formal_sources_do_not_publish_legacy_stage_words(self) -> None:
        paths = [
            *(path for path in sorted(PACKAGE.glob("*.md")) if path.name != "CHANGELOG.md"),
            PACKAGE / "docs/workflow-visual-map.html",
            *sorted((PACKAGE / "references").glob("*.md")),
            *sorted((PACKAGE / "templates").glob("*.md")),
        ]
        offenders = []
        for path in paths:
            matches = sorted({match.group(0) for match in LEGACY_STAGE_WORDS.finditer(path.read_text())})
            if matches:
                offenders.append(f"{path.relative_to(PACKAGE)}: {', '.join(matches)}")
        self.assertEqual(offenders, [], "legacy stage words escaped the compatibility boundary:\n" + "\n".join(offenders))

    def test_legacy_stage_registry_covers_the_full_read_boundary(self) -> None:
        self.assertEqual(legacy_stage_registry(), LEGACY_STAGES)

    def test_release_gate_rejects_every_legacy_stage_word_in_public_docs(self) -> None:
        for legacy in LEGACY_STAGES:
            with self.subTest(legacy=legacy):
                def mutate(package: Path, value: str = legacy) -> None:
                    path = package / "README.md"
                    path.write_text(path.read_text() + f"\n{value}\n")

                result = self.run_copied_release(mutate)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("legacy stage words escaped read-boundary compatibility", result.stdout)

    def test_release_gate_rejects_legacy_stage_words_in_maintenance_docs(self) -> None:
        def mutate(package: Path) -> None:
            path = package / "CONTRIBUTING.md"
            path.write_text(path.read_text() + "\nIntake\n")

        result = self.run_copied_release(mutate)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("CONTRIBUTING.md: legacy stage words", result.stdout)

    def test_changelog_records_reference_migration_and_compatibility_exit(self) -> None:
        changelog = (PACKAGE / "CHANGELOG.md").read_text()
        for token in (
            "project-discovery.md + context-discovery.md + clarify-prioritize.md → understand-goal.md",
            "verification.md + finish-release.md → verify-deliver.md",
            "challenge-decisions.md",
            "learn-review.md",
            "one release cycle",
            "Compatibility remains through the 2.x release cycle and is removed in 3.0.0",
        ):
            self.assertIn(token, changelog)

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

    def run_copied_visual(self, mutate) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "workflow"
            shutil.copytree(PACKAGE, package, ignore=shutil.ignore_patterns(".git"))
            mutate(package)
            result = subprocess.run(
                [sys.executable, "-B", str(package / "scripts/generate_visual_map.py")],
                cwd=package,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            generated = (package / "docs/workflow-visual-map.html").read_text()
            return result, generated

    def test_release_gate_fails_when_target_file_is_missing(self) -> None:
        result = self.run_copied_release(lambda package: (package / "references/verify-deliver.md").unlink())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing target files: references/verify-deliver.md", result.stdout)

    def test_release_gate_fails_on_sensitive_assignment(self) -> None:
        def mutate(package: Path) -> None:
            path = package / "references/understand-goal.md"
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

    def test_visual_map_stales_when_reference_or_plan_contract_changes(self) -> None:
        for relative in (
            "references/verify-deliver.md",
            "templates/task_plan.md",
            "templates/task-owner-prompt.md",
        ):
            with self.subTest(relative=relative):
                def mutate(package: Path, target: str = relative) -> None:
                    path = package / target
                    path.write_text(path.read_text() + "\n<!-- visual source changed -->\n")

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
