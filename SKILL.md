---
name: credit-strategy-analysis
description: Use when 需要分析信贷风控策略、规则挖掘、规则回测、分数截断、策略模拟、Swap 分析、PSI 漂移、IV/KS/Lift 诊断或贷后策略监控。
---

# 信贷风控策略分析

## 概览

本 skill 是信贷风控策略分析的统一入口。它将原 `rule-analysis`、`risk-strategy-metrics` 和 `credit-strategy-skills` 的职责整合为一个可复现的离线分析流程。

本 skill 只做离线分析。不得设计、审批、部署或修改生产策略规则。

## 硬边界

本 skill 不做以下事项：

- 生产上线、灰度发布、流量分配、线上规则部署或审批材料生成。
- 完整 A 卡建模训练流程。
- 在产品形态、场景、标签窗口、成熟窗口、分数方向、金额分母等业务定义缺失时静默使用默认值。
- 将没有真实表现的拒绝样本当作已知好坏样本。
- 未经用户明确批准，将保护列作为规则挖掘特征；若用户批准例外，必须在报告中记录。

## 每次任务先问阻塞问题

运行任何分析前，必须确认以下字段。若必需答案缺失，停止并询问用户。

| 字段 | 何时必需 | 示例 |
|---|---|---|
| 产品形态 | 始终必需 | 循环贷、非循环贷、自定义 |
| 还款方式 | 始终必需 | 等额还款、一次性还本付息、自定义 |
| 应用场景 | 始终必需 | 首借准入、复借、额度、定价、支用、预警、规则复盘 |
| 任务类型 | 始终必需 | 规则挖掘、规则回测、分数截断、策略模拟、Swap、监控、报告 |
| 样本口径 | 始终必需 | 申请样本、通过样本、放款样本、成熟样本、拒绝样本 |
| 标签定义 | 涉及表现指标时必需 | DPD30+ MOB3、DPD60+、正样本定义 |
| 成熟样本规则 | 涉及表现指标时必需 | 成熟标识、观察窗口、是否剔除未成熟样本 |
| 金额定义 | 涉及金额指标时必需 | 逾期未还本金 / 支用金额 |
| 旧策略结果 | Swap 或规则复盘时必需 | 旧通过标识、拒绝码、规则命中字段 |
| 分数字段与方向 | 分数截断或分数策略时必需 | 高分高风险、高分低风险 |
| 路由字段 | 分路由分析时必需 | 渠道、产品、地区、分数段、客群 |

金额维度逾期率的默认建议为：

```text
sum(overdue_unpaid_principal) / sum(drawdown_amount)
```

这只是建议口径。计算前必须让用户确认分子、分母和样本过滤条件。

## 路由

阻塞问题确认后，路由到最小适用 reference。

| 用户意图 | Reference |
|---|---|
| 确认范围、询问必需问题、选择模块 | `references/00-scope-and-routing.md` |
| 产品形态、还款方式、场景矩阵 | `references/01-product-and-scenario.md` |
| 输入字段、保护列、标签和金额契约 | `references/02-data-contract.md` |
| 指标公式与解释 | `references/03-metric-definitions.md` |
| 查找候选阈值或规则 | `references/rules/01-rule-mining.md` |
| 重建已有规则或分析拒绝码 | `references/rules/02-rule-backtest.md` |
| 级联规则漏斗 | `references/rules/03-rule-funnel.md` |
| AND/OR/路由规则组合 | `references/rules/04-rule-combination.md` |
| 分数截断、分数分层、效率前沿 | `references/strategy/01-score-cutoff.md` |
| 离线通过/拒绝策略模拟 | `references/strategy/02-strategy-simulation.md` |
| 新旧策略对比 | `references/strategy/03-swap-analysis.md` |
| 分路由策略 | `references/strategy/04-routing-strategy.md` |
| PSI 漂移与监控 | `references/monitoring/01-psi-monitoring.md` |
| 规则命中率漂移 | `references/monitoring/02-rule-drift.md` |
| 表现漂移 | `references/monitoring/03-performance-drift.md` |
| HTML 报告结构 | `references/reporting/01-html-report.md` |

如果引用文件尚不存在，先使用 `references/00-scope-and-routing.md` 和 `design-framework.md` 作为临时依据；在实现对应脚本前，必须先补齐缺失 reference。

## 全局数据规则

金额字段必须拆分。不得用一个 `amount` 字段承载所有金额含义。

基础必需字段：

- `sample_id`
- `sample_date`
- `Y_label`

推荐金额字段：

- `drawdown_amount`
- `overdue_unpaid_principal`
- `outstanding_principal`
- `due_principal`

以下保护列默认不得作为候选规则特征：

```text
sample_id, sample_date, Y_label,
drawdown_amount, overdue_unpaid_principal, outstanding_principal, due_principal,
old_approval_flag, new_approval_flag,
old_reject_code, new_reject_code,
mature_flag, mob, dpd_max
```

## 输出标准

每个可执行分析模块应输出：

- CSV 明细表和汇总表，便于下游复核。
- JSON 配置或 manifest，记录输入路径、输出路径、行数、已确认业务定义和字段映射。
- 当用户要求业务可读交付物时，输出 HTML 报告。

所有输出必须使用 UTF-8 编码。比例类指标必须使用安全除法，分母为 0 时不得崩溃。

## 常见错误

| 错误 | 必须修正为 |
|---|---|
| 未确认产品、场景、样本、标签就开始分析 | 停止并询问 |
| 将 `amount` 当作通用金额字段 | 拆成明确的分子和分母字段 |
| 用所有可能阈值直接挖规则 | 使用候选阈值、最小命中样本/命中率和稳定性检查 |
| 只按 Lift 排序规则 | 同时输出命中率、坏客户捕获率、坏账率、未命中坏账率 |
| 将 Swap-in 表现当作真实观测 | 标记为估计值，并披露假设 |
| 将灰度或 AB 上线作为 skill 输出 | 删除；本 skill 只做离线分析 |

