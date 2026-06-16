# 指标定义

本文定义 `credit-strategy-analysis` 的统一指标口径。所有规则挖掘、分数截断、策略模拟、Swap、监控和报告必须使用本文口径；若用户要求其他口径，必须在 `run_manifest.json` 和报告中记录。

## 1. 通用计算规则

### 1.1 安全除法

所有比率指标必须使用安全除法：

```text
safe_div(numerator, denominator) =
  null, if denominator is null or denominator == 0
  numerator / denominator, otherwise
```

不得因为分母为 0 导致脚本崩溃。输出为 `null`、空值或配置中约定的缺失值，并在报告中说明。

### 1.2 表现指标样本

涉及坏账率、逾期率、KS、AUC、IV、Lift、Swap 坏样本比较时，必须先确认：

- 标签字段。
- 正样本定义。
- 坏样本定义，例如 DPD30+ MOB3。
- 成熟样本过滤。
- 是否剔除未知或未成熟标签。

未成熟样本、未知标签、拒绝无表现样本不得默认混入表现指标。

### 1.3 金额指标样本

金额指标必须确认分子、分母和样本过滤。默认建议：

```text
amount_bad_rate = sum(overdue_unpaid_principal) / sum(drawdown_amount)
```

不得从含义不清的 `amount` 字段直接计算金额逾期率。

---

## 2. 样本量与通过拒绝指标

| 指标 | 公式 | 含义 |
|---|---|---|
| `sample_cnt` | `count(sample_id)` | 当前分析样本数 |
| `pass_cnt` | `sum(approval_flag == 1)` | 通过样本数 |
| `reject_cnt` | `sum(approval_flag == 0)` | 拒绝样本数 |
| `approval_rate` | `pass_cnt / sample_cnt` | 通过率 |
| `reject_rate` | `reject_cnt / sample_cnt` | 拒绝率 |
| `approval_amount` | `sum(drawdown_amount where approval_flag == 1)` | 通过样本支用金额 |
| `approval_amount_rate` | `approval_amount / sum(drawdown_amount)` | 金额通过率 |

说明：

1. `approval_flag` 可以来自旧策略结果，也可以来自离线模拟结果。
2. 若样本口径不是申请样本，必须在报告中说明通过率分母，例如“放款样本内通过率”通常没有业务意义。

---

## 3. 人维度表现指标

| 指标 | 公式 | 适用样本 |
|---|---|---|
| `bad_cnt` | `sum(Y_label == positive_class)` | 已确认成熟样本 |
| `good_cnt` | `count(Y_label in good_class)` | 已确认成熟样本 |
| `overall_bad_rate` | `bad_cnt / mature_sample_cnt` | 成熟样本 |
| `pass_bad_rate` | `pass_bad_cnt / pass_mature_cnt` | 通过且成熟样本 |
| `reject_bad_rate` | `reject_bad_cnt / reject_mature_cnt` | 拒绝且有表现的成熟样本 |

注意：

1. `reject_bad_rate` 只有在拒绝样本有真实表现时才可直接计算。
2. 若拒绝样本没有表现，必须标注为“不可观测”或“估计值”，不能当作真实坏账率。
3. 通过样本坏账率必须使用通过且成熟样本作为分母。

---

## 4. 金额维度表现指标

默认金额维度逾期率：

```text
amount_bad_rate = sum(overdue_unpaid_principal) / sum(drawdown_amount)
```

| 指标 | 公式 | 说明 |
|---|---|---|
| `bad_amount` | `sum(overdue_unpaid_principal)` | 逾期未还本金合计 |
| `booked_amount` | `sum(drawdown_amount)` | 支用或实际放款金额合计 |
| `amount_bad_rate` | `bad_amount / booked_amount` | 金额维度逾期率 |
| `pass_amount_bad_rate` | `sum(overdue_unpaid_principal where pass) / sum(drawdown_amount where pass)` | 通过样本金额逾期率 |
| `reject_amount_bad_rate` | `sum(overdue_unpaid_principal where reject) / sum(drawdown_amount where reject)` | 拒绝样本金额逾期率，仅在有表现时可直接计算 |

可替代口径：

| 口径 | 公式 | 使用场景 |
|---|---|---|
| 余额口径 | `sum(overdue_unpaid_principal) / sum(outstanding_principal)` | 存量余额风险 |
| 到期本金口径 | `sum(overdue_unpaid_principal) / sum(due_principal)` | 到期应还本金表现 |
| 放款金额口径 | `sum(overdue_unpaid_principal) / sum(drawdown_amount)` | 默认建议口径 |

