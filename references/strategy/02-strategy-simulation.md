# 策略模拟

## 适用范围与阻断

用于比较规则、分数截断、分数 x 规则或分路由策略的离线通过/拒绝结果。它不生成线上部署方案。策略类型、通过/拒绝语义、冲突处理、路由覆盖、分析颗粒度、成熟表现和金额口径未确认时停止。

## 最小输入与按需引用

输入为确认的策略配置、分析单位、规则或分数字段、路由字段（如有）、标签和成熟规则、可选金额字段与旧策略结果。按需读取 `02-data-contract.md` 的策略字段、路由和金额，及 `03-metric-definitions.md` 的第 2、3、4、5、7 节；新旧策略对比另读 Swap 文件。

## 方法步骤

1. 将输入按确认的 `id_cols` 生成唯一分析单位；多行聚合必须在策略判断前按确认规则完成。
2. 校验策略配置：规则、截断、路由策略或组合策略只能使用已确认字段；保护列例外必须在 manifest 中存在。
3. 对规则策略按确认的顺序和命中语义生成决定；对分数策略按已确认方向和缺失分策略生成决定。
4. 对分数 x 规则策略，明确先分层还是先规则，以及冲突时拒绝/通过的优先级；对路由策略，确认每个路由的策略、未覆盖路由和缺失路由处理。
5. 输出样本级策略结果、规则/截断/路由原因和通过标识；不得只输出总体比例而无法审计样本变化。
6. 在成熟可观测样本上计算通过率、拒绝率、通过风险、拒绝风险（如可观测）、坏客户捕获、好客户误伤和确认的金额指标。
7. 若比较多个候选策略，在相同样本、相同成熟过滤和相同分析颗粒度下并列展示；不自动选取“最优”策略。
8. 对拒绝无表现、未覆盖路由、缺失策略字段和样本外推范围作单独披露。

## 候选参数

| 参数 | 可选方式 | 影响 |
|---|---|---|
| 策略类型 | 规则、截断、分数 x 规则、路由 | 决定决策引擎 |
| 规则语义 | 命中即拒绝、命中即通过或确认的多级动作 | 决定结果方向 |
| 组合顺序 | 先规则、先分数、顺序规则或并行规则 | 决定冲突处理 |
| 路由兜底 | 停止、统一策略或用户定义策略 | 决定未覆盖样本处理 |
| 比较总体 | 全样本、确认路由、成熟样本或其他范围 | 决定分母 |
| 金额口径 | 已确认分子、分母和过滤 | 决定金额风险结论 |

## 关键伪代码

```text
require confirmed(strategy_config, decision_semantics, analysis_grain)
units = build_confirmed_analysis_units(input)
validate_strategy_fields_and_route_coverage(units, strategy_config)

for unit in units:
    route = resolve_confirmed_route(unit)
    policy = resolve_confirmed_policy(route)
    decision, reasons = evaluate_policy(unit, policy, confirmed_order_and_conflict_rules)
    save_unit_level_result(unit, decision, reasons, route)

observed = filter_confirmed_mature_population(results)
metrics = summarize_strategy_results(results, observed, confirmed_amount_metric)
compare_candidates_on_identical_population_if_requested()
write_detail_summary_caveats_and_manifest()
```

## 输出

| 文件 | 最少字段 |
|---|---|
| `strategy_decision_detail.csv` | `analysis_unit_id`、路由、策略版本、通过标识、决策原因、规则/截断证据 |
| `strategy_summary.csv` | 策略、样本量、通过/拒绝量与比例、成熟表现、捕获/误伤、金额指标、可观测性标识 |
| `strategy_route_summary.csv` | 路由、覆盖量、策略、通过率、风险、缺失或兜底处理 |
| `strategy_simulation_manifest.json` | 策略配置、顺序、冲突处理、路由和确认口径 |

## 稳定性与可观测性

拒绝样本无真实表现时不得报告为观测风险。策略未覆盖某路由、路由字段为空、规则字段缺失、分析单位不唯一或比较样本不一致时必须停止或单列，不得自动借用其他路由或总体结论。

## 验收不变量

- 每个确认的分析单位仅有一个策略决定和可追溯原因。
- 所有候选策略在比较时使用相同总体、相同聚合和相同成熟过滤。
- 路由策略的覆盖、兜底和汇总权重均已确认。
- 指标分母、金额口径和可观测性状态均输出到汇总和 manifest。
- 模拟结果仅表达离线假设，不生成上线动作。
