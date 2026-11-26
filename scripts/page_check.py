#!/usr/bin/env python3
"""页面交付前的首屏检查：截首屏、量首屏、给出冷读要用的提示词。

只读页面，不改它。冷读本身由调用者派一个子代理完成；本脚本保证截图和三问现成可用。
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
  let first = 0, biggest = 0, biggestText = '';
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
    if (size > biggest) { biggest = size; biggestText = t.slice(0, 24); }
  }
  const seen = el => { const b = el.getBoundingClientRect(); return b.width > 0 && b.height > 0 && b.top < vh && b.bottom > 0; };
  const controls = [...document.querySelectorAll('button,a[href],input,select,textarea,summary,[role=button],[role=tab],[role=slider]')].filter(seen).length;
  const root = document.documentElement;
  return { width: vw, height: vh, screens: +(root.scrollHeight / vh).toFixed(1), firstScreenChars: first,
           firstScreenControls: controls, biggestText, overflowX: root.scrollWidth > vw + 1 };
})()
"""
PROBE = (
    "\n<script>window.addEventListener('load',()=>setTimeout(()=>{const p=document.createElement('pre');"
    f"p.id='{MARK}';p.textContent=JSON.stringify({MEASURE.strip()});document.body.appendChild(p);}},300));</script>\n"
)
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


def measure(chrome: str, source: Path, width: int, height: int) -> dict | None:
    """给本地文件的副本加一段只读的量取脚本；网址不量，只截图。"""
    with tempfile.NamedTemporaryFile("w", suffix=".html", dir=source.parent, prefix=".page-check-", delete=False,
                                     encoding="utf-8") as probe:
        probe.write(source.read_text(encoding="utf-8", errors="replace") + PROBE)
    try:
        dom = run_chrome(chrome, f"--window-size={width},{height}", "--virtual-time-budget=3000", "--dump-dom",
                         Path(probe.name).as_uri())
    finally:
        os.unlink(probe.name)
    found = RESULT.search(dom)
    return json.loads(found.group(1).replace("&quot;", '"').replace("&amp;", "&")) if found else None


def cold_read_prompt(reader: str, shot: Path) -> str:
    asked = "\n".join(f"{index}. {question}" for index, question in enumerate(QUESTIONS, 1))
    return (
        f"你扮演这页的读者：{reader}\n"
        "你没看过任何设计讨论。用 Read 工具只看这一张首屏截图，不读别的文件，不搜索：\n"
        f"{shot}\n"
        "看五秒，只凭这一屏用自己的话回答：\n"
        f"{asked}\n"
        "4. 哪些词、数或区块看不懂或多余？逐条列。\n"
        "哪一问答不出，就直说答不出。"
    )


def check(page: str, reader: str, out_dir: Path) -> str:
    chrome = find_chrome()
    url, source = page_url(page)
    out_dir.mkdir(parents=True, exist_ok=True)
    lines, desktop_shot = [], None
    for name, width, height in SIZES:
        shot = out_dir / f"first-screen-{name}.png"
        shot.unlink(missing_ok=True)
        run_chrome(chrome, f"--window-size={width},{height}", f"--screenshot={shot}", url)
        if not shot.is_file():
            raise CheckError(f"{name} 宽度的首屏没有截出来：{url}")
        desktop_shot = desktop_shot or shot
        result = measure(chrome, source, width, height) if source else None
        if result is None:
            lines.append(f"{name}：截图 {shot}（没量首屏）")
            continue
        notes = []
        if result["overflowX"]:
            notes.append("整页横向溢出")
        if not result["firstScreenControls"]:
            notes.append("首屏没有可操作的控件")
        lines.append(
            f"{name} {result['width']}×{result['height']}：截图 {shot}；整页 {result['screens']} 屏，"
            f"首屏 {result['firstScreenChars']} 字、{result['firstScreenControls']} 个控件，"
            f"最大的字是“{result['biggestText']}”" + ("；注意：" + "、".join(notes) if notes else "")
        )
    return "\n".join([
        "首屏检查",
        *lines,
        "",
        "下一步：把下面这段原样交给一个新的子代理（不能派时，自己只看截图回答）。",
        "----- 冷读提示词 -----",
        cold_read_prompt(reader, desktop_shot),
        "----- 结束 -----",
        "交付时带一行：冷读（谁读的）：答案 / 最重要的数 / 从哪动手；看不懂的。有一问答不出，先改页面再交。",
    ])


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("page", help="本地 HTML 文件或 http(s) 地址")
    parser.add_argument("--reader", required=True, help="页面设计第 1 步那一句：谁，什么场合打开，带着什么问题，看完做什么")
    parser.add_argument("--out", help="截图目录，默认是系统临时目录下的新目录")
    arguments = parser.parse_args(argv)
    out_dir = Path(arguments.out).expanduser() if arguments.out else Path(tempfile.mkdtemp(prefix="page-check-"))
    try:
        print(check(arguments.page, arguments.reader, out_dir))
    except CheckError as error:
        print(f"首屏检查没做成：{error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