用户未确认金额口径时，不得计算金额维度逾期率。

---

## 5. 单规则指标

对规则 `R`，定义：

```text
hit = 1 if R is triggered else 0
pass_by_rule = 1 - hit
```

| 指标 | 公式 | 含义 |
|---|---|---|
| `hit_cnt` | `sum(hit == 1)` | 命中规则样本数 |
| `hit_rate` | `hit_cnt / sample_cnt` | 规则命中率 |
| `rule_bad_cnt` | `sum(hit == 1 and Y_label == positive_class)` | 命中样本坏样本数 |
| `bad_rate` | `rule_bad_cnt / hit_mature_cnt` | 命中样本坏账率 |
| `passed_bad_rate` | `pass_bad_cnt / pass_mature_cnt` | 未命中样本坏账率 |
| `lift` | `bad_rate / overall_bad_rate` | 命中样本坏账率相对整体提升 |
| `bad_capture` | `rule_bad_cnt / total_bad_cnt` | 坏客户捕获率 |
| `good_hit_cnt` | `sum(hit == 1 and Y_label != positive_class)` | 命中样本好客户数 |
| `good_capture` | `good_hit_cnt / total_good_cnt` | 好客户误伤占比 |

解释：

1. `lift > 1` 表示命中样本坏账率高于整体，但不能单独作为规则有效性的判断标准。
2. 高 Lift 可能来自极小样本，必须同时看 `hit_cnt`、`hit_rate` 和 `bad_capture`。
3. 规则推荐排序必须至少同时输出 `hit_rate`、`bad_rate`、`passed_bad_rate`、`lift`、`bad_capture`。

---

## 6. 规则漏斗指标

按规则顺序 `R1 -> R2 -> ... -> Rn` 级联执行时：

| 指标 | 公式 | 含义 |
|---|---|---|
| `remaining_before_cnt_i` | 第 `i` 条规则执行前剩余样本数 | 规则进入样本 |
| `funnel_hit_cnt_i` | 第 `i` 条规则在剩余样本中命中数 | 当前规则新增拒绝 |
| `funnel_hit_rate_i` | `funnel_hit_cnt_i / remaining_before_cnt_i` | 当前层命中率 |
| `remaining_after_cnt_i` | `remaining_before_cnt_i - funnel_hit_cnt_i` | 当前层后剩余样本 |
| `cumulative_reject_cnt_i` | `sum(funnel_hit_cnt_1 ... funnel_hit_cnt_i)` | 累计拒绝数 |
| `cumulative_reject_rate_i` | `cumulative_reject_cnt_i / sample_cnt` | 累计拒绝率 |

一致性要求：

1. `remaining_after_cnt_i` 必须等于下一条规则的 `remaining_before_cnt`。
2. `cumulative_reject_cnt` 必须单调不降。
3. 级联漏斗指标与单规则独立命中指标不能混用。

---

## 7. 分数截断指标

分数任务必须确认 `score_direction`：

- `high_score_high_risk`：分数越高风险越高。
- `high_score_low_risk`：分数越高风险越低。

| 指标 | 公式或含义 |
|---|---|
| `cutoff` | 候选截断点 |
| `cutoff_approval_rate` | 截断规则下通过样本数 / 总样本数 |
| `cutoff_bad_rate` | 截断规则下通过且成熟样本坏账率 |
| `cutoff_amount_bad_rate` | 截断规则下金额维度坏账率，需用户确认金额口径 |
| `ks_at_cutoff` | 该截断点处好坏样本累计分布差 |
| `on_frontier` | 是否位于效率前沿 |

效率前沿：

```text
某策略点 A 在通过率 >= B 且坏账率 <= B 的情况下至少一项更优，则 A 支配 B。
不被其他点支配的策略点集合为效率前沿。
```

注意：KS 是好坏样本累计分布差的最大绝对值，不是通过率与坏账率之差。

---

## 8. KS 与 AUC

### 8.1 KS

对按分数排序后的样本：

```text
KS = max(abs(cum_bad_rate(score_bin) - cum_good_rate(score_bin)))
```

要求：

1. 必须确认分数方向。
2. 必须只在有标签且成熟样本上计算。
3. 若在 OOT 上评估，不得重新拟合分箱。

