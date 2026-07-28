from __future__ import annotations

import re
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SKILL = (PACKAGE / "SKILL.md").read_text()
README = (PACKAGE / "README.md").read_text()
CHANGELOG = (PACKAGE / "CHANGELOG.md").read_text()
REFERENCES = PACKAGE / "references"
ADAPTERS = PACKAGE / "adapters"
METHODS = PACKAGE / "methods"
TASK_PLAN_TEMPLATE = (PACKAGE / "templates/task_plan.md").read_text()
FINDINGS_TEMPLATE = (PACKAGE / "templates/findings.md").read_text()
TASK_OWNER_TEMPLATE = (PACKAGE / "templates/task-owner-prompt.md").read_text()

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
    "verify-results.md",
    "learn-review.md",
    "evolve-system.md",
]
HARNESS_REFERENCES = [
    "shape-experience.md",
    "maintain-design.md",
    "coordinate-agents.md",
    "fix-failures.md",
    "handoff-context.md",
    "deliver-release.md",
]
ADAPTER_FILES = ["merge-parallel-work.md"]
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


def method_pack(name: str) -> str:
    return (METHODS / name).read_text()


def adapter(name: str) -> str:
    return (ADAPTERS / name).read_text()


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
        for token in ("默认快刀", "轻任务", "快速通过", "证据驱动检查点", "不降低验收", "不建立项目文档"):
            self.assertIn(token, SKILL)
        for token in (
            "文件数量、项目重要、常规发布或修改 workflow 自身",
            "不能单独触发升级",
            "难逆产品或架构决策",
            "数据迁移、权限、安全或生产风险",
            "跨系统兼容性",
            "连续失败或证据冲突",
        ):
            self.assertIn(token, SKILL)


