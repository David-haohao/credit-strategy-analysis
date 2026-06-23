# 信贷规则策略 Skill 设计框架

> 版本: v5 | 状态: 五段规则策略主流程

## 目标

`credit-strategy-analysis` 只服务离线规则准入策略分析。它从已确认的数据和产品场景出发，挖掘候选规则，按 Lift 组合为新策略，评估策略效果与新旧 Swap，最后形成报告。不做生产上线、灰度、流量分配、线上规则部署或审批结论。

## 固定流程

| 阶段 | 目的 | 核心产物 |
|---|---|---|
| 0. 数据、产品与分析确认 | 确认产品、数据、样本、颗粒度、标签和旧策略 | 确认配置、字段映射、数据检查、manifest |
| 1. 单规则挖掘 | 用 IV 筛选特征，生成单规则和受限 CART 路径 | 单规则候选、IV/分箱明细、CART 路径 |
| 2. 规则组合 | 按 Lift 选择 TopN 并级联拒绝 | 组合配置、规则漏斗、边际贡献 |
| 3. 策略效果与 Swap | 评估新策略，比较旧策略 | 策略明细、总体效果、Swap 表 |
| 4. 最终报告 | 汇总已确认口径和阶段产物 | HTML 报告、最终 manifest |

阶段 0 是所有运行的前置条件。阶段 1-4 可在已提供上游产物时单独复跑，但不得跳过上游契约确认。

## 核心方法

### 单规则挖掘

- 数值特征候选来自极端区间、用户确认的分位点、缺失值和业务阈值。
- 类别特征候选来自确认的类别或类别组合。
- IV 用于筛选和审计特征；高 IV、小样本、全好/全坏箱和疑似穿越必须警告。
- CART 仅用于提取可解释的 AND 路径；每条路径不超过 3 个特征。
- 候选规则必须先通过用户确认的最小样本量和最小命中率，再参与 Lift 排序。

### 规则组合

- 合格单规则按 Lift 降序排列。
- `TopN` 由用户确认，不设默认值。
- 按排序顺序级联执行，任一命中即拒绝；每层只统计新增拒绝、剩余样本和边际风险贡献。

### 策略效果与 Swap

- 新策略由级联规则组成，统一输出通过率、拒绝率、成熟通过坏账率、坏客户捕获、好客户误伤及确认的金额指标。
- 有旧策略结果时，按 `both_pass`、`both_reject`、`swap_in`、`swap_out` 拆分。
- `swap_out` 只在可观测成熟表现上评估；`swap_in` 未经用户确认估计方法必须标记不可观测。

## 确认约束

产品、场景、样本口径、分析颗粒度、`id_cols`、字段映射、标签、成熟规则、金额分子/分母/过滤、最小样本、最小命中率、分位点、分箱、业务阈值和 `TopN` 都必须由用户确认。`sample_id` 不得作为默认分析单位。

## 文件结构

```text
credit-strategy-analysis/
├── SKILL.md
├── AGENTS.md
├── references/
│   ├── 00-data-product-analysis.md
│   ├── 01-single-rule-mining.md
│   ├── 02-rule-combination.md
│   ├── 03-strategy-evaluation-and-swap.md
│   └── 04-final-report.md
├── scripts/
│   ├── validate_contract.py
│   ├── rule_miner.py
│   ├── rule_combiner.py
│   ├── strategy_evaluator.py
│   └── final_reporter.py
├── schemas/
│   ├── input_contract.yaml
│   ├── confirmation_receipt.schema.json
│   ├── rule_combination.schema.json
│   ├── strategy_evaluation.schema.json
│   └── report_manifest.schema.json
└── templates/final_report.html.j2
```

脚本当前只提供前置校验和稳定 CLI；规则挖掘、组合和评估算法在后续实现阶段开发。
