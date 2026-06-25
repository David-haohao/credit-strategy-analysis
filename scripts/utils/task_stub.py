"""Shared preflight CLI for analysis stages whose business algorithms are pending."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .binning import require_toad
from .contracts import ContractValidationError, load_confirmation_receipt, load_yaml, validate_run_contract
from .output_contract import (
    STAGE_SPECS,
    OutputContractError,
    validate_run_directory,
    write_stage_bundle,
)


STAGE_ID_BY_TASK = {"rule_mining": "01", "rule_combination": "02", "strategy_evaluation": "03"}


def run_task_stub(
    task_name: str, description: str, expected_task_type: str, *, requires_toad: bool = False
) -> int:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", required=True, help="UTF-8 YAML 运行配置")
    parser.add_argument("--confirmation", required=True, help="用户确认凭证 JSON")
    parser.add_argument("--input", required=True, help="UTF-8 CSV 输入数据")
    parser.add_argument("--run-dir", required=True, help="固定阶段目录包的运行根目录")
    args = parser.parse_args()
    try:
        config = load_yaml(args.config)
        if config.get("task", {}).get("task_type") != expected_task_type:
            raise ContractValidationError(f"{task_name}只接受 {expected_task_type} 任务")
        receipt = load_confirmation_receipt(args.confirmation)
        data = pd.read_csv(args.input, encoding="utf-8-sig")
        validate_run_contract(config, receipt, data)
        run_dir = validate_run_directory(config, args.run_dir)
        if requires_toad:
            require_toad()
        stage_id = STAGE_ID_BY_TASK[expected_task_type]
        statuses = {
            name: {"status": "not_available", "reason": "当前 CLI 仅完成前置校验和固定产物包写入；业务算法尚未实现。"}
            for name in STAGE_SPECS[stage_id]["artifacts"]
        }
        if stage_id == "01":
            statuses["rule_stability.csv"] = {"status": "not_applicable", "reason": "未评估（未做时间外验证）"}
        if stage_id == "02":
            statuses["cascade_oot.csv"] = {"status": "not_applicable", "reason": "未评估（未做时间外验证）"}
        write_stage_bundle(
            run_dir,
            stage_id,
            config,
            receipt,
            artifact_statuses=statuses,
            quality_gates={"input_contract": "passed", "analysis_unit_uniqueness": "passed"},
            limitations=["业务算法尚未实现；所有空表不得被解释为规则、策略或风险结论。"],
        )
    except (ContractValidationError, OutputContractError, OSError, RuntimeError, ValueError) as error:
        print(f"{task_name}前置校验失败: {error}")
        return 2
    print(f"{task_name}固定阶段产物包已写入: {Path(args.run_dir) / STAGE_SPECS[stage_id]['directory']}")
    print(f"{task_name}算法尚未实现；当前仅提供稳定 CLI、契约校验和固定空表产物。")
    return 3
