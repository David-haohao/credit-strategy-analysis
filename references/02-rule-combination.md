# 阶段 2：Lift TopN 规则组合

## 适用与阻断条件

用于把阶段 1 已通过准入和稳定性检查的候选规则，按确认的 Lift 定义形成顺序级联的拒绝策略。它不重新分箱、不重新训练 CART，也不支持 AND、OR、路由或分数截断等并行组合语义。

`TopN`、Lift 排序、同 Lift 并列处理和“任一命中即拒绝”必须由用户确认。候选规则来源、分析单位或样本总体不一致时停止。

## 最小输入

- 阶段 1 的 `single_rule_candidates.csv` 和可选 `cart_path_candidates.csv`。
- 每条候选的规则条件、命中明细、开发/OOT 指标和保留状态。
- 用户确认的 `TopN`、排序字段 `lift_desc`、并列处理规则和顺序级联拒绝语义。
- 阶段 0 的确认凭证，确保组合时仍使用同一 `analysis_unit_id`、标签和成熟规则。

## 方法步骤

1. 只读取阶段 1 标记为合格的候选；排除覆盖不足、稳定性失败、不可解释或已去重的规则。
2. 在同一确认样本总体上按确认的 Lift 定义降序排序。并列不得自行以 IV、样本量或名称打破，必须使用用户确认的并列处理；当前 CLI 仅接受 `higher_coverage_first`、`lower_coverage_first`、`input_order`、`rule_id_asc` 四类固定 `tie_policy`。
3. 用户确认 `TopN` 后截取候选清单，并冻结规则 ID、条件、开发期切点和类别分组。
4. 从全体分析单位开始按排序顺序执行：当前规则仅在上层未拒绝样本中评估；任一命中即拒绝，命中单位不再进入后续规则。
5. 每层计算新增拒绝数、累计拒绝数、剩余样本、新增坏客户捕获、累计捕获、新增好客户误伤和边际风险表现。
6. 同时输出每条规则的独立命中与进入该层后的边际命中，识别高 Lift 但与前序规则高度重叠的候选。
7. 在确认 OOT 上应用完全相同的 TopN、顺序和条件，输出层级变化；不得因为 OOT 结果重新排序或替换规则。
8. 将组合规则及逐层结果交给阶段 3，阶段 2 不作通过率目标或上线取舍决策。

## 边际指标计算

第 `k` 层的进入样本是第 `k-1` 层未拒绝样本 `R(k-1)`。令当前规则命中为 `H(k)`，则：

```text
incremental_reject(k) = count(H(k) ∩ R(k-1))
cumulative_reject(k)  = cumulative_reject(k-1) + incremental_reject(k)
remaining(k)          = R(k-1) - H(k)
incremental_bad_capture(k) = bad_count(H(k) ∩ R(k-1)) / bad_count(U)
incremental_good_harm(k)   = good_count(H(k) ∩ R(k-1)) / good_count(U)
```

独立 Lift 用于排序，边际 Lift 仅描述该层在剩余样本中的风险表现，二者不得混用。若某规则因前序规则覆盖而无新增命中，必须保留在重叠输出中并标记为无边际贡献，不能以独立 Lift 代替组合贡献。

当 TopN 大于合格候选数量时停止并要求用户确认缩减 N 或补充候选；不得自动取全部候选。出现并列时按确认的并列规则处理，不能临时按 IV、规则名称或样本量排序。若用户确认 `rule_id_asc`，它只是确定性兜底排序，必须在选择原因中披露，不能伪装成业务优先级。

## 候选参数

| 参数 | 必须确认的内容 | 作用 |
|---|---|---|
| 排序 | `lift_desc` 及 Lift 分子/分母口径 | 固定候选优先级 |
| TopN | 正整数 N | 决定进入级联的规则数 |
| 并列处理 | `higher_coverage_first`、`lower_coverage_first`、`input_order` 或 `rule_id_asc` | 防止隐含二次排序 |
| 级联语义 | `sequential_reject`，任一命中即拒绝 | 固定策略行为 |
| 稳定性门槛 | 阶段 1 合格状态的使用规则 | 决定候选池 |
| 验证窗口 | 确认的 OOT 或时间窗 | 检查顺序迁移 |

## 关键伪代码

```text
eligible = candidates.where(status == "qualified")
ranked = sort_by_confirmed_lift_desc(eligible, confirmed_tie_policy)
selected = take_confirmed_top_n(ranked, TopN)

remaining = all_confirmed_analysis_units
for position, rule in enumerate(selected, start=1):
    hit = evaluate(rule.condition, remaining)
    layer = calculate_incremental_metrics(hit, remaining, confirmed_target)
    reject(rule, hit)
    remaining = remaining.exclude(hit)
    write_layer(position, rule, layer, remaining)

apply_same_selected_rules_to_oot_without_reranking()
```

规则复算只支持阶段 1 声明的安全表达式子集：比较、区间、缺失和 AND 组合；不支持 OR、括号、函数调用或任意 Python 表达式。无法解析的候选规则必须阻断组合，不得静默跳过。

## 输出表

| 文件 | 最少字段 |
|---|---|
| `lift_ranked_rules.csv` | 排名、规则 ID、条件、规则类型、独立样本、独立 Lift、合格状态、入选状态 |
| `cascade_funnel.csv` | 层级、规则 ID、进入样本、新增拒绝、累计拒绝、剩余样本、新增/累计坏客户捕获、新增/累计好客户误伤、边际 Lift |
| `rule_overlap.csv` | 规则对、独立命中、交集、并集、重叠率、后序边际命中 |
| `cascade_oot.csv` | 层级、开发/OOT 覆盖、Lift、捕获、误伤、变化与警告 |
| `rule_combination_manifest.json` | TopN、Lift 口径、并列规则、级联顺序、样本范围和输出路径 |

## 稳定性与可观测性检查

- 每层的新增拒绝必须是前层剩余样本的子集；累计拒绝不能减少，剩余样本不能增加。
- 高重叠导致边际命中很低、OOT 排序严重变化、单层命中不足或规则方向反转时必须披露。
- 规则只依赖阶段 1 冻结的条件；组合阶段不得调整阈值以改善结果。
- 边际坏账表现只对成熟且可观测样本解释，不能将未观察到的拒绝表现当作事实。

## 验收不变量

- 所有入选规则来自阶段 1 合格候选，且按确认的 Lift 降序排列。
- `TopN` 已明确确认，未确认或非正整数时阻断。
- 组合语义固定为“任一命中即拒绝”的顺序级联。
- 每一层输出独立、边际与累计结果，不能用单规则结果简单相加替代。
- OOT 仅验证已冻结组合，不重新排序、不重新选择 TopN。
> **固定输出契约：** 先读取 `references/06-stage-output-contract.md`。本阶段只向 `02_rule_combination/` 写入固定业务表及 manifest/inventory；无 OOT 时 `cascade_oot.csv` 必须保留表头并标记未评估。
