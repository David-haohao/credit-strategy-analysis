---
name: credit-strategy-analysis
description: 用于离线信贷准入规则挖掘、规则组合、新旧策略效果比较、Swap 分析和最终报告。
---

# 信贷规则策略分析

本技能只处理离线规则策略分析：先确认数据与产品，再挖掘规则、按 Lift 组合为准入策略、评估新旧策略差异，最后形成报告。它不包含模型训练、分数截断、线上发布、灰度或监控。

## 使用边界

- 任何产品、场景、样本、颗粒度、字段映射、标签、成熟规则、金额口径和跨颗粒度聚合均须用户确认。
- 不得将 `sample_id` 默认视为分析单位；仅使用确认后的 `id_cols` 生成 `analysis_unit_id`。
- 候选字段映射、经验阈值、TopN、最小样本、分箱数、分位点和业务阈值均不能静默默认。
- 规则候选不是上线规则；报告不自动生成上线决策。

## 五段路由

按任务按需读取当前阶段及其直接依赖，不得默认通读全部文档。

| 阶段 | 目的 | 读取文件 |
|---|---|---|
| 0 | 确认产品、数据和分析口径 | `references/00-data-product-analysis.md` |
| 1 | 发现并检验单规则与受限 CART 路径 | `references/01-single-rule-mining.md` |
| 2 | 以 Lift TopN 构成级联拒绝规则 | `references/02-rule-combination.md` |
| 3 | 评估新策略整体效果及新旧 Swap | `references/03-strategy-evaluation-and-swap.md` |
| 4 | 基于既有产物生成最终报告 | `references/04-final-report.md` |

## 可执行入口

| 命令 | 前置校验 |
|---|---|
| `scripts/validate_contract.py` | 配置、确认凭证、数据列和分析单位 |
| `scripts/rule_miner.py` | 阶段 1 契约及 `toad` 依赖 |
| `scripts/rule_combiner.py` | 阶段 2 的 TopN、Lift 排序和级联语义 |
| `scripts/strategy_evaluator.py` | 阶段 3 的策略和 Swap 可观测性 |
| `scripts/final_reporter.py` | 阶段 4 的来源 manifest 与确认凭证 |

除 `validate_contract` 外，其余命令当前只完成前置校验和 manifest 写入，并明确返回“算法尚未实现”。
