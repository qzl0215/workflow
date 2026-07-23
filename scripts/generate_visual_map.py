#!/usr/bin/env python3
"""Generate the standalone workflow contract panorama from formal sources."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SKILL = PACKAGE / "SKILL.md"
REFERENCES = PACKAGE / "references"
TEMPLATES = PACKAGE / "templates"
CHANGELOG = PACKAGE / "CHANGELOG.md"
OUTPUT = PACKAGE / "docs/workflow-visual-map.html"
REPOSITORY = "https://github.com/qzl0215/workflow"
AGENT_PROMPT = (
    "请安装 GitHub 项目 https://github.com/qzl0215/workflow。先把仓库克隆到临时目录，"
    "再根据你当前 Agent 的配置确认 skills 父目录，不要猜固定路径；运行 "
    "python3 scripts/install.py install --target \"<skills父目录>\"。如果已经安装，则使用 update。"
    "最后运行同一脚本的 check，只有验证通过后才能告诉我安装完成。不要安装任何其他 skill，"
    "也不要覆盖没有备份的旧版本。"
)

PRIMARY_OWNER_FILES = (
    "understand-goal.md",
    "decide-solution.md",
    "plan-tasks.md",
    "execute-tasks.md",
    "verify-deliver.md",
    "learn-review.md",
    "evolve-system.md",
)

HARNESS_FILES = (
    "challenge-decisions.md",
    "shape-experience.md",
    "maintain-design.md",
    "coordinate-agents.md",
    "merge-parallel-work.md",
    "fix-failures.md",
    "handoff-context.md",
)

ACTION_STORIES = {
    "需求澄清": {
        "promise": "不先做，先证明值得做。",
        "pain": "需求看似明确，价值、边界和成功标准却仍靠猜。",
        "solution": "先查事实，再按决策树成批问清关键判断。",
        "best_practice": "独立问题编号批问；承重分支没关就不出需求卡。",
        "question": "为什么做，怎样才算成？",
        "ai": "查事实、排问题、追关键分支。",
        "user": "按编号确认取舍与授权。",
        "outcome": "目标、成功信号与非范围。",
        "evidence": "关键判断有回答或明确处置。",
        "next": "选定方案",
        "fallback": "调查、关键追问或明确阻断",
        "owner": "understand-goal.md",
        "harnesses": ("challenge-decisions.md",),
        "documents": ("findings.md",),
        "case": "“做个 AI 助手”变成“权限内问答，确认后拆单；不自动执行”。",
        "deep": ("四路未知：事实可查就查，取舍待定再问，假设待验就试，外部待解则等授权。", "关键追问：独立问题编号批问，有依赖的分支逐层深挖。", "需求卡只在承重分支全部回答、验证、延期或阻断后生成。"),
    },
    "选定方案": {
        "promise": "先看见终局，再选择路径。",
        "pain": "团队太早爱上第一个解法，局部最优掩盖了整片森林。",
        "solution": "先画出 90 分终局，让关键专家独立判断、交叉质询，再收敛路线。",
        "best_practice": "至少比较两条可行路径，并明确推荐、删除理由和回滚点。",
        "question": "90 分结果该走哪条路？",
        "ai": "画终局、找专家、比路线。",
        "user": "确认方向与关键取舍。",
        "outcome": "推荐方案、边界与回滚点。",
        "evidence": "高回报路线经得起反驳。",
        "next": "拆成任务",
        "fallback": "补事实或重做取舍",
        "owner": "decide-solution.md",
        "harnesses": ("challenge-decisions.md", "shape-experience.md", "maintain-design.md"),
        "documents": ("pre-plan-contract.md", "findings.md"),
        "case": "删除权限语义冲突的旧工单复用，选择独立问题域与可信身份。",
        "deep": ("动态专家：只请最能改变结论的人先独立判断，再互相挑战。", "界面任务：结构未定先线框，确认后再做高保真。"),
    },
    "拆成任务": {
        "promise": "用户选结果，AI 排行动图。",
        "pain": "计划只有待办，没有依赖、文件边界和可失败的验收。",
        "solution": "把已选结果拆成 Plan 与 Ready Task，排清依赖、并行和汇合点。",
        "best_practice": "每个任务都要齐备目标、输入、输出、验收、文件域和依赖。",
        "question": "怎样拆才可做、可验、可交接？",
        "ai": "拆计划与任务，排依赖和并行。",
        "user": "确认纳入哪些业务结果。",
        "outcome": "计划、任务、负责人和验收。",
        "evidence": "每个就绪任务都无需再猜。",
        "next": "执行任务",
        "fallback": "回到目标、方案或体验",
        "owner": "plan-tasks.md",
        "harnesses": ("coordinate-agents.md",),
        "documents": ("task_plan.md", "implementation-plan.md", "index.md"),
        "case": "把问答、拆单、上下文与角色验收拆成可并行、可汇合的任务。",
        "deep": ("六项齐全才执行：目标、输入、输出、验收、文件、依赖。", "只并行文件互不冲突且等待更少的工作。"),
    },
    "执行任务": {
        "promise": "一次做成一个可验收结果。",
        "pain": "旧现场被当成新任务入口，过期代码与错误上下文一起进入执行。",
        "solution": "先证明任务、现场和基线一致，再领取一个就绪任务并完成自验。",
        "best_practice": "新任务用新基线；同一任务按风险同步。",
        "question": "现在最该做成哪一项？",
        "ai": "领取就绪任务，产出并自验。",
        "user": "只确认范围或方向变化。",
        "outcome": "真实产物、变更与任务证据。",
        "evidence": "任务验收由新证据证明。",
        "next": "下一任务或验收交付",
        "fallback": "根因纠错或回到上游",
        "owner": "execute-tasks.md",
        "harnesses": ("coordinate-agents.md", "fix-failures.md", "handoff-context.md"),
        "documents": ("task-owner-prompt.md", "progress.md"),
        "case": "已合入主线的旧分支只读留证，新任务从 fresh 隔离现场开始。",
        "deep": ("开工：先验证 Task 绑定、目标基线、freshness、脏改动归属与可写性。", "失败：找到第一个错误状态，修根因后再继续。", "交接：只带当前任务需要的事实、边界与证据。"),
    },
    "验收交付": {
        "promise": "先证明做成，再按授权交付。",
        "pain": "“代码写完”被当作“业务完成”，验证和外部授权混成一步。",
        "solution": "先验真，再按项目发布真源完成授权内集成发布。",
        "best_practice": "集成后重验，并记录旧现场如何处置。",
        "question": "凭什么完成，能交到哪？",
        "ai": "验真、读发布真源、完成集成。",
        "user": "验收并授权交付目标。",
        "outcome": "验收证据、集成发布与真实状态。",
        "evidence": "发布后核验与授权目标一致。",
        "next": "提炼经验",
        "fallback": "执行任务或补上游缺口",
        "owner": "verify-deliver.md",
        "harnesses": ("merge-parallel-work.md", "fix-failures.md"),
        "documents": ("progress.md",),
        "case": "三种角色与越权路径全部重验；未获发布授权就停在本地已验证。",
        "deep": ("第一道门：证据证明结果。", "第二道门：授权决定交付层级。", "第三道门：项目发布真源驱动集成发布与发布后核验。", "现场处置：继续同一 Task、保留只读或等待授权清理；不默认复用。", "并行成果：各自验完，再串行合入；冲突保留双边意图，并重跑双方验证。"),
    },
    "提炼经验": {
        "promise": "只留下会改变下次行动的经验。",
        "pain": "复盘容易变成漂亮总结，过程噪声反而污染长期知识。",
        "solution": "对照计划与实际偏差，只提炼能改变下一次行动的稳定经验。",
        "best_practice": "轻任务可跳过；没有复用价值时，明确记录本轮不更新。",
        "question": "什么真实偏差造成返工？",
        "ai": "对照计划与实际，找复用差异。",
        "user": "只确认稳定偏好。",
        "outcome": "经验候选、适用条件或不更新。",
        "evidence": "结论有事实，不靠漂亮总结。",
        "next": "回灌改进",
        "fallback": "回到偏差来源",
        "owner": "learn-review.md",
        "harnesses": ("challenge-decisions.md",),
        "documents": ("findings.md", "progress.md"),
        "case": "把重复追问归因于语义缺口；无复用价值的过程不进入长期文档。",
        "deep": ("轻复盘看偏差；标准复盘看根因；项目复盘再看机制。", "没有高价值经验时，明确不更新。"),
    },
    "回灌改进": {
        "promise": "发现好改进，先让你决定。",
        "pain": "按次数回灌会漏掉高价值洞察，也会升级低价值噪音。",
        "solution": "AI 先做最小提案，确认后交给正确项目完成。",
        "best_practice": "只提小改动、大价值；不值得就不改。",
        "question": "什么值得提案，应该在哪里改？",
        "ai": "识别痛点、做减法、推荐落点。",
        "user": "确认需求、方案与计划。",
        "outcome": "已确认提案，或明确不改。",
        "evidence": "目标位置完成改动并重新验明。",
        "next": "拆成任务或交给目标项目",
        "fallback": "补证据、调整提案或不改",
        "owner": "evolve-system.md",
        "harnesses": ("coordinate-agents.md",),
        "documents": ("目标真源",),
        "case": "发现固定次数门压制高价值洞察；用户确认后在目标项目追加计划并验明。",
        "deep": ("模型判断提案价值，不按次数或配额机械升级。", "同项目直接追加计划，跨项目用最小交接胶囊。"),
    },
}

VISUAL_TEMPLATE_NAMES = (
    "index.md",
    "findings.md",
    "pre-plan-contract.md",
    "task_plan.md",
    "implementation-plan.md",
    "progress.md",
    "task-owner-prompt.md",
)

DOCUMENT_EXAMPLES = {
    "findings.md": """## 事实与判断
