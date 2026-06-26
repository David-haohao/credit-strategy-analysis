import math
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.utils.binning import classify_monotonicity
from scripts.utils.metrics import evaluate_binary_rule
from scripts.utils.rule_engine import (
    RuleParseError,
    build_swap_matrix,
    compute_cascade_funnel,
    compute_rule_overlap,
    evaluate_rule,
)


class P1CalculationTests(unittest.TestCase):
    def test_evaluate_binary_rule_standard_metrics_and_zero_denominators(self):
        target = pd.Series([1, 0, 1, 0])
        hit = pd.Series([True, True, False, False])
        metrics = evaluate_binary_rule(hit, target)

        self.assertEqual(metrics["hit_count"], 2)
        self.assertEqual(metrics["coverage_rate"], 0.5)
        self.assertEqual(metrics["reject_rate"], 0.5)
        self.assertEqual(metrics["non_hit_reject_rate"], 0.5)
        self.assertEqual(metrics["reject_lift"], 1.0)
        self.assertEqual(metrics["reject_capture_rate"], 0.5)
        self.assertEqual(metrics["pass_injury_rate"], 0.5)

        zero_bad = evaluate_binary_rule(pd.Series([True, False]), pd.Series([0, 0]))
        self.assertIsNone(zero_bad["reject_lift"])
        self.assertEqual(zero_bad["reject_capture_rate"], 0)

        all_hit = evaluate_binary_rule(pd.Series([True, True]), pd.Series([1, 0]))
        self.assertIsNone(all_hit["non_hit_reject_rate"])

    def test_classify_monotonicity(self):
        self.assertEqual(classify_monotonicity([0.01, 0.02, 0.03]), "increasing")
        self.assertEqual(classify_monotonicity([0.03, 0.02, 0.01]), "decreasing")
        self.assertEqual(classify_monotonicity([0.02, 0.02, 0.02]), "flat")
        self.assertEqual(classify_monotonicity([0.01, 0.03, 0.02]), "non_monotonic")
        self.assertEqual(classify_monotonicity([0.01]), "not_evaluated")
        self.assertEqual(classify_monotonicity([0.01, None, math.nan, 0.03]), "increasing")

    def test_evaluate_rule_safe_subset(self):
        data = pd.DataFrame(
            {
                "income": [900, 1200, 1600, None],
                "age": [22, 31, 45, 38],
                "grade": ["A", "B", "A", "C"],
            }
        )

        self.assertEqual(evaluate_rule("income >= 1000", data).tolist(), [False, True, True, False])
        self.assertEqual(evaluate_rule("income between 1000 and 1500", data).tolist(), [False, True, False, False])
        self.assertEqual(
            evaluate_rule("income between 1000 and 1500 and age < 40", data).tolist(),
            [False, True, False, False],
        )
        self.assertEqual(evaluate_rule("income >= 1000 and age < 40", data).tolist(), [False, True, False, False])
        self.assertEqual(evaluate_rule("income is missing", data).tolist(), [False, False, False, True])
        self.assertEqual(evaluate_rule("income is not missing", data).tolist(), [True, True, True, False])
        self.assertEqual(evaluate_rule("grade == 'A'", data).tolist(), [True, False, True, False])

        with self.assertRaises(RuleParseError):
            evaluate_rule("__import__('os').system('echo unsafe')", data)
        with self.assertRaises(RuleParseError):
            evaluate_rule("income >= 1000 or age < 40", data)
        with self.assertRaises(RuleParseError):
            evaluate_rule("(income >= 1000)", data)
        with self.assertRaises(RuleParseError):
            evaluate_rule("missing(income)", data)

    def test_cascade_funnel_and_overlap(self):
        masks = {
            "R1": pd.Series([True, True, False, False]),
            "R2": pd.Series([True, False, True, False]),
            "R3": pd.Series([False, False, False, False]),
        }
        funnel = compute_cascade_funnel(["R1", "R2"], masks, population_count=4)
        self.assertEqual(funnel[0]["input_count"], 4)
        self.assertEqual(funnel[0]["hit_reject_count"], 2)
        self.assertEqual(funnel[0]["remaining_pass_count"], 2)
        self.assertEqual(funnel[1]["input_count"], 2)
        self.assertEqual(funnel[1]["hit_reject_count"], 1)
        self.assertEqual(funnel[1]["remaining_pass_count"], 1)
        self.assertEqual(funnel[1]["cumulative_reject_rate"], 0.75)

        overlap = compute_rule_overlap(["R1", "R2", "R3"], masks)
        by_pair = {(row["rule_id_a"], row["rule_id_b"]): row for row in overlap}
        self.assertEqual(by_pair[("R1", "R2")]["overlap_count"], 1)
        self.assertEqual(by_pair[("R1", "R2")]["overlap_rate"], 1 / 3)
        self.assertEqual(by_pair[("R1", "R3")]["overlap_rate"], 0)

    def test_build_swap_matrix(self):
        frame = pd.DataFrame(
            {
                "old": ["pass", "pass", "reject", "reject", None],
                "new": ["pass", "reject", "pass", "reject", "pass"],
                "segment": ["A", "A", "B", "B", "B"],
            }
        )
        summary, detail = build_swap_matrix(frame, "old", "new", segment_columns=["segment"])

        groups = {row["swap_group"]: row for row in summary}
        self.assertEqual(groups["both_pass"]["sample_count"], 1)
        self.assertEqual(groups["swap_out"]["sample_count"], 1)
        self.assertEqual(groups["swap_in"]["sample_count"], 1)
        self.assertEqual(groups["both_reject"]["sample_count"], 1)
        self.assertEqual(groups["missing_decision"]["sample_count"], 1)
        self.assertAlmostEqual(sum(row["population_rate"] for row in summary), 1.0)
        self.assertTrue(any(row["segment_name"] == "segment" and row["swap_group"] == "swap_in" for row in detail))


if __name__ == "__main__":
    unittest.main()
