# credit-strategy-analysis 维护者协作规范

本文件面向维护这个技能包的 Agent/开发者；运行时如何使用技能由 `SKILL.md` 和 `references/` 负责。不要在这里重复五阶段路由、CLI 使用说明或业务算法细节。

## 维护边界

- 技能只服务离线信贷策略分析，不扩展为线上配置、上线审批、自动发布、灰度、监控或模型训练。
- 样本字段、样本标签、渠道字段、项目特例排除词不得写死进技能内容；必须放入运行配置、确认凭证或项目产物。
- 固定阶段目录、固定文件名和最小字段集合以 `scripts/utils/output_contract.py` 和 `references/06-stage-output-contract.md` 为准；改变产物名、最小字段或语义时必须提升契约版本。

## 修改原则

- `SKILL.md` 保持精简，只写触发后的运行说明、阶段入口和必要边界。
- 详细流程写入 `references/`，可复用逻辑写入 `scripts/`，schema 写入 `schemas/`，报告模板写入 `templates/`。
- HTML 报告器只能读取已登记且哈希一致的阶段产物，不得扫描目录、读取原始数据或重算上游指标。
- 不输出客户明细、原始 JSON、敏感原值；具体敏感/保护字段由 `analysis_grain.id_cols`、`columns.id_cols`、`feature_policy.protected_columns`、`feature_policy.exclude_features` 和 `feature_policy.excluded_name_tokens` 声明。

## 同步到 Codex 安装目录

- 源仓库为 `D:\my_LLM_project\07-credit-strategy-skills`。
- Codex 实际加载目录为 `C:\Users\david\.codex\skills\credit-strategy-analysis`。
- 同步安装时只复制 Git 跟踪文件；不要复制未跟踪草稿、缓存、`__pycache__` 或临时产物。
- 同步后用 SHA-256 对比源仓库 Git 跟踪文件与安装目录文件，要求缺失数和哈希不一致数均为 0。

## 提交前验证

每次修改后至少执行：

- `py -3.12 -m unittest discover -s tests -v`
- JSON/YAML 解析检查
- 五个 CLI 的 `--help` 检查
- `quick_validate.py` 校验源仓库和安装目录
- 样本字段硬编码扫描，确认正式技能文件未包含项目特例字段
- 安装目录与源仓库 Git 跟踪文件哈希一致性检查

验证通过后再提交。此仓库的远端为 `https://github.com/David-haohao/credit-strategy-analysis.git`，默认分支为 `main`；若直接推送失败，可临时使用本机代理环境变量，不要写入全局代理配置。
