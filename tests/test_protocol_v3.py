from __future__ import annotations

import re
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
REFERENCES = PACKAGE / "references"
TEMPLATES = PACKAGE / "templates"

REQUIRED_CAPABILITY_FILES = {
    "frame.md",
    "grill.md",
    "plan.md",
    "execute.md",
    "prove.md",
    "deliver.md",
    "learn.md",
}

LEGACY_REFERENCE_FILES = {
    "understand-goal.md",
    "decide-solution.md",
    "plan-tasks.md",
    "execute-tasks.md",
    "verify-results.md",
    "learn-review.md",
    "evolve-system.md",
    "shape-experience.md",
    "maintain-design.md",
    "coordinate-agents.md",
    "fix-failures.md",
    "handoff-context.md",
    "deliver-release.md",
}

CORE_OUTCOMES = ("目标框定", "结果规划", "任务执行", "结果验真")
CONDITIONAL_OUTCOMES = ("真实交付", "经验复盘")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def reference(name: str) -> str:
    path = REFERENCES / name
    if not path.is_file():
        raise AssertionError(f"缺少 v3 reference：{name}")
    return read(path)


def reference_files() -> set[str]:
    return {path.name for path in REFERENCES.glob("*.md")}


def assert_any(test: unittest.TestCase, source: str, choices: tuple[str, ...], label: str) -> None:
    test.assertTrue(
        any(choice in source for choice in choices),
        f"{label} 缺少任一稳定语义：{', '.join(choices)}",
    )


def nearby(source: str, marker: str, radius: int = 220) -> str:
    position = source.find(marker)
    if position < 0:
        return ""
    return source[max(0, position - radius) : position + len(marker) + radius]


def strip_machine_boundaries(source: str) -> str:
    """留下人读的正文，移除协议允许保留英文的机器边界。"""

    source = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", source, count=1, flags=re.S)
    source = re.sub(r"```.*?```", "", source, flags=re.S)
    source = re.sub(r"`[^`\n]*`", "", source)
    source = re.sub(r"\]\((?:[^()]|\([^()]*\))*\)", "]", source)
    source = re.sub(r"https?://\S+", "", source)
    source = re.sub(
        r"(?<![\w.-])(?:[A-Za-z0-9_.-]+/)+(?:[A-Za-z0-9_.-]+)|"
        r"(?<![\w.-])[A-Za-z0-9_.-]+\.(?:md|py|json|yaml|yml|toml|sh|html)(?![\w.-])",
        "",
        source,
    )
    source = re.sub(r"(?<![A-Za-z0-9_])[PT]\d+(?:[-–][PT]?\d+)?(?![A-Za-z0-9_])", "", source)
    source = re.sub(r"--?[a-z][a-z0-9-]*", "", source, flags=re.I)
    return source


class WorkflowV3MainlineTest(unittest.TestCase):
    def test_root_declares_v3_and_one_six_outcome_mainline(self) -> None:
        skill = read(PACKAGE / "SKILL.md")
        version = re.search(r"(?m)^version:\s*(\S+)\s*$", skill)
        self.assertIsNotNone(version)
        self.assertEqual(version.group(1), "3.1.0")

        positions = [skill.index(outcome) for outcome in (*CORE_OUTCOMES, *CONDITIONAL_OUTCOMES)]
        self.assertEqual(positions, sorted(positions))
        for outcome in CORE_OUTCOMES:
            self.assertGreaterEqual(skill.count(outcome), 1, outcome)
        for outcome in CONDITIONAL_OUTCOMES:
            context = nearby(skill, outcome, 320)
            assert_any(
                self,
                context,
                ("按需", "条件", "仅当", "需要时", "若", "按真实需要", "时进入"),
                f"{outcome} 条件性",
            )

        assert_any(
            self,
            skill,
            ("不另立阶段", "不是固定阶段", "不增加阶段", "不扩张主链", "不是要求模型举行固定仪式"),
            "条件能力不扩张主链",
        )

    def test_core_capabilities_exist_and_every_current_reference_is_reachable(self) -> None:
        actual = reference_files()
        self.assertTrue(REQUIRED_CAPABILITY_FILES <= actual)
        self.assertTrue(actual.isdisjoint(LEGACY_REFERENCE_FILES))
        skill = read(PACKAGE / "SKILL.md")
        routed = set(re.findall(r"\(references/([A-Za-z0-9_-]+\.md)\)", skill))
        self.assertEqual(routed, actual)
        for name in LEGACY_REFERENCE_FILES:
            self.assertNotIn(f"references/{name}", skill, name)

        broken: list[str] = []
        for source_name in sorted(actual):
            for target in re.findall(r"\(([A-Za-z0-9_-]+\.md)\)", reference(source_name)):
                if target not in actual:
                    broken.append(f"{source_name} -> {target}")
        self.assertEqual(broken, [])


