# 阶段 2：Lift TopN 规则组合

## 目的与输入

使用阶段 1 的合格单规则形成新准入策略。输入为候选规则表、用户确认的 `TopN`、最小样本/命中限制、排序指标和执行语义。

## 固定组合语义

1. 仅使用已通过样本覆盖限制的候选规则。
2. 按 Lift 降序排序；同 Lift 的并列处理规则由用户确认。
3. 选择用户确认的 TopN。
4. 按该顺序级联执行，任一命中即拒绝；后续规则只作用于前序规则未命中的剩余样本。
5. 每层输出新增拒绝、剩余样本、累计拒绝、边际坏客户捕获和边际好客户误伤。

## 伪代码

```text
eligible = filter_candidates_by_confirmed_minimums(candidates)
ordered = sort_descending(eligible, key="lift", tie_rule=confirmed)
selected = ordered.head(confirmed_top_n)
remaining = all_analysis_units
for rule in selected:
    hit = rule.evaluate(remaining)
    record_incremental_contribution(rule, hit, remaining)
    remaining = remaining - hit
new_approval = remaining
```

## 输出

- `02_topn_rules.csv`：Lift 排序、TopN 选择、规则条件与确认参数。
- `02_rule_funnel.csv`：规则顺序、进入、命中、新增拒绝、剩余、累计拒绝和边际贡献。
- `02_new_strategy_config.json`：级联拒绝策略定义。
- `02_manifest.json`：TopN、Lift 排序、并列处理和执行语义。

未确认 TopN、Lift 排序或级联拒绝语义时停止。不得将并联 OR、分路由或其他组合方式替代本阶段。
