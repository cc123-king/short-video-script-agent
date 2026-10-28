# 短视频脚本执行结果

**离线 Mock：不能证明真实模型决策效果**

- 模型：`deterministic-offline-fixture-v1`
- 状态：`tool_failed`
- 结束原因：`model_finished`
- 结果说明：工具无法完成，未宣称脚本成功。
- 脚本版本：`None`
- 知识与规则快照：`f0d329e55d221c3ea5276e802516f4e21a13247e05a73bf0721eaefc5ed8f02f`

## 实际执行记录

| 步骤 | 工具 | 返回摘要 | 简要行动依据 | 后续动作 |
|---|---|---|---|---|
| 1 | search_materials | INJECTED_TOOL_FAILURE: search_materials 测试故障；工具未完成，本次没有成功结果 | 离线测试分支：查找素材 | search_materials |
| 2 | search_materials | INJECTED_TOOL_FAILURE: search_materials 测试故障；工具未完成，本次没有成功结果 | 离线测试分支：观察到暂时性故障，有限重试一次 | finish |
| 3 | finish | 结束状态: tool_failed | 离线测试分支：工具持续失败 | tool_failed |

完整工具参数、返回结果与各版脚本见同目录 result.json。

## 限制

- 仅生成脚本，未生成或发布视频
- 时长为文本启发式估算，非真实配音实测
- 旁白、标题与画面采用受控表达，限制自由创作；素材与实际成片仍需人工复核
- 离线 Mock 只能验证流程，不能证明真实模型决策效果