class ProgressiveRoutingTest(unittest.TestCase):
    def test_progressive_disclosure_is_a_root_policy_not_a_uniform_file_template(self) -> None:
        skill = read(PACKAGE / "SKILL.md")
        assert_any(
            self,
            skill,
            ("只读取当前决定所需", "不预读整套", "按需读取"),
            "最小加载",
        )
        assert_any(
            self,
            skill,
            ("先做最小动作", "先走最小路径", "最小充分"),
            "默认深度",
        )
        assert_any(
            self,
            skill,
            ("真实触发信号", "出现缺口", "按风险渐进展开"),
            "加深条件",
        )

    def test_frame_uses_research_grill_and_experience_as_conditional_feedback(self) -> None:
        source = reference("frame.md")
        for name in ("research.md", "grill.md", "experience.md"):
            self.assertIn(name, source)

        assert_any(self, nearby(source, "research.md"), ("事实", "证据", "可查", "真源"), "调研触发")
        assert_any(self, nearby(source, "grill.md"), ("承重", "取舍", "歧义", "决策"), "质询触发")
        assert_any(
            self,
            nearby(source, "experience.md"),
            ("体验", "界面", "交互", "信息架构", "用户路径"),
            "体验触发",
        )
        for relation in ("串行", "并行"):
            self.assertIn(relation, source)
        assert_any(self, source, ("不固定", "不是固定", "不得固定", "按条件"), "非固定编排")
        assert_any(
            self,
            source,
            ("反馈回", "回到目标", "重算目标", "改写目标契约", "重开受影响", "吸收到契约"),
            "结果反馈",
        )

    def test_existing_page_changes_use_one_real_preview_and_scoped_proof_path(self) -> None:
        root = read(PACKAGE / "SKILL.md")
        experience = reference("experience.md")
        proof = reference("prove.md")
        readme = read(PACKAGE / "README.md")
        visual_source = read(PACKAGE / "scripts/generate_visual_map.py")

        for token in ("改动面", "保护面", "优先复用原实现", "不做全量人工前后对比", "共享边界"):
            self.assertIn(token, root, f"根不变量缺少 {token}")

        for source, label in ((experience, "体验路由"), (readme, "对外说明"), (visual_source, "视觉真源")):
            assert_any(self, source, ("现有页面局部修改", "现有页面的局部修改"), f"{label}局部范围")
            self.assertIn("真实源码", source, f"{label}没有复用真实源码")
            self.assertIn("保护面", source, f"{label}没有声明保护面")
            assert_any(
                self,
                source,
                (
                    "登录态独立验收入口",
                    "受登录保护的独立验收入口",
                    "真实登录态的独立验收入口",
                    "真实登录态的只读独立验收入口",
                ),
                f"{label}真实验收入口",
            )
            assert_any(
                self,
                source,
                ("承重方向分歧", "方向确有承重分歧", "多个互斥方向"),
                f"{label}独立概念稿门",
            )

        for token in ("保护面", "结构性保真", "全量人工前后对比", "受影响入口", "高风险连接点"):
            self.assertIn(token, proof)
        assert_any(
            self,
            proof,
            ("不要求全量人工前后对比", "不做全量人工前后对比", "无需全量人工前后对比"),
            "局部修改的最小验真",
        )
        assert_any(
            self,
            proof,
            ("真实登录态", "当前用户登录态", "受登录保护"),
            "登录态环境边界",
        )
        for token in ("不自动获得新的业务写入授权", "默认只读"):
            self.assertIn(token, experience)


