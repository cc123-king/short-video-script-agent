# 短视频脚本执行结果

**真实模型运行**

- 模型：`qwen-plus`
- 状态：`tool_failed`
- 结束原因：`model_finished`
- 结果说明：search_materials 连续三次调用失败，无法获取产品事实依据，脚本生成中断。
- 脚本版本：`None`
- 知识与规则快照：`f0d329e55d221c3ea5276e802516f4e21a13247e05a73bf0721eaefc5ed8f02f`

## 实际执行记录

| 步骤 | 工具 | 返回摘要 | 简要行动依据 | 后续动作 |
|---|---|---|---|---|
| 1 | search_materials | INJECTED_TOOL_FAILURE: search_materials 测试故障；工具未完成，本次没有成功结果 | 需获取产品事实依据以生成合规脚本 | search_materials |
| 2 | search_materials | INJECTED_TOOL_FAILURE: search_materials 测试故障；工具未完成，本次没有成功结果 | 原查询失败，改写为更具体的产品 ID + 功能关键词组合 | search_materials |
| 3 | search_materials | INJECTED_TOOL_FAILURE: search_materials 测试故障；工具未完成，本次没有成功结果 | 连续两次失败，降级为宽泛查询以尝试获取基础事实 | finish |
| 4 | finish | 结束状态: tool_failed | 工具不可用，无可用事实支撑旁白 | tool_failed |

完整工具参数、返回结果与各版脚本见同目录 result.json。

## 限制

- 仅生成脚本，未生成或发布视频
- 时长为文本启发式估算，非真实配音实测
- 旁白、标题与画面采用受控表达，限制自由创作；素材与实际成片仍需人工复核
- 离线 Mock 只能验证流程，不能证明真实模型决策效果
