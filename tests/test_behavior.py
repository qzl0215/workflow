from __future__ import annotations

import re
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SKILL = (PACKAGE / "SKILL.md").read_text()


def reference(name: str) -> str:
    return (PACKAGE / "references" / name).read_text()


class StateMachineContractTest(unittest.TestCase):
    def test_strict_stage_order_is_explicit(self) -> None:
        order = "Clarify → Readiness → Solution → Experience/N/A → Write → Act ↔ Debug → Verify → Finish"
        self.assertIn(order, SKILL)

    def test_every_state_has_a_complete_interface(self) -> None:
        expected = [
            "Intake",
            "Clarify",
            "Readiness",
            "Solution",
            "Experience",
            "Write",
            "Act",
            "Debug",
            "Verify",
            "Finish",
        ]
        rows = {}
        for line in SKILL.splitlines():
            match = re.match(r"^\| (Intake|Clarify|Readiness|Solution|Experience|Write|Act|Debug|Verify|Finish) \|", line)
            if match:
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                rows[match.group(1)] = cells
        self.assertEqual(list(rows), expected)
        for state, cells in rows.items():
            self.assertEqual(len(cells), 5, state)
            self.assertTrue(all(cells), state)

    def test_readiness_is_minimal_and_cannot_be_skipped_when_blocking(self) -> None:
        text = reference("project-discovery.md")
        self.assertIn("是否必须猜关键事实，或无法验证结果", text)
        self.assertIn("最多新建一份短入口文档", text)
        self.assertIn("不生成治理文档树", text)

    def test_readiness_scenarios_have_zero_or_one_new_file_budget(self) -> None:
        text = reference("project-discovery.md")
        rows = {}
        for line in text.splitlines():
            match = re.match(r"^\| (mature|incomplete|empty|non-blocking gap) \|", line)
            if match:
                rows[match.group(1)] = [cell.strip() for cell in line.strip("|").split("|")]
        self.assertEqual(set(rows), {"mature", "incomplete", "empty", "non-blocking gap"})
        self.assertEqual(rows["mature"][3:5], ["no-op", "0"])
        self.assertEqual(rows["incomplete"][3:5], ["patch existing", "0"])
        self.assertEqual(rows["empty"][3:5], ["create one entry", "1"])
        self.assertEqual(rows["non-blocking gap"][3:5], ["record in findings", "0"])

    def test_readiness_repairs_require_fresh_real_evidence(self) -> None:
        text = reference("project-discovery.md")
        self.assertIn("现有真源链接真实命令/配置", text)
        self.assertIn("fresh reader/command", text)
        self.assertIn("不得为了显得完整再创建同义入口", text)

    def test_ui_work_cannot_reach_write_without_a_selected_contract(self) -> None:
        text = reference("experience-design.md")
        self.assertIn("非 UI 已记录 N/A", SKILL)
        self.assertIn("未选型或缺关键状态时不得进入 Write", text)

    def test_failed_verification_returns_to_work(self) -> None:
        text = reference("verification.md")
        self.assertIn("任一失败就回 Act/Debug 或上游缺口阶段", text)
        self.assertIn("没有 fresh verification 证据，不声称完成", SKILL)

    def test_unauthorized_side_effects_fail_closed(self) -> None:
        text = reference("finish-release.md")
        self.assertIn("必须获得用户对目标和范围的明确授权", text)
        self.assertIn("未授权副作用", reference("verification.md"))


class PrePlanContractTest(unittest.TestCase):
    def test_solution_contract_contains_first_principles_and_delete_test(self) -> None:
        text = reference("solution-design.md")
        for token in ("用户/job", "当前→目标状态", "不变量", "非范围", "删除测试", "可逆性", "回滚点"):
            self.assertIn(token, text)
        self.assertIn("不能把会改变方向的未知丢给 Act", text)
        self.assertIn("才写 ADR", text)

    def test_ux_precedes_visual_direction(self) -> None:
        text = reference("experience-design.md")
        self.assertLess(text.index("journey/flow"), text.index("定义 IA"))
        self.assertLess(text.index("定义 IA"), text.index("2–3 个"))
        for token in ("权限", "空", "加载", "错误", "离线", "reduced-motion", "键盘", "焦点", "长文本"):
            self.assertIn(token, text)

    def test_design_system_patches_existing_truth_before_design_md(self) -> None:
        text = reference("design-system.md")
        self.assertIn("优先补现有设计真源", text)
        self.assertIn("非 UI 任务不得创建空 DESIGN.md", text)
        self.assertIn("代码 tokens 和组件实现仍是数值/行为细节真源", text)

    def test_pre_plan_gate_blocks_write_until_selection(self) -> None:
        contract = (PACKAGE / "templates/pre-plan-contract.md").read_text()
        self.assertEqual(contract.count("- [ ]"), 4)
        self.assertIn("Write fail closed", contract)
        self.assertIn("Act 时再定", contract)
        write = reference("write-plan.md")
        self.assertIn("Solution Contract 已选定", write)
        self.assertIn("Experience Design Contract", write)


class DeliveryLifecycleContractTest(unittest.TestCase):
    def test_write_plan_has_preconditions_dag_scope_and_single_status_owner(self) -> None:
        write = reference("write-plan.md")
        for token in ("Readiness 已通过", "Solution Contract 已选定", "Experience Design Contract", "依赖 DAG", "不得残留 TODO", "整个 Plan 确认"):
            self.assertIn(token, write)
        templates = PACKAGE / "templates"
        registry = "pending / in_progress / completed / blocked"
        self.assertIn(registry, (templates / "task_plan.md").read_text())
        for path in templates.glob("*.md"):
            if path.name != "task_plan.md":
                self.assertNotIn(registry, path.read_text(), path.name)

    def test_act_and_delegation_cover_ready_queue_conflicts_review_and_solo(self) -> None:
        act = reference("act-plan.md")
        delegation = reference("delegation.md")
        for token in ("source fingerprint", "文件域", "共享资源", "授权边界", "Ready Queue"):
            self.assertIn(token, act)
        for token in ("Ready Queue", "文件域", "release candidate", "Reviewer", "solo"):
            self.assertIn(token, delegation)

    def test_debugging_order_is_reproduce_to_root_cause_to_regression(self) -> None:
        debug = reference("debugging-recovery.md")
        ordered = ["写出预期", "收集错误", "向上追踪", "验证一个可证伪假设", "修复根因", "重跑复现"]
        positions = [debug.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("条件等待", debug)
        self.assertIn("固定 sleep", debug)
        self.assertIn("单一 typo", debug)

    def test_verification_rejects_stale_partial_or_failed_evidence(self) -> None:
        verify = reference("verification.md")
        for token in ("fresh 运行", "历史绿灯", "部分日志", "exit code", "任一命令非零", "Task、Plan、整体业务门"):
            self.assertIn(token, verify)

    def test_finish_reports_actual_state_and_requires_authorization(self) -> None:
        finish = reference("finish-release.md")
        for token in ("业务结果", "是否可放心使用", "changelog", "commit、push、merge、deploy、delete", "明确授权", "不得伪造"):
            self.assertIn(token, finish)
        self.assertIn("本地已验证、已提交、已推送、已合并、已部署", finish)


if __name__ == "__main__":
    unittest.main()
