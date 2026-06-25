import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.final_reporter import build_final_report
from scripts.utils.output_contract import (
    OUTPUT_CONTRACT_VERSION,
    OutputContractError,
    STAGE_SPECS,
    initialize_run_bundle,
    load_stage_bundle,
    write_stage_bundle,
)


def config_for(run_dir: Path):
    return {
        "task": {
            "product_form": "installment",
            "repayment_type": "equal_payment",
            "scenario": "first_loan_admission",
            "task_type": "strategy_evaluation",
        },
        "feature_policy": {"protected_columns": []},
        "output": {"directory": str(run_dir)},
        "final_report": {"title": "固定产物测试报告", "report_scope": "离线策略复现"},
    }


def receipt_for():
    return {
        "source": "user_interaction",
        "confirmed": True,
        "product_form": "installment",
        "repayment_type": "equal_payment",
        "scenario": "first_loan_admission",
        "task_type": "strategy_evaluation",
    }


class OutputContractTests(unittest.TestCase):
    def setUp(self):
        self.receipt = receipt_for()

    def _initialize(self, root: Path):
        input_path = root.parent / "source.csv"
        pd.DataFrame({"source_key": ["A1"], "income": [1000]}).to_csv(
            input_path, index=False, encoding="utf-8-sig"
        )
        config = config_for(root)
        config_path = root.parent / "config.yaml"
        receipt_path = root.parent / "receipt.json"
        config_path.write_text("task: {}\n", encoding="utf-8")
        receipt_path.write_text(json.dumps(self.receipt, ensure_ascii=False), encoding="utf-8")
        initialize_run_bundle(root, config, self.receipt, config_path, receipt_path, input_path)
        return config, input_path

    def test_stage_output_contract_declares_fixed_files_and_columns(self):
        expected = {
            "00": {
                "directory": "00_data_contract",
                "upstreams": [],
                "artifacts": {
                    "data_profile.csv": ["metric_name", "metric_value", "metric_status", "notes"],
                    "analysis_unit_check.csv": ["check_name", "status", "observed_value", "expected_value", "notes"],
                    "feature_governance.csv": ["feature_name", "feature_status", "exclusion_reason", "coverage_count", "notes"],
                },
            },
            "01": {
                "directory": "01_rule_mining",
                "upstreams": ["00"],
                "artifacts": {
                    "feature_screening.csv": ["feature_name", "feature_status", "screening_reason", "iv", "coverage_count", "stability_status"],
                    "bin_iv_detail.csv": ["feature_name", "bin_label", "bin_lower", "bin_upper", "good_count", "bad_count", "woe", "iv", "warning"],
                    "single_rule_candidates.csv": ["rule_id", "feature_name", "rule_expression", "hit_count", "coverage_rate", "reject_rate", "non_hit_reject_rate", "reject_lift", "reject_capture_rate", "pass_injury_rate", "candidate_status", "stability_status"],
                    "cart_path_candidates.csv": ["rule_id", "feature_name", "rule_expression", "hit_count", "coverage_rate", "reject_rate", "non_hit_reject_rate", "reject_lift", "reject_capture_rate", "pass_injury_rate", "candidate_status", "stability_status"],
                    "rule_stability.csv": ["rule_id", "stability_status", "evaluation_window", "metric_name", "metric_value", "reason"],
                },
            },
            "02": {
                "directory": "02_rule_combination",
                "upstreams": ["00", "01"],
                "artifacts": {
                    "lift_ranked_rules.csv": ["rank", "rule_id", "feature_name", "rule_expression", "reject_lift", "candidate_status", "selection_reason"],
                    "selected_rule_set.csv": ["execution_order", "rule_id", "logical_feature_group", "decision_action", "selection_basis", "selection_reason"],
                    "cascade_funnel.csv": ["execution_order", "rule_id", "input_count", "hit_reject_count", "remaining_pass_count", "cumulative_reject_rate", "stability_status"],
                    "rule_overlap.csv": ["rule_id_a", "rule_id_b", "overlap_count", "overlap_rate", "notes"],
                    "cascade_oot.csv": ["stability_status", "evaluation_window", "metric_name", "metric_value", "reason"],
                },
            },
            "03": {
                "directory": "03_strategy_evaluation",
                "upstreams": ["00", "01", "02"],
                "artifacts": {
                    "strategy_effect_summary.csv": ["strategy_name", "population", "sample_count", "reject_rate", "approval_rate", "metric_status", "notes"],
                    "strategy_layer_effect.csv": ["execution_order", "rule_id", "sample_count", "reject_rate", "metric_status", "notes"],
                    "swap_summary.csv": ["old_decision", "new_decision", "swap_group", "sample_count", "population_rate", "risk_observability", "risk_estimation_status"],
                    "swap_segment_detail.csv": ["swap_group", "segment_name", "segment_value", "sample_count", "population_rate", "risk_observability", "risk_estimation_status"],
                    "swap_in_risk_estimate.csv": ["estimation_method", "method_status", "score_or_rule_band", "sample_count", "estimated_bad_rate", "estimated_bad_count", "assumption", "reason"],
                    "swap_in_coverage.csv": ["estimation_method", "coverage_status", "eligible_count", "covered_count", "coverage_rate", "reason"],
                },
            },
            "04": {
                "directory": "04_final_report",
                "upstreams": ["00", "01", "02", "03"],
                "artifacts": {
                    "final_report.html": None,
                    "report_source_index.csv": ["section_id", "stage_id", "artifact_name", "relative_path", "sha256", "artifact_status", "limitation"],
                    "report_validation.csv": ["check_name", "status", "details"],
                },
            },
        }
        self.assertEqual(expected, STAGE_SPECS)

    def test_initialization_creates_only_auditable_root_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "run"
            config, input_path = self._initialize(root)

            self.assertTrue((root / "input_config.yaml").is_file())
            self.assertTrue((root / "confirmation_receipt.json").is_file())
            self.assertTrue((root / "run_manifest.json").is_file())
            self.assertTrue((root / "source_fingerprint.json").is_file())
            self.assertFalse((root / input_path.name).exists())
            manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["output_contract_version"], OUTPUT_CONTRACT_VERSION)
            self.assertEqual(manifest["run_directory"], str(root.resolve()))
            self.assertEqual(config["output"]["directory"], str(root))

    def test_stage_bundle_has_fixed_files_and_disallows_overwrite_or_escape(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "run"
            config, _ = self._initialize(root)
            manifest = write_stage_bundle(root, "00", config, self.receipt)
            stage_dir = root / STAGE_SPECS["00"]["directory"]

            self.assertEqual(manifest["stage_id"], "00")
            self.assertTrue((stage_dir / "stage_manifest.json").is_file())
            self.assertTrue((stage_dir / "artifact_inventory.json").is_file())
            for artifact in STAGE_SPECS["00"]["artifacts"]:
                self.assertTrue((stage_dir / artifact).is_file(), artifact)
                self.assertEqual(
                    pd.read_csv(stage_dir / artifact, encoding="utf-8-sig").columns.tolist(),
                    STAGE_SPECS["00"]["artifacts"][artifact],
                )

            with self.assertRaises(OutputContractError):
                write_stage_bundle(root, "00", config, self.receipt)
            with self.assertRaises(OutputContractError):
                write_stage_bundle(root, "00", config, self.receipt, artifact_rows={"../escape.csv": []})

    def test_stage_chain_requires_upstreams_and_is_hash_verified(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "run"
            config, _ = self._initialize(root)
            with self.assertRaisesRegex(OutputContractError, "upstream"):
                write_stage_bundle(root, "01", config, self.receipt)

            for stage_id in ("00", "01", "02", "03"):
                write_stage_bundle(root, stage_id, config, self.receipt)
            loaded = load_stage_bundle(root, "03")
            self.assertEqual(loaded["manifest"]["output_contract_version"], OUTPUT_CONTRACT_VERSION)
            self.assertEqual(loaded["manifest"]["upstream_stage_ids"], ["00", "01", "02"])

            profile = root / STAGE_SPECS["00"]["directory"] / "data_profile.csv"
            profile.write_text("metric_name\nchanged\n", encoding="utf-8")
            with self.assertRaisesRegex(OutputContractError, "hash"):
                load_stage_bundle(root, "00")

    def test_rejects_configured_field_policies_and_json_like_values_from_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "run"
            config, _ = self._initialize(root)
            config["feature_policy"] = {
                "protected_columns": ["entity_key"],
                "exclude_features": ["decision_proxy"],
                "excluded_name_tokens": ["blocked_token"],
            }
            with self.assertRaisesRegex(OutputContractError, "protected"):
                write_stage_bundle(
                    root,
                    "00",
                    config,
                    self.receipt,
                    artifact_rows={"feature_governance.csv": [{"feature_name": "entity_key"}]},
                )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "run"
            config, _ = self._initialize(root)
            with self.assertRaisesRegex(OutputContractError, "JSON"):
                write_stage_bundle(
                    root,
                    "00",
                    config,
                    self.receipt,
                    artifact_rows={"feature_governance.csv": [{"feature_name": "income", "notes": "{\"x\": 1}"}]},
                )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "run"
            config, _ = self._initialize(root)
            config["feature_policy"] = {"excluded_name_tokens": ["blocked_token"]}
            write_stage_bundle(root, "00", config, self.receipt)
            with self.assertRaisesRegex(OutputContractError, "excluded feature token"):
                write_stage_bundle(
                    root,
                    "01",
                    config,
                    self.receipt,
                    artifact_rows={
                        "single_rule_candidates.csv": [
                            {"feature_name": "income", "rule_expression": "blocked_token_score > 600"}
                        ]
                    },
                )

    def test_skill_files_do_not_hardcode_sample_specific_field_names(self):
        forbidden = [
            "".join(parts)
            for parts in [
                ("A", "dm"),
                ("Y", "_", "label"),
                ("sample", "_", "id"),
                ("borrower", "_", "no"),
                ("application", "_", "no"),
                ("customer", "_", "id"),
                ("p", "hone"),
                ("mo", "bile"),
                ("id", "_", "card"),
                ("e", "mail"),
                ("risk", "_", "data"),
                ("raw", "_", "json"),
                ("API", "_", "risk", "_", "model", "_", "result"),
                ("API", "_", "suggest", "_", "creditamt"),
            ]
        ]
        checked_suffixes = {".md", ".py", ".yaml", ".yml", ".json", ".j2"}
        ignored_files = {"design-framework-v2.md"}
        listed = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if listed.returncode == 0:
            candidates = [ROOT / relative for relative in listed.stdout.splitlines()]
        else:
            candidates = [path for path in ROOT.rglob("*") if path.is_file()]
        offenders = []
        for path in candidates:
            if path.name in ignored_files or "__pycache__" in path.parts:
                continue
            if path.suffix.lower() not in checked_suffixes:
                continue
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                pattern = rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])"
                if re.search(pattern, text, flags=re.IGNORECASE):
                    offenders.append(f"{path.relative_to(ROOT)}: {token}")
        self.assertEqual([], offenders)

    def test_final_report_uses_registered_upstream_artifacts_only(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "run"
            config, _ = self._initialize(root)
            for stage_id in ("00", "01", "02", "03"):
                write_stage_bundle(root, stage_id, config, self.receipt)

            report_path = build_final_report(root, config, self.receipt)
            report_dir = root / STAGE_SPECS["04"]["directory"]
            self.assertEqual(report_path, report_dir / "final_report.html")
            self.assertIn("固定产物测试报告", report_path.read_text(encoding="utf-8"))
            source_index = pd.read_csv(
                report_dir / "report_source_index.csv", encoding="utf-8-sig", dtype={"stage_id": str}
            )
            self.assertEqual(set(source_index["stage_id"]), {"00", "01", "02", "03"})
            self.assertTrue((report_dir / "report_validation.csv").is_file())


if __name__ == "__main__":
    unittest.main()
