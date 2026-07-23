#!/usr/bin/env python3
"""Generate the standalone workflow self-introduction from formal sources."""

from __future__ import annotations

import argparse
import hashlib
import html
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

VISUAL_TEMPLATE_NAMES = (
    "index.md",
    "findings.md",
    "pre-plan-contract.md",
    "task_plan.md",
    "implementation-plan.md",
    "progress.md",
    "task-owner-prompt.md",
)

STAGE_QUESTIONS = {
    "需求澄清": "为什么做，怎样算成？",
    "选定方案": "哪条路最值得走？",
    "拆成任务": "怎样拆才可做可验？",
    "执行任务": "现在最该做成什么？",
    "验收交付": "凭什么完成，交到哪？",
    "提炼经验": "什么会改变下一次？",
    "回灌改进": "哪里应该永久变好？",
}

UNKNOWN_SUMMARIES = {
    "事实可查": ("缺客观事实", "我去查项目、数据、工具和可信来源。"),
    "取舍待定": ("缺少你的选择", "我给出推荐和代价，等你做决定。"),
    "假设待验": ("讨论无法证明", "我设计最小实验，让真假可验证。"),
    "外部待解": ("需要范围外条件", "我写清依赖、解锁条件和安全等待方式。"),
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


def source_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(PACKAGE).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:12]


def phase_for(index: int) -> tuple[str, str]:
    if index <= 3:
        return "计划", "不确定 → 承诺"
    if index <= 5:
        return "执行", "承诺 → 证据"
    return "复盘", "结果 → 能力"


def render_stage_cards(state_rows: list[list[str]]) -> str:
    cards: list[str] = []
    for index, row in enumerate(state_rows, 1):
        name = row[0]
        phase, _ = phase_for(index)
        cards.append(
            f'<article class="stage-card" data-stage="{html.escape(name)}">'
            f'<header><span>{index:02d}</span><small>{phase}</small></header>'
            f'<h3>{html.escape(name)}</h3>'
            f'<p>{html.escape(STAGE_QUESTIONS[name])}</p>'
            "</article>"
        )
    return "".join(cards)


def render_unknown_cards(unknown_rows: list[list[str]]) -> str:
    cards: list[str] = []
    for index, (name, _essence, _handling, _return_rule) in enumerate(unknown_rows, 1):
        essence, handling = UNKNOWN_SUMMARIES[name]
        cards.append(
            '<article class="unknown-card">'
            f'<span>{index:02d}</span><h3>{html.escape(name)}</h3>'
            f'<p>{html.escape(handling)}</p><small>{html.escape(essence)}</small>'
            "</article>"
        )
    return "".join(cards)


def render_reference_index(route_rows: list[list[str]]) -> str:
    items: list[str] = []
    for kind, signal, target in route_rows:
        filename = Path(target).name
        ref_text = (REFERENCES / filename).read_text(encoding="utf-8")
        title = re.search(r"^#\s+(.+)$", ref_text, re.MULTILINE)
        if title is None:
            raise ValueError(f"missing reference title: {filename}")
        items.append(
            "<li>"
            f'<span>{html.escape(clean(title.group(1)))}</span>'
            f'<small>{html.escape(kind)} · {html.escape(signal)}</small>'
            f"<code>{html.escape(target)}</code>"
            "</li>"
        )
    return "".join(items)


