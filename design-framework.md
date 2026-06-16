# 风控信贷策略 Skill 设计框架

> 版本: v0.4 | 日期: 2026-06-16 | 状态: 待审核

---

## 一、V4 设计结论

V4 将 `credit-strategy-skills`、`rule-analysis`、`risk-strategy-metrics` 整合为一个统一 skill：

```text
credit-strategy-analysis
```

该 skill 定位为：面向信贷风控策略分析的可复现工具箱，覆盖产品与场景确认、规则挖掘、规则回测、分数截断、策略模拟、Swap 对比、风险指标评估、稳定性监控和报告生成。

该 skill 不做生产上线、灰度发布、流量切换、生产规则部署、上线方案设计或审批材料生成。若数据中包含已上线规则结果，仅用于离线复盘、效果评估和策略备选建议。

---

## 二、合并后的能力边界

### 2.1 被整合的原 skill

| 原 skill | 原职责 | V4 处理方式 |
|---|---|---|
| `rule-analysis` | 规则引擎重建、拒绝码分析、单规则和级联漏斗回测 | 合并为 `rules/backtest` 与 `rules/funnel` |
| `risk-strategy-metrics` | IV/KS/PSI、分箱、WOE、Lift、规则挖掘、策略指标 | 合并为 `metrics`、`binning`、`monitoring`、`rule-mining` |
| `credit-strategy-skills` | 产品场景路由、策略设计、策略模拟、Swap | 作为主入口和任务编排层 |

### 2.2 核心原则

1. 一个入口，一个上下文，不再让用户在多个 skill 之间切换。
2. 规则挖掘、规则回测、分数截断、策略模拟、Swap 和监控使用同一套数据契约。
3. 所有任务必须先确认产品、场景、任务类型、样本口径、分析颗粒度、标签口径和金额口径。
4. 缺失关键输入时必须停止并询问用户，不得静默使用默认值。
5. 只输出离线分析材料，不输出生产上线方案。

---

## 三、强制问答入口

每次使用 skill 前，必须依次确认以下信息。任一阻塞项未明确，不得进入脚本执行。

### 3.1 产品与场景

```text
Q1: 请确认产品形态？
    [1] 循环贷
    [2] 非循环贷
    [3] 其他，请描述

Q2: 请确认还款方式？
    [1] 等额还款
    [2] 一次性还本付息
    [3] 其他，请描述

Q3: 请确认应用场景？
    贷前:
      [A1] 首借准入
      [A2] 复借准入
      [A3] 额度策略
      [A4] 定价策略
      [A5] 支用审批
    贷中:
      [B1] 提额策略
      [B2] 降额策略
      [B3] 提价策略
      [B4] 降价策略
      [B5] 预警管控
    复盘:
      [C1] 已上线规则离线复盘
      [C2] 新旧策略离线对比
```

### 3.2 分析任务与数据口径

| 阻塞问题 | 说明 | 缺失时处理 |
|---|---|---|
| 任务类型 | 规则挖掘、规则回测、分数截断、策略模拟、Swap、监控、报告 | 停止并询问 |
| 样本口径 | 申请样本、通过样本、放款样本、成熟样本、拒绝样本 | 停止并询问 |
| 分析颗粒度 | 客户级、申请级、借据级、支用级、客户-时间窗；以及对应 ID 字段 | 停止并询问 |
| 标签口径 | 30+/60+/90+ DPD、MOB 窗口、正负样本定义 | 停止并询问 |
| 成熟样本口径 | 是否剔除未成熟样本，成熟窗口如何定义 | 涉及表现指标时停止并询问 |
| 金额口径 | 默认建议为逾期未还本金 / 支用金额，但必须确认 | 涉及金额指标时停止并询问 |
| 旧策略结果 | 旧通过标识、旧拒绝码、旧规则命中字段 | Swap/复盘任务缺失则停止 |
| 模型分 | 分数字段、分数方向、分数缺失处理 | 分数类任务缺失则停止 |
| 路由字段 | 渠道、产品、分层、客群或地区 | 分路由任务缺失则停止 |

---

## 四、产品与场景参考卡片

