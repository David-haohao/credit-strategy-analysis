# 范围与路由

本文定义 `credit-strategy-analysis` 的全局入口协议。除非用户只询问某个指标定义，否则每次任务都从这里开始。

## 1. 范围

本 skill 支持离线信贷策略分析：

- 产品与场景确认。
- 数据契约校验。
- 规则挖掘和候选阈值发现。
- 规则回测、拒绝码分析和级联漏斗复盘。
- 分数截断分析和效率前沿。
- 策略模拟。
- Swap-in / Swap-out 对比。
- IV、KS、AUC、Lift、PSI、坏账率趋势和漂移监控。
- CSV、JSON 和 HTML 分析报告。

本 skill 不支持：

- 生产上线或上线方案。
- 灰度发布、线上流量分配或生产规则部署。
- 审批材料生成。
- 完整 A 卡建模训练。
- 对业务定义使用静默默认值。

## 2. 入口顺序

按以下顺序提问。遇到第一个阻塞缺口时停止。

### Step 1：产品上下文

确认：

1. 产品形态：循环贷、非循环贷或自定义。
2. 还款方式：等额还款、一次性还本付息或自定义。
3. 应用场景：首借、复借、额度、定价、支用、贷中调整、预警、规则复盘或新旧策略对比。

如果用户给出非标准产品，继续询问：

- 是否存在可复用额度。
- 是否允许多次支用。
- 还款方式是等额、一次性还本付息，还是混合。
- 支用时是否需要二次审批。

### Step 2：任务类型

将用户请求映射为一个主任务类型。

| 任务类型 | 用户意图 |
|---|---|
| `score_cutoff` | 优化模型分截断、分数分层、通过率和坏账率 trade-off |
| `rule_mining` | 寻找候选规则、阈值、高风险分群 |
| `rule_backtest` | 分析已有规则、拒绝码、离线规则引擎结果 |
| `rule_funnel` | 复盘级联规则贡献和剩余人群 |
| `strategy_simulation` | 模拟候选规则或截断点对通过/拒绝的影响 |
| `swap_analysis` | 比较旧策略和新策略 |
| `monitoring` | 检查 PSI、规则漂移、通过率漂移、坏账率漂移 |
| `reporting` | 基于已完成分析输出业务可读报告 |
| `metric_definition` | 只解释公式或指标含义 |

如果用户一次请求多个任务，优先选择能为后续任务产出输入的任务。例如“挖规则并模拟策略”应先路由到 `rule_mining`，再进入 `strategy_simulation`。

### Step 3：样本与标签契约

确认：

- 样本口径：申请、通过、放款、成熟、拒绝或混合。
- 分析颗粒度：客户级、申请级、借据级、支用级或客户-时间窗。
- 目标字段和正样本定义。
- 坏样本定义，例如 DPD30+ MOB3。
- 是否剔除未成熟样本。
- 日期字段和观察窗口。

如果用户要求表现指标，但成熟样本定义缺失，停止并询问。

如果分析颗粒度缺失，停止并询问。不得默认使用 `sample_id` 作为样本单位。

循环贷常见情况：

- 0/1 标签可能在借据级或支用级生成。
- 同一客户可能有多个借据或多次支用。
- 贷前特征通常是客户级。
- 若需要输出人维度指标，必须确认从借据/支用级到客户级的聚合规则，例如 `max(Y_label)`、任一借据逾期即客户逾期、最近一笔借据、首笔借据或按观察窗聚合。

### Step 4：金额契约

当用户要求金额维度指标时，确认：

- 分子字段。
- 分母字段。
- 是否只过滤通过、放款或成熟样本。

默认建议：

```text
amount_bad_rate = sum(overdue_unpaid_principal) / sum(drawdown_amount)
```

不得从含义不明确的 `amount` 字段直接计算金额维度逾期率。

### Step 5：策略输入

对于新旧策略对比或规则复盘，确认数据是否包含：

- `old_approval_flag`
- `old_reject_code`
- 旧规则命中字段
- 规则执行顺序
- `new_approval_flag` 或新策略配置

对于分数任务，确认：

- 分数字段。
- 分数方向。
- 分数缺失样本是剔除、填补，还是作为单独分群。

对于分路由任务，确认路由字段，以及是否每个路由都需要单独阈值或规则。

## 3. 路由表

| 主任务 | 必需 reference | 阻塞输入 |
|---|---|---|
| `score_cutoff` | `references/strategy/01-score-cutoff.md` | 分数字段、分数方向、分析颗粒度、标签、成熟样本 |
| `rule_mining` | `references/rules/01-rule-mining.md` | 特征字段、分析颗粒度、标签、样本口径、保护列 |
| `rule_backtest` | `references/rules/02-rule-backtest.md` | 分析颗粒度、规则配置或拒绝码，若为级联则需要规则顺序 |
| `rule_funnel` | `references/rules/03-rule-funnel.md` | 分析颗粒度、有序规则或有序拒绝码 |
| `strategy_simulation` | `references/strategy/02-strategy-simulation.md` | 候选规则/截断点、分析颗粒度、样本口径、标签 |
| `swap_analysis` | `references/strategy/03-swap-analysis.md` | 旧策略结果、新策略结果、分析颗粒度、成熟样本 |
| `monitoring` | `references/monitoring/01-psi-monitoring.md` | 分析颗粒度、基准窗口、对比窗口、监控字段 |
| `reporting` | `references/reporting/01-html-report.md` | 已完成分析输出和已确认业务定义 |

如果必需 reference 文件缺失，必须先写该 reference，再实现对应脚本。

## 4. 停止规则

出现以下情况时，停止并询问用户：

- 产品形态、还款方式或应用场景缺失。
- 任务类型不清楚。
- 分析颗粒度缺失。
- 标签颗粒度、特征颗粒度和输出颗粒度不一致，但聚合规则缺失。
- 用户要求表现指标，但标签或成熟样本定义缺失。
- 用户要求金额指标，但分子或分母缺失。
- 用户要求 Swap，但旧策略或新策略结果缺失。
- 用户要求分数截断，但分数方向缺失。
- 用户要求分路由分析，但路由字段缺失。
- 数据集中不存在必需字段。

不得用猜测补齐这些缺口。

## 5. 保护列

以下保护列默认不得作为规则挖掘特征：

```text
sample_id, customer_id, application_id, loan_id, drawdown_id,
sample_date, Y_label,
drawdown_amount, overdue_unpaid_principal, outstanding_principal, due_principal,
old_approval_flag, new_approval_flag,
old_reject_code, new_reject_code,
mature_flag, mob, dpd_max
```

如果用户明确要求覆盖该规则，必须在运行 manifest 和报告中记录例外。

## 6. 输出契约

每个可执行模块应写出：

- 有行级结果时，输出行级明细文件。
- 汇总 CSV。
- 记录已确认业务定义的 JSON manifest。
- 简洁控制台摘要，包括输入路径、输出目录、行数和核心指标。

manifest 必须记录：

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
label:
  target_col:
  positive_class:
  bad_definition:
  maturity_rule:
amount_metric:
  numerator:
  denominator:
  formula:
columns:
  id_cols:
  date_col:
  score_col:
  route_col:
input:
  path:
  row_count:
output:
  directory:
  files:
```

## 7. 脚本运行前检查清单

运行任何脚本前，确认：

- 所选模块与用户请求一致。
- 该模块所有阻塞输入均已确认。
- 必需字段存在。
- 保护列已从特征挖掘中排除。
- 如果包含金额指标，金额公式明确。
- 如果包含表现指标，成熟样本过滤明确。
- 输出目录明确。
