import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.utils.output_contract import STAGE_SPECS, initialize_run_bundle, write_stage_bundle


def _base_config(run_dir: Path, task_type: str) -> dict:
    return {
        "confirmation": {"receipt_path": "confirmation.json"},
        "task": {
            "product_form": "installment",
            "repayment_type": "equal_payment",
            "scenario": "first_loan_admission",
            "task_type": task_type,
        },
        "sample_scope": {"population": "mature_booked"},
        "analysis_grain": {
            "grain": "application",
            "id_cols": ["entity_key"],
            "label_grain": "application",
            "feature_grain": "application",
            "output_grain": "application",
            "aggregation_rule": None,
        },
        "field_mapping": {"confirmed": True, "unmapped_required_fields": []},
        "label": {
            "target_col": "target_flag",
            "positive_class": 1,
            "bad_definition": "confirmed_bad",
            "maturity_rule": "test_mature",
        },
        "columns": {
            "id_cols": ["entity_key"],
            "target_col": "target_flag",
            "old_decision_col": "old_decision",
            "new_decision_col": "new_decision",
        },
        "feature_policy": {
            "candidate_features": ["income", "age"],
            "protected_columns": ["entity_key", "target_flag"],
        },
        "input": {"path": "input.csv"},
        "output": {"directory": str(run_dir)},
    }


def _receipt(task_type: str) -> dict:
    return {
        "source": "user_interaction",
        "confirmed": True,
        "product_form": "installment",
        "repayment_type": "equal_payment",
        "scenario": "first_loan_admission",
        "task_type": task_type,
        "field_mapping": {"confirmed": True},
        "analysis_grain": {"grain": "application", "id_cols": ["entity_key"], "aggregation_rule": None},
        "label": {
            "target_col": "target_flag",
            "positive_class": 1,
            "bad_definition": "confirmed_bad",
            "maturity_rule": "test_mature",
        },
    }


def _write_config_receipt(tmp_dir: Path, run_dir: Path, task_type: str, **extra) -> tuple[Path, Path, dict, dict]:
    config = _base_config(run_dir, task_type)
    config.update(extra)
    receipt = _receipt(task_type)
    config_path = tmp_dir / f"{task_type}.yaml"
    receipt_path = tmp_dir / f"{task_type}.json"
    config["confirmation"]["receipt_path"] = str(receipt_path)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
    return config_path, receipt_path, config, receipt


