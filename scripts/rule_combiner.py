"""Lift TopN 级联规则组合的前置校验入口。"""

try:
    from scripts.utils.task_stub import run_task_stub
except ModuleNotFoundError:
    from utils.task_stub import run_task_stub


if __name__ == "__main__":
    raise SystemExit(run_task_stub("规则组合", "Lift TopN 规则组合前置校验", "rule_combination"))