class UserHandoffContractTest(unittest.TestCase):
    def test_handoff_is_only_when_people_are_needed_and_keeps_two_action_exits(self) -> None:
        self.assertIn("## 用户交接", SKILL)
        for token in (
            "只有需要人参与时才交回控制权",
            "建议下一步｜",
            "回复建议｜",
            "下一 Ready",
            "不得替代",
        ):
            self.assertIn(token, SKILL)

    def test_changed_state_snapshot_is_event_driven_non_blocking_and_deduplicated(self) -> None:
        for token in (
            "状态发生实质变化",
            "下一条可见消息",
            "状态未变化",
            "不重复",
            "播报后继续工作",
            "进度｜■■■◆□□□ 4/7 · 执行任务",
        ):
            self.assertIn(token, SKILL)

    def test_snapshot_uses_clickable_reference_titles_results_and_compact_path(self) -> None:
        for token in (
            "一级中文标题",
            "成果｜",
            "✓ P01 → ● P02 / T03 → ○ P03",
            "不展示 Ready 队列",
            "不探测宿主",
            "不生成 DAG 视觉",
        ):
            self.assertIn(token, SKILL)
        skill_line = next(line for line in SKILL.splitlines() if line.startswith("技能｜"))
        self.assertIn("[执行任务](references/execute-tasks.md)", skill_line)
        self.assertIn("[修复失败](references/fix-failures.md)", skill_line)
        self.assertNotIn("`", skill_line)

    def test_first_two_stages_use_short_feedback_loops_without_asking_discoverable_facts(self) -> None:
        goal = reference("understand-goal.md")
        solution = reference("decide-solution.md")
        for text in (goal, solution):
            self.assertIn("短反馈回路", text)
            self.assertIn("会改变目标、范围、验收或方向", text)
        self.assertIn("事实可查", goal)
        self.assertIn("不问用户", goal)

    def test_solution_confirmation_exposes_the_decision_causal_chain(self) -> None:
        solution = reference("decide-solution.md")
        for token in (
            "方案确认因果链",
            "关键中间动作",
            "正面效果",
            "负面后果",
            "用户需要接受的取舍",
            "不展开普通实现步骤",
            "轻量、无实质取舍",
        ):
            self.assertIn(token, solution)
        self.assertIn(
            "关键中间动作 → 正面效果与负面后果 → 用户需要接受的取舍",
            solution,
        )
        for token in ("关键动作｜", "正面效果｜", "负面后果｜"):
            self.assertIn(token, README)

    def test_recommended_contract_is_the_default_discovery_interface(self) -> None:
        goal = reference("understand-goal.md")
        requirement_row = next(line for line in SKILL.splitlines() if line.startswith("| 需求澄清 |"))
        for token in (
            "需求成熟度硬门",
            "推荐需求契约（待确认）",
            "默认需求发现界面",
            "默认最多一批高价值问题",
            "只有仍存在会改变目标、范围、验收或授权的未知",
            "沉默不等于确认",
            "用户 / 场景 / 现状痛点",
            "目标结果与可观察成功标准",
            "范围与非范围",
            "关键约束、优先级与取舍",
            "授权边界与责任人",
        ):
            self.assertIn(token, goal)
        for token in ("需求成熟度硬门", "关键用户判断已有回答"):
            self.assertIn(token, requirement_row)
        for token in (
            "## 需求成熟度硬门",
            "## 关键追问",
            "答案会改变什么",
            "用户回答 / 明确延期",
        ):
            self.assertIn(token, FINDINGS_TEMPLATE)

    def test_standard_and_project_requirements_need_sufficient_research_and_explicit_contract_confirmation(self) -> None:
        goal = reference("understand-goal.md")
        requirement_row = next(line for line in SKILL.splitlines() if line.startswith("| 需求澄清 |"))
        for token in (
            "项目真源 → 已连接工具与数据 → 官方一手来源 → 最小实验",
            "调研充分性硬门",
            "目标、范围、方案或风险",
            "新增证据",
            "需求契约",
            "明确确认",
            "标准任务",
            "项目任务",
            "轻任务",
        ):
            self.assertIn(token, goal)
        for token in ("调研充分性硬门", "需求契约已获明确确认"):
            self.assertIn(token, requirement_row)
        for token in ("## 调研充分性硬门", "停止依据", "需求契约确认"):
            self.assertIn(token, FINDINGS_TEMPLATE)

    def test_current_state_research_binds_one_fresh_snapshot_before_discovery(self) -> None:
        goal = reference("understand-goal.md")
        execution = reference("execute-tasks.md")
        for token in (
            "依赖可变项目现状",
            "调研前",
            "项目定义的 freshness 机制",
            "固定 source fingerprint",
        ):
            self.assertIn(token, SKILL)
        for token in (
            "新需求",
            "调研前",
            "刷新目标真源",
            "固定 source fingerprint",
            "纯概念问答",
            "不按落后提交数设置阈值",
            "交付前",
        ):
            self.assertIn(token, goal)
        for token in ("调研入口已绑定", "同一现场", "不重复创建"):
            self.assertIn(token, execution)

    def test_requirement_discovery_uses_one_high_value_exception_batch(self) -> None:
        goal = reference("understand-goal.md")
        for token in (
            "默认最多一批高价值问题",
            "完整推荐",
            "关键例外",
            "目标、范围、验收或授权",
            "第二批",
            "实质缺口",
        ):
            self.assertIn(token, goal)
        self.assertNotIn("不设置总问题数上限", goal)

    def test_requirement_clarification_proactively_finds_the_underlying_goal(self) -> None:
        goal = reference("understand-goal.md")
        metadata = SKILL.split("---", 2)[1]
        for token in (
            "表面请求",
            "真实用户结果",
            "不要求用户先说“澄清需求”",
        ):
            self.assertIn(token, metadata)
        for token in (
            "不依赖用户说出“澄清需求”",
            "表面请求与真实用户结果之间",
            "主动进入需求澄清",
        ):
            self.assertIn(token, SKILL)
        for token in (
            "表面请求 → 当前痛点 → 本质目标 → 成功信号",
            "1–3 个最高杠杆问题",
            "问题杠杆",
            "当前理解或推荐",
            "为什么做、真正要改变什么、什么结果最重要",
        ):
            self.assertIn(token, goal)
        for token in (
            "不等你先说“澄清需求”",
            "表面请求 → 当前痛点 → 本质目标 → 成功信号",
            "1–3 个最高杠杆问题",
        ):
            self.assertIn(token, README)
        for token in (
            "## 目标链",
            "表面请求",
            "当前痛点",
            "本质目标",
            "成功信号",
            "当前理解或推荐",
            "默认只保留 1–3 个最高杠杆问题",
        ):
            self.assertIn(token, FINDINGS_TEMPLATE)

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
            "没有视觉方案",
            "多个同等重要成果指向已有目录",
            "移除受影响的下游活动入口",
            "findings/progress",
        ):
            self.assertIn(token, SKILL)

    def test_stage_result_links_are_plain_markdown_without_host_probing(self) -> None:
        for token in (
            "解析为普通 Markdown 链接",
            "不探测宿主",
            "不得保存机器绝对路径",
            "不得保存 `file://`",
            "当前和待开始阶段不链接",
        ):
            self.assertIn(token, SKILL)
        link_line = next(line for line in SKILL.splitlines() if line.startswith("成果｜"))
        self.assertRegex(link_line, r"\[需求澄清\]\([^)]+\)")
        self.assertNotIn("`", link_line)
        self.assertEqual(SKILL[: SKILL.index(link_line)].count("```") % 2, 0)
        self.assertNotRegex(SKILL, r"`[^`\n]*\[[^\]]+\]\([^)]+\)[^`\n]*`")


