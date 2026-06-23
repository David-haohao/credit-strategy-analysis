# 数据契约

本文定义 `credit-strategy-analysis` 的统一输入契约。所有规则挖掘、规则回测、分数截断、策略模拟、Swap、监控和报告任务都必须遵守本文。

## 读取规则

本文是按需词典，不是每个任务的默认阅读内容。先读 `00-scope-and-routing.md`，再只读取当前任务涉及的字段映射、分析颗粒度、标签、金额、策略字段或表现期章节。

## 1. 核心原则

1. 先确认业务口径，再读取数据和运行脚本。
2. 所有表现指标必须有明确标签定义和成熟样本口径。
3. 所有金额指标必须有明确分子、分母和样本过滤条件。
4. 金额字段必须拆分，不得用含义不清的 `amount` 直接计算金额逾期率。
5. 保护列默认不得作为规则挖掘特征。
6. 统一字段名是语义契约，不要求原始数据提前改名。
7. 读取 input 后可以生成字段映射候选，但候选必须经用户确认后才能运行。
8. 缺失必需字段时停止并询问用户，不得自动推断。

## 2. 契约层级

完整输入契约由七层组成：

| 层级 | 作用 | 是否必需 |
|---|---|---|
| 任务上下文 | 产品、还款方式、场景、任务类型 | 必需 |
| 样本口径 | 样本范围、时间字段、时间窗口、是否成熟 | 必需 |
| 分析颗粒度 | 客户级、申请级、借据级、支用级、客户-时间窗及聚合规则 | 必需 |
| 标签口径 | 目标字段、正样本、坏样本定义、成熟窗口 | 涉及表现指标时必需 |
| 金额口径 | 金额分子、分母、公式、过滤条件 | 涉及金额指标时必需 |
| 字段映射 | ID、日期、分数、路由、新旧策略结果等字段 | 按任务必需 |
| 特征策略 | 候选特征、排除字段、保护列例外 | 规则挖掘时必需 |

## 3. 任务上下文

| 字段 | 说明 | 示例 |
|---|---|---|
| `product_form` | 产品形态 | `revolving`、`non_revolving`、`custom` |
| `repayment_type` | 还款方式 | `equal_payment`、`bullet`、`custom` |
| `scenario` | 策略场景 | `first_loan_admission`、`reloan`、`drawdown`、`rule_review` |
| `task_type` | 主任务类型 | `rule_mining`、`score_cutoff`、`swap_analysis` |

若产品为 `custom`，必须补充文字说明，包括是否有额度、是否多次支用、还款方式和支用是否二次审批。

## 4. 样本口径

| 字段 | 说明 | 示例 |
|---|---|---|
| `population` | 样本范围 | `application`、`approved`、`booked`、`mature_booked`、`rejected`、`mixed` |
| `date_col` | 样本日期字段 | `sample_date`、`apply_date`、`drawdown_date` |
| `start_date` | 样本开始日期 | `2026-01-01` |
| `end_date` | 样本结束日期 | `2026-03-31` |
| `mature_flag_col` | 成熟样本标识 | `mature_flag` |
| `include_immature` | 是否包含未成熟样本 | `false` |

表现类指标默认不允许混入未成熟样本。若用户要求包含未成熟样本，报告必须标注偏差风险。

## 5. 分析颗粒度

分析颗粒度决定 `sample_cnt`、通过率、拒绝率、规则命中率和坏账率等指标的分母。不得默认把 `sample_id` 当作唯一分析单位。

| 字段 | 说明 | 示例 |
|---|---|---|
| `grain` | 当前分析单位 | `customer`、`application`、`loan`、`drawdown`、`customer_window` |
| `id_cols` | 与分析单位一致的唯一标识字段，允许多列组合 | `customer_id`、`loan_id`、`customer_id + observation_month` |
| `customer_id_col` | 客户 ID 字段 | `customer_id` |
| `application_id_col` | 申请 ID 字段 | `application_id` |
| `loan_id_col` | 借据 ID 字段 | `loan_id` |
| `drawdown_id_col` | 支用 ID 字段 | `drawdown_id` |
| `label_grain` | 标签所在颗粒度 | `loan`、`drawdown` |
| `feature_grain` | 特征所在颗粒度 | `customer` |
| `output_grain` | 报告输出颗粒度 | `customer` |
| `aggregation_rule` | 跨颗粒度聚合规则 | `any_bad_to_customer`、`latest_loan` |

