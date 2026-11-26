#!/usr/bin/env python3
"""页面交付前的首屏检查：截首屏、量首屏、出一张扫一眼图，给出冷读要用的提示词。

人扫一眼只看得进大字、粗字、颜色和形状，不读小字段落；AI 看截图会逐字读完。
所以冷读用的是扫一眼图：小于 16 像素的细字被抹掉，只剩人五秒内真正看得到的东西。
只读页面，不改它。冷读本身由调用者派一个子代理完成。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SIZES = (("desktop", 1440, 900), ("phone", 390, 844))
CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)
CHROME_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge")
MARK = "__workflow_page_check__"
MEASURE = r"""
(() => {
  const vh = window.innerHeight, vw = window.innerWidth;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let first = 0, biggest = 0, biggestText = '', small = 0; const prose = [], nums = {};
  while (walker.nextNode()) {
    const n = walker.currentNode, t = n.textContent.replace(/\s+/g, '');
    const el = n.parentElement;
    if (!t || !el || ['SCRIPT', 'STYLE', 'TITLE'].includes(el.tagName)) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = document.createRange(); r.selectNodeContents(n);
    const b = r.getBoundingClientRect();
    if (!b.width || !b.height || b.top >= vh || b.bottom <= 0 || b.left >= vw) continue;
    first += t.length;
    const size = parseFloat(cs.fontSize);
    if (size < 16 && parseInt(cs.fontWeight, 10) < 600) small += t.length;
    if (t.length >= 30) prose.push(t.slice(0, 18) + '…（' + t.length + ' 字）');
    for (const m of n.textContent.matchAll(/\d[\d,.]*\s*[亿万]/g)) { const k = m[0].replace(/\s/g, ''); nums[k] = (nums[k] || 0) + 1; }
    if (size > biggest) { biggest = size; biggestText = t.slice(0, 24); }
  }
  const seen = el => { const b = el.getBoundingClientRect(); return b.width > 0 && b.height > 0 && b.top < vh && b.bottom > 0; };
  const controls = [...document.querySelectorAll('button,a[href],input,select,textarea,summary,[role=button],[role=tab],[role=slider]')].filter(seen).length;
  const root = document.documentElement;
  return { width: vw, height: vh, screens: +(root.scrollHeight / vh).toFixed(1), firstScreenChars: first,
           firstScreenControls: controls, biggestText, overflowX: root.scrollWidth > vw + 1,
           smallChars: small, prose, repeated: Object.entries(nums).filter(([, v]) => v > 1).map(([k, v]) => k + ' ×' + v) };
})()
"""
PROBE = (
    "\n<script>window.addEventListener('load',()=>setTimeout(()=>{const p=document.createElement('pre');"
    f"p.id='{MARK}';p.textContent=JSON.stringify({MEASURE.strip()});document.body.appendChild(p);}},300));</script>\n"
)
GLANCE = (
    "\n<script>window.addEventListener('load',()=>{const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT),hide=[];"
    "while(w.nextNode()){const n=w.currentNode,el=n.parentElement;if(!n.textContent.trim()||!el)continue;"
    "const cs=getComputedStyle(el);if(parseFloat(cs.fontSize)<16&&parseInt(cs.fontWeight,10)<600)hide.push(n);}"
    "for(const n of hide){const s=document.createElement('span');s.style.color='transparent';"
    "n.replaceWith(s);s.appendChild(n);}});</script>\n"
)
PROSE_LIMIT = 60
RESULT = re.compile(rf'<pre id="{MARK}">([^<]*)</pre>')
QUESTIONS = ("这页的答案是什么？", "最重要的数是哪个？", "你从哪里动手？")


class CheckError(RuntimeError):
    """可以直接给使用者看的失败原因。"""


def find_chrome() -> str:
    chosen = os.environ.get("WORKFLOW_CHROME")
    candidates = [chosen] if chosen else [*CHROME_CANDIDATES, *(shutil.which(name) for name in CHROME_NAMES)]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise CheckError("找不到 Chrome 或 Chromium；装一个，或用环境变量 WORKFLOW_CHROME 指给它。首屏没截，冷读没做。")


def page_url(page: str) -> tuple[str, Path | None]:
    if re.match(r"https?://", page):
        return page, None
    path = Path(page).expanduser().resolve()
    if not path.is_file():
        raise CheckError(f"找不到页面文件：{path}")
    return path.as_uri(), path


def run_chrome(chrome: str, *arguments: str) -> str:
    try:
        done = subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", *arguments],
            capture_output=True, text=True, timeout=90, check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise CheckError("Chrome 90 秒内没有返回。") from error
    return done.stdout


def with_copy(source: Path, extra: str, *arguments: str) -> str:
    """给本地文件的临时副本加一段脚本再交给浏览器；副本用完即删，原文件不动。"""
    with tempfile.NamedTemporaryFile("w", suffix=".html", dir=source.parent, prefix=".page-check-", delete=False,
                                     encoding="utf-8") as copy:
        copy.write(source.read_text(encoding="utf-8", errors="replace") + extra)
    try:
        return run_chrome(chrome_path(), *arguments, Path(copy.name).as_uri())
    finally:
        os.unlink(copy.name)


def chrome_path() -> str:
    return find_chrome()


def measure(chrome: str, source: Path, width: int, height: int) -> dict | None:
    dom = with_copy(source, PROBE, f"--window-size={width},{height}", "--virtual-time-budget=3000", "--dump-dom")
    found = RESULT.search(dom)
    return json.loads(found.group(1).replace("&quot;", '"').replace("&amp;", "&")) if found else None


def cold_read_prompt(reader: str, shot: Path) -> str:
    asked = "\n".join(f"{index}. {question}" for index, question in enumerate(QUESTIONS, 1))
    return (
        f"你扮演这页的读者：{reader}\n"
        "你没看过任何设计讨论。用 Read 工具只看这一张首屏截图，不读别的文件，不搜索：\n"
        f"{shot}\n"
        "这是人扫一眼时看得进的样子：细小的字已经抹掉，只剩大字、粗字、颜色和形状。"
        "不要猜被抹掉的字写了什么。只凭看得到的回答：\n"
        f"{asked}\n"
        "4. 哪些词、数或区块看不懂或多余？逐条列。\n"
        "哪一问答不出，就直说答不出。"
    )


def check(page: str, reader: str, out_dir: Path) -> str:
    chrome = find_chrome()
    url, source = page_url(page)
    out_dir.mkdir(parents=True, exist_ok=True)
    lines, problems, glance_shot = [], [], None
    for name, width, height in SIZES:
        shot = out_dir / f"first-screen-{name}.png"
        shot.unlink(missing_ok=True)
        run_chrome(chrome, f"--window-size={width},{height}", f"--screenshot={shot}", url)
        if not shot.is_file():
            raise CheckError(f"{name} 宽度的首屏没有截出来：{url}")
        result = measure(chrome, source, width, height) if source else None
        if result is None:
            lines.append(f"{name}：截图 {shot}（没量首屏）")
            continue
        lines.append(
            f"{name} {result['width']}×{result['height']}：截图 {shot}；整页 {result['screens']} 屏，"
            f"首屏 {result['firstScreenChars']} 字（其中细小字 {result['smallChars']} 字）、"
            f"{result['firstScreenControls']} 个控件，最大的字是“{result['biggestText']}”"
        )
        if result["overflowX"]:
            problems.append(f"{name}：整页横向溢出")
        if name != "desktop":
            continue
        if not result["firstScreenControls"]:
            problems.append("首屏没有可操作的控件")
        prose_chars = sum(int(re.search(r"（(\d+) 字）", item).group(1)) for item in result["prose"])
        if prose_chars > PROSE_LIMIT:
            problems.append(f"首屏有 {prose_chars} 字成段文字（上限 {PROSE_LIMIT}），人扫一眼不读："
                            + "；".join(result["prose"]))
        if result["repeated"]:
            problems.append("同一个数在首屏出现不止一次：" + "、".join(result["repeated"]))
    if source:
        glance_shot = out_dir / "glance-desktop.png"
        glance_shot.unlink(missing_ok=True)
        with_copy(source, GLANCE, "--window-size=1440,900", "--virtual-time-budget=3000",
                  f"--screenshot={glance_shot}")
        if not glance_shot.is_file():
            raise CheckError("扫一眼图没有截出来。")
        lines.append(f"扫一眼图（细小字已抹掉）：{glance_shot}")
    verdict = ["结论：不过。先改页面再交：", *(f"- {item}" for item in problems)] if problems else ["结论：量得出的项都过了。"]
    return problems, "\n".join([
        "首屏检查",
        *lines,
        *verdict,
        "",
        "下一步：把下面这段原样交给一个新的子代理（不能派时，自己只看截图回答）。",
        "----- 冷读提示词 -----",
        cold_read_prompt(reader, glance_shot or out_dir / "first-screen-desktop.png"),
        "----- 结束 -----",
        "交付时带一行：冷读（谁读的）：答案 / 最重要的数 / 从哪动手。有一问答不出，改大字、图和位置，不加说明文字。",
    ])


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("page", help="本地 HTML 文件或 http(s) 地址")
    parser.add_argument("--reader", required=True, help="页面设计第 1 步那一句：谁，什么场合打开，带着什么问题，看完做什么")
    parser.add_argument("--out", help="截图目录，默认是系统临时目录下的新目录")
    arguments = parser.parse_args(argv)
    out_dir = Path(arguments.out).expanduser() if arguments.out else Path(tempfile.mkdtemp(prefix="page-check-"))
    try:
        problems, report = check(arguments.page, arguments.reader, out_dir)
    except CheckError as error:
        print(f"首屏检查没做成：{error}", file=sys.stderr)
        return 2
    print(report)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
