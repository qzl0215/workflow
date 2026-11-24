#!/usr/bin/env python3
"""从技能真源生成可展开说明页，不维护第二套政策。"""
from __future__ import annotations

import argparse
import ast
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
            # inline() resolves from the package root, so re-root links that are not inlined sources.
            return f'[{label}]({path})'
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
                     + '<div class="reference-context"><span class="label">何时读</span>' + context + '</div>'
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
    manifest = PACKAGE/'workflow-package.json'
    page = fill(page, {'__FILEMAP__': file_map(lambda p: (PACKAGE/p).read_text(encoding='utf-8'), manifest.read_text(encoding='utf-8'))
                       if manifest.is_file() else ''})
    return fill(page, {'__REVIEW_INFO__': '本页不含源码差异。下载<a href="https://github.com/qzl0215/workflow/releases/latest">正式 Release</a> 里的 workflow-review.html 查看。',
                       '__PATCH__': 'null', '__CSS__': '', '__LIBRARY__': ''}), identity


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(['git', *args], cwd=repo, capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise ValueError(result.stderr.strip() or 'Git 读取失败')
    return result.stdout


def previous_release(repo: Path, target: str) -> str:
    """Newest CHANGELOG version of the target that is already tagged on another commit."""
    after = git(repo, 'rev-parse', '--verify', '--end-of-options', target+'^{commit}').strip()
    for version in re.findall(r'^## \[(\d+\.\d+\.\d+)\]', git(repo, 'show', f'{after}:CHANGELOG.md'), re.M):
        try:
            tagged = git(repo, 'rev-parse', '--verify', '--quiet', f'refs/tags/{version}^{{commit}}').strip()
        except ValueError:
            continue
        if tagged != after:
            return version
    raise ValueError('CHANGELOG 里没有可作基线的已发布版本，请用 --base 指定')


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
    page = fill(page, {'__FILEMAP__': file_map(lambda p: git(repo, 'show', f'{after}:{p}'), git(repo, 'show', f'{after}:workflow-package.json'))
                       if 'workflow-package.json' in names else ''})
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


FOLDERS = [('references/', '按需参考，事件发生才读'), ('templates/', '模板'), ('scripts/', '随包脚本'),
           ('dev/', '开发与发布脚本，不随包'), ('docs/', '人读的生成页'), ('evals/', '评测记录'), ('tests/', '回归测试'), ('', '仓库说明')]
NOT_SOURCE = ('CHANGELOG.md', 'workflow-package.json', 'docs/', 'evals/4', 'evals/5', 'evals/cases.json')


def references_between(texts: dict[str, str]) -> list[tuple[str, str]]:
    """A file points at another when its text names the path, a relative link, or a unique basename."""
    names = {}
    for path in texts:
        names[posixpath.basename(path)] = names.get(posixpath.basename(path), 0) + 1
    edges = []
    for source, body in texts.items():
        if source.startswith(NOT_SOURCE) or not body:
            continue
        for target in texts:
            if target == source or target.startswith('docs/assets/') or target in {'.gitignore', 'LICENSE'}:
                continue
            if source.endswith('.py') and (not (target.endswith('.py') or target in {'SKILL.md', 'workflow-package.json', 'templates/work.md'})
                                           or (target.startswith('tests/') and not source.startswith('tests/'))):
                continue
            base = posixpath.basename(target)
            if (('/' in target and target in body) or f'({posixpath.relpath(target, posixpath.dirname(source) or ".")})' in body
                    or (names[base] == 1 and base in body)):
                edges.append((source, target))
    return edges


def external_skills(texts: dict[str, str]) -> list[str]:
    found = []
    for path, body in texts.items():
        if path == 'SKILL.md' or path.startswith('references/'):
            for line in body.splitlines():
                if '装有' in line:
                    found += [n for n in re.findall(r'`([a-z][a-z0-9-]+)`', line) if n not in found]
    return found


def purpose(path: str, body: str) -> str:
    if path.endswith('.md') and body:
        return opening(body)
    if path.endswith('.py'):
        try:
            doc = ast.get_docstring(ast.parse(body)) or ''
        except SyntaxError:
            doc = ''
        return doc.strip().splitlines()[0] if doc.strip() else ''
    return ''


def file_map(read, manifest_text: str) -> str:
    manifest = json.loads(manifest_text)
    runtime = set(manifest['runtime']['files'])
    files = sorted(runtime | set(manifest['source_only']) | {'workflow-package.json'})
    texts = {}
    for path in files:
        try:
            texts[path] = '' if path.startswith('docs/') else read(path)
        except (OSError, UnicodeDecodeError, subprocess.CalledProcessError):
            texts[path] = ''
    edges = references_between(texts)
    outs = {f: [g for s, g in edges if s == f] for f in files}
    ins = {f: [s for s, g in edges if g == f] for f in files}
    when, order = {}, []
    for condition, target in table_rows(section(texts['SKILL.md'], '按需读取'), 2):
        for _, path in LINK.findall(target):
            when[path] = condition
            order.append(path)
    externals = external_skills(texts)
    esc = html.escape

    def title(path: str) -> str:
        heading = re.search(r'^# (.+)$', texts.get(path, ''), re.M)
        return heading[1] if heading and path.endswith('.md') else posixpath.basename(path)

    def chip(path: str) -> str:
        return f'<button class="chip" data-go="{esc(path)}">{esc(path)}</button>'

    tree = ''
    for path in ('SKILL.md',):
        tree += f'<button class="file" data-go="SKILL.md" data-rt="1"><i></i>SKILL.md</button>'
    for folder, note in FOLDERS:
        members = [f for f in files if (f.startswith(folder) if folder else '/' not in f) and f != 'SKILL.md']
        if not members:
            continue
        tree += f'<div class="folder"><b>{esc(folder or "根目录")}</b><small>{esc(note)}</small></div>'
        for f in sorted(members, key=lambda f: (f not in runtime, f)):
            name = posixpath.basename(f) if folder else f
            if f.startswith('docs/assets/'):
                name = 'assets/…/' + name
            tree += f'<button class="file sub" data-go="{esc(f)}" data-rt="{int(f in runtime)}"><i></i>{esc(name)}</button>'

    panels = ''
    for f in files:
        body = texts[f]
        badge = '随包安装' if f in runtime else '仅源码'
        lines = f' · {len(body.splitlines())} 行' if body else ''
        lead = (f'<p class="map-when"><span class="label">何时读</span>{inline(when[f])}</p>' if f in when
                else f'<p class="map-lead">{inline(purpose(f, body))}</p>' if purpose(f, body) else '')
        main_in = [g for g in ins[f] if not (g.endswith('.py') and not f.endswith('.py'))]
        tool_in = [g for g in ins[f] if g not in main_in]
        more = (f'<details class="map-more"><summary>另有 {len(tool_in)} 个脚本和测试提到它</summary>'
                + ''.join(chip(g) for g in tool_in) + '</details>') if tool_in else ''
        named = ''.join(f'<span class="chip ext">{esc(n)} · 外部技能</span>' for n in externals
                        if f'`{n}`' in body and ('装有' in body)) if f.startswith('references/') else ''
        read_link = (f'<a class="map-read" href="#{anchor(f)}">阅读全文</a>'
                     if f == 'SKILL.md' or (f.startswith(('references/', 'templates/')) and f.endswith('.md')) else '')
        panels += (f'<section class="map-panel" data-path="{esc(f)}" data-out="{esc(json.dumps(outs[f]))}" data-in="{esc(json.dumps(main_in))}" hidden>'
                   f'<span class="label">{esc(f)} · {badge}{lines}</span><h3>{esc(title(f))}</h3>{lead}'
                   f'<div class="map-rels"><div><span class="label">引用它的文件</span>'
                   + (''.join(chip(g) for g in main_in) or ('' if more else '<span class="none">没有</span>')) + more
                   + '</div><div><span class="label">它引用的文件</span>'
                   + (''.join(chip(g) for g in outs[f]) + named or '<span class="none">没有</span>')
                   + f'</div></div>{read_link}</section>')

    # Load diagram: description → SKILL.md → references in routing order → what they name.
    refs = [p for p in order if p in texts]
    leaves = []
    for ref in ['SKILL.md', *refs]:
        for g in outs[ref]:
            if g in runtime and not g.startswith('references/') and g != 'SKILL.md' and g not in leaves:
                leaves.append(g)
    leaves += [f'@{n}' for n in externals]
    rows = max(len(refs), len(leaves), 1)
    height, row_y = 70 + rows * 66, lambda i: 60 + i * 66
    mid = 60 + (rows * 66 - 10) // 2

    def node(x, y, w, path, first, second, cls=''):
        go = f' data-go="{esc(path)}" tabindex="0" role="button"' if path else ''
        return (f'<g class="n {cls}"{go}><rect x="{x}" y="{y}" width="{w}" height="56" rx="5"/>'
                f'<text class="t" x="{x+12}" y="{y+24}">{esc(first)}</text><text class="s" x="{x+12}" y="{y+43}">{esc(second)}</text></g>')
    svg = ''.join(f'<text class="col" x="{x}" y="30">{label}</text>' for x, label in
                  [(10, '常驻上下文'), (200, '命中后读一次'), (400, '事件发生才读'), (760, '被点名才用')])
    svg += f'<path class="e" d="M160 {mid+28} H198"/>'
    for i, ref in enumerate(refs):
        svg += f'<path class="e" d="M350 {mid+28} C 375 {mid+28}, 375 {row_y(i)+28}, 398 {row_y(i)+28}"/>'
    for j, leaf in enumerate(leaves):
        sources = ([r for r in refs if leaf in outs[r]] if not leaf.startswith('@')
                   else [r for r in refs if f'`{leaf[1:]}`' in texts[r]])
        dashed = ' d' if leaf.startswith('@') or leaf.endswith('.py') else ''
        for r in sources:
            i = refs.index(r)
            svg += f'<path class="e{dashed}" d="M690 {row_y(i)+28} C 725 {row_y(i)+28}, 725 {row_y(j)+28}, 758 {row_y(j)+28}"/>'
        if 'SKILL.md' in ins.get(leaf, []) and not sources:
            svg += f'<path class="e" d="M275 {mid} V 44 H 880 V {row_y(j)}"/>'
    svg += node(10, mid, 150, None, 'description', '技能的触发描述', 'desc')
    svg += node(200, mid, 150, 'SKILL.md', 'SKILL.md', '入口：判断、推进、路由', 'hub')
    for i, ref in enumerate(refs):
        svg += node(400, row_y(i), 290, ref, title(ref), posixpath.basename(ref))
    for j, leaf in enumerate(leaves):
        if leaf.startswith('@'):
            svg += node(760, row_y(j), 240, None, leaf[1:], '外部技能 · 本机装有才调用', 'leaf ext')
        else:
            svg += node(760, row_y(j), 240, leaf, posixpath.basename(leaf), dict(FOLDERS).get(posixpath.dirname(leaf) + '/', ''), 'leaf')
    figure = (f'<div class="map-figure"><svg viewBox="0 0 1010 {height}" role="img" aria-label="加载关系：触发描述常驻，命中后读 SKILL.md，参考在对应事件发生时才读，模板、脚本和外部技能被点名才用。">'
              f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="currentColor"/></marker></defs>{svg}</svg></div>'
              '<p class="figure-note"><span>实线：读文档。虚线：运行脚本或调用外部技能。点方块看详情。</span></p>')
    return (f'<section id="files" class="files"><h2>文件与引用</h2>'
            f'<p class="map-sum">共 {len(files)} 个文件，{len(runtime)} 个随包安装（实心点），其余只在源码里。引用关系从文件正文里的链接推出。</p>{figure}'
            f'<div class="map-explorer"><nav class="map-tree" aria-label="仓库目录">{tree}</nav><div class="map-detail">{panels}</div></div></section>')


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>workflow __VERSION__ · 工作地图</title>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; base-uri 'none'; form-action 'none'">
__CSS__
<style>
:root{color-scheme:light;--ink:#182c30;--muted:#56666a;--accent:#086a70;--line:#d4dcd9;--paper:#f7f8f5;--soft:#eaf2ef}
*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;color:var(--ink);background:var(--paper);font:16px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
a{color:var(--accent);text-underline-offset:4px}button,input,select{font:inherit;color:inherit}button,a,summary,input,select{touch-action:manipulation}button,summary{cursor:pointer}:focus-visible{outline:3px solid #d0872d;outline-offset:4px}button{background:transparent}p{margin:12px 0}h1,h2,h3{line-height:1.35}h1{font-size:46px;letter-spacing:-.035em;margin:18px 0}h2{font-size:27px;margin:0 0 14px}h3{font-size:19px}code{font:.9em/1.6 ui-monospace,monospace;overflow-wrap:anywhere;background:var(--soft);padding:2px 5px;border-radius:3px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--paper);padding:16px;border:1px solid var(--line);font:13px/1.7 ui-monospace,monospace;overflow:auto}.table{overflow:auto}table{border-collapse:collapse;width:100%}th,td{padding:12px;text-align:left;border-bottom:1px solid var(--line)}td{vertical-align:top}th{color:var(--accent)}
.topbar{max-width:1200px;margin:auto;display:flex;align-items:center;justify-content:space-between;padding:22px 32px;border-bottom:1px solid var(--line);font-size:13px}.brand{font-weight:800;letter-spacing:.13em}.topbar nav{display:flex;gap:22px}.topbar nav a{text-decoration:none;color:var(--muted)}main{max-width:1200px;margin:auto;padding:40px 32px 70px}.hero{margin-bottom:32px}.label{font:700 11px/1.6 ui-monospace,-apple-system,sans-serif;letter-spacing:.08em;color:var(--accent);text-transform:uppercase}.hero p{max-width:40em;color:var(--muted)}.hero p a{margin-left:8px}
.flow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-bottom:30px}.flow-node{border:1px solid var(--line);padding:22px 18px;text-align:left;background:var(--paper);min-width:0;min-height:133px;border-radius:3px}.flow-node[aria-selected=true]{background:var(--accent);border-color:var(--accent);color:white}.flow-node strong{display:block;font-size:23px;margin:0 0 6px}.flow-node span{font-size:13px;opacity:.85}.figure-note{color:var(--muted);font-size:12px;margin:10px 0 30px}
.workbench{display:grid;grid-template-columns:225px minmax(0,1fr);gap:36px;padding:28px 0 40px;border-top:1px solid var(--line)}.panel-intro h2{font-size:24px;margin-top:8px}.panel-intro p{font-size:14px;color:var(--muted)}.panel-intro a{font-size:13px}.decision{border-bottom:1px solid var(--line);background:white}.decision summary{display:flex;align-items:center;gap:18px;list-style:none;padding:17px 20px;font-size:15px}.decision summary::-webkit-details-marker{display:none}.decision summary:after{content:'+';margin-left:auto;font-size:22px;color:var(--accent)}.decision[open] summary:after{content:'−'}.branch-number{font:13px ui-monospace,monospace;color:var(--accent);flex:none}.branch-body{padding:0 22px 18px 57px;font-size:14px}.branch-body .label{display:block}.action-path{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:6px 0 12px}.action-path>span:not(.arrow){border:1px solid var(--line);padding:5px 10px;background:var(--soft)}.arrow{color:var(--accent);font-size:20px}.branch-body p{margin-bottom:0}.capability-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px 34px}.capability-group h3{font-size:13px;letter-spacing:.06em;color:var(--muted);border-bottom:2px solid var(--accent);padding-bottom:8px;margin:0}.module-row{border-bottom:1px solid var(--line);padding:10px 0}.module-row p{margin:0;font-size:15px}.module-row a{font-weight:650;text-decoration:none}.module-condition{display:block;color:var(--muted);font-size:12px;line-height:1.6;margin-top:3px}.outcome{display:grid;grid-template-columns:minmax(0,1fr) 22px minmax(0,1.5fr);gap:14px;align-items:center;padding:17px 0;border-bottom:1px solid var(--line);font-size:14px}.outcome>div{font-weight:650}.outcome p{margin:0}.outcome:last-child>div{color:var(--accent)}.searchline{display:flex;gap:12px;margin-bottom:18px;align-items:center}.searchline input{width:100%;border:0;border-bottom:1px solid var(--line);background:transparent;padding:10px 0;min-width:0}.searchline span{font-size:12px;color:var(--muted);white-space:nowrap}.no-result{font-size:14px;color:var(--muted)}
#changes{border-top:1px solid var(--line);padding-top:32px;margin-top:10px}.change-layout{max-width:74ch;font-size:15px}.change-layout .rule{padding-left:16px;border-left:2px solid var(--accent);margin:14px 0}.review{margin-top:24px;border:1px solid var(--line);padding:18px 22px;background:white}.review>summary{font-size:16px;font-weight:650}.review small{color:var(--muted)}.toolbar{display:flex;gap:16px;flex-wrap:wrap;margin:20px 0}.toolbar select{background:var(--paper);padding:6px;border:1px solid var(--line)}#diff{overflow-x:auto}.d2h-wrapper{background:white;color:#222}.d2h-code-line-ctn{white-space:pre-wrap;overflow-wrap:anywhere}.d2h-code-side-line{width:100%}.d2h-wrapper td{padding:0}.d2h-wrapper a{color:var(--accent)}#diff-status{font-size:13px;color:var(--muted)}footer{font-size:12px;color:var(--muted);margin-top:35px}
.reader{position:fixed;inset:0 0 0 auto;margin:0;border:0;border-left:1px solid var(--line);width:min(720px,100vw);max-width:100vw;height:100dvh;max-height:100dvh;background:#fff;color:var(--ink);padding:0}.reader::backdrop{background:#12292e70}.reader-bar{position:sticky;top:0;z-index:2;background:#fff;display:flex;justify-content:space-between;align-items:center;padding:16px 28px;border-bottom:1px solid var(--line)}.reader-bar span{font-size:12px;color:var(--muted)}.reader-bar button{border:1px solid var(--line);padding:5px 14px;border-radius:3px}.reference{padding:26px 32px 50px;max-width:100%}.reference>summary{list-style:none;font-size:30px;font-weight:700;pointer-events:none}.reference>summary::-webkit-details-marker{display:none}.reference-context{border-left:3px solid var(--accent);padding:10px 16px;background:var(--soft);margin:20px 0;font-size:14px}.reference-context p{margin:4px 0}.reference-context:has(>.label:only-child){display:none}.raw-source{margin:20px 0;font-size:13px;color:var(--muted)}.reading-body{max-width:40em;line-height:1.95;font-size:16px}.reading-body>h2:first-child{display:none}.reading-body h3{font-size:21px;border-top:1px solid var(--line);padding-top:25px;margin-top:30px}.reading-body p{margin:18px 0}.reading-body .rule{padding:8px 0 8px 15px;border-left:2px solid var(--line);margin:12px 0}.reading-body table{font-size:14px}
@media(max-width:900px){.workbench{grid-template-columns:1fr;gap:18px}.panel-intro p{margin:6px 0}.flow-node strong{font-size:19px}.flow-node{padding:18px 12px}}
@media(max-width:600px){main{padding:25px 18px 45px}.topbar{padding:16px 18px}.topbar nav{gap:12px;font-size:12px}h1{font-size:34px}.hero{margin-bottom:25px}.figure-note{font-size:11px}.capability-grid{grid-template-columns:1fr}.decision summary{padding:14px 10px;gap:12px}.branch-body{padding:0 15px 15px 35px}.reference{padding:22px 20px}.reader-bar{padding:14px 20px}.outcome{gap:8px;font-size:13px}.reading-body{font-size:15px}.toolbar{font-size:13px}.review{padding:15px}.topbar .brand{letter-spacing:.05em}}
@media(max-width:600px){.flow{grid-template-columns:1fr;gap:8px}.flow-node{min-height:0;padding:13px 16px;display:flex;justify-content:space-between;align-items:center;gap:10px}.flow-node strong{margin:0;font-size:18px}.flow-node span{text-align:right;font-size:12px}}
.files{border-top:1px solid var(--line);padding-top:32px;margin:10px 0 30px}.map-sum{color:var(--muted);font-size:14px}.map-figure{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:4px;padding:8px}.map-figure svg{display:block;min-width:820px;width:100%;height:auto;color:var(--ink)}.map-figure .col{font:700 11px ui-monospace,monospace;fill:var(--accent);letter-spacing:.08em}.map-figure .n rect{fill:var(--paper);stroke:var(--line)}.map-figure .n[data-go]{cursor:pointer}.map-figure .n[data-go]:hover rect,.map-figure .n.on rect{stroke:var(--accent);stroke-width:2}.map-figure .hub rect{fill:var(--soft);stroke:var(--accent)}.map-figure .ext rect{stroke-dasharray:4 3}.map-figure .t{font:600 13px -apple-system,"PingFang SC",sans-serif;fill:currentColor}.map-figure .s{font:11px -apple-system,"PingFang SC",sans-serif;fill:var(--muted)}.map-figure .e{fill:none;stroke:var(--accent);stroke-width:1.3;marker-end:url(#ah);color:var(--accent);opacity:.75}.map-figure .e.d{stroke-dasharray:5 4}
.map-explorer{display:grid;grid-template-columns:250px minmax(0,1fr);gap:28px;margin-top:22px;align-items:start}.map-tree{position:sticky;top:12px;max-height:calc(100dvh - 24px);overflow:auto;border-right:1px solid var(--line);padding-right:12px;font-size:13px}.map-tree .folder{margin:14px 0 4px;display:flex;flex-direction:column}.map-tree .folder small{color:var(--muted);font-size:11px}.map-tree .file{display:flex;align-items:center;gap:8px;width:100%;text-align:left;border:0;padding:4px 6px;border-radius:3px;font:12px/1.5 ui-monospace,monospace;overflow-wrap:anywhere}.map-tree .file.sub{padding-left:14px}.map-tree .file i{flex:none;width:8px;height:8px;border-radius:50%;border:1.5px solid var(--accent)}.map-tree .file[data-rt="1"] i{background:var(--accent)}.map-tree .file:hover{background:var(--soft)}.map-tree .file.on{background:var(--accent);color:#fff}.map-tree .file.on i{border-color:#fff}.map-tree .file.in:after{content:'引用它';margin-left:auto;font:10px sans-serif;color:var(--accent)}.map-tree .file.out:after{content:'被它引用';margin-left:auto;font:10px sans-serif;color:#b0642a}
.map-panel h3{font-size:24px;margin:6px 0 10px}.map-when,.map-lead{border-left:3px solid var(--accent);background:var(--soft);padding:10px 14px;font-size:14px}.map-when .label{display:block}.map-rels{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:16px 0}.map-rels .label{display:block;margin-bottom:6px}.chip{display:inline-block;border:1px solid var(--line);background:#fff;border-radius:3px;padding:2px 8px;margin:0 6px 6px 0;font:12px/1.6 ui-monospace,monospace}.chip:hover{border-color:var(--accent)}.chip.ext{border-style:dashed;color:var(--muted)}.none{color:var(--muted);font-size:13px}.map-more{font-size:12px;color:var(--muted);margin-top:4px}.map-read{font-size:14px;font-weight:650}
@media(max-width:760px){.map-explorer{grid-template-columns:1fr}.map-tree{position:static;max-height:280px;border-right:0;border-bottom:1px solid var(--line);padding:0 0 10px}.map-rels{grid-template-columns:1fr}}
</style></head><body>
<div class="topbar"><a class="brand" href="#overview">WORKFLOW / __VERSION__</a><nav aria-label="页面导航"><a href="#files">文件与引用</a><a href="#changes">本版变化</a><a href="#review">版本对比</a><a href="../README.md">使用说明</a></nav></div>
<main data-source-digest="__DIGEST__">
<header id="overview" class="hero"><h1>workflow 怎样处理一个请求</h1><p>下面三项对应 SKILL.md 里的三段规则，点选查看。每份参考的读取条件和全文也能在本页打开。<a href="__ROOT_LINK__">SKILL.md 原文</a></p></header>
<div class="flow" role="tablist" aria-label="选择要查看的规则">
<button class="flow-node" id="tab-request" role="tab" aria-selected="true" aria-controls="panel-request" tabindex="0"><strong>本轮做到哪</strong><span>回答、直接做，还是先确认</span></button>
<button class="flow-node" id="tab-capabilities" role="tab" aria-selected="false" aria-controls="panel-capabilities" tabindex="-1"><strong>读哪份参考</strong><span>缺什么读什么</span></button>
<button class="flow-node" id="tab-outcomes" role="tab" aria-selected="false" aria-controls="panel-outcomes" tabindex="-1"><strong>何时继续或结束</strong><span>继续 · 恢复 · 交接 · 结束</span></button></div>
<section class="workbench" role="tabpanel" id="panel-request" aria-labelledby="tab-request"><div class="panel-intro"><h2>本轮做到哪</h2><p>找到符合当前情况的一行，展开看本轮动作和停在哪里。</p></div><div>__DECISIONS__</div></section>
<section class="workbench" role="tabpanel" id="panel-capabilities" aria-labelledby="tab-capabilities" hidden><div class="panel-intro"><h2>读哪份参考</h2><p>缺什么读什么，可以只读一份，也可以不读。点名称看全文。</p></div><div><div class="searchline"><input id="search" type="search" placeholder="搜索参考名称或正文" aria-label="搜索参考名称或正文"><span id="count" role="status"></span></div><div id="routing" class="capability-grid">__ROUTING__</div><p class="no-result" id="no-result" hidden>没有匹配的参考，换个词试试。</p></div></section>
<section class="workbench" role="tabpanel" id="panel-outcomes" aria-labelledby="tab-outcomes" hidden><div class="panel-intro"><h2>何时继续或结束</h2><p>按当前状态找下一步。目标、交付和验收都成立才结束。</p></div><div>__OUTCOMES__</div></section>
__FILEMAP__
<section id="changes"><h2>本版变化</h2><div class="change-layout">__CHANGES__</div></section>
<details id="review" class="review"><summary>版本对比</summary><p>上方“本版变化”取自 CHANGELOG。</p><div>__REVIEW_INFO__</div><div class="toolbar" id="diff-controls"><label>内容 <select id="scope"><option value="rules">技能规则与参考</option><option value="all">全部源码（含维护工具）</option></select></label><label>布局 <select id="layout"><option value="side-by-side">并排</option><option value="line-by-line">逐行</option></select></label></div><p id="diff-status" role="status"></p><div id="diff"></div></details>
<footer>本页由技能源码生成 · source sha256 __DIGEST__</footer></main>
<dialog class="reader" id="reader" aria-label="技能文件正文"><div class="reader-bar"><span>技能文件正文</span><button id="close-reader" autofocus>关闭 ×</button></div>__REFERENCES__</dialog>
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
function draw(){const target=document.getElementById('diff'),status=document.getElementById('diff-status');target.textContent='';document.getElementById('diff-controls').hidden=!patch?.trim();if(patch===null)return;if(!patch.trim()){status.textContent='没有文本差异。';return;}if(!window.Diff2Html){status.textContent='差异显示不了：页面里的 diff2html 没有加载。请重新生成审阅页，或下载正式 Release 的 workflow-review.html。';return;}try{const rule=name=>name==='SKILL.md'||/^(references|templates)\/.*\.md$/.test(name);const files=Diff2Html.parse(patch).filter(f=>document.getElementById('scope').value==='all'||rule(f.oldName)||rule(f.newName));target.innerHTML=Diff2Html.html(files,{drawFileList:true,matching:'lines',diffStyle:'char',maxLineSizeInBlockForComparison:1000,outputFormat:document.getElementById('layout').value});status.textContent=files.length?'显示 '+files.length+' 个文件。文本变化不等于行为收益。':'技能规则与参考没有文本变化；可切换到全部源码。';}catch(error){status.textContent='无法解析差异：'+error.message;}}
const mapPanels=[...document.querySelectorAll('.map-panel')],mapFiles=[...document.querySelectorAll('.map-tree .file')],mapNodes=[...document.querySelectorAll('.map-figure [data-go]')];
function pick(path,scroll){const panel=mapPanels.find(p=>p.dataset.path===path);if(!panel)return;mapPanels.forEach(p=>p.hidden=p!==panel);const out=JSON.parse(panel.dataset.out),inn=JSON.parse(panel.dataset.in);mapFiles.forEach(f=>{const g=f.dataset.go;f.classList.toggle('on',g===path);f.classList.toggle('out',out.includes(g));f.classList.toggle('in',inn.includes(g));});mapNodes.forEach(n=>n.classList.toggle('on',n.dataset.go===path));if(scroll)panel.scrollIntoView({block:'start'});}
document.addEventListener('click',event=>{const go=event.target.closest('[data-go]');if(go)pick(go.dataset.go,!go.closest('.map-tree'));});mapNodes.forEach(n=>n.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();pick(n.dataset.go,true);}}));pick('SKILL.md',false);
document.getElementById('layout').onchange=draw;document.getElementById('scope').onchange=draw;document.getElementById('review').ontoggle=event=>{if(event.target.open)draw();};search();reveal();
</script></body></html>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument('--base', help='对比基线 Git 引用；省略时取 CHANGELOG 里上一个已发布版本')
    parser.add_argument('--target', default='HEAD', help='对比目标 Git 引用')
    parser.add_argument('--review-output', type=Path, help='输出独立、离线的审阅 HTML')
    args = parser.parse_args()
    try:
        if args.base or args.review_output:
            if not args.review_output or args.check:
                raise ValueError('对比需要 --review-output，不能组合 --check')
            if args.review_output.resolve().is_relative_to(PACKAGE):
                raise ValueError('版本审阅资产须输出到源码仓库外')
            if args.review_output.exists():
                raise ValueError('拒绝覆盖已有版本审阅资产；请选择新输出路径')
            page, info = build_review(PACKAGE, args.base or previous_release(PACKAGE, args.target), args.target)
            with args.review_output.open('x', encoding='utf-8') as output:
                output.write(page)
            print(f'workflow_review: {info["base"]} -> {info["target"]}')
            if git(PACKAGE, 'status', '--porcelain').strip():
                print('提示：工作区有未提交改动，不在这次对比里。', file=sys.stderr)
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
