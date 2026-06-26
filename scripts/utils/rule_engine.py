"""Safe rule, cascade, overlap, and Swap helpers for fixed strategy artifacts."""

from __future__ import annotations

import operator
import re
from typing import Any, Iterable, Sequence

import pandas as pd


class RuleParseError(ValueError):
    """Raised when a rule expression is outside the supported safe subset."""


class RuleEngineNotImplementedError(NotImplementedError):
    pass


_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_.]*"
_VALUE = r"(?:'[^']*'|\"[^\"]*\"|-?\d+(?:\.\d+)?|[A-Za-z0-9_.-]+)"
_OPERATORS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}
_PASS_VALUES = {"1", "true", "pass", "passed", "approve", "approved", "accept", "accepted"}
_REJECT_VALUES = {"0", "false", "reject", "rejected", "deny", "denied", "decline", "declined"}


def _parse_value(raw: str) -> Any:
    value = raw.strip()
    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _require_column(data: pd.DataFrame, name: str) -> pd.Series:
    if name not in data.columns:
        raise RuleParseError(f"rule references missing column: {name}")
    return data[name]


def _evaluate_atomic(expression: str, data: pd.DataFrame) -> pd.Series:
    expr = expression.strip()
    missing = re.fullmatch(rf"(?P<name>{_IDENTIFIER})\s+is\s+(?P<neg>not\s+)?missing", expr, flags=re.IGNORECASE)
    if missing:
        result = _require_column(data, missing.group("name")).isna()
        return ~result if missing.group("neg") else result

    between = re.fullmatch(
        rf"(?P<name>{_IDENTIFIER})\s+between\s+(?P<lower>{_VALUE})\s+and\s+(?P<upper>{_VALUE})",
        expr,
        flags=re.IGNORECASE,
    )
    if between:
        series = _require_column(data, between.group("name"))
        lower = _parse_value(between.group("lower"))
        upper = _parse_value(between.group("upper"))
        return series.ge(lower).fillna(False) & series.le(upper).fillna(False)

    comparison = re.fullmatch(
        rf"(?P<name>{_IDENTIFIER})\s*(?P<op>>=|<=|==|!=|>|<)\s*(?P<value>{_VALUE})",
        expr,
        flags=re.IGNORECASE,
    )
    if comparison:
        series = _require_column(data, comparison.group("name"))
        value = _parse_value(comparison.group("value"))
        try:
            return _OPERATORS[comparison.group("op")](series, value).fillna(False)
        except TypeError as error:
            raise RuleParseError(f"rule comparison type mismatch: {expr}") from error

    raise RuleParseError(f"unsupported rule expression: {expr}")


def _split_and_conditions(expression: str) -> list[str]:
    parts: list[str] = []
    position = 0
    text = expression.strip()
    atomic_patterns = [
        rf"{_IDENTIFIER}\s+between\s+{_VALUE}\s+and\s+{_VALUE}",
        rf"{_IDENTIFIER}\s+is\s+(?:not\s+)?missing",
        rf"{_IDENTIFIER}\s*(?:>=|<=|==|!=|>|<)\s*{_VALUE}",
    ]
    while position < len(text):
        if position:
            separator = re.match(r"\s+and\s+", text[position:], flags=re.IGNORECASE)
            if not separator:
                raise RuleParseError(f"unsupported rule expression: {expression}")
            position += separator.end()
        matched = None
        for pattern in atomic_patterns:
            candidate = re.match(pattern, text[position:], flags=re.IGNORECASE)
            if candidate:
                matched = candidate.group(0)
                break
        if matched is None:
            raise RuleParseError(f"unsupported rule expression: {expression}")
        parts.append(matched.strip())
        position += len(matched)
    return parts


def evaluate_rule(expression: str, data: pd.DataFrame) -> pd.Series:
    """Evaluate a confirmed simple rule expression without Python eval."""
    if not isinstance(expression, str) or not expression.strip():
        raise RuleParseError("rule expression is empty")
    if re.search(r"__|import|exec|eval|lambda|;|\|{2}|&{2}|\(|\)|\s+or\s+", expression, flags=re.IGNORECASE):
        raise RuleParseError("rule expression contains forbidden syntax")
    parts = _split_and_conditions(expression)
    result = pd.Series(True, index=data.index)
    for part in parts:
        result = result & _evaluate_atomic(part, data).reindex(data.index, fill_value=False)
    return result.fillna(False).astype(bool)


def compute_cascade_funnel(
    ordered_rule_ids: Sequence[str],
    rule_masks: dict[str, pd.Series],
    population_count: int | None = None,
) -> list[dict[str, Any]]:
    """Compute sequential reject counts for already ordered rules."""
    if not ordered_rule_ids:
        return []
    first_mask = rule_masks[ordered_rule_ids[0]]
    index = first_mask.index
    population = int(population_count if population_count is not None else len(index))
    remaining = pd.Series(True, index=index)
    cumulative_reject = 0
    rows: list[dict[str, Any]] = []
    for order, rule_id in enumerate(ordered_rule_ids, start=1):
        mask = rule_masks[rule_id].reindex(index, fill_value=False).astype(bool)
        input_count = int(remaining.sum())
        marginal_hit = remaining & mask
        hit_count = int(marginal_hit.sum())
        cumulative_reject += hit_count
        remaining = remaining & ~mask
        rows.append(
            {
                "execution_order": order,
                "rule_id": rule_id,
                "input_count": input_count,
                "hit_reject_count": hit_count,
                "remaining_pass_count": int(remaining.sum()),
                "cumulative_reject_rate": cumulative_reject / population if population else None,
                "stability_status": "未评估（未做时间外验证）",
            }
        )
    return rows