class CrossHostHandoffContractTest(unittest.TestCase):
    def test_snapshot_uses_one_text_contract_without_host_probing(self) -> None:
        for token in (
            "普通文本",
            "普通 Markdown",
            "不探测宿主",
            "不生成 DAG 视觉",
            "不建立第二状态真源",
        ):
            self.assertIn(token, SKILL)
        self.assertNotIn("原生 Plan/Task 视图", SKILL)

    def test_markdown_links_keep_portable_result_and_reference_targets(self) -> None:
        for token in (
            "项目相对路径",
            "选定方案优先指向已选视觉预览",
            "没有视觉方案",
            "一级中文标题",
        ):
            self.assertIn(token, SKILL)

    def test_readme_shows_three_state_aware_handoffs_with_two_reply_exits(self) -> None:
        for heading in ("### 场景一：方向决策", "### 场景二：阻断或授权", "### 场景三：最终完成"):
            self.assertIn(heading, README)
        for token in (
            "结论｜",
            "进度｜■◆□□□□□ 2/7 · 选定方案",
            "进度｜■■■■◆□□ 5/7 · 验收交付",
            "进度｜■■■■■■◆ 7/7 · 回灌改进",
            "技能｜",
            "成果｜",
            "状态｜已完成",
            "建议下一步｜",
            "回复建议｜",
            "回复“采用推荐方案”",
            "回复“授权发布”或“保持本地已验证”",
            "回复“继续下一目标”或直接提出新任务",
        ):
            self.assertIn(token, README)
        self.assertNotIn("阶段｜8/8", README)
        self.assertNotIn("最佳下一步｜", README)
        self.assertEqual(README.count("> 建议下一步｜"), 3)
        self.assertEqual(README.count("> 回复建议｜"), 3)
        linked_lines = [line for line in README.splitlines() if "> 成果｜" in line]
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

    def test_reverse_challenge_is_owned_by_requirement_and_solution_instead_of_a_duplicate_harness(self) -> None:
        goal = reference("understand-goal.md")
        solution = reference("decide-solution.md")
        self.assertFalse((REFERENCES / "challenge-decisions.md").exists())
        for token in ("决策树", "回答含糊", "同一编号"):
            self.assertIn(token, goal)
        for token in ("challenger", "交叉质询", "推翻条件", "奥卡姆硬门"):
            self.assertIn(token, solution)


class ReferenceArchitectureTest(unittest.TestCase):
    def test_semantic_owner_harness_and_adapter_registries_are_routed_without_count_equality(self) -> None:
        actual = sorted(path.name for path in REFERENCES.glob("*.md"))
        expected = sorted(PRIMARY_REFERENCES + HARNESS_REFERENCES)
        self.assertEqual(actual, expected)

        for name in expected:
            self.assertEqual(SKILL.count(f"`references/{name}`"), 1, name)
        self.assertEqual(sorted(path.name for path in ADAPTERS.glob("*.md")), ADAPTER_FILES)
        for name in ADAPTER_FILES:
            self.assertEqual(SKILL.count(f"`adapters/{name}`"), 1, name)
        for token in (
            "owner 与 harness 不要求数量相等",
            "独立问题",
            "不同退出条件",
            "唯一触发",
            "低共触发率",
            "单独加载收益",
            "平台机械件归 adapter",
        ):
            self.assertIn(token, SKILL)

    def test_every_reference_uses_the_seven_section_schema(self) -> None:
        for name, text in [
            *((name, reference(name)) for name in PRIMARY_REFERENCES + HARNESS_REFERENCES),
            *((name, adapter(name)) for name in ADAPTER_FILES),
        ]:
            positions = [text.index(heading) for heading in SCHEMA_HEADINGS]
            self.assertEqual(positions, sorted(positions), name)
            self.assertEqual(sum(text.count(heading) for heading in SCHEMA_HEADINGS), 7, name)

    def test_formal_references_do_not_reintroduce_legacy_stage_words(self) -> None:
        for name in PRIMARY_REFERENCES + HARNESS_REFERENCES:
            self.assertNotRegex(reference(name), LEGACY_STAGES, name)
        for name in ADAPTER_FILES:
            self.assertNotRegex(adapter(name), LEGACY_STAGES, name)


