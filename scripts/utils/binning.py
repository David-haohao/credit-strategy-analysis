"""toad 分箱依赖检查与分箱辅助函数。"""

from __future__ import annotations

from importlib.util import find_spec
import math
from typing import Iterable


def require_toad() -> None:
    if find_spec("toad") is None:
        raise RuntimeError("规则挖掘、WOE、IV 与分箱任务必须安装 toad")


def classify_monotonicity(bad_rates: Iterable[float | int | None]) -> str:
    """Classify bad-rate monotonicity for ordered non-missing bins."""
    values: list[float] = []
    for value in bad_rates:
        if value is None:
            continue
        number = float(value)
        if math.isnan(number):
            continue
        values.append(number)
    if len(values) < 2:
        return "not_evaluated"
    non_decreasing = all(left <= right for left, right in zip(values, values[1:]))
    non_increasing = all(left >= right for left, right in zip(values, values[1:]))
    has_increase = any(left < right for left, right in zip(values, values[1:]))
    has_decrease = any(left > right for left, right in zip(values, values[1:]))
    if non_decreasing and not has_increase and non_increasing and not has_decrease:
        return "flat"
    if non_decreasing and has_increase:
        return "increasing"
    if non_increasing and has_decrease:
        return "decreasing"
    return "non_monotonic"
