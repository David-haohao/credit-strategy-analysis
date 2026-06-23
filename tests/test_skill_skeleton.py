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

CORE_METHOD_REFERENCES = [
    "references/rules/01-rule-mining.md",
    "references/rules/02-rule-backtest.md",
    "references/strategy/01-score-cutoff.md",
    "references/strategy/02-strategy-simulation.md",
]

SUPPORTING_METHOD_REFERENCES = [
    "references/rules/03-rule-funnel.md",
    "references/rules/04-rule-combination.md",
    "references/strategy/03-swap-analysis.md",
    "references/strategy/04-routing-strategy.md",
    "references/monitoring/01-psi-monitoring.md",
    "references/monitoring/02-rule-drift.md",
    "references/monitoring/03-performance-drift.md",
    "references/reporting/01-html-report.md",
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

    def test_routing_is_compact_and_requires_on_demand_reading(self):
        routing = (ROOT / "references/00-scope-and-routing.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(routing.splitlines()), 120)
        self.assertIn("按需读取", routing)
        self.assertIn("按路由只读取任务所需", skill)
        self.assertIn("不得默认通读全部前置文档", agents)

    def test_core_method_references_have_decision_sections(self):
        headings = [
            "## 适用范围与阻断",
            "## 最小输入与按需引用",
            "## 方法步骤",
            "## 候选参数",
            "## 关键伪代码",
            "## 输出",
            "## 验收不变量",
        ]
        for relative_path in CORE_METHOD_REFERENCES:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            for heading in headings:
                self.assertIn(heading, content, f"{relative_path}: {heading}")

    def test_supporting_method_references_define_execution_and_disclosure(self):
        headings = ["## 最小输入", "## 计算顺序", "## 输出与披露", "## 验收"]
        for relative_path in SUPPORTING_METHOD_REFERENCES:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            for heading in headings:
                self.assertIn(heading, content, f"{relative_path}: {heading}")

    def test_metric_dictionary_has_task_reference_index(self):
        content = (ROOT / "references/03-metric-definitions.md").read_text(encoding="utf-8")
        self.assertIn("## 任务引用索引", content)
        for task in ("规则挖掘", "规则回测", "分数截断", "策略模拟", "Swap", "监控"):
            self.assertIn(task, content)


if __name__ == "__main__":
    unittest.main()
