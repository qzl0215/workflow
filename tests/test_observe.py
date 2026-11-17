from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workflow_observe", PACKAGE / "dev/observe.py")
observe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observe)

BASE = "Base directory for this skill: /home/someone/.claude/skills/"


def user(text, stamp="2026-11-10T08:00:00Z", **extra):
    return {"type": "user", "timestamp": stamp, "message": {"content": text}, **extra}


def call(tool_id, name, **tool_input):
    return {"type": "assistant", "timestamp": "2026-11-10T08:01:00Z",
            "message": {"content": [{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}]}}


def result(tool_id, body="ok", error=False):
    return {"type": "user", "timestamp": "2026-11-10T08:01:01Z",
            "message": {"content": [{"type": "tool_result", "tool_use_id": tool_id, "content": body, "is_error": error}]}}


def reference(name):
    return f"/home/someone/.claude/skills/workflow/references/{name}.md"


class ObserveTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.projects = Path(self.temp.name) / "projects"

    def session(self, events, name="s1"):
        path = self.projects / "project" / f"{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n", encoding="utf-8")
        return path

    def test_reference_read_needs_a_successful_tool_call_after_load(self):
        path = self.session([
            user("帮我做个新功能"),
            user(BASE + "workflow\n\n# 工作流"),
            call("a", "Read", file_path=reference("frame")),
            result("a"),
            call("b", "Read", file_path=reference("recover")),
            result("b", "File does not exist", error=True),
            {"type": "assistant", "timestamp": "2026-11-10T08:02:00Z",
             "message": {"content": [{"type": "text", "text": "我读过 " + reference("prove")}]}},
            call("c", "Bash", command="cat " + reference("deliver")),
            result("c"),
        ])
        observed = observe.observe_session(path)
        self.assertTrue(observed["loaded"])
        self.assertEqual(
            [(read["reference"], read["calls_since_load"]) for read in observed["reference_reads"]],
            [("references/frame.md", 1), ("references/deliver.md", 3)])
        summary = observe.summarize([observed], ["references/frame.md", "references/prove.md", "references/recover.md"])
        self.assertEqual(summary["silent_references"], ["references/prove.md", "references/recover.md"])
        self.assertEqual(summary["references"]["references/frame.md"], {"sessions": 1, "reads": 1, "early": 1, "late": 0})

    def test_only_words_typed_by_the_user_count_as_user_messages(self):
        path = self.session([
            user("<system-reminder>\nYou are operating in a git worktree.\n</system-reminder>\n\n还是不行，页面打不开"),
            user("<task-notification><status>completed</status></task-notification>"),
            user("<command-name>/model</command-name><command-args></command-args>"),
            user("<command-name>/workflow</command-name><command-args>不是我要的，重新来</command-args>"),
            user("内部提示", isMeta=True),
            user("This session is being continued", isCompactSummary=True),
            user(BASE + "page-craft\n\n# 页面"),
            result("missing"),
        ])
        observed = observe.observe_session(path)
        self.assertEqual(observed["user_messages"], 2)
        self.assertEqual([(hit["kind"], hit["line"]) for hit in observed["friction"]], [("still_failing", 1), ("rework", 4)])
        self.assertEqual([skill["name"] for skill in observed["skills"]], ["page-craft"])
        self.assertFalse(observed["loaded"])

    def test_error_streak_ignores_host_noise_and_counts_repeated_inputs(self):
        events = [user("修一下"), user(BASE + "workflow\n\n# 工作流")]
        for index in range(3):
            events += [call(f"t{index}", "mcp__host__tool"), result(f"t{index}", "PreToolUse hook did not respond before its timeout", error=True)]
        events += [call("ok", "Bash", command="ls"), result("ok")]
        for index, command in enumerate(["make test", "make test", "make build"]):
            events += [call(f"e{index}", "Bash", command=command), result(f"e{index}", "Exit code 2", error=True)]
        observed = observe.observe_session(self.session(events))
        self.assertEqual(len(observed["error_streaks"]), 1)
        streak = observed["error_streaks"][0]
        self.assertEqual((streak["length"], streak["repeated_inputs"], streak["tools"]), (3, 1, ["Bash"]))

    def test_time_window_sidechains_and_empty_sessions_are_excluded(self):
        path = self.session([
            user("旧消息", stamp="2026-10-01T00:00:00Z"),
            user("子任务提示", isSidechain=True),
            user("窗口内的请求", stamp="2026-11-10T00:00:00Z"),
        ])
        self.assertEqual(observe.observe_session(path, since="2026-11-01")["user_messages"], 1)
        self.assertIsNone(observe.observe_session(path, since="2026-12-01"))

    def test_details_stay_outside_the_package_and_excerpt_keeps_line_numbers(self):
        path = self.session([user("为什么又失败了"), call("a", "Bash", command="pytest"), result("a", "1 failed", error=True)])
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            observe.main(["--projects", str(self.projects), "--output", str(PACKAGE / "observed.json")])
        output = Path(self.temp.name) / "observed.json"
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            self.assertEqual(observe.main(["--projects", str(self.projects), "--output", str(output)]), 0)
        self.assertIn("会话 1", printed.getvalue())
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["sessions"][0]["friction"][0]["line"], 1)
        text = observe.excerpt(path, 2, 1)
        self.assertIn("1 2026-11-10T08:00 用户: 为什么又失败了", text)
        self.assertIn("3 2026-11-10T08:01 报错: 1 failed", text)


if __name__ == "__main__":
    unittest.main()
