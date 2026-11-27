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

    def test_choice_questions_count_accounts_and_typed_answers(self):
        options = [{"label": "规则加核对", "description": "体验不变，代码量约 40 行，约 25 分钟，每周多维护一项"},
                   {"label": "只写规则", "description": "最省"}]
        bare = [{"label": "甲", "description": "快"}, {"label": "乙", "description": "稳"}]
        path = self.session([
            user("帮我做个新功能"),
            user(BASE + "workflow\n\n# 工作流"),
            call("a", "AskUserQuestion", questions=[{"question": "怎么落地？", "options": options}]),
            result("a", 'The user answered: "怎么落地？"="规则加核对". Read the answers carefully'),
            call("b", "AskUserQuestion", questions=[{"question": "选哪个？", "options": bare}]),
            result("b", 'The user answered: "选哪个？"="缺少背景，选不了". Read the answers carefully'),
        ])
        session = observe.observe_session(path)
        self.assertEqual([choice["typed"] for choice in session["choices"]], [False, True])
        self.assertEqual([len(choice["accounts"]) for choice in session["choices"]], [4, 0])
        summary = observe.summarize([session], [])
        self.assertEqual((summary["choices"], summary["choices_with_accounts"], summary["choices_typed"]), (2, 1, 1))

    def test_long_turn_closings_record_length_and_visual(self):
        def text(body):
            return {"type": "assistant", "timestamp": "2026-11-10T08:02:00Z",
                    "message": {"content": [{"type": "text", "text": body}]}}
        work = [event for number in range(observe.LONG_TURN_CALLS)
                for event in (call(f"w{number}", "Bash", command="ls"), result(f"w{number}"))]
        path = self.session([
            user("帮我做个新功能"),
            user(BASE + "workflow\n\n# 工作流"),
            *work, text("字" * (observe.LONG_CLOSING_CHARS + 1)),
            user("继续"),
            *work, call("v", "mcp__visualize__show_widget", title="report"), result("v"), text("见上图。"),
            user("好"),
            call("s", "Bash", command="ls"), result("s"), text("小事做完了。"),
        ])
        session = observe.observe_session(path)
        self.assertEqual([(closing["visual"], closing["chars"] > observe.LONG_CLOSING_CHARS)
                          for closing in session["closings"]], [(False, True), (True, False)])
        summary = observe.summarize([session], [])
        self.assertEqual((summary["long_turn_closings"], summary["long_turn_closings_visual"],
                          summary["long_turn_closings_wordy"]), (2, 1, 1))


if __name__ == "__main__":
    unittest.main()
