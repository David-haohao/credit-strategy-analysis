"""为未实现的分析任务提供一致的前置校验 CLI。"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .binning import require_toad
from .contracts import (
    ContractValidationError,
    load_confirmation_receipt,
    load_yaml,
    validate_run_contract,
    write_run_manifest,
)


def run_task_stub(
    task_name: str,
    description: str,
    *,
    expected_task_type: str,
    requires_toad: bool = False,
) -> int:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", required=True, help="UTF-8 YAML 运行配置")
    parser.add_argument("--confirmation", required=True, help="用户确认凭证 JSON")
    parser.add_argument("--input", required=True, help="UTF-8 CSV 输入数据")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    args = parser.parse_args()
    try:
        config = load_yaml(args.config)
        receipt = load_confirmation_receipt(args.confirmation)
        data = pd.read_csv(args.input, encoding="utf-8-sig")
        validation = validate_run_contract(config, receipt, data)
        if config["task"]["task_type"] != expected_task_type:
            raise ContractValidationError(
                f"{task_name}要求 task.task_type={expected_task_type}"
            )
        if requires_toad:
            require_toad()
        manifest = write_run_manifest(
            Path(args.output_dir),
            config,
            receipt,
            validation,
            len(data),
            ["run_manifest.json"],
        )
    except (ContractValidationError, OSError, RuntimeError, ValueError) as error:
        print(f"{task_name}前置校验失败: {error}")
        return 2
    print(f"{task_name}前置校验通过，已写入: {manifest}")
    print(f"{task_name}算法尚未实现；当前仅提供稳定 CLI 和契约校验。")
    return 3