def compute_rule_overlap(ordered_rule_ids: Sequence[str], rule_masks: dict[str, pd.Series]) -> list[dict[str, Any]]:
    """Compute pairwise rule overlap as Jaccard intersection over union."""
    rows: list[dict[str, Any]] = []
    for left_index, left_id in enumerate(ordered_rule_ids):
        left = rule_masks[left_id].astype(bool)
        for right_id in ordered_rule_ids[left_index + 1 :]:
            right = rule_masks[right_id].reindex(left.index, fill_value=False).astype(bool)
            intersection = int((left & right).sum())
            union = int((left | right).sum())
            rows.append(
                {
                    "rule_id_a": left_id,
                    "rule_id_b": right_id,
                    "overlap_count": intersection,
                    "overlap_rate": intersection / union if union else 0,
                    "notes": "jaccard_intersection_over_union",
                }
            )
    return rows


def _normalize_decision(value: Any) -> str:
    if pd.isna(value):
        return "missing"
    key = str(value).strip().lower()
    if key in _PASS_VALUES:
        return "pass"
    if key in _REJECT_VALUES:
        return "reject"
    return "missing"


def _swap_group(old: str, new: str) -> str:
    if old == "pass" and new == "pass":
        return "both_pass"
    if old == "pass" and new == "reject":
        return "swap_out"
    if old == "reject" and new == "pass":
        return "swap_in"
    if old == "reject" and new == "reject":
        return "both_reject"
    return "missing_decision"


def build_swap_matrix(
    data: pd.DataFrame,
    old_decision_col: str,
    new_decision_col: str,
    *,
    segment_columns: Iterable[str] | None = None,
    swap_in_observability: str = "unobservable",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build mutually exclusive old/new strategy decision groups."""
    if old_decision_col not in data.columns or new_decision_col not in data.columns:
        missing = [column for column in (old_decision_col, new_decision_col) if column not in data.columns]
        raise RuleParseError(f"decision column missing: {', '.join(missing)}")
    frame = data.copy()
    frame["_old_norm"] = frame[old_decision_col].map(_normalize_decision)
    frame["_new_norm"] = frame[new_decision_col].map(_normalize_decision)
    frame["_swap_group"] = [_swap_group(old, new) for old, new in zip(frame["_old_norm"], frame["_new_norm"])]
    total = len(frame)
    rows: list[dict[str, Any]] = []
    order = ["both_pass", "both_reject", "swap_in", "swap_out", "missing_decision"]
    for group in order:
        group_frame = frame[frame["_swap_group"] == group]
        if group_frame.empty and group == "missing_decision":
            continue
        if group == "swap_in":
            risk_observability = swap_in_observability
            risk_status = "estimated" if swap_in_observability == "estimated" else "unobservable"
        elif group == "missing_decision":
            risk_observability = "not_available"
            risk_status = "decision_missing_or_unknown"
        elif group == "both_reject":
            risk_observability = "decision_only"
            risk_status = "not_directly_observed"
        else:
            risk_observability = "direct_if_mature_label_available"
            risk_status = "observable_if_label_available"
        old_value = "missing_or_unknown" if group == "missing_decision" else group.split("_")[0]
        new_value = "missing_or_unknown" if group == "missing_decision" else group.split("_")[-1]
        if group == "swap_in":
            old_value, new_value = "reject", "pass"
        if group == "swap_out":
            old_value, new_value = "pass", "reject"
        if group == "both_pass":
            old_value, new_value = "pass", "pass"
        if group == "both_reject":
            old_value, new_value = "reject", "reject"
        rows.append(
            {
                "old_decision": old_value,
                "new_decision": new_value,
                "swap_group": group,
                "sample_count": int(len(group_frame)),
                "population_rate": len(group_frame) / total if total else None,
                "risk_observability": risk_observability,
                "risk_estimation_status": risk_status,
            }
        )

    segment_rows: list[dict[str, Any]] = []
    for segment in segment_columns or []:
        if segment not in frame.columns:
            raise RuleParseError(f"segment column missing: {segment}")
        grouped = frame.groupby(["_swap_group", segment], dropna=False).size().reset_index(name="sample_count")
        for _, item in grouped.iterrows():
            sample_count = int(item["sample_count"])
            group = str(item["_swap_group"])
            if group == "swap_in":
                risk_observability = swap_in_observability
                risk_status = "estimated" if swap_in_observability == "estimated" else "unobservable"
            else:
                risk_observability = "direct_if_mature_label_available"
                risk_status = "observable_if_label_available"
            segment_rows.append(
                {
                    "swap_group": group,
                    "segment_name": segment,
                    "segment_value": str(item[segment]),
                    "sample_count": sample_count,
                    "population_rate": sample_count / total if total else None,
                    "risk_observability": risk_observability,
                    "risk_estimation_status": risk_status,
                }
            )
    return rows, segment_rows
