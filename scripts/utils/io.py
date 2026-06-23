"""统一 UTF-8 输入输出。"""

from pathlib import Path

import pandas as pd


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def write_csv(data: pd.DataFrame, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(target, index=False, encoding="utf-8-sig")
    return target
