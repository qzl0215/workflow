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
    --dump-dom) printf '%s' '<pre id="__workflow_page_check__">{"width":1440,"height":813,"screens":2.5,"firstScreenChars":120,"firstScreenControls":0,"biggestText":"49.8 万","overflowX":true}</pre>' ;;
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

    def test_gives_screenshots_measures_and_a_ready_cold_read_prompt(self) -> None:
        out = self.root / "shots"
        result = run(str(self.page), "--reader", "运营同事，反复打开", "--out", str(out), chrome=str(self.chrome))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((out / "first-screen-desktop.png").is_file())
        self.assertTrue((out / "first-screen-phone.png").is_file())
        self.assertIn("整页 2.5 屏", result.stdout)
        self.assertIn("整页横向溢出", result.stdout)
        self.assertIn("首屏没有可操作的控件", result.stdout)
        self.assertIn("你扮演这页的读者：运营同事，反复打开", result.stdout)
        self.assertIn(str(out / "first-screen-desktop.png"), result.stdout)
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
