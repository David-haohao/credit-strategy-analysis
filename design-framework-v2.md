# 风控信贷策略 Skill 设计框架 V2

> 版本: v0.2 | 日期: 2026-06-16 | 状态: 待 Claude 审核

---

## 一、V2 设计结论

V2 将原计划中的 `credit-strategy-skills`、`rule-analysis`、`risk-strategy-metrics` 统一整合为一个 skill：

```text
credit-strategy-analysis
```

该 skill 的定位是：面向信贷风控策略的可复现分析工具箱，覆盖规则挖掘、规则回测、策略模拟、Swap 对比、风险指标评估、稳定性监控和策略分析报告生成。

V2 不负责真实系统上线、灰度发布、流量切换、生产规则部署或上线方案设计。若数据中包含已上线规则结果，仅用于离线复盘和效果评估。

---

## 二、合并后的能力边界

### 2.1 被整合的原 skill

| 原 skill | 原职责 | V2 处理方式 |
|---|---|---|
| `rule-analysis` | 规则引擎重建、规则命中、拒绝码、单规则和级联漏斗回测 | 合并为 `rules/backtest` 与 `rules/funnel` 模块 |
| `risk-strategy-metrics` | IV/KS/PSI、分箱、WOE、Lift、规则挖掘、策略指标 | 合并为 `metrics`、`binning`、`monitoring`、`rule-mining` 模块 |
| `credit-strategy-skills` | 策略设计、策略模拟、Swap、场景路由 | 作为主入口和任务编排层 |

### 2.2 合并后的核心原则

1. 一个入口，一个分析上下文，不再让用户在多个 skill 之间切换。
2. 规则挖掘、规则回测、指标评估使用同一套数据契约和指标口径。
3. 所有分析任务都必须先确认场景、样本口径、标签口径和金额口径。
4. 对缺失关键输入的任务，必须停止并提示用户补充，不自动假设。
5. 生产上线和上线方案不在 skill 范围内，只生成可审阅的离线策略分析交付物。

---

## 三、产品与场景定义

### 3.1 产品 2x2 快捷选项

| | 等额还款 | 一次性还本付息 |
|---|---|---|
| **循环贷** | 有额度、多次支用、按月还本付息 | 有额度、多次支用、到期还本 |
| **非循环贷** | 一次性放款、按月还本付息 | 一次性放款、到期还本 |

每次任务启动时，优先让用户选择上述 2x2 产品形态；同时支持自定义产品说明。

### 3.2 策略场景

| 阶段 | 场景 | 适用产品 | 典型问题 |
|---|---|---|---|
| 贷前 | 首借准入 | 全部 | 是否通过、拒绝原因、准入阈值 |
| 贷前 | 复借准入 | 非循环贷为主 | 历史表现如何影响再次申请 |
| 贷前 | 额度策略 | 全部 | 授信额度或放款金额如何确定 |
| 贷前 | 定价策略 | 全部 | 利率/费率与风险等级如何联动 |
| 支用 | 支用审批 | 循环贷为主，部分非循环贷 | 授信后每次支用是否重新校验 |
| 贷中 | 提额/降额 | 循环贷 | 行为变化后如何调额度 |
| 贷中 | 提价/降价 | 循环贷 | 风险或留存压力变化后如何调价 |
| 贷中 | 预警管控 | 全部 | 是否冻结、限额、人工审核或提醒 |
| 复盘 | 已上线规则表现 | 全部 | 规则是否有效、是否误伤、是否衰减 |

### 3.3 场景适用矩阵

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

## 四、任务启动阻塞问题

每次使用 skill，必须先确认以下信息。没有确认就不得进入脚本执行。

| 问题 | 说明 | 缺失时处理 |
|---|---|---|
| 产品形态 | 2x2 快捷选项或自定义产品 | 停止并询问 |
| 策略场景 | 首借、复借、额度、定价、支用、贷中、复盘等 | 停止并询问 |
| 任务类型 | 规则挖掘、规则回测、策略模拟、Swap、监控、报告 | 停止并询问 |
| 样本口径 | 申请样本、通过样本、放款样本、成熟样本、拒绝样本 | 停止并询问 |
| 标签口径 | 30+/60+/90+ DPD、MOB 窗口、是否剔除未成熟样本 | 停止并询问 |
| 金额口径 | 默认建议为逾期未还本金 / 支用金额，但需用户确认 | 停止并询问 |
| 是否有旧策略结果 | 旧拒绝码、旧通过标识、旧规则命中字段 | Swap/复盘任务缺失则停止 |
| 是否有模型分 | A/B/C 卡分数、分数方向、分数缺失处理 | 分数类任务缺失则停止 |

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