- 已证实：后台已有登录态与页面知识接口。
- 未知：截图能否跨用户读取；进入最小实验。
- 取舍：自动执行风险高，本期明确不做。
- 结论：只做权限内问答与确认后拆单。
- 来源：接口代码、三种角色实测、业务确认。""",
    "pre-plan-contract.md": """## 已确认方案
- 目标：运营在当前页面直接提问并生成问题单草稿。
- 推荐：独立问题域 + 可信身份。
- 删除：复用旧工单；权限与所有权语义冲突。
- 体验：桌面侧栏，移动端全宽；先线框后高保真。
- 回滚：关闭入口，不影响原工单链。""",
    "task_plan.md": """### Current Snapshot
- 当前阶段：执行任务
- 活跃任务：P02-T02｜问题单草稿
- 最近完成：权限内问答已通过角色测试
- 下一步：实现草稿并验证越权路径
- 阻断：无
- 范围：自动提交与审批不做""",
    "implementation-plan.md": """## P02-T02｜问题单草稿
- 输入：已确认的独立问题域契约
- 输出：多卡草稿与确认动作
- 文件：draft service / side panel
- 依赖：权限问答已完成
- 验收：普通运营可编辑；越权用户不可见
- 回退：关闭草稿入口""",
    "progress.md": """## 验证证据
- 动作：重跑运营、管理员、越权用户三条路径
- 结果：18/18 自动检查通过
- 真实场景：越权截图返回 403
- 交付状态：本地已验证
- 未执行：发布；尚未获得授权
- 下一步：业务验收""",
    "task-owner-prompt.md": """## 当前任务
- 目标：完成问题单多卡草稿
- 允许修改：draft service / side panel
- 禁止修改：登录与原工单流程
- 依赖：权限问答 completed
- 验收：可编辑、可删除、可确认
- 失败即停：权限边界不清或需要改方案
- 返回：变更、证据、风险""",
    "index.md": """## 页面知识与需求助手
- 当前计划：P02｜确认后拆单
- 当前任务：P02-T02｜问题单草稿
- 状态来源：task_plan.md
- 事实与取舍：findings.md
- 执行证据：progress.md
- 入口：plans/260720-需求助手/""",
    "目标真源": """## 已确认回灌提案
