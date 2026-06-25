# 信贷规则策略分析协作规范

## 工作边界

仅支持五阶段离线分析：数据与产品确认、单规则挖掘、Lift TopN 规则组合、策略效果与 Swap、最终报告。不得扩展为线上配置、上线审批、自动发布、灰度、监控或模型训练。

执行前必须由用户确认产品形态、还款方式、场景、样本口径、时间窗口、分析粒度、`id_cols`、字段映射、标签和成熟规则、候选特征、金额口径、规则参数、TopN 与级联语义。涉及 Swap-in 风险估计，还须确认成熟标签、可用时点、观察窗口、估计方法和分箱/压力假设。

## 输出目录包

- 先遵循 `references/06-stage-output-contract.md`。`--run-dir` 必须等于 `output.directory`，所有写入路径必须位于该目录内。
- 根目录固定保存 `input_config.yaml`、`confirmation_receipt.json`、`run_manifest.json`、`source_fingerprint.json`；绝不复制原始输入文件。
- 每阶段固定保存业务表、`stage_manifest.json` 和 `artifact_inventory.json`。默认不得覆盖；恢复仅允许配置、确认、输入指纹和上游哈希完全一致。
- 输出一律 UTF-8。禁止客户标识、原始 JSON、敏感原值或未登记数据进入 CSV、manifest、inventory 或 HTML。
- `feature_name`、候选特征、分箱、单规则和 CART 规则必须遵守当次配置中确认的 `feature_policy.exclude_features` 与 `feature_policy.excluded_name_tokens`。

## 解释约束

- CART 只可抽取根到叶的 AND 路径，且最多 3 个特征。
- 规则组合只允许已确认的 Lift 降序 TopN 与“任一命中即拒绝”的级联语义。
- 成熟风险、金额和 Swap 指标必须披露分母、样本范围与可观测性。
- 无 OOT 时固定写“未评估（未做时间外验证）”；无真实成熟表现时不得用经确认的旧决策字段、审批结果字段或代理标签替代风险结论。
- HTML 只读取已登记、哈希验证通过的阶段产物；不扫描目录、不重算指标、不生成上线建议。

## 验证与提交

每次修改后运行单元测试、YAML/JSON 解析、五个 CLI 的 `--help` 与最小阶段目录包演练。当前技能目录不是 Git 仓库，无法在此目录提交或推送。
