"""策略效果与 Swap 评估入口。"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

try:
    from scripts.utils.contracts import ContractValidationError, load_confirmation_receipt, load_yaml, validate_run_contract
    from scripts.utils.metrics import safe_rate
    from scripts.utils.output_contract import STAGE_SPECS, OutputContractError, load_stage_bundle, validate_run_directory, write_stage_bundle
    from scripts.utils.rule_engine import RuleParseError, build_swap_matrix, evaluate_rule
except ModuleNotFoundError:
    from utils.contracts import ContractValidationError, load_confirmation_receipt, load_yaml, validate_run_contract
    from utils.metrics import safe_rate
    from utils.output_contract import STAGE_SPECS, OutputContractError, load_stage_bundle, validate_run_directory, write_stage_bundle
    from utils.rule_engine import RuleParseError, build_swap_matrix, evaluate_rule


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="策略效果与 Swap 前置校验和固定产物计算")
    parser.add_argument("--config", required=True, help="UTF-8 YAML 运行配置")
    parser.add_argument("--confirmation", required=True, help="用户确认凭证 JSON")
    parser.add_argument("--input", required=True, help="UTF-8 CSV 输入数据")
    parser.add_argument("--run-dir", required=True, help="固定阶段目录包的运行根目录")
    return parser.parse_args()


def _stage2_dir(run_dir: str | Path) -> Path:
    return Path(load_stage_bundle(run_dir, "02")["directory"])


def _new_reject_mask_from_rules(run_dir: str | Path, data: pd.DataFrame) -> pd.Series:
    stage2 = _stage2_dir(run_dir)
    selected = pd.read_csv(stage2 / "selected_rule_set.csv", encoding="utf-8-sig")
    ranked = pd.read_csv(stage2 / "lift_ranked_rules.csv", encoding="utf-8-sig")
    if selected.empty:
        return pd.Series(False, index=data.index)
    merged = selected.merge(ranked[["rule_id", "rule_expression"]], on="rule_id", how="left")
    reject = pd.Series(False, index=data.index)
    for _, row in merged.iterrows():
        try:
            reject = reject | evaluate_rule(str(row["rule_expression"]), data)
        except RuleParseError as error:
            raise OutputContractError(f"selected rule cannot be evaluated for strategy: {row['rule_id']}: {error}") from error
    return reject.astype(bool)


def _strategy_summary(run_dir: str | Path, data: pd.DataFrame, config: dict) -> list[dict]:
    reject = _new_reject_mask_from_rules(run_dir, data)
    sample_count = len(data)
    reject_count = int(reject.sum())
    return [
        {
            "strategy_name": "stage_02_selected_rule_set",
            "population": config.get("strategy_evaluation", {}).get("comparison_population")
            or config.get("sample_scope", {}).get("population"),
            "sample_count": sample_count,
            "reject_rate": safe_rate(reject_count, sample_count),
            "approval_rate": safe_rate(sample_count - reject_count, sample_count),
            "metric_status": "generated",
            "notes": "基于阶段 2 入选规则复算新策略拒绝；不生成上线建议",
        }
    ]


def _strategy_layer_effect(run_dir: str | Path) -> list[dict]:
    stage2 = _stage2_dir(run_dir)
    funnel = pd.read_csv(stage2 / "cascade_funnel.csv", encoding="utf-8-sig")
    rows = []
    for _, row in funnel.iterrows():
        input_count = int(row["input_count"]) if pd.notna(row.get("input_count")) else 0
        hit_count = int(row["hit_reject_count"]) if pd.notna(row.get("hit_reject_count")) else 0
        rows.append(
            {
                "execution_order": row.get("execution_order"),
                "rule_id": row.get("rule_id"),
                "sample_count": input_count,
                "reject_rate": safe_rate(hit_count, input_count),
                "metric_status": "generated",
                "notes": "阶段 2 级联漏斗边际层效果",
            }
        )
    return rows


def _swap_not_available_rows(data: pd.DataFrame, reason: str) -> tuple[dict, dict]:
    rows = {
        "swap_summary.csv": [
            {
                "old_decision": "not_available",
                "new_decision": "not_available",
                "swap_group": "not_available",
                "sample_count": len(data),
                "population_rate": 1.0 if len(data) else None,
                "risk_observability": "not_available",
                "risk_estimation_status": reason,
            }
        ],
        "swap_segment_detail.csv": [],
        "swap_in_risk_estimate.csv": [
            {
                "estimation_method": "not_available",
                "method_status": "not_available",
                "score_or_rule_band": None,
                "sample_count": 0,
                "estimated_bad_rate": None,
                "estimated_bad_count": None,
                "assumption": None,
                "reason": reason,
            }
        ],
        "swap_in_coverage.csv": [
            {
                "estimation_method": "not_available",
                "coverage_status": "not_available",
                "eligible_count": 0,
                "covered_count": 0,
                "coverage_rate": None,
                "reason": reason,
            }
        ],
    }
    statuses = {
        name: {"status": "not_available", "reason": reason}
        for name in ("swap_summary.csv", "swap_segment_detail.csv", "swap_in_risk_estimate.csv", "swap_in_coverage.csv")
    }
    return rows, statuses


def _swap_rows(data: pd.DataFrame, config: dict) -> tuple[dict, dict]:
    evaluation = config.get("strategy_evaluation", {})
    if not evaluation.get("compare_with_old_strategy"):
        return _swap_not_available_rows(data, "未启用新旧策略比较")
    old_col = evaluation.get("old_decision_col")
    new_col = evaluation.get("new_decision_col")
    if old_col not in data.columns or new_col not in data.columns:
        return _swap_not_available_rows(data, "缺少旧策略或新策略决策字段")
    observability = evaluation.get("swap_in_observability") or "unobservable"
    summary, detail = build_swap_matrix(
        data,
        old_col,
        new_col,
        segment_columns=evaluation.get("segment_columns") or [],
        swap_in_observability=observability,
    )
    swap_in_count = sum(int(row["sample_count"]) for row in summary if row["swap_group"] == "swap_in")
    if observability == "estimated":
        method = evaluation.get("swap_in_estimation_method") or "not_confirmed"
        method_status = "not_available"
        reason = "P1 仅登记已确认估计方法；具体风险估计算法未在本轮实现"
    else:
        method = "unobservable"
        method_status = "unobservable"
        reason = "swap_in 无直接成熟表现，且本次确认不可观测"
    rows = {
        "swap_summary.csv": summary,
        "swap_segment_detail.csv": detail,
        "swap_in_risk_estimate.csv": [
            {
                "estimation_method": method,
                "method_status": method_status,
                "score_or_rule_band": "swap_in_total",
                "sample_count": swap_in_count,
                "estimated_bad_rate": None,
                "estimated_bad_count": None,
                "assumption": None,
                "reason": reason,
            }
        ],
        "swap_in_coverage.csv": [
            {
                "estimation_method": method,
                "coverage_status": method_status,
                "eligible_count": swap_in_count,
                "covered_count": 0,
                "coverage_rate": 0 if swap_in_count else None,
                "reason": reason,
            }
        ],
    }
    statuses = {}
    if method_status != "unobservable":
        statuses["swap_in_risk_estimate.csv"] = {"status": "not_available", "reason": reason}
        statuses["swap_in_coverage.csv"] = {"status": "not_available", "reason": reason}
    return rows, statuses


def build_strategy_artifacts(run_dir: str | Path, data: pd.DataFrame, config: dict) -> tuple[dict, dict]:
    rows = {
        "strategy_effect_summary.csv": _strategy_summary(run_dir, data, config),
        "strategy_layer_effect.csv": _strategy_layer_effect(run_dir),
    }
    swap_rows, statuses = _swap_rows(data, config)
    rows.update(swap_rows)
    return rows, statuses


def main() -> int:
    args = _parse_args()
    try:
        config = load_yaml(args.config)
        if config.get("task", {}).get("task_type") != "strategy_evaluation":
            raise ContractValidationError("策略效果与 Swap 评估只接受 strategy_evaluation 任务")
        receipt = load_confirmation_receipt(args.confirmation)
        data = pd.read_csv(args.input, encoding="utf-8-sig")
        validate_run_contract(config, receipt, data)
        run_dir = validate_run_directory(config, args.run_dir)
        rows, statuses = build_strategy_artifacts(run_dir, data, config)
        write_stage_bundle(
            run_dir,
            "03",
            config,
            receipt,
            artifact_rows=rows,
            artifact_statuses=statuses,
            quality_gates={"input_contract": "passed", "swap_group_exhaustiveness": "passed"},
            limitations=["阶段 3 仅计算固定策略效果与 Swap 聚合产物；不生成上线建议。"],
        )
    except (ContractValidationError, OutputContractError, OSError, RuntimeError, ValueError) as error:
        print(f"策略效果与 Swap 评估失败: {error}")
        return 2
    print(f"策略效果与 Swap 评估固定阶段产物包已写入: {Path(args.run_dir) / STAGE_SPECS['03']['directory']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