### 4.1 产品 2x2 矩阵

| | 等额还款 | 一次性还本付息 |
|---|---|---|
| **循环贷** | 有额度、多次支用、按月还本付息 | 有额度、多次支用、到期还本 |
| **非循环贷** | 一次性放款、按月还本付息 | 一次性放款、到期还本 |

该矩阵只作为用户确认的参考卡片，不用于自动推断。

### 4.2 场景适用矩阵

| 场景 | 循环+等额 | 循环+一次性 | 非循环+等额 | 非循环+一次性 |
|---|:---:|:---:|:---:|:---:|
| 首借准入 | ✓ | ✓ | ✓ | ✓ |
| 复借准入 | 可选 | 可选 | ✓ | ✓ |
| 额度策略 | ✓ | ✓ | ✓ | ✓ |
| 定价策略 | ✓ | ✓ | ✓ | ✓ |
| 支用审批 | ✓ | ✓ | 可选 | 可选 |
| 提额/降额 | ✓ | ✓ | 不适用 | 不适用 |
| 提价/降价 | ✓ | ✓ | 可选 | 可选 |
| 预警管控 | ✓ | ✓ | ✓ | ✓ |
| 规则复盘 | ✓ | ✓ | ✓ | ✓ |

---

## 五、数据模式

| 数据模式 | 样本特征 | 可执行任务 |
|---|---|---|
| 纯规则数据 | 特征 + 标签，无模型分 | 单规则挖掘、CART 规则、规则组合、策略模拟、规则回测 |
| 有模型分数据 | 特征 + 标签 + 模型分 | 分数截断、分数分层、分数 x 规则联合策略、Swap |
| 已上线规则数据 | 拒绝码、通过标识、规则命中字段 | 规则复盘、漏斗分析、误伤分析、边际贡献分析 |
| 监控数据 | 时间字段 + 规则/分数/表现指标 | PSI、通过率漂移、坏账率漂移、规则命中率漂移 |
| 混合数据 | 部分样本有分、部分有规则码 | 可执行，但必须先确认缺失样本处理方式 |

---

## 六、统一数据契约

### 6.1 基础字段

| 字段 | 类型 | 用途 |
|---|---|---|
| `id_cols` | list[str] | 与分析颗粒度一致的唯一标识字段，允许多列组合 |
| `customer_id` | str/int | 客户标识，客户级或跨颗粒度聚合时必需 |
| `application_id` | str/int | 申请标识，申请级分析时必需 |
| `loan_id` | str/int | 借据标识，借据级标签或输出时必需 |
| `drawdown_id` | str/int | 支用标识，支用级标签或输出时必需 |
| `sample_date` | datetime | 申请、支用、放款或观测时间 |
| `Y_label` | int, 0/1 | 表现标签，1 表示坏样本 |

`sample_id` 只作为可选字段，不得默认作为唯一分析单位。脚本如需统一 ID，应根据用户确认的 `id_cols` 生成 `analysis_unit_id`，并写入 `run_manifest.json`。

### 6.1.1 分析颗粒度

分析颗粒度决定 `sample_cnt`、通过率、拒绝率、规则命中率和坏账率等指标的分母，必须由用户确认。

| 颗粒度 | 含义 | 常见 ID |
|---|---|---|
| `customer` | 客户级 | `customer_id` |
| `application` | 申请级 | `application_id` |
| `loan` | 借据级 | `loan_id` |
| `drawdown` | 支用级 | `drawdown_id` |
| `customer_window` | 客户-时间窗 | `customer_id + observation_month` |

循环贷场景中，0/1 标签可能基于借据或支用，一个客户可能有多个借据或多次支用；贷前特征通常是人维度。若输出人维度指标，必须确认如何从借据或支用聚合到客户，例如 `any_bad_to_customer`、`max_label`、`latest_loan`、`first_loan` 或时间窗聚合。

### 6.2 金额字段

金额字段必须拆分，不再使用单一 `amount` 字段承载所有含义。

