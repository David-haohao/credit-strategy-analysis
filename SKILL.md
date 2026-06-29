---
name: credit-strategy-analysis
description: 用于离线信贷准入规则挖掘、规则组合、新旧策略效果比较、Swap 分析和最终报告。
---

# 信贷规则策略分析

仅用于离线策略分析：确认口径、挖掘规则、以 Lift 组合策略、评估新旧策略及 Swap，并生成报告。不包含模型训练、分数截断、线上发布、灰度或监控。

## 使用边界

- 产品、场景、样本、时间、分析粒度、字段映射、标签、成熟规则、金额口径、聚合规则和策略参数必须由用户确认；不得猜测。
- 不得从未确认的任意标识列推断分析单位；只可用已确认的 `id_cols` 生成分析单位。
- 规则候选不等于上线规则；报告不自动给出上线决策。
- 经确认的旧决策字段、审批结果字段、拒绝原因、既有模型输出和授信建议不能作为 `swap_in` 真实风险标签或预估特征。

## 固定输出契约

每次运行先读 `references/06-stage-output-contract.md`，再执行对应阶段。所有命令使用显式 `--run-dir`，且必须等于配置中的 `output.directory`。每阶段输出固定目录包、`stage_manifest.json` 与 `artifact_inventory.json`；最终 HTML/XLSX 报告只读已登记且哈希一致的上游聚合产物。

## 五段路由

按需读取当前阶段及其直接依赖，不得默认通读全部文档。

| 阶段 | 目的 | 必读文件 |
|---|---|---|
| 0 | 确认产品、数据、分析口径并初始化运行目录包 | `references/06-stage-output-contract.md`、`references/00-data-product-analysis.md` |
| 1 | 发现并检验单规则与受限 CART 路径 | `references/06-stage-output-contract.md`、`references/01-single-rule-mining.md` |
| 2 | 以 Lift TopN 构成级联拒绝策略 | `references/06-stage-output-contract.md`、`references/02-rule-combination.md` |
| 3 | 评估整体策略效果和新旧 Swap | `references/06-stage-output-contract.md`、`references/03-strategy-evaluation-and-swap.md`；估计 `swap_in` 风险时再读 `references/05-swap-in-risk-estimation.md` |
| 4 | 从既有、已校验产物生成最终报告 | `references/06-stage-output-contract.md`、`references/04-final-report.md` |

## 可执行入口

| 命令 | 输入与输出 |
|---|---|
| `scripts/validate_contract.py` | 校验配置、确认凭证、数据列和分析单位；以 `--run-dir` 写阶段 00。 |
| `scripts/rule_miner.py` | 校验阶段 01 契约；按确认的数值切点来源生成最小候选规则，并以 `--run-dir` 写固定阶段 01 包。 |
| `scripts/rule_combiner.py` | 校验 TopN、Lift 和级联语义；以 `--run-dir` 写固定阶段 02 包。 |
| `scripts/strategy_evaluator.py` | 校验策略与 Swap 可观测性；以 `--run-dir` 写固定阶段 03 包。 |
| `scripts/final_reporter.py` | 校验阶段 00 至 03 的 manifest/inventory/哈希；以 `--run-dir` 写阶段 04 自包含 HTML 与固定 11 Sheet XLSX。 |

当前 CLI 已覆盖阶段 0 契约校验、阶段 1 最小数值阈值候选、阶段 2 Lift TopN 级联漏斗/重叠、阶段 3 策略效果与 Swap 聚合，以及阶段 4 HTML/XLSX 目录报告。阶段 1 仍不执行完整 toad 分箱/WOE/IV、CART 路径生成或业务解释；未执行项必须在固定产物状态中标为 `not_available` 或 `not_applicable`。
