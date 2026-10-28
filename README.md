# 有素材依据的短视频脚本 Agent

面向内容创作者和营销运营，将主题、受众、平台、目标时长和风格转为可编辑分镜脚本。使用 **千问 `qwen-plus` 的原生工具调用**选择检索、检查、修正或结束；代码负责事实表达、版本一致性、时长及执行上限的校验。

所有产品资料和品牌规则都是合成测试数据，不代表小影科技或其产品的功能。业务背景调研见 [需求说明](docs/01-requirements.md)。本项目生成脚本，不生成或发布视频。

## 评审入口

1. 阅读 [方案设计](docs/02-solution.md)，了解模型决策与代码约束的分工。
2. 阅读 [评估说明](docs/03-evaluation.md)、[真实千问实际运行结果](examples/real/evaluation.md) 和 [离线实际运行结果](examples/offline/evaluation.md)。本次 41 项自动化测试通过，真实模型及离线各 11 个场景断言通过，包含无依据画面的实际修正。**离线 Mock 只验证流程，不能证明模型决策效果。**
3. `result.json` 包含完整输入、各版脚本、工具参数、工具返回、后续动作和简要依据；`report.md` 提供分镜、时长、来源及路径的可读视图。
4. 按下列命令重新运行。测试不需要 API Key。

## 环境和安装

- Python **3.11+**，在 Windows Python 3.12 实测。
- **无第三方运行依赖**，无需安装 Agent 框架或数据库。
- CLI 入口使用仓库内 `src/`；不需要 `pip install -e .`。
- `requirements.txt` 明确标注无第三方依赖。

在 PowerShell 中进入本仓库（示例路径）：

```powershell
Set-Location 'D:\Projects\short-video-script-agent'
python --version
python -m unittest discover -s tests -v
```

macOS/Linux 同样使用 `python3 run.py ...`，并使用自己的仓库路径。

## 无 Key 离线运行

```powershell
python run.py run --provider mock --input examples/inputs/normal.json --output work/my-offline-run
python run.py evaluate --provider mock --output work/offline-evaluation
```

单次运行产生 `input.json`、`result.json` 和 `report.md`。批量运行还产生 `evaluation.json`、`evaluation.md`。输出明确标记 `offline_mock`。

## 千问真实模型运行

先在阿里云百炼开通相应地域的模型服务及 API Key。**使用控制台 API Key 页显示的 OpenAI 兼容 Base URL，并保证 Key、工作空间与地域匹配。** 新工作空间地址形如 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`，不要把 `{WorkspaceId}` 原样填入。默认 DashScope 地址仅保留旧接口兼容。参考 [千问 Function Calling 官方文档](https://help.aliyun.com/zh/model-studio/qwen-function-calling) 及 [兼容接口说明](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope)。

```powershell
python scripts/configure.py
python run.py config-status
python run.py run --provider qwen --input examples/inputs/normal.json --output work/my-qwen-run
python run.py evaluate --provider qwen --output work/qwen-evaluation
```

配置脚本不回显 Key，写入被 Git 排除的 `.env`；也支持同名环境变量，环境变量优先。字段见 `.env.example`：

Windows 隐藏输入不便时，可改运行 `python scripts/configure_gui.py`，在本地星号输入框粘贴 Key 后保存。该窗口只保存配置，不上传文件或调用模型；需要 Python 自带的 Tkinter。

| 字段 | 默认 / 用途 |
|---|---|
| `DASHSCOPE_API_KEY` | 必填，仅真实模型需要 |
| `QWEN_MODEL` | `qwen-plus` |
| `QWEN_BASE_URL` | 按控制台填写工作空间接口；代码回退值为旧 DashScope 兼容地址 |
| `QWEN_TIMEOUT_SECONDS` | `60`，范围 1–120 秒 |

`config-status` 仅显示 Key 是否存在、是否符合基本格式，不显示内容；支持含点号的工作空间新 Key，拒绝带星号的脱敏值。新 Key 只在创建时显示一次，需复制完整值或保存在本地。格式检查通过不等于认证成功。真实调用会产生模型服务费用；每次任务最多 14 轮模型决策、24 次工具调用。HTTP 请求不自动重试。

## 输入和输出

示例输入：

```json
{
  "theme": "轻剪演示版的字幕与竖屏创作介绍",
  "audience": "刚开始制作短视频的内容创作者",
  "platform": "抖音",
  "target_seconds": 30,
  "style": "简洁、友好，展示实际操作，不夸大效果",
  "product_id": "clip-demo"
}
```

支持可选 `initial_script`，用于评估并修正用户提供的初稿，结构见 `examples/inputs/overtime.json`。该案例的六个镜头各停留 6.5 秒，实际初次估算为 39 秒，要求修改到 18 秒以内。

输出状态：`completed`、`needs_input`、`blocked`、`incomplete`、`tool_failed`。`completed` 仅代表该脚本通过本项目的文本时长估算和合成规则检查，仍需人工复核画面语义和实际成片。

## 复现不同反馈与上限

```powershell
python run.py run --provider qwen --input examples/inputs/overtime.json --output work/overtime
python run.py run --provider qwen --input examples/inputs/rule_repair.json --output work/rule-repair
python run.py run --provider mock --input examples/inputs/normal.json --max-tool-calls 1 --output work/limited
python run.py evaluate --provider qwen --only normal overtime rule_repair visual_repair --output work/focused-evaluation
python scripts/verify_evidence.py examples/offline
```

自定义工具故障：创建 JSON 文件，例如 `{"search_materials":1}`，通过 `run --faults 文件路径` 注入一次检索失败。故障发生在工具端；模型不预先获知失败次数，是否重试由模型看到错误后决定。批量场景定义见 `examples/scenarios.json`。

替换 `data/materials.json` 或通过 `--catalog 新文件` 指定资料，可检查模型是否根据新事实改变脚本。使用 `--duration-profile 新文件` 可改变估算语速，检查后续动作是否改变。

退出码：`0` 成功任务 / 全部场景断言通过；`1` 批量验证存在失败；`2` 单任务未完成或需补充；`3` 配置或输入错误。

## 目录

```text
src/script_agent/    Agent 循环、千问接口、离线 Mock、工具、校验、报告
tests/              标准库 unittest 可执行测试
data/               合成产品素材、品牌规则、中文时长模型
examples/inputs/    可复制的请求与用户初稿
examples/offline/   实际离线输入、输出、Trace、批量结果
examples/real/      实际 qwen-plus 输入、输出、Trace、批量结果
examples/experiments/  保留的调试阶段结果，包括未通过案例
examples/test-results.txt  实际自动测试输出
examples/scenarios.json
docs/               需求、方案、评估、AI 使用、复盘
scripts/            本地 Key 配置、证据回放、交付打包
.github/workflows/  无密钥 CI
```

## 已知限制

- 中文口播估时为可解释的启发式模型，不是 TTS 或视频时长测量，不保证每位配音者的实际语速。
- 旁白使用素材核准表达；标题使用中性核准标题。没有界面资料时，画面仅接受中性镜头、明确占位或本镜已引用事实的原文文字卡。该受控表达方案限制自由创作，不能声称验证了任意自由文本的语义真实性。
- 本地关键词/字词匹配适合小规模合成库，不等同于生产级语义检索。
- 一次任务内资料固定为快照；不实现跨进程任务恢复、协作式编辑或真实平台发布。
- 已完成真实模型验证和一项作答者人工审阅；其他人工验收尚未执行的项目保留未勾选，详见评估和 AI 使用说明。