| 字段 | 类型 | 用途 |
|---|---|---|
| `drawdown_amount` | float | 支用金额或实际放款金额 |
| `overdue_unpaid_principal` | float | 逾期未还本金 |
| `outstanding_principal` | float | 当前未还本金余额，可选 |
| `due_principal` | float | 到期应还本金，可选 |

默认金额维度逾期率建议：

```text
amount_bad_rate = sum(overdue_unpaid_principal) / sum(drawdown_amount)
```

该公式只是默认建议。每次涉及金额维度指标时，必须让用户确认分子、分母和样本过滤条件。

### 6.3 策略与规则字段

| 字段 | 类型 | 用途 |
|---|---|---|
| `old_approval_flag` | int, 0/1 | 旧策略是否通过 |
| `new_approval_flag` | int, 0/1 | 新策略模拟后是否通过 |
| `old_reject_code` | str | 旧策略拒绝码 |
| `new_reject_code` | str | 新策略模拟拒绝码 |
| `route` | str | 路由、渠道、客群、产品或地区分层 |
| `model_score` | float | 模型分 |
| `sample_weight` | float | 样本权重，可选 |

### 6.4 表现期字段

| 字段 | 类型 | 用途 |
|---|---|---|
| `mob` | int | 表现观察期 |
| `dpd_max` | int | 最大逾期天数 |
| `mature_flag` | int, 0/1 | 是否表现成熟 |

涉及坏账率、逾期率、Lift、KS、IV、Swap 坏样本比较时，必须确认是否只使用成熟样本。未成熟样本不能默认混入表现评估。

### 6.5 保护列

以下字段默认禁止作为规则挖掘特征：

```text
sample_id, customer_id, application_id, loan_id, drawdown_id,
sample_date, Y_label,
drawdown_amount, overdue_unpaid_principal, outstanding_principal, due_principal,
old_approval_flag, new_approval_flag,
old_reject_code, new_reject_code,
mature_flag, mob, dpd_max
```

如用户明确要求使用其中某个字段，必须在报告中标注为人工指定例外。

---

## 七、分析流程

V4 不再设计为强制线性流水线。入口根据用户任务路由到独立模块，必要时串联。

```text
入口确认
  ├── 分数截断优化
  ├── 规则挖掘
  ├── 规则回测与漏斗复盘
  ├── 策略模拟
  ├── Swap in/out 分析
  ├── 风险指标与稳定性监控
  └── 报告生成
```

推荐组合流程：

| 目标 | 推荐模块顺序 |
|---|---|
| 从特征发现候选规则 | 入口确认 -> 规则挖掘 -> 策略模拟 -> 报告 |
| 已上线规则复盘 | 入口确认 -> 规则回测 -> 漏斗复盘 -> 稳定性监控 -> 报告 |
| 分数截断策略 | 入口确认 -> 分数截断 -> 效率前沿 -> 策略模拟 -> 报告 |
| 新旧策略对比 | 入口确认 -> 旧策略重建 -> 新策略模拟 -> Swap -> 分路由分析 -> 报告 |

---

## 八、核心任务模块

### 8.1 分数截断优化

适用于有模型分的数据。

输入要求：

1. `model_score` 字段。
2. 分数方向：高分高风险或高分低风险。
3. `Y_label` 与成熟样本口径。
4. 若涉及金额指标，确认金额口径。

输出指标：

| 指标 | 含义 |
|---|---|
| 各候选截断点通过率 | 截断后通过样本 / 总样本 |
| 各候选截断点坏账率 | 截断后通过样本中的坏账率 |
| KS | 正负样本累计分布差的最大值 |
| 坏账率约束下的最优截断 | 给定容忍坏账率上限，最大化通过率 |
| 通过率约束下的最优截断 | 给定最低通过率，最小化坏账率 |
| 效率前沿 | 通过率与坏账率 trade-off 下的 Pareto 最优点 |

注意：KS 不是“通过率与坏账率之差”，而是好坏样本累计分布差的最大绝对值。

### 8.2 规则挖掘

目标：从特征中发现可解释、可复现、稳定的候选规则。

#### 8.2.1 单规则挖掘

不允许直接遍历所有可能阈值作为默认方案。V4 使用候选阈值搜索：

