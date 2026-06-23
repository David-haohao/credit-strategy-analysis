import json
from pathlib import Path
import subprocess
import sys
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


EXPECTED_REFERENCES = [
    "references/00-scope-and-routing.md",
    "references/01-product-and-scenario.md",
    "references/02-data-contract.md",
    "references/03-metric-definitions.md",
    "references/rules/01-rule-mining.md",
    "references/rules/02-rule-backtest.md",
    "references/rules/03-rule-funnel.md",
    "references/rules/04-rule-combination.md",
    "references/strategy/01-score-cutoff.md",
    "references/strategy/02-strategy-simulation.md",
    "references/strategy/03-swap-analysis.md",
    "references/strategy/04-routing-strategy.md",
    "references/monitoring/01-psi-monitoring.md",
    "references/monitoring/02-rule-drift.md",
    "references/monitoring/03-performance-drift.md",
    "references/reporting/01-html-report.md",
]

EXPECTED_SCHEMAS = [
    "schemas/confirmation_receipt.schema.json",
    "schemas/rule_config.schema.json",
    "schemas/strategy_config.schema.json",
    "schemas/report_manifest.schema.json",
]

EXPECTED_CLI = [
    "scripts/validate_contract.py",
    "scripts/rule_miner.py",
    "scripts/rule_backtester.py",
    "scripts/strategy_simulator.py",
    "scripts/score_cutoff_optimizer.py",
    "scripts/swap_analyzer.py",
    "scripts/metric_reporter.py",
    "scripts/monitoring_reporter.py",
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


if __name__ == "__main__":
    unittest.main()
