#!/usr/bin/env python3
"""从技能真源生成可展开说明页，不维护第二套政策。"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import posixpath
from pathlib import Path
import re
import sys
import subprocess

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


def anchor(path: str) -> str:
    return "doc-" + path.encode().hex()


def fill(page: str, values: dict[str, str]) -> str:
    # Replace only original template tokens, never tokens carried in a diff.
    return re.sub('|'.join(re.escape(key) for key in values), lambda match: values[match[0]], page)


def document(text: str, relative: str, sources: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        label, target = match.groups()
        if ':' not in target and not target.startswith('#'):
            path = posixpath.normpath(posixpath.join(posixpath.dirname(relative), target.split('#')[0]))
            if path in sources:
                return f'[{label}](#{anchor(path)})'
        return match[0]
    return render(LINK.sub(replace, text))


def opening(text: str) -> str:
    paragraph = re.search(r'^# [^\n]+\n+(.*?)(?=\n\s*\n|\Z)', text, re.M | re.S)
    return paragraph[1].strip() if paragraph else ''


def section(text: str, title: str) -> str:
    match = re.search(r'^## ' + re.escape(title) + r'\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    return match[1].strip() if match else ''


def table_rows(text: str, columns: int) -> list[list[str]]:
    rows, first = [], True
    for line in text.splitlines():
        if not line.startswith('|'):
            first = True
            continue
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        if first:
            first = False
            continue
        if len(cells) == columns and not all(re.fullmatch(r':?-+:?', cell) for cell in cells):
            rows.append(cells)
    return rows


def route_groups(sources: dict[str, str]) -> dict[str, list[list[str]]]:
    groups, group = {}, '按需参考'
    for block in re.split(r'(^### .+$)', sources['SKILL.md'], flags=re.M):
        if block.startswith('### '):
            group = block[4:].strip()
        else:
            for condition, target in table_rows(block, 2):
                if any(path.split('#')[0] in sources and path.startswith('references/') for _, path in LINK.findall(target)):
                    groups.setdefault(group, []).append([condition, target])
    covered = {path.split('#')[0] for rows in groups.values() for _, target in rows for _, path in LINK.findall(target)}
    for path, contents in sources.items():
        if path.startswith('references/') and path not in covered:
            title = re.search(r'^# (.+)$', contents, re.M)[1]
            groups.setdefault('其他按需参考', []).append([opening(contents), f'[{title}]({path})'])
    return groups


def routing(sources: dict[str, str]) -> str:
    return ''.join('<section class="capability-group"><h3>' + html.escape(group) + '</h3><div class="module-list">'
                   + ''.join('<div class="module-row">' + document(target, 'SKILL.md', sources)
                             + '<span class="module-condition">' + inline(condition) + '</span></div>'
                             for condition, target in rows) + '</div></section>'
                   for group, rows in route_groups(sources).items())


def decisions(text: str) -> str:
    rows = table_rows(section(text, '判断当前请求'), 3)
    if not rows:
        return '<p>该版本未将请求分支列成表格，请从完整入口查看原有规则。</p>'
    return ''.join('<details class="decision"><summary><span class="branch-number">' + str(i + 1).zfill(2)
                   + '</span>' + inline(condition) + '</summary><div class="branch-body"><span class="label">本轮动作</span>'
                   + '<div class="action-path">' + '<span class="arrow" aria-hidden="true">→</span>'.join('<span>' + inline(step) + '</span>' for step in action.split(' → '))
                   + '</div><p><span class="label">结束或交接点</span>' + inline(stop) + '</p></div></details>'
                   for i, (condition, action, stop) in enumerate(rows))


def outcomes(text: str) -> str:
    if not table_rows(section(text, '推进与停止'), 2):
        return '<p>该版本未将停止条件列成表格，请从完整入口查看原有规则。</p>'
    return '<div class="outcome-list">' + ''.join('<div class="outcome"><div>' + inline(state)
                   + '</div><span class="arrow" aria-hidden="true">→</span><p>' + inline(action) + '</p></div>'
                   for state, action in table_rows(section(text, '推进与停止'), 2)) + '</div>'


def page_from_sources(sources: dict[str, str], changelog: str = '') -> tuple[str, str]:
    text = sources['SKILL.md']
    match = re.search(r"^version:\s*(\S+)$", text, re.M)
    if not match:
        raise ValueError("SKILL.md 缺少版本")
    version = match.group(1)
    notes = re.search(r'^## \[' + re.escape(version) + r'\][^\n]*\n(.*?)(?=^## \[|\Z)', changelog, re.M | re.S)
    changes = notes[1].strip() if notes else '此版本未提供变更说明；请查看版本差异。'
    # Navigation and release notes reuse existing sources, with no second inventory.
    digest = hashlib.sha256()
    digest.update(changes.encode() + b'\0')
    cards = []
    conditions = {}
    for rows in route_groups(sources).values():
        for condition, target in rows:
            for _, path in LINK.findall(target):
                conditions[path] = condition + ' → ' + target
    for relative, contents in sources.items():
        digest.update(relative.encode() + b"\0" + contents.encode() + b"\0")
        title = re.search(r"^# (.+)$", contents, re.M)
        if not title:
            raise ValueError(f"缺少标题：{relative}")
        context = document(conditions[relative], 'SKILL.md', sources) if relative in conditions else ''
        cards.append(f'<details class="reference" id="{anchor(relative)}" data-path="{html.escape(relative)}" hidden>'
                     + "<summary>" + html.escape(title.group(1)) + "</summary>"
                     + '<div class="reference-context"><span class="label">何时调用</span>' + context + '</div>'
                     + '<details class="raw-source"><summary>查看完整 Markdown 原文</summary><pre>' + html.escape(contents) + '</pre></details>'
                     + '<div class="reading-body">' + document(contents, relative, sources) + '</div></details>')
    identity = digest.hexdigest()[:12]
    page = TEMPLATE.replace("__VERSION__", html.escape(version)).replace("__DIGEST__", identity)
    page = fill(page, {'__CHANGES__': render(changes), '__REFERENCES__': '\n'.join(cards),
                       '__INTRO__': document(opening(text), 'SKILL.md', sources),
                       '__ROUTING__': routing(sources), '__DECISIONS__': decisions(text), '__OUTCOMES__': outcomes(text),
                       '__ROOT_LINK__': '#' + anchor('SKILL.md')})
    return page, identity


def build() -> tuple[str, str]:
    paths = ['SKILL.md', *sorted(p.relative_to(PACKAGE).as_posix() for p in (PACKAGE/'references').glob('*.md'))]
    if (PACKAGE/'templates/work.md').is_file():
        paths.append('templates/work.md')
    changelog = PACKAGE/'CHANGELOG.md'
    page, identity = page_from_sources({p: (PACKAGE/p).read_text(encoding='utf-8') for p in paths},
                                      changelog.read_text(encoding='utf-8') if changelog.is_file() else '')
    return fill(page, {'__REVIEW_INFO__': '下载 <a href="https://github.com/qzl0215/workflow/releases/latest">正式 Release</a> 的 workflow-review.html 查看版本差异。',
                       '__PATCH__': '""', '__CSS__': '', '__LIBRARY__': ''}), identity


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(['git', *args], cwd=repo, capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise ValueError(result.stderr.strip() or 'Git 读取失败')
    return result.stdout


def build_review(repo: Path, base: str, target: str, *, asset_root: Path | None = None) -> tuple[str, dict]:
    """Build a portable review from immutable trees, never from dirty working files."""
    def resolve(value: str) -> str:
        if value.startswith('-'):
            raise ValueError('无效版本引用')
        return git(repo, 'rev-parse', '--verify', '--end-of-options', value+'^{commit}').strip()
    before, after = resolve(base), resolve(target)
    names = git(repo, 'ls-tree', '-r', '--name-only', after).splitlines()
    paths = ['SKILL.md', *sorted(p for p in names if p.startswith('references/') and p.endswith('.md'))]
    if 'templates/work.md' in names:
        paths.append('templates/work.md')
    page, digest = page_from_sources({p: git(repo, 'show', f'{after}:{p}') for p in paths},
                                    git(repo, 'show', f'{after}:CHANGELOG.md') if 'CHANGELOG.md' in names else '')
    excluded = ['docs/workflow-visual-map.html', 'docs/assets/diff2html/diff2html.min.js',
                'docs/assets/diff2html/diff2html.min.css', 'docs/assets/diff2html/LICENSE.md']
    patch = git(repo, '-c', 'core.quotePath=false', 'diff', '--no-ext-diff', '--no-textconv', '--no-color',
                '--find-renames', before, after, '--', '.', *(':(exclude)'+p for p in excluded))
    info = {'base': before, 'target': after, 'source_digest': digest, 'patch': patch, 'excluded': excluded}
    if asset_root is None:
        asset = lambda name: git(repo, 'show', f'{after}:docs/assets/diff2html/{name}')
    else:
        asset = lambda name: (asset_root/name).read_text(encoding='utf-8')
    provenance = json.loads(asset('provenance.json'))
    for record in provenance['files']:
        if hashlib.sha256(asset(record['file']).encode()).hexdigest() != record['sha256']:
            raise ValueError('diff2html 静态资源身份不匹配')
    css, js, license_text = asset('diff2html.min.css'), asset('diff2html.min.js'), asset('LICENSE.md')
    if '</script' in js.lower() or '</style' in css.lower():
        raise ValueError('静态资源不能安全内联')
    description = (f'基线 <code>{before}</code> → 目标 <code>{after}</code><br>'
                   f'diff2html {html.escape(provenance["version"])}；全文取自目标提交。差异不包含生成 HTML 与库文件：'
                   + html.escape(', '.join(excluded)) + '。二进制差异仅显示 Git 标记。'
                   + '<details><summary>开源许可证</summary><pre>'+html.escape(license_text)+'</pre></details>')
    page = fill(page, {'__REVIEW_INFO__': description, '__PATCH__': json.dumps(patch, ensure_ascii=True).replace('<','\\u003c'),
                       '__CSS__': '<style>'+css+'</style>', '__LIBRARY__': '<script>'+js+'</script>'})
    # The standalone release must not depend on sibling repository documents.
    page = page.replace('href="../', f'href="https://github.com/qzl0215/workflow/blob/{after}/')
    return page, info


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>workflow __VERSION__ · 工作地图</title>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; base-uri 'none'; form-action 'none'">
__CSS__
<style>
:root{color-scheme:light;--ink:#182c30;--muted:#56666a;--accent:#086a70;--line:#d4dcd9;--paper:#f7f8f5;--soft:#eaf2ef}
*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;color:var(--ink);background:var(--paper);font:16px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
a{color:var(--accent);text-underline-offset:4px}button,input,select{font:inherit;color:inherit}button,a,summary,input,select{touch-action:manipulation}button,summary{cursor:pointer}:focus-visible{outline:3px solid #d0872d;outline-offset:4px}button{background:transparent}p{margin:12px 0}h1,h2,h3{line-height:1.35}h1{font-size:46px;letter-spacing:-.035em;margin:18px 0}h2{font-size:27px;margin:0 0 14px}h3{font-size:19px}code{font:.9em/1.6 ui-monospace,monospace;overflow-wrap:anywhere;background:var(--soft);padding:2px 5px;border-radius:3px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--paper);padding:16px;border:1px solid var(--line);font:13px/1.7 ui-monospace,monospace;overflow:auto}.table{overflow:auto}table{border-collapse:collapse;width:100%}th,td{padding:12px;text-align:left;border-bottom:1px solid var(--line)}td{vertical-align:top}th{color:var(--accent)}
.topbar{max-width:1200px;margin:auto;display:flex;align-items:center;justify-content:space-between;padding:22px 32px;border-bottom:1px solid var(--line);font-size:13px}.brand{font-weight:800;letter-spacing:.13em}.topbar nav{display:flex;gap:22px}.topbar nav a{text-decoration:none;color:var(--muted)}main{max-width:1200px;margin:auto;padding:40px 32px 70px}.hero{display:grid;grid-template-columns:1.5fr 1fr;gap:50px;align-items:end;margin-bottom:32px}.eyebrow,.label{font:700 11px/1.6 ui-monospace,-apple-system,sans-serif;letter-spacing:.08em;color:var(--accent);text-transform:uppercase}.hero h1 span{color:var(--accent)}.hero p{max-width:32em;color:var(--muted)}.hero-note{border-left:2px solid var(--accent);padding-left:22px;font-size:15px}.hero-note p{margin:4px 0 12px}.hero-note a{font-size:13px}
.flow{position:relative;margin:0;background:white;border:1px solid var(--line);padding:28px 26px 64px;border-radius:4px}.flow-grid{position:relative;z-index:1;display:grid;grid-template-columns:1fr 50px 1fr 50px 1fr;align-items:center}.flow-node{border:1px solid var(--line);padding:22px 18px;text-align:left;background:var(--paper);min-width:0;min-height:133px;border-radius:3px}.flow-node[aria-selected=true]{background:var(--accent);border-color:var(--accent);color:white}.flow-node small{font:12px ui-monospace,monospace;display:block;opacity:.75}.flow-node strong{display:block;font-size:23px;margin:10px 0 4px}.flow-node span{font-size:13px;opacity:.85}.connector{color:var(--accent);font-size:28px;text-align:center}.return-line{position:absolute;bottom:20px;left:50%;width:34%;height:38px;border:1px solid var(--accent);border-top:0;border-radius:0 0 8px 8px;pointer-events:none}.return-line:before{content:'↑';position:absolute;left:-7px;top:0;color:var(--accent);background:#fff;line-height:1}.return-line span{position:absolute;bottom:-12px;left:10%;white-space:nowrap;background:#fff;padding:0 12px;font-size:12px;color:var(--accent)}.figure-note{display:flex;justify-content:space-between;gap:20px;color:var(--muted);font-size:12px;margin:10px 0 30px}
.workbench{display:grid;grid-template-columns:225px minmax(0,1fr);gap:36px;padding:28px 0 40px;border-top:1px solid var(--line)}.panel-intro h2{font-size:24px;margin-top:8px}.panel-intro p{font-size:14px;color:var(--muted)}.panel-intro a{font-size:13px}.decision{border-bottom:1px solid var(--line);background:white}.decision summary{display:flex;align-items:center;gap:18px;list-style:none;padding:17px 20px;font-size:15px}.decision summary::-webkit-details-marker{display:none}.decision summary:after{content:'+';margin-left:auto;font-size:22px;color:var(--accent)}.decision[open] summary:after{content:'−'}.branch-number{font:13px ui-monospace,monospace;color:var(--accent);flex:none}.branch-body{padding:0 22px 18px 57px;font-size:14px}.branch-body .label{display:block}.action-path{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:6px 0 12px}.action-path>span:not(.arrow){border:1px solid var(--line);padding:5px 10px;background:var(--soft)}.arrow{color:var(--accent);font-size:20px}.branch-body p{margin-bottom:0}.capability-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px 34px}.capability-group h3{font-size:13px;letter-spacing:.06em;color:var(--muted);border-bottom:2px solid var(--accent);padding-bottom:8px;margin:0}.module-row{border-bottom:1px solid var(--line);padding:10px 0}.module-row p{margin:0;font-size:15px}.module-row a{font-weight:650;text-decoration:none}.module-row a:after{content:' ↗';font-size:11px}.module-condition{display:block;color:var(--muted);font-size:12px;line-height:1.6;margin-top:3px}.outcome{display:grid;grid-template-columns:minmax(0,1fr) 22px minmax(0,1.5fr);gap:14px;align-items:center;padding:17px 0;border-bottom:1px solid var(--line);font-size:14px}.outcome>div{font-weight:650}.outcome p{margin:0}.outcome:last-child>div{color:var(--accent)}.searchline{display:flex;gap:12px;margin-bottom:18px;align-items:center}.searchline input{width:100%;border:0;border-bottom:1px solid var(--line);background:transparent;padding:10px 0;min-width:0}.searchline span{font-size:12px;color:var(--muted);white-space:nowrap}.no-result{font-size:14px;color:var(--muted)}
#changes{border-top:1px solid var(--line);padding-top:32px;margin-top:10px}.change-layout{max-width:74ch;font-size:15px}.change-layout .rule{padding-left:16px;border-left:2px solid var(--accent);margin:14px 0}.review{margin-top:24px;border:1px solid var(--line);padding:18px 22px;background:white}.review>summary{font-size:16px;font-weight:650}.review small{color:var(--muted)}.toolbar{display:flex;gap:16px;flex-wrap:wrap;margin:20px 0}.toolbar select{background:var(--paper);padding:6px;border:1px solid var(--line)}#diff{overflow-x:auto}.d2h-wrapper{background:white;color:#222}.d2h-code-line-ctn{white-space:pre-wrap;overflow-wrap:anywhere}.d2h-code-side-line{width:100%}.d2h-wrapper td{padding:0}.d2h-wrapper a{color:var(--accent)}#diff-status{font-size:13px;color:var(--muted)}footer{font-size:12px;color:var(--muted);margin-top:35px}
.reader{position:fixed;inset:0 0 0 auto;margin:0;border:0;border-left:1px solid var(--line);width:min(720px,100vw);max-width:100vw;height:100dvh;max-height:100dvh;background:#fff;color:var(--ink);padding:0}.reader::backdrop{background:#12292e70}.reader-bar{position:sticky;top:0;z-index:2;background:#fff;display:flex;justify-content:space-between;align-items:center;padding:16px 28px;border-bottom:1px solid var(--line)}.reader-bar span{font-size:12px;color:var(--muted)}.reader-bar button{border:1px solid var(--line);padding:5px 14px;border-radius:3px}.reference{padding:26px 32px 50px;max-width:100%}.reference>summary{list-style:none;font-size:30px;font-weight:700;pointer-events:none}.reference>summary::-webkit-details-marker{display:none}.reference-context{border-left:3px solid var(--accent);padding:10px 16px;background:var(--soft);margin:20px 0;font-size:14px}.reference-context p{margin:4px 0}.reference-context:has(>.label:only-child){display:none}.raw-source{margin:20px 0;font-size:13px;color:var(--muted)}.reading-body{max-width:40em;line-height:1.95;font-size:16px}.reading-body>h2:first-child{display:none}.reading-body h3{font-size:21px;border-top:1px solid var(--line);padding-top:25px;margin-top:30px}.reading-body p{margin:18px 0}.reading-body .rule{padding:8px 0 8px 15px;border-left:2px solid var(--line);margin:12px 0}.reading-body table{font-size:14px}
@media(max-width:900px){.hero{grid-template-columns:1fr;gap:15px}.hero-note{max-width:40em}.workbench{grid-template-columns:1fr;gap:18px}.panel-intro p{margin:6px 0}.flow-node strong{font-size:19px}.flow-node{padding:18px 12px}.flow-grid{grid-template-columns:1fr 28px 1fr 28px 1fr}}
@media(max-width:600px){main{padding:25px 18px 45px}.topbar{padding:16px 18px}.topbar nav{gap:12px;font-size:12px}h1{font-size:34px}.hero{margin-bottom:25px}.hero-note{font-size:14px}.flow{padding:14px 12px 52px}.flow-grid{grid-template-columns:1fr 18px 1fr 18px 1fr}.flow-node{padding:14px 7px;min-height:116px}.flow-node strong{font-size:16px}.flow-node span{font-size:11px}.connector{font-size:18px}.return-line{left:18%;width:65%;bottom:18px}.return-line span{font-size:10px;left:5%;padding:0 5px}.figure-note{display:block;font-size:11px}.capability-grid{grid-template-columns:1fr}.decision summary{padding:14px 10px;gap:12px}.branch-body{padding:0 15px 15px 35px}.reference{padding:22px 20px}.reader-bar{padding:14px 20px}.outcome{gap:8px;font-size:13px}.reading-body{font-size:15px}.toolbar{font-size:13px}.review{padding:15px}.topbar .brand{letter-spacing:.05em}}
@media(max-width:600px){.flow{padding:16px}.flow-grid{grid-template-columns:1fr}.flow-node{min-height:0;padding:13px 16px;display:grid;grid-template-columns:1fr 1fr;align-items:center;gap:4px 10px}.flow-node small{grid-column:1;font-size:11px}.flow-node strong{grid-column:1;grid-row:2;margin:0;font-size:18px}.flow-node span{grid-column:2;grid-row:1/3;text-align:right;font-size:12px}.connector{transform:rotate(90deg);font-size:22px;height:26px;line-height:26px}.return-line{position:static;border:0;width:auto;height:auto;margin-top:14px}.return-line:before{display:none}.return-line span{position:static;background:transparent;display:block;text-align:center;font-size:12px;white-space:normal}.return-line span:before{content:'↩ ';font-size:16px}}
</style></head><body>
<div class="topbar"><a class="brand" href="#overview">WORKFLOW / __VERSION__</a><nav aria-label="页面导航"><a href="#changes">本版变化</a><a href="#review">版本对比</a><a href="../README.md">使用说明</a></nav></div>
<main data-source-digest="__DIGEST__">
<header id="overview" class="hero"><div><span class="eyebrow">工作地图 / 按需运行</span><h1>先分清任务，<br><span>再把结果做实。</span></h1><p>先看工作路径，点节点查判断条件。<br>每项能力的使用条件、做法和完整原文都可直接查看。</p></div><div class="hero-note"><p><b>AI 读得省</b>：精简入口，缺什么才读什么。</p><p><b>人读得懂</b>：先看关系，细节随时展开。</p><a href="__ROOT_LINK__">查看 AI 入口与完整规则 ↗</a></div></header>
<figure class="flow" aria-label="工作闭环示意图：判断请求，按需补齐能力，验证结果；仍有就绪工作则继续。">
<div class="flow-grid" role="tablist" aria-label="选择要了解的环节">
<button class="flow-node" id="tab-request" role="tab" aria-selected="true" aria-controls="panel-request" tabindex="0"><small>请求边界</small><strong>这次能做什么</strong><span>范围 · 确认 · 已有授权</span></button><span class="connector" aria-hidden="true">↔</span>
<button class="flow-node" id="tab-capabilities" role="tab" aria-selected="false" aria-controls="panel-capabilities" tabindex="-1"><small>当前缺口</small><strong>现在缺什么</strong><span>按需调用 · 补齐即返回</span></button><span class="connector" aria-hidden="true">↔</span>
<button class="flow-node" id="tab-outcomes" role="tab" aria-selected="false" aria-controls="panel-outcomes" tabindex="-1"><small>结果证据</small><strong>何时才算完成</strong><span>继续 · 恢复 · 交接 · 结束</span></button></div>
<div class="return-line"><span>仍有授权内工作可做，就继续</span></div></figure>
<div class="figure-note"><span>三个判断问题，按当前情况使用；不是必须走完的三个阶段。</span><span>根入口足够时，可以零参考。</span></div>
<section class="workbench" role="tabpanel" id="panel-request" aria-labelledby="tab-request"><div class="panel-intro"><span class="label">先识别本轮边界</span><h2>同一个请求，<br>先分清走哪条路。</h2><p>展开符合当前情况的一项，查看本轮动作与停止位置。</p><a href="__ROOT_LINK__">核对完整判断规则 ↗</a></div><div>__DECISIONS__</div></section>
<section class="workbench" role="tabpanel" id="panel-capabilities" aria-labelledby="tab-capabilities" hidden><div class="panel-intro"><span class="label">缺口驱动调用</span><h2>能力可以组合，<br>不用整套加载。</h2><p>这些分组用于定位问题，不是四个必经阶段。点击名称查看条件、方法与原文。</p><a href="__ROOT_LINK__">核对路由与例外 ↗</a></div><div><div class="searchline"><input id="search" type="search" placeholder="搜索能力或技能正文" aria-label="搜索能力或技能全文"><span id="count" role="status"></span></div><div id="routing" class="capability-grid">__ROUTING__</div><p class="no-result" id="no-result" hidden>没有匹配内容。换一个词，或查看完整入口。</p></div></section>
<section class="workbench" role="tabpanel" id="panel-outcomes" aria-labelledby="tab-outcomes" hidden><div class="panel-intro"><span class="label">闭环而非跑完步骤</span><h2>进度不等于结果，<br>证据决定下一步。</h2><p>对照当前状态，继续、恢复或交接。只有范围内的目标与交付都成立，才结束。</p><a href="__ROOT_LINK__">核对执行边界 ↗</a></div><div>__OUTCOMES__</div></section>
<section id="changes"><span class="label">版本记录 / 直接来自 CHANGELOG</span><h2>这次具体改了什么</h2><div class="change-layout">__CHANGES__</div></section>
<details id="review" class="review"><summary>查看版本高亮对比</summary><p>上方说明来自目标版本的 CHANGELOG。这里保留可复查的源码差异。</p><div>__REVIEW_INFO__</div><div class="toolbar" id="diff-controls"><label>内容 <select id="scope"><option value="rules">技能规则与参考</option><option value="all">全部源码（含维护工具）</option></select></label><label>布局 <select id="layout"><option value="side-by-side">并排</option><option value="line-by-line">逐行</option></select></label></div><p id="diff-status" role="status"></p><div id="diff"></div></details>
<footer>判断条件、能力分组与正文取自同一份技能源码。图只解释关系，不提供额外授权。source sha256 __DIGEST__</footer></main>
<dialog class="reader" id="reader" aria-label="技能详细阅读"><div class="reader-bar"><span>技能细节 / 与 AI 使用的正文一致</span><button id="close-reader" autofocus>关闭 ×</button></div>__REFERENCES__</dialog>
__LIBRARY__<script id="patch-data" type="application/json">__PATCH__</script><script>
const docs=[...document.querySelectorAll('.reference')],reader=document.getElementById('reader'),tabs=[...document.querySelectorAll('[role=tab]')];
function selectTab(tab){tabs.forEach(t=>{const active=t===tab;t.setAttribute('aria-selected',active);t.tabIndex=active?0:-1;document.getElementById(t.getAttribute('aria-controls')).hidden=!active;});}
tabs.forEach((tab,i)=>{tab.onclick=()=>selectTab(tab);tab.onkeydown=event=>{let next;if(event.key==='ArrowRight')next=(i+1)%tabs.length;if(event.key==='ArrowLeft')next=(i+tabs.length-1)%tabs.length;if(event.key==='Home')next=0;if(event.key==='End')next=tabs.length-1;if(next!==undefined){event.preventDefault();selectTab(tabs[next]);tabs[next].focus();}};});
function search(){const query=document.getElementById('search').value.toLowerCase();let count=0;document.querySelectorAll('.module-row').forEach(row=>{const linked=[...row.querySelectorAll('a[href^="#"]')].map(a=>document.getElementById(a.hash.slice(1)));row.hidden=!(row.textContent+' '+linked.map(d=>d?.textContent||'').join(' ')).toLowerCase().includes(query);if(!row.hidden)count++;});document.querySelectorAll('.capability-group').forEach(g=>g.hidden=![...g.querySelectorAll('.module-row')].some(r=>!r.hidden));document.getElementById('count').textContent=count+' 项';document.getElementById('no-result').hidden=count!==0;}
document.getElementById('search').oninput=search;
function reveal(){const element=document.getElementById(location.hash.slice(1));if(!element)return;if(element.classList.contains('reference')){docs.forEach(d=>{d.hidden=d!==element;d.open=d===element;});if(!reader.open)reader.showModal();reader.scrollTop=0;}else if(element.tagName==='DETAILS'){element.open=true;element.scrollIntoView();}}
window.addEventListener('hashchange',reveal);document.addEventListener('click',event=>{const link=event.target.closest('a[href^="#"]');if(link&&link.hash===location.hash)reveal();});document.getElementById('close-reader').onclick=()=>reader.close();
reader.addEventListener('click',event=>{if(event.target===reader){const r=reader.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right)reader.close();}});
const patch=JSON.parse(document.getElementById('patch-data').textContent);
function draw(){const target=document.getElementById('diff'),status=document.getElementById('diff-status');target.textContent='';document.getElementById('diff-controls').hidden=!patch.trim();if(!patch.trim()){status.textContent='没有文本差异。';return;}if(!window.Diff2Html){status.textContent='差异库未加载，请核对本地资源。';return;}try{const rule=name=>name==='SKILL.md'||/^(references|templates)\/.*\.md$/.test(name);const files=Diff2Html.parse(patch).filter(f=>document.getElementById('scope').value==='all'||rule(f.oldName)||rule(f.newName));target.innerHTML=Diff2Html.html(files,{drawFileList:true,matching:'lines',diffStyle:'char',outputFormat:document.getElementById('layout').value});status.textContent=files.length?'显示 '+files.length+' 个文件。文本变化不等于行为收益。':'技能规则与参考没有文本变化；可切换到全部源码。';}catch(error){status.textContent='无法解析差异：'+error.message;}}
document.getElementById('layout').onchange=draw;document.getElementById('scope').onchange=draw;document.getElementById('review').ontoggle=event=>{if(event.target.open)draw();};search();reveal();
</script></body></html>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument('--base', help='对比基线 Git 引用')
    parser.add_argument('--target', default='HEAD', help='对比目标 Git 引用')
    parser.add_argument('--review-output', type=Path, help='输出独立、离线的审阅 HTML')
    args = parser.parse_args()
    try:
        if args.base or args.review_output:
            if not args.base or not args.review_output or args.check:
                raise ValueError('--base 与 --review-output 必须同时使用，不能组合 --check')
            if args.review_output.resolve().is_relative_to(PACKAGE):
                raise ValueError('版本审阅资产须输出到源码仓库外')
            if args.review_output.exists():
                raise ValueError('拒绝覆盖已有版本审阅资产；请选择新输出路径')
            page, info = build_review(PACKAGE, args.base, args.target)
            with args.review_output.open('x', encoding='utf-8') as output:
                output.write(page)
            print(f'workflow_review: {info["base"]} -> {info["target"]}')
            return 0
        page, _ = build()
        if args.check:
            assets = PACKAGE/'docs/assets/diff2html'
            provenance = json.loads((assets/'provenance.json').read_text(encoding='utf-8'))
            for entry in provenance['files']:
                if hashlib.sha256((assets/entry['file']).read_bytes()).hexdigest() != entry['sha256']:
                    raise ValueError('diff2html 静态资源身份不匹配')
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