1. 数值变量按分位点、业务阈值或 toad/chi 分箱生成候选切点。
2. 类别变量按类别、类别组合或缺失特殊值生成候选规则。
3. 每条候选规则必须满足最小样本数和最小命中率。
4. 排序不能只看 Lift，必须同时输出 hit_rate、bad_capture、bad_rate、passed_bad_rate。
5. 如果有 OOT 或时间窗口，必须输出稳定性对比。

推荐默认约束：

| 约束 | 默认建议 | 是否允许用户覆盖 |
|---|---:|:---:|
| 最小命中样本数 | 50 | ✓ |
| 最小命中率 | 1% | ✓ |
| 最大分箱数 | 8 | ✓ |
| 缺失值 | 单独成箱 | ✓ |
| 排序主指标 | bad_capture + bad_rate + hit_rate 联合看 | ✓ |

#### 8.2.2 CART 规则挖掘

CART 用于发现多条件 AND 组合规则。

默认只支持单棵可解释 CART，不默认启用随机森林规则提取。随机森林高频规则可作为后续扩展，不进入 V4 首版标准模块。

方法论要求：

| 约束 | 要求 |
|---|---|
| 可解释性 | `max_depth` 建议 2-4 |
| 样本稳定性 | `min_samples_leaf` 不低于总样本 1% 或用户指定 |
| 叶子合并 | bad_rate 接近且统计不显著的叶子可合并 |
| 单调性 | 对已知单调特征检查规则方向 |
| 过拟合 | 对比 train/OOT 或 train/test 的 Lift 衰减，衰减过大需警告 |
| 输出 | 每个叶子路径、命中数、命中率、坏账率、Lift、坏客户捕获率 |

#### 8.2.3 规则组合

| 组合方式 | 含义 | 输出要求 |
|---|---|---|
| AND | 多条规则同时命中 | 交集样本、坏账率、命中率 |
| OR | 任一规则命中 | 并集样本、坏账率、命中率 |
| Sequential | 按顺序逐层过滤 | 每层进入人数、命中人数、剩余人数、累计拒绝率 |
| Routing | 不同路由使用不同规则集 | 路由级结果和整体加权结果 |

### 8.3 规则回测与漏斗复盘

该模块吸收原 `rule-analysis` 的核心能力。

适用场景：

1. 已有规则条件，需要离线重建规则结果。
2. 已有拒绝码，需要复盘每条规则命中和漏斗贡献。
3. 需要比较线下模拟结果与线上审批结果。

标准输出：

| 文件 | 内容 |
|---|---|
| `rule_overall_summary.csv` | 总体通过、拒绝、坏账率、金额坏账率 |
| `rule_single_summary.csv` | 每条规则独立命中表现 |
| `rule_funnel_summary.csv` | 按规则顺序的级联漏斗 |
| `rule_hit_detail.csv` | 样本级命中明细 |
| `rule_backtest_report.html` | 可读报告 |

一致性校验：

1. 样本级输出行数必须等于输入行数。
2. 拒绝码必须属于配置中的规则集合。
3. 单规则 `sample_cnt - hit_cnt = pass_cnt`，其中 `sample_cnt` 必须基于已确认分析颗粒度。
4. 级联漏斗下一层进入人数必须等于上一层剩余人数。
5. 审批结果与拒绝码必须一致：有拒绝码则不通过。

### 8.4 策略模拟

目标：给定候选规则、分数截断或路由策略，模拟离线策略效果。

支持模式：

| 模式 | 说明 |
|---|---|
| 规则策略 | 使用规则条件生成通过/拒绝 |
| 分数策略 | 使用 `model_score` 截断生成通过/拒绝 |
| 分数 x 规则 | 分数分层后套不同规则 |
| 路由策略 | 不同 `route` 使用不同规则集 |

核心指标：

