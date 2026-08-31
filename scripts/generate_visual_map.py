#!/usr/bin/env python3
"""从 Workflow 3.x 正式真源生成单页完整改造画面。"""

from __future__ import annotations

import argparse
import hashlib
import html
import re
import sys
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SKILL = PACKAGE / "SKILL.md"
README = PACKAGE / "README.md"
CHANGELOG = PACKAGE / "CHANGELOG.md"
REFERENCES = PACKAGE / "references"
WORK_TEMPLATE = PACKAGE / "templates/work.md"
OUTPUT = PACKAGE / "docs/workflow-visual-map.html"
REPOSITORY = "https://github.com/qzl0215/workflow"

REFERENCE_SPECS = (
    ("目标框定", "frame.md", "核心", "用目标与验收形成契约就绪"),
    ("最小研究", "research.md", "框定反馈", "只查会改变决定的事实"),
    ("深度质询", "grill.md", "框定反馈", "挑战承重假设与失败代价"),
    ("体验探索", "experience.md", "框定反馈", "体验会改方向时才展开"),
    ("结果规划", "plan.md", "核心", "形成可确认方案、责任与依赖"),
    ("编排协作", "orchestrate.md", "执行支撑", "选择串并联、角色与隔离"),
    ("执行任务", "execute.md", "核心", "形成产物与候选回执"),
    ("恢复失败", "recover.md", "执行支撑", "失败后用新证据改路径"),
    ("结果验真", "prove.md", "核心", "接受覆盖结果的新鲜证据"),
    ("真实交付", "deliver.md", "条件", "把同一候选写入真实目标"),
    ("经验复盘", "learn.md", "条件", "压缩带来治理检查与可行动经验"),
)

AGENT_PROMPT = (
    "请安装 GitHub 项目 https://github.com/qzl0215/workflow。先克隆到临时目录，"
    "再根据当前 Agent 配置确认 skills 父目录，不要猜固定路径；运行 "
    "python3 scripts/install.py install --target \"<skills父目录>\"。若已有安装则使用 update。"
    "随后运行 enable-auto-update 和 check；只有唯一性与完整性验证通过后才报告完成。"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def source_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(PACKAGE).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:12]


def title_of(text: str, path: Path) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    if match is None:
        raise ValueError(f"缺少一级标题：{path.relative_to(PACKAGE)}")
    return match.group(1).strip()


def validate_sources(skill_text: str, changelog_text: str, version: str) -> list[Path]:
    expected_refs = {filename for _title, filename, _group, _summary in REFERENCE_SPECS}
    actual_refs = {path.name for path in REFERENCES.glob("*.md")}
    if not expected_refs <= actual_refs:
        missing = sorted(expected_refs - actual_refs)
        raise ValueError(f"完整改造画面缺少当前 reference：{missing}")

    template_files = {path.name for path in (PACKAGE / "templates").glob("*.md")}
    if "work.md" not in template_files:
        raise ValueError("模板缺少 work.md")
    legacy_state_templates = {
        "findings.md",
        "progress.md",
        "implementation-plan.md",
        "index.md",
        "task-owner-prompt.md",
        "task_plan.md",
    }
    duplicates = sorted(template_files & legacy_state_templates)
    if duplicates:
        raise ValueError(f"仍存在重复状态模板：{duplicates}")

    required_root_tokens = (
        "目标框定 → 结果规划 → 任务执行 → 结果验真",
        "真实交付",
        "经验复盘",
        "grill-me",
        "单一控制面",
        "进度｜",
        "技能｜",
        "成果｜",
        "路径｜",
        "关键出口展示",
        "业务含义",
        "契约就绪",
        "方案就绪",
        "真正看懂",
    )
    missing_tokens = [token for token in required_root_tokens if token not in skill_text]
    if missing_tokens:
        raise ValueError("SKILL.md 缺少视觉契约：" + "，".join(missing_tokens))

    paths = [SKILL, README, CHANGELOG, WORK_TEMPLATE]
    for expected_title, filename, _group, _summary in REFERENCE_SPECS:
        path = REFERENCES / filename
        text = read(path)
        if title_of(text, path) != expected_title:
            raise ValueError(f"标题不匹配：references/{filename}")
        if f"references/{filename}" not in skill_text:
            raise ValueError(f"根路由未链接：references/{filename}")
        paths.append(path)

    work_text = read(WORK_TEMPLATE)
    for token in ("协调者", "候选", "已接受", "结果计划与依赖"):
        if token not in work_text:
            raise ValueError(f"work.md 缺少控制面语义：{token}")

    if re.search(rf"^## \[{re.escape(version)}\]", changelog_text, re.MULTILINE) is None:
        raise ValueError(f"CHANGELOG.md 缺少当前版本 {version}")
    return paths