class PlanningAndExecutionContractTest(unittest.TestCase):
    def test_project_truth_uses_three_hot_sources_and_conditional_navigation(self) -> None:
        handoff = reference("handoff-context.md")
        index = (PACKAGE / "templates/index.md").read_text()
        progress = (PACKAGE / "templates/progress.md").read_text()
        self.assertFalse((PACKAGE / "templates/pre-plan-contract.md").exists())
        for token in (
            "复杂项目只有真实恢复需求时才启用热真源",
            "简单任务默认零新增项目文档",
            "标准任务默认零新增项目文档",
            "需要持久恢复",
            "一份最小 `task_plan.md`",
            "`task_plan.md`",
            "`findings.md`",
            "`progress.md`",
            "`implementation-plan.md`：仅在",
            "`index.md`：仅在",
            "不新建归档文档",
        ):
            self.assertIn(token, SKILL)
        for token in ("decision receipt", "rolling handoff", "不创建 archive 文档"):
            self.assertIn(token, handoff)
        self.assertIn("不复制原始 stdout", progress)
        self.assertIn("默认列表只登记 `status: active`", index)
        for forbidden in ("生命周期", "当前阶段快照", "活跃 Task", "更新时间"):
            self.assertNotIn(f"| {forbidden} |", index)

    def test_findings_keep_one_current_decision_without_flip_flop_noise(self) -> None:
        goal = reference("understand-goal.md")
        solution = reference("decide-solution.md")
        coordination = reference("coordinate-agents.md")
        handoff = reference("handoff-context.md")

        self.assertIn("同一决策主题只保留一条当前有效的 decision receipt", SKILL)
        for token in (
            "最新目标或要求",
            "高置信",
            "原位重写",
            "不并列保留来回过程",
            "实质风险",
            "先向用户确认",
            "确认后仍只留最终结论",
        ):
            self.assertIn(token, FINDINGS_TEMPLATE)
        for text in (goal, solution):
            self.assertIn("最新目标或要求", text)
            self.assertIn("覆盖旧结论", text)
            self.assertIn("先向用户确认", text)
        self.assertIn("只合并为一条当前 decision receipt", coordination)
        self.assertIn("findings 原位重写同一决策主题的当前 decision receipt", handoff)

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

    def test_solution_owner_selects_minimum_experts_and_routes_one_primary_and_one_challenger_pack(self) -> None:
        text = reference("decide-solution.md")
        for token in (
            "H0/H1 默认单视角",
            "不加载专家或方法包",
            "项目重要或修改 workflow 自身",
            "会改变最终推荐的关键决策",
            "lead + 必要补位 + challenger",
            "独有判断",
            "预期证据",
            "推翻条件",
            "退出条件",
            "H2 默认最多 3 个",
            "H3 默认最多 5 个",
            "影响 × 不确定性 × 难逆性",
            "一个主方法包",
            "一个挑战方法包",
            "每包只运行 1–2 个",
        ):
            self.assertIn(token, text)

    def test_four_method_packs_cover_every_pua_method_once_and_are_lazy_loaded(self) -> None:
        packs = {
            "strategic-value.md": ("P10", "Amazon", "小米"),
            "essence-subtraction.md": ("Tesla", "Apple", "拼多多"),
            "experiment-attack.md": ("字节", "腾讯", "华为", "Netflix"),
            "delivery-compounding.md": ("阿里", "京东", "美团", "百度"),
        }
        combined = "\n".join(method_pack(name) for name in packs)
        for name, methods in packs.items():
            text = method_pack(name)
            self.assertLessEqual(len(text), 7000, name)
            for method in methods:
                self.assertIn(method, text)
        for method in (item for methods in packs.values() for item in methods):
            self.assertEqual(combined.count(method), 1, method)
        for name in packs:
            self.assertEqual(SKILL.count(f"`methods/{name}`"), 1, name)
        self.assertIn("默认只加载一个主方法包和一个挑战方法包", SKILL)

    def test_common_protocol_loading_paths_stay_within_context_budgets(self) -> None:
        root_bytes = (PACKAGE / "SKILL.md").stat().st_size
        requirement_bytes = root_bytes + (REFERENCES / "understand-goal.md").stat().st_size
        method_sizes = sorted((path.stat().st_size for path in METHODS.glob("*.md")), reverse=True)
        solution_bytes = root_bytes + (REFERENCES / "decide-solution.md").stat().st_size + sum(method_sizes[:2])
        self.assertLessEqual(root_bytes, 15_000)
        self.assertLessEqual(requirement_bytes, 23_000)
        self.assertLessEqual(solution_bytes, 24_000)

    def test_final_recommendation_has_a_vetoing_occam_gate_and_material_changes_invalidate_it(self) -> None:
        text = reference("decide-solution.md")
        for token in (
            "奥卡姆硬门",
            "只对最终推荐方案",
            "否决",
            "删除项",
            "最简充分版",
            "额外复杂度的举证",
            "实质修改",
            "旧回执失效",
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

    def test_plan_owner_only_requires_dag_for_real_branching_or_shared_resources(self) -> None:
        text = reference("plan-tasks.md")
        template = (PACKAGE / "templates/task_plan.md").read_text()
        for token in (
            "DAG 触发门",
            "两个以上分支",
            "跨 owner",
            "共享资源",
            "紧凑 Task 表",
            "不得为了形式生成 DAG",
        ):
            self.assertIn(token, text)
        self.assertIn("不满足 DAG 触发门时删除本节", template)

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

    def test_verify_owner_bounds_browser_driver_debugging_without_weakening_evidence(self) -> None:
        text = reference("verify-results.md")
        for token in (
            "两种可见控制方式",
            "90 秒",
            "驱动故障",
            "产品验收",
            "直达 URL",
            "ready 信号",
            "可见业务内容",
            "网络状态",
            "交互本身",
            "明确未覆盖",
            "不得写成产品通过",
        ):
            self.assertIn(token, text)

    def test_mutating_task_requires_one_execution_site_validity_check(self) -> None:
        text = reference("execute-tasks.md")
        for token in (
            "执行现场有效性检查",
            "标记进行中之前",
            "Task 绑定",
            "目标基线",
            "freshness 来源",
            "脏改动归属",
            "新 Task",
            "同一活跃 Task",
            "同一计划链的后续 Task",
            "已被目标吸收",
            "只读诊断",
            "不是新的 stage 或 status",
        ):
            self.assertIn(token, text)
        self.assertNotIn("behind > 0 就 rebase", text)

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
        verification = reference("verify-results.md")
        delivery = reference("deliver-release.md")
        self.assertIn("所有任务必经", verification)
        self.assertIn("结果已经通过验收", delivery)
        self.assertLess(SKILL.index("references/verify-results.md"), SKILL.index("references/deliver-release.md"))

    def test_verification_owner_uses_one_rc_receipt_and_scoped_invalidation(self) -> None:
        text = reference("verify-results.md")
        progress = (PACKAGE / "templates/progress.md").read_text()
        for token in (
            "RC 证据回执",
            "command-scoped source tree/hash + verification command + environment class",
            "路径和 commit 元数据",
            "commit、rebase、复制目录和相同制品",
            "impact set",
            "同一输入不得重复运行",
            "只使受影响证据失效",
            "生产形态预检",
            "cold / warm",
            "真实规模",
            "资源峰值",
            "payload / 缓存 / 序列化",
        ):
            self.assertIn(token, text)
        for token in ("RC receipt", "是否复用", "耗时"):
            self.assertIn(token, progress)
        for token in (
            "fresh 运行",
            "exit code",
            "Task → Plan → 整体业务",
            "本地已验证",
            "不能用授权",
            "未覆盖项",
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

    def test_high_actual_execution_cost_forces_review_before_completion(self) -> None:
        verification = reference("verify-results.md")
        delivery = reference("deliver-release.md")
        review = reference("learn-review.md")

        for token in (
            "收尾复盘门",
            "完成前判断是否复盘",
        ):
            self.assertIn(token, SKILL)
        for token in ("收尾复盘门", "严格超过 1 小时", "严格超过 200 万", "没有可靠遥测时不猜"):
            self.assertIn(token, README)
        for token in (
            "实际执行时间严格超过 1 小时",
            "任务累计 token 严格超过 200 万",
            "等待用户、审批和纯监控等待",
            "平台没有可靠遥测时不猜",
            "no-op",
        ):
            self.assertIn(token, review)
        for text in (verification, delivery):
            self.assertIn("收尾复盘门", text)
            self.assertIn("不得直接完成", text)

    def test_confirmed_complete_evolution_proposal_executes_without_duplicate_confirmation(self) -> None:
        evolution = reference("evolve-system.md")
        for token in (
            "完整回灌提案",
            "确认前不得写入",
            "一次明确确认",
            "直接进入回灌实施",
            "不重复索取 Plan 确认",
        ):
            self.assertIn(token, evolution)
        for token in ("完整回灌提案", "确认前不写入", "一次明确确认", "不再重复索取 Plan 确认"):
            self.assertIn(token, README)

    def test_evolution_has_evidence_promotion_and_authority_boundaries(self) -> None:
        text = reference("evolve-system.md")
        self.assertNotIn("两次独立复现", text)
        self.assertNotIn("复现次数", text)
        for token in (
            "模型判断",
            "奥卡姆剃刀",
            "最小充分路径",
            "痛点问题",
            "推断需求",
            "最小改造",
            "预期价值",
            "接受 / 调整 / 暂不做",
            "完整回灌提案",
            "完整 Plan",
            "no-op",
            "唯一 owner",
            "失败验收",
            "外部副作用仍需明确授权",
        ):
            self.assertIn(token, text)

    def test_accepted_evolution_routes_to_the_truth_owner_without_hiding_normal_gates(self) -> None:
        evolution = reference("evolve-system.md")
        planning = reference("plan-tasks.md")
        execution = reference("execute-tasks.md")
        for token in (
            "原验收未满足",
            "修正原 P/T",
            "新的用户结果",
            "零距离 handoff",
            "side-task capsule",
            "无法唯一定位",
            "唯一真源",
            "fail closed",
            "来源任务保持“回灌改进”",
            "目标任务从“拆成任务”开始",
            "handoff 提示词生成不算完成",
            "实际变更与 fresh 验证",
        ):
            self.assertIn(token, evolution)
        for token in ("来源：原始需求 / 回灌提案 / 外部 handoff", "新的用户结果追加新 Plan"):
            self.assertIn(token, planning + TASK_PLAN_TEMPLATE)
        self.assertIn("原验收未满足时重开原 Task", execution)

    def test_root_contract_presents_evolution_as_a_user_decision_not_an_automatic_write(self) -> None:
        evolution_row = next(line for line in SKILL.splitlines() if line.startswith("| 回灌改进 |"))
        for token in ("回灌提案", "用户确认", "目标 owner"):
            self.assertIn(token, evolution_row)
        self.assertIn("提案不等于写入授权", SKILL)


class IntegratedReleaseContractTest(unittest.TestCase):
    def test_final_report_shows_three_business_delivery_states_without_internal_ids(self) -> None:
        delivery = reference("deliver-release.md")
        for token in (
            "代码完成｜",
            "合并完成｜",
            "线上生效｜",
            "三项都出现",
            "不得展示提交哈希",
            "精确技术标识只写",
        ):
            self.assertIn(token, delivery)
        final_scenario = README.split("### 场景三：最终完成", 1)[1].split("## ", 1)[0]
        for token in ("代码完成｜", "合并完成｜", "线上生效｜"):
            self.assertIn(token, final_scenario)
        self.assertNotRegex(final_scenario, r"\b[0-9a-f]{7,40}\b")

    def test_integrated_release_is_a_required_gate_when_delivery_is_requested(self) -> None:
        delivery = reference("deliver-release.md")
        for token in (
            "集成发布不是可选收尾",
            "本地已验证只是中间状态",
            "commit、push、merge",
            "授权交付目标",
        ):
            self.assertIn(token, delivery)

    def test_release_contract_is_derived_from_project_truth(self) -> None:
        delivery = reference("deliver-release.md")
        for token in (
            "项目规则 → 部署/发布文档 → CI/脚本 → 仓库配置",
            "release contract",
            "remote、目标分支、集成方式、版本/tag/release、部署入口、回滚和发布后 smoke",
            "通用 workflow 不猜平台",
        ):
            self.assertIn(token, delivery)

    def test_integration_uses_latest_target_and_proves_real_delivery_state(self) -> None:
        delivery = reference("deliver-release.md")
        for token in (
            "fetch 最新目标",
            "PR/MR 只在",
            "必需 CI",
            "fast-forward",
            "禁止 force",
            "内容等价检查",
            "每个唯一最终源码内容最多一次全量验证",
            "核对真实远端与发布状态",
            "不逐步重复确认",
        ):
            self.assertIn(token, delivery)
        release_row = next(line for line in SKILL.splitlines() if line.startswith("| 验收交付 |"))
        self.assertIn("按需加载项目发布真源", release_row)
        self.assertIn("条件交付", release_row)

    def test_delivery_records_workspace_disposition_without_automatic_cleanup(self) -> None:
        delivery = reference("deliver-release.md")
        for token in (
            "现场处置",
            "保留只读",
            "等待授权清理",
            "继续同一 Task",
            "不得绑定新 Task",
        ):
            self.assertIn(token, delivery)

    def test_semantic_response_changes_verify_persistent_cache_upgrade_paths(self) -> None:
        delivery = reference("verify-results.md")
        for token in (
            "响应身份、排序、归属或过滤语义",
            "跨刷新持久缓存",
            "版本化、失效或兼容迁移",
            "带旧缓存的升级路径",
            "只测空缓存不算完成",
            "无持久缓存不增加此门",
        ):
            self.assertIn(token, delivery)

    def test_humans_approve_business_and_authority_not_code(self) -> None:
        delivery = reference("verify-results.md")
        for token in (
            "默认用户不审代码",
            "业务结果和风险",
            "AI 负责 diff 自审",
            "不把代码判断转嫁给非技术用户",
        ):
            self.assertIn(token, delivery)
        self.assertIn("用户不承担代码审阅", README)

    def test_release_graph_keeps_only_steps_with_independent_value(self) -> None:
        delivery = reference("deliver-release.md")
        for token in (
            "定向测试 → 一次源码全量测试 → commit/rebase → 内容等价检查 → 发布同一制品 → 安装烟测",
            "真实环境类别",
            "最小发布图",
            "PR/MR 只在",
            "分支保护、必需 CI、项目规则或真实 reviewer 要求",
            "没有独立价值的节点删除",
            "一个平台动作安全完成时合并",
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

    def test_visual_work_uses_three_progressive_decision_gates(self) -> None:
        experience = reference("shape-experience.md")
        solution = reference("decide-solution.md")
        for text in (experience, solution, README):
            for token in ("方向粗选", "方案精修", "确认开动"):
                self.assertIn(token, text)
            self.assertLess(text.index("方向粗选"), text.index("方案精修"))
            self.assertLess(text.index("方案精修"), text.index("确认开动"))

        for token in (
            "三个静态视觉粗稿",
            "同批",
            "并行",
            "只精修一个方向",
            "模拟数据",
            "不连接真实数据",
            "明确指定方向",
            "极端 fixture",
        ):
            self.assertIn(token, experience)

    def test_design_truth_is_only_created_for_stable_reuse(self) -> None:
        text = reference("maintain-design.md")
        for token in ("优先补现有设计真源", "稳定复用价值", "非 UI 任务不得创建", "代码 tokens"):
            self.assertIn(token, text)

    def test_agent_coordination_separates_expert_views_from_implementation(self) -> None:
        text = reference("coordinate-agents.md")
        for token in (
            "默认 solo",
            "独立 Reviewer 不是默认门",
            "只读独立视角",
            "确认计划后",
            "文件域隔离",
            "P9",
            "Reviewer",
            "solo",
        ):
            self.assertIn(token, text)

    def test_parallel_merge_restores_late_merger_responsibility(self) -> None:
        text = adapter("merge-parallel-work.md")
        for token in (
            "独立 worktree",
            "fetch 最新目标",
            "合并队列",
            "后合并者",
            "rebase",
            "MERGE_NOTE",
            "语义冲突",
            "不得整文件选边",
            "--continue",
            "内容等价时复用",
            "不授予外部动作权限",
        ):
            self.assertIn(token, text)

    def test_final_process_occam_gate_removes_cost_without_new_reports(self) -> None:
        verification = reference("verify-results.md")
        for token in (
            "六问流程奥卡姆门",
            "专家会诊",
            "subagent",
            "方法包",
            "新增文档",
            "新证据",
            "恢复能力",
            "不创建独立报告",
        ):
            self.assertIn(token, verification)

    def test_failure_loop_and_handoff_remain_bounded(self) -> None:
        failure = reference("fix-failures.md")
        ordered = ["写出预期", "收集错误", "向上追踪", "可证伪假设", "修复根因", "重跑复现"]
        positions = [failure.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("固定 sleep", failure)

        handoff = reference("handoff-context.md")
        for token in ("L0", "L1", "L2", "L3", "L4", "Task capsule", "fail closed"):
            self.assertIn(token, handoff)
        for token in ("执行现场", "Task 绑定", "目标基线", "freshness", "可写性"):
            self.assertIn(token, handoff)
            self.assertIn(token, TASK_OWNER_TEMPLATE)

    def test_handoff_uses_business_boundaries_instead_of_mechanical_thread_budgets(self) -> None:
        handoff = reference("handoff-context.md")
        for token in (
            "上下文同一性门",
            "目标结果",
            "验收",
            "owner",
            "交付边界",
            "独立 side-task capsule",
            "已交付后新缺陷",
            "新的独立用户结果",
            "固定轮次、分钟、token 或压缩次数",
        ):
            self.assertIn(token, handoff)


class RootCauseClosureContractTest(unittest.TestCase):
    def test_local_single_point_failure_uses_a_proportionate_fast_path(self) -> None:
        failure = reference("fix-failures.md")
        for token in (
            "单点 typo",
            "局部条件错误",
            "相称验证",
            "不启动同源影响面审计",
            "不新增项目文档",
        ):
            self.assertIn(token, failure)

    def test_shared_mechanism_failure_requires_a_bounded_homologous_audit(self) -> None:
        failure = reference("fix-failures.md")
        for token in (
            "共享底层机制",
            "系统不变量",
            "同源影响集",
            "定向搜索",
            "消费者",
            "搜索边界",
            "停止依据",
        ):
            self.assertIn(token, failure)
        ordered = ["先分类", "识别不变量", "审计同源影响集", "按证据确定修复范围"]
        positions = [failure.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))

    def test_similar_symptoms_with_different_causes_are_excluded(self) -> None:
        failure = reference("fix-failures.md")
        for token in ("只有症状相似", "根因不同", "排除在当前范围外", "独立缺陷"):
            self.assertIn(token, failure)

    def test_unproven_neighbor_risk_needs_an_experiment_or_residual_risk(self) -> None:
        failure = reference("fix-failures.md")
        for token in (
            "证据不足",
            "最小实验",
            "不得直接扩大改造",
            "残余风险",
            "独立 side task",
        ):
            self.assertIn(token, failure)

    def test_high_risk_foundational_fix_remains_incomplete_after_mitigation(self) -> None:
        failure = reference("fix-failures.md")
        for token in (
            "安全止血",
            "退出条件",
            "审计影响面",
            "删除临时补丁",
            "临时缓解不得描述为根因修复完成",
        ):
            self.assertIn(token, failure)

    def test_shared_mechanism_acceptance_requires_three_evidence_layers(self) -> None:
        verification = reference("verify-results.md")
        for token in (
            "共享机制级修复",
            "症状证据",
            "机制证据",
            "影响面证据",
            "原始页面恢复",
            "验收门不通过",
            "局部单点错误",
            "相称验证",
        ):
            self.assertIn(token, verification)

    def test_root_cause_closure_uses_progress_without_a_second_rule_owner(self) -> None:
        failure = reference("fix-failures.md")
        verification = reference("verify-results.md")
        progress = (PACKAGE / "templates/progress.md").read_text()
        for token in (
            "当前症状",
            "最小复现",
            "已证实根因",
            "被破坏的不变量",
            "同源影响集",
            "检查方法",
            "已纳入修复",
            "明确排除",
            "尚未证实的风险",
            "修复边界",
            "停止依据",
        ):
            self.assertIn(token, progress)
        decision_rule = "根因相同且影响已证实"
        self.assertIn(decision_rule, failure)
        for reader in (verification, progress, SKILL, README):
            self.assertNotIn(decision_rule, reader)
        self.assertIn("不建独立故障报告", failure)


class ProjectKnowledgeRetirementContractTest(unittest.TestCase):
    def test_long_term_knowledge_uses_a_minimal_consumption_and_discovery_gate(self) -> None:
        review = reference("learn-review.md")
        evolution = reference("evolve-system.md")
        findings = (PACKAGE / "templates/findings.md").read_text()
        progress = (PACKAGE / "templates/progress.md").read_text()
        task_plan = (PACKAGE / "templates/task_plan.md").read_text()

        for token in ("未来什么场景会用", "改变什么核心结论或行动", "怎样从问题找到唯一真源"):
            self.assertIn(token, review + evolution)
        gate = "说不清未来何时会用、会改变什么核心结论或行动、怎样从问题找到唯一真源的内容，不进入长期知识层"
        self.assertIn(gate, evolution)
        for reader in (SKILL, README, review, findings, progress, task_plan):
            self.assertNotIn(gate, reader)
        for token in ("use scenario", "decision / action impact", "canonical source", "retrieval path"):
            self.assertIn(token, findings)
        for token in ("消费场景 → 核心决策价值", "唯一真源 / 检索路径"):
            self.assertIn(token, progress)
        for token in ("消费价值与可发现性门", "长期知识层", "及时删除"):
            self.assertIn(token, SKILL + README + task_plan)
        for token in ("不为每条知识补 owner、失效条件或维护表单", "只有可变知识",
                      "代码、配置或 fresh 探测"):
            self.assertIn(token, evolution)

    def test_temporary_evidence_is_deleted_by_default_without_a_new_retention_process(self) -> None:
        review = reference("learn-review.md")
        evolution = reference("evolve-system.md")
        for token in ("临时证据", "验收和退休完成后及时删除", "不可重现",
                      "审计、回滚或事故恢复", "复用现有证据系统", "不新建冷证据管理流程"):
            self.assertIn(token, review + evolution)
        for token in ("奥卡姆剃刀", "最小充分"):
            self.assertIn(token, evolution)

    def test_knowledge_writeback_integrates_truth_and_updates_navigation_only_on_topology_change(self) -> None:
        evolution = reference("evolve-system.md")
        for token in ("语义整合", "不是追加式补丁", "Knowledge Delta 只作回执",
                      "知识拓扑变化", "新建、迁移、替换或废弃唯一真源", "不建立 AI 专用知识真源"):
            self.assertIn(token, evolution)
        for token in ("原 Plan 的退休事务", "不另开 Plan", "新的用户结果"):
            self.assertIn(token, evolution)
        for token in ("原 Plan 的退休事务", "不另开 Plan"):
            self.assertIn(token, README)
        for token in ("内容更新", "不机械改动根导航"):
            self.assertIn(token, evolution)

    def test_project_knowledge_has_one_entry_and_claim_owners(self) -> None:
        evolution = reference("evolve-system.md")
        for token in ("项目知识入口", "AGENTS.md", "README", "TRUTH", "只做导航", "不复制代码事实",
                      "不新建中央知识库", "候选实现", "部署运行态", "规范要求", "设计理由",
                      "授权与验收", "活动工作状态", "派生导航", "version / fingerprint", "fail closed"):
            self.assertIn(token, evolution)
        for token in ("项目知识导航", "完成 Plan 立即退出日常上下文", "退休检查"):
            self.assertIn(token, README)

    def test_completed_plan_exits_hot_path_and_passes_retirement_gate(self) -> None:
        review = reference("learn-review.md")
        task_plan = (PACKAGE / "templates/task_plan.md").read_text()
        for token in ("完成 Plan", "默认上下文", "立即退出", "显式追溯"):
            self.assertIn(token, reference("handoff-context.md"))
        for token in ("长期知识", "临时证据", "例外保留证据", "未解决项", "Plan 处置"):
            self.assertIn(token, review)
            self.assertIn(token, task_plan)
        for forbidden in ("promoted / already_owned / intentionally_ephemeral / unresolved",
                          "长期 owner / 证据位置", "恢复位置 / 保留期限"):
            self.assertNotIn(forbidden, review + task_plan)
        for text, tokens in ((review + task_plan, ("退休检查", "不得物理删除")),
                             (reference("deliver-release.md"), ("物理删除", "精确删除授权", "现有证据系统")),
                             (review, ("Knowledge Delta", "长期真源发生变化", "不为每个 Task", "新建"))):
            for token in tokens:
                self.assertIn(token, text)

    def test_legacy_index_reads_stop_after_the_active_section(self) -> None:
        handoff = reference("handoff-context.md")
        for text in (SKILL, handoff):
            for token in ("旧索引", "`Active` 区段", "下一个同级标题", "不得整文件读取"):
                self.assertIn(token, text)


class ExecutionSitePublicContractTest(unittest.TestCase):
    def test_public_docs_explain_that_old_workspaces_are_not_new_task_entrypoints(self) -> None:
        for token in (
            "旧工作现场",
            "新任务",
            "同一任务",
            "只读追溯",
            "不能默认复用",
        ):
            self.assertIn(token, README)


if __name__ == "__main__":
    unittest.main()