class DepthAndCoordinationTest(unittest.TestCase):
    def test_grill_preserves_depth_but_stops_on_contract_stability(self) -> None:
        source = reference("grill.md")
        for choices, label in (
            (("承重决策", "承重问题", "承重假设", "会改变目标", "会改变契约"), "问题选择"),
            (("决策树", "质询前沿", "最上游", "重算"), "递进深挖"),
            (("用户决定", "用户选择", "明确委托"), "决策归属"),
            (("可验证假设", "最小实验", "可失败验证"), "未知转实验"),
            (("明确风险承担者", "风险承担", "延期", "阻断", "blocker"), "未决出口"),
            (("AI 代选", "模型代选", "安全可逆细节", "可代选"), "非承重细节"),
            (("契约稳定", "目标稳定", "停止条件", "退出条件"), "停止规则"),
        ):
            assert_any(self, source, choices, label)
        root = read(PACKAGE / "SKILL.md")
        alias_context = nearby(root, "grill-me", 180)
        self.assertIn("grill.md", alias_context)

    def test_plan_derives_serial_and_parallel_tasks_from_real_dependencies(self) -> None:
        source = reference("plan.md")
        for token in ("计划", "任务", "串行", "并行", "依赖", "验收", "验证"):
            self.assertIn(token, source)
        assert_any(self, source, ("文件冲突", "写冲突", "同一真源"), "并发冲突")
        assert_any(self, source, ("独立执行", "可独立", "独立闭环"), "任务可执行性")
        assert_any(
            self,
            source,
            ("不是为了凑并行", "不强制并行", "不固定串并联", "由依赖决定", "真实依赖决定串行"),
            "自然拆分",
        )

    def test_orchestration_gives_each_worker_a_sufficient_capsule_and_one_receipt(self) -> None:
        source = reference("orchestrate.md")
        for choices, label in (
            (("目标", "预期结果"), "子任务结果"),
            (("已知输入", "上下文"), "子任务输入"),
            (("范围", "文件域", "边界"), "子任务边界"),
            (("验收", "完成条件"), "子任务验收"),
            (("验证", "证据"), "子任务验证"),
            (("依赖", "前置"), "子任务依赖"),
            (("授权", "副作用"), "子任务授权"),
            (("candidate", "候选回执", "候选结果"), "worker 返回候选"),
            (("accepted", "接受回执", "协调者接受"), "协调者接纳"),
        ):
            assert_any(self, source, choices, label)
        self.assertIn("并行实施", source)
        for choices, label in (
            (("独立写现场", "写入权不冲突", "独立文件域"), "写隔离"),
            (("可独立验证", "独立验收"), "验证隔离"),
            (("并行收益", "净收益", "缩短关键路径"), "并行价值"),
        ):
            assert_any(self, source, choices, label)
        assert_any(
            self,
            source,
            ("不复制整份背景", "不重复发送完整上下文", "增量上下文", "避免轮询", "不重复轮询"),
            "协作效率",
        )

        execution = reference("execute.md")
        assert_any(
            self,
            execution,
            ("每个子 Task 独立判断深度", "每个子任务独立判断深度", "按当前任务判断深度"),
            "子任务独立深度",
        )
        assert_any(
            self,
            execution,
            ("由这个 Task 的未知", "由当前任务的未知", "按可逆性", "按失败代价"),
            "深度触发",
        )

    def test_recovery_and_orchestration_use_evidence_instead_of_fixed_counts(self) -> None:
        orchestration = reference("orchestrate.md")
        recovery = reference("recover.md")
        assert_any(
            self,
            orchestration,
            ("按独立问题", "按依赖", "按并行收益", "按风险", "真实并行收益", "净收益"),
            "代理数量自适应",
        )
        assert_any(
            self,
            recovery,
            ("新证据", "新增观察", "根因假设", "失败分类", "改变假设", "改变策略"),
            "重试依据",
        )
        assert_any(
            self,
            recovery,
            ("相同失败", "没有新证据", "停止重试", "转为阻断", "停止扩张", "新证据不再缩小根因"),
            "重试停止",
        )


