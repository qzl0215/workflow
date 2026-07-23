from __future__ import annotations

import re
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SKILL = (PACKAGE / "SKILL.md").read_text()
README = (PACKAGE / "README.md").read_text()
CHANGELOG = (PACKAGE / "CHANGELOG.md").read_text()
REFERENCES = PACKAGE / "references"
TASK_PLAN_TEMPLATE = (PACKAGE / "templates/task_plan.md").read_text()

STAGES = [
    "需求澄清",
    "选定方案",
    "拆成任务",
    "执行任务",
    "验收交付",
    "提炼经验",
    "回灌改进",
]
UNKNOWN_ROUTES = ["事实可查", "取舍待定", "假设待验", "外部待解"]
PRIMARY_REFERENCES = [
    "understand-goal.md",
    "decide-solution.md",
    "plan-tasks.md",
    "execute-tasks.md",
    "verify-deliver.md",
    "learn-review.md",
    "evolve-system.md",
]
HARNESS_REFERENCES = [
    "challenge-decisions.md",
    "shape-experience.md",
    "maintain-design.md",
    "coordinate-agents.md",
    "merge-parallel-work.md",
    "fix-failures.md",
    "handoff-context.md",
]
SCHEMA_HEADINGS = [
    "## 何时进入",
    "## 已知输入",
    "## 深度判断",
    "## 核心动作",
    "## 写入真源",
    "## 停止 / 通过",
    "## 失败回路 / 能力缺口",
]
LEGACY_STAGES = re.compile(
    r"(?<![A-Za-z0-9_])(?:看清目标|Intake|Clarify|Readiness|Solution|Experience|Write|Act|Debug|Verify|Finish)(?![A-Za-z0-9_])"
)


def reference(name: str) -> str:
    return (REFERENCES / name).read_text()


class CanonicalStageContractTest(unittest.TestCase):
    def test_first_stage_is_requirement_clarification(self) -> None:
        self.assertIn("计划：需求澄清 → 选定方案 → 拆成任务", SKILL)
        self.assertIn("需求澄清 → 选定方案 → 拆成任务 → 执行任务 → 验收交付 → 提炼经验 → 回灌改进", SKILL)
        self.assertNotIn("## 看清目标中的四路未知", SKILL)

    def test_three_phases_and_seven_stage_order_are_the_only_mainline(self) -> None:
        self.assertIn("计划：需求澄清 → 选定方案 → 拆成任务", SKILL)
        self.assertIn("执行：执行任务 → 验收交付", SKILL)
        self.assertIn("复盘：提炼经验 → 回灌改进", SKILL)
        self.assertIn("需求澄清 → 选定方案 → 拆成任务 → 执行任务 → 验收交付 → 提炼经验 → 回灌改进", SKILL)

        rows: dict[str, list[str]] = {}
        stage_pattern = "|".join(STAGES)
        for line in SKILL.splitlines():
            match = re.match(rf"^\| ({stage_pattern}) \|", line)
            if match:
                rows[match.group(1)] = [cell.strip() for cell in line.strip("|").split("|")]
        self.assertEqual(list(rows), STAGES)
        for stage, cells in rows.items():
            self.assertEqual(len(cells), 5, stage)
            self.assertTrue(all(cells), stage)

    def test_stage_has_one_persisted_owner_and_new_writes_use_chinese_only(self) -> None:
        for token in ("只持久化一个 `stage`", "新写入只允许七个中文值", "旧值只在读取边界归一"):
            self.assertIn(token, SKILL)
        self.assertNotRegex(SKILL, LEGACY_STAGES)

    def test_light_work_fast_passes_without_weakening_evidence(self) -> None:
        for token in ("轻任务", "快速通过", "证据驱动检查点", "不降低验收", "不建立项目文档"):
            self.assertIn(token, SKILL)


class UserHandoffContractTest(unittest.TestCase):
    def test_handoff_is_conclusion_first_and_only_when_people_are_needed(self) -> None:
        self.assertIn("## 用户交接", SKILL)
        for token in (
            "只有需要人参与时才交回控制权",
            "连续工作不强制输出阶段导航",
            "`阶段｜n/7 · 阶段名`",
            "结论 → 当前阶段 → 阶段成果 → 风险或待决策（按需）→ 最佳下一步与回复方式",
        ):
            self.assertIn(token, SKILL)

    def test_first_two_stages_use_short_feedback_loops_without_asking_discoverable_facts(self) -> None:
        goal = reference("understand-goal.md")
        solution = reference("decide-solution.md")
        for text in (goal, solution):
            self.assertIn("短反馈回路", text)
            self.assertIn("会改变目标、范围、验收或方向", text)
        self.assertIn("事实可查", goal)
        self.assertIn("不问用户", goal)

    def test_later_stages_continue_until_a_real_handoff_trigger(self) -> None:
        plan = reference("plan-tasks.md")
        execute = reference("execute-tasks.md")
        self.assertIn("完整 Plan 确认", plan)
        for token in ("不因普通进度或 Task 完成停下", "真实 blocker", "新的业务决策"):
            self.assertIn(token, execute)


