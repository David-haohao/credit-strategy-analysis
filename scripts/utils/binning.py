"""toad 分箱依赖检查。"""

from importlib.util import find_spec


def require_toad() -> None:
    if find_spec("toad") is None:
        raise RuntimeError("规则挖掘、WOE、IV 与分箱任务必须安装 toad")
