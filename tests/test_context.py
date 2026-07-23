from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "scripts/build_context_capsule.py"
CANONICAL_STAGES = (
    "需求澄清",
    "选定方案",
    "拆成任务",
    "执行任务",
    "验收交付",
    "提炼经验",
    "回灌改进",
)
LEGACY_STAGE_MAP = {
    "看清目标": "需求澄清",
    "Intake": "需求澄清",
    "Clarify": "需求澄清",
    "Readiness": "需求澄清",
    "Solution": "选定方案",
    "Strategic Planning": "选定方案",
    "Experience": "选定方案",
    "Write": "拆成任务",
    "Write Plan": "拆成任务",
    "Act": "执行任务",
    "Act Plan": "执行任务",
    "Debug": "执行任务",
    "Verify": "验收交付",
    "Finish": "验收交付",
}


class ContextContractTest(unittest.TestCase):
    def make_task(
        self,
        root: Path,
        *,
        include_task: bool = True,
        frontmatter_stage: str | None = None,
        snapshot_stage: str | None = "执行任务",
    ) -> Path:
        task_dir = root / "plans/260719-demo"
        task_dir.mkdir(parents=True, exist_ok=True)
        frontmatter = (
            f"---\nstage: {frontmatter_stage}\nstatus: active\n---\n\n"
            if frontmatter_stage is not None
            else ""
        )
        snapshot_line = f"- 当前阶段：{snapshot_stage}\n" if snapshot_stage is not None else ""
        task_section = """
#### P01-T01｜最小切片
- 上下文引用：findings:E01；domain:demo
- 完成标准：只加载相关证据
""" if include_task else ""
        (task_dir / "task_plan.md").write_text(
            f"""{frontmatter}# Demo

### Current Snapshot
{snapshot_line}- 活跃 Plan / Task：P01 / P01-T01

## 4. 执行计划

#### P01｜结果
- 业务 DONE：示例可工作
{task_section}
#### P01-T02｜无关任务
SHOULD_NOT_BE_LOADED
"""
        )
        (task_dir / "findings.md").write_text(
            """# Findings

| 证据 ID | 事实 | 来源 |
|---|---|---|
| E01 | 最小上下文有效 | test |
| E99 | SHOULD_NOT_BE_LOADED | old |
"""
        )
        (task_dir / "implementation-plan.md").write_text(
            """# Implementation

### P01-T01｜实现
- 验证：context test

### P01-T02｜无关
SHOULD_NOT_BE_LOADED
"""
        )
        (task_dir / "progress.md").write_text(
            """# Progress

## Handoff checkpoint
- 最近完成：拆成任务
- 下一步：P01-T01

## Old history
SHOULD_NOT_BE_LOADED
"""
        )
        return task_dir

    def run_capsule(
        self,
        task_dir: Path,
        output: str = "json",
        *,
        stage: str | None = None,
        allow_missing: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            "-B",
            str(SCRIPT),
            "--task-dir",
            str(task_dir),
            "--plan",
            "P01",
            "--task",
            "P01-T01",
            "--format",
            output,
        ]
        if stage is not None:
            command.extend(("--stage", stage))
        if allow_missing:
            command.append("--allow-missing")
        return subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def add_stage_results(self, task_dir: Path, rows: list[tuple[str, str, str]]) -> None:
        route_rows = "\n".join(f"| {stage} | {target_type} | `{path}` |" for stage, target_type, path in rows)
        task_plan = task_dir / "task_plan.md"
        task_plan.write_text(
            task_plan.read_text()
            + "\n## 阶段成果路由\n\n"
            + "| 阶段 | 目标类型 | 项目相对入口 |\n"
            + "|---|---|---|\n"
            + route_rows
            + "\n"
        )

    def test_all_canonical_chinese_stages_round_trip_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            for stage in CANONICAL_STAGES:
                with self.subTest(stage=stage):
                    task_dir = self.make_task(Path(temp), snapshot_stage=stage)
                    result = self.run_capsule(task_dir)
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertEqual(json.loads(result.stdout)["stage"], stage)

    def test_requirement_clarification_is_canonical_and_old_chinese_name_is_read_only_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = self.make_task(Path(temp), snapshot_stage=None)
            canonical = self.run_capsule(task_dir, stage="需求澄清")
            self.assertEqual(canonical.returncode, 0, canonical.stdout)
            self.assertEqual(json.loads(canonical.stdout)["stage"], "需求澄清")

            legacy = self.run_capsule(task_dir, stage="看清目标")
            self.assertEqual(legacy.returncode, 0, legacy.stdout)
            self.assertEqual(json.loads(legacy.stdout)["stage"], "需求澄清")
            self.assertNotIn('"stage": "看清目标"', legacy.stdout)

    def test_legacy_stage_values_are_normalized_at_the_cli_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = self.make_task(Path(temp), snapshot_stage=None)
            for legacy, canonical in LEGACY_STAGE_MAP.items():
                with self.subTest(legacy=legacy):
                    result = self.run_capsule(task_dir, stage=legacy)
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertEqual(json.loads(result.stdout)["stage"], canonical)
                    self.assertNotIn(f'"stage": "{legacy}"', result.stdout)

    def test_cli_stage_is_optional_when_task_plan_has_a_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_capsule(self.make_task(Path(temp)))
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(json.loads(result.stdout)["stage"], "执行任务")

    def test_cli_stage_must_match_task_plan_truth(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_capsule(self.make_task(Path(temp)), stage="看清目标")
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("阶段冲突", result.stdout)
            self.assertNotIn('"schema_version"', result.stdout)

    def test_frontmatter_and_snapshot_must_not_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = self.make_task(
                Path(temp),
                frontmatter_stage="看清目标",
                snapshot_stage="执行任务",
            )
            result = self.run_capsule(task_dir)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("阶段冲突", result.stdout)

    def test_legacy_frontmatter_and_snapshot_are_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            frontmatter = self.make_task(
                Path(temp),
                frontmatter_stage="Act",
                snapshot_stage="执行任务",
            )
            result = self.run_capsule(frontmatter)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(json.loads(result.stdout)["stage"], "执行任务")

            snapshot = self.make_task(Path(temp), snapshot_stage="Act Plan")
            result = self.run_capsule(snapshot)
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["stage"], "执行任务")
            self.assertNotIn("Act Plan", json.dumps(payload, ensure_ascii=False))

    def test_legacy_snapshot_is_canonicalized_in_markdown_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = self.make_task(Path(temp), snapshot_stage="Act")
            result = self.run_capsule(task_dir, output="markdown")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("执行任务", result.stdout)
            self.assertNotRegex(result.stdout, r"\bAct\b")

    def test_missing_task_plan_stage_and_cli_assertion_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = self.make_task(Path(temp), snapshot_stage=None)
            result = self.run_capsule(task_dir)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("缺少阶段", result.stdout)

    def test_unknown_stage_fails_closed_without_emitting_a_capsule(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_capsule(
                self.make_task(Path(temp)),
                stage="Almost Done",
                allow_missing=True,
            )
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("未知阶段", result.stdout)
            self.assertNotIn('"schema_version"', result.stdout)

    def test_capsule_loads_only_l0_to_l2_slices(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_capsule(self.make_task(Path(temp)))
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], 2)
            self.assertFalse(payload["fail_closed"])
            self.assertIn("domain:demo", payload["external_refs"])
            selected = json.dumps(payload["slices"], ensure_ascii=False)
            self.assertIn("E01", selected)
            self.assertNotIn("SHOULD_NOT_BE_LOADED", selected)

    def test_capsule_carries_active_stage_result_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = self.make_task(Path(temp))
            self.add_stage_results(
                task_dir,
                [
                    ("需求澄清", "document", "plans/260719-demo/findings.md"),
                    ("选定方案", "visual", "design/selected.html"),
                    ("拆成任务", "collection", "plans/260719-demo/"),
                ],
            )
            result = self.run_capsule(task_dir)
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(
                payload["stage_results"],
                [
                    {"stage": "需求澄清", "target_type": "document", "path": "plans/260719-demo/findings.md"},
                    {"stage": "选定方案", "target_type": "visual", "path": "design/selected.html"},
                    {"stage": "拆成任务", "target_type": "collection", "path": "plans/260719-demo"},
                ],
            )

            markdown = self.run_capsule(task_dir, output="markdown")
            self.assertEqual(markdown.returncode, 0, markdown.stdout)
            self.assertIn("L1｜Active stage results", markdown.stdout)
            self.assertIn("design/selected.html", markdown.stdout)

    def test_old_task_without_stage_results_recovers_with_empty_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_capsule(self.make_task(Path(temp)))
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(json.loads(result.stdout)["stage_results"], [])

    def test_legacy_route_stage_is_normalized_and_removed_routes_stay_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = self.make_task(Path(temp))
            self.add_stage_results(task_dir, [("看清目标", "document", "findings.md")])
            result = self.run_capsule(task_dir)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(
                json.loads(result.stdout)["stage_results"],
                [{"stage": "需求澄清", "target_type": "document", "path": "findings.md"}],
            )
            self.assertNotIn("拆成任务", json.dumps(json.loads(result.stdout)["stage_results"], ensure_ascii=False))

    def test_invalid_or_duplicate_stage_result_routes_fail_closed(self) -> None:
        invalid_cases = {
            "unknown type": [("需求澄清", "preview", "findings.md")],
            "absolute path": [("需求澄清", "document", "/tmp/findings.md")],
            "parent escape": [("需求澄清", "document", "../findings.md")],
            "file URL": [("需求澄清", "document", "file:///tmp/findings.md")],
            "unknown stage": [("完成", "document", "findings.md")],
            "duplicate stage": [
                ("需求澄清", "document", "findings.md"),
                ("需求澄清", "visual", "selected.html"),
            ],
        }
        for name, rows in invalid_cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                task_dir = self.make_task(Path(temp))
                self.add_stage_results(task_dir, rows)
                result = self.run_capsule(task_dir, allow_missing=True)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("阶段成果路由", result.stdout)
                self.assertNotIn('"schema_version"', result.stdout)

    def test_missing_current_task_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_capsule(self.make_task(Path(temp), include_task=False))
            self.assertEqual(result.returncode, 2)
            self.assertIn("task_plan.md#P01-T01", result.stdout)

    def test_markdown_exposes_all_loading_levels(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_capsule(self.make_task(Path(temp)), output="markdown")
            self.assertEqual(result.returncode, 0, result.stdout)
            for level in ("L0｜Location", "L1｜Current Snapshot", "L2｜Current Task", "L3/L4｜Context accounting"):
                self.assertIn(level, result.stdout)

    def test_roles_and_paths_are_platform_neutral(self) -> None:
        root = (PACKAGE / "SKILL.md").read_text()
        templates = "\n".join(path.read_text() for path in (PACKAGE / "templates").glob("*.md"))
        for role in ("总协调者", "Plan owner", "Task owner", "Reviewer"):
            self.assertIn(f"**{role}**", root)
        for forbidden in ("/opt/" + "obrain", "/" + "Users" + "/", "C:\\" + "Users\\"):
            self.assertNotIn(forbidden, root + templates)


if __name__ == "__main__":
    unittest.main()
