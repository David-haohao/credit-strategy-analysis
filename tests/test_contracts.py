import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml

from scripts.utils.contracts import (
    ContractValidationError,
    build_analysis_unit_id,
    safe_div,
    validate_run_contract,
    write_run_manifest,
)


def valid_config():
    return {
        "task": {
            "product_form": "revolving",
            "repayment_type": "equal_payment",
            "scenario": "first_loan_admission",
            "task_type": "strategy_simulation",
        },
        "confirmation": {"receipt_path": "confirmation.json"},
        "sample_scope": {"population": "mature_booked"},
        "analysis_grain": {
            "grain": "customer",
            "id_cols": ["customer_id"],
            "label_grain": "customer",
            "feature_grain": "customer",
            "output_grain": "customer",
            "aggregation_rule": None,
        },
        "field_mapping": {
            "mode": "user_provided",
            "confirmed": True,
            "candidate_columns": {},
            "unmapped_required_fields": [],
        },
        "label": {
            "target_col": "Y_label",
            "positive_class": 1,
            "bad_definition": "DPD30_plus_MOB3",
            "maturity_rule": "mature_flag == 1",
        },
        "amount_metric": {
            "enabled": True,
            "numerator": "overdue_unpaid_principal",
            "denominator": "drawdown_amount",
            "formula": "sum(numerator) / sum(denominator)",
            "filter": "mature_flag == 1",
        },
        "columns": {
            "id_cols": ["customer_id"],
            "target_col": "Y_label",
            "date_col": "sample_date",
            "score_col": None,
            "score_direction": None,
        },
        "feature_policy": {
            "candidate_features": ["income"],
            "protected_columns": ["customer_id", "Y_label"],
            "allow_protected_override": False,
            "protected_overrides": [],
        },
        "input": {"path": "input.csv"},
        "output": {"directory": "output"},
    }


def valid_receipt():
    return {
        "schema_version": "0.1",
        "source": "user_interaction",
        "confirmed": True,
        "product_form": "revolving",
        "repayment_type": "equal_payment",
        "scenario": "first_loan_admission",
        "task_type": "strategy_simulation",
        "field_mapping": {"confirmed": True},
        "analysis_grain": {
            "grain": "customer",
            "id_cols": ["customer_id"],
            "aggregation_rule": None,
        },
        "label": {
            "target_col": "Y_label",
            "positive_class": 1,
            "bad_definition": "DPD30_plus_MOB3",
            "maturity_rule": "mature_flag == 1",
        },
        "amount_metric": {
            "enabled": True,
            "numerator": "overdue_unpaid_principal",
            "denominator": "drawdown_amount",
            "formula": "sum(numerator) / sum(denominator)",
            "filter": "mature_flag == 1",
        },
    }


class ContractValidationTests(unittest.TestCase):
    def setUp(self):
        self.config = valid_config()
        self.receipt = valid_receipt()
        self.data = pd.DataFrame(
            {
                "customer_id": ["C1", "C2"],
                "Y_label": [0, 1],
                "income": [1000, 800],
                "sample_date": ["2026-01-01", "2026-01-02"],
                "mature_flag": [1, 1],
                "overdue_unpaid_principal": [0, 50],
                "drawdown_amount": [100, 100],
            }
        )

    def assert_contract_error(self, config=None, receipt=None, data=None, text=""):
        with self.assertRaisesRegex(ContractValidationError, text):
            validate_run_contract(
                config or self.config,
                receipt if receipt is not None else self.receipt,
                data if data is not None else self.data,
            )

    def test_requires_user_confirmation_receipt(self):
        with self.assertRaisesRegex(ContractValidationError, "确认凭证"):
            validate_run_contract(self.config, None, self.data)

    def test_rejects_unconfirmed_field_mapping(self):
        config = copy.deepcopy(self.config)
        config["field_mapping"]["confirmed"] = False
        self.assert_contract_error(config=config, text="字段映射")

    def test_requires_receipt_path_in_config(self):
        config = copy.deepcopy(self.config)
        config.pop("confirmation")
        self.assert_contract_error(config=config, text="确认凭证路径")

    def test_rejects_receipt_with_different_task_context(self):
        receipt = copy.deepcopy(self.receipt)
        receipt["scenario"] = "reloan"
        self.assert_contract_error(receipt=receipt, text="应用场景")

    def test_rejects_missing_analysis_grain(self):
        config = copy.deepcopy(self.config)
        config["analysis_grain"]["grain"] = None
        self.assert_contract_error(config=config, text="分析颗粒度")

    def test_rejects_non_unique_analysis_unit(self):
        duplicate_data = pd.concat([self.data, self.data.iloc[[0]]], ignore_index=True)
        self.assert_contract_error(data=duplicate_data, text="不唯一")

    def test_requires_aggregation_when_grains_differ(self):
        config = copy.deepcopy(self.config)
        config["analysis_grain"]["label_grain"] = "loan"
        config["analysis_grain"]["aggregation_rule"] = None
        self.assert_contract_error(config=config, text="聚合规则")

    def test_rejects_incomplete_amount_definition(self):
        config = copy.deepcopy(self.config)
        config["amount_metric"]["denominator"] = None
        self.assert_contract_error(config=config, text="金额口径")

    def test_rejects_protected_candidate_feature(self):
        config = copy.deepcopy(self.config)
        config["feature_policy"]["candidate_features"] = ["Y_label"]
        self.assert_contract_error(config=config, text="保护列")

    def test_valid_contract_generates_analysis_unit_and_manifest(self):
        validated = validate_run_contract(self.config, self.receipt, self.data)
        unit_id = build_analysis_unit_id(self.data, ["customer_id"])
        self.assertEqual(unit_id.tolist(), ["C1", "C2"])
        self.assertIsNone(safe_div(1, 0))

        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest_path = write_run_manifest(
                Path(tmp_dir),
                self.config,
                self.receipt,
                validated,
                input_row_count=len(self.data),
                output_files=["summary.csv"],
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertTrue(manifest["confirmation_receipt"]["confirmed"])
        self.assertEqual(manifest["confirmation_receipt_path"], "confirmation.json")
        self.assertEqual(manifest["analysis_grain"]["grain"], "customer")

    def test_validate_contract_cli_writes_manifest(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir:
            directory = Path(tmp_dir)
            config_path = directory / "config.yaml"
            receipt_path = directory / "confirmation.json"
            input_path = directory / "input.csv"
            output_dir = directory / "output"
            config = copy.deepcopy(self.config)
            config["confirmation"]["receipt_path"] = str(receipt_path)
            config["input"]["path"] = str(input_path)
            with config_path.open("w", encoding="utf-8") as file:
                yaml.safe_dump(config, file, allow_unicode=True, sort_keys=False)
            receipt_path.write_text(json.dumps(self.receipt, ensure_ascii=False), encoding="utf-8")
            self.data.to_csv(input_path, index=False, encoding="utf-8-sig")

            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts/validate_contract.py"),
                    "--config", str(config_path),
                    "--confirmation", str(receipt_path),
                    "--input", str(input_path),
                    "--output-dir", str(output_dir),
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((output_dir / "run_manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
