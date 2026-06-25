# 阶段 3：策略效果与 Swap 评估

## 适用与阻断条件

用于把阶段 2 的级联拒绝规则视为新准入策略，统一评估策略效果；当旧策略结果可用时，对齐新旧决策并进行 Swap 分析。它不改变规则顺序、阈值或 TopN，也不对不可观测样本制造表现标签。

新策略决策、成熟标签、样本总体、指标口径或金额定义未确认时停止。若开启新旧比较，旧/新决策字段、比较总体和 `swap_in` 可观测性处理均须确认。

## 最小输入

- 阶段 0 的确认凭证、成熟样本、`analysis_unit_id`、标签、金额口径和旧策略字段（如有）。
- 阶段 2 的 `cascade_funnel.csv`、样本级新策略决策和组合 manifest。
- 确认的通过/拒绝定义，以及新策略拒绝规则命中明细。
- 旧策略比较启用时：旧/新决策列、共同样本范围、分层字段、`swap_in` 为估计或不可观测的声明；估计时还需确认方法。

## 方法步骤

1. 对齐阶段 2 的新策略决策和阶段 0 的成熟表现，确认每个 `analysis_unit_id` 仅出现一次且分母一致。
2. 将“未命中任一拒绝规则”定义为新策略通过，“命中至少一条”定义为新策略拒绝；按确认标签计算通过/拒绝量、通过率、拒绝率、成熟风险、坏客户捕获和好客户误伤。
3. 对金额指标，仅在确认的分子、分母、过滤和聚合颗粒度下汇总；同时输出计数口径，不能以金额指标替代样本风险。
4. 若存在旧策略，以同一比较总体构造四个互斥分组：`both_pass`、`both_reject`、`swap_in`（旧拒新通过）与 `swap_out`（旧通过新拒绝）。
5. 对 `both_pass`、`both_reject` 和满足成熟表现条件的 `swap_out`，标记直接观测并计算对应表现。`swap_in` 默认没有直接表现，只能标为“估计”或“不可观测”。
6. 用户确认估计方法时，单独输出估计值、方法、假设、适用样本和选择偏差；未确认时不生成 `swap_in` 坏账率。
7. 按确认的产品、时间、客群或其他分层复算，并检查总体结论是否掩盖方向相反的分层结果。
8. 形成策略取舍结论和风险披露，供阶段 4 报告引用；不输出上线决策。

若用户要求预估 `swap_in` 风险，读取 `references/05-swap-in-risk-estimation.md`。该参考页定义三方分分箱映射、单规则局部外推、Parceling/augmentation 和接受倾向诊断的适用边界；不得仅凭旧决策字段、审批结果字段或代理标签生成坏账率。

## 指标与 Swap 分组口径

新策略的样本指标必须基于相同成熟总体计算：

```text
approval_rate = new_pass_count / comparison_population_count
reject_rate   = new_reject_count / comparison_population_count
pass_bad_rate = bad_count(new_pass) / count(new_pass)
bad_capture   = bad_count(new_reject) / bad_count(comparison_population)
good_harm     = good_count(new_reject) / good_count(comparison_population)
```

金额风险仅在已确认过滤后的单位上计算，例如 `sum(确认分子) / sum(确认分母)`；必须与样本坏账率并列展示，不能混用分母。

| Swap 分组 | 旧策略 | 新策略 | 表现解释 |
|---|---|---|---|
| `both_pass` | 通过 | 通过 | 若成熟表现存在，可直接观测 |
| `both_reject` | 拒绝 | 拒绝 | 仅描述决策一致性；表现是否可观测取决于样本来源 |
| `swap_out` | 通过 | 拒绝 | 旧策略通过且成熟时可直接观察被新策略拒绝客群 |
| `swap_in` | 拒绝 | 通过 | 通常没有直接表现，必须估计或标注不可观测 |

