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


def routing(sources: dict[str, str]) -> str:
    """Visualize authored conditions; never maintain a second routing catalog."""
    cards, covered = [], set()
    for line in sources['SKILL.md'].splitlines():
        if not line.startswith('|'):
            continue
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        if len(cells) != 2:
            continue
        targets = {target.split('#')[0] for _, target in LINK.findall(cells[1])
                   if target.split('#')[0] in sources and target.startswith('references/')}
        if targets:
            covered.update(targets)
            cards.append('<article class="route-card" role="listitem"><div class="condition">'
                         + inline(cells[0]) + '</div><span class="route-arrow" aria-hidden="true">↓</span>'
                         + '<div class="destination">' + document(cells[1], 'SKILL.md', sources) + '</div></article>')
    extra = []
    for path, contents in sources.items():
        if path.startswith('references/') and path not in covered:
            title = re.search(r'^# (.+)$', contents, re.M)[1]
            extra.append('<article class="route-card" role="listitem"><h3><a href="#'
                         + anchor(path) + '">' + html.escape(title) + '</a></h3>'
                         + document(opening(contents), path, sources) + '</article>')
    return ('<div class="route-grid" role="list">' + ''.join(cards) + '</div>'
            + ('<h3>其他按需参考</h3><div class="route-grid supplemental" role="list">'
               + ''.join(extra) + '</div>' if extra else ''))


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
    for relative, contents in sources.items():
        digest.update(relative.encode() + b"\0" + contents.encode() + b"\0")
        title = re.search(r"^# (.+)$", contents, re.M)
        if not title:
            raise ValueError(f"缺少标题：{relative}")
        cards.append(f'<details class="reference" id="{anchor(relative)}" data-path="{html.escape(relative)}">'
                     + "<summary>" + html.escape(title.group(1)) + "</summary>"
                     + f'<small>{html.escape(relative)}</small>' + document(contents, relative, sources) + "</details>")
    identity = digest.hexdigest()[:12]
    page = TEMPLATE.replace("__VERSION__", html.escape(version)).replace("__DIGEST__", identity)
    page = fill(page, {'__CHANGES__': render(changes), '__REFERENCES__': '\n'.join(cards),
                       '__INTRO__': document(opening(text), 'SKILL.md', sources),
                       '__ROUTING__': routing(sources), '__ROOT_LINK__': '#' + anchor('SKILL.md')})
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


