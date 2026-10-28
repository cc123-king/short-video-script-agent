# 测试预期、实际结果、失败与限制

## 当前验证状态

- 已执行 **41 项标准库自动化测试，全部通过**：[实际测试输出](../examples/test-results.txt)。
- 已执行 **11 个离线场景与 11 个真实 qwen-plus 场景，各 11/11 通过验收断言**，新增无依据画面修正场景。这里的通过不代表任意输入或全部语义质量均已验证。
- 离线场景结果：[批量报告](../examples/offline/evaluation.md)、[机器可读断言](../examples/offline/evaluation.json)。这些记录只证明离线流程和工具行为。
- 真实模型结果：[批量报告](../examples/real/evaluation.md)、[机器可读断言](../examples/real/evaluation.json)。本次完整批次有 9 个不同工具调用序列；更重要的是，实际反馈确实引起了重写、重试、补检查或结束。
- 两套共 22 个场景的工具参数和返回已通过 `scripts/verify_evidence.py` 在当前资料及创作策略快照下回放，包括原始异常参数的检查。回放证明工具证据一致，不证明模型身份或全部语义正确。
- [实际回放输出](../examples/replay-results.txt) 保存在 `examples/`。
- 作答者曾核对修复前正常报告中的一条旁白引用和待确认标记；这不代表已经人工验收新版全部画面，见 [人工检查清单](06-human-review.md)。

当前 `examples/real/` 来自收紧画面规则、澄清占位完成边界及修复异常参数历史后的一次完整 11 场景批次，未手改真实模型的脚本或 Trace。修复前十场景证据原样保存在 [旧版记录](../examples/experiments/before-visual-policy/README.md)；收紧规则后的第一轮中断批次保存在 [调试记录](../examples/experiments/visual-policy-first-pass/README.md)。初次配置及更早调试失败也继续保留。

## 真实模型关键结果

| 场景 | 实际结果 | 证据 |
|---|---|---|
| 正常生成 | completed，20.4 秒；界面仅为不描述操作的占位，逐镜引用可核对 | [报告](../examples/real/normal/report.md) |
| 超时初稿 | 39.0 秒 → 15.9 秒，实际生成新版本并复检 | [完整记录](../examples/real/overtime/result.json) |
| 违规宣称 | 初稿“效率提升80%”被检出，实际改写后 17.6 秒并复检通过；格式异常调用也保留原文 | [报告](../examples/real/rule_repair/report.md) |
| 更短目标 | 10 秒上限：16.2 → 12.5 → 12.5 → 9.6 秒，保留每次实际修改 | [完整记录](../examples/real/short_target/result.json) |
| 无解时长 | 1 秒上限，压缩至 3.0 秒仍超限；完成请求被代码拒绝，最终明确 incomplete | [报告](../examples/real/impossible_target/report.md) |
| 资料替换 | completed，11.0 秒；只引用“仅支持导入字幕文件”，标题与画面不再暗示比例切换 | [报告](../examples/real/changed_material/report.md) |
| 暂时故障 | 首次检索失败，模型再查后完成，20.4 秒 | [报告](../examples/real/transient_failure/report.md) |
| 持续故障 | 3 次实际注入失败后 tool_failed，无成功脚本 | [报告](../examples/real/persistent_failure/report.md) |
| 缺输入 / 无素材 | 均 needs_input，列出缺口 | [缺输入](../examples/real/missing/report.md) / [无素材](../examples/real/no_material/report.md) |
| 画面修正 | 原稿两处无依据能力描述均返回 UNSUPPORTED_VISUAL；模型改稿后 15.0 秒并复检通过 | [完整记录](../examples/real/visual_repair/result.json) |

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
| visual_repair | 待确认标签不能豁免无依据能力，模型实际替换画面再复检 | [报告](../examples/offline/visual_repair/report.md) |

这些场景涵盖正常、缺信息、无资料、工具失败及超时修正/明确失败。`result.json` 保存完整参数和实际返回，不能用报告摘要替代。不同路径的数量也不能单独证明模型智能，必须结合真实模型记录和观察结果判断。

## 关键边界测试

`tests/test_agent.py` 检查：旧版检查不能授权新版；超时/违规不能完成；事实 ID 不等于支持任意宣称；未检索事实不能引用；桥接语和字幕不能夹带宣称；改变原文后旧表达失效；待确认标签不能授权自动字幕或比例切换；未在黑名单中的画面宣称仍会被拒绝；事实卡必须在同镜引用来源；标题不能增加能力；安全占位仍标待确认；时间轴、上限、坏 JSON、异常历史恢复及自由文本不能绕过门槛。

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
7. 旧真实生成中出现未提供的 UI 控件与手势细节，最初按作答者选择标为待确认。进一步复查发现“自动生成文字气泡”“不同比例切换”涉及新增能力，仅标待确认不足。现已限制标题与画面选择，拒绝无依据操作，只允许中性镜头、事实原文文字卡和明确占位；新增 visual_repair 的真实拒绝、修改和复检证据。
8. 收紧规则后的首轮模型把界面占位误判为未完成，且短目标多次微调无效。明确文本脚本的完成边界，并允许短目标删减开场与事实数量。首轮已保存的实际结果保留于 `examples/experiments/visual-policy-first-pass/`，未计入本次完整批次通过数。
9. 模型曾返回缺闭合括号等格式异常参数；旧实现把异常原文回传到历史，兼容接口拒绝后续请求。现在 Trace 保留原文，只在历史副本中规范参数以便继续对话，工具仍返回 INVALID_JSON 且不执行；真实模型在观察格式错误后重新提交成功。异常未被隐藏或自动当作有效调用。

这些修改由 AI 实施并自动验证，不能记为作答者本人亲自修改代码。

## 限制与失败判定

估时只验证文本启发式上限；核准旁白、中性标题及受控画面限制了开放创作能力。没有界面资料时输出占位或事实卡，不能等同于已有可直接拍摄的产品界面演示；素材原文本身、真实品牌要求及成片仍需人工复核。真实模型输出存在非确定性，可能先产生坏参数或尝试错误状态；原始反馈、代码拒绝与后续动作均保留。未开通服务、Key/地域不匹配、网络错误或限流时返回明确失败，不自动降级为“真实模型成功”。