class StageResultRoutingContractTest(unittest.TestCase):
    def test_task_plan_has_one_portable_route_truth(self) -> None:
        for token in (
            "## 阶段成果路由",
            "| 阶段 | 目标类型 | 项目相对入口 |",
            "document / visual / collection",
            "每个已完成阶段最多一个活动入口",
            "只保存项目相对路径",
        ):
            self.assertIn(token, TASK_PLAN_TEMPLATE)

    def test_route_selection_and_invalidation_are_business_driven(self) -> None:
        for token in (
            "单一业务成果直达文件",
            "选定方案优先指向已选视觉预览",
            "多个同等重要成果指向已有目录",
            "宿主不能打开目录时",
            "`index.md`",
            "移除受影响的下游活动入口",
            "findings/progress",
        ):
            self.assertIn(token, SKILL)

    def test_stage_result_links_are_runtime_resolved_plain_markdown(self) -> None:
        for token in (
            "交接时按当前宿主解析",
            "不得保存机器绝对路径",
            "不得保存 `file://`",
            "当前和待开始阶段不链接",
        ):
            self.assertIn(token, SKILL)
        link_line = next(line for line in SKILL.splitlines() if line.startswith("真实交接格式："))
        self.assertRegex(link_line, r"\[需求澄清\]\([^)]+\)")
        self.assertNotIn("`", link_line)
        self.assertEqual(SKILL[: SKILL.index(link_line)].count("```") % 2, 0)
        self.assertNotRegex(SKILL, r"`[^`\n]*\[[^\]]+\]\([^)]+\)[^`\n]*`")


class CrossHostHandoffContractTest(unittest.TestCase):
    def test_native_views_are_optional_derived_enhancement(self) -> None:
        for token in (
            "原生 Plan/Task 视图",
            "零配置可用时",
            "派生展示",
            "正式阶段或任务状态变化时",
            "不可用时静默使用文本交接",
            "不修改用户设置",
            "不得成为第二状态真源",
        ):
            self.assertIn(token, SKILL)

    def test_host_rendering_has_file_visual_directory_and_plain_text_fallbacks(self) -> None:
        for token in (
            "支持本地 Markdown 链接",
            "只能识别文件路径",
            "视觉文件使用宿主预览",
            "目录不支持时打开 `index.md`",
            "自定义 URL scheme",
            "ANSI 控制码",
            "跨平台 Widget",
        ):
            self.assertIn(token, SKILL)

    def test_readme_shows_three_conclusion_first_handoffs_with_reply_options(self) -> None:
        for heading in ("### 场景一：方向决策", "### 场景二：阻断或授权", "### 场景三：最终完成"):
            self.assertIn(heading, README)
        for token in (
            "结论｜",
            "阶段｜2/7 · 选定方案",
            "阶段｜5/7 · 验收交付",
            "阶段｜7/7 · 回灌改进",
            "状态｜已完成",
            "最佳下一步｜",
            "回复“采用推荐方案”",
            "回复“授权发布”或“保持本地已验证”",
            "回复“继续下一目标”或直接提出新任务",
        ):
            self.assertIn(token, README)
        self.assertNotIn("阶段｜8/8", README)
        linked_lines = [line for line in README.splitlines() if "回看｜" in line]
        self.assertEqual(len(linked_lines), 3)
        for line in linked_lines:
            self.assertIn("](", line)
            self.assertNotIn("`", line)


class UnknownAndHarnessContractTest(unittest.TestCase):
    def test_four_unknown_routes_are_explicit_and_are_not_stages(self) -> None:
        rows: dict[str, list[str]] = {}
        route_pattern = "|".join(UNKNOWN_ROUTES)
        for line in SKILL.splitlines():
            match = re.match(rf"^\| ({route_pattern}) \|", line)
            if match:
                rows[match.group(1)] = [cell.strip() for cell in line.strip("|").split("|")]
        self.assertEqual(list(rows), UNKNOWN_ROUTES)
        for route, cells in rows.items():
            self.assertEqual(len(cells), 4, route)
            self.assertTrue(all(cells), route)
        self.assertIn("四路未知不是阶段", SKILL)

    def test_harness_depth_is_automatic_explainable_and_gate_safe(self) -> None:
        for token in (
            "H0",
            "H1",
            "H2",
            "H3",
            "AI 按动作自动选择",
            "H2/H3",
            "说明为什么需要加深",
            "硬门不得降级",
            "可用能力下降时只改变手段，不降低判断深度",
        ):
            self.assertIn(token, SKILL)

    def test_grill_is_a_dual_entry_decision_harness(self) -> None:
        text = reference("challenge-decisions.md")
        for token in ("问题入口", "方案入口", "Grill", "一次尽量合并关键问题", "会改变方向"):
            self.assertIn(token, text)


