try:
    from scripts.utils.task_stub import run_task_stub
except ModuleNotFoundError:
    from utils.task_stub import run_task_stub

if __name__ == "__main__":
    raise SystemExit(
        run_task_stub(
            "Lift TopN 规则组合",
            "Lift TopN 规则组合前置校验",
            expected_task_type="rule_combination",
        )
    )