TEMPLATE = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>workflow __VERSION__ · 人类阅读版</title>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; base-uri 'none'; form-action 'none'">
__CSS__
<style>
:root{color-scheme:light;--paper:#233b36;--muted:#526b64;--mint:#176b58;--line:#ccdcd4}
*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;background:#f6f7f2;color:var(--paper);font:16px/1.8 system-ui,-apple-system,sans-serif}
main{max-width:1180px;margin:auto;padding:40px 28px}header{padding-bottom:34px;border-bottom:1px solid var(--line)}
header .eyebrow{color:var(--mint);letter-spacing:.12em;font-size:13px;font-weight:700}h1{font-size:clamp(34px,5vw,52px);line-height:1.25;margin:18px 0}h2{font-size:28px;margin:36px 0 12px}h3{font-size:20px}
p{max-width:85ch}a{color:var(--mint);text-underline-offset:4px}a:hover{color:#094432}a:focus-visible,summary:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--mint);outline-offset:4px}
.rule{padding-left:16px;border-left:3px solid var(--mint)}code{font: .9em/1.7 ui-monospace,monospace;background:#e5eee7;padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}
pre{padding:18px;background:#edf2ec;border:1px solid var(--line);overflow:auto}pre code{padding:0;background:none;white-space:pre}
.table{overflow:auto}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:12px;border-bottom:1px solid var(--line)}th{color:var(--mint)}
details{border:1px solid var(--line);border-radius:10px;padding:18px 22px;margin:12px 0;background:#fff}summary{cursor:pointer;font-weight:700;font-size:19px}details[open]{background:#fff}
footer{margin-top:45px;padding-top:20px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}
input,button,select{font:inherit;padding:8px;border:1px solid var(--line);border-radius:6px}button,summary{cursor:pointer}.toolbar{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}.toolbar input[type=search]{flex:1;min-width:180px}.reference{scroll-margin-top:20px}small{color:var(--muted)}#navigation{margin:20px 0}.d2h-wrapper{background:white;color:#222;padding:12px;border-radius:8px}.d2h-code-line-ctn{white-space:pre-wrap;overflow-wrap:anywhere}.d2h-code-side-line{width:100%}.d2h-wrapper a{color:#12614e}.d2h-wrapper table{table-layout:auto}.d2h-wrapper td{padding:0}.d2h-wrapper th{color:#222}#diff:empty{display:none}
.hero{display:grid;grid-template-columns:1fr 1fr;gap:34px;align-items:center}.hero p{max-width:36em}.reading-map{margin:0}.reading-map svg{display:block;width:100%;height:auto}.reading-map figcaption{font-size:13px;text-align:center;color:var(--muted)}
.jump-links{display:flex;flex-wrap:wrap;gap:10px;margin:22px 0 0}.jump-links a{padding:5px 13px;border:1px solid var(--line);border-radius:24px;text-decoration:none;background:#fff}
.section-intro{color:var(--muted);margin-top:0}.route-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.route-card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:20px;display:flex;flex-direction:column;min-width:0}.condition{flex:1}.route-arrow{color:var(--mint);font-size:24px;line-height:1.5}.destination{border-top:1px solid var(--line);padding-top:10px}.destination p{margin:0}.destination a{font-weight:700}.supplemental .route-card{background:#eef3ec}.route-card h3{margin:0}.route-card p{font-size:15px}.reference>h2{font-size:24px}.reference>h3{border-bottom:1px solid var(--line);padding-bottom:6px}section,details{scroll-margin-top:20px}#changes{border-top:1px solid var(--line);margin-top:36px}#diff{overflow-x:auto}
@media(max-width:850px){.hero{grid-template-columns:1fr}.reading-map{max-width:520px}.route-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){main{padding:24px 16px}details{padding:14px}th,td{padding:9px}body{font-size:15px}.route-grid{grid-template-columns:1fr}.hero{gap:16px}}
</style></head><body><main data-source-digest="__DIGEST__">
<header id="overview"><p class="eyebrow">WORKFLOW · __VERSION__ · 人类阅读版</p>
<div class="hero"><div><h1>一个入口，<br>按需调用。</h1>__INTRO__<p><a href="__ROOT_LINK__">展开 AI 使用的精简入口 ↗</a></p></div>
<figure class="reading-map"><svg viewBox="0 0 520 250" role="img" aria-labelledby="map-title map-description"><title id="map-title">一份内容，两种阅读方式</title><desc id="map-description">AI 直接读取 Markdown 入口和参考，人类阅读由它们生成的图文页面，规则只维护一份。</desc>
<rect x="4" y="26" width="214" height="190" rx="18" fill="#e8f0e8" stroke="#ccdcd4"/><rect x="302" y="26" width="214" height="190" rx="18" fill="#fff" stroke="#ccdcd4"/>
<g fill="none" stroke="#176b58" stroke-width="2.5"><path d="M86 59h35l16 16v47H86z M121 59v16h16 M97 89l-6 6 6 6 M122 89l6 6-6 6 M112 86l-7 19"/><rect x="371" y="62" width="76" height="57" rx="5"/><path d="M371 76h76 M381 88h21v21h-21z M411 88h25 M411 98h25 M411 108h17 M230 120h59 M280 112l9 8-9 8"/></g>
<g fill="#233b36" text-anchor="middle" font-family="system-ui,sans-serif"><text x="111" y="153" font-size="23" font-weight="700">AI 读精简文本</text><text x="111" y="185" font-size="14">入口 + 按需参考</text><text x="409" y="153" font-size="23" font-weight="700">人读图文结构</text><text x="409" y="185" font-size="14">总览 + 导航 + 版本对比</text><text x="260" y="103" font-size="12" fill="#176b58">生成</text></g></svg><figcaption>内容只维护一份，图文页随发布更新。</figcaption></figure></div>
<nav class="jump-links" aria-label="阅读导航"><a href="#routing">按情况找参考</a><a href="#documents">查阅全文</a><a href="#changes">本版变化</a><a href="#review">版本对比</a><a href="../README.md">安装与使用</a></nav></header>
<section id="routing"><h2>遇到什么情况，读取哪份参考</h2><p class="section-intro">按当前缺口定位，点击参考名称展开原文。箭头表示条件与参考的对应关系，不是依次执行的步骤。</p>__ROUTING__</section>
<section id="documents" aria-label="按需展开规则"><h2>查阅完整规则</h2><p class="section-intro">标题、正文和链接来自 AI 使用的同一份 Markdown。搜索后可只展开相关内容。</p><div class="toolbar"><input id="search" type="search" aria-label="搜索规则全文" placeholder="搜索名称、路径或正文"><button id="expand">展开结果</button><button id="collapse">全部折叠</button><span id="count"></span></div>__REFERENCES__</section>
<section id="changes"><h2>本版变化</h2>__CHANGES__</section>
<details id="review"><summary>查看版本高亮对比</summary><p>上方说明来自目标版本的 CHANGELOG；跨版本的完整变化以这里的差异为准。</p><div>__REVIEW_INFO__</div><div class="toolbar" id="diff-controls"><label>内容 <select id="scope"><option value="rules">技能规则与参考</option><option value="all">全部源码（含维护工具）</option></select></label><label>布局 <select id="layout"><option value="side-by-side">并排</option><option value="line-by-line">逐行</option></select></label></div><p id="diff-status" role="status"></p><div id="diff"></div></details>
<footer>由 CHANGELOG、SKILL.md、其参考与工作模板生成。页面不定义额外规则。source sha256 __DIGEST__</footer>
</main>__LIBRARY__<script id="patch-data" type="application/json">__PATCH__</script><script>
const docs=[...document.querySelectorAll('.reference')];
function search(){const query=document.getElementById('search').value.toLowerCase();docs.forEach(d=>d.hidden=!d.textContent.toLowerCase().includes(query));document.getElementById('count').textContent=docs.filter(d=>!d.hidden).length+' / '+docs.length;}
document.getElementById('search').oninput=search;document.getElementById('expand').onclick=()=>docs.filter(d=>!d.hidden).forEach(d=>d.open=true);document.getElementById('collapse').onclick=()=>docs.forEach(d=>d.open=false);
function reveal(){const element=document.getElementById(location.hash.slice(1));if(element&&element.tagName==='DETAILS'){if(element.classList.contains('reference')){document.getElementById('search').value='';search();}element.open=true;element.scrollIntoView();}}
window.addEventListener('hashchange',reveal);
document.addEventListener('click',event=>{const link=event.target.closest('a[href^="#"]');if(link&&link.hash===location.hash)reveal();});
const patch=JSON.parse(document.getElementById('patch-data').textContent);
function draw(){
 const target=document.getElementById('diff'),status=document.getElementById('diff-status');target.textContent='';
 document.getElementById('diff-controls').hidden=!patch.trim();
 if(!patch.trim()){status.textContent='没有文本差异。';return;}
 if(!window.Diff2Html){status.textContent='差异库未加载，请核对本地资源。';return;}
 try{
  const rule=name=>name==='SKILL.md'||/^(references|templates)\\/.*\\.md$/.test(name);
  const files=Diff2Html.parse(patch).filter(f=>document.getElementById('scope').value==='all'||rule(f.oldName)||rule(f.newName));
  target.innerHTML=Diff2Html.html(files,{drawFileList:true,matching:'lines',diffStyle:'char',outputFormat:document.getElementById('layout').value});
  status.textContent=files.length?'显示 '+files.length+' 个文件。文本变化不等于行为收益；验证结果见本版说明。':'技能规则与参考没有文本变化；可切换到全部源码查看维护改动。';
 }catch(error){status.textContent='无法解析差异：'+error.message;}
}
document.getElementById('layout').onchange=draw;document.getElementById('scope').onchange=draw;
document.getElementById('review').ontoggle=event=>{if(event.target.open)draw();};search();reveal();
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
