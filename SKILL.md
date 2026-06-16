---
name: credit-strategy-analysis
description: Use when 需要分析信贷风控策略、规则挖掘、规则回测、分数截断、策略模拟、Swap 分析、PSI 漂移、IV/KS/Lift 诊断或贷后策略监控。
---

# 信贷风控策略分析

## 定位

这是信贷风控策略分析的统一入口，整合 `rule-analysis`、`risk-strategy-metrics` 和原策略框架能力。

只做离线分析：规则挖掘、规则回测、分数截断、策略模拟、Swap 对比、指标诊断、监控与报告。不做生产上线、灰度发布、流量切换、线上规则部署或审批材料。

## 启动前必须确认

任何分析执行前，先确认阻塞项；缺失则停止并询问，不得静默默认。

必问：

- 产品形态：循环贷、非循环贷或自定义。
- 还款方式：等额、一次性还本付息或自定义。
- 应用场景：首借、复借、额度、定价、支用、贷中、预警、规则复盘或新旧策略对比。
- 任务类型：规则挖掘、规则回测、分数截断、策略模拟、Swap、监控或报告。
- 样本口径：申请、通过、放款、成熟、拒绝或混合。

按需必问：

- 表现指标：标签定义、正样本、成熟样本规则。
- 金额指标：分子、分母、样本过滤。默认建议为 `sum(overdue_unpaid_principal) / sum(drawdown_amount)`，但必须由用户确认。
- 分数任务：分数字段、分数方向、缺失分处理。
- Swap/复盘：旧策略结果、新策略结果、拒绝码或规则命中字段。
- 分路由任务：路由字段及是否分路由建规则/阈值。

## 路由

先读 `references/00-scope-and-routing.md`。确认任务后进入对应 reference：

| 意图 | Reference |
|---|---|
| 产品与场景 | `references/01-product-and-scenario.md` |
| 数据契约 | `references/02-data-contract.md` |
| 指标定义 | `references/03-metric-definitions.md` |
| 规则挖掘 | `references/rules/01-rule-mining.md` |
| 规则回测 | `references/rules/02-rule-backtest.md` |
| 规则漏斗 | `references/rules/03-rule-funnel.md` |
| 规则组合 | `references/rules/04-rule-combination.md` |
| 分数截断 | `references/strategy/01-score-cutoff.md` |
| 策略模拟 | `references/strategy/02-strategy-simulation.md` |
| Swap 分析 | `references/strategy/03-swap-analysis.md` |
| 分路由策略 | `references/strategy/04-routing-strategy.md` |
| 监控漂移 | `references/monitoring/` |
| 报告生成 | `references/reporting/01-html-report.md` |

如果目标 reference 尚未创建，先基于 `design-framework.md` 补齐 reference，再实现脚本。

## 全局规则

- 不使用含义不清的 `amount` 直接计算金额逾期率；金额字段必须拆成明确分子和分母。
- 保护列默认不得作为规则特征：ID、日期、标签、金额结果、审批结果、拒绝码、成熟标识、MOB、DPD。
- 单规则挖掘不得默认遍历所有可能阈值；使用候选阈值、最小命中样本/命中率和稳定性检查。
- 规则排序不得只看 Lift；同时看命中率、坏账率、坏客户捕获率和未命中坏账率。
- Swap-in 表现通常不是观测值，必须标注估计假设和偏差风险。
- 每个可执行分析应输出 UTF-8 CSV/JSON；业务交付物按需输出 HTML。

