"""Lift TopN 级联规则组合入口。"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

try:
    from scripts.utils.contracts import ContractValidationError, load_confirmation_receipt, load_yaml, validate_run_contract
    from scripts.utils.output_contract import STAGE_SPECS, OutputContractError, load_stage_bundle, validate_run_directory, write_stage_bundle
    from scripts.utils.rule_engine import RuleParseError, compute_cascade_funnel, compute_rule_overlap, evaluate_rule
except ModuleNotFoundError:
    from utils.contracts import ContractValidationError, load_confirmation_receipt, load_yaml, validate_run_contract
    from utils.output_contract import STAGE_SPECS, OutputContractError, load_stage_bundle, validate_run_directory, write_stage_bundle
    from utils.rule_engine import RuleParseError, compute_cascade_funnel, compute_rule_overlap, evaluate_rule


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lift TopN 规则组合前置校验与级联漏斗计算")
    parser.add_argument("--config", required=True, help="UTF-8 YAML 运行配置")
    parser.add_argument("--confirmation", required=True, help="用户确认凭证 JSON")
    parser.add_argument("--input", required=True, help="UTF-8 CSV 输入数据")
    parser.add_argument("--run-dir", required=True, help="固定阶段目录包的运行根目录")
    return parser.parse_args()


def _load_stage1_candidates(run_dir: str | Path) -> pd.DataFrame:
    bundle = load_stage_bundle(run_dir, "01")
    stage_dir = Path(bundle["directory"])
    frames = []
    for artifact in ("single_rule_candidates.csv", "cart_path_candidates.csv"):
        path = stage_dir / artifact
        frame = pd.read_csv(path, encoding="utf-8-sig")
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=STAGE_SPECS["01"]["artifacts"]["single_rule_candidates.csv"])
    candidates = pd.concat(frames, ignore_index=True)
    candidates = candidates.dropna(subset=["rule_id", "rule_expression"]).copy()
    if candidates.empty:
        return candidates
    status = candidates["candidate_status"].fillna("").astype(str).str.lower()
    return candidates[~status.isin({"rejected", "failed", "not_candidate", "not_available"})].copy()


def _rank_candidates(candidates: pd.DataFrame, top_n: int) -> tuple[list[dict], list[dict], pd.DataFrame]:
    ranked = candidates.copy()
    ranked["reject_lift_numeric"] = pd.to_numeric(ranked["reject_lift"], errors="coerce")
    ranked = ranked.sort_values(
        by=["reject_lift_numeric", "coverage_rate", "rule_id"],
        ascending=[False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    ranked_rows = []
    selected_rows = []
    for index, row in ranked.iterrows():
        rank = index + 1
        selected = rank <= top_n
        ranked_rows.append(
            {
                "rank": rank,
                "rule_id": row["rule_id"],
                "feature_name": row.get("feature_name"),
                "rule_expression": row["rule_expression"],
                "reject_lift": row.get("reject_lift"),
                "candidate_status": row.get("candidate_status") or "candidate",
                "selection_reason": "selected_by_confirmed_top_n" if selected else "not_selected_beyond_top_n",
            }
        )
        if selected:
            selected_rows.append(
                {
                    "execution_order": rank,
                    "rule_id": row["rule_id"],
                    "logical_feature_group": row.get("feature_name"),
                    "decision_action": "reject",
                    "selection_basis": "lift_desc_top_n",
                    "selection_reason": "selected_by_confirmed_top_n",
                }
            )
    return ranked_rows, selected_rows, ranked.head(top_n).copy()


def build_rule_combination_artifacts(run_dir: str | Path, data: pd.DataFrame, config: dict) -> tuple[dict, dict]:
    candidates = _load_stage1_candidates(run_dir)
    top_n = int(config.get("rule_combination", {}).get("top_n"))
    statuses = {"cascade_oot.csv": {"status": "not_applicable", "reason": "未评估（未做时间外验证）"}}
    if candidates.empty:
        reason = "阶段 1 未提供可组合的候选规则"
        statuses.update(
            {
                "lift_ranked_rules.csv": {"status": "not_available", "reason": reason},
                "selected_rule_set.csv": {"status": "not_available", "reason": reason},
                "cascade_funnel.csv": {"status": "not_available", "reason": reason},
                "rule_overlap.csv": {"status": "not_available", "reason": reason},
            }
        )
        return {}, statuses

    ranked_rows, selected_rows, selected = _rank_candidates(candidates, top_n)
    rule_masks = {}
    for _, row in selected.iterrows():
        try:
            rule_masks[str(row["rule_id"])] = evaluate_rule(str(row["rule_expression"]), data)
        except RuleParseError as error:
            raise OutputContractError(f"selected rule cannot be evaluated: {row['rule_id']}: {error}") from error
    ordered_rule_ids = [str(row["rule_id"]) for _, row in selected.iterrows()]
    rows = {
        "lift_ranked_rules.csv": ranked_rows,
        "selected_rule_set.csv": selected_rows,
        "cascade_funnel.csv": compute_cascade_funnel(ordered_rule_ids, rule_masks, population_count=len(data)),
        "rule_overlap.csv": compute_rule_overlap(ordered_rule_ids, rule_masks),
        "cascade_oot.csv": [
            {
                "stability_status": "未评估（未做时间外验证）",
                "evaluation_window": None,
                "metric_name": None,
                "metric_value": None,
                "reason": "未做时间外验证",
            }
        ],
    }
    return rows, statuses


def main() -> int:
    args = _parse_args()
    try:
        config = load_yaml(args.config)
        if config.get("task", {}).get("task_type") != "rule_combination":
            raise ContractValidationError("规则组合只接受 rule_combination 任务")
        receipt = load_confirmation_receipt(args.confirmation)
        data = pd.read_csv(args.input, encoding="utf-8-sig")
        validate_run_contract(config, receipt, data)
        run_dir = validate_run_directory(config, args.run_dir)
        rows, statuses = build_rule_combination_artifacts(run_dir, data, config)
        write_stage_bundle(
            run_dir,
            "02",
            config,
            receipt,
            artifact_rows=rows,
            artifact_statuses=statuses,
            quality_gates={"input_contract": "passed", "cascade_semantics": "passed"},
            limitations=["阶段 2 仅执行已登记候选规则的 Lift 排序、级联漏斗和重叠计算；不重新挖掘规则。"],
        )
    except (ContractValidationError, OutputContractError, OSError, RuntimeError, ValueError) as error:
        print(f"规则组合失败: {error}")
        return 2
    print(f"规则组合固定阶段产物包已写入: {Path(args.run_dir) / STAGE_SPECS['02']['directory']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
