"""跨任务共享的策略评估指标函数。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .contracts import safe_div


def safe_rate(numerator: float | int | None, denominator: float | int | None) -> float | None:
    """Safely calculate a rate and return None when the denominator is empty."""
    return safe_div(numerator, denominator)


def lift(hit_bad_rate: float | None, overall_bad_rate: float | None) -> float | None:
    """Calculate rule lift from hit bad rate and overall bad rate."""
    return safe_rate(hit_bad_rate, overall_bad_rate)


def bad_capture(hit_bad_count: int, total_bad_count: int) -> float | None:
    """Calculate bad-customer capture rate."""
    if total_bad_count == 0:
        return 0 if hit_bad_count == 0 else None
    return safe_rate(hit_bad_count, total_bad_count)


def good_harm(hit_good_count: int, total_good_count: int) -> float | None:
    """Calculate good-customer injury rate."""
    if total_good_count == 0:
        return 0 if hit_good_count == 0 else None
    return safe_rate(hit_good_count, total_good_count)


def _clean_binary_inputs(hit_mask: Any, target: Any, positive_class: Any = 1) -> tuple[pd.Series, pd.Series]:
    frame = pd.DataFrame({"hit": pd.Series(hit_mask), "target": pd.Series(target)})
    frame = frame.dropna(subset=["target"]).copy()
    hit = frame["hit"].fillna(False).astype(bool)
    bad = frame["target"].eq(positive_class)
    return hit.reset_index(drop=True), bad.reset_index(drop=True)


def evaluate_binary_rule(hit_mask: Any, target: Any, positive_class: Any = 1) -> dict[str, float | int | None]:
    """Evaluate one binary reject rule on an already confirmed mature sample."""
    hit, bad = _clean_binary_inputs(hit_mask, target, positive_class)
    total_count = int(len(bad))
    hit_count = int(hit.sum())
    non_hit_count = total_count - hit_count
    total_bad_count = int(bad.sum())
    total_good_count = total_count - total_bad_count
    hit_bad_count = int((hit & bad).sum())
    hit_good_count = hit_count - hit_bad_count
    non_hit_bad_count = total_bad_count - hit_bad_count
    hit_bad_rate = safe_rate(hit_bad_count, hit_count)
    overall_bad_rate = safe_rate(total_bad_count, total_count)
    return {
        "hit_count": hit_count,
        "coverage_rate": safe_rate(hit_count, total_count),
        "reject_rate": hit_bad_rate,
        "non_hit_reject_rate": safe_rate(non_hit_bad_count, non_hit_count),
        "reject_lift": lift(hit_bad_rate, overall_bad_rate),
        "reject_capture_rate": bad_capture(hit_bad_count, total_bad_count),
        "pass_injury_rate": good_harm(hit_good_count, total_good_count),
    }


def amount_bad_rate(data: pd.DataFrame, numerator: str, denominator: str) -> float | None:
    """按已确认的金额字段计算金额风险率。"""
    return safe_div(data[numerator].sum(), data[denominator].sum())
