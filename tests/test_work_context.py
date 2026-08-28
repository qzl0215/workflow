from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "scripts/work_context.py"


class WorkContextTest(unittest.TestCase):
    def run_context(
        self,
        task_dir: Path,
        *,
        task: str = "P01-T01",
        output: str = "json",
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
            task,
            "--format",
            output,
        ]
        if allow_missing:
            command.append("--allow-missing")
        return subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def write_work(self, root: Path) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        (root / "work.md").write_text(
            """# 工作真源

## 当前状态
- 状态：active
- 当前动作：任务执行

## 目标契约
- 目标：让升级可恢复
- 验收：旧版本可以安全进入新运行时

## 结果计划
### P01｜升级桥
- 依赖：无

#### P01-T01｜实现 manifest
- 任务状态：active
- 完成：逐文件 hash 通过
- 上下文：E01

#### P01-T02｜无关任务
- 任务状态：waiting
SHOULD_NOT_BE_LOADED

## 当前结果
- manifest 解析已完成

## 已接受回执
- P01-T01 / E01：定向测试通过
- P01-T02 / E99：SHOULD_NOT_BE_LOADED

## 下一动作
- 验证升级

## 阻断与交付
- 阻断：无
- 交付状态：未交付

## 经验候选
- 暂无
""",
            encoding="utf-8",
        )
        return root

    def test_work_md_wins_and_capsule_only_loads_selected_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = self.write_work(Path(temp) / "task")
            (task_dir / "task_plan.md").write_text("LEGACY_SHOULD_NOT_WIN", encoding="utf-8")
            result = self.run_context(task_dir)
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["source"], "work.md")
            self.assertEqual(payload["status"], "active")
            self.assertEqual(payload["work_status"], "active")
            self.assertEqual(payload["task_status"], "active")
            self.assertTrue(payload["dispatchable"])
            self.assertIn("P01", payload["plan_result"])
            self.assertNotIn("P01-T01", payload["plan_result"])
            self.assertIn("P01-T01", payload["task_contract"])
            self.assertNotIn("P01-T02", payload["task_contract"])
            self.assertIn("E01", payload["accepted_receipts"])
            self.assertNotIn("E99", payload["accepted_receipts"])
            self.assertNotIn("LEGACY_SHOULD_NOT_WIN", result.stdout)
            for field in (
                "contract_hash",
                "plan_contract_hash",
                "task_contract_hash",
                "capsule_hash",
            ):
                self.assertRegex(payload[field], r"^sha256:[0-9a-f]{64}$")

    def test_contract_task_and_capsule_identities_change_at_their_own_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = self.write_work(Path(temp) / "task")
            first = json.loads(self.run_context(task_dir).stdout)
            work = task_dir / "work.md"
            work.write_text(
                work.read_text(encoding="utf-8").replace("逐文件 hash 通过", "逐文件 hash 与 doctor 通过"),
                encoding="utf-8",
            )
            second = json.loads(self.run_context(task_dir).stdout)
            self.assertEqual(first["contract_hash"], second["contract_hash"])
            self.assertNotEqual(first["task_contract_hash"], second["task_contract_hash"])
            self.assertNotEqual(first["capsule_hash"], second["capsule_hash"])

    def test_legacy_is_read_only_and_delivery_stays_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp) / "legacy"
            task_dir.mkdir()
            (task_dir / "task_plan.md").write_text(
                """---
stage: 验收交付
status: active
---
# 旧计划
## 需求与验收
- 目标：完成升级
## P01｜旧计划结果
### P01-T01｜旧任务
- 完成标准：E01 通过
""",
                encoding="utf-8",
            )
            (task_dir / "findings.md").write_text("| E01 | 已通过 | test |\n", encoding="utf-8")
            before = sorted(path.name for path in task_dir.iterdir())
            result = self.run_context(task_dir)
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["source"], "legacy-v2-read-only")
            self.assertEqual(payload["action_hint"], "结果验真")
            self.assertEqual(payload["delivery"], "unknown")
            self.assertIn("不证明", payload["legacy_note"])
            self.assertEqual(sorted(path.name for path in task_dir.iterdir()), before)

    def test_invalid_work_status_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = self.write_work(Path(temp) / "task")
            work = task_dir / "work.md"
            work.write_text(work.read_text().replace("状态：active", "状态：almost"), encoding="utf-8")
            result = self.run_context(task_dir)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("状态无效", result.stdout)
            self.assertNotIn('"capsule_hash"', result.stdout)
            still_blocked = self.run_context(task_dir, allow_missing=True)
            self.assertEqual(still_blocked.returncode, 2, still_blocked.stdout)

    def test_missing_source_can_only_emit_an_explicit_empty_capsule(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp) / "missing"
            task_dir.mkdir()
            blocked = self.run_context(task_dir)
            self.assertEqual(blocked.returncode, 2, blocked.stdout)
            allowed = self.run_context(task_dir, allow_missing=True)
            self.assertEqual(allowed.returncode, 0, allowed.stdout)
            payload = json.loads(allowed.stdout)
            self.assertEqual(payload["source"], "missing")
            self.assertEqual(payload["status"], "blocked")
            self.assertFalse(payload["dispatchable"])
            self.assertEqual(payload["delivery"], "unknown")

    def test_plan_task_identity_and_waiting_state_fail_closed_for_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = self.write_work(Path(temp) / "task")
            wrong_plan = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--task-dir",
                    str(task_dir),
                    "--plan",
                    "P02",
                    "--task",
                    "P01-T01",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(wrong_plan.returncode, 2, wrong_plan.stdout)
            self.assertIn("不属于", wrong_plan.stdout)

            waiting = self.run_context(task_dir, task="P01-T02")
            self.assertEqual(waiting.returncode, 0, waiting.stdout)
            payload = json.loads(waiting.stdout)
            self.assertEqual(payload["task_status"], "waiting")
            self.assertFalse(payload["dispatchable"])

            work = task_dir / "work.md"
            work.write_text(
                work.read_text(encoding="utf-8").replace("- 任务状态：active\n", "", 1),
                encoding="utf-8",
            )
            missing_status = self.run_context(task_dir)
            self.assertEqual(missing_status.returncode, 2, missing_status.stdout)
            self.assertIn("禁止派发", missing_status.stdout)

    def test_contract_identity_never_hides_tail_changes_or_silent_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = self.write_work(Path(temp) / "task")
            first = json.loads(self.run_context(task_dir).stdout)
            work = task_dir / "work.md"
            work.write_text(
                work.read_text(encoding="utf-8").replace(
                    "- 上下文：E01",
                    "- 上下文：E01\n- 尾部授权：不得外部写入",
                ),
                encoding="utf-8",
            )
            second = json.loads(self.run_context(task_dir).stdout)
            self.assertNotEqual(first["task_contract_hash"], second["task_contract_hash"])
            self.assertIn("尾部授权", second["task_contract"])

            work.write_text(
                work.read_text(encoding="utf-8").replace(
                    "- 尾部授权：不得外部写入",
                    "- 承重边界：" + ("不" * 5000),
                ),
                encoding="utf-8",
            )
            oversized = self.run_context(task_dir)
            self.assertEqual(oversized.returncode, 2, oversized.stdout)
            self.assertIn("超过安全字节上限", oversized.stdout)


if __name__ == "__main__":
    unittest.main()
