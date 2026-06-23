# 信贷策略分析执行约束

## 范围

本技能仅用于离线策略分析、回测、监控和报告。不得生成生产上线、灰度、流量切换或线上规则部署方案。

## 执行顺序

1. 读取 `references/00-scope-and-routing.md` 并向用户确认阻塞口径。
2. 读取 input 后只生成字段映射候选；不得据此执行。
3. 将用户确认内容写入独立 JSON 确认凭证。
4. 运行 `scripts/validate_contract.py`；校验失败时停止并解释缺失项。
5. 根据已确认任务读取对应 reference 并运行对应脚本。

## 不可推断项

不得自行决定分析颗粒度、`id_cols`、跨颗粒度聚合、字段映射、标签定义、成熟口径、金额分子/分母/过滤条件、分数方向或路由口径。`sample_id` 不是默认分析单位。

## 依赖与输出

- Python 依赖见 `requirements.txt`；规则挖掘、WOE、IV、分箱任务必须安装 `toad`。
- CSV 使用 UTF-8-SIG；JSON、YAML、Markdown 和 HTML 使用 UTF-8。
- 每次成功校验或执行都写入 `run_manifest.json`，其中必须包含确认凭证。
