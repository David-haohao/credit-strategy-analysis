# 阶段 3：策略效果与 Swap

## 目的与输入

评估阶段 2 形成的新准入策略，并在旧策略结果存在时做新旧 Swap。输入为新策略样本级结果、确认的成熟标签、金额口径和可选旧策略通过/拒绝结果。

## 整体策略效果

以确认分析单位计算：

- `approval_rate`、`reject_rate`
- `pass_bad_rate`、`reject_bad_rate`（仅有真实表现时）
- 坏客户捕获、好客户误伤
- 确认的金额风险指标

未成熟、未知标签和拒绝无真实表现样本不得混入观测风险指标。

## Swap

当旧策略存在时，按新旧通过结果分为 `both_pass`、`both_reject`、`swap_in`、`swap_out`。

- `swap_out` 仅在旧策略通过且有成熟表现时计算直接观测风险和捕获。
- `swap_in` 在旧策略下通常没有表现；未确认估计方法时必须标记为不可观测，不得当作真实坏账率。
- 所有分群可按用户确认的产品、渠道或时间分层，但不引入分路由策略。

## 伪代码

```text
new_result = apply_selected_sequential_reject_rules(all_units)
evaluate_new_strategy_on_confirmed_mature_population(new_result)
if old_strategy_result_exists:
    groups = split_into_both_pass_both_reject_swap_in_swap_out(old, new)
    evaluate_observable_groups(groups)
    label_swap_in_as_estimated_or_unobservable()
```

## 输出

- `03_strategy_summary.csv`：通过、拒绝、成熟风险、捕获、误伤和金额指标。
- `03_strategy_detail.csv`：分析单位、新策略结果、规则命中和可观测性状态。
- `03_swap_summary.csv`、`03_swap_detail.csv`：四类 Swap 人群及直接观测/估计/不可观测标记。
- `03_manifest.json`：新策略版本、旧策略字段、成熟规则和金额口径。