| 指标 | 公式或含义 |
|---|---|
| `approval_rate` | 通过样本数 / 总样本数 |
| `reject_rate` | 拒绝样本数 / 总样本数 |
| `pass_bad_rate` | 通过样本坏样本数 / 通过样本数 |
| `reject_bad_rate` | 拒绝样本坏样本数 / 拒绝样本数 |
| `bad_capture` | 拒绝坏样本数 / 总坏样本数 |
| `amount_bad_rate` | 默认 `sum(overdue_unpaid_principal) / sum(drawdown_amount)`，需用户确认 |
| `approval_amount_rate` | 通过样本支用金额 / 总支用金额 |

### 8.5 Swap-in / Swap-out 分析

目标：比较旧策略与新策略的差异，回答“新策略是否更好、好在哪里、代价是什么”。

必需条件：

1. 必须有旧策略结果，或能够重建旧策略结果。
2. 必须有新策略模拟结果。
3. 涉及坏账比较时，必须确认成熟样本口径。

分群定义：

| 分群 | 含义 | 风险标签可观测性 |
|---|---|---|
| `both_pass` | 新旧都通过 | 通常可观测 |
| `both_reject` | 新旧都拒绝 | 通常不可完整观测 |
| `swap_in` | 旧拒新通过 | 风险表现通常需要预估或外部验证 |
| `swap_out` | 旧通过新拒 | 通常可直接用历史表现评估 |

核心指标：

| 指标 | 含义 |
|---|---|
| `delta_approval_rate` | 新旧通过率差异 |
| `delta_pass_bad_rate` | 新旧通过人群坏账率差异 |
| `swap_in_bad_rate` | 被新策略放入人群的坏账率，可能需要预估 |
| `swap_out_bad_rate` | 被新策略挡出人群的坏账率 |
| `swap_out_bad_capture` | 新增拒绝捕获的坏样本占比 |
| `amount_bad_rate_delta` | 金额维度逾期率变化 |

Swap-in 的预估方案不在 V4 中强行固定。可选方法包括相似客群匹配、分数段/路由分层替代、拒绝推断或外部实验数据，但必须在报告中明确假设和偏差风险。

### 8.6 风险指标与稳定性监控

该模块吸收原 `risk-strategy-metrics` 的指标能力，但不做完整 A 卡建模训练。

支持指标：

| 指标 | 用途 |
|---|---|
| IV | 特征区分能力 |
| KS | 分数或变量区分能力 |
| AUC | 存在模型分或概率分时计算 |
| Lift | 规则、分数段或策略命中的风险提升 |
| PSI | 分数、特征、规则命中率或通过率稳定性 |
| bad rate trend | 分箱坏账率趋势和单调性 |

关键约束：

1. 分箱、WOE、IV 只能在开发样本拟合，不得在 OOT 上重新拟合。
2. 监控类 PSI 必须确认基准窗口和对比窗口。
3. 缺失值默认单独成箱。
4. 规则挖掘不能只用 IV 或 Lift 作为唯一决策依据。

### 8.7 报告生成

每个任务都应输出机器可读文件和人可读报告。

| 输出 | 说明 |
|---|---|
| CSV | 明细表、汇总表、规则表、Swap 表 |
| JSON | 任务配置、字段映射、规则配置、运行 manifest |
| HTML | 面向业务和审核的离线分析报告 |

HTML 报告必须包含：

1. 任务背景和用户确认口径。
2. 数据样本范围、时间窗口、成熟样本定义。
3. 核心指标和分母解释。
4. 规则、截断点或策略明细。
5. 风险提示：样本偏差、未成熟样本、拒绝样本无标签、过拟合风险。
6. 离线分析结论和策略备选建议，不包含生产部署动作或上线方案。

---

## 九、推荐目录结构

