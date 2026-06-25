# 阶段 1：单规则挖掘

## 适用与阻断条件

用于从阶段 0 已确认的成熟样本和贷前特征中发现可解释候选拒绝规则。它不训练完整评分模型，也不把候选规则直接作为上线策略。字段映射、分析颗粒度、标签、成熟规则、候选特征、最小样本/命中限制或稳定性窗口未确认时停止。

IV、WOE 和 chi 分箱必须安装 `toad`；缺失时阻断涉及这些方法的任务。CART 仅用于发现根到叶的 AND 路径，任何单条路径最多 3 个特征。

## 最小输入

- 阶段 0 的确认凭证、运行配置、`analysis_unit_id` 和成熟样本。
- 确认的目标列、正样本定义、成熟过滤和可选开发/OOT 时间标识。
- 候选贷前特征、保护列清单、允许的特征例外及原因。
- 用户确认的 IV 筛选、分箱、分位点、最小样本、最小命中率、稳定性和 CART 参数。

## 方法步骤

1. 以确认的成熟规则过滤样本，并保留分析单位和时间字段；未成熟、未知和排除标签不参加表现排序。
2. 进行特征准入：排除保护列、标签泄漏、常量、高缺失但未批准处理、无法解析字段和未经确认的高基数类别；记录每个排除原因。
3. 对准入特征用 `toad` 进行确认分箱与 WOE/IV 计算。IV 用于筛选和描述，不单独证明规则有效；输出各箱好坏分布和 IV 分量。
4. 数值特征从确认业务阈值、确认分位点的两端极端区间、chi 分箱边界和缺失值生成有限候选。不得遍历所有唯一值。
5. 类别特征从确认业务分组、确认低频合并和缺失组生成候选。不得将所有稀疏取值逐一写成规则。
6. 对每条候选计算命中量、命中率、命中坏账率、未命中坏账率、Lift、坏客户捕获率、好客户误伤和可选金额指标。`Lift = 命中坏账率 / 总体坏账率`，总体坏账率为零时输出空值。
7. 若用户确认需要交互规则，拟合单棵受限 CART，抽取根到叶路径。只保留 AND 条件、每条路径最多 3 个特征，并按与单规则相同的分析单位重新计算指标。
8. 合并同一特征同方向的嵌套规则，删除高度重叠、覆盖不足、风险反向或难以解释的候选；保留删除依据。
9. 在确认的 OOT 或时间窗口应用开发期切点和类别分组，禁止重新分箱；比较覆盖、坏账率、Lift 和捕获变化。
10. 输出合格候选及未入选原因，交由阶段 2 选择 TopN，不自动改变准入策略。

## 指标计算与候选保留

对任一候选规则 `r`，在确认的成熟总体 `U` 上计算：

```text
hit_count       = count(r 命中)
hit_rate        = hit_count / count(U)
hit_bad_rate    = bad_count(r 命中) / hit_count
non_hit_bad_rate= bad_count(r 未命中) / non_hit_count
overall_bad_rate= bad_count(U) / count(U)
lift            = hit_bad_rate / overall_bad_rate
bad_capture     = bad_count(r 命中) / bad_count(U)
good_harm       = good_count(r 命中) / good_count(U)
```

IV 的箱级计算为 `(坏样本分布 - 好样本分布) * ln(坏样本分布 / 好样本分布)` 的求和；是否使用平滑、平滑方式和零好/零坏箱处理必须由用户确认并记录。不能通过删除全好/全坏箱来消除风险信号。

候选进入阶段 2 前，必须同时满足确认的样本/命中限制、字段可解释性、方向合理性和稳定性检查。高 IV 或高 Lift 但覆盖极低、OOT 反转或明显依赖缺失异常的规则应保留证据，但标为不合格或需人工复核。

## 候选参数

| 参数 | 确认内容 | 使用位置 |
|---|---|---|
| IV 筛选 | 阈值、缺失/高基数字段处理与例外 | 特征准入 |
| 数值候选 | 业务切点、分位点列表、chi 分箱和缺失规则 | 极端区间与单规则 |
| 类别候选 | 业务分组、低频阈值、未知/缺失处理 | 类别单规则 |
| 最小限制 | 最小命中样本、最小命中率及坏样本限制 | 候选准入 |
| 稳定性 | 开发/OOT 窗口、可接受的变化界限 | 候选保留 |
| CART | 是否启用、叶子最小样本和最多 3 个特征路径 | 多特征 AND 规则 |
| 去重 | 嵌套和重叠判定阈值、业务可解释性优先级 | 候选精简 |

## 关键伪代码

```text
require_confirmed(stage_0, feature_policy, mining_parameters)
development = filter_to_mature_population(data, maturity_rule)
features = screen_features(development, protected_columns, approved_exceptions)

for feature in features:
    bins, woe, iv = toad_bin_woe_iv(feature, confirmed_target, confirmed_binning)
    candidates = business_thresholds(feature)
    candidates += tail_intervals(confirmed_quantiles)
    candidates += chi_bin_intervals(bins) + [missing_condition(feature)]
    for condition in finite_candidates(candidates):
        metrics = evaluate(condition, development, analysis_unit_id)
        keep_if_meets_confirmed_coverage(metrics)

if cart_enabled:
    paths = extract_and_paths(restricted_cart(features, max_features_per_path=3))
    re_evaluate(paths, development)

deduplicate_and_apply_development_bins_to_oot()
write_feature_screening_bins_candidates_and_stability()
```

## 输出表

| 文件 | 最少字段 |
|---|---|
| `feature_screening.csv` | 特征、数据类型、缺失率、唯一值、IV、保留/排除、原因 |
| `bin_iv_detail.csv` | 特征、箱/类别、样本量、好/坏样本、坏账率、WOE、IV 分量 |
| `single_rule_candidates.csv` | 规则 ID、特征、条件、规则类型、命中量、命中率、坏账率、未命中坏账率、Lift、捕获、误伤 |
| `cart_path_candidates.csv` | 路径、特征数、AND 条件、叶子样本、全部规则指标、保留状态 |
| `rule_stability.csv` | 规则 ID、开发/OOT 覆盖、坏账率、Lift、捕获、变化、警告 |
| `rule_mining_manifest.json` | 已确认参数、`toad` 版本、开发/OOT 范围和输出路径 |

## 稳定性与可观测性检查

- 开发期与 OOT 必须使用相同切点、类别合并和缺失定义；不得在 OOT 重新拟合。
- 命中不足、单箱全好/全坏、极端 Lift、类别稀疏、规则方向反转和时间漂移必须标记。
- CART 路径超过 3 个特征直接丢弃，不通过压缩文字或省略条件规避限制。
- 标签只能在成熟且可观测的样本上评估；拒绝样本无表现时不能用于直接坏账率结论。

## 验收不变量

- 每个候选规则可由确认字段和条件在同一分析单位复现。
- 所有 IV、WOE 和分箱结果来自 `toad`，并保留分箱明细。
- 每条规则满足用户确认的最小限制，且同时显示覆盖、Lift、捕获和误伤。
- 受限 CART 的任一路径最多 3 个特征。
- 规则排序和入选理由不只依赖 IV 或 Lift 单一指标。
> **固定输出契约：** 先读取 `references/06-stage-output-contract.md`。本阶段只向 `01_rule_mining/` 写入契约列出的五张业务表及 manifest/inventory；无时间外验证时稳定性状态必须写“未评估（未做时间外验证）”。
