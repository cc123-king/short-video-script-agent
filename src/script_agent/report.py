"""Human-readable evidence, derived only from actual result objects."""
from pathlib import Path

from .domain import narration, write_json


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(result):
    mode = "真实模型运行" if result["execution_mode"] == "real_model" else "离线 Mock：不能证明真实模型决策效果"
    lines = ["# 短视频脚本执行结果", "", f"**{mode}**", "", f"- 模型：`{result['model']}`", f"- 状态：`{result['status']}`", f"- 结束原因：`{result['termination']}`", f"- 结果说明：{result['message']}", f"- 脚本版本：`{result['revision_id']}`", f"- 知识与规则快照：`{result['knowledge_sha256']}`", ""]
    if result["missing_information"]:
        lines.extend(["待补充：" + "；".join(result["missing_information"]), ""])
    if result["script"]:
        lines.extend([f"## {result['script']['title']}", "", "| 分镜 | 画面 | 旁白 | 屏幕文字 | 估算起止（秒） | 事实 ID |", "|---|---|---|---|---|---|"])
        timing = {row["shot_id"]: row for row in (result["duration"] or {}).get("shots", [])}
        pending = {item["shot_id"] for item in (result["rules"] or {}).get("pending_confirmations", [])}
        for shot in result["script"]["shots"]:
            row = timing.get(shot["id"], {})
            facts = ", ".join(s["fact_id"] for s in shot["segments"] if s["fact_id"])
            visual = ("【界面待确认示意】" if shot["id"] in pending else "【创作画面建议】") + shot["visual"]
            values = [shot["id"], visual, narration(shot), shot["on_screen_text"], f"{row.get('start_seconds', '?')}–{row.get('end_seconds', '?')}", facts]
            lines.append("| " + " | ".join(cell(v) for v in values) + " |")
        lines.append("")
    if result["duration"]:
        duration = result["duration"]
        lines.extend([f"预计总时长：**{duration['estimated_total_seconds']} 秒**；上限 {duration['target_seconds']} 秒；时长通过：{duration['within_limit']}。", "", duration["method"] + "。" + duration["limitation"] + "。", ""])
    if result["rules"]:
        rules = result["rules"]
        lines.extend([f"规则检查通过：**{rules['passed']}**。", "", "## 素材引用", "", "| 分镜 | 素材 ID / 版本 | 事实 ID | 来源原文 | 实际使用 |", "|---|---|---|---|---|"])
        for citation in rules["citations"]:
            lines.append("| " + " | ".join(cell(v) for v in [citation["shot_id"], citation["material_id"] + " / " + citation["version"], citation["fact_id"], citation["quote"], citation["used_text"]]) + " |")
        if rules["issues"]:
            lines.extend(["", "风险："] + [f"- {item['code']} / {item['field']}：{item['message']}" for item in rules["issues"]])
        if rules.get("pending_confirmations"):
            lines.extend(["", "## 待确认的界面镜头", "", "以下画面是创作示意，需补充界面资料再细化。脚本文本检查通过不代表这些界面细节已获确认。", ""])
            lines.extend([f"- {item['shot_id']}：{item['reason']}；需补充：{item['required_material']}。" for item in rules["pending_confirmations"]])
        lines.append("")
    lines.extend(["## 实际执行记录", "", "| 步骤 | 工具 | 返回摘要 | 简要行动依据 | 后续动作 |", "|---|---|---|---|---|"])
    for event in result["trace"]:
        next_action = event["next_action"] or {}
        values = [event["step"], event["tool"], event["observation_summary"], event["decision_basis"], next_action.get("tool", next_action.get("status", ""))]
        lines.append("| " + " | ".join(cell(v) for v in values) + " |")
    lines.extend(["", "完整工具参数、返回结果与各版脚本见同目录 result.json。", "", "## 限制", ""] + ["- " + v for v in result["limitations"]])
    return "\n".join(lines) + "\n"


def save_result(directory, result):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    write_json(directory / "input.json", result["request"])
    write_json(directory / "result.json", result)
    (directory / "report.md").write_text(render_markdown(result), encoding="utf-8")
