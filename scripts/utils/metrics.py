"""跨任务共享的最小指标函数。"""

from __future__ import annotations

import pandas as pd

from .contracts import safe_div


def amount_bad_rate(data: pd.DataFrame, numerator: str, denominator: str) -> float | None:
    """按已确认的金额字段计算金额风险率。"""
    return safe_div(data[numerator].sum(), data[denominator].sum())
