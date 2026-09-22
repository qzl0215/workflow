from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workflow_evaluate", PACKAGE / "scripts/evaluate.py")
evaluate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate)


class EvaluationHarnessTest(unittest.TestCase):
    def test_rubric_and_expected_actions_never_enter_model_input(self):
        case = {"id": "example", "scenario": "independent task", "expected": ["execute"],
                "failure": "HIDDEN_RUBRIC", "split": "holdout"}
        prompt = evaluate.prompt_for("policy", [case])
        self.assertNotIn("HIDDEN_RUBRIC", prompt)
        self.assertNotIn('"expected"', prompt)
        self.assertNotIn('"split"', prompt)

    def test_missing_duplicate_and_wrong_answers_do_not_pass(self):
        cases = [{"id": "one", "expected": ["ask"]}]
        self.assertEqual(evaluate.score(cases, {"decisions": [{"id": "one", "action": "execute"}]})["failures"], ["one"])
        for decisions in ([], [{"id": "unknown"}], [{"id": "one"}, {"id": "one"}]):
            with self.assertRaises(ValueError):
                evaluate.score(cases, {"decisions": decisions})

    def test_case_set_is_valid_and_has_unseen_scenarios(self):
        cases = evaluate.load_cases(PACKAGE / "evals/cases.json")
        self.assertEqual({c["split"] for c in cases}, {"development", "holdout"})
        self.assertTrue(all(c["failure"] for c in cases))

    def test_task_fixtures_and_checkers_do_not_accept_self_reported_success(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            prompt = evaluate.prepare_task(directory, "goal_conflict")
            self.assertIn("注册", prompt)
            before = evaluate.snapshot(directory)
            self.assertTrue(evaluate.check_task(directory, "goal_conflict", before)["passed"])
            (directory / "signup.py").write_text("REQUIRED = ['phone']\n")
            self.assertFalse(evaluate.check_task(directory, "goal_conflict", before)["passed"])
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            evaluate.prepare_task(directory, "project_memory")
            before = evaluate.snapshot(directory)
            self.assertFalse(evaluate.check_task(directory, "project_memory", before)["passed"])
            (directory / "docs/policy.md").write_text("下个版本试用期 14 天，当前代码未改。\n")
            (directory / "docs/decisions.md").write_text("旧决定被替代：下个版本改为 14 天。\n")
            self.assertTrue(evaluate.check_task(directory, "project_memory", before)["passed"])
            (directory / "docs/policy.md").write_text("当前代码 30 天；已决定下个版本为 14 天，尚未实现。\n")
            self.assertTrue(evaluate.check_task(directory, "project_memory", before)["passed"])
            (directory / "app.py").write_text("TRIAL_DAYS = 14\n")
            self.assertFalse(evaluate.check_task(directory, "project_memory", before)["passed"])

    def test_reference_identity_includes_paths_and_contents(self):
        first = evaluate.content_hash({"a.md": "one", "b.md": "two"})
        self.assertEqual(first, evaluate.content_hash({"b.md": "two", "a.md": "one"}))
        self.assertNotEqual(first, evaluate.content_hash({"a.md": "changed", "b.md": "two"}))
        self.assertNotEqual(first, evaluate.content_hash({"a.md": "one", "c.md": "two"}))

    def test_clear_fix_allows_only_new_fixture_bytecode_not_other_edits(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            evaluate.prepare_task(directory, "clear_fix")
            before = evaluate.snapshot(directory)
            self.assertFalse(evaluate.check_task(directory, "clear_fix", before)["passed"])
            (directory / "main.py").write_text("def total(values):\n    return sum(values)\n")
            cache = directory / "__pycache__"
            cache.mkdir()
            (cache / "main.cpython-313.pyc").write_bytes(b"disposable test cache")
            self.assertTrue(evaluate.check_task(directory, "clear_fix", before)["passed"])
            (cache / "unexpected.pyc").write_bytes(b"not a fixture cache")
            self.assertFalse(evaluate.check_task(directory, "clear_fix", before)["passed"])

    def test_plan_only_preserves_user_files(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            evaluate.prepare_task(directory, "plan_first")
            before = evaluate.snapshot(directory)
            self.assertTrue(evaluate.check_task(directory, "plan_first", before)["passed"])
            (directory / "user-notes.txt").write_text("overwritten")
            self.assertFalse(evaluate.check_task(directory, "plan_first", before)["passed"])

    def test_demo_handoff_fixture_preserves_project_while_waiting_for_choice(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            prompt = evaluate.prepare_task(directory, "demo_handoff")
            self.assertIn("直接作出下一步决定", prompt)
            before = evaluate.snapshot(directory)
            self.assertTrue(evaluate.check_task(directory, "demo_handoff", before)["passed"])
            (directory / "demo-a.html").write_text("implemented without approval\n")
            self.assertFalse(evaluate.check_task(directory, "demo_handoff", before)["passed"])


if __name__ == "__main__":
    unittest.main()
