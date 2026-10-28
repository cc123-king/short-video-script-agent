# 短视频脚本执行结果

**真实模型运行**

- 模型：`qwen-plus`
- 状态：`needs_input`
- 结束原因：`model_finished`
- 结果说明：未检索到产品 'unlisted-coffee-machine' 的合成资料（facts 或 approved_lines），无法生成符合品牌规范的旁白内容。请提供该产品的准确名称、型号，或补充其功能事实描述（如支持语音控制、可远程预约、兼容豆粉双模等）以便继续。
- 脚本版本：`None`
- 知识与规则快照：`f0d329e55d221c3ea5276e802516f4e21a13247e05a73bf0721eaefc5ed8f02f`

待补充：product_id 对应的产品事实资料（facts）

## 实际执行记录

| 步骤 | 工具 | 返回摘要 | 简要行动依据 | 后续动作 |
|---|---|---|---|---|
| 1 | search_materials | 检索到 0 条素材:  | 检索产品合成资料以获取事实卡和核准表达 | finish |
| 2 | finish | 结束状态: needs_input | search_materials 返回空 materials，无可用事实卡 | needs_input |

完整工具参数、返回结果与各版脚本见同目录 result.json。

## 限制

- 仅生成脚本，未生成或发布视频
- 时长为文本启发式估算，非真实配音实测
- 旁白、标题与画面采用受控表达，限制自由创作；素材与实际成片仍需人工复核
- 离线 Mock 只能验证流程，不能证明真实模型决策效果
