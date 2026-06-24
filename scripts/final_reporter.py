"""最终报告的来源产物前置校验入口。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.utils.contracts import (
        ContractValidationError,
        load_confirmation_receipt,
        load_yaml,
        validate_report_contract,
    )
except ModuleNotFoundError:
    from utils.contracts import (
        ContractValidationError,
        load_confirmation_receipt,
        load_yaml,
        validate_report_contract,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="最终报告来源产物前置校验")
    parser.add_argument("--config", required=True, help="UTF-8 YAML 运行配置")
    parser.add_argument("--confirmation", required=True, help="用户确认凭证 JSON")
    parser.add_argument("--source-manifest", required=True, help="前序阶段 run_manifest.json")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_yaml(args.config)
        receipt = load_confirmation_receipt(args.confirmation)
        source_manifest = json.loads(Path(args.source_manifest).read_text(encoding="utf-8"))
        validation = validate_report_contract(config, receipt, source_manifest)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "final_report_precheck_manifest.json"
        path.write_text(
            json.dumps({"validation": validation, "source_manifest": str(args.source_manifest)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (ContractValidationError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"最终报告前置校验失败: {error}")
        return 2
    print(f"最终报告前置校验通过，已写入: {path}")
    print("最终报告算法尚未实现；当前仅提供稳定 CLI 和来源产物校验。")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
