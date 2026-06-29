# 阶段 4：最终报告

## 适用与阻断条件

用于将阶段 00 至 03 已登记、哈希一致的聚合产物汇总为最终报告包。阶段 4 只做展示、索引和披露，不重新计算 IV、Lift、级联、策略效果、Swap 或风险估计，也不从字段名、对话记录或行业惯例补猜缺失口径。

缺少阶段 manifest、artifact inventory、关键聚合表、可观测性披露或来源哈希不一致时必须阻断。报告可以形成证据支持的策略取舍结论和风险披露，但不自动产生上线决策、放量建议或审批材料。

## 最小输入

- 阶段 00 的确认凭证、输入指纹、数据画像、分析单位检查和字段治理结果。
- 阶段 01 的特征筛选、分箱明细、单规则候选、CART 候选和稳定性输出。
- 阶段 02 的 Lift 排名、入选规则集、级联漏斗、规则重叠和级联 OOT 输出。
- 阶段 03 的策略效果、分层效果、Swap 汇总、Swap 分层、Swap-in 风险估计和覆盖率输出。
- 已确认的报告标题、报告范围、时间窗口、展示层级、脱敏规则和结论措辞边界。

## 方法步骤

1. 读取阶段 00 至 03 的 `stage_manifest.json` 与 `artifact_inventory.json`，校验上游哈希、契约版本、确认凭证和报告可用状态。
2. 只从 inventory 登记的聚合产物构建 `report_source_index.csv`，不得扫描目录、读取原始数据或临时拼接未登记文件。
3. 按固定 HTML 章节组织来源、状态和限制；图表或摘要指标缺少上游登记来源时显示“未提供/不可用”。
4. 按固定 11 Sheet 结构写出 `final_report.xlsx`；每个 Sheet 只展示上游已提供字段和来源状态。
5. 写出 `report_validation.csv`，记录来源哈希、契约、可观测性、缺失产物和不重算指标检查。
6. 将 HTML、XLSX 和两个审计 CSV 一并登记到阶段 04 inventory，并写入 Stage 4 manifest。

## 候选参数

| 参数 | 必须确认的内容 | 作用 |
|---|---|---|
| 报告标题与范围 | 产品、场景、样本范围、时间窗口 | 限定报告结论边界 |
| 展示层级 | 总体及已确认的产品、时间、客群分层 | 防止选择性呈现 |
| 指标展示规则 | 样本指标、金额指标、分母、格式、缺失展示 | 保持口径透明 |
| 脱敏规则 | 字段名、规则表达式、金额和敏感值展示边界 | 防止泄露客户标识、原始 JSON 或敏感原值 |
| 结论措辞 | 证据结论、估计限制、上线决策禁用措辞 | 防止报告替代审批或上线决策 |

## 输出表

| 文件 | 格式 | 固定要求 |
|---|---|---|
| `final_report.html` | HTML | 自包含中文叙事报告；只嵌入已登记聚合产物的展示数据，不读取外部文件 |
| `final_report.xlsx` | XLSX | 11 个固定 Sheet 的结构化报告；缺失内容以“未提供/不可用”呈现 |
| `report_source_index.csv` | CSV | 映射 HTML/XLSX 章节到上游 stage、artifact、relative_path、SHA-256、状态和限制 |
| `report_validation.csv` | CSV | 记录来源校验、哈希校验、契约校验、可观测性校验和缺失披露 |

## HTML 固定章节

| 章节 | 必须回答的问题 | 来源 |
|---|---|---|
| 分析概要 | 产品、场景、样本范围、候选规则、入选规则和主要限制是什么 | 阶段 00-03 manifest 与 inventory |
| 数据与口径 | 分析单位、标签、成熟规则、时间窗口、金额口径和字段治理是什么 | 阶段 00 产物 |
| 单规则挖掘 | 哪些特征/规则可用，IV、单调性、Lift、覆盖率和稳定性状态如何 | 阶段 01 产物 |
| 规则组合策略 | TopN 选择依据、级联漏斗、规则重叠和 OOT 状态如何 | 阶段 02 产物 |
| 策略效果与 Swap | 新旧策略总体效果、分层效果和 four-way Swap 规模如何 | 阶段 03 产物 |
| 风险披露 | 哪些指标为直接观测、估计或不可观测，哪些限制影响结论 | 阶段 00-03 限制与状态 |

所有图表和表格必须标注样本范围、时间窗口、分母、来源文件和观测类型。直接观测、估计、不可观测必须使用不同标签；不可把估计 `swap_in`、未成熟样本或不可观测风险写成确定事实。

