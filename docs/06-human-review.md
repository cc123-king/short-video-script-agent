# 作答者人工验收与理解清单

此文件是待执行清单，勾选前必须亲自操作，不将 AI 自动测试替代个人验证。

## 1. 正常运行与事实核对

```powershell
Set-Location 'D:\Projects\short-video-script-agent'
python run.py run --provider qwen --input examples/inputs/normal.json --output work/human-normal
```

查看 `work/human-normal/report.md` 与 `data/materials.json`。

已确认的人工审阅：2026-10-28，作答者查看了 AI 已运行的正常报告，核对一条旁白有原文支持，并确认界面待确认标记正确。该旧版原始报告现保存在 `examples/experiments/before-visual-policy/real/normal/report.md`。后续审查发现旧版画面仍暗示无依据产品能力，已由 AI 修复并重新运行；原有人工审阅不代表作答者已经验收新版全部镜头，也未写成亲自重新运行任务。

- [ ] 标题、分镜、旁白和目标受众相符。
- [ ] 每个产品事实能对应素材 ID、版本和原文。
- [ ] 没有素材未提供的效果数据、价格或功能承诺。
- [ ] 时长、检查结果与脚本版本一致。
- [x] 已对照修复前的真实样例人工核对至少一条旁白与界面待确认标记。

## 2. 超时反馈与实际修正

```powershell
python run.py run --provider qwen --input examples/inputs/overtime.json --output work/human-overtime
```

- [ ] 在 `result.json` 中找到 39 秒初稿的工具返回。
- [ ] 比较前后版本，确认文字、镜头数量或实际停留发生合理修改。
- [ ] 检查修正后仍有清楚的产品介绍，且新版本重新检查。
- [ ] 用自己的话解释工具结果如何改变模型动作。

## 3. 自己选择一次业务改进

可以检查“画面是否可拍摄”“产品卖点是否突出”“字幕是否过密”。发现实际问题后记录：

```text
发现的问题：
依据（文件/版本/分镜）：
我的判断与修改要求：
实际修改者（本人/AI）：
验证命令与结果：
剩余限制：
```

没有发现问题时如实记录检查结果，无需人为制造个人修改。

## 4. 关键代码理解

- `agent.py`：找到模型返回工具调用、工具结果送回下一轮的位置。
- `tools.py`：解释为什么 completed 不能引用旧版本检查。
- `tools.py`：解释真实素材 ID 为什么仍可能对应不受支持的宣称。
- `providers.py`：区分真实千问接入与固定策略离线 Mock。

## 最终提交前

- [ ] 文档中的个人贡献属实，人工验收记录已补充。
- [x] GitHub 仓库已公开，已验证未登录可访问。
- [ ] 提交题号、URL 与最终 commit SHA；SHA 与提交内容一致。
- [ ] `.env` 未跟踪，仓库不包含真实 Key、隐私数据或考试页面截图。