def render_reference_index() -> str:
    items: list[str] = []
    for index, (title, filename, group, summary) in enumerate(REFERENCE_SPECS, 1):
        items.append(
            '<li class="ref-item">'
            f'<span class="ref-num">{index:02d}</span>'
            '<div>'
            f'<b>{html.escape(title)}</b>'
            f'<p>{html.escape(summary)}</p>'
            f'<code>references/{html.escape(filename)}</code>'
            '</div>'
            f'<small>{html.escape(group)}</small>'
            '</li>'
        )
    return "".join(items)


def build() -> tuple[str, str]:
    skill_text = read(SKILL)
    changelog_text = read(CHANGELOG)
    version_match = re.search(
        r"^version:\s*(\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?)\s*$",
        skill_text,
        re.MULTILINE,
    )
    if version_match is None:
        raise ValueError("SKILL.md 缺少可识别版本")
    version = version_match.group(1)
    digest_paths = validate_sources(skill_text, changelog_text, version)
    digest = source_digest(digest_paths)

    replacements = {
        "__VERSION__": html.escape(version),
        "__DIGEST__": digest,
        "__REFERENCE_INDEX__": render_reference_index(),
        "__REPOSITORY__": html.escape(REPOSITORY, quote=True),
        "__AGENT_PROMPT__": html.escape(AGENT_PROMPT),
    }
    rendered = HTML_TEMPLATE
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    if re.search(r"__[A-Z][A-Z0-9_]+__", rendered):
        raise ValueError("生成页仍有未替换标记")
    return rendered, digest


HTML_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Workflow 3.0 完整改造画面：四大核心环节、条件反馈、多 Agent 编排、单一控制面、交付与复盘边界。">
<meta name="color-scheme" content="dark light">
<title>Workflow 3.0｜完整改造画面</title>
<style>
:root{
  --bg:#071114;--panel:#0d1b1f;--panel-2:#11252a;--paper:#ecf2ed;--muted:#9eb0ad;
  --line:#294046;--mint:#65f0c1;--cyan:#62d8ff;--orange:#ff9a62;--yellow:#f4dc70;
  --gutter:clamp(18px,5vw,92px);font-family:"Avenir Next","SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;
  color:var(--paper);background:var(--bg)
}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:76px}body{margin:0;min-width:320px;background:var(--bg);color:var(--paper)}
a{color:inherit;text-decoration:none}button{font:inherit}code,.mono{font-family:"SFMono-Regular",Consolas,monospace}:focus-visible{outline:3px solid var(--mint);outline-offset:3px}
.shell{width:min(1480px,calc(100% - 2 * var(--gutter)));margin:auto}.topbar{position:sticky;top:0;z-index:20;border-bottom:1px solid rgb(101 240 193 / 20%);background:rgb(7 17 20 / 88%);backdrop-filter:blur(18px)}
.topbar .shell{height:68px;display:flex;align-items:center;justify-content:space-between;gap:24px}.brand{font-weight:900;letter-spacing:-.04em}.brand span{margin-left:9px;color:var(--mint);font:800 10px "SFMono-Regular",monospace;letter-spacing:.1em}
.nav{display:flex;gap:clamp(12px,2vw,30px)}.nav a{min-height:44px;display:flex;align-items:center;color:var(--muted);font-size:12px;font-weight:750}.nav a:hover{color:var(--mint)}
.hero{position:relative;overflow:hidden;padding:clamp(76px,11vw,170px) 0 clamp(70px,9vw,140px)}.hero:after{content:"";position:absolute;width:720px;height:720px;right:-260px;top:-360px;border-radius:50%;background:radial-gradient(circle,rgb(98 216 255 / 18%),transparent 68%);pointer-events:none}
.eyebrow,.kicker{margin:0 0 18px;color:var(--mint);font:800 11px "SFMono-Regular",monospace;letter-spacing:.15em;text-transform:uppercase}.hero h1{max-width:13ch;margin:0;font-size:clamp(55px,8vw,132px);line-height:.91;letter-spacing:-.075em}.hero h1 span{display:block;color:var(--mint)}
.hero-grid{display:grid;grid-template-columns:1.4fr .6fr;gap:clamp(42px,8vw,130px);align-items:end}.lede{max-width:820px;margin:32px 0 0;color:#c0cdca;font-size:clamp(18px,1.5vw,26px);line-height:1.65}.hero-note{border-top:2px solid var(--mint);padding-top:22px}.hero-note p{margin:0 0 26px;color:var(--muted);line-height:1.65}.hero-facts{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line)}.hero-facts div{padding:18px;background:var(--panel)}.hero-facts b{display:block;color:var(--mint);font-size:25px}.hero-facts span{font-size:11px;color:var(--muted)}
.section{padding:clamp(72px,9vw,140px) 0;border-top:1px solid var(--line)}.section-head{display:grid;grid-template-columns:1fr .72fr;gap:60px;align-items:end;margin-bottom:clamp(42px,6vw,78px)}.section h2{max-width:15ch;margin:0;font-size:clamp(38px,5vw,78px);line-height:.98;letter-spacing:-.06em}.intro{margin:0;color:var(--muted);font-size:16px;line-height:1.75}
.core-flow{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.core-card{position:relative;min-height:260px;padding:25px;border:1px solid var(--line);background:linear-gradient(145deg,var(--panel),#091619)}.core-card:not(:last-child):after{content:"→";position:absolute;right:-16px;top:49%;z-index:2;width:20px;text-align:center;color:var(--mint);font-weight:900}.core-card .num{color:var(--mint);font:800 10px "SFMono-Regular",monospace}.core-card h3{margin:70px 0 12px;font-size:clamp(25px,2.2vw,36px);letter-spacing:-.045em}.core-card p{margin:0;color:var(--muted);font-size:13px;line-height:1.65}.core-card code{display:block;margin-top:18px;color:var(--cyan);font-size:10px}
.conditional-flow{display:grid;grid-template-columns:1fr auto 1fr;gap:18px;align-items:stretch;margin-top:18px}.conditional-card{padding:22px;border:1px dashed var(--line);background:var(--panel)}.conditional-card b{display:block;margin-bottom:8px;color:var(--orange)}.conditional-card p{margin:0;color:var(--muted);font-size:13px;line-height:1.6}.flow-arrow{display:grid;place-items:center;color:var(--yellow);font-weight:900}
.frame-layout{display:grid;grid-template-columns:.68fr 1.32fr;gap:clamp(30px,6vw,92px)}.frame-hub{display:flex;min-height:370px;align-items:center;justify-content:center;border:1px solid var(--mint);background:radial-gradient(circle,rgb(101 240 193 / 12%),transparent 65%)}.hub-inner{text-align:center}.hub-inner span{display:block;color:var(--muted);font:750 10px "SFMono-Regular",monospace}.hub-inner b{display:block;margin:10px 0;color:var(--mint);font-size:40px;letter-spacing:-.05em}.feedback-list{display:grid;gap:10px}.feedback-card{display:grid;grid-template-columns:110px 1fr;gap:22px;padding:22px;border:1px solid var(--line);background:var(--panel)}.feedback-card:first-child{border-color:var(--cyan)}.feedback-card code{color:var(--cyan);font-size:12px}.feedback-card h3{margin:0 0 7px;font-size:18px}.feedback-card p{margin:0;color:var(--muted);font-size:13px;line-height:1.62}.feedback-rule{margin:14px 0 0;padding:18px 20px;border-left:3px solid var(--yellow);background:rgb(244 220 112 / 7%);color:#ced6d3;line-height:1.7}
.plan-grid{display:grid;grid-template-columns:1.05fr .95fr;gap:1px;background:var(--line);border:1px solid var(--line)}.plan-panel{padding:clamp(28px,4vw,60px);background:var(--panel)}.plan-panel h3{margin:0 0 24px;font-size:28px;letter-spacing:-.04em}.dag{display:grid;gap:10px}.dag-node{padding:15px;border:1px solid var(--line);background:var(--bg);font-size:13px}.dag-node.root,.dag-node.merge{border-color:var(--mint);color:var(--mint);font-weight:850}.dag-parallel{display:grid;grid-template-columns:1fr 1fr;gap:10px}.dag-arrow{text-align:center;color:var(--mint)}.depth-list{margin:0;padding:0;list-style:none}.depth-list li{padding:18px 0;border-top:1px solid var(--line)}.depth-list li:first-child{border-top:0}.depth-list b{display:block;margin-bottom:6px}.depth-list span{color:var(--muted);font-size:13px;line-height:1.6}
.agent-pipe{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;gap:12px;align-items:center;margin-top:18px}.pipe-node{min-height:132px;padding:20px;border:1px solid var(--line);background:var(--panel)}.pipe-node b{display:block;margin-bottom:9px;color:var(--cyan)}.pipe-node p{margin:0;color:var(--muted);font-size:12px;line-height:1.6}.pipe-arrow{color:var(--mint);font-weight:900}
.truth-section{background:#e8eee9;color:#0a1719}.truth-section .kicker{color:#08785d}.truth-section .intro{color:#526461}.truth-grid{display:grid;grid-template-columns:.72fr 1.28fr;gap:clamp(32px,7vw,110px)}.work-card{padding:clamp(28px,4vw,54px);background:#0c1b1e;color:var(--paper);box-shadow:18px 18px 0 #b7c9c3}.work-card header{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:18px}.work-card header b{font-size:24px}.work-card header span{color:var(--mint);font:750 10px "SFMono-Regular",monospace}.work-lines{display:grid;gap:12px;margin-top:22px}.work-line{height:11px;border-radius:8px;background:#21363a}.work-line:nth-child(2){width:84%}.work-line:nth-child(3){width:68%}.work-line.accepted{width:91%;background:var(--mint)}
.control-rules{display:grid;gap:1px;background:#afbfba;border:1px solid #afbfba}.control-rule{display:grid;grid-template-columns:72px 1fr;gap:18px;padding:22px;background:#e8eee9}.control-rule span{color:#08785d;font:900 10px "SFMono-Regular",monospace}.control-rule b{display:block;margin-bottom:6px}.control-rule p{margin:0;color:#53615f;font-size:13px;line-height:1.6}
.boundary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.boundary-card{min-height:230px;padding:24px;border:1px solid var(--line);background:var(--panel)}.boundary-card b{display:block;margin-bottom:30px;color:var(--mint);font-size:23px}.boundary-card p{margin:0 0 12px;color:var(--muted);font-size:13px;line-height:1.65}.boundary-card.is-conditional b{color:var(--orange)}.boundary-note{margin-top:14px;padding:20px;border:1px solid var(--yellow);color:#e8dfaf;line-height:1.7}
.status-shell{max-width:900px;margin:auto;border:1px solid var(--line);background:#050b0d;box-shadow:0 30px 90px rgb(0 0 0 / 25%)}.status-top{height:36px;display:flex;align-items:center;gap:7px;padding:0 14px;border-bottom:1px solid var(--line)}.status-top i{width:8px;height:8px;border-radius:50%;background:var(--line)}.status-body{padding:clamp(24px,4vw,44px);font:clamp(12px,1.4vw,17px)/2 "SFMono-Regular",Consolas,monospace}.status-body p{margin:0}.status-body b{display:inline-block;width:4em;color:var(--mint)}.status-body .done{color:#f3f6f4}.status-body .current{color:var(--yellow)}.status-explain{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;margin-top:1px;background:var(--line)}.status-explain div{padding:18px;background:var(--panel);font-size:12px;line-height:1.55;color:var(--muted)}.status-explain b{display:block;color:var(--paper);margin-bottom:5px}
.ref-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0;padding:0;list-style:none}.ref-item{display:grid;grid-template-columns:34px 1fr auto;gap:14px;align-items:start;padding:18px;border:1px solid var(--line);background:var(--panel)}.ref-num{color:var(--mint);font:800 10px "SFMono-Regular",monospace}.ref-item b{display:block}.ref-item p{margin:5px 0;color:var(--muted);font-size:12px}.ref-item code{color:var(--cyan);font-size:9px}.ref-item small{padding:4px 7px;border:1px solid var(--line);color:var(--muted);font-size:9px}
.migration{background:var(--orange);color:#1b100a}.migration .kicker{color:#6e2a08}.migration .intro{color:#69361f}.migration-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.migration-card{padding:clamp(28px,4vw,52px);border:2px solid #1b100a;background:rgb(255 255 255 / 16%)}.migration-card h3{margin:0 0 18px;font-size:31px;letter-spacing:-.04em}.migration-card p{line-height:1.7}.migration-card code{background:#1b100a;color:#fff;padding:3px 6px}.migration-note{margin:20px 0 0;font-weight:800;line-height:1.65}
.install{background:var(--mint);color:#071114}.install-grid{display:grid;grid-template-columns:.8fr 1.2fr;gap:clamp(30px,7vw,100px);align-items:start}.install h2{max-width:10ch}.install pre{margin:0;padding:24px;overflow:auto;background:#071114;color:var(--paper);white-space:pre-wrap;font:11px/1.7 "SFMono-Regular",monospace}.copy-row{display:flex;align-items:center;gap:14px;margin-top:12px}.copy{min-height:46px;padding:0 18px;border:0;background:#071114;color:#fff;font-weight:850;cursor:pointer}.copy-status{font-size:12px;font-weight:800}.install-commands{margin-top:18px;padding-top:18px;border-top:1px solid rgb(7 17 20 / 35%);font:11px/1.8 "SFMono-Regular",monospace}.footer{padding:24px 0;border-top:1px solid rgb(7 17 20 / 35%);font-size:10px;display:flex;justify-content:space-between;gap:20px}.footer a{font-weight:900}
@media(max-width:1050px){.hero-grid,.section-head,.frame-layout,.truth-grid,.install-grid{grid-template-columns:1fr}.core-flow{grid-template-columns:1fr 1fr}.core-card:nth-child(2):after{display:none}.plan-grid{grid-template-columns:1fr}.agent-pipe{grid-template-columns:1fr}.pipe-arrow{transform:rotate(90deg);text-align:center}.boundary-grid{grid-template-columns:1fr}.nav a:nth-child(-n+2){display:none}}
@media(max-width:680px){:root{--gutter:18px}.topbar .shell{height:60px}.hero{padding-top:70px}.hero h1{font-size:clamp(48px,15vw,76px)}.hero-facts,.core-flow,.conditional-flow,.dag-parallel,.status-explain,.ref-grid,.migration-grid{grid-template-columns:1fr}.core-card{min-height:0}.core-card h3{margin-top:34px}.core-card:after{display:none}.conditional-flow .flow-arrow{transform:rotate(90deg)}.feedback-card{grid-template-columns:1fr}.work-card{box-shadow:9px 9px 0 #b7c9c3}.ref-item{grid-template-columns:28px 1fr}.ref-item small{display:none}.footer{display:block}.footer span{display:block;margin-top:6px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
</style>
</head>
<body data-source-digest="__DIGEST__">
<!-- 生成文件，请勿手改。真源：SKILL.md、README.md、CHANGELOG.md、十一份 references 与 templates/work.md。 -->
<header class="topbar">
  <div class="shell">
    <a class="brand" href="#top">workflow <span>V__VERSION__</span></a>
    <nav class="nav" aria-label="页面导航">
      <a href="#architecture">主链</a><a href="#frame">框定反馈</a><a href="#agents">多 Agent</a><a href="#migration">迁移</a>
    </nav>
  </div>
</header>
<main id="top">
  <section class="hero">
    <div class="shell hero-grid">
      <div>
        <p class="eyebrow">Workflow 3.0 · 完整改造画面</p>
        <h1>少规定过程，<span>严守结果。</span></h1>
        <p class="lede">四大核心环节守住结果闭环，条件反馈保留深度，任务胶囊承载多 Agent 协作。模型可以自由选择怎么做，但不能跳过承重决定、授权和新鲜证据。</p>
      </div>
      <aside class="hero-note">
        <p>这不是把旧流程换一组名字，而是把固定仪式改成渐进路由：最小动作足够就停，真实风险出现才加深，缺口只回到它的原因。</p>
        <div class="hero-facts">
          <div><b>4</b><span>核心结果环节</span></div><div><b>2</b><span>条件结果环节</span></div>
          <div><b>11</b><span>渐进 reference</span></div><div><b>1</b><span>持久控制面</span></div>
        </div>
      </aside>
    </div>
  </section>

  <section class="section" id="architecture">
    <div class="shell">
      <header class="section-head">
        <div><p class="kicker">唯一用户主链</p><h2>从目标，到有证据的结果。</h2></div>
        <p class="intro">阶段是进展投影，不是固定仪式。已有可信输入可以快速通过；发现缺口，就回到最早能修正它的位置。</p>
      </header>
      <div class="core-flow">
        <article class="core-card"><span class="num">01 · FRAME</span><h3>目标框定</h3><p>默认用目标与验收形成契约就绪；其他边界确实影响方案时才补充。</p><code>references/frame.md</code></article>
        <article class="core-card"><span class="num">02 · PLAN</span><h3>结果规划</h3><p>展示目标、推荐方案、验收和交付路径，经确认或委托形成方案就绪。</p><code>references/plan.md</code></article>
        <article class="core-card"><span class="num">03 · EXECUTE</span><h3>任务执行</h3><p>实施当前就绪责任，返回真实产物、候选证据和偏差。</p><code>references/execute.md</code></article>
        <article class="core-card"><span class="num">04 · PROVE</span><h3>结果验真</h3><p>读取实际产物，用新鲜证据证明任务、计划和用户结果。</p><code>references/prove.md</code></article>
      </div>
      <div class="conditional-flow">
        <article class="conditional-card"><b>条件：真实交付</b><p>只有提交、合并、部署、发布或外部写入才进入；验真不自动授权交付。</p></article>
        <div class="flow-arrow">→</div>
        <article class="conditional-card"><b>条件：经验复盘</b><p>事实能改变未来行动时进入；上下文压缩带来工作规则、信息组织和业务动作的治理检查，检查后仍可 no-op。</p></article>
      </div>
      <p class="boundary-note"><b>就绪链：</b>意见与设想先整理为候选目标；目标与验收清楚后形成契约就绪，推荐方案经用户确认或委托后形成方案就绪。用户说“开动”后，一次确认在实施、验真和真实交付之间持续有效。</p>
    </div>
  </section>

  <section class="section" id="frame">
    <div class="shell">
      <header class="section-head">
        <div><p class="kicker">Frame 内的条件反馈</p><h2>先查事实，再决定是否加深。</h2></div>
        <p class="intro">研究、质询、体验不是默认并行的三道工序。它们只为一个结果契约提供候选输入，并且只在结论真的改变时互相回流。</p>
      </header>
      <div class="frame-layout">
        <div class="frame-hub"><div class="hub-inner"><span>统一合成责任</span><b>结果契约</b><span>目标 · 验收 · 按需边界</span></div></div>
        <div>
          <div class="feedback-list">
            <article class="feedback-card"><code>research</code><div><h3>事实不足才做最小研究</h3><p>只查会改变当前决定的事实；达到停止条件就结束，不追求资料穷尽。</p></div></article>
            <article class="feedback-card"><code>grill-me</code><div><h3>承重决定仍不稳才深度质询</h3><p>用反例、失败场景、隐藏代价和可逆替代方向挑战假设，直到边际信息不再改变推荐。</p></div></article>
            <article class="feedback-card"><code>experience</code><div><h3>现有页面局部修改走真实预览</h3><p>在真实源码划分改动面与保护面，优先使用复用真实登录态的只读独立验收入口；只有承重方向分歧才制作独立概念稿。</p></div></article>
          </div>
          <p class="feedback-rule"><b>并行例外：</b>事实线彼此独立、能隔离且明显缩短关键路径时，可以并行取得候选输入；目标责任者统一合成。新结论只重开受影响部分，不全量循环。</p>
        </div>
      </div>
    </div>
  </section>

  <section class="section" id="agents">
    <div class="shell">
      <header class="section-head">
        <div><p class="kicker">Plan → Confirm → Execute</p><h2>先让方案可判断，再按结果拆任务。</h2></div>
        <p class="intro">用户先看到目标、推荐方案、验收和交付路径；确认后，内部任务再按真实依赖和净收益安排串并联。</p>
      </header>
      <div class="plan-grid">
        <article class="plan-panel">
          <h3>串并联不是固定模板</h3>
          <div class="dag">
            <div class="dag-node root">P01 · 可独立验收的结果</div><div class="dag-arrow">↓</div>
            <div class="dag-node">T01 · 先建立公共边界（串行）</div><div class="dag-arrow">↓</div>
            <div class="dag-parallel"><div class="dag-node">T02 · 独立实现 A</div><div class="dag-node">T03 · 独立实现 B</div></div><div class="dag-arrow">↓</div>
            <div class="dag-node merge">汇合 · 语义消解 · 整体验真</div>
          </div>
        </article>
        <article class="plan-panel">
          <h3>每个子任务独立定深度</h3>
          <ul class="depth-list">
            <li><b>局部、已知、易回退</b><span>直接实施，做能区分成败的定向验证。</span></li>
            <li><b>跨模块或共享接口</b><span>先确认消费者与边界，再增加相邻集成证据。</span></li>
            <li><b>并发、迁移、安全或生产风险</b><span>先建可失败实验、回退点和更强观测，再实施。</span></li>
            <li><b>目标或体验仍未定</b><span>精确返回上游，不在执行中用个人偏好补齐。</span></li>
          </ul>
        </article>
      </div>
      <div class="agent-pipe">
        <article class="pipe-node"><b>协调者发任务胶囊</b><p>只给结果、输入、验收、边界、授权、依赖、契约身份和返回条件。</p></article><div class="pipe-arrow">→</div>
        <article class="pipe-node"><b>执行者返候选回执</b><p>报告实际产物、验证、失败、偏差、未覆盖项与执行时身份，不写控制面。</p></article><div class="pipe-arrow">→</div>
        <article class="pipe-node"><b>协调者接受或拒绝</b><p>核对契约、真实产物、证据身份与语义冲突后，才进入整体结果。</p></article>
      </div>
    </div>
  </section>

  <section class="section truth-section">
    <div class="shell">
      <header class="section-head">
        <div><p class="kicker">单一持久控制面</p><h2>一个 work.md，不是一个巨型日志。</h2></div>
        <p class="intro">删除五份文件对当前状态的重复描述，保留恢复真正需要的信息。简单任务连 work.md 都不创建。</p>
      </header>
      <div class="truth-grid">
        <div class="work-card">
          <header><b>work.md</b><span>协调者唯一可写</span></header>
          <div class="work-lines"><div class="work-line accepted"></div><div class="work-line"></div><div class="work-line"></div><div class="work-line"></div></div>
        </div>
        <div class="control-rules">
          <article class="control-rule"><span>01</span><div><b>只存当前投影</b><p>结果契约、计划依赖、状态、已接受证据、阻断和当前就绪责任。</p></div></article>
          <article class="control-rule"><span>02</span><div><b>胶囊和回执默认内联</b><p>只有跨上下文恢复或昂贵、不可复现证据需要时才物化。</p></div></article>
          <article class="control-rule"><span>03</span><div><b>候选不能冒充接受</b><p>子 Agent 不并发改写控制面；协调者验收后才写入已接受区。</p></div></article>
          <article class="control-rule"><span>04</span><div><b>恢复不读流水账</b><p>被替代和拒绝的候选留在上下文，默认不进入长期注意力。</p></div></article>
        </div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="shell">
      <header class="section-head">
        <div><p class="kicker">Prove / Deliver / Learn</p><h2>证明、交付、学习，三件事分别成立。</h2></div>
        <p class="intro">交付成功不反向证明业务结果；验真成功不自动授权交付；复盘也不能在真实交付状态未知时定稿。</p>
      </header>
      <div class="boundary-grid">
        <article class="boundary-card"><b>Prove · 必经</b><p>证明当前产物和用户状态满足结果契约。</p><p>相同输入、环境和验证语义上的有效证据可以复用；跨真实环境边界必须 fresh。</p></article>
        <article class="boundary-card is-conditional"><b>Deliver · 条件</b><p>把同一候选写入真实目标，并在真实消费入口冒烟。</p><p>任一步失败就停止后续外部写入，保留可恢复现场。</p></article>
        <article class="boundary-card is-conditional"><b>Learn · 条件</b><p>只接受有未来触发场景、证据和唯一真源的经验。</p><p>上下文压缩带来工作规则、项目入口、冗余、真源、导航与动作价值检查；无可行动发现就是 no-op。</p></article>
      </div>
      <p class="boundary-note"><b>默认顺序：</b>有交付时先 `prove → deliver`，有复用价值信号才进入 `learn`；上下文压缩始终构成该信号。无交付时也在 `prove` 后先过同一复盘门。等待平台时可并行收集与交付结果无关的候选观察，但最终接受发生在交付事实之后。</p>
    </div>
  </section>

  <section class="section">
    <div class="shell">
      <header class="section-head">
        <div><p class="kicker">用户阶段画面</p><h2>关键出口清楚呈现，让用户真正看懂。</h2></div>
        <p class="intro">首次进展、环节实质变化、真实阻断、最终交付和交回控制权形成新的用户画面；状态不变不重复，轻量任务可只在最终出口展示一次。</p>
      </header>
      <div class="status-shell">
        <div class="status-top"><i></i><i></i><i></i></div>
        <div class="status-body">
          <p><b>结论｜</b><span class="done">新版工作流已安全启用，后续任务会按新规则执行</span></p>
          <p><b>进度｜</b><span class="current">■■■■｜■— · 核心结果完成 · 已完成真实更新 · 本次无需复盘</span></p>
          <p><b>技能｜</b><span>任务执行 · 结果验真 · 真实交付</span></p>
          <p><b>成果｜</b><span class="done">✓ 旧版已安全替换 · ✓ 新版已确认可正常使用 · ✓ 没有产生重复安装</span></p>
          <p><b>路径｜</b><span>确认更新目标 → 安全替换旧版 → 验证实际可用</span></p>
        </div>
      </div>
      <p class="boundary-note"><b>理解优先：</b>主画面使用用户熟悉的词，先回答发生了什么、有什么影响、怎样决定或行动。专业术语先解释实际含义；文件数、检查器、命令、哈希和内部编号只在影响决定或可信度时作为技术证据展开。</p>
      <div class="status-explain"><div><b>进度</b>当前实际进入的用户环节</div><div><b>技能</b>本轮真正读取的参考</div><div><b>成果</b>已接受结果与下一验证点</div><div><b>路径</b>多任务时的最短活动路径</div></div>
    </div>
  </section>

  <section class="section">
    <div class="shell">
      <header class="section-head">
        <div><p class="kicker">十一份渐进路由器</p><h2>每份都从最小动作开始。</h2></div>
        <p class="intro">四大环节不复制四棵同形目录树。每份 reference 自己说明停止条件、加深信号与缺口回流，模型只读当前决定所需内容。</p>
      </header>
      <ul class="ref-grid">__REFERENCE_INDEX__</ul>
    </div>
  </section>

  <section class="section migration" id="migration">
    <div class="shell">
      <header class="section-head">
        <div><p class="kicker">2.x → 3.x</p><h2>2.26 是精简运行时的桥。</h2></div>
        <p class="intro">3.x Release 不再把测试和维护文档安装进模型运行时。更新器必须先理解 manifest，不能靠猜文件集合迁移。</p>
      </header>
      <div class="migration-grid">
        <article class="migration-card"><h3>已有 2.26.x</h3><p>可以直接运行 <code>sync</code>。2.26 会核对 manifest、逐文件 SHA-256 和 runtime doctor，在同文件系统暂存验证后事务替换。</p></article>
        <article class="migration-card"><h3>2.25.x 或更早</h3><p>旧更新器应失败关闭并保留原安装。请取得已验证的 3.x tag 或正式 Release，用其中的新安装器执行 <code>update</code>，再运行 <code>check</code>。</p></article>
      </div>
      <p class="migration-note">不要手工删除旧版再覆盖 ZIP。失败关闭是兼容边界的一部分，不是需要绕过的错误。</p>
    </div>
  </section>

  <section class="section install">
    <div class="shell install-grid">
      <div><p class="kicker">开始使用</p><h2>把目标交给 workflow。</h2><p class="intro">安装后直接描述真实目标；简单任务走快路，只有承重未知、风险、恢复或真实交付需要时才加深。</p></div>
      <div>
        <pre><code id="agent-prompt">__AGENT_PROMPT__</code></pre>
        <div class="copy-row"><button class="copy" type="button" data-copy-target="agent-prompt">复制给 Agent</button><span class="copy-status" aria-live="polite"></span></div>
        <div class="install-commands">git clone --depth 1 https://github.com/qzl0215/workflow.git<br>cd workflow<br>python3 scripts/install.py install --target "&lt;skills父目录&gt;"<br>python3 scripts/install.py check --target "&lt;skills父目录&gt;"</div>
      </div>
    </div>
    <footer class="shell footer"><span>作者 zhonglin · 页面由正式真源生成，不手改。</span><span><a href="__REPOSITORY__">GitHub</a> · source sha256 <code>__DIGEST__</code></span></footer>
  </section>
</main>
<script>
const button=document.querySelector('[data-copy-target]');
button.addEventListener('click',async()=>{
  const value=document.getElementById(button.dataset.copyTarget).textContent.trim();
  try{await navigator.clipboard.writeText(value)}catch(_){
    const area=document.createElement('textarea');area.value=value;area.setAttribute('readonly','');
    area.style.position='fixed';area.style.opacity='0';document.body.appendChild(area);area.select();
    document.execCommand('copy');area.remove();
  }
  button.textContent='已复制';document.querySelector('.copy-status').textContent='可以粘贴给当前 Agent';
});
</script>
</body>
</html>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="检查生成页面是否与正式真源一致")
    args = parser.parse_args()
    try:
        generated, _digest = build()
    except (OSError, ValueError) as exc:
        print(f"视觉图真源错误：{exc}", file=sys.stderr)
        return 2

    if args.check:
        if not OUTPUT.is_file() or read(OUTPUT) != generated:
            print(f"视觉图已过期：{OUTPUT}", file=sys.stderr)
            return 1
        print("workflow_visual_map: OK")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generated, encoding="utf-8")
    print(f"已生成 {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
