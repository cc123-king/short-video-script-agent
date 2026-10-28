# 场景验证结果

执行模式：**offline_mock**；通过 11/11；不同工具路径 7。

离线 Mock 结果不能证明真实模型动态决策；场景断言通过不等于完整语义质量验证。

| 场景 | 预期状态 | 实际状态 | 断言通过 | 记录 |
|---|---|---|---|---|
| normal | completed | completed | True | [报告](normal/report.md) / [完整记录](normal/result.json) |
| missing | needs_input | needs_input | True | [报告](missing/report.md) / [完整记录](missing/result.json) |
| no_material | needs_input, blocked | needs_input | True | [报告](no_material/report.md) / [完整记录](no_material/result.json) |
| transient_failure | completed | completed | True | [报告](transient_failure/report.md) / [完整记录](transient_failure/result.json) |
| persistent_failure | tool_failed, incomplete, blocked | tool_failed | True | [报告](persistent_failure/report.md) / [完整记录](persistent_failure/result.json) |
| overtime | completed | completed | True | [报告](overtime/report.md) / [完整记录](overtime/result.json) |
| rule_repair | completed | completed | True | [报告](rule_repair/report.md) / [完整记录](rule_repair/result.json) |
| short_target | completed | completed | True | [报告](short_target/report.md) / [完整记录](short_target/result.json) |
| impossible_target | blocked, incomplete, needs_input | blocked | True | [报告](impossible_target/report.md) / [完整记录](impossible_target/result.json) |
| changed_material | completed | completed | True | [报告](changed_material/report.md) / [完整记录](changed_material/result.json) |
| visual_repair | completed | completed | True | [报告](visual_repair/report.md) / [完整记录](visual_repair/result.json) |
