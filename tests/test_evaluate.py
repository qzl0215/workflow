from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workflow_evaluate", PACKAGE / "scripts/evaluate.py")
evaluate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate)


class EvaluationHarnessTest(unittest.TestCase):
    def test_timeout_preserves_partial_observation_without_passing(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)
            args=evaluate.argparse.Namespace(output=out,codex='codex',effort='medium')
            partial=b'{"type":"item.started","item":{"id":"pending","type":"command_execution","command":"cat references/a.md"}}\n'
            timeout=evaluate.subprocess.TimeoutExpired('codex',300,output=partial,stderr=b'timed out')
            with patch.object(evaluate.subprocess,'run',side_effect=timeout):
                result=evaluate.task_trial(args,'model','candidate','policy',{'references/a.md':'# reference'},'run','fact_only')
            self.assertFalse(result['passed'])
            self.assertEqual(result['exit_code'],124)
            observed=json.loads((out/'run.loads.json').read_text())
            self.assertFalse(observed['complete'])
            self.assertEqual(observed['pending_commands'],['pending'])

    def test_reference_observation_requires_output_not_path_or_self_report(self):
        refs = {"references/recover.md": "# 恢复\n\n" + "可证伪的假设与原始错误构成恢复依据。" * 3 + "\n"}
        def event(kind, **values):
            return json.dumps({"type": kind, "item": {"id": "read-1", "type": "command_execution", **values}})
        started = event("item.started", command="cat references/recover.md")
        failed = event("item.completed", command="cat references/recover.md", exit_code=1, aggregated_output="Permission denied")
        claimed = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": refs["references/recover.md"]}})
        empty = evaluate.observe_references(started + "\n" + claimed, refs)
        self.assertEqual(empty["observed_paths"], [])
        self.assertFalse(empty["complete"])
        denied = evaluate.observe_references(failed, refs)
        self.assertEqual(denied["observed_paths"], [])
        self.assertEqual(denied["attempts"][0]["status"], "failed")
        completed = event("item.completed", command="cat references/recover.md", exit_code=0, aggregated_output=refs["references/recover.md"])
        actual = evaluate.observe_references(started + "\n" + completed, refs)
        self.assertEqual(actual["observed_paths"], ["references/recover.md"])
        self.assertEqual(len(actual["attempts"]), 1)
        self.assertEqual(actual["attempts"][0]["evidence"], "full_content")

    def test_reference_observation_preserves_unknown_partial_and_usage(self):
        refs = {"references/a.md": "# A\n\n" + "独有事实甲乙丙丁戊己庚辛壬癸" * 4 + "\n\n未显示的另一段正文。\n"}
        events = [
            {"type": "item.completed", "item": {"id": "1", "type": "command_execution", "command": "python read.py", "exit_code": 0, "aggregated_output": refs["references/a.md"].splitlines()[2]}},
            {"type": "item.completed", "item": {"id": "2", "type": "command_execution", "command": "wc -c references/a.md", "exit_code": 0, "aggregated_output": "123 references/a.md"}},
            {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 20}},
        ]
        result = evaluate.observe_references("\n".join(map(json.dumps, events)), refs)
        self.assertEqual(result["attempts"][0]["evidence"], "unique_excerpt")
        self.assertEqual(result["attempts"][1]["status"], "unknown")
        self.assertEqual(result["usage"]["input_tokens"], 100)
        self.assertEqual(result["observed_paths"], ["references/a.md"])

    def test_routing_negative_cases_check_real_changes_and_observations(self):
        for case in evaluate.ROUTING_CASES:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                prompt = evaluate.prepare_task(root, case)
                self.assertNotIn("forbidden_reads", prompt)
                before = evaluate.snapshot(root)
                result = evaluate.check_task(root, case, before, "仅报告现有事实")
                self.assertIn("semantic_review", result)
                (root / "user-notes.txt").write_text("damaged")
                self.assertFalse(evaluate.check_task(root, case, before)["passed"])
        result = evaluate.score_routing("fact_only", {"complete": True, "observed_paths": ["references/initialize.md"]})
        self.assertFalse(result["passed"])
        self.assertIsNone(evaluate.score_routing("fact_only", {"complete": False, "observed_paths": []})["passed"])

    def test_resumed_non_git_fix_accepts_only_byte_identical_original_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evaluate.prepare_task(root, 'resumed_fix')
            before = evaluate.snapshot(root)
            (root/'main.py.bak').write_bytes((root/'main.py').read_bytes())
            (root/'main.py').write_text('def total(values):\n    return sum(values)\n')
            self.assertTrue(evaluate.check_task(root,'resumed_fix',before)['passed'])
            (root/'main.py.bak').write_text('unrelated data')
            self.assertFalse(evaluate.check_task(root,'resumed_fix',before)['passed'])

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

    def test_raw_source_passes_only_when_answer_reflects_raw_tickets(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            prompt = evaluate.prepare_task(directory, "raw_source")
            curated = prompt + (directory / "summary.md").read_text() + (directory / "README.md").read_text()
            self.assertNotIn("扣", curated)
            self.assertIn("重复扣费", (directory / "data/tickets.csv").read_text())
            before = evaluate.snapshot(directory)
            self.assertFalse(evaluate.check_task(directory, "raw_source", before, "物流、质量、退换货、其他四个目录")["passed"])
            self.assertTrue(evaluate.check_task(directory, "raw_source", before, "原始工单里重复扣费占 14%，单列支付目录")["passed"])
            (directory / "summary.md").write_text("rewritten\n")
            self.assertFalse(evaluate.check_task(directory, "raw_source", before, "重复扣费单列")["passed"])

    def test_expert_rewrite_requires_rewritten_task_first(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            prompt = evaluate.prepare_task(directory, "expert_rewrite")
            self.assertIn("作为专家", prompt)
            before = evaluate.snapshot(directory)
            opening = '{"type":"item.completed","item":{"type":"agent_message","text":"先按阶段拆耗时，再用原始调用记录核对"}}'
            command = '{"type":"item.started","item":{"type":"command_execution","command":"cat README.md"}}'
            first = evaluate.opening_message(opening + "\n" + command)
            self.assertEqual(first, "先按阶段拆耗时，再用原始调用记录核对")
            self.assertIsNone(evaluate.opening_message(command + "\n" + opening))
            self.assertTrue(evaluate.check_task(directory, "expert_rewrite", before, "📋 结论", first)["passed"])
            self.assertFalse(evaluate.check_task(directory, "expert_rewrite", before, "结论后补", None)["passed"])
            (directory / "prompt.md").write_text("edited\n")
            self.assertFalse(evaluate.check_task(directory, "expert_rewrite", before, "📋 结论", first)["passed"])


if __name__ == "__main__":
    unittest.main()
