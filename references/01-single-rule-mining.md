# 阶段 1：单规则挖掘

## 目的与输入

在确认的成熟样本和候选特征中生成可解释候选规则。输入为阶段 0 的配置、成熟标签、候选特征和可选时间/OOT 标识；`toad` 用于分箱与 IV，`scikit-learn` 用于 CART。

## 方法

1. 对特征进行 IV 和分箱诊断；保护列、泄漏字段、常量字段和未确认特征排除。
2. 数值特征从用户确认的极端区间、分位点、缺失值、业务阈值和 chi 分箱边界生成候选规则。
3. 类别特征从确认类别、类别组合和缺失值生成候选规则，不遍历全部高基数取值。
4. 对每条规则计算命中量、命中率、坏账率、未命中坏账率、Lift、坏客户捕获和好客户误伤。
5. 可选 CART 仅提取根到叶的 AND 路径；每条路径不超过 3 个特征，重新按单规则口径评估。
6. 只保留满足用户确认的最小样本量和最小命中率的候选；开发期与确认窗口/OOT 的风险方向不一致时标记警告。

## 伪代码

```text
features = confirmed_candidate_features - protected_columns
for feature in features:
    bins, iv = fit_bins_and_iv_on_confirmed_development_sample(feature)
    rules = extreme_intervals + confirmed_quantiles + missing + business_thresholds
    evaluate_each_rule(rules)
cart_paths = extract_paths_with_at_most_3_features_if_confirmed()
eligible = rules_passing_confirmed_min_sample_and_hit_rate()
write_eligible_rules_sorted_by_lift(eligible)
```

## 输出

- `01_feature_iv.csv`：特征、IV、分箱数、缺失率和警告。
- `01_single_rule_candidates.csv`：规则、特征、条件、命中、风险、Lift、捕获、误伤、稳定性。
- `01_cart_paths.csv`：最多 3 个特征的路径及其同口径指标。
- `01_manifest.json`：候选参数、特征排除与稳定性窗口。

IV、极端区间、分位点、最小样本、最小命中率和 CART 是否启用都必须由用户确认，不设默认值。
