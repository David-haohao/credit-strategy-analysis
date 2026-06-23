---
name: credit-strategy-analysis
description: Use when 需要分析信贷风控策略、规则挖掘、规则回测、分数截断、策略模拟、Swap 分析、PSI 漂移、IV/KS/Lift 诊断或贷后策略监控。
---

# 信贷风控策略分析

## 定位

这是信贷风控策略分析的统一入口，只做离线分析：规则挖掘、规则回测、分数截断、策略模拟、Swap 对比、指标诊断、监控与报告。不做生产上线、灰度发布、流量切换、线上规则部署或审批材料。

## 路由

先读 `references/00-scope-and-routing.md`，确认阻塞项后按路由只读取任务所需的契约、指标和方法文件：

| 意图 | 方法文件 |
|---|---|
| 产品与场景 | `references/01-product-and-scenario.md` |
| 规则挖掘 | `references/rules/01-rule-mining.md` |
| 规则回测、漏斗、组合 | `references/rules/02-rule-backtest.md`、`03-rule-funnel.md`、`04-rule-combination.md` |
| 分数截断、策略模拟 | `references/strategy/01-score-cutoff.md`、`02-strategy-simulation.md` |
| Swap、分路由 | `references/strategy/03-swap-analysis.md`、`04-routing-strategy.md` |
| 监控漂移 | `references/monitoring/` |
| 报告生成 | `references/reporting/01-html-report.md` |
| 只问指标 | `references/03-metric-definitions.md` 的相关章节 |

## 全局规则

- 颗粒度、字段映射、聚合、标签、成熟规则、金额口径、分数方向和路由不得推断；确认要求详见路由卡和数据契约。
- 保护列不得作为规则特征；候选阈值、分箱和稳定性参数均需用户确认。
- Swap-in 不得当作直接观测表现；每个可执行分析均输出 UTF-8 文件和 manifest。
- 每个命令均要求 `--config`、`--confirmation`、`--input`、`--output-dir`，并先执行 `scripts/validate_contract.py`。