### 8.2 AUC

AUC 表示随机抽取一个坏样本和一个好样本时，模型将坏样本排在更高风险位置的概率。

要求：

1. 必须确认风险方向。
2. AUC 只适用于连续分数或概率分。
3. 如果高分表示低风险，应在计算前转换方向，或在报告中明确说明。

---

## 9. WOE 与 IV

### 9.1 WOE

对分箱 `i`：

```text
WOE_i = ln((good_i / total_good) / (bad_i / total_bad))
```

若本项目采用“坏样本在分子”的 WOE 变体，必须在报告中注明。默认使用好样本占比 / 坏样本占比。

### 9.2 IV

```text
IV = sum((good_i / total_good - bad_i / total_bad) * WOE_i)
```

要求：

1. 分箱必须在开发样本拟合。
2. OOT 或监控样本只能应用已有分箱。
3. 缺失值默认单独成箱。
4. IV 只能作为筛选参考，不能单独决定策略规则。

---

## 10. PSI

PSI 用于衡量基准窗口和对比窗口的分布变化。

对分箱 `i`：

```text
PSI = sum((actual_i - expected_i) * ln(actual_i / expected_i))
```

其中：

- `expected_i`：基准窗口第 `i` 箱占比。
- `actual_i`：对比窗口第 `i` 箱占比。

要求：

1. 必须确认基准窗口和对比窗口。
2. 分箱应来自基准窗口，不能每个窗口重新分箱。
3. 占比为 0 时必须使用平滑值或安全处理，并在报告中说明。

常用解释：

| PSI | 解释 |
|---:|---|
| `< 0.1` | 分布较稳定 |
| `0.1 - 0.25` | 有一定漂移，需要关注 |
| `> 0.25` | 明显漂移，需要排查 |

阈值只是经验参考，实际告警线应结合业务波动和样本量确认。

---

## 11. Swap 指标

新旧策略对比按以下四类人群拆分：

| 分群 | 定义 |
|---|---|
| `both_pass` | 旧策略通过，新策略通过 |
| `both_reject` | 旧策略拒绝，新策略拒绝 |
| `swap_in` | 旧策略拒绝，新策略通过 |
| `swap_out` | 旧策略通过，新策略拒绝 |

核心指标：

| 指标 | 公式或含义 |
|---|---|
| `delta_approval_rate` | `new_approval_rate - old_approval_rate` |
| `delta_pass_bad_rate` | `new_pass_bad_rate - old_pass_bad_rate` |
| `swap_in_cnt` | `count(old_reject and new_pass)` |
| `swap_out_cnt` | `count(old_pass and new_reject)` |
| `swap_in_bad_rate` | Swap-in 人群坏账率，通常需要估计 |
| `swap_out_bad_rate` | Swap-out 人群坏账率，通常可直接观测 |
| `swap_out_bad_capture` | `swap_out_bad_cnt / total_bad_cnt` |
| `amount_bad_rate_delta` | 新旧金额维度逾期率之差 |

限制：

1. Swap-in 人群在旧策略下通常被拒，缺少真实表现，不能默认当作观测坏账率。
2. Swap-in 若使用估计值，必须披露估计方法，例如相似客群匹配、分数段替代、拒绝推断或实验样本。
3. Swap 结果必须支持按 `route`、渠道、产品、分数段或时间窗口分层。

---

## 12. 监控指标

| 指标 | 监控对象 | 常见频率 |
|---|---|---|
| `approval_rate` | 通过率 | 日/周 |
| `reject_rate` | 拒绝率 | 日/周 |
| `rule_hit_rate` | 单规则命中率 | 日/周 |
| `score_psi` | 分数分布 | 周/月 |
| `feature_psi` | 重点特征分布 | 周/月 |
| `bad_rate` | 成熟样本坏账率 | 周/月，取决于表现窗口 |
| `amount_bad_rate` | 金额维度风险 | 周/月，取决于表现窗口 |

监控报告必须区分：

- 实时可观测指标，例如通过率、拒绝率、规则命中率。
- 滞后表现指标，例如 DPD30+ MOB3 坏账率。

---

## 13. 报告披露要求

报告中每个指标必须说明：

1. 样本范围。
2. 时间窗口。
3. 标签定义。
4. 成熟样本过滤。
5. 分子和分母。
6. 是否为直接观测或估计。
7. 分母为 0 或样本量过小的处理方式。

