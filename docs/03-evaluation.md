# 测试预期、实际结果、失败与限制

## 当前验证状态

- 已执行 **34 项标准库自动化测试，全部通过**：[实际测试输出](../examples/test-results.txt)。
- 已执行 **10 个离线场景与 10 个真实 qwen-plus 场景，各 10/10 通过验收断言**。这里的通过不代表任意输入或全部语义质量均已验证。
- 离线场景结果：[批量报告](../examples/offline/evaluation.md)、[机器可读断言](../examples/offline/evaluation.json)。这些记录只证明离线流程和工具行为。
- 真实模型结果：[批量报告](../examples/real/evaluation.md)、[机器可读断言](../examples/real/evaluation.json)。10 个工具调用序列各不相同；更重要的是，实际反馈确实引起了重写、重试、补检查或结束。
- 两套共 20 个场景的工具参数和返回已通过 `scripts/verify_evidence.py` 在当前资料快照下回放。回放证明工具证据一致，不证明模型身份或全部语义正确。
- 作答者已人工核对正常真实报告中的一条旁白引用和界面待确认标记；其他人工检查如实保留未完成，见 [人工检查清单](06-human-review.md)。

初次配置失败和调试阶段未通过的记录均保留。最终汇总采用同一组场景的已保存实际结果，其中无解时长案例在状态校验修复后单独重跑；未重新请求其他已通过案例来拼接虚构执行过程。

## 真实模型关键结果

| 场景 | 实际结果 | 证据 |
|---|---|---|
| 正常生成 | completed，21.0 秒，逐镜来源与待确认项可核对 | [报告](../examples/real/normal/report.md) |
| 超时初稿 | 39.0 秒 → 17.6 秒，保留 3 个不同脚本版本及检查反馈 | [完整记录](../examples/real/overtime/result.json) |
| 违规宣称 | 初稿“效率提升80%”被检出，实际改写后 17.4 秒并复检通过 | [报告](../examples/real/rule_repair/report.md) |
| 更短目标 | 10 秒上限：20.4 → 17.6 → 13.5 → 9.6 秒 | [完整记录](../examples/real/short_target/result.json) |
| 无解时长 | 1 秒上限，模型尝试修正后明确 blocked，未报成功 | [报告](../examples/real/impossible_target/report.md) |
| 资料替换 | 改用“仅支持导入字幕文件”的新原文，不继续引用旧的字幕编辑事实 | [报告](../examples/real/changed_material/report.md) |
| 暂时故障 | 首次检索失败，模型再查，后续修正规则问题并完成 | [报告](../examples/real/transient_failure/report.md) |
| 持续故障 | 3 次真实注入失败后 blocked，无成功脚本 | [报告](../examples/real/persistent_failure/report.md) |
| 缺输入 / 无素材 | 均 needs_input，列出缺口 | [缺输入](../examples/real/missing/report.md) / [无素材](../examples/real/no_material/report.md) |

## 场景与证据

| 场景 | 预期 | 离线实际证据 |
|---|---|---|
| normal | 正常完成，引用支持事实、时长不超限 | [报告](../examples/offline/normal/report.md) |
| missing | 请求补充平台、时长、风格，不猜测业务条件 | [报告](../examples/offline/missing/report.md) |
| no_material | 补检索或请求素材，不编造事实 | [报告](../examples/offline/no_material/report.md) |
| transient_failure | 观察一次工具失败后调整，恢复完成 | [报告](../examples/offline/transient_failure/report.md) |
| persistent_failure | 明确失败或未完成，不虚报成功 | [报告](../examples/offline/persistent_failure/report.md) |
| overtime | 输入初稿实际超限，修改实际内容，再次通过 | [报告](../examples/offline/overtime/report.md) |
| rule_repair | 初稿包含无依据宣称，检查失败，修改后复检 | [报告](../examples/offline/rule_repair/report.md) |
| short_target | 目标由 30 秒改为 10 秒后调整脚本 | [报告](../examples/offline/short_target/report.md) |
| impossible_target | 1 秒内无法承载现有产品旁白，明确无法完成 | [报告](../examples/offline/impossible_target/report.md) |
| changed_material | 替换资料后实际引用新原文 | [报告](../examples/offline/changed_material/report.md) |

这些场景涵盖正常、缺信息、无资料、工具失败及超时修正/明确失败。`result.json` 保存完整参数和实际返回，不能用报告摘要替代。不同路径的数量也不能单独证明模型智能，必须结合真实模型记录和观察结果判断。

## 关键边界测试

`tests/test_agent.py` 检查：旧版检查不能授权新版；超时/违规不能完成；事实 ID 不等于支持任意宣称；未检索事实不能引用；桥接语和字幕不能夹带宣称；改变原文后旧表达失效；时间轴对应分镜；停止上限；坏 JSON；工具和模型失败；自由文本不能绕过完成门槛。

`tests/test_provider.py` 用 HTTP fixture 检查协议、usage 和错误处理，不把接口 fixture 当作真实模型调用。HTTP 错误不回显 Key 或服务端原始请求体。

运行：

```powershell
python -m unittest discover -s tests -v
python run.py evaluate --provider mock --output work/offline-evaluation
python run.py evaluate --provider qwen --output work/qwen-evaluation
```

## 已发现并修正的问题

1. 评估器最初假定超时场景至少已有一版脚本。模型接口在第一轮失败时出现 `StopIteration`，导致无法汇总失败。已改为空版本时产生失败断言，保留真实失败结果。
2. Key 检查最初只判断非空。本地只有一个字符也被当作已配置，导致无效认证请求。后续又发现过严的字符限制会拒绝含点号的工作空间新 Key。现已支持新格式，拒绝不完整或带星号的脱敏值；格式检查不代替认证。接口应使用控制台显示的工作空间 Base URL。
3. 离线修正最初只保留一条事实，虽然满足时长上限，脚本结构过弱。已调整测试替身，预算允许时保留开场、事实演示、行动语；真实模型提示也明确要求保留内容结构。
4. 第一轮真实模型仅通过 1/3 核心场景：有时把自己应完成的编辑工作当作缺失输入，或提前修改了用户初稿。已明确执行职责、时长仅为上限，并校验初稿首次原样评估。原始记录保留在 `examples/experiments/first-model-pass/`，后续三项核心验证通过的阶段记录在 `examples/experiments/second-model-pass/`。
5. 对持续工具失败，评估接受 `tool_failed`、`incomplete` 或 `blocked` 三种明确未完成状态，同时强制要求实际工具故障证据且无成功脚本。不能仅因模型选用 blocked 标签就误判；也不能把 completed 纳入允许范围。
6. 一次完整真实批次初报 8/10：除上述持续失败标签差异外，模型将 1 秒无解约束误报成 tool_failed。新增故障证据校验后，仅重跑该无解案例，得到 blocked；再对全部已保存实际记录按当前明确判据汇总为 10/10。修复前整批记录保留于 `examples/experiments/full-before-status-fix/`。
7. 真实生成中出现未提供的 UI 控件与手势细节。经作答者选择，将相关镜头逐项标为待确认、要求补充界面素材，避免将创作示意混同于已验证产品事实。

这些修改由 AI 实施并自动验证，不能记为作答者本人亲自修改代码。

## 限制与失败判定

估时只验证文本启发式上限；标题/画面语义需要人工审阅；检索规模和核准文案限制了开放创作能力。真实模型输出存在非确定性，记录保留模型 ID、response ID、usage 和调用次数，重新运行可能产生不同脚本。未开通服务、Key/地域不匹配、网络错误或限流时返回明确失败，不自动降级为“真实模型成功”。