class ReferenceArchitectureTest(unittest.TestCase):
    def test_reference_set_is_exactly_seven_owners_and_seven_harnesses(self) -> None:
        actual = sorted(path.name for path in REFERENCES.glob("*.md"))
        expected = sorted(PRIMARY_REFERENCES + HARNESS_REFERENCES)
        self.assertEqual(actual, expected)

        for name in expected:
            self.assertEqual(SKILL.count(f"`references/{name}`"), 1, name)

    def test_every_reference_uses_the_seven_section_schema(self) -> None:
        for name in PRIMARY_REFERENCES + HARNESS_REFERENCES:
            text = reference(name)
            positions = [text.index(heading) for heading in SCHEMA_HEADINGS]
            self.assertEqual(positions, sorted(positions), name)
            self.assertEqual(sum(text.count(heading) for heading in SCHEMA_HEADINGS), 7, name)

    def test_formal_references_do_not_reintroduce_legacy_stage_words(self) -> None:
        for name in PRIMARY_REFERENCES + HARNESS_REFERENCES:
            self.assertNotRegex(reference(name), LEGACY_STAGES, name)


class PlanningAndExecutionContractTest(unittest.TestCase):
    def test_goal_owner_routes_unknowns_and_protects_document_budget(self) -> None:
        text = reference("understand-goal.md")
        for token in (
            "事实可查",
            "取舍待定",
            "假设待验",
            "外部待解",
            "价值门 A",
            "最多一份短入口文档",
            "不能自行发现的关键问题",
        ):
            self.assertIn(token, text)

    def test_solution_owner_uses_dynamic_experts_and_ai_roi(self) -> None:
        text = reference("decide-solution.md")
        for token in (
            "90 分最终画面",
            "动态专家森林",
            "不写死专家头衔",
            "独立发散",
            "交叉质询",
            "价值门 B",
            "AI 高 ROI",
            "删除测试",
        ):
            self.assertIn(token, text)

    def test_plan_owner_uses_p9_dag_and_file_isolation(self) -> None:
        text = reference("plan-tasks.md")
        for token in (
            "P9 六要素",
            "目标",
            "输入",
            "输出",
            "验收",
            "文件域",
            "依赖",
            "Plan 总 DAG",
            "Task 局部 DAG",
            "Ready Queue",
            "人的工作天数",
            "AI 执行路径",
        ):
            self.assertIn(token, text)

    def test_execute_owner_keeps_scope_and_fresh_task_evidence(self) -> None:
        text = reference("execute-tasks.md")
        for token in (
            "单 Task 循环",
            "source fingerprint",
            "fresh evidence",
            "范围变化分流",
            "Ready Queue",
            "不在执行任务中偷做上游决策",
        ):
            self.assertIn(token, text)

    def test_continuous_delivery_authorization_advances_ready_tasks_without_stopping(self) -> None:
        text = reference("execute-tasks.md")
        for token in (
            "持续推进授权",
            "自动进入下一个 Ready Task",
            "所有纳入 Plan 验收完成",
            "真实 blocker",
            "新的业务决策",
        ):
            self.assertIn(token, text)


class VerificationReviewAndEvolutionContractTest(unittest.TestCase):
    def test_evidence_acceptance_precedes_authorized_delivery(self) -> None:
        text = reference("verify-deliver.md")
        evidence = text.index("证据验收门")
        delivery = text.index("授权交付门")
        self.assertLess(evidence, delivery)
        for token in (
            "fresh 运行",
            "exit code",
            "Task → Plan → 整体业务",
            "commit、push、merge、deploy、delete",
            "明确授权",
            "本地已验证",
            "不得伪造",
        ):
            self.assertIn(token, text)

    def test_review_is_tiered_and_can_be_a_no_op(self) -> None:
        text = reference("learn-review.md")
        for token in (
            "轻任务：跳过",
            "标准任务：条件触发",
            "项目任务：最小偏差检查",
            "fresh-agent 检查",
            "no-op",
            "下次更少踩坑",
        ):
            self.assertIn(token, text)

    def test_evolution_has_evidence_promotion_and_authority_boundaries(self) -> None:
        text = reference("evolve-system.md")
        for token in (
            "两次独立复现",
            "一次严重、系统性且可复现的问题",
            "唯一 owner",
            "失败验收",
            "维护 ROI 为正",
            "用户明确偏好",
            "推断只留在 findings",
            "独立进化 Plan",
            "本地、可逆、可验证",
            "外部副作用仍需明确授权",
        ):
            self.assertIn(token, text)