### 6.1 基础必需列

| 字段 | 类型 | 用途 |
|---|---|---|
| `sample_id` | str/int | 样本唯一标识 |
| `sample_date` | datetime | 申请、支用或观测时间 |
| `Y_label` | int, 0/1 | 表现标签，1 表示坏样本 |

### 6.2 金额字段

金额相关字段不得再用单一 `amount` 表示，必须拆开。

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

但该公式只是默认建议。每次任务必须让用户确认金额分子和分母，不能静默采用。

### 6.3 策略与规则字段

| 字段 | 类型 | 用途 |
|---|---|---|
| `old_approval_flag` | int, 0/1 | 旧策略是否通过 |
| `new_approval_flag` | int, 0/1 | 新策略模拟后是否通过 |
| `old_reject_code` | str | 旧策略拒绝码 |
| `new_reject_code` | str | 新策略模拟拒绝码 |
| `route` | str | 路由、渠道、客群或产品分层 |
| `model_score` | float | 模型分 |
| `sample_weight` | float | 样本权重，可选 |

### 6.4 表现期字段

| 字段 | 类型 | 用途 |
|---|---|---|
| `mob` | int | 表现观察期 |
| `dpd_max` | int | 最大逾期天数 |
| `mature_flag` | int, 0/1 | 是否表现成熟 |

规则：涉及坏账率、逾期率、Lift、KS、IV、Swap 坏样本比较时，必须确认是否只使用成熟样本。未成熟样本不能默认混入表现评估。

### 6.5 保护列

以下字段默认禁止作为规则挖掘特征：

```text
sample_id, sample_date, Y_label,
drawdown_amount, overdue_unpaid_principal, outstanding_principal, due_principal,
old_approval_flag, new_approval_flag,
old_reject_code, new_reject_code,
mature_flag, mob, dpd_max
```

如用户明确要求使用其中某个字段，必须在报告中标注为人工指定例外。

---

## 七、核心任务模块

### 7.1 规则挖掘

目标：从特征中发现可解释、可复现、稳定的候选规则。

#### 7.1.1 单规则挖掘

不再直接“遍历所有可能阈值”。V2 改为候选阈值搜索：

1. 数值变量先按分位点、业务阈值或 toad/chi 分箱生成候选切点。
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

#### 7.1.2 CART 规则挖掘

用于发现多条件 AND 组合规则。

默认只支持单棵可解释 CART，不默认启用随机森林规则提取。随机森林高频规则可作为后续增强，不进入 V2 首版。

关键约束：

| 参数 | 默认建议 |
|---|---|
| `max_depth` | 2-4 |
| `min_samples_leaf` | 不低于总样本 1% 或用户指定 |
| `class_weight` | 可选，需在报告中记录 |
| 输出 | 每个叶子路径、命中数、命中率、坏账率、Lift、坏客户捕获率 |

#### 7.1.3 规则组合

支持三类组合：

| 组合方式 | 含义 | 输出要求 |
|---|---|---|
| AND | 多条规则同时命中 | 交集样本、坏账率、命中率 |
| OR | 任一规则命中 | 并集样本、坏账率、命中率 |
| Sequential | 按顺序逐层过滤 | 每层进入人数、命中人数、剩余人数、累计拒绝率 |

---

### 7.2 规则回测与漏斗复盘

该模块吸收原 `rule-analysis` 的核心能力。

适用场景：

1. 已有规则条件，需要离线重建规则结果。
2. 已有拒绝码，需要复盘每条规则命中和漏斗贡献。
3. 需要比较线下模拟结果与线上 `Adm` 或旧审批结果。

必需输入：

| 任务 | 必需字段 |
|---|---|
| 重建规则 | 规则所需特征字段 |
| 拒绝码复盘 | `old_reject_code` 或等价字段 |
| 审批对比 | `old_approval_flag` 或 `Adm` |
| 表现复盘 | `Y_label` + 成熟样本口径 |

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
3. 单规则 `sample_cnt - hit_cnt = pass_cnt`。
4. 级联漏斗下一层进入人数必须等于上一层剩余人数。
5. 线下审批结果与拒绝码必须一致：有拒绝码则不通过。