def render_document_index() -> str:
    return "".join(f"<code>{html.escape(filename)}</code>" for filename in VISUAL_TEMPLATE_NAMES)


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

    current_release = re.search(
        rf"^## \[{re.escape(current_version)}\].*?(?=^## \[|\Z)",
        changelog_text,
        re.MULTILINE | re.DOTALL,
    )
    if current_release is None:
        raise ValueError("current changelog does not support the visual self-introduction")

    state_rows = table_rows(
        source_section(skill_text, "## 状态接口与硬门", "## 用户交接"),
        5,
    )
    unknown_rows = table_rows(
        source_section(skill_text, "## 需求澄清中的四路未知", "## harness 深度"),
        4,
    )
    route_rows = table_rows(
        source_section(skill_text, "## 按需路由", "## 文件真源"),
        3,
    )
    if len(state_rows) != 7 or len(unknown_rows) != 4 or len(route_rows) != 14:
        raise ValueError(
            "unexpected contract shape: "
            f"states={len(state_rows)}, unknowns={len(unknown_rows)}, routes={len(route_rows)}"
        )
    if tuple(STAGE_QUESTIONS) != tuple(row[0] for row in state_rows):
        raise ValueError("stage question registry does not match canonical stage order")
    if tuple(UNKNOWN_SUMMARIES) != tuple(row[0] for row in unknown_rows):
        raise ValueError("unknown summary registry does not match canonical route order")

    routed_files = {Path(row[2]).name for row in route_rows}
    if set(PRIMARY_OWNER_FILES) | set(HARNESS_FILES) != routed_files:
        raise ValueError("capability registry does not match routed references")
    missing_templates = [
        filename for filename in VISUAL_TEMPLATE_NAMES if not (TEMPLATES / filename).is_file()
    ]
    if missing_templates:
        raise ValueError(f"missing visual templates: {', '.join(missing_templates)}")

    digest_paths = [SKILL, CHANGELOG, *sorted(REFERENCES.glob("*.md"))]
    digest_paths.extend(TEMPLATES / name for name in VISUAL_TEMPLATE_NAMES)
    digest = source_digest(digest_paths)

    replacements = {
        "__DIGEST__": digest,
        "__VERSION__": html.escape(current_version),
        "__VERSION_LABEL__": html.escape(version_label),
        "__REPOSITORY__": html.escape(REPOSITORY, quote=True),
        "__AGENT_PROMPT__": html.escape(AGENT_PROMPT),
        "__STAGE_CARDS__": render_stage_cards(state_rows),
        "__UNKNOWN_CARDS__": render_unknown_cards(unknown_rows),
        "__REFERENCE_INDEX__": render_reference_index(route_rows),
        "__DOCUMENT_INDEX__": render_document_index(),
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
<meta name="description" content="workflow 的当前自述：一眼看懂它如何把复杂目标推进到已验证结果。">
<meta name="color-scheme" content="dark">
<title>我是 workflow｜复杂工作，推进到真的完成</title>
<style>
:root{--ink:#0b0c09;--ink-2:#13140f;--paper:#f1eee4;--signal:#ffd43b;--signal-2:#ffe88f;--muted:#aaa99f;--line:#35362e;--paper-line:#b9b4a8;--gutter:clamp(20px,4vw,96px);font-family:"Avenir Next","SF Pro Display","SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;color:var(--paper);background:var(--ink)}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:76px}html,body{margin:0;min-width:320px;background:var(--ink)}body{overflow-x:hidden}button,a{font:inherit;color:inherit}a{text-decoration:none}button{cursor:pointer}code,.mono{font-family:"SFMono-Regular",Consolas,monospace}:focus-visible{outline:3px solid var(--signal);outline-offset:3px}
.skip{position:fixed;z-index:100;left:16px;top:12px;transform:translateY(-180%);padding:11px 15px;background:var(--signal);color:var(--ink);font-weight:850}.skip:focus{transform:none}
.page-shell{width:calc(100% - (2 * var(--gutter)));margin-inline:auto}.topbar{position:sticky;z-index:50;top:0;height:72px;border-bottom:1px solid rgb(241 238 228 / 12%);background:rgb(11 12 9 / 90%);backdrop-filter:blur(16px)}.topbar .page-shell{height:100%;display:flex;align-items:center;justify-content:space-between;gap:28px}.brand{min-height:44px;display:flex;align-items:center;gap:11px;font-weight:950;letter-spacing:-.04em}.brand span{color:var(--signal);font:800 9px "SFMono-Regular",Consolas,monospace;letter-spacing:.08em}.page-nav{display:flex;align-items:center;gap:clamp(14px,2vw,34px)}.page-nav a{min-height:44px;display:inline-flex;align-items:center;color:var(--muted);font-size:12px;font-weight:800}.page-nav a:hover{color:var(--signal)}
.hero{position:relative;isolation:isolate;min-height:calc(100svh - 72px);display:flex;align-items:center;padding-block:clamp(70px,8vh,140px);overflow:hidden}.hero::before{content:"";position:absolute;z-index:-2;inset:0;background:linear-gradient(90deg,transparent 49.95%,rgb(241 238 228 / 5%) 50%,transparent 50.05%)}.hero::after{content:"";position:absolute;z-index:-1;width:min(58vw,1100px);aspect-ratio:1;right:-12vw;top:-20vw;border-radius:50%;background:radial-gradient(circle,rgb(255 212 59 / 14%),transparent 67%);filter:blur(10px)}.hero-grid{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(280px,.45fr);gap:clamp(48px,7vw,150px);align-items:end}.eyebrow{margin:0 0 24px;color:var(--signal);font:800 11px "SFMono-Regular",Consolas,monospace;letter-spacing:.16em;text-transform:uppercase}.hero h1{margin:0;max-width:14ch;font-size:clamp(58px,6.2vw,132px);font-weight:760;line-height:.9;letter-spacing:-.075em;text-wrap:balance}.hero h1 span{display:block;color:var(--signal)}.hero-lede{max-width:840px;margin:36px 0 0;color:#cfccc1;font-size:clamp(18px,1.45vw,28px);line-height:1.55}.hero-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:32px}.button{min-height:48px;padding:0 19px;border:1px solid var(--signal);display:inline-flex;align-items:center;justify-content:center;font-weight:900}.button-primary{background:var(--signal);color:var(--ink)}.button-secondary{background:transparent}.button:hover{border-color:var(--paper);background:var(--paper);color:var(--ink)}.identity-card{border-top:2px solid var(--signal);padding-top:24px}.identity-card p{margin:0;color:var(--muted);font-size:15px;line-height:1.72}.identity-card strong{display:block;margin-bottom:12px;color:var(--paper);font-size:21px}.identity-facts{display:grid;gap:0;margin-top:30px;border-bottom:1px solid var(--line)}.identity-facts span{padding:14px 0;border-top:1px solid var(--line);color:#d9d5ca;font-size:12px;font-weight:800}.identity-facts b{color:var(--signal);font:800 10px "SFMono-Regular",Consolas,monospace}
.proof-strip{border-block:1px solid var(--line);background:var(--ink-2)}.proof-strip .page-shell{display:grid;grid-template-columns:repeat(3,1fr)}.proof-strip p{margin:0;padding:22px 24px;border-right:1px solid var(--line);font-size:13px;font-weight:800}.proof-strip p:first-child{padding-left:0}.proof-strip p:last-child{border-right:0}.proof-strip span{color:var(--signal);font:800 10px "SFMono-Regular",Consolas,monospace}
.section{padding-block:clamp(82px,9vw,180px)}.section-head{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(280px,.55fr);gap:clamp(40px,7vw,140px);align-items:end}.kicker{margin:0 0 18px;color:#6a5a00;font:800 10px "SFMono-Regular",Consolas,monospace;letter-spacing:.16em;text-transform:uppercase}.section h2{margin:0;max-width:16ch;font-size:clamp(44px,4.8vw,96px);font-weight:760;line-height:.94;letter-spacing:-.065em;text-wrap:balance}.section-intro{margin:0;color:#5d5a53;font-size:clamp(16px,1.2vw,22px);line-height:1.7}.path-section{background:var(--paper);color:var(--ink)}.phase-legend{display:grid;grid-template-columns:3fr 2fr 2fr;margin-top:clamp(38px,5vw,80px);border-block:2px solid var(--ink)}.phase-legend div{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:16px 20px;border-right:1px solid var(--ink)}.phase-legend div:first-child{padding-left:0}.phase-legend div:last-child{border-right:0}.phase-legend b{font-size:16px}.phase-legend span{color:#67645c;font:750 10px "SFMono-Regular",Consolas,monospace}.stage-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));margin-top:24px;border-block:1px solid var(--ink)}.stage-card{min-width:0;min-height:230px;padding:20px;border-right:1px solid var(--ink)}.stage-card:first-child{padding-left:0}.stage-card:last-child{border-right:0}.stage-card header{display:flex;align-items:center;justify-content:space-between;gap:12px}.stage-card header span{color:#6f6c64;font:800 10px "SFMono-Regular",Consolas,monospace}.stage-card header small{padding:4px 7px;border:1px solid #9e9a90;font-size:9px;font-weight:850}.stage-card h3{margin:54px 0 12px;font-size:clamp(20px,1.45vw,30px);letter-spacing:-.045em}.stage-card p{margin:0;color:#5f5c55;font-size:13px;line-height:1.55}.stage-card:hover{background:var(--signal)}.stage-card:hover header span,.stage-card:hover p{color:var(--ink)}.path-note{display:flex;justify-content:space-between;gap:30px;margin:22px 0 0;color:#5c5952;font-size:13px}.path-note b{color:var(--ink)}
.working-section{background:var(--ink);color:var(--paper)}.working-grid{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);border:1px solid var(--line)}.working-panel{padding:clamp(30px,4vw,78px);background:var(--ink)}.working-panel.is-signal{background:var(--signal);color:var(--ink)}.working-panel .kicker{color:var(--signal)}.working-panel.is-signal .kicker{color:#5d5000}.working-panel h2{max-width:11ch;font-size:clamp(40px,4vw,82px)}.working-list{margin:clamp(36px,4vw,68px) 0 0;padding:0;list-style:none}.working-list li{display:grid;grid-template-columns:44px 1fr;gap:18px;padding:22px 0;border-top:1px solid var(--line)}.is-signal .working-list li{border-color:rgb(11 12 9 / 35%)}.working-list span{font:800 10px "SFMono-Regular",Consolas,monospace}.working-list h3{margin:0 0 8px;font-size:18px}.working-list p{margin:0;color:var(--muted);font-size:14px;line-height:1.6}.is-signal .working-list p{color:#51480b}
.unknown-section{background:var(--paper);color:var(--ink)}.unknown-grid{display:grid;grid-template-columns:repeat(4,1fr);margin-top:clamp(42px,5vw,86px);border-block:2px solid var(--ink)}.unknown-card{min-height:280px;padding:22px 24px;border-right:1px solid var(--ink)}.unknown-card:first-child{padding-left:0}.unknown-card:last-child{border-right:0}.unknown-card span{color:#706d65;font:800 10px "SFMono-Regular",Consolas,monospace}.unknown-card h3{margin:52px 0 16px;font-size:clamp(24px,1.8vw,34px);letter-spacing:-.045em}.unknown-card p{margin:0;font-weight:850;line-height:1.55}.unknown-card small{display:block;margin-top:16px;color:#66635c;line-height:1.55}.unknown-card:hover{background:var(--signal)}
.truth-section{background:var(--ink-2)}.truth-grid{display:grid;grid-template-columns:.72fr 1.28fr;gap:clamp(50px,8vw,160px);align-items:start}.truth-copy h2{max-width:10ch}.truth-copy p{max-width:570px;color:var(--muted);font-size:16px;line-height:1.75}.truth-cards{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--line)}.truth-card{min-height:190px;padding:26px 26px 30px 0;border-bottom:1px solid var(--line)}.truth-card:nth-child(odd){border-right:1px solid var(--line)}.truth-card:nth-child(even){padding-left:26px}.truth-card span{color:var(--signal);font:800 10px "SFMono-Regular",Consolas,monospace}.truth-card h3{margin:34px 0 10px;font-size:22px}.truth-card p{margin:0;color:var(--muted);font-size:13px;line-height:1.6}
.install-section{background:var(--signal);color:var(--ink)}.install-head{display:grid;grid-template-columns:1fr .55fr;gap:clamp(40px,7vw,140px);align-items:end}.install-head .kicker{color:#5d5000}.install-head p{margin:0;color:#51480b;font-size:16px;line-height:1.7}.install-grid{display:grid;grid-template-columns:1.15fr .85fr;margin-top:clamp(38px,5vw,76px);border-block:2px solid var(--ink)}.install-panel{padding:26px 28px 30px}.install-panel:first-child{padding-left:0;border-right:1px solid var(--ink)}.install-panel h3{margin:0 0 18px;font-size:20px}.install-panel pre{margin:0;padding:20px;overflow:auto;background:var(--ink);color:var(--paper);white-space:pre-wrap;font:11px/1.7 "SFMono-Regular",Consolas,monospace}.copy-row{display:flex;align-items:center;gap:14px;margin-top:14px}.copy-button{min-height:48px;padding:0 18px;border:1px solid var(--ink);background:var(--ink);color:var(--paper);font-weight:900}.copy-button:hover{background:var(--paper);color:var(--ink)}.copy-status{font-size:11px;font-weight:850}.terminal-steps{margin:0;padding:0;list-style:none}.terminal-steps li{padding:13px 0;border-top:1px solid rgb(11 12 9 / 32%)}.terminal-steps li:first-child{border-top:0}.terminal-steps code{font-size:11px}.maintenance{margin-top:20px;border-top:1px solid rgb(11 12 9 / 40%)}.maintenance summary{min-height:52px;display:flex;align-items:center;justify-content:space-between;cursor:pointer;font-weight:900;list-style:none}.maintenance summary::-webkit-details-marker{display:none}.maintenance summary::after{content:"＋";font-size:21px}.maintenance[open] summary::after{content:"－"}.maintenance-grid{display:grid;grid-template-columns:1.35fr .65fr;gap:36px;padding:18px 0 8px}.maintenance h4{margin:0 0 14px}.reference-index{display:grid;grid-template-columns:1fr 1fr;gap:12px 20px;margin:0;padding:0;list-style:none}.reference-index li{min-width:0;padding-top:10px;border-top:1px solid rgb(11 12 9 / 30%)}.reference-index span,.reference-index small,.reference-index code{display:block}.reference-index span{font-size:11px;font-weight:850}.reference-index small{margin-top:4px;color:#63590e;font-size:9px;line-height:1.4}.reference-index code{margin-top:4px;overflow-wrap:anywhere;font-size:8px}.document-index{display:flex;flex-wrap:wrap;gap:7px}.document-index code{padding:7px 9px;border:1px solid var(--ink);font-size:9px}.footer{display:flex;justify-content:space-between;gap:24px;padding-block:24px;font-size:10px}.footer a{min-height:44px;display:inline-flex;align-items:center;font-weight:900}
@media(min-width:1800px){:root{--gutter:clamp(96px,4vw,168px)}.topbar{height:84px}.hero{min-height:calc(100svh - 84px)}.hero-grid{grid-template-columns:minmax(0,1.7fr) minmax(360px,.3fr)}.hero h1{font-size:clamp(108px,5.2vw,168px)}.hero-lede{max-width:1100px}.stage-card{min-height:300px;padding:30px}.stage-card h3{margin-top:86px}.unknown-card{min-height:340px;padding:30px}.unknown-card h3{margin-top:78px}}
@media(max-width:1380px){.stage-grid{grid-template-columns:repeat(4,1fr)}.stage-card{border-bottom:1px solid var(--ink)}.stage-card:nth-child(4n){border-right:0}.stage-card:nth-child(5){padding-left:0}.unknown-grid{grid-template-columns:1fr 1fr}.unknown-card:nth-child(2){border-right:0}.unknown-card:nth-child(-n+2){border-bottom:1px solid var(--ink)}}
@media(max-width:940px){.hero-grid,.section-head,.truth-grid,.install-head{grid-template-columns:1fr}.hero-grid{align-items:start}.hero h1{max-width:13ch}.identity-card{max-width:620px}.stage-grid{grid-template-columns:1fr 1fr}.stage-card:nth-child(even){border-right:0}.stage-card:nth-child(odd){padding-left:0;border-right:1px solid var(--ink)}.phase-legend{grid-template-columns:1fr}.phase-legend div{padding-inline:0;border-right:0;border-bottom:1px solid var(--ink)}.phase-legend div:last-child{border-bottom:0}.working-grid{grid-template-columns:1fr}.truth-copy h2{max-width:14ch}.install-grid{grid-template-columns:1fr}.install-panel{padding-inline:0}.install-panel:first-child{border-right:0;border-bottom:1px solid var(--ink)}.maintenance-grid{grid-template-columns:1fr}}
@media(max-width:640px){:root{--gutter:18px}.topbar{height:62px}.page-nav a:not(:last-child){display:none}.hero{min-height:auto;padding-block:72px}.hero::before{display:none}.hero h1{font-size:clamp(48px,15vw,74px)}.hero-lede{margin-top:26px;font-size:17px}.hero-actions{display:grid}.button{width:100%}.proof-strip .page-shell{grid-template-columns:1fr}.proof-strip p{padding:16px 0;border-right:0;border-bottom:1px solid var(--line)}.proof-strip p:last-child{border-bottom:0}.section{padding-block:76px}.section h2{font-size:clamp(39px,12vw,58px)}.stage-grid,.unknown-grid,.truth-cards{grid-template-columns:1fr}.stage-card,.stage-card:nth-child(n),.unknown-card,.unknown-card:nth-child(n){min-height:0;padding:20px 0;border-right:0;border-bottom:1px solid var(--ink)}.stage-card h3,.unknown-card h3{margin:28px 0 10px}.path-note{display:block}.path-note span{display:block;margin-top:9px}.working-panel{padding:34px 24px}.working-list li{grid-template-columns:34px 1fr}.truth-card,.truth-card:nth-child(n){min-height:0;padding:22px 0;border-right:0}.install-panel pre{font-size:9px}.reference-index{grid-template-columns:1fr}.footer{display:block}.footer span{display:block;margin-top:6px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important}}
@media print{.topbar,.hero-actions,.copy-row{display:none}.hero{min-height:auto}.section{padding-block:50px}.page-shell{width:100%}.hero,.working-section,.truth-section{color:#111;background:#fff}.identity-card,.working-panel,.truth-card{border-color:#aaa}.working-grid{display:block}.working-panel{color:#111;background:#fff}.working-panel p,.truth-section p{color:#333}.install-section{background:#fff}}
</style>
</head>
<body data-source-digest="__DIGEST__">
<!-- GENERATED FILE — DO NOT EDIT. Source: SKILL.md + CHANGELOG.md + references/*.md + selected templates. -->
<a class="skip" href="#intro">跳到正文</a>
<header class="topbar">
  <div class="page-shell">
    <a class="brand" href="#intro">workflow <span>__VERSION_LABEL__</span></a>
    <nav class="page-nav" aria-label="页面导航">
      <a href="#path">主链</a>
      <a href="#working">协作方式</a>
      <a href="#unknowns">处理未知</a>
      <a href="#install">安装</a>
    </nav>
  </div>
</header>
<main>
  <section class="hero" id="intro" data-user-layer>
    <div class="page-shell hero-grid">
      <div>
        <p class="eyebrow">复杂工作的 AI 总导演</p>
        <h1><span>我是 workflow。</span>复杂工作，交给我推进到真的完成。</h1>
        <p class="hero-lede">你给我目标。我先查事实和已有真源，再和你确认关键取舍；之后我会拆计划、连续执行、用新证据验收，并只在需要你决定或授权时停下。</p>
        <div class="hero-actions">
          <a class="button button-primary" href="#path">一眼看懂我</a>
          <a class="button button-secondary" href="#install">安装我</a>
        </div>
      </div>
      <aside class="identity-card">
        <p><strong>我是单包协议。</strong>只安装这个目录，我就能独立运行；不默认依赖别的技能，也不会为了显得完整给项目堆文档。</p>
        <div class="identity-facts">
          <span><b>01</b> 一条业务主链</span>
          <span><b>07</b> 七个证据检查点</span>
          <span><b>14</b> 十四项按需能力</span>
          <span><b>__VERSION__</b> 当前协议版本</span>
        </div>
      </aside>
    </div>
  </section>
  <div class="proof-strip" aria-label="三个工作原则">
    <div class="page-shell">
      <p><span>轻任务</span><br>答案明确，就直接做完并验证。</p>
      <p><span>复杂任务</span><br>只走必要动作，不走形式流程。</p>
      <p><span>完成判断</span><br>没有新证据，我不会说已经完成。</p>
    </div>
  </div>

  <section class="section path-section" id="path" data-user-layer>
    <div class="page-shell">
      <header class="section-head">
        <div><p class="kicker">计划 · 执行 · 复盘</p><h2>我只有一条主链。</h2></div>
        <p class="section-intro">七个动作各自只回答一个业务问题。证据已经存在就快速通过；发现缺口，就回到真正产生缺口的位置。</p>
      </header>
      <div class="phase-legend" aria-label="三段流程">
        <div><b>计划</b><span>不确定 → 承诺</span></div>
        <div><b>执行</b><span>承诺 → 证据</span></div>
        <div><b>复盘</b><span>结果 → 能力</span></div>
      </div>
      <div class="stage-grid">__STAGE_CARDS__</div>
      <p class="path-note"><b>这不是七场固定仪式。</b><span>简单事整体走短路；价值、完整计划、验收和授权四道门不会降级。</span></p>
    </div>
  </section>

  <section class="section working-section" id="working" data-user-layer>
    <div class="page-shell working-grid">
      <article class="working-panel">
        <p class="kicker">默认连续推进</p>
        <h2>大多数时候，我会自己往前走。</h2>
        <ol class="working-list">
          <li><span>01</span><div><h3>先查，再问</h3><p>项目、工具、数据和已有规则能回答的事实，我自己查，不把调查工作转给你。</p></div></li>
          <li><span>02</span><div><h3>按任务深度工作</h3><p>局部小事轻量处理；遇到重要体验、并行价值或高风险，再按需加深。</p></div></li>
          <li><span>03</span><div><h3>状态变化就播报</h3><p>我会给你最新进度、实际成果和下一步，但普通进度不会打断连续执行。</p></div></li>
          <li><span>04</span><div><h3>只保留最小真源</h3><p>能补现有文件就不新建；文档没有独立读者和决策用途，就不留下。</p></div></li>
        </ol>
      </article>
      <article class="working-panel is-signal">
        <p class="kicker">需要你接棒时才停</p>
        <h2>这些节点，我一定等你。</h2>
        <ol class="working-list">
          <li><span>01</span><div><h3>纠正目标</h3><p>我的关键理解会改变结果、范围或验收时，请你校正。</p></div></li>
          <li><span>02</span><div><h3>选择方向</h3><p>路线有真实取舍时，我会给推荐、代价和最短回复。</p></div></li>
          <li><span>03</span><div><h3>确认完整计划</h3><p>你确认纳入哪些业务结果；任务编排和执行细节由我收敛。</p></div></li>
          <li><span>04</span><div><h3>授权与验收</h3><p>提交、发布、删除等外部影响，以及最终接收结果，都由你决定。</p></div></li>
        </ol>
      </article>
    </div>
  </section>

  <section class="section unknown-section" id="unknowns" data-user-layer>
    <div class="page-shell">
      <header class="section-head">
        <div><p class="kicker">不确定，不等于追问</p><h2>遇到不确定，我不会一股脑问你。</h2></div>
        <p class="section-intro">我先判断它是事实、取舍、假设还是外部依赖，再选择调查、请你决定、做实验或明确等待。</p>
      </header>
      <div class="unknown-grid">__UNKNOWN_CARDS__</div>
    </div>
  </section>

  <section class="section truth-section" data-user-layer>
    <div class="page-shell truth-grid">
      <div class="truth-copy">
        <p class="eyebrow">真实运行底线</p>
        <h2>快，但不靠猜。</h2>
        <p>我追求的是更高结果、更低关键风险和更少未来重复成本。执行快不是省掉重要判断的理由。</p>
      </div>
      <div class="truth-cards">
        <article class="truth-card"><span>01</span><h3>一次只有一个当前动作</h3><p>纠错、体验、协作只是按需增强，不再制造第二套状态。</p></article>
        <article class="truth-card"><span>02</span><h3>证据可以让我快进</h3><p>已有可信输入就快速通过，但关键门槛不会被跳过。</p></article>
        <article class="truth-card"><span>03</span><h3>没有新证据，不说完成</h3><p>代码写完不等于业务完成，本地通过也不等于已经交付。</p></article>
        <article class="truth-card"><span>04</span><h3>外部影响必须有授权</h3><p>未经明确允许，我不会提交、发布、合并、删除或扩大影响。</p></article>
      </div>
    </div>
  </section>

  <section class="section install-section" id="install">
    <div class="page-shell">
      <header class="install-head">
        <div><p class="kicker">开始使用</p><h2>把我交给你的 Agent。</h2></div>
        <p>最省事的方式，是复制下面整段指令。Agent 会自己识别 skills 目录、安装并验证，不需要你先猜路径。</p>
      </header>
      <div class="install-grid">
        <article class="install-panel">
          <h3>复制安装指令</h3>
          <pre><code id="agent-prompt">__AGENT_PROMPT__</code></pre>
          <div class="copy-row"><button class="copy-button" type="button" data-copy-target="agent-prompt">复制给 Agent</button><span class="copy-status" aria-live="polite"></span></div>
        </article>
        <article class="install-panel">
          <h3>或在终端安装</h3>
          <ol class="terminal-steps">
            <li><code>git clone --depth 1 https://github.com/qzl0215/workflow.git</code></li>
            <li><code>cd workflow</code></li>
            <li><code>python3 scripts/install.py install</code></li>
            <li><code>python3 scripts/install.py check --target "&lt;skills父目录&gt;"</code></li>
          </ol>
          <details class="maintenance">
            <summary>维护者：查看正式能力与文件索引</summary>
            <div class="maintenance-grid">
              <div><h4>14 项按需能力</h4><ul class="reference-index">__REFERENCE_INDEX__</ul></div>
              <div><h4>工作文档模板</h4><div class="document-index">__DOCUMENT_INDEX__</div></div>
            </div>
          </details>
        </article>
      </div>
      <footer class="footer">
        <span>作者 zhonglin · 页面由正式来源生成，不手改。</span>
        <span><a href="__REPOSITORY__">GitHub</a> · <code>source sha256 __DIGEST__</code></span>
      </footer>
    </div>
  </section>
</main>
<script>
const copyButton=document.querySelector('[data-copy-target]');
copyButton.addEventListener('click',async()=>{
  const target=document.getElementById(copyButton.dataset.copyTarget);
  try{await navigator.clipboard.writeText(target.textContent.trim())}
  catch(_){
    const area=document.createElement('textarea');
    area.value=target.textContent.trim();
    area.setAttribute('readonly','');
    area.style.position='fixed';
    area.style.opacity='0';
    document.body.appendChild(area);
    area.select();
    document.execCommand('copy');
    area.remove();
  }
  document.querySelector('.copy-status').textContent='已复制';
  copyButton.textContent='已复制';
});
</script>
</body>
</html>
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
