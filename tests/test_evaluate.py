from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

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


if __name__ == "__main__":
    unittest.main()