class DeliveryLearningAndTruthTest(unittest.TestCase):
    def test_context_compaction_forces_a_harness_and_occam_retrospective(self) -> None:
        skill = read(PACKAGE / "SKILL.md")
        learning = reference("learn.md")

        compaction_context = nearby(skill, "上下文压缩", 320)
        assert_any(
            self,
            compaction_context,
            ("必须进入", "强制进入", "必进", "不得略过"),
            "上下文压缩触发复盘",
        )
        for choices, label in (
            (("workflow", "工作流"), "workflow harness"),
            (("项目级", "项目内", "当前项目"), "项目级 harness"),
            (("重复", "冗余"), "重复冗余"),
            (("唯一真源", "单一真源"), "唯一真源精炼度"),
            (("导航", "入口", "可发现"), "导航清晰度"),
            (("删除", "移除"), "无效动作删除测试"),
            (("结果",), "结果关联"),
            (("风险",), "风险覆盖"),
        ):
            assert_any(self, learning, choices, label)
        assert_any(
            self,
            learning,
            ("不等于缺陷", "不直接证明", "不自动判定", "仍可 no-op"),
            "压缩事件不预设缺陷结论",
        )

    def test_delivery_and_learning_have_distinct_gates_and_one_real_status_boundary(self) -> None:
        delivery = reference("deliver.md")
        learning = reference("learn.md")
        proof = reference("prove.md")
        orchestration = reference("orchestrate.md")
        research = reference("research.md")
        recovery = reference("recover.md")

        for token in ("验真", "授权", "交付", "回滚", "交付后"):
            self.assertIn(token, delivery)
        assert_any(self, delivery, ("已通过", "accepted", "验真通过"), "交付前证据门")

        for token in ("验真", "交付状态", "候选"):
            self.assertIn(token, learning)
        assert_any(self, learning, ("只读", "不写入", "不触发外部写入"), "复盘预判边界")
        assert_any(self, learning, ("定稿", "接受", "最终结论", "实际状态"), "复盘收口")
        assert_any(self, learning, ("不沉淀", "no-op", "无需沉淀"), "复盘允许空结果")

        combined = read(PACKAGE / "SKILL.md") + "\n" + delivery + "\n" + learning
        for choices, label in (
            (("并行", "同时"), "允许候选分析重叠"),
            (("候选", "candidate"), "并行内容仍是候选"),
            (("交付状态", "交付事实", "交付结果"), "真实状态依赖"),
            (("最终接受", "定稿", "最终经验", "接受发生"), "最终收口"),
        ):
            assert_any(self, combined, choices, label)

        assert_any(
            self,
            proof,
            ("验真责任者只返回", "复核者只返回", "验真者只返回"),
            "验真者不成为控制面写者",
        )
        assert_any(
            self,
            proof,
            ("协调者唯一写入", "始终由协调者写入", "只有协调者写入", "协调者作最终接受判断并唯一写入"),
            "控制面唯一写者",
        )
        for gate in ("plan", "execute", "prove"):
            self.assertIn(gate, learning, f"经验实际回灌仍需经过 {gate}")
        assert_any(
            self,
            learning,
            ("不能直接修改", "不得直接修改", "不直接修改"),
            "复盘不绕过结果门",
        )
        assert_any(
            self,
            orchestration,
            ("隔离候选", "候选现场"),
            "并行结果只汇合到候选",
        )
        assert_any(
            self,
            orchestration,
            ("不更新真实目标", "不得更新真实目标", "不能改变真实目标"),
            "真实目标只由交付改变",
        )
        for source, label in ((research, "研究"), (recovery, "恢复")):
            assert_any(
                self,
                source,
                ("协调者最终接受", "协调者作最终接受", "只有协调者接受"),
                f"{label}候选由协调者接受",
            )
        assert_any(
            self,
            learning,
            ("无交付目标时", "没有交付目标时"),
            "无交付结果的复盘入口",
        )
        assert_any(
            self,
            learning,
            ("有交付目标时", "存在交付目标时"),
            "有交付结果的复盘入口",
        )
        skill = read(PACKAGE / "SKILL.md")
        learning_row = nearby(skill, "| 经验复盘", 260)
        assert_any(
            self,
            learning_row,
            ("实际回灌另走结果门", "回灌另走结果门", "回灌另行验真"),
            "根契约不让复盘绕过结果门",
        )

    def test_work_replaces_legacy_state_templates_and_has_one_writer(self) -> None:
        actual = {path.name for path in TEMPLATES.glob("*.md")}
        self.assertIn("work.md", actual)
        self.assertTrue(
            actual.isdisjoint(
                {
                    "findings.md",
                    "progress.md",
                    "implementation-plan.md",
                    "index.md",
                    "task-owner-prompt.md",
                    "task_plan.md",
                }
            )
        )
        source = read(TEMPLATES / "work.md")

        for status in ("active", "waiting", "blocked", "done"):
            self.assertIn(status, source)
        for choices, label in (
            (("目标契约", "结果契约"), "目标"),
            (("结果计划", "Plan"), "计划"),
            (("依赖", "前置"), "依赖"),
            (("当前结果", "当前产物"), "当前结果"),
            (("已接受回执", "accepted receipt", "接受回执"), "接受回执"),
            (("证据", "evidence"), "证据"),
            (("下一就绪责任", "下一动作", "下一步"), "下一就绪责任"),
            (("阻断", "blocker"), "阻断"),
            (("交付", "delivery"), "交付"),
            (("经验", "learning"), "经验"),
        ):
            assert_any(self, source, choices, label)

        assert_any(self, source, ("仅协调者写", "协调者唯一写入", "唯一写者"), "单写者")
        assert_any(self, source, ("worker 只返回候选", "执行者只返回候选", "子代理只提交候选"), "候选边界")
        assert_any(self, source, ("协调者接受", "协调者验收后写入", "accepted"), "接受边界")
        assert_any(self, source, ("默认内联", "优先内联"), "capsule / receipt 默认形态")
        assert_any(self, source, ("复杂协作", "跨上下文", "昂贵证据"), "物化触发")
        assert_any(self, source, ("输入 / 真源", "输入与真源", "已接受上游证据"), "恢复所需输入")
        assert_any(self, source, ("授权 / 非目标", "授权与非目标"), "任务授权边界")
        assert_any(self, source, ("验证 / 返回", "验证与返回条件"), "任务返回边界")
        assert_any(self, source, ("恢复入口", "物化候选入口"), "按需物化定位")
        assert_any(self, source, ("整体验真", "计划验真"), "父计划结果不能由子任务绿灯替代")
        assert_any(self, source, ("细化触发", "就绪时展开"), "等待任务渐进细化")
        assert_any(self, source, ("相对目标契约的增量", "继承内容不重复"), "任务字段不复制上游契约")

        waiting = source.split("#### P01-T02", 1)[1].split("## 当前结果", 1)[0]
        for expanded in ("输入 / 真源", "授权 / 非目标", "文件 / 资源隔离", "验证 / 返回"):
            self.assertNotIn(expanded, waiting, f"waiting 任务不应提前展开：{expanded}")