循环贷场景尤其需要确认颗粒度：0/1 标签可能基于借据或支用，一个客户可能有多个借据或多次支用；贷前特征通常是人维度。若输出人维度指标，必须先请用户确认如何从借据或支用聚合到客户。

以下常见聚合规则只作为候选项，用于向用户提问，不得自动采用：

| 聚合规则 | 含义 |
|---|---|
| `any_bad_to_customer` | 任一借据或支用坏，则客户为坏 |
| `max_label` | 取同一客户下标签最大值 |
| `latest_loan` | 取最新借据标签 |
| `first_loan` | 取首笔借据标签 |
| `window_aggregation` | 在确认的时间窗内聚合 |

若分析颗粒度缺失，必须停止并询问。若标签、特征和输出颗粒度不一致，但聚合规则缺失，也必须停止。

## 6. 标签口径

| 字段 | 说明 | 示例 |
|---|---|---|
| `target_col` | 标签字段 | `Y_label` |
| `positive_class` | 坏样本取值 | `1` |
| `bad_definition` | 坏样本定义 | `DPD30_plus_MOB3` |
| `maturity_rule` | 成熟窗口或规则 | `MOB >= 3`、`mature_flag == 1` |
| `exclude_values` | 需要剔除的标签值 | `[2]` 表示未成熟或未知 |

要求：

1. 标签必须是二分类或可映射为二分类。
2. 正样本必须显式定义。
3. 不能把未知、未成熟、拒绝无表现样本当作真实好坏样本。

## 7. 金额口径

金额字段必须明确分子和分母。

推荐默认口径：

```text
amount_bad_rate = sum(overdue_unpaid_principal) / sum(drawdown_amount)
```

| 字段 | 说明 |
|---|---|
| `numerator` | 金额指标分子，默认建议 `overdue_unpaid_principal` |
| `denominator` | 金额指标分母，默认建议 `drawdown_amount` |
| `formula` | 计算公式 |
| `filter` | 金额指标适用样本过滤 |

可用金额字段：

| 字段 | 含义 | 是否可作为规则特征 |
|---|---|---|
| `drawdown_amount` | 支用金额或实际放款金额 | 默认禁止 |
| `overdue_unpaid_principal` | 逾期未还本金 | 禁止 |
| `outstanding_principal` | 当前未还本金余额 | 默认禁止 |
| `due_principal` | 到期应还本金 | 默认禁止 |

不得从单一 `amount` 字段直接计算金额维度逾期率。若源数据只有 `amount`，必须让用户确认它代表支用金额、放款金额、余额还是到期应还本金，并映射到明确字段。

## 8. 字段映射

字段映射分两步完成：

1. 读取 input 的列名、类型和样例值，生成候选映射。
2. 将候选映射展示给用户确认；确认前不得执行分析。

统一契约字段是内部语义标准，用于脚本、报告和 manifest 对齐。原始数据列名可以不同，例如 `cust_no`、`uid`、`user_id` 都可能是客户 ID 候选，但必须由用户确认后才能映射到 `customer_id_col`。

若同一列可能对应多个语义，或多个列可能对应同一语义，必须停止并询问用户。不得仅凭字段名自动决定。

### 8.1 基础字段

| 字段 | 是否必需 | 说明 |
|---|---|---|
| `id_cols` | 必需 | 与分析颗粒度一致的唯一标识字段，允许多列组合 |
| `date_col` | 必需 | 申请、支用、放款或观测时间 |
| `target_col` | 表现指标必需 | 标签字段 |

### 8.2 ID 字段

| 字段 | 何时必需 | 说明 |
|---|---|---|
| `customer_id_col` | 客户级、人维聚合或贷前特征分析 | 客户唯一标识 |
| `application_id_col` | 申请级分析 | 申请唯一标识 |
| `loan_id_col` | 借据级标签或借据级输出 | 借据唯一标识 |
| `drawdown_id_col` | 支用级标签或支用级输出 | 支用唯一标识 |

`sample_id` 只作为可选字段。若脚本需要统一分析 ID，应根据用户确认的 `id_cols` 生成 `analysis_unit_id`，并写入 manifest。

### 8.3 分数任务字段

