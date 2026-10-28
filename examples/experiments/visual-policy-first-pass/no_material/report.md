# 短视频脚本执行结果

**真实模型运行**

- 模型：`qwen-plus`
- 状态：`needs_input`
- 结束原因：`model_finished`
- 结果说明：未检索到 product_id='unlisted-coffee-machine' 的产品资料（facts 或 approved_lines），无法生成符合品牌事实引用规则的旁白。请提供该智能咖啡机的真实产品文档、功能说明或核准文案。
- 脚本版本：`None`
- 知识与规则快照：`f0d329e55d221c3ea5276e802516f4e21a13247e05a73bf0721eaefc5ed8f02f`

待补充：product_id='unlisted-coffee-machine' 的产品事实资料（facts）或核准旁白（approved_lines）

## 实际执行记录

| 步骤 | 工具 | 返回摘要 | 简要行动依据 | 后续动作 |
|---|---|---|---|---|
| 1 | search_materials | 检索到 0 条素材:  | 根据 product_id 检索产品合成资料 | finish |
| 2 | finish | 结束状态: needs_input | search_materials 返回空 materials，无可用事实依据生成合规脚本 | needs_input |

完整工具参数、返回结果与各版脚本见同目录 result.json。

## 限制

- 仅生成脚本，未生成或发布视频
- 时长为文本启发式估算，非真实配音实测
- 旁白、标题与画面采用受控表达，限制自由创作；素材与实际成片仍需人工复核
- 离线 Mock 只能验证流程，不能证明真实模型决策效果
