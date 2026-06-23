# 规则回测

## 适用范围与阻断

用于按已确认规则配置重建离线结果，或复盘已有拒绝码和规则命中。规则条件、规则顺序、拒绝码语义、缺失值处理、分析颗粒度或字段映射缺失时停止。不得把线上通过标识直接当作离线规则重建结果而不说明比较口径。

## 最小输入与按需引用

输入为确认后的规则配置、规则所需字段、分析单位和可选的线上审批/拒绝码。级联分析必须提供顺序；仅有拒绝码时需确认其拆分规则。按需读取 `02-data-contract.md` 的策略字段和 `03-metric-definitions.md` 的第 2、3、5、6 节。

## 方法步骤

1. 校验规则配置结构、规则代码唯一性、字段存在性、操作符和数据类型；将数值、日期、类别和空值按确认语义标准化。
2. 对每个分析单位初始化 `offline_approval=1` 与空拒绝码；同一单位多行时先按已确认聚合规则生成分析单位，不能按原始行直接计数。
3. 独立模式：每条规则在完整分析总体上独立求值，输出其单规则命中表现，不改变其他规则的输入总体。
4. 顺序模式：仅在上一层剩余样本上执行下一条规则；首次或所有命中的拒绝码拼接规则必须由用户确认。
5. 规则命中后设置离线拒绝；按确认规则生成拒绝码、命中明细和通过/拒绝标识。
6. 如存在线上结果，输出离线与线上通过/拒绝、拒绝码的一致性和差异样本；差异只用于复盘，不自动归因为规则错误。
7. 对有成熟标签的可观测样本计算规则和漏斗风险表现；拒绝无表现样本必须标为不可观测。

## 候选参数

| 参数 | 可选方式 | 影响 |
|---|---|---|
| 执行模式 | 独立、顺序或两者同时输出 | 决定分母与命中含义 |
| 多命中拒绝码 | 首条、全部按顺序拼接或其他确认格式 | 决定样本级审计结果 |
| 空值语义 | 缺失不命中、缺失命中或规则专用定义 | 直接影响拒绝量 |
| 类型转换失败 | 停止、标记异常或确认的业务处理 | 防止静默 NaN 改变规则 |
| 线上对比键 | 明确的线上审批/拒绝码字段 | 决定一致性比较范围 |
| 表现样本 | 成熟样本过滤与标签口径 | 决定风险指标分母 |

## 关键伪代码

```text
require confirmed(rule_config, execution_mode, null_semantics, analysis_grain)
units = build_confirmed_analysis_units(input)
validate_rule_fields_and_types(units, rule_config)

independent = []
for rule in ordered_rules:
    hit = evaluate(rule.condition, units, confirmed_null_semantics)
    independent.append(summarize_single_rule(rule, hit, units))

remaining = units
for rule in ordered_rules:
    hit = evaluate(rule.condition, remaining, confirmed_null_semantics)
    append_funnel_step(rule, remaining, hit)
    assign_reject_code(hit, rule, confirmed_code_policy)
    remaining = remaining[not hit]

compare_with_online_result_if_provided()
validate_row_level_and_funnel_invariants()
write_detail_summary_and_manifest()
```

## 输出

| 文件 | 最少字段 |
|---|---|
| `rule_hit_detail.csv` | `analysis_unit_id`、每条规则命中、离线通过标识、离线拒绝码、线上结果（如有） |
| `rule_overall_summary.csv` | 样本量、通过/拒绝量与比例、可观测风险指标、线上对比（如有） |
| `rule_single_summary.csv` | 规则代码、独立命中量、命中率、风险、Lift、捕获、误伤 |
| `rule_funnel_summary.csv` | 层级、进入量、新增拒绝、剩余量、累计拒绝和风险指标 |
| `rule_backtest_manifest.json` | 规则版本、顺序、空值语义、聚合和确认口径 |

## 可观测性与异常

拒绝样本没有真实表现时，不计算为观测 `reject_bad_rate`。规则字段无法转换、配置代码重复、线上拒绝码无法解析、分析单位不唯一或顺序缺失时停止；不得以空字符串、零或默认通过静默替代。

## 验收不变量

- 样本级结果一行对应一个确认的 `analysis_unit_id`。
- 规则代码唯一且输出拒绝码仅来自已确认配置。
- 独立统计满足 `sample_cnt - hit_cnt = pass_cnt`。
- 漏斗中下一层进入量等于上一层剩余量，累计拒绝量单调不减。
- 有拒绝码的样本必须为离线拒绝；无拒绝码的离线状态必须与确认的码策略一致。