class IntegratedReleaseContractTest(unittest.TestCase):
    def test_integrated_release_is_a_required_gate_when_delivery_is_requested(self) -> None:
        delivery = reference("verify-deliver.md")
        for token in (
            "### 集成发布门",
            "不是可选收尾",
            "本地已验证只是中间状态",
            "提交、合并和发布",
            "提交合并发布",
        ):
            self.assertIn(token, delivery)

    def test_release_contract_is_derived_from_project_truth(self) -> None:
        delivery = reference("verify-deliver.md")
        for token in (
            "项目规则 → 部署/发布文档 → CI/脚本 → 仓库配置",
            "release contract",
            "remote、目标分支、集成方式、版本/tag/release、部署入口、回滚和发布后 smoke",
            "不凭通用 workflow 猜平台命令",
        ):
            self.assertIn(token, delivery)

    def test_integration_uses_latest_target_and_proves_real_delivery_state(self) -> None:
        delivery = reference("verify-deliver.md")
        for token in (
            "fetch 最新目标",
            "PR/MR 不是默认步骤",
            "必需 CI",
            "fast-forward",
            "禁止 force",
            "集成后 fresh 重验",
            "真实远端与发布状态",
            "不逐步重复确认",
        ):
            self.assertIn(token, delivery)
        release_row = next(line for line in SKILL.splitlines() if line.startswith("| 验收交付 |"))
        self.assertIn("项目发布真源", release_row)
        self.assertIn("集成发布", release_row)

    def test_humans_approve_business_and_authority_not_code(self) -> None:
        delivery = reference("verify-deliver.md")
        for token in (
            "默认用户不审代码",
            "业务结果、风险与外部授权",
            "AI 负责 diff 自审",
            "不得要求用户确认代码",
        ):
            self.assertIn(token, delivery)
        self.assertIn("用户不承担代码审阅", README)

    def test_release_graph_keeps_only_steps_with_independent_value(self) -> None:
        delivery = reference("verify-deliver.md")
        for token in (
            "最小发布图",
            "PR/MR 不是默认步骤",
            "分支保护、必需 CI、项目规则或真实 reviewer",
            "没有独立价值的节点必须删除",
            "一个平台动作安全完成",
        ):
            self.assertIn(token, delivery)

    def test_public_explanation_distinguishes_local_green_from_real_delivery(self) -> None:
        for token in (
            "本地已验证 ≠ 已交付",
            "项目部署/发布文档",
            "提交 → 合并 → 发布 → 发布后 smoke",
            "集成发布",
        ):
            self.assertIn(token, README)
        self.assertIn("Restored the integrated release gate", CHANGELOG)


class SupportingHarnessContractTest(unittest.TestCase):
    def test_experience_uses_fidelity_ladder(self) -> None:
        text = reference("shape-experience.md")
        self.assertIn("线框图", text)
        self.assertIn("高保真", text)
        self.assertLess(text.index("线框图"), text.index("高保真"))
        for token in ("journey/flow", "空", "加载", "错误", "reduced-motion", "键盘", "焦点"):
            self.assertIn(token, text)

    def test_design_truth_is_only_created_for_stable_reuse(self) -> None:
        text = reference("maintain-design.md")
        for token in ("优先补现有设计真源", "稳定复用价值", "非 UI 任务不得创建", "代码 tokens"):
            self.assertIn(token, text)

    def test_agent_coordination_separates_expert_views_from_implementation(self) -> None:
        text = reference("coordinate-agents.md")
        for token in (
            "只读独立视角",
            "确认计划后",
            "文件域隔离",
            "P9",
            "Reviewer",
            "solo",
        ):
            self.assertIn(token, text)

    def test_parallel_merge_restores_late_merger_responsibility(self) -> None:
        text = reference("merge-parallel-work.md")
        for token in (
            "独立 worktree",
            "创建前先 fetch 最新目标分支",
            "项目发布契约决定是否使用 CI 或 MR",
            "允许修改同一原始文件",
            "合并队列",
            "后合并者",
            "rebase",
            "MERGE_NOTE",
            "文本冲突",
            "语义冲突",
            "rebase --continue",
            "不得 rebase --abort",
            "前提假设、时间先后、不变量",
            "不得整文件选边",
            "双方验证命令",
            "项目规则",
            "长期授权",
        ):
            self.assertIn(token, text)

    def test_failure_loop_and_handoff_remain_bounded(self) -> None:
        failure = reference("fix-failures.md")
        ordered = ["写出预期", "收集错误", "向上追踪", "可证伪假设", "修复根因", "重跑复现"]
        positions = [failure.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("固定 sleep", failure)

        handoff = reference("handoff-context.md")
        for token in ("L0", "L1", "L2", "L3", "L4", "Task capsule", "fail closed"):
            self.assertIn(token, handoff)


if __name__ == "__main__":
    unittest.main()
