"""策略效果与 Swap 评估的前置校验入口。"""

try:
    from scripts.utils.task_stub import run_task_stub
except ModuleNotFoundError:
    from utils.task_stub import run_task_stub


if __name__ == "__main__":
    raise SystemExit(
        run_task_stub("策略效果与 Swap 评估", "策略效果与 Swap 前置校验", "strategy_evaluation")
    )
