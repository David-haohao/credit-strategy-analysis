"""Validate inputs and create the stage-00 fixed output bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

try:
    from scripts.utils.contracts import ContractValidationError, load_confirmation_receipt, load_yaml, validate_run_contract
    from scripts.utils.output_contract import OutputContractError, initialize_run_bundle, write_stage_bundle
except ModuleNotFoundError:  # Supports direct execution from scripts/.
    from utils.contracts import ContractValidationError, load_confirmation_receipt, load_yaml, validate_run_contract
    from utils.output_contract import OutputContractError, initialize_run_bundle, write_stage_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验信用策略分析输入契约，并写入阶段 00 目录包")
    parser.add_argument("--config", required=True, help="UTF-8 YAML 运行配置")
    parser.add_argument("--confirmation", required=True, help="UTF-8 JSON 用户确认凭证")
    parser.add_argument("--input", required=True, help="UTF-8 CSV 输入数据")
    parser.add_argument("--run-dir", required=True, help="固定阶段目录包的运行根目录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_yaml(args.config)
        receipt = load_confirmation_receipt(args.confirmation)
        data = pd.read_csv(args.input, encoding="utf-8-sig")
        validation = validate_run_contract(config, receipt, data)
        run_dir = initialize_run_bundle(args.run_dir, config, receipt, args.config, args.confirmation, args.input)
        feature_policy = config.get("feature_policy", {})
        candidates = feature_policy.get("candidate_features") or []
        excluded_features = {str(feature) for feature in (feature_policy.get("exclude_features") or [])}
        excluded_tokens = [
            str(token).strip().lower()
            for token in (feature_policy.get("excluded_name_tokens") or [])
            if str(token).strip()
        ]
        safe_candidates = [
            feature
            for feature in candidates
            if str(feature) not in excluded_features
            and not any(token in str(feature).lower() for token in excluded_tokens)
        ]
        write_stage_bundle(
            run_dir,
            "00",
            config,
            receipt,
            artifact_rows={
                "data_profile.csv": [
                    {"metric_name": "input_row_count", "metric_value": len(data), "metric_status": "generated", "notes": "原始输入行数"},
                    {"metric_name": "input_column_count", "metric_value": len(data.columns), "metric_status": "generated", "notes": "原始输入字段数"},
                ],
                "analysis_unit_check.csv": [
                    {
                        "check_name": "analysis_unit_count",
                        "status": "passed",
                        "observed_value": validation["analysis_unit_count"],
                        "expected_value": validation["analysis_unit_count"],
                        "notes": "已按确认的 id_cols 校验唯一性",
                    }
                ],
                "feature_governance.csv": [
                    {
                        "feature_name": str(feature),
                        "feature_status": "candidate",
                        "exclusion_reason": None,
                        "coverage_count": None,
                        "notes": "来源于已确认候选特征",
                    }
                    for feature in safe_candidates
                ],
            },
            quality_gates={"input_contract": "passed", "analysis_unit_uniqueness": "passed"},
            limitations=["阶段 0 仅完成数据与口径校验，不包含规则挖掘。"],
        )
    except (ContractValidationError, OutputContractError, OSError, ValueError) as error:
        print(f"契约校验失败: {error}")
        return 2
    print(f"数据与口径阶段已写入: {Path(args.run_dir) / '00_data_contract'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
