---
name: credit-strategy-analysis
description: Use when 需要按数据确认、单规则挖掘、Lift TopN 组合、新旧准入策略效果与 Swap、最终报告的固定流程分析信贷规则策略。
---

# 信贷规则策略分析

本技能只做离线规则准入策略分析，不做生产上线、灰度、线上规则部署或审批结论。

## 五段流程

1. 读取 `references/00-data-product-analysis.md`，确认数据、产品、样本、颗粒度、标签、成熟规则、字段映射和旧策略。
2. 读取 `references/01-single-rule-mining.md`，挖掘 IV 支持的单规则、极端区间/分位点规则和最多 3 特征的 CART 路径。
3. 读取 `references/02-rule-combination.md`，按 Lift 降序选择用户确认的 TopN，级联拒绝形成新策略。
4. 读取 `references/03-strategy-evaluation-and-swap.md`，评估整体策略效果，并在有旧策略时做 Swap。
5. 读取 `references/04-final-report.md`，基于上游产物形成最终离线报告。

## 硬约束

- 产品、数据、颗粒度、字段映射、标签、成熟规则、金额口径、候选参数和 TopN 未确认时停止。
- `sample_id` 不是默认分析单位；跨颗粒度聚合必须由用户确认。
- 规则组合只能按确认的 Lift 排序和级联拒绝语义运行，任一命中即拒绝。
- `swap_in` 不是默认可观测表现；必须标记为估计或不可观测。
- 每个命令使用 `--config`、`--confirmation`、`--input`、`--output-dir`，先执行 `scripts/validate_contract.py`。
