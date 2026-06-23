# 分数截断

## 适用范围与阻断

用于已有模型分或风险概率的离线截断、分层和效率前沿分析。不用于重新训练模型。分数字段、风险方向、缺失分处理、分析颗粒度、成熟标签和业务约束未确认时停止；不得根据字段名猜测高分代表高风险还是低风险。

## 最小输入与按需引用

输入为确认后的 `model_score`、分析单位、成熟标签、可选金额字段、时间/OOT 标识和业务约束。按需读取 `02-data-contract.md` 的分数字段、金额与表现期，及 `03-metric-definitions.md` 的第 2、3、4、7、8 节。

## 方法步骤

1. 依据确认的风险方向将分数标准化为“数值越高风险越高”的排序键；原始分数保留在输出中。
2. 按确认的缺失分策略处理：剔除、单独分群或其他明确策略。缺失分不得静默填补。
3. 仅用确认的成熟表现样本计算候选截断表现；未成熟和未知标签单列报告但不参与坏账率、KS 或约束判断。
4. 从用户确认的既有截断、业务切点、分位点或评分分箱生成有限候选点；相同分数不可被拆成不同通过结果。
5. 对每个候选点按确认的通过方向生成通过/拒绝，计算通过率、通过样本坏账率、金额风险率、坏客户捕获和该点的累计 KS。
6. 先过滤不满足用户确认的风险、通过率、金额或样本量约束的点，再在剩余点中识别 Pareto 前沿。
7. 在确认的 OOT 或时间窗口应用开发期候选点，比较通过率、风险、KS 与约束满足情况；不在 OOT 上重新选择切点。
8. 输出前沿和非前沿结果，说明选择需要用户决策而非自动推荐单一截断。

## 候选参数

| 参数 | 可选方式 | 影响 |
|---|---|---|
| 风险方向 | 高分高风险或高分低风险 | 决定通过侧 |
| 候选点来源 | 既有截断、业务切点、分位点、固定评分分箱 | 决定搜索空间 |
| 缺失分处理 | 剔除、单独分群或确认的替代规则 | 决定覆盖与偏差 |
| 业务约束 | 最大坏账率、最低通过率、金额风险或样本量 | 决定可行集合 |
| 前沿目标 | 通过率与风险、金额、捕获的优先级 | 决定 Pareto 展示和选择 |
| 稳定性窗口 | OOT 或确认时间窗 | 决定可复用性判断 |

## 关键伪代码

```text
require confirmed(score, direction, missing_policy, maturity, constraints)
scored = normalize_to_risk_order(input, direction)
observed = filter_confirmed_mature_labels(scored)
candidates = confirmed_existing_or_business_or_quantile_cutoffs(observed)

for cutoff in finite_candidates(candidates):
    decision = apply_cutoff(scored, cutoff, direction, missing_policy)
    metrics = evaluate_mature_pass_population(decision, observed)
    record(cutoff, metrics, constraint_status(metrics, constraints))

frontier = non_dominated_feasible_points(recorded_points)
apply_same_cutoffs_to_confirmed_oot_if_available()
write_all_points_frontier_and_stability_comparison()
```

## 输出

| 文件 | 最少字段 |
|---|---|
| `score_cutoff_curve.csv` | 截断点、通过方向、通过/拒绝量与比例、成熟通过坏账率、金额风险、KS、约束状态、是否前沿 |
| `score_band_summary.csv` | 分数段、样本量、成熟量、好坏样本、坏账率、累计好坏分布 |
| `score_cutoff_stability.csv` | 开发与 OOT/时间窗的通过率、风险、KS 与变化 |
| `score_cutoff_manifest.json` | 分数方向、缺失分策略、候选来源、业务约束和选择记录 |

## 稳定性与异常

分数常量、标签单一、有效成熟样本不足、分母为零、缺失分占比异常或 OOT 方向反转时必须警告。业务约束没有可行点时输出不可行原因，不得放宽约束或选择最近点。

## 验收不变量

- 每个相同原始分数在同一缺失策略下得到同一通过结果。
- 所有表现指标只使用确认的成熟样本，且说明分析颗粒度。
- 候选点和约束均来自确认配置；不存在静默默认截断。
- Pareto 点不被其他可行点在所有确认目标上同时支配。
- OOT 仅应用开发期切点，不重新选点或重算分箱。
