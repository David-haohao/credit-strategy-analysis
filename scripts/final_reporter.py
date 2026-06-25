"""Generate a self-contained HTML report from verified stage bundles only."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

try:
    from scripts.utils.contracts import ContractValidationError, load_confirmation_receipt, load_yaml
    from scripts.utils.output_contract import STAGE_SPECS, load_stage_bundle, write_stage_bundle
    from scripts.utils.report_writer import render_template
except ModuleNotFoundError:  # Supports direct execution from the scripts directory.
    from utils.contracts import ContractValidationError, load_confirmation_receipt, load_yaml
    from utils.output_contract import STAGE_SPECS, load_stage_bundle, write_stage_bundle
    from utils.report_writer import render_template


REPORT_SECTIONS = {
    "00": "数据与产品口径",
    "01": "规则挖掘",
    "02": "规则组合",
    "03": "策略效果与 Swap",
}


def _source_rows(run_dir: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    validations: list[dict[str, str]] = []
    for stage_id, section_title in REPORT_SECTIONS.items():
        bundle = load_stage_bundle(run_dir, stage_id)
        limitations = "; ".join(bundle["manifest"].get("limitations", [])) or "无"
        for artifact in bundle["inventory"]["artifacts"]:
            rows.append(
                {
                    "section_id": section_title,
                    "stage_id": stage_id,
                    "artifact_name": artifact["artifact_name"],
                    "relative_path": artifact["relative_path"],
                    "sha256": artifact["sha256"],
                    "artifact_status": artifact["status"],
                    "limitation": artifact.get("reason") or limitations,
                }
            )
        validations.append(
            {
                "check_name": f"阶段 {stage_id} 的 manifest、inventory 与产物哈希",
                "status": "passed",
                "details": "已按固定输出契约校验；报告未重新计算指标。",
            }
        )
    return rows, validations


def build_final_report(run_dir: str | Path, config: Mapping[str, Any], receipt: Mapping[str, Any]) -> Path:
    """Build stage 04 from registered artifacts, without reading raw source data."""
    source_rows, validations = _source_rows(run_dir)
    title = str(config.get("final_report", {}).get("title") or "信用策略分析报告")
    scope = str(config.get("final_report", {}).get("report_scope") or "以已校验阶段产物为准")
    html = render_template(
        Path(__file__).resolve().parents[1] / "templates",
        "final_report.html.j2",
        {
            "title": title,
            "scope": scope,
            "source_rows": source_rows,
            "validations": validations,
            "sections": REPORT_SECTIONS,
        },
    )
    write_stage_bundle(
        run_dir,
        "04",
        config,
        receipt,
        artifact_rows={
            "report_source_index.csv": source_rows,
            "report_validation.csv": validations,
        },
        limitations=["报告仅汇总已登记且哈希校验通过的聚合产物；不重新计算指标。"],
        html_content=html,
    )
    return Path(run_dir).resolve() / STAGE_SPECS["04"]["directory"] / "final_report.html"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从已校验阶段目录包生成最终 HTML 报告")
    parser.add_argument("--config", required=True, help="UTF-8 YAML 最终报告配置")
    parser.add_argument("--confirmation", required=True, help="UTF-8 JSON 用户确认凭证")
    parser.add_argument("--run-dir", required=True, help="已初始化的运行根目录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_yaml(args.config)
        receipt = load_confirmation_receipt(args.confirmation)
        path = build_final_report(args.run_dir, config, receipt)
    except (ContractValidationError, OSError, ValueError) as error:
        print(f"最终报告生成失败: {error}")
        return 2
    print(f"最终报告已写入: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
