try:
    from scripts.utils.task_stub import run_task_stub
except ModuleNotFoundError:
    from utils.task_stub import run_task_stub

if __name__ == "__main__":
    raise SystemExit(run_task_stub("Swap 分析", "Swap 分析前置校验"))
