try:
    from scripts.utils.task_stub import run_task_stub
except ModuleNotFoundError:
    from utils.task_stub import run_task_stub

if __name__ == "__main__":
    raise SystemExit(
        run_task_stub("规则挖掘", "规则挖掘前置校验", "rule_mining", requires_toad=True)
    )
