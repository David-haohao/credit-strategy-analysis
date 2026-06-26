"""规则挖掘入口：最小数值阈值候选生成。"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    from scripts.utils.contracts import ContractValidationError, load_confirmation_receipt, load_yaml, validate_run_contract
    from scripts.utils.metrics import evaluate_binary_rule
    from scripts.utils.output_contract import STAGE_SPECS, OutputContractError, load_stage_bundle, validate_run_directory, write_stage_bundle
    from scripts.utils.rule_engine import RuleParseError, evaluate_rule
except ModuleNotFoundError:
    from utils.contracts import ContractValidationError, load_confirmation_receipt, load_yaml, validate_run_contract
    from utils.metrics import evaluate_binary_rule
    from utils.output_contract import STAGE_SPECS, OutputContractError, load_stage_bundle, validate_run_directory, write_stage_bundle
    from utils.rule_engine import RuleParseError, evaluate_rule


_SAFE_FEATURE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="规则挖掘前置校验与最小数值阈值候选生成")
    parser.add_argument("--config", required=True, help="UTF-8 YAML 运行配置")
    parser.add_argument("--confirmation", required=True, help="用户确认凭证 JSON")
    parser.add_argument("--input", required=True, help="UTF-8 CSV 输入数据")
    parser.add_argument("--run-dir", required=True, help="固定阶段目录包的运行根目录")
    return parser.parse_args()


def _format_cut(value: float) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.12g}"


def _parse_value(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _configured_features(config: dict) -> list[str]:
    policy = config.get("feature_policy", {})
    protected = {str(item).lower() for item in (policy.get("protected_columns") or [])}
    excluded = {str(item).lower() for item in (policy.get("exclude_features") or [])}
    tokens = [str(item).lower() for item in (policy.get("excluded_name_tokens") or []) if str(item).strip()]
    result = []
    for feature in policy.get("candidate_features") or []:
        name = str(feature).strip()
        lowered = name.lower()
        if not name or lowered in protected or lowered in excluded or any(token in lowered for token in tokens):
            continue
        result.append(name)
    return result


def _cuts_for_feature(series: pd.Series, sources: Iterable[str]) -> list[float]:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return []
    cuts: list[float] = []
    for source in sources:
        text = str(source).strip().lower()
        if text.startswith("quantile:"):
            q = _parse_value(text.split(":", 1)[1])
            if q is None or q < 0 or q > 1:
                continue
            cuts.append(float(numeric.quantile(q)))
        elif text.startswith("value:"):
            value = _parse_value(text.split(":", 1)[1])
            if value is not None:
                cuts.append(float(value))
    deduped = sorted({cut for cut in cuts if pd.notna(cut)})
    return deduped


def _candidate_status(metrics: dict, min_hit_count: int, min_hit_rate: float) -> str:
    if int(metrics["hit_count"]) < min_hit_count:
        return "filtered_min_hit_count"
    coverage = metrics["coverage_rate"]
    if coverage is None or float(coverage) < min_hit_rate:
        return "filtered_min_hit_rate"
    return "candidate"


def _rule_row(rule_id: str, feature: str, expression: str, data: pd.DataFrame, target_col: str, positive_class, min_hit_count: int, min_hit_rate: float) -> dict:
    try:
        hit = evaluate_rule(expression, data)
    except RuleParseError as error:
        raise OutputContractError(f"generated rule cannot be evaluated: {expression}: {error}") from error
    metrics = evaluate_binary_rule(hit, data[target_col], positive_class=positive_class)
    return {
        "rule_id": rule_id,
        "feature_name": feature,
        "rule_expression": expression,
        "hit_count": metrics["hit_count"],
        "coverage_rate": metrics["coverage_rate"],
        "reject_rate": metrics["reject_rate"],
        "non_hit_reject_rate": metrics["non_hit_reject_rate"],
        "reject_lift": metrics["reject_lift"],
        "reject_capture_rate": metrics["reject_capture_rate"],
        "pass_injury_rate": metrics["pass_injury_rate"],
        "candidate_status": _candidate_status(metrics, min_hit_count, min_hit_rate),
        "stability_status": "未评估（未做时间外验证）",
    }


def build_rule_mining_artifacts(data: pd.DataFrame, config: dict) -> tuple[dict, dict]:
    features = _configured_features(config)
    rule_config = config.get("rule_mining", {})
    cut_sources = list(rule_config.get("numeric_cut_sources") or [])
    min_hit_count = int(rule_config.get("min_hit_count") or 1)
    min_hit_rate = float(rule_config.get("min_hit_rate") or 0)
    target_col = config.get("label", {}).get("target_col") or config.get("columns", {}).get("target_col")
    positive_class = config.get("label", {}).get("positive_class", 1)
    if target_col not in data.columns:
        raise OutputContractError("target column missing for rule mining")

    feature_rows = []
    candidate_rows = []
    for feature in features:
        if feature not in data.columns:
            feature_rows.append(
                {
                    "feature_name": feature,
                    "feature_status": "not_available",
                    "screening_reason": "feature_column_missing",
                    "iv": None,
                    "coverage_count": None,
                    "monotonicity": "not_evaluated",
                    "stability_status": "未评估（未做时间外验证）",
                }
            )
            continue
        if not _SAFE_FEATURE.fullmatch(feature):
            feature_rows.append(
                {
                    "feature_name": feature,
                    "feature_status": "not_available",
                    "screening_reason": "feature_name_not_supported_by_safe_rule_syntax",
                    "iv": None,
                    "coverage_count": int(data[feature].notna().sum()),
                    "monotonicity": "not_evaluated",
                    "stability_status": "未评估（未做时间外验证）",
                }
            )
            continue
        numeric = pd.to_numeric(data[feature], errors="coerce")
        if numeric.notna().sum() == 0:
            feature_rows.append(
                {
                    "feature_name": feature,
                    "feature_status": "not_available",
                    "screening_reason": "non_numeric_feature_not_supported_in_p1_5",
                    "iv": None,
                    "coverage_count": int(data[feature].notna().sum()),
                    "monotonicity": "not_evaluated",
                    "stability_status": "未评估（未做时间外验证）",
                }
            )
            continue
        cuts = _cuts_for_feature(numeric, cut_sources)
        feature_rows.append(
            {
                "feature_name": feature,
                "feature_status": "generated" if cuts else "not_available",
                "screening_reason": "minimal_numeric_cut_candidates_no_iv" if cuts else "missing_confirmed_numeric_cut_sources",
                "iv": None,
                "coverage_count": int(numeric.notna().sum()),
                "monotonicity": "not_evaluated",
                "stability_status": "未评估（未做时间外验证）",
            }
        )
        for cut_index, cut in enumerate(cuts, start=1):
            formatted = _format_cut(cut)
            for direction, operator_text in (("ge", ">="), ("lt", "<")):
                expression = f"{feature} {operator_text} {formatted}"
                candidate_rows.append(
                    _rule_row(
                        f"{feature}__{direction}__{cut_index}",
                        feature,
                        expression,
                        data,
                        target_col,
                        positive_class,
                        min_hit_count,
                        min_hit_rate,
                    )
                )
        if numeric.isna().any():
            candidate_rows.append(
                _rule_row(
                    f"{feature}__missing",
                    feature,
                    f"{feature} is missing",
                    data,
                    target_col,
                    positive_class,
                    min_hit_count,
                    min_hit_rate,
                )
            )

    reason_no_cut = "缺少确认切点来源" if not cut_sources else "未生成可用候选规则"
    statuses = {
        "bin_iv_detail.csv": {"status": "not_available", "reason": "P1.5 未执行完整 toad 分箱/WOE/IV"},
        "cart_path_candidates.csv": {"status": "not_applicable", "reason": "P1.5 未执行 CART 路径生成"},
        "rule_stability.csv": {"status": "not_applicable", "reason": "未评估（未做时间外验证）"},
    }
    if not candidate_rows:
        statuses["single_rule_candidates.csv"] = {"status": "not_available", "reason": reason_no_cut}
    rows = {
        "feature_screening.csv": feature_rows,
        "single_rule_candidates.csv": candidate_rows,
        "rule_stability.csv": [
            {
                "rule_id": None,
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
        if config.get("task", {}).get("task_type") != "rule_mining":
            raise ContractValidationError("规则挖掘只接受 rule_mining 任务")
        receipt = load_confirmation_receipt(args.confirmation)
        data = pd.read_csv(args.input, encoding="utf-8-sig")
        validate_run_contract(config, receipt, data)
        run_dir = validate_run_directory(config, args.run_dir)
        load_stage_bundle(run_dir, "00")
        rows, statuses = build_rule_mining_artifacts(data, config)
        write_stage_bundle(
            run_dir,
            "01",
            config,
            receipt,
            artifact_rows=rows,
            artifact_statuses=statuses,
            quality_gates={"input_contract": "passed", "minimal_candidate_generation": "passed"},
            limitations=["阶段 1 本轮仅执行确认切点的最小数值阈值候选生成；未执行完整 toad 分箱/WOE/IV 或 CART。"],
        )
    except (ContractValidationError, OutputContractError, OSError, RuntimeError, ValueError) as error:
        print(f"规则挖掘失败: {error}")
        return 2
    print(f"规则挖掘固定阶段产物包已写入: {Path(args.run_dir) / STAGE_SPECS['01']['directory']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