```text
credit-strategy-analysis/
├── SKILL.md
├── AGENTS.md
├── references/
│   ├── 00-scope-and-routing.md
│   ├── 01-product-and-scenario.md
│   ├── 02-data-contract.md
│   ├── 03-metric-definitions.md
│   ├── rules/
│   │   ├── 01-rule-mining.md
│   │   ├── 02-rule-backtest.md
│   │   ├── 03-rule-funnel.md
│   │   └── 04-rule-combination.md
│   ├── strategy/
│   │   ├── 01-score-cutoff.md
│   │   ├── 02-strategy-simulation.md
│   │   ├── 03-swap-analysis.md
│   │   └── 04-routing-strategy.md
│   ├── monitoring/
│   │   ├── 01-psi-monitoring.md
│   │   ├── 02-rule-drift.md
│   │   └── 03-performance-drift.md
│   └── reporting/
│       └── 01-html-report.md
├── scripts/
│   ├── score_cutoff_optimizer.py
│   ├── rule_miner.py
│   ├── rule_backtester.py
│   ├── strategy_simulator.py
│   ├── swap_analyzer.py
│   ├── metric_reporter.py
│   ├── monitoring_reporter.py
│   └── utils/
│       ├── contracts.py
│       ├── metrics.py
│       ├── rule_engine.py
│       ├── binning.py
│       ├── report_writer.py
│       └── io.py
├── schemas/
│   ├── input_contract.yaml
│   ├── rule_config.schema.json
│   ├── strategy_config.schema.json
│   └── report_manifest.schema.json
├── templates/
│   ├── strategy_report.html.j2
│   └── monitoring_report.html.j2
└── tests/
    ├── test_contracts.py
    ├── test_metrics.py
    ├── test_score_cutoff.py
    ├── test_rule_engine.py
    ├── test_rule_miner.py
    ├── test_rule_backtester.py
    ├── test_strategy_simulator.py
    ├── test_swap_analyzer.py
    └── test_monitoring_reporter.py
```

---

## 十、主入口 SKILL.md 设计

### 10.1 建议名称

```yaml
name: credit-strategy-analysis
description: Use when analyzing credit risk strategies, rule mining, rule backtesting, score cutoff decisions, strategy simulation, swap analysis, PSI drift, IV/KS/Lift diagnostics, or strategy monitoring for lending portfolios.
```

### 10.2 入口路由

| 用户意图 | 路由模块 |
|---|---|
| 找规则、挖规则、找阈值 | `rules/01-rule-mining.md` |
| 已有规则复盘、拒绝码分析、漏斗 | `rules/02-rule-backtest.md` + `rules/03-rule-funnel.md` |
| 分数截断、分数分层、效率前沿 | `strategy/01-score-cutoff.md` |
| 策略通过率、坏账率模拟 | `strategy/02-strategy-simulation.md` |
| 新旧策略对比 | `strategy/03-swap-analysis.md` |
| 不同渠道/分层策略 | `strategy/04-routing-strategy.md` |
| PSI、规则命中漂移、坏账率漂移 | `monitoring/*` |
| 只问指标含义 | `03-metric-definitions.md` |

### 10.3 入口阻塞规则

```text
如果产品、还款方式、场景、任务类型、样本口径、分析颗粒度、标签口径、金额口径缺失，必须先询问用户。
如果标签颗粒度、特征颗粒度和输出颗粒度不一致，且缺少聚合规则，也必须先询问用户。
不得用默认值静默执行。
不得生成生产上线方案。
```

---

## 十一、配置文件设计

### 11.1 策略任务配置

```yaml
task:
  product_type: revolving_equal_payment
  scenario: first_loan_admission
  task_type: strategy_simulation

sample_scope:
  population: mature_booked
  date_col: sample_date
  start_date: 2026-01-01
  end_date: 2026-03-31
  mature_flag_col: mature_flag

analysis_grain:
  grain: customer
  id_cols: [customer_id]
  customer_id_col: customer_id
  loan_id_col: loan_id
  drawdown_id_col: drawdown_id
  label_grain: loan
  feature_grain: customer
  output_grain: customer
  aggregation_rule: any_bad_to_customer

label:
  target_col: Y_label
  bad_definition: DPD30_plus_MOB3
  positive_class: 1

amount_metric:
  numerator: overdue_unpaid_principal
  denominator: drawdown_amount
  formula: sum(numerator) / sum(denominator)

columns:
  id_cols: [customer_id]
  score_col: model_score
  route_col: route
  old_approval_col: old_approval_flag
  old_reject_code_col: old_reject_code
```

### 11.2 规则配置