class P1CliIntegrationTests(unittest.TestCase):
    def _prepare_run(self, tmp_dir: Path):
        run_dir = tmp_dir / "run"
        input_path = tmp_dir / "input.csv"
        data = pd.DataFrame(
            {
                "entity_key": ["A", "B", "C", "D"],
                "target_flag": [1, 0, 1, 0],
                "income": [1200, 800, 1500, 700],
                "age": [35, 24, 22, 41],
                "old_decision": ["pass", "pass", "reject", "reject"],
                "new_decision": ["pass", "reject", "pass", "reject"],
            }
        )
        data.to_csv(input_path, index=False, encoding="utf-8-sig")
        config_path, receipt_path, config, receipt = _write_config_receipt(tmp_dir, run_dir, "rule_mining")
        initialize_run_bundle(run_dir, config, receipt, config_path, receipt_path, input_path)
        write_stage_bundle(run_dir, "00", config, receipt)
        write_stage_bundle(
            run_dir,
            "01",
            config,
            receipt,
            artifact_rows={
                "single_rule_candidates.csv": [
                    {
                        "rule_id": "R_income",
                        "feature_name": "income",
                        "rule_expression": "income >= 1000",
                        "hit_count": 2,
                        "coverage_rate": 0.5,
                        "reject_rate": 1.0,
                        "non_hit_reject_rate": 0.0,
                        "reject_lift": 2.0,
                        "reject_capture_rate": 1.0,
                        "pass_injury_rate": 0.0,
                        "candidate_status": "candidate",
                        "stability_status": "未评估（未做时间外验证）",
                    },
                    {
                        "rule_id": "R_age",
                        "feature_name": "age",
                        "rule_expression": "age < 30",
                        "hit_count": 2,
                        "coverage_rate": 0.5,
                        "reject_rate": 0.5,
                        "non_hit_reject_rate": 0.5,
                        "reject_lift": 1.0,
                        "reject_capture_rate": 0.5,
                        "pass_injury_rate": 0.5,
                        "candidate_status": "candidate",
                        "stability_status": "未评估（未做时间外验证）",
                    },
                ]
            },
        )
        return run_dir, input_path

    def test_rule_combiner_cli_writes_ranked_cascade_and_overlap(self):
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp_dir = Path(raw_tmp)
            run_dir, input_path = self._prepare_run(tmp_dir)
            config_path, receipt_path, _, _ = _write_config_receipt(
                tmp_dir,
                run_dir,
                "rule_combination",
                rule_combination={
                    "top_n": 2,
                    "rank_by": "lift_desc",
                    "execution_mode": "sequential_reject",
                    "tie_policy": "higher_coverage_first",
                },
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/rule_combiner.py"),
                    "--config",
                    str(config_path),
                    "--confirmation",
                    str(receipt_path),
                    "--input",
                    str(input_path),
                    "--run-dir",
                    str(run_dir),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            stage_dir = run_dir / STAGE_SPECS["02"]["directory"]
            ranked = pd.read_csv(stage_dir / "lift_ranked_rules.csv", encoding="utf-8-sig")
            funnel = pd.read_csv(stage_dir / "cascade_funnel.csv", encoding="utf-8-sig")
            overlap = pd.read_csv(stage_dir / "rule_overlap.csv", encoding="utf-8-sig")
            self.assertEqual(ranked["rule_id"].tolist(), ["R_income", "R_age"])
            self.assertEqual(funnel["hit_reject_count"].tolist(), [2, 1])
            self.assertEqual(funnel["remaining_pass_count"].tolist(), [2, 1])
            self.assertEqual(len(overlap), 1)
            self.assertEqual(int(overlap.iloc[0]["overlap_count"]), 1)

    def test_strategy_evaluator_cli_writes_swap_matrix(self):
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp_dir = Path(raw_tmp)
            run_dir, input_path = self._prepare_run(tmp_dir)
            combo_config_path, combo_receipt_path, _, _ = _write_config_receipt(
                tmp_dir,
                run_dir,
                "rule_combination",
                rule_combination={
                    "top_n": 2,
                    "rank_by": "lift_desc",
                    "execution_mode": "sequential_reject",
                    "tie_policy": "higher_coverage_first",
                },
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/rule_combiner.py"),
                    "--config",
                    str(combo_config_path),
                    "--confirmation",
                    str(combo_receipt_path),
                    "--input",
                    str(input_path),
                    "--run-dir",
                    str(run_dir),
                ],
                cwd=ROOT,
                check=True,
            )
            config_path, receipt_path, _, _ = _write_config_receipt(
                tmp_dir,
                run_dir,
                "strategy_evaluation",
                strategy_evaluation={
                    "compare_with_old_strategy": True,
                    "old_decision_col": "old_decision",
                    "new_decision_col": "new_decision",
                    "comparison_population": "mature_booked",
                    "swap_in_observability": "unobservable",
                    "segment_columns": [],
                },
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/strategy_evaluator.py"),
                    "--config",
                    str(config_path),
                    "--confirmation",
                    str(receipt_path),
                    "--input",
                    str(input_path),
                    "--run-dir",
                    str(run_dir),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            stage_dir = run_dir / STAGE_SPECS["03"]["directory"]
            swap = pd.read_csv(stage_dir / "swap_summary.csv", encoding="utf-8-sig")
            groups = dict(zip(swap["swap_group"], swap["sample_count"]))
            self.assertEqual(groups["both_pass"], 1)
            self.assertEqual(groups["swap_out"], 1)
            self.assertEqual(groups["swap_in"], 1)
            self.assertEqual(groups["both_reject"], 1)
            risk = pd.read_csv(stage_dir / "swap_in_risk_estimate.csv", encoding="utf-8-sig")
            self.assertEqual(risk.iloc[0]["method_status"], "unobservable")


if __name__ == "__main__":
    unittest.main()
