# 数据契约

本文定义 `credit-strategy-analysis` 的统一输入契约。所有规则挖掘、规则回测、分数截断、策略模拟、Swap、监控和报告任务都必须遵守本文。

## 1. 核心原则

1. 先确认业务口径，再读取数据和运行脚本。
2. 所有表现指标必须有明确标签定义和成熟样本口径。
3. 所有金额指标必须有明确分子、分母和样本过滤条件。
4. 金额字段必须拆分，不得用含义不清的 `amount` 直接计算金额逾期率。
5. 保护列默认不得作为规则挖掘特征。
6. 缺失必需字段时停止并询问用户，不得自动推断。

## 2. 契约层级

完整输入契约由六层组成：

| 层级 | 作用 | 是否必需 |
|---|---|---|
| 任务上下文 | 产品、还款方式、场景、任务类型 | 必需 |
| 样本口径 | 样本范围、时间字段、时间窗口、是否成熟 | 必需 |
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

## 5. 标签口径

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

## 6. 金额口径

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

## 7. 字段映射

### 7.1 基础字段

| 字段 | 是否必需 | 说明 |
|---|---|---|
| `id_col` | 必需 | 样本唯一标识 |
| `date_col` | 必需 | 申请、支用、放款或观测时间 |
| `target_col` | 表现指标必需 | 标签字段 |

### 7.2 分数任务字段

| 字段 | 何时必需 | 说明 |
|---|---|---|
| `score_col` | 分数截断、分数分层、分数策略 | 模型分 |
| `score_direction` | 分数任务 | `high_score_high_risk` 或 `high_score_low_risk` |
| `score_missing_policy` | 分数任务 | `exclude`、`separate_bin`、`impute` |

### 7.3 新旧策略字段

| 字段 | 何时必需 | 说明 |
|---|---|---|
| `old_approval_col` | Swap、规则复盘 | 旧策略通过标识 |
| `old_reject_code_col` | 拒绝码复盘 | 旧拒绝码 |
| `new_approval_col` | Swap | 新策略通过标识或模拟结果 |
| `new_reject_code_col` | Swap | 新策略拒绝码或模拟结果 |
| `route_col` | 分路由分析 | 渠道、产品、地区、客群或分数段 |

## 8. 特征策略

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
sample_id, sample_date, Y_label,
drawdown_amount, overdue_unpaid_principal, outstanding_principal, due_principal,
old_approval_flag, new_approval_flag,
old_reject_code, new_reject_code,
mature_flag, mob, dpd_max
```

## 9. 按任务的字段要求

| 任务 | 必需契约 |
|---|---|
| `rule_mining` | 任务上下文、样本口径、标签口径、特征策略 |
| `rule_backtest` | 任务上下文、样本口径、规则配置或拒绝码字段 |
| `rule_funnel` | 任务上下文、样本口径、有序规则或有序拒绝码 |
| `score_cutoff` | 任务上下文、样本口径、标签口径、分数字段与方向 |
| `strategy_simulation` | 任务上下文、样本口径、标签口径、候选规则或截断点 |
| `swap_analysis` | 任务上下文、样本口径、标签口径、旧策略结果、新策略结果 |
| `monitoring` | 任务上下文、监控字段、基准窗口、对比窗口 |
| `reporting` | 已完成分析输出、任务上下文、指标口径 |

## 10. 校验规则

执行脚本前必须校验：

1. 必需字段存在于输入数据。
2. `target_col` 可转换为二分类。
3. `positive_class` 存在于标签字段中。
4. 表现指标已定义成熟样本过滤。
5. 金额指标已定义分子、分母和过滤条件。
6. 保护列不在候选特征中，除非用户明确批准。
7. 分数字段缺失处理策略已确认。
8. Swap 任务同时有旧策略和新策略结果。
9. 日期字段可解析为日期。
10. 输出目录明确。

任何校验失败都应停止，并给出缺失字段或缺失口径清单。

## 11. 输出到 manifest

每次运行必须把最终确认的契约写入 `run_manifest.json`，至少包含：

```yaml
task_type:
product_form:
repayment_type:
scenario:
sample_scope:
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
  id_col:
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

