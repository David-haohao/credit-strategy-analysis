"""Versioned stage-bundle contract for offline credit-strategy analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping

import pandas as pd


OUTPUT_CONTRACT_VERSION = "1.1"


class OutputContractError(ValueError):
    """Raised when a stage output cannot be safely reproduced or traced."""


STAGE_SPECS: dict[str, dict[str, Any]] = {
    "00": {
        "directory": "00_data_contract",
        "upstreams": [],
        "artifacts": {
            "data_profile.csv": ["metric_name", "metric_value", "metric_status", "notes"],
            "analysis_unit_check.csv": ["check_name", "status", "observed_value", "expected_value", "notes"],
            "feature_governance.csv": ["feature_name", "feature_status", "exclusion_reason", "coverage_count", "notes"],
        },
    },
    "01": {
        "directory": "01_rule_mining",
        "upstreams": ["00"],
        "artifacts": {
            "feature_screening.csv": ["feature_name", "feature_status", "screening_reason", "iv", "coverage_count", "monotonicity", "stability_status"],
            "bin_iv_detail.csv": ["feature_name", "bin_order", "bin_label", "bin_lower", "bin_upper", "good_count", "bad_count", "bad_rate", "woe", "iv", "warning"],
            "single_rule_candidates.csv": ["rule_id", "feature_name", "rule_expression", "hit_count", "coverage_rate", "reject_rate", "non_hit_reject_rate", "reject_lift", "reject_capture_rate", "pass_injury_rate", "candidate_status", "stability_status"],
            "cart_path_candidates.csv": ["rule_id", "feature_name", "rule_expression", "hit_count", "coverage_rate", "reject_rate", "non_hit_reject_rate", "reject_lift", "reject_capture_rate", "pass_injury_rate", "candidate_status", "stability_status"],
            "rule_stability.csv": ["rule_id", "stability_status", "evaluation_window", "metric_name", "metric_value", "reason"],
        },
    },
    "02": {
        "directory": "02_rule_combination",
        "upstreams": ["00", "01"],
        "artifacts": {
            "lift_ranked_rules.csv": ["rank", "rule_id", "feature_name", "rule_expression", "reject_lift", "candidate_status", "selection_reason"],
            "selected_rule_set.csv": ["execution_order", "rule_id", "logical_feature_group", "decision_action", "selection_basis", "selection_reason"],
            "cascade_funnel.csv": ["execution_order", "rule_id", "input_count", "hit_reject_count", "remaining_pass_count", "cumulative_reject_rate", "stability_status"],
            "rule_overlap.csv": ["rule_id_a", "rule_id_b", "overlap_count", "overlap_rate", "notes"],
            "cascade_oot.csv": ["stability_status", "evaluation_window", "metric_name", "metric_value", "reason"],
        },
    },
    "03": {
        "directory": "03_strategy_evaluation",
        "upstreams": ["00", "01", "02"],
        "artifacts": {
            "strategy_effect_summary.csv": ["strategy_name", "population", "sample_count", "reject_rate", "approval_rate", "metric_status", "notes"],
            "strategy_layer_effect.csv": ["execution_order", "rule_id", "sample_count", "reject_rate", "metric_status", "notes"],
            "swap_summary.csv": ["old_decision", "new_decision", "swap_group", "sample_count", "population_rate", "risk_observability", "risk_estimation_status"],
            "swap_segment_detail.csv": ["swap_group", "segment_name", "segment_value", "sample_count", "population_rate", "risk_observability", "risk_estimation_status"],
            "swap_in_risk_estimate.csv": ["estimation_method", "method_status", "score_or_rule_band", "sample_count", "estimated_bad_rate", "estimated_bad_count", "assumption", "reason"],
            "swap_in_coverage.csv": ["estimation_method", "coverage_status", "eligible_count", "covered_count", "coverage_rate", "reason"],
        },
    },
    "04": {
        "directory": "04_final_report",
        "upstreams": ["00", "01", "02", "03"],
        "artifacts": {
            "final_report.html": None,
            "report_source_index.csv": ["section_id", "stage_id", "artifact_name", "relative_path", "sha256", "artifact_status", "limitation"],
            "report_validation.csv": ["check_name", "status", "details"],
        },
    },
}

def _excluded_name_tokens(config: Mapping[str, Any]) -> list[str]:
    values = config.get("feature_policy", {}).get("excluded_name_tokens") or []
    return [str(value).strip() for value in values if str(value).strip()]


def _configured_protected_names(config: Mapping[str, Any]) -> list[str]:
    feature_policy = config.get("feature_policy", {})
    columns = config.get("columns", {})
    grain = config.get("analysis_grain", {})
    values = []
    values.extend(feature_policy.get("protected_columns") or [])
    values.extend(feature_policy.get("exclude_features") or [])
    values.extend(columns.get("id_cols") or [])
    values.extend(grain.get("id_cols") or [])
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        name = str(value).strip()
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            result.append(name)
    return result


def _contains_token(values: pd.Series, token: str) -> bool:
    return values.str.contains(token, case=False, regex=False).any()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def file_sha256(path: str | Path) -> str:
    return _sha256_bytes(Path(path).read_bytes())


def json_sha256(value: Any) -> str:
    return _sha256_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _assert_within(path: Path, root: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise OutputContractError(f"output path escapes run directory: {path}") from error


def _require_stage(stage_id: str) -> dict[str, Any]:
    if stage_id not in STAGE_SPECS:
        raise OutputContractError(f"unknown stage id: {stage_id}")
    return STAGE_SPECS[stage_id]


def _dependency_versions() -> dict[str, str | None]:
    result: dict[str, str | None] = {"python": sys.version.split()[0]}
    for package in ("pandas", "numpy", "scikit-learn", "toad", "PyYAML", "Jinja2"):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = None
    return result


def _root_paths(run_dir: str | Path) -> dict[str, Path]:
    root = _resolve(run_dir)
    return {
        "root": root,
        "config": root / "input_config.yaml",
        "receipt": root / "confirmation_receipt.json",
        "manifest": root / "run_manifest.json",
        "source": root / "source_fingerprint.json",
    }


def initialize_run_bundle(
    run_dir: str | Path,
    config: Mapping[str, Any],
    receipt: Mapping[str, Any],
    config_path: str | Path,
    receipt_path: str | Path,
    input_path: str | Path,
) -> Path:
    """Create an auditable run root without copying raw source data."""
    paths = _root_paths(run_dir)
    root = paths["root"]
    configured_directory = config.get("output", {}).get("directory")
    if not configured_directory:
        raise OutputContractError("config.output.directory is required")
    if _resolve(configured_directory) != root:
        raise OutputContractError("config.output.directory must equal --run-dir")
    if root.exists() and any(root.iterdir()):
        raise OutputContractError("run directory already exists and is not empty")

    source = _resolve(input_path)
    config_source = _resolve(config_path)
    receipt_source = _resolve(receipt_path)
    if not source.is_file() or not config_source.is_file() or not receipt_source.is_file():
        raise OutputContractError("config, confirmation receipt, and input must be existing files")

    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(config_source, paths["config"])
    shutil.copyfile(receipt_source, paths["receipt"])
    source_fingerprint = {
        "input_path": str(source),
        "input_sha256": file_sha256(source),
        "input_size_bytes": source.stat().st_size,
        "config_source_path": str(config_source),
        "config_sha256": file_sha256(config_source),
        "receipt_source_path": str(receipt_source),
        "receipt_sha256": file_sha256(receipt_source),
    }
    paths["source"].write_text(json.dumps(source_fingerprint, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "output_contract_version": OUTPUT_CONTRACT_VERSION,
        "created_at": _utc_now(),
        "run_directory": str(root),
        "source_fingerprint_sha256": file_sha256(paths["source"]),
        "config_sha256": json_sha256(dict(config)),
        "confirmation_receipt_sha256": json_sha256(dict(receipt)),
        "dependency_versions": _dependency_versions(),
        "stages": {},
        "raw_input_copied": False,
    }
    paths["manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return root


def validate_run_directory(config: Mapping[str, Any], run_dir: str | Path) -> Path:
    """Require the configured output root and CLI run directory to be identical."""
    configured_directory = config.get("output", {}).get("directory")
    if not configured_directory:
        raise OutputContractError("config.output.directory is required")
    root = _resolve(run_dir)
    if _resolve(configured_directory) != root:
        raise OutputContractError("config.output.directory must equal --run-dir")
    return root


def _load_run_manifest(run_dir: str | Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    paths = _root_paths(run_dir)
    if not paths["manifest"].is_file() or not paths["source"].is_file():
        raise OutputContractError("run bundle has not been initialized")
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if manifest.get("output_contract_version") != OUTPUT_CONTRACT_VERSION:
        raise OutputContractError("unsupported output contract version")
    source = json.loads(paths["source"].read_text(encoding="utf-8"))
    if manifest.get("source_fingerprint_sha256") != file_sha256(paths["source"]):
        raise OutputContractError("source fingerprint hash mismatch")
    return paths["root"], manifest, source


def _validate_frame(
    frame: pd.DataFrame,
    columns: list[str],
    artifact_name: str,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    protected_names = _configured_protected_names(config)
    excluded_tokens = _excluded_name_tokens(config)
    column_values = pd.Series([str(column) for column in frame.columns])
    for name in protected_names:
        if _contains_token(column_values, name):
            raise OutputContractError(f"protected field is forbidden in {artifact_name}: {name}")
    for token in excluded_tokens:
        if _contains_token(column_values, token):
            raise OutputContractError(f"excluded feature token is forbidden in {artifact_name}: {token}")
    extra = sorted(set(frame.columns) - set(columns))
    if extra:
        raise OutputContractError(f"unexpected columns in {artifact_name}: {', '.join(extra)}")
    for governed_column in ("feature_name", "rule_expression", "logical_feature_group"):
        if governed_column in frame.columns:
            values = frame[governed_column].dropna().astype(str)
            for name in protected_names:
                if _contains_token(values, name):
                    raise OutputContractError(
                        f"{governed_column} contains protected field configured for this run: {name}"
                    )
            for token in excluded_tokens:
                if _contains_token(values, token):
                    raise OutputContractError(
                        f"{governed_column} contains excluded feature token configured for this run: {token}"
                    )
    object_values = frame.select_dtypes(include="object").astype(str)
    if not object_values.empty and object_values.apply(lambda column: column.str.lstrip().str.startswith(("{", "[")).any()).any():
        raise OutputContractError(f"raw JSON is forbidden in {artifact_name}")
    return frame.reindex(columns=columns)


def _empty_or_rows(
    rows: Any,
    columns: list[str],
    artifact_name: str,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    if rows is None:
        frame = pd.DataFrame(columns=columns)
    elif isinstance(rows, pd.DataFrame):
        frame = rows.copy()
    else:
        frame = pd.DataFrame(rows)
    return _validate_frame(frame, columns, artifact_name, config)


def _stage_paths(root: Path, stage_id: str) -> tuple[Path, Path, Path]:
    spec = _require_stage(stage_id)
    directory = root / spec["directory"]
    _assert_within(directory, root)
    return directory, directory / "stage_manifest.json", directory / "artifact_inventory.json"


def _load_stage_unchecked(root: Path, stage_id: str) -> dict[str, Any]:
    directory, manifest_path, inventory_path = _stage_paths(root, stage_id)
    if not manifest_path.is_file() or not inventory_path.is_file():
        raise OutputContractError(f"missing upstream stage bundle: {stage_id}")
    return {
        "directory": directory,
        "manifest_path": manifest_path,
        "inventory_path": inventory_path,
        "manifest": json.loads(manifest_path.read_text(encoding="utf-8")),
        "inventory": json.loads(inventory_path.read_text(encoding="utf-8")),
    }


def load_stage_bundle(run_dir: str | Path, stage_id: str) -> dict[str, Any]:
    """Load and fully verify a registered stage bundle and its upstream chain."""
    root, _, _ = _load_run_manifest(run_dir)
    spec = _require_stage(stage_id)
    bundle = _load_stage_unchecked(root, stage_id)
    manifest = bundle["manifest"]
    inventory = bundle["inventory"]
    if manifest.get("output_contract_version") != OUTPUT_CONTRACT_VERSION:
        raise OutputContractError("stage manifest output contract version mismatch")
    if manifest.get("stage_id") != stage_id:
        raise OutputContractError("stage manifest id mismatch")
    if manifest.get("artifact_inventory_sha256") != file_sha256(bundle["inventory_path"]):
        raise OutputContractError("artifact inventory hash mismatch")
    entries = inventory.get("artifacts")
    if not isinstance(entries, list) or {entry.get("artifact_name") for entry in entries} != set(spec["artifacts"]):
        raise OutputContractError("artifact inventory does not match fixed stage contract")
    for entry in entries:
        name = entry["artifact_name"]
        artifact = bundle["directory"] / name
        _assert_within(artifact, bundle["directory"])
        if not artifact.is_file() or entry.get("sha256") != file_sha256(artifact):
            raise OutputContractError(f"artifact hash mismatch: {name}")
        if spec["artifacts"][name] is not None:
            columns = pd.read_csv(artifact, encoding="utf-8-sig").columns.tolist()
            if columns != spec["artifacts"][name]:
                raise OutputContractError(f"artifact columns do not match contract: {name}")
    if manifest.get("upstream_stage_ids") != spec["upstreams"]:
        raise OutputContractError("upstream stage ids do not match contract")
    for upstream in spec["upstreams"]:
        upstream_bundle = load_stage_bundle(root, upstream)
        expected = manifest.get("upstream_stage_manifest_sha256", {}).get(upstream)
        if expected != file_sha256(upstream_bundle["manifest_path"]):
            raise OutputContractError(f"upstream stage hash mismatch: {upstream}")
    return bundle


def write_stage_bundle(
    run_dir: str | Path,
    stage_id: str,
    config: Mapping[str, Any],
    receipt: Mapping[str, Any],
    *,
    artifact_rows: Mapping[str, Any] | None = None,
    artifact_statuses: Mapping[str, Mapping[str, str]] | None = None,
    limitations: list[str] | None = None,
    quality_gates: Mapping[str, str] | None = None,
    resume: bool = False,
    html_content: str | None = None,
) -> dict[str, Any]:
    """Write one fixed stage directory, or safely resume an identical one."""
    root, run_manifest, _ = _load_run_manifest(run_dir)
    spec = _require_stage(stage_id)
    directory, manifest_path, inventory_path = _stage_paths(root, stage_id)
    config_hash = json_sha256(dict(config))
    receipt_hash = json_sha256(dict(receipt))
    if directory.exists():
        if not resume:
            raise OutputContractError(f"stage directory already exists: {directory}")
        bundle = load_stage_bundle(root, stage_id)
        existing = bundle["manifest"]
        if existing.get("config_sha256") != config_hash or existing.get("confirmation_receipt_sha256") != receipt_hash:
            raise OutputContractError("resume requires matching config and confirmation receipt hashes")
        if existing.get("source_fingerprint_sha256") != run_manifest["source_fingerprint_sha256"]:
            raise OutputContractError("resume requires matching source fingerprint hash")
        return existing

    rows = dict(artifact_rows or {})
    statuses = dict(artifact_statuses or {})
    unknown = sorted(set(rows) - set(spec["artifacts"]))
    if unknown:
        raise OutputContractError(f"unknown or escaped artifact path: {', '.join(unknown)}")
    frames: dict[str, pd.DataFrame] = {}
    for name, columns in spec["artifacts"].items():
        if columns is not None:
            frames[name] = _empty_or_rows(rows.get(name), columns, name, config)
    if html_content is not None and stage_id != "04":
        raise OutputContractError("HTML content is only allowed for stage 04")

    upstream_hashes: dict[str, str] = {}
    for upstream in spec["upstreams"]:
        upstream_bundle = load_stage_bundle(root, upstream)
        upstream_hashes[upstream] = file_sha256(upstream_bundle["manifest_path"])

    directory.mkdir(parents=False, exist_ok=False)
    entries: list[dict[str, Any]] = []
    for name, columns in spec["artifacts"].items():
        target = directory / name
        _assert_within(target, directory)
        if columns is None:
            target.write_text(html_content or "<!doctype html><html lang=\"zh-CN\"><meta charset=\"utf-8\"><title>待生成报告</title></html>", encoding="utf-8")
            row_count = None
        else:
            frames[name].to_csv(target, index=False, encoding="utf-8-sig")
            row_count = int(len(frames[name]))
        status_info = statuses.get(name, {})
        status = status_info.get("status", "generated")
        if status not in {"generated", "not_applicable", "not_available", "failed"}:
            raise OutputContractError(f"invalid artifact status for {name}: {status}")
        entries.append(
            {
                "artifact_name": name,
                "relative_path": f"{spec['directory']}/{name}",
                "status": status,
                "reason": status_info.get("reason"),
                "row_count": row_count,
                "columns": columns,
                "sha256": file_sha256(target),
                "report_eligible": status == "generated",
            }
        )
    inventory = {"output_contract_version": OUTPUT_CONTRACT_VERSION, "stage_id": stage_id, "artifacts": entries}
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "output_contract_version": OUTPUT_CONTRACT_VERSION,
        "stage_id": stage_id,
        "stage_directory": spec["directory"],
        "created_at": _utc_now(),
        "run_status": "completed",
        "config_sha256": config_hash,
        "confirmation_receipt_sha256": receipt_hash,
        "source_fingerprint_sha256": run_manifest["source_fingerprint_sha256"],
        "upstream_stage_ids": spec["upstreams"],
        "upstream_stage_manifest_sha256": upstream_hashes,
        "dependency_versions": _dependency_versions(),
        "parameters": dict(config),
        "quality_gates": dict(quality_gates or {}),
        "warnings": [],
        "limitations": list(limitations or []),
        "artifact_inventory_sha256": file_sha256(inventory_path),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    run_manifest["stages"][stage_id] = {
        "directory": spec["directory"],
        "stage_manifest_sha256": file_sha256(manifest_path),
        "status": "completed",
    }
    _root_paths(root)["manifest"].write_text(json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
