# 短视频脚本执行结果

**离线 Mock：不能证明真实模型决策效果**

- 模型：`deterministic-offline-fixture-v1`
- 状态：`needs_input`
- 结束原因：`model_finished`
- 结果说明：资料中没有可用产品事实，请补充素材。
- 脚本版本：`None`
- 知识与规则快照：`f0d329e55d221c3ea5276e802516f4e21a13247e05a73bf0721eaefc5ed8f02f`

待补充：产品事实与素材

## 实际执行记录

| 步骤 | 工具 | 返回摘要 | 简要行动依据 | 后续动作 |
|---|---|---|---|---|
| 1 | search_materials | 检索到 0 条素材:  | 离线测试分支：查找素材 | search_materials |
| 2 | search_materials | 检索到 0 条素材:  | 离线测试分支：改写检索词 | finish |
| 3 | finish | 结束状态: needs_input | 离线测试分支：两次检索无结果 | needs_input |

完整工具参数、返回结果与各版脚本见同目录 result.json。

## 限制

- 仅生成脚本，未生成或发布视频
- 时长为文本启发式估算，非真实配音实测
- 旁白、标题与画面采用受控表达，限制自由创作；素材与实际成片仍需人工复核
- 离线 Mock 只能验证流程，不能证明真实模型决策效果