- 痛点：固定次数门会错过单次高价值洞察。
- 推断需求：让 AI 做价值判断，再由用户决定。
- 最小改造：替换次数门，复用现有计划与交接胶囊。
- 预期价值：减少低价值规则、重复沟通和无意义上下文。
- 验收：目标位置完成改动并返回 fresh 证据。""",
}


def clean(value: str) -> str:
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = value.replace("**", "").replace("__", "")
    value = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", value)
    return re.sub(r"\s+", " ", value).strip(" -：:|\n\t")


def source_section(text: str, start: str, end: str) -> str:
    try:
        return text.split(start, 1)[1].split(end, 1)[0]
    except IndexError as exc:
        raise ValueError(f"missing source section: {start}") from exc


def derive_action_statuses(release_text: str) -> dict[str, str]:
    def bucket(heading: str) -> str:
        match = re.search(
            rf"^### {re.escape(heading)}\s*(.*?)(?=^### |\Z)",
            release_text,
            re.MULTILINE | re.DOTALL,
        )
        return match.group(1) if match else ""

    added = bucket("Added")
    changed = bucket("Changed")
    return {
        name: "本版新增" if name in added else "本版强化" if name in changed else "保持稳定"
        for name in ACTION_STORIES
    }


def table_rows(block: str, columns: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in block.splitlines():
        if not line.startswith("|") or re.match(r"^\|\s*:?-", line):
            continue
        cells = [clean(cell) for cell in line.strip("|").split("|")]
        if len(cells) != columns or cells[0] in {"阶段", "类型", "未知类型"}:
            continue
        rows.append(cells)
    return rows


def markdown_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+)$", text, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[clean(match.group(1))] = text[match.end():end].strip()
    return sections


def first_sentence(body: str, limit: int = 120) -> str:
    parts: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith(("|", "<!--", "```", "###")):
            continue
        line = re.sub(r"^(?:[-*]|\d+\.)\s+", "", line)
        parts.append(clean(line))
        if "。" in line or len(" ".join(parts)) >= limit:
            break
    value = " ".join(parts)
    return value if len(value) <= limit else value[: limit - 1].rstrip("，； ") + "…"


def reference_trigger(sections: dict[str, str]) -> str:
    for heading in ("何时进入", "触发", "何时读取", "进入条件", "原则"):
        if heading in sections:
            return first_sentence(sections[heading])
    return "当前阶段命中该能力边界时。"


def reference_exit(sections: dict[str, str]) -> str:
    for heading in ("停止 / 通过", "出口", "停止条件", "降级与出口"):
        if heading in sections:
            return first_sentence(sections[heading])
    return "当前缺口有明确结论、证据和下一阶段入口。"


def reference_sop(text: str) -> list[str]:
    steps = [clean(match.group(1)) for match in re.finditer(r"^\d+\.\s+(.+)$", text, re.MULTILINE)]
    if steps:
        return steps[:8]
    bullets = [
        clean(match.group(1))
        for match in re.finditer(r"^-\s+(?:\*\*)?(.+)$", text, re.MULTILINE)
        if not match.group(1).startswith("**L")
    ]
    return bullets[:6] or ["读取当前阶段最小证据，完成对应出口门禁。"]


def source_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(PACKAGE).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:12]


def render_action_buttons(actions: list[dict[str, object]]) -> str:
    phases = (
        ("计划", "不确定 → 承诺", actions[:3]),
        ("执行", "承诺 → 证据", actions[3:5]),
        ("复盘", "结果 → 能力", actions[5:]),
    )
    groups: list[str] = []
    for phase_index, (name, result, items) in enumerate(phases):
        buttons: list[str] = []
        for item in items:
            selected = item["index"] == "1"
            buttons.append(
                f'<button class="action-button" id="action-tab-{item["index"]}" type="button" role="tab" '
                f'data-action="{html.escape(str(item["name"]))}" '
                f'data-status="{html.escape(str(item["status"]))}" '
                f'aria-controls="workbench" aria-selected="{str(selected).lower()}" tabindex="{0 if selected else -1}">'
                f'<span>{html.escape(str(item["index"]))}</span>'
                f'<b>{html.escape(str(item["name"]))}</b>'
                f'<small>{html.escape(str(item["promise"]))}</small>'
                '</button>'
            )
        groups.append(
            f'<div class="phase phase-{phase_index + 1}" data-phase="{name}">'
            f'<button class="phase-header" type="button" data-phase-toggle '
            f'aria-expanded="true" aria-controls="phase-actions-{phase_index + 1}"><b>{name}</b><span>{result}</span></button>'
            f'<div class="phase-actions" id="phase-actions-{phase_index + 1}">{"".join(buttons)}</div></div>'
        )
    return '<div class="phase-map" role="tablist" aria-label="workflow 七动作">' + "".join(groups) + "</div>"


def render_document_buttons(documents: list[dict[str, str]]) -> str:
    return "".join(
        f'<button class="doc-tab" id="doc-tab-1-{index}" type="button" role="tab" data-doc="{index}" '
        f'aria-controls="doc-panel" aria-selected="{str(index == 0).lower()}" '
        f'tabindex="{0 if index == 0 else -1}">{html.escape(item["file"])}</button>'
        for index, item in enumerate(documents)
    )


def render_deep_items(items: list[str]) -> str:
    return "".join(f"<li>{html.escape(item)}</li>" for item in items)


def render_reference_index(references: list[dict[str, str]]) -> str:
    return "".join(
        '<li>'
        f'<span>{html.escape(item["display"])}</span>'
        f'<code>{html.escape(item["path"])}</code>'
        '</li>'
        for item in references
    )


def render_document_index() -> str:
    return "".join(f"<code>{html.escape(filename)}</code>" for filename in VISUAL_TEMPLATE_NAMES)



def phase_for(index: int) -> tuple[str, str]:
    if index <= 3:
        return "计划", "不确定 → 承诺"
    if index <= 5:
        return "执行", "承诺 → 证据"
    return "复盘", "结果 → 能力"


def render_deck_nav(actions: list[dict[str, object]]) -> str:
    items = [
        ("slide-cover", "开场", "00"),
        ("slide-overview", "全景", "01"),
        *[
            (f"slide-{item['name']}", str(item["name"]), f"{int(str(item['index'])) + 1:02d}")
            for item in actions
        ],
        ("slide-unknowns", "四路未知", "09"),
        ("slide-roundtable", "专家圆桌", "10"),
        ("slide-install", "安装", "11"),
    ]
    return "".join(
        f'<button type="button" data-slide-target="{html.escape(target)}" '
        f'aria-label="前往第 {index} 页：{html.escape(label)}">'
        f'<span>{index}</span><b>{html.escape(label)}</b></button>'
        for target, label, index in items
    )


def render_document_switcher(action: dict[str, object]) -> str:
    action_index = html.escape(str(action["index"]))
    documents = list(action["documents"])
    buttons = []
    panels = []
    for index, document in enumerate(documents):
        selected = index == 0
        tab_id = f"doc-tab-{action_index}-{index}"
        panel_id = f"doc-panel-{action_index}-{index}"
        buttons.append(
            f'<button class="doc-tab" id="{tab_id}" type="button" role="tab" '
            f'data-doc-index="{index}" aria-selected="{str(selected).lower()}" '
            f'aria-controls="{panel_id}" tabindex="{0 if selected else -1}">'
            f'{html.escape(str(document["file"]))}</button>'
        )
        panels.append(
            f'<pre class="doc-panel" id="{panel_id}" role="tabpanel" '
            f'aria-labelledby="{tab_id}"{" hidden" if not selected else ""}>'
            f'<code>{html.escape(str(document["sample"]))}</code></pre>'
        )
    return (
        '<div class="document-switcher"><div class="doc-tabs" role="tablist" '
        f'aria-label="{html.escape(str(action["name"]))} 的产物示例">'
        + "".join(buttons)
        + '</div><div class="doc-panels">'
        + "".join(panels)
        + "</div></div>"
    )


def render_action_slides(actions: list[dict[str, object]]) -> str:
    slides = []
    for action in actions:
        index = int(str(action["index"]))
        phase, phase_result = phase_for(index)
        slides.append(
            f'<section class="slide action-slide" id="slide-{html.escape(str(action["name"]))}" '
            f'data-kind="action" data-label="{html.escape(str(action["name"]))}" '
            f'data-chapter="{phase}" data-user-layer>'
            '<div class="slide-inner action-layout">'
            '<header class="action-heading reveal">'
            f'<div class="step-mark"><span>0{index}</span><b>{phase}</b><small>{phase_result}</small></div>'
            '<div>'
            f'<p class="slide-kicker">{html.escape(str(action["status"]))} · {html.escape(str(action["name"]))}</p>'
            f'<h2>{html.escape(str(action["promise"]))}</h2>'
            f'<p class="action-question">这一步只回答：<strong>{html.escape(str(action["question"]))}</strong></p>'
            "</div></header>"
            '<div class="action-story reveal">'
            '<div class="pain-block"><span class="story-label">痛点</span>'
            f'<p>{html.escape(str(action["pain"]))}</p></div>'
            '<div class="solution-block"><span class="story-label">解决方案</span>'
            f'<p>{html.escape(str(action["solution"]))}</p></div>'
            '<div class="practice-block"><span class="story-label">最佳实践</span>'
            f'<p>{html.escape(str(action["best_practice"]))}</p></div>'
            "</div>"
            '<div class="action-proof reveal">'
            '<div class="proof-copy">'
            '<span class="story-label">谁做什么</span>'
            f'<dl><div><dt>AI</dt><dd>{html.escape(str(action["ai"]))}</dd></div>'
            f'<div><dt>你</dt><dd>{html.escape(str(action["user"]))}</dd></div>'
            f'<div><dt>产物</dt><dd>{html.escape(str(action["outcome"]))}</dd></div>'
            f'<div><dt>证据</dt><dd>{html.escape(str(action["evidence"]))}</dd></div></dl>'
            f'<p class="case-note"><b>真实变化</b>{html.escape(str(action["case"]))}</p>'
            "</div>"
            f'{render_document_switcher(action)}'
            "</div>"
            '<footer class="slide-route reveal">'
            f'<span>下一步 <b>{html.escape(str(action["next"]))}</b></span>'
            f'<span>有缺口 <b>{html.escape(str(action["fallback"]))}</b></span>'
            "</footer>"
            "</div></section>"
        )
    return "".join(slides)


def render_unknown_cards(unknowns: list[dict[str, str]]) -> str:
    return "".join(
        '<article class="route-card reveal">'
        f'<span>{index:02d}</span><h3>{html.escape(item["name"])}</h3>'
        f'<p>{html.escape(item["essence"])}</p><b>{html.escape(item["handling"])}</b>'
        f'<small>{html.escape(item["return"])}</small></article>'
        for index, item in enumerate(unknowns, 1)
    )


def build() -> tuple[str, str]:
    skill_text = SKILL.read_text(encoding="utf-8")
    changelog_text = CHANGELOG.read_text(encoding="utf-8")
    version = re.search(
        r"^version:\s*(?P<full>(?P<major>\d+)\.(?P<minor>\d+)\.\d+"
        r"(?:-(?P<channel>[A-Za-z]+)(?:\.\d+)?)?)$",
        skill_text,
        re.MULTILINE,
    )
    if version is None:
        raise ValueError("SKILL.md does not contain a supported semantic version")
    current_version = version.group("full")
    version_label = f"V{version.group('major')}.{version.group('minor')}"
    if version.group("channel"):
        version_label += f" {version.group('channel').upper()}"
    state_rows = table_rows(source_section(skill_text, "## 状态接口与硬门", "## 按需路由"), 5)
    unknown_rows = table_rows(
        source_section(skill_text, "## 需求澄清中的四路未知", "## harness 深度"), 4
    )
    route_rows = table_rows(source_section(skill_text, "## 按需路由", "## 文件真源"), 3)
    if len(state_rows) != 7 or len(unknown_rows) != 4 or len(route_rows) != 14:
        raise ValueError(
            "unexpected contract shape: "
            f"states={len(state_rows)}, unknowns={len(unknown_rows)}, routes={len(route_rows)}"
        )

    if tuple(ACTION_STORIES) != tuple(row[0] for row in state_rows):
        raise ValueError("action story registry does not match canonical stage order")
    current_release = re.search(
        rf"^## \[{re.escape(current_version)}\].*?(?=^## \[|\Z)",
        changelog_text,
        re.MULTILINE | re.DOTALL,
    )
    if current_release is None:
        raise ValueError("current changelog does not support the visual action update states")
    action_statuses = derive_action_statuses(current_release.group(0))

    states: list[dict[str, object]] = []
    for index, (name, entry, writes, exit_rule, fallback) in enumerate(state_rows, 1):
        story = ACTION_STORIES[name]
        states.append({
            "index": str(index),
            "name": name,
            "label": story["promise"],
            "promise": story["promise"],
            "pain": story["pain"],
            "solution": story["solution"],
            "best_practice": story["best_practice"],
            "question": story["question"],
            "ai": story["ai"],
            "user": story["user"],
            "outcome": story["outcome"],
            "evidence": story["evidence"],
            "next": story["next"],
            "fallback": story["fallback"],
            "case": story["case"],
            "owner": story["owner"],
            "harnesses": list(story["harnesses"]),
            "documents": [
                {"file": filename, "sample": DOCUMENT_EXAMPLES[filename]}
                for filename in story["documents"]
            ],
            "deep": list(story["deep"]),
            "status": action_statuses[name],
            "source_entry": entry,
            "source_writes": writes,
            "source_exit": exit_rule,
            "source_fallback": fallback,
        })

    unknowns = [
        {"name": name, "essence": essence, "handling": handling, "return": return_rule}
        for name, essence, handling, return_rule in unknown_rows
    ]

    references: list[dict[str, str]] = []
    for kind, signal, target in route_rows:
        filename = Path(target).name
        ref_text = (REFERENCES / filename).read_text(encoding="utf-8")
        title = re.search(r"^#\s+(.+)$", ref_text, re.MULTILINE)
        if title is None:
            raise ValueError(f"missing reference title: {filename}")
        references.append({
            "file": filename,
            "path": target,
            "kind": kind,
            "display": clean(title.group(1)),
            "signal": signal,
        })

    routed_files = {str(item["file"]) for item in references}
    if set(PRIMARY_OWNER_FILES) | set(HARNESS_FILES) != routed_files:
        raise ValueError("action capability registry does not match routed references")
    for action in ACTION_STORIES.values():
        if action["owner"] not in PRIMARY_OWNER_FILES:
            raise ValueError(f"unknown primary owner: {action['owner']}")
        if not set(action["harnesses"]).issubset(HARNESS_FILES):
            raise ValueError("unknown action harness")
        if not set(action["documents"]).issubset(DOCUMENT_EXAMPLES):
            raise ValueError("unknown action document")

    digest_paths = [SKILL, CHANGELOG, *sorted(REFERENCES.glob("*.md"))]
    digest_paths.extend(TEMPLATES / name for name in VISUAL_TEMPLATE_NAMES)
    digest = source_digest(digest_paths)
    changed_count = sum(status != "保持稳定" for status in action_statuses.values())
    change_summary = (
        "本版：七动作均有更新"
        if changed_count == len(action_statuses)
        else f"本版：{changed_count} 个动作有更新"
    )
    initial = states[0]
    initial_document = initial["documents"][0]
    state_json = json.dumps(states, ensure_ascii=False).replace("</", "<\\/")

    replacements = {
        "__DIGEST__": digest,
        "__VERSION_LABEL__": html.escape(version_label),
        "__REPOSITORY__": html.escape(REPOSITORY, quote=True),
        "__AGENT_PROMPT__": html.escape(AGENT_PROMPT),
        "__CHANGE_SUMMARY__": html.escape(change_summary),
        "__ACTION_BUTTONS__": render_action_buttons(states),
        "__DECK_NAV__": render_deck_nav(states),
        "__ACTION_SLIDES__": render_action_slides(states),
        "__UNKNOWN_CARDS__": render_unknown_cards(unknowns),
        "__ACTION_NAME__": html.escape(str(initial["name"])),
        "__ACTION_PROMISE__": html.escape(str(initial["promise"])),
        "__ACTION_STATUS__": html.escape(str(initial["status"])),
        "__ACTION_QUESTION__": html.escape(str(initial["question"])),
        "__ACTION_AI__": html.escape(str(initial["ai"])),
        "__ACTION_USER__": html.escape(str(initial["user"])),
        "__ACTION_OUTCOME__": html.escape(str(initial["outcome"])),
        "__ACTION_EVIDENCE__": html.escape(str(initial["evidence"])),
        "__ACTION_NEXT__": html.escape(str(initial["next"])),
        "__ACTION_FALLBACK__": html.escape(str(initial["fallback"])),
        "__ACTION_CASE__": html.escape(str(initial["case"])),
        "__DEEP_ITEMS__": render_deep_items(initial["deep"]),
        "__DOC_BUTTONS__": render_document_buttons(initial["documents"]),
        "__DOC_NAME__": html.escape(str(initial_document["file"])),
        "__DOC_SAMPLE__": html.escape(str(initial_document["sample"])),
        "__REFERENCE_INDEX__": render_reference_index(references),
        "__DOCUMENT_INDEX__": render_document_index(),
        "__ACTION_JSON__": state_json,
    }
    rendered = HTML_TEMPLATE
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    if re.search(r"__[A-Z][A-Z0-9_]+__", rendered):
        raise ValueError("unresolved visual template marker")
    return rendered, digest


HTML_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="workflow：把模糊目标变成已验证结果的交互式演示文稿。">
<meta name="color-scheme" content="dark">
<title>workflow｜把模糊目标变成已验证结果</title>
<style>
:root{--ink:#090a08;--panel:#12130f;--panel-2:#181914;--paper:#f4f0e6;--signal:#ffd338;--muted:#aaa89f;--dim:#74736c;--line:#393a32;--max:1480px;font-family:"Avenir Next","SF Pro Display","SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;color:var(--paper);background:var(--ink)}
*{box-sizing:border-box}html,body{height:100%;margin:0;background:var(--ink)}html{scroll-behavior:smooth}body{min-width:320px;overflow:hidden}button,a{font:inherit;color:inherit}button{cursor:pointer}code,.mono{font-family:"SFMono-Regular",Consolas,monospace}:focus-visible{outline:3px solid var(--signal);outline-offset:3px}.skip{position:fixed;z-index:100;left:12px;top:10px;transform:translateY(-180%);padding:11px 15px;background:var(--signal);color:var(--ink);font-weight:850}.skip:focus{transform:none}
body::before{content:"";position:fixed;z-index:0;width:680px;height:680px;left:calc(var(--pointer-x,80)*1% - 340px);top:calc(var(--pointer-y,15)*1% - 340px);border-radius:50%;background:radial-gradient(circle,rgb(255 211 56 / 7%),transparent 67%);pointer-events:none}.deck-top{position:fixed;z-index:50;inset:0 0 auto;height:64px;display:grid;grid-template-columns:1fr minmax(160px,420px) 1fr;align-items:center;gap:20px;padding:0 30px;border-bottom:1px solid rgb(244 240 230 / 12%);background:rgb(9 10 8 / 88%);backdrop-filter:blur(16px)}.brand{min-height:44px;display:flex;align-items:center;gap:10px;text-decoration:none;font-weight:900;letter-spacing:-.035em}.brand span{color:var(--signal);font:800 9px "SFMono-Regular",Consolas,monospace;letter-spacing:.08em}.deck-progress{height:2px;background:#34352f;overflow:hidden}.deck-progress span{display:block;width:100%;height:100%;background:var(--signal);transform:scaleX(.0833);transform-origin:left;transition:transform .35s ease}.deck-state{justify-self:end;display:flex;align-items:center;gap:12px;color:var(--muted);font:700 10px "SFMono-Regular",Consolas,monospace;letter-spacing:.08em}.deck-state b{color:var(--paper);font-size:11px}.deck-state i{width:6px;height:6px;border-radius:50%;background:var(--signal);box-shadow:0 0 0 4px rgb(255 211 56 / 10%)}
.deck-nav{position:fixed;z-index:45;left:25px;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:4px}.deck-nav button{width:46px;min-height:44px;padding:0;border:0;background:transparent;color:var(--dim);display:flex;align-items:center;gap:10px;text-align:left}.deck-nav button span{width:20px;font:700 8px "SFMono-Regular",Consolas,monospace}.deck-nav button b{position:absolute;left:45px;padding:8px 10px;background:var(--paper);color:var(--ink);font-size:11px;white-space:nowrap;opacity:0;transform:translateX(-8px);pointer-events:none;transition:opacity .18s ease,transform .18s ease}.deck-nav button::after{content:"";width:23px;height:2px;background:currentColor;transform:scaleX(.56);transform-origin:left;transition:transform .2s ease,background .2s ease}.deck-nav button:hover b,.deck-nav button:focus-visible b{opacity:1;transform:none}.deck-nav button[aria-current="true"]{color:var(--signal)}.deck-nav button[aria-current="true"]::after{transform:scaleX(1);background:var(--signal)}
.deck-controls{position:fixed;z-index:45;right:24px;bottom:22px;display:flex;gap:6px}.deck-controls button{min-width:48px;min-height:48px;border:1px solid var(--line);background:var(--panel);color:var(--paper);font-size:18px}.deck-controls button:hover{border-color:var(--signal);background:var(--signal);color:var(--ink)}.deck-controls button:disabled{opacity:.3;cursor:not-allowed}
.deck{position:relative;z-index:1;height:100svh;overflow-y:auto;overflow-x:hidden;scroll-snap-type:y mandatory;scroll-behavior:smooth;overscroll-behavior-y:contain}.slide{position:relative;isolation:isolate;min-height:100svh;padding:96px clamp(74px,8vw,132px) 72px;display:flex;align-items:center;scroll-snap-align:start;scroll-snap-stop:always;overflow:hidden;border-bottom:1px solid var(--line)}.slide::before{content:"";position:absolute;z-index:-1;inset:0;background:linear-gradient(90deg,transparent 49.95%,rgb(244 240 230 / 4%) 50%,transparent 50.05%)}.slide-inner{width:min(var(--max),100%);margin:auto}.slide-kicker,.story-label{font:800 10px/1 "SFMono-Regular",Consolas,monospace;letter-spacing:.14em;text-transform:uppercase}.slide-kicker{margin:0 0 18px;color:var(--signal)}.slide h1,.slide h2{margin:0;max-width:1120px;font-weight:760;letter-spacing:-.075em;text-wrap:balance}.slide h1{font-size:clamp(62px,8.1vw,134px);line-height:.87}.slide h2{font-size:clamp(44px,5.7vw,86px);line-height:.92}.reveal{opacity:1;transform:none}.js .reveal{opacity:0;transform:translateY(24px);transition:opacity .65s ease,transform .65s cubic-bezier(.2,.8,.2,1)}.js .slide.is-active .reveal{opacity:1;transform:none}.js .slide.is-active .reveal:nth-child(2){transition-delay:.08s}.js .slide.is-active .reveal:nth-child(3){transition-delay:.16s}.js .slide.is-active .reveal:nth-child(4){transition-delay:.24s}
.cover-slide{background:radial-gradient(circle at 78% 30%,rgb(255 211 56 / 11%),transparent 26%),var(--ink)}.cover-grid{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(260px,.45fr);gap:6vw;align-items:end}.cover-lede{margin:30px 0 0;max-width:720px;color:var(--muted);font-size:clamp(17px,1.7vw,24px);line-height:1.55}.cover-aside{border-top:1px solid var(--signal);padding-top:20px}.cover-aside p{margin:0;color:var(--muted);font-size:14px;line-height:1.75}.cover-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:26px}.primary-action,.secondary-action,.copy-button{min-height:48px;padding:0 17px;border:1px solid var(--signal);font-weight:850;text-decoration:none;display:inline-flex;align-items:center;justify-content:center}.primary-action,.copy-button{background:var(--signal);color:var(--ink)}.secondary-action{background:transparent;color:var(--paper)}.primary-action:hover,.copy-button:hover{background:var(--paper);border-color:var(--paper)}.secondary-action:hover{color:var(--ink);background:var(--signal)}
.overview-slide{background:var(--paper);color:var(--ink)}.overview-slide .slide-kicker{color:#685800}.overview-head{display:grid;grid-template-columns:1fr .7fr;gap:7vw;align-items:end}.overview-head p:last-child{margin:0;color:#5f5e58;font-size:17px;line-height:1.7}.phase-strip{display:grid;grid-template-columns:3fr 2fr 2fr;margin-top:44px;border-block:2px solid var(--ink)}.phase-column{min-width:0;padding:18px 20px 20px;border-right:1px solid var(--ink)}.phase-column:last-child{border-right:0}.phase-column header{display:flex;justify-content:space-between;gap:12px}.phase-column header b{font-size:18px}.phase-column header span{font:700 10px "SFMono-Regular",Consolas,monospace;color:#66635d}.phase-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:35px}.phase-actions a{min-height:44px;padding:0 11px;border:1px solid #9f9b90;text-decoration:none;display:inline-flex;align-items:center;font-size:12px;font-weight:800}.phase-actions a:hover{border-color:var(--ink);background:var(--signal)}.overview-note{display:flex;justify-content:space-between;gap:24px;margin-top:20px;color:#625f58;font-size:12px}.overview-note b{color:var(--ink)}
.action-slide{background:var(--ink)}.action-slide:nth-of-type(odd){background:#0c0d0a}.action-layout{display:grid;grid-template-rows:auto auto auto auto;gap:22px}.action-heading{display:grid;grid-template-columns:180px 1fr;gap:35px;align-items:end}.step-mark{padding:14px 0 12px;border-block:1px solid var(--line)}.step-mark span{display:block;color:var(--signal);font:800 44px/1 "SFMono-Regular",Consolas,monospace;letter-spacing:-.08em}.step-mark b,.step-mark small{display:block}.step-mark b{margin-top:18px;font-size:16px}.step-mark small{margin-top:4px;color:var(--dim);font-size:10px}.action-question{margin:14px 0 0;color:var(--muted);font-size:14px}.action-question strong{color:var(--paper)}.action-story{display:grid;grid-template-columns:.8fr 1.1fr 1.1fr;border-block:1px solid var(--line)}.action-story>div{min-height:116px;padding:18px 22px 20px;border-right:1px solid var(--line)}.action-story>div:first-child{padding-left:0}.action-story>div:last-child{border-right:0}.story-label{color:var(--signal)}.action-story p{margin:12px 0 0;max-width:47ch;color:#d6d2c7;font-size:15px;line-height:1.55}.pain-block p{color:var(--muted)}.action-proof{display:grid;grid-template-columns:.8fr 1.2fr;border:1px solid var(--line);background:var(--panel)}.proof-copy{padding:20px 22px}.proof-copy dl{display:grid;grid-template-columns:1fr 1fr;margin:14px 0 0}.proof-copy dl div{padding:10px 12px 10px 0;border-top:1px solid var(--line)}.proof-copy dt{color:var(--dim);font:800 9px "SFMono-Regular",Consolas,monospace}.proof-copy dd{margin:6px 0 0;font-size:12px;line-height:1.45}.case-note{margin:12px 0 0;color:var(--muted);font-size:11px;line-height:1.55}.case-note b{display:block;margin-bottom:4px;color:var(--signal)}.document-switcher{min-width:0;padding:17px 18px;border-left:1px solid var(--line);background:#0e0f0c}.doc-tabs{display:flex;gap:6px;overflow-x:auto}.doc-tab{min-height:44px;padding:0 10px;border:1px solid var(--line);background:transparent;color:var(--muted);font:700 10px "SFMono-Regular",Consolas,monospace;white-space:nowrap}.doc-tab[aria-selected="true"]{border-color:var(--signal);background:var(--signal);color:var(--ink)}.doc-panel{min-height:150px;max-height:210px;margin:10px 0 0;padding:14px;overflow:auto;border:1px solid var(--line);background:#080906;color:#d8d4c8;white-space:pre-wrap;font:10px/1.55 "SFMono-Regular",Consolas,monospace}.doc-panel[hidden]{display:none}.slide-route{display:flex;justify-content:space-between;gap:20px;color:var(--dim);font-size:11px}.slide-route b{color:var(--paper)}
.unknown-slide{background:var(--paper);color:var(--ink)}.unknown-slide .slide-kicker{color:#685800}.route-grid{display:grid;grid-template-columns:repeat(4,1fr);margin-top:42px;border-block:2px solid var(--ink)}.route-card{min-height:270px;padding:22px 20px;border-right:1px solid var(--ink)}.route-card:last-child{border-right:0}.route-card span{font:800 10px "SFMono-Regular",Consolas,monospace;color:#6a675f}.route-card h3{margin:42px 0 15px;font-size:25px;letter-spacing:-.04em}.route-card p{min-height:52px;color:#5e5b55;line-height:1.55}.route-card b,.route-card small{display:block}.route-card b{margin-top:18px;padding-top:14px;border-top:1px solid #a7a298;font-size:13px;line-height:1.55}.route-card small{margin-top:11px;color:#716e66}.route-card:hover{background:var(--signal)}
.roundtable-slide{background:var(--ink)}.roundtable-layout{display:grid;grid-template-columns:.9fr 1.1fr;gap:7vw;align-items:center}.roundtable-copy p{max-width:620px;color:var(--muted);font-size:16px;line-height:1.7}.roundtable-flow{border-block:1px solid var(--line)}.round-row{display:grid;grid-template-columns:82px 1fr;gap:22px;padding:22px 0;border-bottom:1px solid var(--line)}.round-row:last-child{border-bottom:0}.round-row span{color:var(--signal);font:800 10px "SFMono-Regular",Consolas,monospace}.round-row h3{margin:0 0 7px;font-size:22px}.round-row p{margin:0;color:var(--muted);line-height:1.6}.roundtable-note{margin-top:20px;color:var(--dim);font-size:12px}
.install-slide{background:var(--signal);color:var(--ink);align-items:flex-start}.install-slide .slide-inner{padding-top:3vh}.install-slide .slide-kicker{color:#5d5000}.install-head{display:flex;justify-content:space-between;gap:40px;align-items:end}.install-head p{max-width:510px;margin:0;color:#4d4509;line-height:1.6}.install-grid{display:grid;grid-template-columns:1.15fr .85fr;margin-top:34px;border-block:2px solid var(--ink)}.install-panel{padding:22px 24px 24px}.install-panel:first-child{padding-left:0;border-right:1px solid var(--ink)}.install-panel h3{margin:0 0 15px;font-size:19px}.install-panel pre{margin:0;padding:16px;overflow:auto;background:var(--ink);color:var(--paper);white-space:pre-wrap;font:10px/1.65 "SFMono-Regular",Consolas,monospace}.copy-row{display:flex;align-items:center;gap:12px;margin-top:12px}.copy-button{border-color:var(--ink);background:var(--ink);color:var(--paper)}.copy-status{font-size:11px;font-weight:800}.terminal-steps{margin:0;padding:0;list-style:none}.terminal-steps li{padding:12px 0;border-top:1px solid rgb(9 10 8 / 30%)}.terminal-steps li:first-child{border-top:0}.terminal-steps code{font-size:10px}.maintainer{margin-top:18px;border-top:1px solid rgb(9 10 8 / 35%)}.maintainer summary{min-height:48px;display:flex;align-items:center;justify-content:space-between;cursor:pointer;font-weight:850;list-style:none}.maintainer summary::-webkit-details-marker{display:none}.maintainer summary::after{content:"＋";font-size:20px}.maintainer[open] summary::after{content:"－"}.maintainer-grid{display:grid;grid-template-columns:1fr 1fr;gap:28px;padding:15px 0 5px}.maintainer h4{margin:0 0 12px}.reference-index{columns:2;margin:0;padding:0;list-style:none}.reference-index li{break-inside:avoid;margin-bottom:8px}.reference-index span{display:block;font-size:10px;font-weight:800}.reference-index code{font-size:8px}.document-index{display:flex;flex-wrap:wrap;gap:6px}.document-index code{padding:6px 8px;border:1px solid var(--ink);font-size:9px}.install-footer{display:flex;justify-content:space-between;gap:20px;margin-top:17px;font-size:10px}.install-footer a{min-height:44px;padding:0 8px;display:inline-flex;align-items:center;font-weight:850}
@media(max-width:1050px){.deck-nav{display:none}.slide{padding-inline:40px}.cover-grid,.roundtable-layout{grid-template-columns:1fr}.cover-aside{max-width:620px}.overview-head{grid-template-columns:1fr}.phase-strip{grid-template-columns:1fr}.phase-column{border-right:0;border-bottom:1px solid var(--ink)}.phase-column:last-child{border-bottom:0}.action-heading{grid-template-columns:130px 1fr}.action-proof{grid-template-columns:1fr}.document-switcher{border-left:0;border-top:1px solid var(--line)}.route-grid{grid-template-columns:1fr 1fr}.route-card:nth-child(2){border-right:0}.route-card:nth-child(-n+2){border-bottom:1px solid var(--ink)}}
@media(max-width:700px){body{overflow:auto}.deck-top{height:58px;grid-template-columns:1fr auto;padding:0 16px}.deck-progress{display:none}.deck-state span{display:none}.deck{height:100svh;scroll-snap-type:y proximity}.slide{min-height:100svh;padding:82px 18px 76px;align-items:flex-start;overflow:visible}.slide::before{display:none}.slide h1{font-size:clamp(50px,18vw,76px)}.slide h2{font-size:clamp(39px,13vw,58px)}.cover-grid{gap:38px}.cover-lede{font-size:17px}.cover-actions{display:grid}.primary-action,.secondary-action{width:100%}.overview-head{gap:25px}.phase-strip{margin-top:28px}.phase-column{padding-inline:0}.phase-actions{margin-top:18px}.overview-note{display:block}.overview-note span{display:block;margin-top:8px}.action-layout{gap:18px}.action-heading{grid-template-columns:1fr;gap:18px}.step-mark{display:grid;grid-template-columns:auto 1fr;gap:8px 14px;align-items:end}.step-mark span{grid-row:1/3}.action-story{grid-template-columns:1fr}.action-story>div{min-height:0;padding:16px 0;border-right:0;border-bottom:1px solid var(--line)}.action-story>div:last-child{border-bottom:0}.action-proof{display:block}.proof-copy{padding:18px 16px}.proof-copy dl{grid-template-columns:1fr}.document-switcher{padding:15px}.doc-panel{max-height:300px}.slide-route{display:block}.slide-route span{display:block;margin-top:7px}.route-grid{grid-template-columns:1fr;margin-top:28px}.route-card{min-height:0;padding:18px 0;border-right:0;border-bottom:1px solid var(--ink)!important}.route-card h3{margin:18px 0 10px}.route-card p{min-height:0}.roundtable-layout{gap:30px}.round-row{grid-template-columns:56px 1fr}.install-head{display:block}.install-head p{margin-top:18px}.install-grid{grid-template-columns:1fr}.install-panel{padding:18px 0}.install-panel:first-child{border-right:0;border-bottom:1px solid var(--ink)}.maintainer-grid{grid-template-columns:1fr}.reference-index{columns:1}.install-footer{display:block}.install-footer span{display:block;margin-top:6px}.deck-controls{right:12px;bottom:12px}.deck-controls button{min-width:44px;min-height:44px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.deck{scroll-behavior:auto}*,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important}.js .reveal{opacity:1;transform:none}}
@media print{body{overflow:visible;background:#fff}.deck-top,.deck-nav,.deck-controls{display:none}.deck{height:auto;overflow:visible}.slide{min-height:100vh;page-break-after:always;color:#111;background:#fff!important;border-bottom:0}.cover-slide,.roundtable-slide,.action-slide{color:#111}.slide-kicker,.story-label{color:#715f00}.action-proof,.document-switcher{background:#fff}.doc-panel{color:#111;background:#f4f1e8}}
</style>
<script id="runtime-bootstrap">document.documentElement.classList.add('js')</script>
</head>
<body data-source-digest="__DIGEST__">
<!-- GENERATED FILE — DO NOT EDIT. Source: SKILL.md + CHANGELOG.md + references/*.md + selected templates. -->
<a class="skip" href="#slide-cover">跳到演示文稿</a>
<header class="deck-top"><a class="brand" href="#slide-cover">workflow <span>__VERSION_LABEL__</span></a><div class="deck-progress" aria-hidden="true"><span></span></div><div class="deck-state" aria-live="polite"><i></i><span>当前</span><b data-deck-label>开场</b><em data-deck-count>01 / 12</em></div></header>
<nav class="deck-nav" aria-label="演示文稿导航">__DECK_NAV__</nav>
<div class="deck-controls" aria-label="翻页控制"><button type="button" data-deck-prev aria-label="上一页">↑</button><button type="button" data-deck-next aria-label="下一页">↓</button></div>
<main class="deck" id="main">
<section class="slide cover-slide" id="slide-cover" data-label="开场" data-chapter="开始" data-user-layer><div class="slide-inner cover-grid"><div class="reveal"><p class="slide-kicker">复杂任务的单一工作流</p><h1>把模糊目标，变成已验证结果。</h1><p class="cover-lede">AI 负责查清、想透、拆好、做成、验真；你只在价值、取舍、验收和授权时决定。</p><div class="cover-actions"><button class="primary-action" type="button" data-slide-target="slide-overview">开始演示</button><button class="secondary-action" type="button" data-slide-target="slide-install">如何安装</button></div></div><aside class="cover-aside reveal"><p>七个动作不是七场仪式。已有证据就快速通过；简单事直接做。每一步只增加结果、降低风险、减少重复。</p></aside></div></section>
<section class="slide overview-slide" id="slide-overview" data-label="全景" data-chapter="总览" data-user-layer><div class="slide-inner"><div class="overview-head reveal"><div><p class="slide-kicker">为什么需要 workflow</p><h2>复杂工作最怕的，不是难，而是一路都在猜。</h2></div><p>目标没说清就开工，方案没比较就押注，任务没验收就并行，代码写完就宣布交付。workflow 用三段七动作，把每一次猜测变成事实、决策或证据。</p></div><div class="phase-strip reveal"><article class="phase-column"><header><b>计划</b><span>不确定 → 承诺</span></header><div class="phase-actions"><a href="#slide-需求澄清">需求澄清</a><a href="#slide-选定方案">选定方案</a><a href="#slide-拆成任务">拆成任务</a></div></article><article class="phase-column"><header><b>执行</b><span>承诺 → 证据</span></header><div class="phase-actions"><a href="#slide-执行任务">执行任务</a><a href="#slide-验收交付">验收交付</a></div></article><article class="phase-column"><header><b>复盘</b><span>结果 → 能力</span></header><div class="phase-actions"><a href="#slide-提炼经验">提炼经验</a><a href="#slide-回灌改进">回灌改进</a></div></article></div><p class="overview-note reveal"><b>证据是快速通过的凭证，不是额外仪式。</b><span>轻任务绕过完整流程，关键价值门、验收门和授权门不降级。</span></p></div></section>
__ACTION_SLIDES__
<section class="slide unknown-slide" id="slide-unknowns" data-label="四路未知" data-chapter="方法" data-user-layer><div class="slide-inner"><div class="overview-head reveal"><div><p class="slide-kicker">不确定，不等于追问</p><h2>先判断未知属于哪一路。</h2></div><p>workflow 不把调查工作转嫁给用户，也不把需要决策的取舍伪装成技术问题。四路未知处理完，都回到当前业务动作。</p></div><div class="route-grid">__UNKNOWN_CARDS__</div></div></section>
<section class="slide roundtable-slide" id="slide-roundtable" data-label="专家圆桌" data-chapter="方法" data-user-layer><div class="slide-inner roundtable-layout"><div class="roundtable-copy reveal"><p class="slide-kicker">复杂决策才启用</p><h2>先看见整片森林，再选路线。</h2><p>workflow 不预设专家名单。它先判断“把这件事做到 90 分，谁最能改变结论”，再邀请 3–5 个关键视角，用同一份事实完成独立判断和相互挑战。</p><p class="roundtable-note">简单、低风险、容易回退的任务不会为了“专家感”强行开会。</p></div><div class="roundtable-flow reveal"><article class="round-row"><span>01</span><div><h3>独立发散</h3><p>每个专家分别勾勒终局、依赖、盲区和会改变判断的新证据。</p></div></article><article class="round-row"><span>02</span><div><h3>交叉质询</h3><p>挑战未经证明的假设、局部最优和被忽略的角色或生命周期。</p></div></article><article class="round-row"><span>03</span><div><h3>主持收敛</h3><p>合成完整森林图景，比较 2–3 条路线，给出推荐、备选和删除理由。</p></div></article></div></div></section>
<section class="slide install-slide" id="slide-install" data-label="安装" data-chapter="开始使用"><div class="slide-inner"><div class="install-head reveal"><div><p class="slide-kicker">最后一步</p><h2>安装 workflow。</h2></div><p>只安装一个 skill。最省事的方式，是把左侧指令完整复制给你的 Agent；它会自动识别自己的 skills 目录并在安装后验证。</p></div><div class="install-grid reveal"><article class="install-panel"><h3>复制给你的 Agent</h3><pre><code id="agent-prompt">__AGENT_PROMPT__</code></pre><div class="copy-row"><button class="copy-button" type="button" data-copy-target="agent-prompt">复制安装指令</button><span class="copy-status" aria-live="polite"></span></div></article><article class="install-panel"><h3>或在终端安装</h3><ol class="terminal-steps"><li><code>git clone --depth 1 https://github.com/qzl0215/workflow.git</code></li><li><code>cd workflow</code></li><li><code>python3 scripts/install.py install</code></li><li><code>python3 scripts/install.py check --target &quot;&lt;skills父目录&gt;&quot;</code></li></ol><details class="maintainer"><summary>查看维护者索引</summary><div class="maintainer-grid"><div><h4>14 项能力</h4><ul class="reference-index">__REFERENCE_INDEX__</ul></div><div><h4>七类工作文档</h4><div class="document-index">__DOCUMENT_INDEX__</div></div></div></details></article></div><footer class="install-footer reveal"><span>作者 zhonglin · 页面由正式来源生成，不手改。</span><span><a href="__REPOSITORY__">GitHub</a> · <code>source sha256 __DIGEST__</code></span></footer></div></section>
</main>
<script type="application/json" id="workflow-actions">__ACTION_JSON__</script>
<script>
const deck=document.querySelector('.deck');const slides=[...document.querySelectorAll('.slide')];const navButtons=[...document.querySelectorAll('[data-slide-target]')];const prevButton=document.querySelector('[data-deck-prev]');const nextButton=document.querySelector('[data-deck-next]');const label=document.querySelector('[data-deck-label]');const counter=document.querySelector('[data-deck-count]');const progress=document.querySelector('.deck-progress span');let currentIndex=0;let replaceTimer;
function goTo(index,focus=false){const target=slides[Math.max(0,Math.min(slides.length-1,index))];target.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});if(focus)target.setAttribute('tabindex','-1'),target.focus({preventScroll:true})}
function update(index){currentIndex=index;const slide=slides[index];label.textContent=slide.dataset.label;counter.textContent=String(index+1).padStart(2,'0')+' / '+String(slides.length).padStart(2,'0');progress.style.transform='scaleX('+((index+1)/slides.length)+')';prevButton.disabled=index===0;nextButton.disabled=index===slides.length-1;navButtons.forEach(button=>button.setAttribute('aria-current',String(button.dataset.slideTarget===slide.id)));clearTimeout(replaceTimer);replaceTimer=setTimeout(()=>history.replaceState(null,'','#'+slide.id),160)}
const observer=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(!entry.isIntersecting||entry.intersectionRatio<.52)return;const index=slides.indexOf(entry.target);slides.forEach((slide,i)=>slide.classList.toggle('is-active',i===index));update(index)})},{root:deck,threshold:[.52,.7]});slides.forEach(slide=>observer.observe(slide));
navButtons.forEach(button=>button.addEventListener('click',event=>{if(button.tagName==='A')return;event.preventDefault();goTo(slides.findIndex(slide=>slide.id===button.dataset.slideTarget))}));prevButton.addEventListener('click',()=>goTo(currentIndex-1));nextButton.addEventListener('click',()=>goTo(currentIndex+1));
document.addEventListener('keydown',event=>{if(event.target.closest('.doc-tab,summary,pre'))return;const nextKeys=['ArrowDown','ArrowRight','PageDown',' '];const prevKeys=['ArrowUp','ArrowLeft','PageUp'];if(nextKeys.includes(event.key)){event.preventDefault();goTo(currentIndex+1)}else if(prevKeys.includes(event.key)){event.preventDefault();goTo(currentIndex-1)}else if(event.key==='Home'){event.preventDefault();goTo(0)}else if(event.key==='End'){event.preventDefault();goTo(slides.length-1)}});
document.querySelectorAll('.doc-tab').forEach(button=>{button.addEventListener('click',()=>{const switcher=button.closest('.document-switcher');switcher.querySelectorAll('.doc-tab').forEach(tab=>{const selected=tab===button;tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1});switcher.querySelectorAll('.doc-panel').forEach(panel=>panel.hidden=panel.id!==button.getAttribute('aria-controls'))});button.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight'].includes(event.key))return;event.preventDefault();const tabs=[...button.closest('.doc-tabs').querySelectorAll('.doc-tab')];const index=tabs.indexOf(button);const next=tabs[(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length];next.focus();next.click()})});
const copyButton=document.querySelector('[data-copy-target]');copyButton.addEventListener('click',async()=>{const target=document.getElementById(copyButton.dataset.copyTarget);try{await navigator.clipboard.writeText(target.textContent.trim())}catch(_){const area=document.createElement('textarea');area.value=target.textContent.trim();area.setAttribute('readonly','');area.style.position='fixed';area.style.opacity='0';document.body.appendChild(area);area.select();document.execCommand('copy');area.remove()}document.querySelector('.copy-status').textContent='已复制';copyButton.textContent='已复制'});
document.addEventListener('pointermove',event=>{document.body.style.setProperty('--pointer-x',String(event.clientX/innerWidth*100));document.body.style.setProperty('--pointer-y',String(event.clientY/innerHeight*100))},{passive:true});
const initialIndex=slides.findIndex(slide=>'#'+slide.id===location.hash);slides[Math.max(0,initialIndex)].classList.add('is-active');update(Math.max(0,initialIndex));
</script>
</body></html>
'''

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the generated document is stale")
    args = parser.parse_args()
    try:
        generated, _ = build()
    except ValueError as exc:
        print(f"visual map source error: {exc}", file=sys.stderr)
        return 2
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != generated:
            print(f"stale visual map: {OUTPUT}", file=sys.stderr)
            return 1
        print("workflow_visual_map: OK")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generated, encoding="utf-8")
    print(f"generated {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