| 字段 | 何时必需 | 说明 |
|---|---|---|
| `score_col` | 分数截断、分数分层、分数策略 | 模型分 |
| `score_direction` | 分数任务 | `high_score_high_risk` 或 `high_score_low_risk` |
| `score_missing_policy` | 分数任务 | `exclude`、`separate_bin`、`impute` |

### 8.4 新旧策略字段

| 字段 | 何时必需 | 说明 |
|---|---|---|
| `old_approval_col` | Swap、规则复盘 | 旧策略通过标识 |
| `old_reject_code_col` | 拒绝码复盘 | 旧拒绝码 |
| `new_approval_col` | Swap | 新策略通过标识或模拟结果 |
| `new_reject_code_col` | Swap | 新策略拒绝码或模拟结果 |
| `route_col` | 分路由分析 | 渠道、产品、地区、客群或分数段 |

## 9. 特征策略

规则挖掘必须明确候选特征和排除规则。

| 配置 | 说明 |
|---|---|
| `candidate_features` | 明确候选特征列表；为空时表示从非保护列中自动选择 |
| `exclude_features` | 用户指定排除字段 |
| `protected_columns` | 默认保护列 |
| `allow_protected_override` | 是否允许用户覆盖保护列规则 |
| `protected_override_reason` | 覆盖原因，必须写入报告 |

默认保护列：

```text
sample_id, customer_id, application_id, loan_id, drawdown_id,
sample_date, Y_label,
drawdown_amount, overdue_unpaid_principal, outstanding_principal, due_principal,
old_approval_flag, new_approval_flag,
old_reject_code, new_reject_code,
mature_flag, mob, dpd_max
```

## 10. 按任务的字段要求

| 任务 | 必需契约 |
|---|---|
| `rule_mining` | 任务上下文、样本口径、分析颗粒度、标签口径、特征策略 |
| `rule_backtest` | 任务上下文、样本口径、分析颗粒度、规则配置或拒绝码字段 |
| `rule_funnel` | 任务上下文、样本口径、分析颗粒度、有序规则或有序拒绝码 |
| `score_cutoff` | 任务上下文、样本口径、分析颗粒度、标签口径、分数字段与方向 |
| `strategy_simulation` | 任务上下文、样本口径、分析颗粒度、标签口径、候选规则或截断点 |
| `swap_analysis` | 任务上下文、样本口径、分析颗粒度、标签口径、旧策略结果、新策略结果 |
| `monitoring` | 任务上下文、分析颗粒度、监控字段、基准窗口、对比窗口 |
| `reporting` | 已完成分析输出、任务上下文、指标口径 |

## 11. 校验规则

执行脚本前必须校验：

1. 必需字段存在于输入数据。
2. 字段映射已经用户确认，而不是仅由脚本候选匹配得出。
3. 分析颗粒度已确认，`id_cols` 能唯一标识该颗粒度。
4. 标签颗粒度、特征颗粒度和输出颗粒度不一致时，聚合规则已确认。
5. `target_col` 可转换为二分类。
6. `positive_class` 存在于标签字段中。
7. 表现指标已定义成熟样本过滤。
8. 金额指标已定义分子、分母和过滤条件。
9. 保护列不在候选特征中，除非用户明确批准。
10. 分数字段缺失处理策略已确认。
11. Swap 任务同时有旧策略和新策略结果。
12. 日期字段可解析为日期。
13. 输出目录明确。

任何校验失败都应停止，并给出缺失字段或缺失口径清单。

## 12. 输出到 manifest

每次运行必须把最终确认的契约写入 `run_manifest.json`，至少包含：

```yaml
task_type:
product_form:
repayment_type:
scenario:
sample_scope:
analysis_grain:
  grain:
  id_cols:
  customer_id_col:
  application_id_col:
  loan_id_col:
  drawdown_id_col:
  label_grain:
  feature_grain:
  output_grain:
  aggregation_rule:
field_mapping:
  mode:
  confirmed:
  candidate_columns:
  unmapped_required_fields:
label:
  target_col:
  positive_class:
  bad_definition:
  maturity_rule:
amount_metric:
  numerator:
  denominator:
  formula:
  filter:
columns:
  id_cols:
  date_col:
  score_col:
  score_direction:
  route_col:
  old_approval_col:
  old_reject_code_col:
feature_policy:
  candidate_features:
  exclude_features:
  protected_columns:
  protected_overrides:
input:
  path:
  row_count:
output:
  directory:
  files:
```