## XLSX 固定 Sheet

| Sheet | 内容 | 来源 |
|---|---|---|
| `01_报告摘要` | 基本信息、核心指标状态、Swap 概览、结论与披露 | 阶段 00-03 已登记产物 |
| `02_数据口径` | 字段映射、数据质量、分析单位唯一性、样本口径 | 阶段 00 产物 |
| `03_特征筛选` | 特征状态、IV、覆盖量、单调性、排除原因 | 阶段 01 `feature_screening.csv` |
| `04_分箱明细` | 分箱顺序、好坏分布、bad_rate、WOE、IV 分量、警告 | 阶段 01 `bin_iv_detail.csv` |
| `05_单规则候选` | 规则表达式、命中量、覆盖率、Lift、捕获、误伤、候选状态 | 阶段 01/02 产物 |
| `06_Lift排序` | 排名、规则 ID、Lift、候选状态、选择原因 | 阶段 02 `lift_ranked_rules.csv` |
| `07_级联漏斗` | 执行顺序、进入量、命中拒绝量、剩余量、累计拒绝率 | 阶段 02 `cascade_funnel.csv` |
| `08_规则重叠` | 规则对、重叠量、重叠率、说明 | 阶段 02 `rule_overlap.csv` |
| `09_策略效果` | 策略名称、总体、样本量、拒绝率、通过率、指标状态 | 阶段 03 `strategy_effect_summary.csv` |
| `10_Swap矩阵` | both_pass、both_reject、swap_in、swap_out 的规模、占比和可观测性 | 阶段 03 Swap 产物 |
| `11_风险披露` | 未评估、不可观测、不可估计、金额限制、OOT 限制和来源校验 | 阶段 00-03 manifest、inventory 与 `report_validation.csv` |

XLSX 允许只展示上游已提供字段。若上游未提供某个摘要指标，阶段 4 不补算，必须显示“未提供/不可用”及来源限制。

## 指标展示规则

- 报告中出现的样本量、规则数、TopN、通过/拒绝量、Swap 人群量和风险指标必须能从 `report_source_index.csv` 回溯到上游文件和 SHA-256。
- Claude 建议中的“计算项”必须由阶段 00-03 预计算并登记后展示；阶段 4 不在 HTML 或 XLSX 中临时计算。
- 不使用类 KS 的近似命名作为报告指标名；如需展示捕获与误伤的差值，只能命名为“捕获误伤差”或等价业务描述，并要求上游阶段预计算。
- 金额风险指标仅在配置和确认凭证显式启用金额口径、且阶段 03 已生成对应聚合指标时展示。
- 图表数据必须来自已登记 CSV；图表不可用时显示“未生成/不可用原因”，不能静默隐藏。

## 稳定性与可观测性检查

- OOT、规则稳定性、级联稳定性、成熟表现和 Swap-in 风险估计缺失时，必须在 HTML、XLSX 和 `report_validation.csv` 中披露状态和原因。
- 直接观测、估计、不可观测不得合并成同一个风险结论；估计值必须展示估计方法和假设。
- 若上游产物状态为 `not_available`、`not_applicable` 或 `failed`，报告只能展示状态和限制，不能将空表解读为零风险或零效果。
- 任意客户明细、原始 JSON、敏感原值或未登记来源进入报告即失败。

## 关键伪代码

```text
upstream = load_stage_manifests_and_inventories("00", "01", "02", "03")
assert_registered_paths_and_hashes(upstream)
assert_no_unregistered_source_used()

source_index = build_report_source_index(upstream)
html = render_html_from_registered_artifacts(source_index)
xlsx = render_fixed_workbook_from_registered_artifacts(source_index)

write_stage_04(
    final_report_html=html,
    final_report_xlsx=xlsx,
    report_source_index=source_index,
    report_validation=validation_rows,
)
```

## 验收不变量

- 阶段 4 固定输出 `final_report.html`、`final_report.xlsx`、`report_source_index.csv`、`report_validation.csv`。
- 报告只消费阶段 00-03 已登记且哈希一致的聚合产物，不读取原始数据、不扫描目录、不重算指标。
- 所有结论均可追溯到确认凭证、manifest、inventory 和 `report_source_index.csv`。
- 直接观测、估计、不可观测必须分标签展示；不可用内容必须显式披露原因。
- 报告不输出客户明细、原始 JSON、敏感原值，不自动产生上线或放量建议。

> **固定输出契约：** 先读取 `references/06-stage-output-contract.md`。当前 Stage 4 契约版本为 `1.2`，新增 `final_report.xlsx` 为固定报告产物。
