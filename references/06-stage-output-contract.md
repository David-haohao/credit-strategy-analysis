# 阶段输出目录包契约

## 适用与阻断条件

所有五阶段运行必须先采用本契约。调用方必须显式提供 `--run-dir`，且它与 `input_config.yaml` 的 `output.directory` 解析后的绝对路径完全一致。

出现下列情形必须阻断：运行目录非空、路径越出 `run_dir`、上游 manifest 或产物哈希不一致、固定 CSV 缺失或字段变更、未登记来源进入 HTML、或尝试复制原始输入文件。

## 最小输入

- 已确认的 UTF-8 配置、确认凭证和原始输入文件；原始输入只记录路径与 SHA-256，不复制到运行目录。
- 阶段 0 的输入契约校验；阶段 1 至 4 还必须存在已校验的前序阶段目录包。
- 配置中的 `output.directory`、显式 `--run-dir`、产物契约版本 `1.2`。

## 方法步骤

1. 阶段 0 在根目录写入 `input_config.yaml`、`confirmation_receipt.json`、`run_manifest.json` 和 `source_fingerprint.json`。
2. 每一阶段写入固定子目录，并写入 `stage_manifest.json` 与 `artifact_inventory.json`。
3. inventory 逐项记录路径、状态、行数、字段、SHA-256、报告可用性及原因；manifest 记录参数、输入/上游哈希、依赖版本、门禁、警告与限制。
4. HTML/XLSX 报告仅读取阶段 00 至 03 的 manifest 和 inventory 所登记、且哈希一致的聚合产物；不扫描目录、不读取原始数据、不重新计算指标。
5. 已存在阶段默认阻断覆盖；只有 `resume` 且配置、确认凭证、输入指纹和上游哈希均一致时，才允许复用。

## 候选参数

| 参数 | 固定规则 |
|---|---|
| `output_contract_version` | `1.2`；产物名、最小字段或语义变化必须升版本。 |
| `--run-dir` | 必填、显式、不可使用隐式时间戳目录。 |
| `artifact_status` | 仅 `generated`、`not_applicable`、`not_available`、`failed`。 |
| `resume` | 默认 `false`；仅在四类哈希均一致时有效。 |
| 原始数据 | 不复制；禁止客户标识、原始 JSON、敏感原值进入阶段产物或 HTML。 |

## 关键伪代码

```python
assert resolve(config["output"]["directory"]) == resolve(run_dir)
assert target.resolve().is_relative_to(run_dir.resolve())
assert sha256(artifact) == inventory[artifact]["sha256"]
assert sha256(upstream_manifest) == stage_manifest["upstream_stage_manifest_sha256"][stage]
```

## 输出表

| 阶段目录 | 固定业务产物 |
|---|---|
| `00_data_contract` | `data_profile.csv`、`analysis_unit_check.csv`、`feature_governance.csv` |
| `01_rule_mining` | `feature_screening.csv`、`bin_iv_detail.csv`、`single_rule_candidates.csv`、`cart_path_candidates.csv`、`rule_stability.csv` |
| `02_rule_combination` | `lift_ranked_rules.csv`、`selected_rule_set.csv`、`cascade_funnel.csv`、`rule_overlap.csv`、`cascade_oot.csv` |
| `03_strategy_evaluation` | `strategy_effect_summary.csv`、`strategy_layer_effect.csv`、`swap_summary.csv`、`swap_segment_detail.csv`、`swap_in_risk_estimate.csv`、`swap_in_coverage.csv` |
| `04_final_report` | `final_report.html`、`final_report.xlsx`、`report_source_index.csv`、`report_validation.csv` |

所有固定 CSV 均写 UTF-8 表头。无 OOT 时 `rule_stability.csv`、`cascade_oot.csv` 标注“未评估（未做时间外验证）”；无成熟表现或第三方分时 Swap-in 风险估计明确标为不可观测或不可估计，不得用旧决策字段、审批结果字段或代理标签替代真实坏账标签。

阶段 01 的单调性审查是固定契约的一部分：`feature_screening.csv` 必须包含 `monotonicity`，取值为 `increasing`、`decreasing`、`flat`、`non_monotonic` 或 `not_evaluated`；`bin_iv_detail.csv` 必须包含 `bin_order` 与 `bad_rate`，用于按分箱顺序复核特征与坏样本率的方向关系。缺失箱应单独输出，但不参与有效分箱方向判定。

## 稳定性与可观测性检查

- 规则、分箱和组合表内的 `feature_name` 必须遵守当次配置中确认的 `feature_policy.exclude_features` 与 `feature_policy.excluded_name_tokens`。
- 任意原始 JSON、客户标识或敏感字段名进入产物即失败。
- 稳定性、OOT、成熟表现和 Swap-in 风险估计是否可观测，必须写入 artifact 状态与原因；空表不能被解读为零风险或零效果。

## 验收不变量

- 每阶段有且只有契约声明的业务产物，并同时具备 `stage_manifest.json`、`artifact_inventory.json`。
- 所有可报告产物均可从 `report_source_index.csv` 回溯到路径和 SHA-256。
- `final_report.html` 自包含，`final_report.xlsx` 固定 11 个 Sheet；二者均不依赖未登记的目录扫描、原始数据或外部图表文件。
- 任何产物内容、字段或语义变化必须通过新测试并提升 `output_contract_version`。
