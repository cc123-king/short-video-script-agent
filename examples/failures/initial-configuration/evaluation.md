# 场景验证结果

执行模式：**real_model**；通过 0/3；不同工具路径 1。

离线 Mock 结果不能证明真实模型动态决策；场景断言通过不等于完整语义质量验证。

| 场景 | 预期状态 | 实际状态 | 断言通过 | 记录 |
|---|---|---|---|---|
| normal | completed | tool_failed | False | [报告](normal/report.md) / [完整记录](normal/result.json) |
| overtime | completed | tool_failed | False | [报告](overtime/report.md) / [完整记录](overtime/result.json) |
| rule_repair | completed | tool_failed | False | [报告](rule_repair/report.md) / [完整记录](rule_repair/result.json) |