---

### 7.3 策略模拟

目标：给定一组候选规则或分数截断，模拟新策略效果。

支持模式：

| 模式 | 说明 |
|---|---|
| 规则策略 | 使用规则条件生成通过/拒绝 |
| 分数策略 | 使用 `model_score` 截断生成通过/拒绝 |
| 分数 x 规则 | 分数分层后套不同规则 |
| 路由策略 | 不同 route 使用不同规则集 |

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

反推截断支持两类约束：

1. 目标通过率约束：在满足目标通过率附近寻找坏账率最低方案。
2. 坏账率上限约束：在不超过坏账率上限的前提下寻找最高通过率方案。

---

### 7.4 Swap-in / Swap-out 分析

目标：比较旧策略与新策略的差异，回答“新策略是否更好、好在哪里、代价是什么”。

必需条件：

1. 必须有旧策略结果，或能够重建旧策略结果。
2. 必须有新策略模拟结果。
3. 涉及坏账比较时，必须确认成熟样本口径。

输出分群：

| 分群 | 含义 |
|---|---|
| `both_pass` | 新旧都通过 |
| `both_reject` | 新旧都拒绝 |
| `swap_in` | 旧拒新通过 |
| `swap_out` | 旧通过新拒 |

核心指标：

| 指标 | 含义 |
|---|---|
| `delta_approval_rate` | 新旧通过率差异 |
| `delta_pass_bad_rate` | 新旧通过人群坏账率差异 |
| `swap_in_bad_rate` | 被新策略放入人群的坏账率 |
| `swap_out_bad_rate` | 被新策略挡出人群的坏账率 |
| `swap_out_bad_capture` | 新增拒绝捕获的坏样本占比 |
| `amount_bad_rate_delta` | 金额维度逾期率变化 |

必须支持按 `route`、渠道、产品、分数段、时间窗口分层输出。

---

### 7.5 风险指标与稳定性监控

该模块吸收原 `risk-strategy-metrics` 的指标能力，但不做完整 A 卡建模。

支持指标：

| 指标 | 用途 |
|---|---|
| IV | 特征区分能力 |
| KS | 分数或变量区分能力 |
| AUC | 仅当存在模型分或概率分时计算 |
| Lift | 规则、分数段或策略命中的风险提升 |
| PSI | 分数、特征、规则命中率或通过率稳定性 |
| bad rate trend | 分箱坏账率趋势和单调性 |

关键约束：

1. 分箱、WOE、IV 只能在开发样本拟合，不得在 OOT 上重新拟合。
2. 监控类 PSI 必须确认基准窗口和对比窗口。
3. 缺失值默认单独成箱。
4. 规则挖掘不能只用 IV 或 Lift 作为唯一决策依据。

---

### 7.6 报告生成

每个任务都应输出机器可读文件和人可读报告。

| 输出 | 说明 |
|---|---|
| CSV | 明细表、汇总表、规则表、Swap 表 |
| JSON | 任务配置、字段映射、规则配置、运行 manifest |
| HTML | 面向业务和审核的可读报告 |

HTML 报告必须包含：

1. 任务背景和用户确认口径。
2. 数据样本范围、时间窗口、成熟样本定义。
3. 核心指标和分母解释。
4. 规则/策略明细。
5. 风险提示：样本偏差、未成熟样本、拒绝样本无标签、过拟合风险。
6. 离线分析结论、风险提示和策略备选建议，不包含生产部署动作或上线方案。

---

## 八、推荐目录结构

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
│   │   ├── 01-strategy-simulation.md
│   │   ├── 02-score-cutoff.md
│   │   ├── 03-swap-analysis.md
│   │   └── 04-routing-strategy.md
│   ├── monitoring/
│   │   ├── 01-psi-monitoring.md
│   │   ├── 02-rule-drift.md
│   │   └── 03-performance-drift.md
│   └── reporting/
│       └── 01-html-report.md
├── scripts/
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
    ├── test_rule_engine.py
    ├── test_rule_miner.py
    ├── test_rule_backtester.py
    ├── test_strategy_simulator.py
    ├── test_swap_analyzer.py
    └── test_monitoring_reporter.py
