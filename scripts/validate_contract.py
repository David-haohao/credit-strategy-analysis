"""验证策略分析运行配置并生成 run_manifest.json。"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

try:
    from scripts.utils.contracts import (
        ContractValidationError,
        load_confirmation_receipt,
        load_yaml,
        validate_run_contract,
        write_run_manifest,
    )
except ModuleNotFoundError:  # 支持 python scripts/validate_contract.py 直接执行。
    from utils.contracts import (
        ContractValidationError,
        load_confirmation_receipt,
        load_yaml,
        validate_run_contract,
        write_run_manifest,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="验证信贷策略分析输入契约")
    parser.add_argument("--config", required=True, help="UTF-8 YAML 运行配置")
    parser.add_argument("--confirmation", required=True, help="用户确认凭证 JSON")
    parser.add_argument("--input", required=True, help="UTF-8 CSV 输入数据")
    parser.add_argument("--output-dir", required=True, help="manifest 输出目录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_yaml(args.config)
        receipt = load_confirmation_receipt(args.confirmation)
        data = pd.read_csv(args.input, encoding="utf-8-sig")
        validation = validate_run_contract(config, receipt, data)
        manifest = write_run_manifest(
            Path(args.output_dir), config, receipt, validation, len(data), ["run_manifest.json"]
        )
    except (ContractValidationError, OSError, ValueError) as error:
        print(f"契约校验失败: {error}")
        return 2
    print(f"契约校验通过，已写入: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
