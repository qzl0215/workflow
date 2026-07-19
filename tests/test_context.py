from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "scripts/build_context_capsule.py"


class ContextContractTest(unittest.TestCase):
    def make_task(self, root: Path, *, include_task: bool = True) -> Path:
        task_dir = root / "plans/260719-demo"
        task_dir.mkdir(parents=True)
        task_section = """
#### P01-T01｜最小切片
- 上下文引用：findings:E01；domain:demo
- 完成标准：只加载相关证据
""" if include_task else ""
        (task_dir / "task_plan.md").write_text(
            f"""# Demo

### Current Snapshot
- 当前阶段：Act
- 活跃 Plan / Task：P01 / P01-T01

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
- 最近完成：Write
- 下一步：P01-T01

## Old history
SHOULD_NOT_BE_LOADED
"""
        )
        return task_dir

    def run_capsule(self, task_dir: Path, output: str = "json") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                "--task-dir",
                str(task_dir),
                "--plan",
                "P01",
                "--task",
                "P01-T01",
                "--stage",
                "Act",
                "--format",
                output,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

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
        for role in ("Orchestrator", "Owner", "Worker", "Reviewer"):
            self.assertIn(f"**{role}**", root)
        for forbidden in ("/opt/" + "obrain", "/" + "Users" + "/", "C:\\" + "Users\\"):
            self.assertNotIn(forbidden, root + templates)


if __name__ == "__main__":
    unittest.main()
