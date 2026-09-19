#!/usr/bin/env python3
"""从技能真源生成可展开说明页，不维护第二套政策。"""
from __future__ import annotations

import argparse
import hashlib
import html
from pathlib import Path
import re
import sys

PACKAGE = Path(__file__).resolve().parents[1]
OUTPUT = PACKAGE / "docs/workflow-visual-map.html"
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def inline(text: str) -> str:
    def link(match: re.Match) -> str:
        label, raw = match.groups()
        if raw.startswith(("https://", "http://", "#")):
            target = raw
        else:
            target = "../" + raw
        return f'<a href="{html.escape(target, quote=True)}">{html.escape(label)}</a>'
    # Escape before interpreting markdown so document text cannot inject HTML.
    escaped = html.escape(text)
    escaped = LINK.sub(lambda m: link(m), escaped)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def render(text: str) -> str:
    text = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S)
    output, paragraph, table, code = [], [], [], []
    in_code = False

    def flush() -> None:
        if paragraph:
            output.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()
        if table:
            rows = []
            for index, line in enumerate(table):
                cells = [part.strip() for part in line.strip("|").split("|")]
                if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                    continue
                tag = "th" if index == 0 else "td"
                rows.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>")
            output.append('<div class="table"><table>' + "".join(rows) + "</table></div>")
            table.clear()

    for line in text.splitlines():
        if line.startswith("```"):
            flush()
            if in_code:
                output.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
                code.clear()
            in_code = not in_code
        elif in_code:
            code.append(line)
        elif not line.strip():
            flush()
        elif line.startswith("|"):
            if paragraph:
                flush()
            table.append(line)
        elif re.match(r"^#{1,6} ", line):
            flush()
            marks, title = line.split(" ", 1)
            level = min(len(marks) + 1, 6)
            output.append(f"<h{level}>{inline(title)}</h{level}>")
        elif line.startswith("- "):
            flush()
            output.append('<p class="rule">' + inline(line[2:]) + "</p>")
        else:
            paragraph.append(line)
    flush()
    if in_code:
        raise ValueError("未闭合代码块")
    return "\n".join(output)


def build() -> tuple[str, str]:
    skill = PACKAGE / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    match = re.search(r"^version:\s*(\S+)$", text, re.M)
    if not match:
        raise ValueError("SKILL.md 缺少版本")
    version = match.group(1)
    # The route table is the sole reference index. No fixed stage names or
    # confirmation wording is required by this renderer.
    references = list(dict.fromkeys(raw for _, raw in LINK.findall(text) if raw.startswith("references/")))
    paths = [skill, *(PACKAGE / raw for raw in references), PACKAGE / "templates/work.md"]
    digest = hashlib.sha256()
    cards = []
    for path in paths:
        contents = path.read_text(encoding="utf-8")
        relative = path.relative_to(PACKAGE).as_posix()
        digest.update(relative.encode() + b"\0" + contents.encode() + b"\0")
        if path != skill:
            title = re.search(r"^# (.+)$", contents, re.M)
            if not title:
                raise ValueError(f"缺少标题：{relative}")
            # References link to siblings; normalize those links for docs/.
            if relative.startswith("references/"):
                contents = LINK.sub(lambda m: f"[{m[1]}]({m[2] if ':' in m[2] or m[2].startswith('#') else 'references/' + m[2]})", contents)
            cards.append("<details><summary>" + html.escape(title.group(1)) + "</summary>" + render(contents) + "</details>")
    identity = digest.hexdigest()[:12]
    page = TEMPLATE.replace("__VERSION__", html.escape(version)).replace("__DIGEST__", identity)
    page = page.replace("__ROOT__", render(text)).replace("__REFERENCES__", "\n".join(cards))
    return page, identity


TEMPLATE = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>workflow __VERSION__ · 工作规则</title>
<style>
:root{color-scheme:dark;--paper:#f0f1e9;--muted:#abb8b1;--mint:#a8edca;--line:#314039}
*{box-sizing:border-box}body{margin:0;background:#101b16;color:var(--paper);font:16px/1.8 system-ui,-apple-system,sans-serif}
main{max-width:1000px;margin:auto;padding:60px 24px}header{padding-bottom:36px;border-bottom:1px solid var(--line)}
header p{color:var(--mint);letter-spacing:.1em}h1{font-size:clamp(38px,7vw,64px);line-height:1.2;margin:18px 0}h2{font-size:28px;margin-top:36px}h3{font-size:21px}
p{max-width:85ch}a{color:var(--mint);text-underline-offset:4px}a:hover{color:#fff}a:focus-visible,summary:focus-visible{outline:2px solid var(--mint);outline-offset:5px}
.rule{padding-left:16px;border-left:3px solid var(--mint)}code{font: .9em/1.7 ui-monospace,monospace;background:#203128;padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}
pre{padding:18px;background:#07110b;border:1px solid var(--line);overflow:auto}pre code{padding:0;background:none;white-space:pre}
.table{overflow:auto}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:12px;border-bottom:1px solid var(--line)}th{color:var(--mint)}
details{border:1px solid var(--line);border-radius:10px;padding:18px 22px;margin:12px 0}summary{cursor:pointer;font-weight:700;font-size:19px}details[open]{background:#15251c}
footer{margin-top:45px;padding-top:20px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}
@media(max-width:600px){main{padding:28px 16px}details{padding:14px}th,td{padding:9px}body{font-size:15px}}
</style></head><body><main data-source-digest="__DIGEST__">
<header><p>workflow · __VERSION__</p><h1>目标明确，持续完成。</h1><a href="../README.md">安装与使用</a> · <a href="../evals/README.md">行为评测</a></header>
<section>__ROOT__</section><section aria-label="按需展开参考">__REFERENCES__</section>
<footer>由 SKILL.md、其参考与工作模板生成。页面不定义额外规则。source sha256 __DIGEST__</footer>
</main></body></html>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        page, _ = build()
        if args.check:
            if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != page:
                print("视觉图已过期", file=sys.stderr)
                return 1
            print("workflow_visual_map: OK")
        else:
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(page, encoding="utf-8")
            print("已生成 docs/workflow-visual-map.html")
    except (OSError, ValueError) as exc:
        print(f"视觉图真源错误：{exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
