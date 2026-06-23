import json
from pathlib import Path
import subprocess
import sys
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


EXPECTED_REFERENCES = [
    "references/00-data-product-analysis.md",
    "references/01-single-rule-mining.md",
    "references/02-rule-combination.md",
    "references/03-strategy-evaluation-and-swap.md",
    "references/04-final-report.md",
]

EXPECTED_SCHEMAS = [
    "schemas/confirmation_receipt.schema.json",
    "schemas/rule_combination.schema.json",
    "schemas/strategy_evaluation.schema.json",
    "schemas/report_manifest.schema.json",
]

EXPECTED_CLI = [
    "scripts/validate_contract.py",
    "scripts/rule_miner.py",
    "scripts/rule_combiner.py",
    "scripts/strategy_evaluator.py",
    "scripts/final_reporter.py",
]

RETIRED_PATHS = [
    "design-framework-v2.md",
    "references/00-scope-and-routing.md",
    "references/01-product-and-scenario.md",
    "references/02-data-contract.md",
    "references/03-metric-definitions.md",
    "references/rules",
    "references/strategy",
    "references/monitoring",
    "references/reporting",
    "scripts/rule_backtester.py",
    "scripts/strategy_simulator.py",
    "scripts/score_cutoff_optimizer.py",
    "scripts/swap_analyzer.py",
    "scripts/metric_reporter.py",
    "scripts/monitoring_reporter.py",
    "schemas/rule_config.schema.json",
    "schemas/strategy_config.schema.json",
    "templates/monitoring_report.html.j2",
    "templates/strategy_report.html.j2",
]

class SkillSkeletonTests(unittest.TestCase):
    def test_skill_routes_and_agents_are_present(self):
        self.assertTrue((ROOT / "AGENTS.md").is_file())
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("尚未创建", skill_text)
        for relative_path in EXPECTED_REFERENCES:
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

    def test_yaml_and_json_schemas_parse(self):
        with (ROOT / "schemas/input_contract.yaml").open(encoding="utf-8") as file:
            self.assertIsInstance(yaml.safe_load(file), dict)
        for relative_path in EXPECTED_SCHEMAS:
            with (ROOT / relative_path).open(encoding="utf-8") as file:
                self.assertIsInstance(json.load(file), dict)

    def test_all_commands_expose_help(self):
        for relative_path in EXPECTED_CLI:
            result = subprocess.run(
                [sys.executable, str(ROOT / relative_path), "--help"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, f"{relative_path}: {result.stderr}")

    def test_five_stage_pipeline_is_the_only_entry_route(self):
        routing = (ROOT / "references/00-data-product-analysis.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("五段", routing)
        self.assertIn("单规则挖掘", skill)
        self.assertIn("TopN", skill)
        self.assertIn("级联拒绝", agents)
        for retired_path in RETIRED_PATHS:
            self.assertFalse((ROOT / retired_path).exists(), retired_path)

    def test_single_rule_mining_covers_iv_extremes_and_three_feature_cart(self):
        content = (ROOT / "references/01-single-rule-mining.md").read_text(encoding="utf-8")
        for term in ("IV", "极端区间", "分位点", "缺失值", "CART", "不超过 3 个特征"):
            self.assertIn(term, content)

    def test_rule_combination_uses_lift_top_n_and_sequential_reject(self):
        content = (ROOT / "references/02-rule-combination.md").read_text(encoding="utf-8")
        for term in ("Lift", "TopN", "降序", "级联", "任一命中即拒绝", "边际"):
            self.assertIn(term, content)

    def test_strategy_evaluation_and_swap_disclose_observability(self):
        content = (ROOT / "references/03-strategy-evaluation-and-swap.md").read_text(encoding="utf-8")
        for term in ("approval_rate", "pass_bad_rate", "both_pass", "both_reject", "swap_in", "swap_out", "不可观测"):
            self.assertIn(term, content)


if __name__ == "__main__":
    unittest.main()