估计 `swap_in` 时，报告必须把估计口径与直接观测值分表显示，至少记录估计方法、训练/匹配总体、覆盖率、关键假设和选择偏差。没有这些内容时只能输出数量与不可观测标识。

## 候选参数

| 参数 | 必须确认的内容 | 作用 |
|---|---|---|
| 新策略通过定义 | 未命中级联拒绝规则或其他明确映射 | 固定通过/拒绝分组 |
| 评估总体 | 成熟总体、时间范围、过滤和权重（如使用） | 固定所有分母 |
| 风险指标 | 样本坏账率、确认金额指标及分母 | 统一效果计算 |
| 旧策略比较 | 是否启用、旧/新决策字段、共同样本范围 | 生成 Swap |
| `swap_in` 处理 | 估计方法或明确不可观测 | 禁止伪造直接表现 |
| `swap_in` 估计 | 成熟标签、训练总体、特征/三方分时点、分箱与压力假设、不可外推处理 | 形成可审计估计区间 |
| 分层 | 产品、时间、客群或确认分组 | 发现异质性 |

## 关键伪代码

```text
new_decision = cascade_result.to_decision(pass_if_no_rule_hit=True)
overall = evaluate_strategy(new_decision, mature_label, confirmed_amount_metric)

if compare_with_old_strategy:
    aligned = align_on_analysis_unit(old_decision, new_decision)
    groups = {
        both_pass: old_pass & new_pass,
        both_reject: old_reject & new_reject,
        swap_in: old_reject & new_pass,
        swap_out: old_pass & new_reject,
    }
    direct = evaluate_observed(groups[both_pass, both_reject, swap_out])
    swap_in = estimate_or_mark_unobservable(groups[swap_in], confirmed_method)
    assert_mutually_exclusive_and_exhaustive(groups)

write_strategy_effect_swap_and_disclosures()
```

## 输出表

| 文件 | 最少字段 |
|---|---|
| `strategy_effect_summary.csv` | 策略、总体样本、通过/拒绝量与占比、成熟风险、坏客户捕获、好客户误伤、金额指标、分母说明 |
| `strategy_layer_effect.csv` | 级联层级、进入样本、新增拒绝、边际风险、累计效果 |
| `swap_summary.csv` | 分组、样本量、占比、旧/新决策、表现指标、可观测性、估计方法 |
| `swap_segment_detail.csv` | 分层、Swap 分组、样本量、表现、可观测性、风险提示 |
| `strategy_evaluation_manifest.json` | 比较总体、决策字段、金额口径、估计假设、输出路径 |

## 稳定性与可观测性检查

- 四个 Swap 分组必须互斥且并集等于确认的共同比较总体；缺失旧/新决策的单位单独披露，不得静默丢弃。
- `swap_out` 只有在旧策略实际通过且存在成熟表现时才是直接观测；否则同样需要标记限制。
- `swap_in` 不得标为直接观测。估计方法、假设和偏差必须与直接观测指标分列。
- 所有通过率、风险、捕获、误伤和金额指标必须保留分母、样本范围与成熟过滤。
- 发现分层方向反转、样本不足或金额与样本结论不一致时必须写入风险披露。

## 验收不变量

- 新策略决策可由阶段 2 冻结规则逐单位复现。
- 整体策略效果与阶段 2 级联拒绝量一致。
- `both_pass`、`both_reject`、`swap_in`、`swap_out` 完整、互斥且可追溯。
- `swap_in` 仅为估计或不可观测，绝不伪装为直接观测。
- 报告前的结论同时呈现风险收益、好客户误伤和观测边界。
> **固定输出契约：** 先读取 `references/06-stage-output-contract.md`。本阶段只向 `03_strategy_evaluation/` 写入固定 Swap 表及 manifest/inventory；无成熟表现或可用第三方分时，Swap-in 风险表必须标记不可观测/不可估计，不得使用旧决策字段、审批结果字段或代理标签代替真实风险。
