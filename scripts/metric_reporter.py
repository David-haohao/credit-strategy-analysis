try:
    from scripts.utils.task_stub import run_task_stub
except ModuleNotFoundError:
    from utils.task_stub import run_task_stub

if __name__ == "__main__":
    raise SystemExit(run_task_stub("指标报告", "指标报告前置校验", requires_toad=True))
