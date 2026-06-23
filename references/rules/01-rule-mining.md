# 规则挖掘

## 适用范围与阻断

用于从已确认的特征和成熟标签中发现可解释的候选拒绝规则，不用于完整 A 卡训练，也不把候选规则直接视为上线规则。字段映射、分析颗粒度、标签、成熟规则、候选特征和保护列例外未确认时停止。`toad` 缺失时，涉及 chi 分箱、WOE 或 IV 的分支停止。

## 最小输入与按需引用

输入：确认后的分析单位、`Y_label`、成熟过滤、候选特征、时间或 OOT 标识（如有）。数值或类别字段必须能解释为贷前可用特征；标签、金额结果、审批结果、拒绝码、日期和 ID 默认排除。

按需读取：`02-data-contract.md` 的特征策略、标签和表现期；`03-metric-definitions.md` 的第 2、3、5、9 节。若要发现交互规则，再读取本文件的 CART 分支；不因此启动完整模型训练。

## 方法步骤

1. 以用户确认的成熟规则过滤表现样本，保留分析单位和时间字段用于稳定性检查。
2. 按特征策略排除保护列、泄漏字段、常量字段、无法解析字段和未经批准的高基数字段；输出排除原因。
3. 对数值特征分别以业务切点、用户确认的分位点和 `toad` chi 分箱生成有限候选切点；缺失值保留为独立候选分群。
4. 对类别特征以确认的业务分组、低频合并和缺失值生成候选；不得逐一把全部唯一取值当作候选规则。
5. 对每条单规则计算命中量、命中率、坏账率、未命中坏账率、Lift、坏客户捕获率和好客户误伤，指标定义以词典为准。
6. 如用户要求组合发现，训练单棵受限 CART，仅提取从根到叶的 AND 路径；每条路径仍按单规则口径重新评估。
7. 删除同一特征同方向的嵌套弱规则和高度重叠规则，保留业务可解释性、覆盖和风险贡献更优者。
8. 在确认的时间窗口或 OOT 上应用开发期切点，不重新分箱；比较命中率、坏账率、Lift 和捕获率变化。
9. 仅输出候选排序和证据，由用户决定是否进入策略模拟。

## 候选参数

以下均为候选项，必须由用户确认并写入配置；未确认不得自动采用。

| 参数 | 可选方式 | 影响 |
|---|---|---|
| 开发样本 | 确认的时间窗、批准样本或其他样本口径 | 决定规则可学习的总体 |
| 数值切点来源 | 业务切点、分位点列表、chi 分箱或组合 | 决定候选数量和可解释性 |
| 分箱目标 | 常见候选为 3-5 箱，最大箱数需确认 | 箱数过多会提高不稳定风险 |
| 最小命中限制 | 固定样本数、样本占比或两者同时限制 | 防止小样本高 Lift |
| 类别合并 | 业务分组、最小频次或其他规则 | 防止稀疏类别偶然性 |
| CART 深度 | 常见候选为 2-4 层及叶子样本限制 | 深度越大，过拟合风险越高 |
| 稳定性窗口 | 时间窗、OOT 或交叉窗口 | 决定规则保留标准 |

## 关键伪代码

```text
require confirmed(contract, label, maturity, feature_policy, parameters)
development = filter_to_confirmed_mature_population(input)
features = exclude_protected_and_unapproved_fields(development)

for feature in features:
    candidates = business_breaks + confirmed_quantiles + chi_bins(feature)
    candidates += missing_and_confirmed_category_groups(feature)
    for condition in finite_candidates(candidates):
        metrics = evaluate_rule(condition, development, analysis_unit_id)
        if meets_confirmed_coverage(metrics): save_single_rule(condition, metrics)

if cart_requested:
    paths = extract_paths(fit_confirmed_restricted_cart(features, development))
    re_evaluate_each_path(paths)

deduplicate_overlap_and_nested_rules()
apply_development_bins_to_confirmed_stability_window()
rank_by_confirmed_multi_metric_policy()
write_candidates_and_evidence()
```

## 输出

| 文件 | 最少字段 |
|---|---|
| `rule_feature_screening.csv` | 特征、保留/排除、原因、缺失率、唯一值信息 |
| `rule_bin_detail.csv` | 特征、箱/类别、样本数、好坏样本、坏账率、WOE、IV 分量 |
| `rule_candidates.csv` | 规则 ID、条件、命中量、命中率、坏账率、未命中坏账率、Lift、坏客户捕获、好客户误伤、稳定性结果 |
| `rule_cart_paths.csv` | 路径、叶子样本量、风险指标、开发/稳定性窗口对比 |
| `rule_mining_manifest.json` | 已确认参数、特征例外、时间窗口、排序方法和输出路径 |

## 稳定性与异常

开发期高 Lift 但命中不足、OOT 风险排序反转、类别大量缺失、单箱全好或全坏、特征疑似表现期泄漏时必须警告，不得自动推荐。零分母指标输出空值；未成熟或未知标签不参与表现排序。

## 验收不变量

- 每条规则均可由已确认字段和条件复现，且说明分析颗粒度。
- 不存在保护列或未经批准的字段作为特征。
- 候选切点不是全部唯一值遍历，且每条规则满足用户确认的覆盖限制。
- OOT 或稳定性比较只应用开发期切点，不重新拟合。
- 排序不只依赖 Lift，至少同时展示覆盖、风险、捕获和未命中表现。
