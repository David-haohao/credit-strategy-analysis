"""运行前契约、确认凭证与 manifest 校验。"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml


TASK_TYPES = frozenset(
    {"rule_mining", "rule_combination", "strategy_evaluation", "final_report"}
)


class ContractValidationError(ValueError):
    """输入、用户确认或任务语义不满足契约。"""


def safe_div(numerator: float | int | None, denominator: float | int | None) -> float | None:
    """安全计算比例；分子或分母缺失、分母为零时返回 None。"""
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def load_yaml(path: str | Path) -> dict[str, Any]:
    """读取 UTF-8 YAML 配置。"""
    with Path(path).open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ContractValidationError("配置文件顶层必须是对象")
    return data


def load_confirmation_receipt(path: str | Path) -> dict[str, Any]:
    """读取独立用户确认凭证。"""
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ContractValidationError("确认凭证顶层必须是对象")
    return data


def build_analysis_unit_id(data: pd.DataFrame, id_cols: Iterable[str]) -> pd.Series:
    """用已确认 ID 组合生成分析单位，绝不默认使用 sample_id。"""
    columns = list(id_cols)
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ContractValidationError(f"分析单位 ID 字段缺失: {', '.join(missing)}")
    if not columns:
        raise ContractValidationError("分析颗粒度必须指定 id_cols")
    if data[columns].isna().any().any():
        raise ContractValidationError("分析单位 ID 不允许为空")
    return data[columns].astype(str).agg("\x1f".join, axis=1)


def _require(mapping: dict[str, Any], key: str, label: str) -> Any:
    value = mapping.get(key)
    if value is None or value == "" or value == []:
        raise ContractValidationError(f"缺少{label}")
    return value


def _same_or_error(config_value: Any, receipt_value: Any, label: str) -> None:
    if config_value != receipt_value:
        raise ContractValidationError(f"确认凭证与配置的{label}不一致")


def _validate_task_context(config: dict[str, Any], receipt: dict[str, Any] | None) -> str:
    if receipt is None:
        raise ContractValidationError("缺少用户确认凭证")
    if receipt.get("source") != "user_interaction" or receipt.get("confirmed") is not True:
        raise ContractValidationError("确认凭证必须来自用户交互且明确确认")
    _require(config.get("confirmation", {}), "receipt_path", "确认凭证路径")

    task = config.get("task", {})
    for key, label in (
        ("product_form", "产品形态"),
        ("repayment_type", "还款方式"),
        ("scenario", "应用场景"),
        ("task_type", "任务类型"),
    ):
        _require(task, key, label)
        _same_or_error(task[key], receipt.get(key), label)
    task_type = task["task_type"]
    if task_type not in TASK_TYPES:
        raise ContractValidationError("任务类型不属于五段规则策略流程")
    return task_type


def _validate_task_settings(config: dict[str, Any], task_type: str) -> None:
    if task_type == "rule_combination":
        combination = config.get("rule_combination", {})
        top_n = _require(combination, "top_n", "TopN")
        if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
            raise ContractValidationError("TopN 必须是大于零的整数")
        if _require(combination, "rank_by", "Lift 排序") != "lift_desc":
            raise ContractValidationError("规则组合必须按 lift_desc 排序")
        if _require(combination, "execution_mode", "级联拒绝语义") != "sequential_reject":
            raise ContractValidationError("规则组合必须使用 sequential_reject")
        _require(combination, "tie_policy", "Lift 并列处理规则")

    if task_type == "strategy_evaluation":
        evaluation = config.get("strategy_evaluation", {})
        compare = evaluation.get("compare_with_old_strategy")
        if not isinstance(compare, bool):
            raise ContractValidationError("必须确认是否与旧策略比较")
        if compare:
            _require(evaluation, "old_decision_col", "旧策略决策字段")
            _require(evaluation, "new_decision_col", "新策略决策字段")
            _require(evaluation, "comparison_population", "新旧策略比较总体")
            observability = _require(evaluation, "swap_in_observability", "swap_in 可观测性")
            if observability not in {"estimated", "unobservable"}:
                raise ContractValidationError("swap_in 可观测性只能为 estimated 或 unobservable")
            if observability == "estimated":
                _require(evaluation, "swap_in_estimation_method", "swap_in 估计方法")


def _required_input_columns(config: dict[str, Any]) -> set[str]:
    columns = config.get("columns", {})
    grain = config.get("analysis_grain", {})
    label = config.get("label", {})
    required = set(grain.get("id_cols") or [])
    for name in ("target_col", "date_col"):
        value = columns.get(name) or label.get(name)
        if value:
            required.add(value)
    amount = config.get("amount_metric", {})
    if amount.get("enabled"):
        required.update((amount.get("numerator"), amount.get("denominator")))
    evaluation = config.get("strategy_evaluation", {})
    if evaluation.get("compare_with_old_strategy"):
        required.update((evaluation.get("old_decision_col"), evaluation.get("new_decision_col")))
    return {column for column in required if column}


def validate_run_contract(
    config: dict[str, Any], receipt: dict[str, Any] | None, data: pd.DataFrame
) -> dict[str, Any]:
    """校验需要原始分析数据的前三阶段任务。"""
    task_type = _validate_task_context(config, receipt)
    if task_type == "final_report":
        raise ContractValidationError("最终报告不接受原始数据契约，请使用 final_reporter")
    _validate_task_settings(config, task_type)

    sample_scope = config.get("sample_scope", {})
    _require(sample_scope, "population", "样本口径")

    field_mapping = config.get("field_mapping", {})
    if field_mapping.get("confirmed") is not True:
        raise ContractValidationError("字段映射尚未获得用户确认")
    if field_mapping.get("unmapped_required_fields"):
        raise ContractValidationError("存在未确认映射的必需字段")
    if receipt.get("field_mapping", {}).get("confirmed") is not True:
        raise ContractValidationError("确认凭证未确认字段映射")

    grain = config.get("analysis_grain", {})
    grain_name = _require(grain, "grain", "分析颗粒度")
    id_cols = _require(grain, "id_cols", "分析颗粒度 id_cols")
    receipt_grain = receipt.get("analysis_grain", {})
    _same_or_error(grain_name, receipt_grain.get("grain"), "分析颗粒度")
    _same_or_error(list(id_cols), list(receipt_grain.get("id_cols") or []), "分析颗粒度 id_cols")

    grain_values = [grain.get(name) for name in ("label_grain", "feature_grain", "output_grain")]
    if any(value and value != grain_name for value in grain_values):
        aggregation_rule = _require(grain, "aggregation_rule", "跨颗粒度聚合规则")
        _same_or_error(aggregation_rule, receipt_grain.get("aggregation_rule"), "聚合规则")
    elif grain.get("aggregation_rule") != receipt_grain.get("aggregation_rule"):
        raise ContractValidationError("确认凭证与配置的聚合规则不一致")

    label = config.get("label", {})
    for key, label_name in (
        ("target_col", "标签字段"),
        ("positive_class", "正样本定义"),
        ("bad_definition", "坏样本定义"),
        ("maturity_rule", "成熟样本口径"),
    ):
        _require(label, key, label_name)
        _same_or_error(label[key], receipt.get("label", {}).get(key), label_name)

    amount = config.get("amount_metric", {})
    if amount.get("enabled"):
        for key, label_name in (
            ("numerator", "金额口径分子"),
            ("denominator", "金额口径分母"),
            ("formula", "金额口径公式"),
            ("filter", "金额口径样本过滤"),
        ):
            _require(amount, key, label_name)
            _same_or_error(amount[key], receipt.get("amount_metric", {}).get(key), label_name)

    feature_policy = config.get("feature_policy", {})
    candidate_features = set(feature_policy.get("candidate_features") or [])
    protected_columns = set(feature_policy.get("protected_columns") or [])
    overrides = set(feature_policy.get("protected_overrides") or [])
    protected_candidates = candidate_features & protected_columns
    if protected_candidates and (
        feature_policy.get("allow_protected_override") is not True
        or not protected_candidates.issubset(overrides)
    ):
        raise ContractValidationError("保护列不得作为候选特征")

    required_columns = _required_input_columns(config)
    missing_columns = sorted(required_columns - set(data.columns))
    if missing_columns:
        raise ContractValidationError(f"输入数据缺少必需字段: {', '.join(missing_columns)}")
    analysis_unit_id = build_analysis_unit_id(data, id_cols)
    if analysis_unit_id.duplicated().any():
        raise ContractValidationError("当前分析颗粒度下的分析单位不唯一")

    return {
        "task_type": task_type,
        "analysis_unit_count": int(analysis_unit_id.nunique()),
        "id_cols": list(id_cols),
        "required_columns": sorted(required_columns),
        "input_columns": list(data.columns),
    }


def validate_report_contract(
    config: dict[str, Any], receipt: dict[str, Any] | None, source_manifest: dict[str, Any]
) -> dict[str, Any]:
    """校验最终报告只引用已有产物及确认凭证。"""
    task_type = _validate_task_context(config, receipt)
    if task_type != "final_report":
        raise ContractValidationError("final_reporter 只接受 final_report 任务")
    report = config.get("final_report", {})
    _require(report, "source_manifests", "报告来源 manifest")
    _require(report, "title", "报告标题")
    _require(report, "report_scope", "报告范围")
    source_receipt = source_manifest.get("confirmation_receipt")
    if not isinstance(source_receipt, dict) or source_receipt.get("confirmed") is not True:
        raise ContractValidationError("报告来源 manifest 缺少已确认凭证")
    for key in ("product_form", "repayment_type", "scenario"):
        _same_or_error(receipt.get(key), source_receipt.get(key), f"报告来源{key}")
    return {"task_type": task_type, "source_manifest_keys": sorted(source_manifest)}


def write_run_manifest(
    output_dir: str | Path,
    config: dict[str, Any],
    receipt: dict[str, Any],
    validation: dict[str, Any],
    input_row_count: int,
    output_files: list[str],
) -> Path:
    """写入可审计、UTF-8 编码的运行 manifest。"""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": config.get("task", {}),
        "sample_scope": config.get("sample_scope", {}),
        "analysis_grain": config.get("analysis_grain", {}),
        "field_mapping": config.get("field_mapping", {}),
        "label": config.get("label", {}),
        "amount_metric": config.get("amount_metric", {}),
        "confirmation_receipt_path": config.get("confirmation", {}).get("receipt_path"),
        "confirmation_receipt": receipt,
        "validation": validation,
        "input": {"path": config.get("input", {}).get("path"), "row_count": input_row_count},
        "output": {"directory": str(directory), "files": output_files},
    }
    path = directory / "run_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