```yaml
rules:
  - code: R001
    name: high_debt_ratio
    condition:
      field: debt_ratio
      op: ">="
      value: 0.65
  - code: R002
    name: recent_overdue
    condition:
      field: recent_dpd_days
      op: ">"
      value: 0
execution:
  mode: sequential
  default_approval: 1
```

---

## 十二、测试策略

V4 首版至少需要以下测试：

| 测试文件 | 覆盖内容 |
|---|---|
| `test_contracts.py` | 必需列缺失、金额口径未确认、标签异常、未成熟样本处理 |
| `test_metrics.py` | safe division、坏账率、金额坏账率、Lift、PSI、KS |
| `test_score_cutoff.py` | 分数方向、KS、效率前沿、约束截断 |
| `test_rule_engine.py` | AND/OR/sequential、拒绝码顺序、保护列禁止使用 |
| `test_rule_miner.py` | 候选阈值、最小样本数、缺失成箱、不过度遍历 |
| `test_rule_backtester.py` | 单规则汇总、漏斗汇总、拒绝码一致性 |
| `test_strategy_simulator.py` | 通过率、拒绝率、目标通过率反推 |
| `test_swap_analyzer.py` | both_pass、both_reject、swap_in、swap_out |
| `test_monitoring_reporter.py` | PSI 窗口、规则命中漂移、分层监控 |

关键测试原则：

1. 所有分母为 0 的指标必须返回空值或约定值，不允许崩溃。
2. 所有输出必须 UTF-8 编码。
3. 所有 CLI 必须支持 `--input`、`--config`、`--output-dir`。
4. 所有运行必须写出 `run_manifest.json`，记录配置、输入路径、输出路径、样本数和口径。

---

## 十三、V4 不做的事情

以下内容明确不进入 V4 首版：

1. 不做生产系统上线。
2. 不做灰度流量切换。
3. 不直接改线上规则引擎。
4. 不生成生产上线方案或审批材料。
5. 不默认启用随机森林规则提取。
6. 不做完整 A/B 实验平台。
7. 不做完整 A 卡建模训练流程。
8. 不在用户未确认金额口径时计算金额逾期率。
9. 不在用户未确认成熟样本口径时计算坏账表现指标。
10. 不把拒绝样本无标签部分当作已知真实表现。

---

## 十四、V4 相比 V3 的关键修正

| V3 问题 | V4 修正 |
|---|---|
| 仍把 `rule-analysis` 和 `risk-strategy-metrics` 作为外部协作 skill | 合并为一个 `credit-strategy-analysis` |
| 主流程包含上线部署 | 移除上线部署，只保留离线分析 |
| 目录含 `strategy-launch` | 删除上线目录，增加 monitoring/reporting/schema |
| 金额字段仍用单一 `amount` | 拆成 `drawdown_amount` 与 `overdue_unpaid_principal` |
| 金额逾期率写成逾期本金余额 / 放款总额 | 改为默认建议 `逾期未还本金 / 支用金额`，但必须用户确认 |
| 单规则仍遍历所有可能阈值 | 改为候选阈值 + 最小样本 + 最小命中率 + 稳定性约束 |
| KS 定义不严谨 | 明确为好坏样本累计分布差的最大值 |
| 阻塞确认只覆盖产品、还款、场景 | 扩展到任务、样本、标签、成熟样本、金额、旧策略、模型分 |
| Swap-in 预估未形成边界 | 明确可选估计方法和必须披露偏差 |

---

## 十五、建议 Claude 审核重点

请 Claude 重点审核：

1. 合并后的 `credit-strategy-analysis` 是否覆盖原三个 skill 的核心能力。
2. 阻塞式问答是否足够防止静默默认值。
3. 数据契约是否支撑规则挖掘、回测、分数截断、策略模拟、Swap 和监控。
4. 金额维度逾期率默认口径是否继续采用 `逾期未还本金 / 支用金额`。
5. 单规则候选阈值策略是否足够防止过拟合。
6. Score Cutoff、效率前沿和 KS 定义是否满足业务分析需要。
7. Swap-in 预估是否应在 V4 首版只作为风险提示，还是需要指定一种默认估计方法。
