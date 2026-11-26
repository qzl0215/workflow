"""首屏检查脚本的行为：用一个假浏览器，不依赖本机装了什么。"""

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "scripts/page_check.py"
FAKE_CHROME = """#!/bin/sh
for a in "$@"; do
  case "$a" in
    --screenshot=*) printf png > "${a#--screenshot=}" ;;
    --dump-dom) printf '%s' '<pre id="__workflow_page_check__">{"width":1440,"height":813,"screens":2.5,"firstScreenChars":120,"firstScreenControls":0,"biggestText":"49.8 万","overflowX":true,"smallChars":90,"prose":["每件商品按下面的先后找到跟随…（70 字）"],"repeated":["1.74亿 ×2"]}</pre>' ;;
  esac
done
"""


def run(*arguments: str, chrome: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "WORKFLOW_CHROME": chrome}
    return subprocess.run([sys.executable, "-B", str(SCRIPT), *arguments], capture_output=True, text=True, env=env)


class PageCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.page = self.root / "page.html"
        self.page.write_text("<!doctype html><title>t</title><p>写入 49.8 万</p>", encoding="utf-8")
        self.chrome = self.root / "chrome"
        self.chrome.write_text(FAKE_CHROME, encoding="utf-8")
        self.chrome.chmod(self.chrome.stat().st_mode | stat.S_IXUSR)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_flags_prose_and_repeats_and_hands_the_glance_view_to_the_cold_read(self) -> None:
        out = self.root / "shots"
        result = run(str(self.page), "--reader", "运营同事，反复打开", "--out", str(out), chrome=str(self.chrome))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue((out / "first-screen-desktop.png").is_file())
        self.assertTrue((out / "glance-desktop.png").is_file())
        self.assertIn("结论：不过", result.stdout)
        self.assertIn("首屏有 70 字成段文字", result.stdout)
        self.assertIn("1.74亿 ×2", result.stdout)
        self.assertIn(str(out / "glance-desktop.png"), result.stdout)
        self.assertIn("细小的字已经抹掉", result.stdout)
        self.assertTrue((out / "first-screen-phone.png").is_file())
        self.assertIn("整页 2.5 屏", result.stdout)
        self.assertIn("整页横向溢出", result.stdout)
        self.assertIn("首屏没有可操作的控件", result.stdout)
        self.assertIn("你扮演这页的读者：运营同事，反复打开", result.stdout)
        for question in ("这页的答案是什么", "最重要的数是哪个", "你从哪里动手"):
            self.assertIn(question, result.stdout)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["chrome", "page.html", "shots"])

    def test_fails_closed_without_a_browser_or_a_page(self) -> None:
        missing_browser = run(str(self.page), "--reader", "x", chrome=str(self.root / "nope"))
        self.assertEqual(missing_browser.returncode, 2)
        self.assertIn("冷读没做", missing_browser.stderr)
        missing_page = run(str(self.root / "none.html"), "--reader", "x", chrome=str(self.chrome))
        self.assertEqual(missing_page.returncode, 2)
        self.assertIn("找不到页面文件", missing_page.stderr)


if __name__ == "__main__":
    unittest.main()
