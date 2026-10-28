"""Repeatable scenario runner; assertions inspect artifacts, not model prose."""
from pathlib import Path

from .agent import run_agent
from .domain import read_json, validate_request, write_json
from .knowledge import Knowledge
from .providers import MockProvider, QwenProvider, local_config
from .report import save_result


def assess(result, scenario):
    checks = []
    def check(name, passed):
        checks.append({"name": name, "passed": bool(passed)})
    check("期望任务状态", result["status"] in scenario["expected_statuses"])
    check("未超工具调用上限", result["metrics"]["tool_calls"] <= result["metrics"]["max_tool_calls"])
    if result["status"] == "completed":
        check("最终版本时长通过", result["duration"] and result["duration"]["within_limit"])
        check("最终版本规则通过", result["rules"] and result["rules"]["passed"])
        check("有来源支持", result["rules"] and len(result["rules"]["citations"]) > 0)
        submitted = [event["observation"]["revision_id"] for event in result["trace"] if event["tool"] == "estimate_duration" and event["observation"].get("ok")]
        check("完成于最新版本", submitted and result["revision_id"] == submitted[-1])
    if scenario.get("require_revision"):
        check("实际产生至少两版不同脚本", len(result["revisions"]) >= 2)
        first = next(iter(result["revisions"].values()), None)
        check("首版超时长", first and not first["duration"]["within_limit"])
    if scenario.get("require_rule_repair"):
        failed = [r for r in result["revisions"].values() if r.get("rules") and not r["rules"]["passed"]]
        check("实际检测到规则问题", failed)
        check("规则反馈后修改脚本", failed and len(result["revisions"]) >= 2)
    if scenario.get("require_tool_error"):
        check("记录真实注入的工具失败", any(not event["observation"].get("ok") and event["observation"].get("error", {}).get("code") == "INJECTED_TOOL_FAILURE" for event in result["trace"]))
    if scenario.get("require_no_script"):
        check("不输出成功脚本", result["script"] is None)
    if scenario.get("required_quote"):
        citations = (result["rules"] or {}).get("citations", [])
        check("依据替换后的原文生成", any(item["quote"] == scenario["required_quote"] for item in citations))
    return {"case_id": scenario["id"], "execution_mode": result["execution_mode"], "expected_statuses": scenario["expected_statuses"], "actual_status": result["status"], "passed": all(item["passed"] for item in checks), "checks": checks, "result_file": scenario["id"] + "/result.json", "path": [event["tool"] for event in result["trace"]]}


def evaluate(root, provider_name, output, only=None, on_event=None):
    root, output = Path(root), Path(output)
    scenarios = read_json(root / "examples/scenarios.json")["scenarios"]
    if only:
        scenarios = [scenario for scenario in scenarios if scenario["id"] in only]
        if len(scenarios) != len(set(only)):
            raise ValueError("--only 中存在未知场景")
    rows = []
    for scenario in scenarios:
        if on_event:
            on_event(f"场景 {scenario['id']}")
        knowledge = Knowledge(root / scenario.get("catalog", "data/materials.json"), root / "data/brand_rules.json", root / "data/duration_profile.json")
        provider = MockProvider() if provider_name == "mock" else QwenProvider(local_config(root))
        request = validate_request(read_json(root / scenario["input"]))
        result = run_agent(provider, knowledge, request, failures=scenario.get("failures"), on_event=on_event)
        save_result(output / scenario["id"], result)
        rows.append(assess(result, scenario))
    return save_summary(rows, provider_name, output)


def save_summary(rows, provider_name, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    paths = {tuple(row["path"]) for row in rows}
    summary = {"provider": provider_name, "execution_mode": "offline_mock" if provider_name == "mock" else "real_model", "passed": sum(row["passed"] for row in rows), "total": len(rows), "distinct_tool_paths": len(paths), "all_passed": all(row["passed"] for row in rows), "results": rows, "note": "离线 Mock 结果不能证明真实模型动态决策；场景断言通过不等于完整语义质量验证。"}
    write_json(output / "evaluation.json", summary)
    lines = ["# 场景验证结果", "", f"执行模式：**{summary['execution_mode']}**；通过 {summary['passed']}/{summary['total']}；不同工具路径 {len(paths)}。", "", summary["note"], "", "| 场景 | 预期状态 | 实际状态 | 断言通过 | 记录 |", "|---|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['case_id']} | {', '.join(row['expected_statuses'])} | {row['actual_status']} | {row['passed']} | [报告]({row['case_id']}/report.md) / [完整记录]({row['result_file']}) |")
    (output / "evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary
