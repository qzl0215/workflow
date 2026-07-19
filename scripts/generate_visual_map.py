#!/usr/bin/env python3
"""Generate the standalone Chinese workflow introduction from SKILL.md."""

from __future__ import annotations

import argparse
import hashlib
import html
import sys
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE / "SKILL.md"
OUTPUT = PACKAGE / "docs/workflow-visual-map.html"
REPOSITORY = "https://github.com/qzl0215/workflow"
AGENT_PROMPT = (
    "请安装 GitHub 项目 https://github.com/qzl0215/workflow。先把仓库克隆到临时目录，"
    "再根据你当前 Agent 的配置确认 skills 父目录，不要猜固定路径；运行 "
    "python3 scripts/install.py install --target \"<skills父目录>\"。如果已经安装，则使用 update。"
    "最后运行同一脚本的 check，只有验证通过后才能告诉我安装完成。不要安装任何其他 skill，"
    "也不要覆盖没有备份的旧版本。"
)
STATE_LABELS = {
    "Intake": "接住任务",
    "Clarify": "澄清目标",
    "Readiness": "检查能否开工",
    "Solution": "收敛方案",
    "Experience": "选定体验",
    "Write": "写执行计划",
    "Act": "实施",
    "Debug": "定位根因",
    "Verify": "验证结果",
    "Finish": "交付收尾",
}


def section(text: str, heading: str, next_heading: str) -> str:
    try:
        return text.split(heading, 1)[1].split(next_heading, 1)[0]
    except IndexError as exc:
        raise ValueError(f"missing source section: {heading}") from exc


def table_rows(block: str, columns: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in block.splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) != columns or cells[0] in {"阶段", "信号"}:
            continue
        rows.append(cells)
    return rows


def render_state_cards(states: list[list[str]]) -> str:
    cards: list[str] = []
    for index, (name, entry, writes, exit_rule, fallback) in enumerate(states, 1):
        cards.append(
            f'<article class="stage-card" data-stage="{html.escape(name)}">'
            f'<div class="stage-head"><span class="stage-index">{index:02d}</span>'
            f'<span class="stage-en">{html.escape(name)}</span></div>'
            f'<h3>{html.escape(STATE_LABELS[name])}</h3>'
            f'<p class="stage-outcome">{html.escape(exit_rule)}</p>'
            f'<details><summary>查看阶段契约</summary><dl>'
            f'<dt>进入依据</dt><dd>{html.escape(entry)}</dd>'
            f'<dt>允许写入</dt><dd>{html.escape(writes)}</dd>'
            f'<dt>出口条件</dt><dd>{html.escape(exit_rule)}</dd>'
            f'<dt>不满足时</dt><dd>{html.escape(fallback)}</dd>'
            f'</dl></details></article>'
        )
    return "".join(cards)


def render_route_cards(routes: list[list[str]]) -> str:
    return "".join(
        f'<article class="route-card"><span class="route-mark" aria-hidden="true"></span>'
        f'<p>{html.escape(signal)}</p><code>{html.escape(target)}</code></article>'
        for signal, target in routes
    )


HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="workflow：一个可独立安装、零外部 skill 依赖的复杂任务总导演。">
<title>workflow｜复杂任务总导演</title>
<style>
:root {
  --ink: #17201b;
  --ink-soft: #465149;
  --paper: #f3efe4;
  --paper-deep: #e9e2d2;
  --card: #fffdf7;
  --line: #c9c1ae;
  --green: #125f45;
  --green-dark: #0a4532;
  --orange: #c45c27;
  --yellow: #efc85b;
  --shadow: 0 18px 50px rgba(23, 32, 27, .10);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 16px/1.7 "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif;
}
a { color: inherit; }
button, a { -webkit-tap-highlight-color: transparent; }
:focus-visible { outline: 3px solid var(--yellow); outline-offset: 4px; }
.skip-link { position: fixed; top: 10px; left: 10px; z-index: 20; transform: translateY(-160%); background: var(--ink); color: white; padding: 10px 14px; }
.skip-link:focus { transform: translateY(0); }
.shell { width: min(1180px, calc(100% - 40px)); margin: 0 auto; position: relative; }
.topbar { display: flex; justify-content: space-between; align-items: center; gap: 24px; padding: 22px 0; border-bottom: 1px solid var(--line); }
.brand { font: 800 15px/1 ui-monospace, SFMono-Regular, Menlo, monospace; text-decoration: none; letter-spacing: -.03em; }
.topbar nav { display: flex; gap: 22px; font-size: 14px; }
.topbar nav a { text-decoration: none; color: var(--ink-soft); }
.topbar nav a:hover { color: var(--green); }
.hero { min-height: 720px; display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(340px, .92fr); gap: clamp(40px, 8vw, 110px); align-items: center; padding: 84px 0 96px; }
.eyebrow { margin: 0 0 20px; color: var(--green); font: 800 13px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .12em; text-transform: uppercase; }
h1, h2, h3, p { overflow-wrap: anywhere; }
h1 { margin: 0; max-width: 720px; font: 800 clamp(60px, 9vw, 116px)/.88 "Songti SC", STSong, "Noto Serif CJK SC", serif; letter-spacing: -.075em; }
h1 span { color: var(--green); }
.lede { max-width: 650px; margin: 32px 0 0; color: var(--ink-soft); font-size: clamp(18px, 2vw, 23px); line-height: 1.65; }
.hero-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 34px; }
.button { display: inline-flex; align-items: center; justify-content: center; min-height: 48px; border: 1px solid var(--ink); padding: 0 18px; background: transparent; color: var(--ink); text-decoration: none; font-weight: 750; cursor: pointer; }
.button.primary { background: var(--ink); color: white; }
.button:hover { transform: translateY(-2px); }
.hero-board { position: relative; background: var(--green-dark); color: #f7f2e7; border: 1px solid #0c3528; padding: 28px; box-shadow: var(--shadow); }
.hero-board::before { content: "运行规则 / RUNBOOK"; display: block; padding-bottom: 16px; border-bottom: 1px solid #ffffff35; color: #d5e1d9; font: 700 11px ui-monospace, monospace; letter-spacing: .12em; }
.rule { display: grid; grid-template-columns: 42px 1fr; gap: 14px; padding: 20px 0; border-bottom: 1px solid #ffffff25; }
.rule:last-child { border-bottom: 0; padding-bottom: 2px; }
.rule b { color: var(--yellow); font: 800 20px ui-monospace, monospace; }
.rule p { margin: 0; }
.rule strong { display: block; margin-bottom: 3px; font-size: 17px; }
.rule span { color: #c7d6cd; font-size: 14px; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); border: 1px solid var(--line); border-right: 0; margin-bottom: 96px; background: #ffffff45; }
.stat { min-height: 130px; padding: 22px; border-right: 1px solid var(--line); display: flex; flex-direction: column; justify-content: space-between; }
.stat b { font: 800 44px/1 ui-monospace, SFMono-Regular, monospace; color: var(--green); }
.stat span { color: var(--ink-soft); font-size: 14px; }
section { padding: 92px 0; border-top: 1px solid var(--line); }
.section-head { display: grid; grid-template-columns: minmax(0, .72fr) minmax(320px, .48fr); gap: 36px; align-items: end; margin-bottom: 42px; }
.kicker { margin: 0 0 12px; color: var(--orange); font: 800 12px ui-monospace, monospace; letter-spacing: .12em; text-transform: uppercase; }
h2 { margin: 0; font: 800 clamp(38px, 5vw, 68px)/1 "Songti SC", STSong, "Noto Serif CJK SC", serif; letter-spacing: -.055em; }
.section-note { margin: 0; color: var(--ink-soft); }
.use-grid { display: grid; grid-template-columns: 1.1fr .9fr; gap: 18px; }
.use-card { min-height: 340px; padding: clamp(26px, 4vw, 48px); border: 1px solid var(--line); background: var(--card); }
.use-card.dark { background: var(--ink); color: white; border-color: var(--ink); }
.use-card h3 { margin: 0 0 24px; font: 800 28px/1.2 "Songti SC", STSong, serif; }
.check-list { list-style: none; margin: 0; padding: 0; }
.check-list li { position: relative; padding: 13px 0 13px 32px; border-top: 1px solid currentColor; border-color: #8c958f55; }
.check-list li::before { content: "✓"; position: absolute; left: 0; color: var(--orange); font-weight: 900; }
.use-card.dark .check-list li::before { content: "—"; color: var(--yellow); }
.install-card { display: grid; grid-template-columns: .42fr .58fr; border: 1px solid var(--ink); background: var(--card); box-shadow: var(--shadow); }
.install-copy { padding: clamp(28px, 5vw, 56px); background: var(--green); color: white; }
.install-copy .kicker { color: var(--yellow); }
.install-copy h2 { font-size: clamp(38px, 5vw, 62px); }
.install-copy p { color: #d9e7df; }
.install-panel { min-width: 0; padding: clamp(24px, 4vw, 44px); display: flex; flex-direction: column; justify-content: center; }
.install-panel pre { margin: 0; max-height: 320px; overflow: auto; white-space: pre-wrap; background: #171c19; color: #f4f0e6; border: 1px solid #050706; padding: 22px; font: 13px/1.75 ui-monospace, SFMono-Regular, Menlo, monospace; }
.copy-row { display: flex; align-items: center; flex-wrap: wrap; gap: 14px; margin-top: 16px; }
.copy-row .button { background: var(--ink); color: white; }
.copy-status { color: var(--green); font-size: 14px; }
.steps { display: grid; grid-template-columns: repeat(3, 1fr); border: 1px solid var(--line); border-right: 0; }
.start-step { position: relative; min-height: 220px; padding: 28px; border-right: 1px solid var(--line); background: #ffffff45; }
.start-step b { display: block; color: var(--orange); font: 800 13px ui-monospace, monospace; }
.start-step h3 { margin: 48px 0 12px; font-size: 23px; }
.start-step p { margin: 0; color: var(--ink-soft); }
.stage-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.stage-card { min-width: 0; min-height: 270px; padding: 22px; background: var(--card); border: 1px solid var(--line); border-top: 4px solid var(--green); }
.stage-card:nth-child(5), .stage-card:nth-child(8), .stage-card:nth-child(10) { border-top-color: var(--orange); }
.stage-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.stage-index { color: var(--green); font: 800 22px ui-monospace, monospace; }
.stage-en { color: var(--ink-soft); font: 700 11px ui-monospace, monospace; text-transform: uppercase; }
.stage-card h3 { margin: 22px 0 10px; font: 800 22px/1.2 "Songti SC", STSong, serif; }
.stage-outcome { margin: 0; color: var(--ink-soft); font-size: 14px; }
details { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--line); }
summary { cursor: pointer; color: var(--green); font-size: 13px; font-weight: 750; }
dl { margin: 12px 0 0; font-size: 12px; }
dt { margin-top: 10px; color: var(--ink-soft); font-weight: 800; }
dd { margin: 2px 0 0; }
.route-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.route-card { min-width: 0; min-height: 150px; padding: 22px; background: #ffffff55; border: 1px solid var(--line); }
.route-mark { display: block; width: 34px; height: 5px; margin-bottom: 26px; background: var(--orange); }
.route-card p { margin: 0 0 15px; font-weight: 750; }
code { color: var(--green); font: 12px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; word-break: break-all; }
.principles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.principle { padding: 26px 0; border-top: 4px solid var(--ink); }
.principle h3 { margin: 0 0 10px; font-size: 20px; }
.principle p { margin: 0; color: var(--ink-soft); }
footer { padding: 38px 0 60px; border-top: 1px solid var(--line); color: var(--ink-soft); }
.footer-row { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.stamp { font: 11px ui-monospace, SFMono-Regular, monospace; }
@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; min-height: auto; padding-top: 64px; }
  .hero-board { max-width: 620px; }
  .stats { grid-template-columns: repeat(2, 1fr); border-bottom: 0; }
  .stat { border-bottom: 1px solid var(--line); }
  .section-head, .install-card { grid-template-columns: 1fr; }
  .stage-grid { grid-template-columns: repeat(2, 1fr); }
  .route-grid, .principles { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 620px) {
  .shell { width: min(100% - 28px, 1180px); }
  .topbar nav a:not(:last-child) { display: none; }
  .hero { padding: 52px 0 70px; gap: 36px; }
  h1 { font-size: clamp(58px, 22vw, 88px); }
  .stats { margin-bottom: 70px; }
  .stat { min-height: 112px; padding: 18px; }
  section { padding: 70px 0; }
  .section-head { grid-template-columns: 1fr; margin-bottom: 30px; }
  .use-grid, .steps, .stage-grid, .route-grid, .principles { grid-template-columns: 1fr; }
  .steps { border-bottom: 0; }
  .start-step { min-height: 180px; border-bottom: 1px solid var(--line); }
  .stage-card { min-height: auto; }
  .footer-row { align-items: flex-start; flex-direction: column; }
}
@media (prefers-reduced-motion: no-preference) {
  .button, .stage-card, .route-card { transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease; }
  .stage-card:hover, .route-card:hover { transform: translateY(-4px); border-color: var(--green); box-shadow: 0 12px 32px rgba(23, 32, 27, .08); }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
}
</style>
</head>
<body>
<a class="skip-link" href="#main">跳到主要内容</a>
<header class="shell topbar">
  <a class="brand" href="#top">workflow / 2.0 beta</a>
  <nav aria-label="页面导航">
    <a href="#use">什么时候用</a>
    <a href="#flow">工作流程</a>
    <a href="__REPOSITORY__">GitHub</a>
  </nav>
</header>
<main id="main">
  <div class="shell hero" id="top">
    <div>
      <p class="eyebrow">workflow · 复杂任务总导演</p>
      <h1>复杂任务<br><span>真正做完</span></h1>
      <p class="lede">一个可独立安装的 AI skill。从需求挖掘到设计、计划、执行、调试、验证与交付，只装这一个就够了。</p>
      <div class="hero-actions">
        <a class="button primary" href="#install">复制给 Agent 安装</a>
        <a class="button" href="#flow">看十阶段闭环</a>
      </div>
    </div>
    <aside class="hero-board" aria-label="workflow 核心运行规则">
      <div class="rule"><b>01</b><p><strong>先想清楚，再写计划</strong><span>UI 任务必须先定体验、视觉和动效。</span></p></div>
      <div class="rule"><b>02</b><p><strong>只补真正阻断的基础</strong><span>成熟项目零改动，极端时最多新增一份入口文档。</span></p></div>
      <div class="rule"><b>03</b><p><strong>没有证据，不说完成</strong><span>每一层结论都要有刚刚跑出的验证支撑。</span></p></div>
      <div class="rule"><b>04</b><p><strong>外部动作，明确授权</strong><span>不会擅自提交、推送、发布、部署或删除。</span></p></div>
    </aside>
  </div>

  <div class="shell stats" aria-label="workflow 结构数据">
    <div class="stat"><b>1</b><span>一个根 skill 入口</span></div>
    <div class="stat"><b>10</b><span>十个闭环阶段</span></div>
    <div class="stat"><b>14</b><span>十四份按需能力</span></div>
    <div class="stat"><b>0</b><span>外部 skill 依赖</span></div>
  </div>

  <section id="use">
    <div class="shell">
      <div class="section-head">
        <div><p class="kicker">Use the right tool</p><h2>什么时候用</h2></div>
        <p class="section-note">workflow 专门处理“不能靠一次回答安全做完”的任务。小事不立项，复杂事不跳步。</p>
      </div>
      <div class="use-grid">
        <article class="use-card">
          <h3>适合交给 workflow</h3>
          <ul class="check-list">
            <li>跨文件、跨步骤或跨会话的复杂功能</li>
            <li>需求混杂，需要先做取舍和方案收敛</li>
            <li>涉及 UI、视觉、动效或完整交互状态</li>
            <li>需要多 Agent 协作、调试、发布或交付</li>
          </ul>
        </article>
        <article class="use-card dark">
          <h3>这些事直接做更快</h3>
          <ul class="check-list">
            <li>纯问答或解释一个概念</li>
            <li>修改一个错别字</li>
            <li>一次性、低风险的小操作</li>
            <li>已经明确且一步可验证的任务</li>
          </ul>
        </article>
      </div>
    </div>
  </section>

  <section id="install">
    <div class="shell install-card">
      <div class="install-copy">
        <p class="kicker">One prompt install</p>
        <h2>复制给 Agent 安装</h2>
        <p>不用先研究 skills 目录，也不用安装其他 skill。Agent 会确认自己的目录、安装并跑完检查；有歧义就停下来，不会猜。</p>
      </div>
      <div class="install-panel">
        <pre><code id="agent-prompt">__AGENT_PROMPT__</code></pre>
        <div class="copy-row">
          <button class="button" type="button" data-copy-target="agent-prompt">复制安装指令</button>
          <span class="copy-status" aria-live="polite"></span>
        </div>
      </div>
    </div>
  </section>

  <section aria-labelledby="start-title">
    <div class="shell">
      <div class="section-head">
        <div><p class="kicker">Quick start</p><h2 id="start-title">三步开始</h2></div>
        <p class="section-note">安装完成后，不需要学习命令语法。正常说出目标即可。</p>
      </div>
      <div class="steps">
        <article class="start-step"><b>STEP 01</b><h3>让 Agent 安装</h3><p>复制上面的指令，等待安装与检查都通过。</p></article>
        <article class="start-step"><b>STEP 02</b><h3>直接描述目标</h3><p>说清想要的结果、已有材料和不能碰的边界。</p></article>
        <article class="start-step"><b>STEP 03</b><h3>按证据验收</h3><p>查看实际产物、验证结果、风险与下一步，不接受口头完成。</p></article>
      </div>
    </div>
  </section>

  <section id="flow">
    <div class="shell">
      <div class="section-head">
        <div><p class="kicker">Closed loop</p><h2>十阶段闭环</h2></div>
        <p class="section-note">每张卡片都有明确入口、允许写入、出口和回退。阶段不满足就返回缺口来源，不带病推进。</p>
      </div>
      <div class="stage-grid">__STATE_CARDS__</div>
    </div>
  </section>

  <section aria-labelledby="routes-title">
    <div class="shell">
      <div class="section-head">
        <div><p class="kicker">Progressive loading</p><h2 id="routes-title">按需能力库</h2></div>
        <p class="section-note">十四项能力全部随 workflow 一起安装，但默认一次只读取当前需要的一项，减少上下文噪音。</p>
      </div>
      <div class="route-grid">__ROUTE_CARDS__</div>
    </div>
  </section>

  <section aria-labelledby="principles-title">
    <div class="shell">
      <div class="section-head">
        <div><p class="kicker">Less, but complete</p><h2 id="principles-title">完整，但不臃肿</h2></div>
        <p class="section-note">第一性原理决定必须守住什么；奥卡姆剃刀负责删除不产生结果的流程与文档。</p>
      </div>
      <div class="principles">
        <article class="principle"><h3>项目基础只设一道门</h3><p>能定位入口、约束、关键命令和验证路径就直接通过，不维护大而全的 Foundation 体系。</p></article>
        <article class="principle"><h3>设计只在需要时进入</h3><p>UI 任务先选体验与动效；非 UI 明确记为不适用，不走形式流程。</p></article>
        <article class="principle"><h3>平台能力可以降级</h3><p>没有浏览器、Git、memory 或 subagent 仍能安全推进，只是不伪造缺失的证据。</p></article>
      </div>
    </div>
  </section>
</main>
<footer>
  <div class="shell footer-row">
    <span>workflow · 单技能复杂任务编排</span>
    <span class="stamp">source sha256 __DIGEST__ · standalone / no external assets</span>
  </div>
</footer>
<script>
(() => {
  const button = document.querySelector("[data-copy-target]");
  const status = document.querySelector(".copy-status");
  if (!button || !status) return;
  button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copyTarget);
    if (!target) return;
    const value = target.textContent.trim();
    try {
      await navigator.clipboard.writeText(value);
    } catch (_) {
      const area = document.createElement("textarea");
      area.value = value;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    status.textContent = "已复制，可以粘贴给 Agent";
    button.textContent = "已复制";
  });
})();
</script>
</body>
</html>
"""


def render() -> str:
    source = SOURCE.read_text(encoding="utf-8")
    states = table_rows(section(source, "## 状态接口与硬门", "## 按需路由"), 5)
    routes = table_rows(section(source, "## 按需路由", "## 文件真源"), 2)
    if len(states) != 10 or len(routes) != 14:
        raise ValueError(f"unexpected contract shape: states={len(states)}, routes={len(routes)}")
    unknown = [name for name, *_ in states if name not in STATE_LABELS]
    if unknown:
        raise ValueError("missing Chinese state labels: " + ", ".join(unknown))
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
    return (
        HTML_TEMPLATE.replace("__REPOSITORY__", html.escape(REPOSITORY, quote=True))
        .replace("__AGENT_PROMPT__", html.escape(AGENT_PROMPT))
        .replace("__STATE_CARDS__", render_state_cards(states))
        .replace("__ROUTE_CARDS__", render_route_cards(routes))
        .replace("__DIGEST__", digest)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the generated document is stale")
    args = parser.parse_args()
    try:
        generated = render()
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