```

---

## 九、主入口 SKILL.md 设计

### 9.1 建议名称

```yaml
name: credit-strategy-analysis
description: Use when analyzing credit risk strategies, rule mining, rule backtesting, strategy simulation, swap analysis, cutoff decisions, PSI drift, IV/KS/Lift diagnostics, or strategy monitoring for lending portfolios.
```

### 9.2 入口路由

用户请求进入后，先判断任务类型：

| 用户意图 | 路由模块 |
|---|---|
| 找规则、挖规则、找阈值 | `rules/01-rule-mining.md` |
| 已有规则复盘、拒绝码分析、漏斗 | `rules/02-rule-backtest.md` + `rules/03-rule-funnel.md` |
| 策略通过率、坏账率模拟 | `strategy/01-strategy-simulation.md` |
| 分数截断、分数分层 | `strategy/02-score-cutoff.md` |
| 新旧策略对比 | `strategy/03-swap-analysis.md` |
| 不同渠道/分层策略 | `strategy/04-routing-strategy.md` |
| PSI、规则命中漂移、坏账率漂移 | `monitoring/*` |
| 只问指标含义 | `03-metric-definitions.md` |

### 9.3 阻塞式确认

入口文档必须明确：

```text
如果产品、场景、任务、样本口径、标签口径、金额口径缺失，必须先询问用户。
不得用默认值静默执行。
```

---

## 十、配置文件设计

### 10.1 策略任务配置

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

label:
  target_col: Y_label
  bad_definition: DPD30_plus_MOB3
  positive_class: 1

amount_metric:
  numerator: overdue_unpaid_principal
  denominator: drawdown_amount
  formula: sum(numerator) / sum(denominator)

columns:
  id_col: sample_id
  score_col: model_score
  route_col: route
  old_approval_col: old_approval_flag
  old_reject_code_col: old_reject_code
```

### 10.2 规则配置

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

## 十一、测试策略

V2 首版至少需要以下测试：

| 测试文件 | 覆盖内容 |
|---|---|
| `test_contracts.py` | 必需列缺失、金额口径未确认、标签异常、未成熟样本处理 |
| `test_metrics.py` | safe division、坏账率、金额坏账率、Lift、PSI、KS |
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

## 十二、V2 不做的事情

以下内容明确不进入 V2 首版：

1. 不做生产系统上线。
2. 不做灰度流量切换。
3. 不直接改线上规则引擎。
4. 不默认启用随机森林规则提取。
5. 不做完整 A/B 实验平台。
6. 不做完整 A 卡建模训练流程。
7. 不在用户未确认金额口径时计算金额逾期率。
8. 不在用户未确认成熟样本口径时计算坏账表现指标。
9. 不生成生产上线方案或审批材料。

---

## 十三、V2 相比 V1 的关键变化

| V1 | V2 |
|---|---|
| 多个 skill 边界并存 | 合并成一个 `credit-strategy-analysis` |
| 数据契约较薄 | 拆分基础字段、金额字段、策略字段、表现期字段 |
| `amount` 字段含义模糊 | 明确 `drawdown_amount` 与 `overdue_unpaid_principal` |
| 金额逾期率未定 | 默认建议逾期未还本金 / 支用金额，但每次必须确认 |
| 单规则遍历所有阈值 | 改为候选阈值 + 最小样本 + 稳定性约束 |
| 包含上线部署 | 移除生产部署和上线方案，只输出离线分析材料 |
| 与 rule-analysis/risk-strategy-metrics 重叠 | 吸收二者能力并重设模块边界 |
| 方法论偏多 | 增加配置、schema、CLI、manifest、测试要求 |

---

## 十四、建议 Claude 审核重点

请 Claude 重点审核以下问题：

1. 合并 `rule-analysis` 与 `risk-strategy-metrics` 后，是否仍有职责边界不清。
2. 数据契约是否足够支撑规则挖掘、规则回测、策略模拟、Swap 和监控。
3. 金额维度逾期率的默认公式是否应继续采用 `逾期未还本金 / 支用金额`。
4. 单规则挖掘的候选阈值策略是否足够防止过拟合。
5. 是否应该在 V2 首版保留 HTML 报告，还是只输出 CSV/JSON。
6. 是否需要在 V2 首版支持时间窗口稳定性，还是放到 V2.1。
7. `credit-strategy-analysis` 是否是合适的最终 skill 名称。