class UserCommunicationAndLanguageTest(unittest.TestCase):
    def test_user_snapshot_is_mandatory_at_key_exits_without_repeating_unchanged_state(self) -> None:
        skill = read(PACKAGE / "SKILL.md")
        for label in ("结论", "进度", "技能", "成果", "路径"):
            self.assertRegex(skill, rf"(?m)^(?:>\s*)?{label}[｜|]", label)
        for trigger in ("首次", "实质变化", "真实阻塞", "最终交付", "交回控制权"):
            self.assertIn(trigger, skill, f"关键出口缺少：{trigger}")
        assert_any(self, skill, ("必须展示", "强制展示", "必须使用"), "关键出口强制画面")
        assert_any(self, skill, ("同一轮", "轻量任务"), "轻量任务合并播报")
        assert_any(
            self,
            skill,
            ("无变化不重复", "状态未变不重复", "不播报相同快照", "不重复没有变化的快照"),
            "去重",
        )

        path_lines = [line for line in skill.splitlines() if re.match(r"^(?:>\s*)?路径[｜|]", line)]
        self.assertTrue(path_lines)
        result_lines = [line for line in skill.splitlines() if re.match(r"^(?:>\s*)?成果[｜|]", line)]
        self.assertTrue(result_lines)
        sample = "\n".join(result_lines + path_lines)
        for internal in ("runtime", "Manifest", "doctor", "SHA", "P01", "T03"):
            self.assertNotIn(internal, sample, f"用户主画面泄漏内部术语：{internal}")
        assert_any(
            self,
            skill,
            ("业务含义", "业务人员", "用户能理解", "对用户意味着什么"),
            "业务阅读意义",
        )
        assert_any(
            self,
            skill,
            ("技术证据", "技术细节", "内部标识"),
            "技术信息降级",
        )
        assert_any(
            self,
            skill,
            ("发生了什么", "现在是否可用", "是否需要行动"),
            "主视图决策价值",
        )
        self.assertRegex(
            skill,
            r"内部\s*`?P/T`?.{0,40}(?:补充|定位价值)",
            "内部任务编号只能按需作为定位补充",
        )

    def test_human_readable_protocol_body_is_chinese(self) -> None:
        allowed = {
            "AI",
            "API",
            "CLI",
            "Git",
            "GitHub",
            "HTTP",
            "HTTPS",
            "JSON",
            "SHA",
            "URL",
            "workflow",
        }
        paths = [
            PACKAGE / "SKILL.md",
            *(REFERENCES / name for name in sorted(reference_files())),
            TEMPLATES / "work.md",
        ]
        violations: list[str] = []
        for path in paths:
            prose = strip_machine_boundaries(read(path))
            words = set(re.findall(r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z-]*(?![A-Za-z0-9_])", prose))
            unexpected = sorted(word for word in words if word not in allowed)
            if unexpected:
                violations.append(f"{path.relative_to(PACKAGE)}: {', '.join(unexpected)}")
        self.assertEqual(violations, [], "人读正文残留英文：\n" + "\n".join(violations))

    def test_protocol_does_not_hard_code_expert_question_or_retry_counts(self) -> None:
        paths = [
            PACKAGE / "SKILL.md",
            *(REFERENCES / name for name in sorted(reference_files())),
            TEMPLATES / "work.md",
        ]
        source = "\n".join(strip_machine_boundaries(read(path)) for path in paths)
        chinese_number = "一二三四五六七八九十百两"
        forbidden = (
            rf"(?:固定|恰好|必须|最多|至少)\s*(?:为|使用|安排|组成)?\s*[0-9{chinese_number}]+\s*(?:名|位|个)?\s*(?:专家|子代理|代理)",
            rf"(?:固定|恰好|必须|最多|至少)\s*(?:问|追问|提出)?\s*[0-9{chinese_number}]+\s*(?:道|个)?\s*(?:题|问题)",
            rf"(?:固定|恰好|必须|最多|至少|上限)\s*(?:重试|追问)?\s*[0-9{chinese_number}]+\s*(?:次|轮)",
            rf"(?:重试|追问)\s*(?:固定|恰好|必须|最多|至少|上限|为)?\s*[0-9{chinese_number}]+\s*(?:次|轮)",
        )
        matches = [match.group(0) for pattern in forbidden for match in re.finditer(pattern, source)]
        self.assertEqual(matches, [], f"发现固定规模规则：{matches}")


if __name__ == "__main__":
    unittest.main()
