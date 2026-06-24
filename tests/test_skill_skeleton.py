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
]

EXPECTED_CLI = [
    "scripts/validate_contract.py",
    "scripts/rule_miner.py",
    "scripts/rule_combiner.py",
    "scripts/strategy_evaluator.py",
    "scripts/final_reporter.py",
]

RETIRED_PATHS = [
    "references/00-scope-and-routing.md",
    "references/02-data-contract.md",
    "references/03-metric-definitions.md",
    "scripts/rule_backtester.py",
    "scripts/score_cutoff_optimizer.py",
    "scripts/strategy_simulator.py",
    "scripts/swap_analyzer.py",
    "scripts/metric_reporter.py",
    "scripts/monitoring_reporter.py",
    "templates/monitoring_report.html.j2",
    "templates/strategy_report.html.j2",
]

REQUIRED_SECTIONS = [
    "## 适用与阻断条件",
    "## 最小输入",
    "## 方法步骤",
    "## 候选参数",
    "## 关键伪代码",
    "## 输出表",
    "## 稳定性与可观测性检查",
    "## 验收不变量",
]


class SkillSkeletonTests(unittest.TestCase):
    def test_five_stage_entry_files_and_references_exist(self):
        self.assertTrue((ROOT / "AGENTS.md").is_file())
        self.assertTrue((ROOT / "SKILL.md").is_file())
        self.assertTrue((ROOT / "design-framework.md").is_file())
        for relative_path in EXPECTED_REFERENCES:
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

    def test_only_five_stage_references_and_cli_are_active(self):
        for relative_path in RETIRED_PATHS:
            self.assertFalse((ROOT / relative_path).exists(), relative_path)
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("按需读取", skill)
        self.assertNotIn("references/monitoring", skill)
        self.assertNotIn("score_cutoff", skill)
        self.assertNotIn("routing", skill)

    def test_yaml_and_json_schemas_parse(self):
        with (ROOT / "schemas/input_contract.yaml").open(encoding="utf-8") as file:
            self.assertIsInstance(yaml.safe_load(file), dict)
        for relative_path in EXPECTED_SCHEMAS:
            with (ROOT / relative_path).open(encoding="utf-8") as file:
                self.assertIsInstance(json.load(file), dict)

    def test_all_five_commands_expose_help(self):
        for relative_path in EXPECTED_CLI:
            result = subprocess.run(
                [sys.executable, str(ROOT / relative_path), "--help"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, f"{relative_path}: {result.stderr}")

    def test_every_stage_has_complete_method_sections(self):
        for relative_path in EXPECTED_REFERENCES:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            for heading in REQUIRED_SECTIONS:
                self.assertIn(heading, content, f"{relative_path}: {heading}")

    def test_core_rule_and_strategy_constraints_are_documented(self):
        mining = (ROOT / EXPECTED_REFERENCES[1]).read_text(encoding="utf-8")
        combination = (ROOT / EXPECTED_REFERENCES[2]).read_text(encoding="utf-8")
        evaluation = (ROOT / EXPECTED_REFERENCES[3]).read_text(encoding="utf-8")
        report = (ROOT / EXPECTED_REFERENCES[4]).read_text(encoding="utf-8")
        self.assertIn("最多 3 个特征", mining)
        self.assertIn("IV", mining)
        self.assertIn("Lift", combination)
        self.assertIn("TopN", combination)
        self.assertIn("任一命中即拒绝", combination)
        self.assertIn("swap_in", evaluation)
        self.assertIn("swap_out", evaluation)
        self.assertIn("直接观测", evaluation)
        self.assertIn("不重新计算", report)
        self.assertIn("不自动产生上线决策", report)


if __name__ == "__main__":
    unittest.main()
