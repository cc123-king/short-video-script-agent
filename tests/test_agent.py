import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from script_agent.agent import run_agent
from script_agent.domain import ValidationError, missing_fields, read_json, validate_request, validate_script, write_json
from script_agent.evaluation import assess
from script_agent.knowledge import Knowledge
from script_agent.providers import MockProvider, make_demo_script
from script_agent.report import save_result
from script_agent.tools import ToolSession


def knowledge(catalog=None):
    return Knowledge(catalog or ROOT / "data/materials.json", ROOT / "data/brand_rules.json", ROOT / "data/duration_profile.json")


class ScriptToolsTests(unittest.TestCase):
    def setUp(self):
        self.request = read_json(ROOT / "examples/inputs/normal.json")
        self.knowledge = knowledge()
        self.session = ToolSession(self.knowledge, self.request)
        self.materials = self.session.execute("search_materials", {"query": "轻剪", "reason": "测试检索"})["materials"]
        self.script = make_demo_script(self.request, self.materials)

    def call(self, name, **args):
        return self.session.execute(name, {"reason": "基于可见结果进行测试", **args})

    def submit_and_check(self, script=None):
        duration = self.call("estimate_duration", script=script or self.script)
        rules = self.call("check_rules", revision_id=duration["revision_id"])
        return duration, rules

    def test_completed_requires_both_checks_on_latest_content(self):
        duration = self.call("estimate_duration", script=self.script)
        finish = self.call("finish", status="completed", message="完成", revision_id=duration["revision_id"])
        self.assertFalse(finish["ok"])
        self.call("check_rules", revision_id=duration["revision_id"])
        finish = self.call("finish", status="completed", message="完成", revision_id=duration["revision_id"])
        self.assertTrue(finish["ok"])

    def test_older_pass_cannot_authorize_changed_script(self):
        first, _ = self.submit_and_check()
        changed = copy.deepcopy(self.script)
        changed["shots"][0]["visual"] += "切换机位。"
        second = self.call("estimate_duration", script=changed)
        self.assertNotEqual(first["revision_id"], second["revision_id"])
        self.assertFalse(self.call("finish", status="completed", message="完成", revision_id=first["revision_id"])["ok"])
        self.assertFalse(self.call("finish", status="completed", message="完成", revision_id=second["revision_id"])["ok"])

    def test_estimate_uses_actual_narration_not_only_hold(self):
        short = copy.deepcopy(self.script)
        for shot in short["shots"]:
            shot["hold_seconds"] = 0.5
        result = self.call("estimate_duration", script=short)
        self.assertGreater(result["estimated_total_seconds"], len(short["shots"]) * 0.5)
        long = copy.deepcopy(short)
        long["shots"][0]["segments"][0]["text"] *= 5
        other = self.call("estimate_duration", script=long)
        self.assertGreater(other["estimated_total_seconds"], result["estimated_total_seconds"])

    def test_timeline_matches_total_and_each_shot(self):
        result = self.call("estimate_duration", script=self.script)
        previous = 0
        for timing, shot in zip(result["shots"], self.script["shots"]):
            self.assertEqual(timing["shot_id"], shot["id"])
            self.assertEqual(timing["start_seconds"], previous)
            self.assertGreaterEqual(timing["estimated_seconds"], timing["visual_hold_seconds"])
            self.assertGreaterEqual(timing["estimated_seconds"] + 0.01, timing["speech_seconds"])
            previous = timing["end_seconds"]
        self.assertEqual(previous, result["estimated_total_seconds"])

    def test_unretrieved_fact_cannot_be_cited(self):
        empty = ToolSession(self.knowledge, self.request)
        result = empty.execute("estimate_duration", {"script": self.script, "reason": "测试"})
        rules = empty.execute("check_rules", {"revision_id": result["revision_id"], "reason": "测试"})
        self.assertFalse(rules["passed"])
        self.assertIn("UNSEEN_FACT", [item["code"] for item in rules["issues"]])

    def test_real_id_cannot_support_invented_claim(self):
        script = copy.deepcopy(self.script)
        fact_shot = next(shot for shot in script["shots"] if shot["segments"][0]["kind"] == "fact")
        fact_shot["segments"][0]["text"] = "支持自动生成整部电影。"
        _, rules = self.submit_and_check(script)
        self.assertFalse(rules["passed"])
        self.assertIn("UNSUPPORTED_CLAIM", [i["code"] for i in rules["issues"]])

    def test_invented_claim_cannot_hide_in_caption_or_bridge(self):
        script = copy.deepcopy(self.script)
        script["shots"][0]["segments"][0]["text"] = "效率提升80%"
        script["shots"][0]["on_screen_text"] = "支持智能翻译所有语言"
        _, rules = self.submit_and_check(script)
        codes = {item["code"] for item in rules["issues"]}
        self.assertTrue({"UNAPPROVED_COPY", "UNSUPPORTED_CAPTION", "BRAND_RISK"} <= codes)

    def test_rule_failure_cannot_finish_successfully(self):
        unsafe = read_json(ROOT / "examples/inputs/rule_repair.json")["initial_script"]
        duration, rules = self.submit_and_check(unsafe)
        self.assertFalse(rules["passed"])
        self.assertFalse(self.call("finish", status="completed", message="完成", revision_id=duration["revision_id"])["ok"])

    def test_specific_ui_scene_is_marked_pending_even_when_copy_passes(self):
        script = copy.deepcopy(self.script)
        script["shots"][0]["visual"] = "点击右上角按钮，双指缩放预览窗口。"
        _, rules = self.submit_and_check(script)
        self.assertTrue(rules["passed"])
        self.assertTrue(any(item["shot_id"] == script["shots"][0]["id"] and item["status"] == "needs_confirmation" for item in rules["pending_confirmations"]))

    def test_overtime_cannot_finish_successfully(self):
        overtime = read_json(ROOT / "examples/inputs/overtime.json")["initial_script"]
        duration, _ = self.submit_and_check(overtime)
        self.assertFalse(duration["within_limit"])
        self.assertFalse(self.call("finish", status="completed", message="完成", revision_id=duration["revision_id"])["ok"])

    def test_missing_fields_cannot_be_guessed_by_tool(self):
        session = ToolSession(self.knowledge, {"product_id": "clip-demo"})
        result = session.execute("estimate_duration", {"script": self.script, "reason": "测试"})
        self.assertFalse(result["ok"])
        self.assertFalse(session.execute("finish", {"status": "completed", "message": "完成", "reason": "测试"})["ok"])

    def test_product_scope_is_enforced(self):
        session = ToolSession(self.knowledge, {**self.request, "product_id": "other"})
        result = session.execute("search_materials", {"query": "轻剪 字幕", "reason": "测试"})
        self.assertEqual(result["count"], 0)

    def test_script_version_is_immutable(self):
        duration = self.call("estimate_duration", script=self.script)
        self.script["shots"][0]["visual"] = "修改调用者对象"
        self.assertNotEqual(self.session.revisions[duration["revision_id"]]["script"], self.script)

    def test_reselecting_known_content_still_requires_it_to_be_latest(self):
        first, _ = self.submit_and_check()
        changed = copy.deepcopy(self.script)
        changed["title"] = "另一个标题"
        self.submit_and_check(changed)
        self.assertFalse(self.call("finish", status="completed", message="完成", revision_id=first["revision_id"])["ok"])
        selected = self.call("estimate_duration", script=self.script)
        self.assertEqual(first["revision_id"], selected["revision_id"])
        self.assertTrue(self.call("finish", status="completed", message="完成", revision_id=first["revision_id"])["ok"])

    def test_tool_fault_does_not_create_revision(self):
        self.session.failures["estimate_duration"] = 1
        self.assertFalse(self.call("estimate_duration", script=self.script)["ok"])
        self.assertFalse(self.session.revisions)

    def test_unmet_constraint_cannot_be_misreported_as_tool_failure(self):
        result = self.call("finish", status="tool_failed", message="错误分类")
        self.assertFalse(result["ok"])
        self.session.failures["search_materials"] = 1
        self.call("search_materials", query="字幕")
        self.assertTrue(self.call("finish", status="tool_failed", message="检索工具实际失败")["ok"])

    def test_user_initial_draft_must_be_evaluated_before_silent_edits(self):
        request = read_json(ROOT / "examples/inputs/rule_repair.json")
        session = ToolSession(self.knowledge, request)
        changed = session.execute("estimate_duration", {"script": self.script, "reason": "提前改写"})
        self.assertFalse(changed["ok"])
        initial = session.execute("estimate_duration", {"script": request["initial_script"], "reason": "原样检查"})
        self.assertTrue(initial["ok"])

    def test_request_validation_rejects_invalid_numeric_limits(self):
        for value in (True, float("nan"), float("inf"), -1, 1000):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_request({**self.request, "target_seconds": value})

    def test_unknown_script_fields_cannot_override_estimate(self):
        with self.assertRaises(ValidationError):
            validate_script({**self.script, "estimated_total_seconds": 1})

    def test_changed_source_invalidates_old_product_copy(self):
        catalog = copy.deepcopy(self.knowledge.catalog)
        fact = catalog["materials"][0]["facts"][0]
        fact["text"] = "轻剪演示版仅支持导入字幕文件。"
        fact["approved_lines"] = ["支持导入字幕文件。"]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "materials.json"
            write_json(path, catalog)
            changed = knowledge(path)
            self.assertNotEqual(changed.fingerprint, self.knowledge.fingerprint)
            session = ToolSession(changed, self.request)
            session.execute("search_materials", {"query": "轻剪", "reason": "测试"})
            duration = session.execute("estimate_duration", {"script": self.script, "reason": "测试"})
            rules = session.execute("check_rules", {"revision_id": duration["revision_id"], "reason": "测试"})
            self.assertFalse(rules["passed"])


class AgentBoundaryTests(unittest.TestCase):
    def test_all_offline_acceptance_scenarios(self):
        for scenario in read_json(ROOT / "examples/scenarios.json")["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                result = run_agent(MockProvider(), knowledge(ROOT / scenario.get("catalog", "data/materials.json")), read_json(ROOT / scenario["input"]), failures=scenario.get("failures"))
                self.assertEqual(result["execution_mode"], "offline_mock")
                self.assertTrue(assess(result, scenario)["passed"])

    def test_limits_return_explicit_incomplete_with_prior_results(self):
        request = read_json(ROOT / "examples/inputs/normal.json")
        for limits, expected in (({"max_steps": 1}, "step_limit"), ({"max_tool_calls": 1}, "tool_call_limit")):
            with self.subTest(limits=limits):
                result = run_agent(MockProvider(), knowledge(), request, **limits)
                self.assertEqual(result["status"], "incomplete")
                self.assertEqual(result["termination"], expected)
                self.assertEqual(len(result["trace"]), 1)

    def test_bad_model_json_is_observed_then_stopped_by_limit(self):
        class Broken(MockProvider):
            def respond(self, messages, tools):
                message = self.call("search_materials", query="轻剪", reason="测试")
                message["tool_calls"][0]["function"]["arguments"] = "{bad"
                return message
        result = run_agent(Broken(), knowledge(), read_json(ROOT / "examples/inputs/normal.json"), max_steps=2)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["trace"][0]["observation"]["error"]["code"], "INVALID_JSON")

    def test_free_text_cannot_report_completion(self):
        class Pretender(MockProvider):
            def respond(self, messages, tools):
                return {"role": "assistant", "content": "脚本成功并通过所有检查"}
        result = run_agent(Pretender(), knowledge(), read_json(ROOT / "examples/inputs/normal.json"), max_steps=2)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["script"])

    def test_provider_error_is_explicit_failure(self):
        from script_agent.providers import ProviderError
        class Failed(MockProvider):
            def respond(self, messages, tools):
                raise ProviderError("模拟服务不可用")
        result = run_agent(Failed(), knowledge(), read_json(ROOT / "examples/inputs/normal.json"))
        self.assertEqual(result["status"], "tool_failed")
        self.assertEqual(result["termination"], "provider_error")

    def test_failure_before_first_revision_is_reported_without_crashing(self):
        from script_agent.providers import ProviderError
        class Failed(MockProvider):
            def respond(self, messages, tools):
                raise ProviderError("模拟认证失败")
        scenario = next(s for s in read_json(ROOT / "examples/scenarios.json")["scenarios"] if s["id"] == "overtime")
        result = run_agent(Failed(), knowledge(), read_json(ROOT / scenario["input"]))
        report = assess(result, scenario)
        self.assertFalse(report["passed"])
        self.assertEqual(report["actual_status"], "tool_failed")

    def test_report_and_json_are_derived_from_actual_result(self):
        result = run_agent(MockProvider(), knowledge(), read_json(ROOT / "examples/inputs/normal.json"))
        with tempfile.TemporaryDirectory() as temp:
            save_result(temp, result)
            self.assertEqual(read_json(Path(temp) / "result.json"), result)
            report = (Path(temp) / "report.md").read_text(encoding="utf-8")
            self.assertIn("离线 Mock", report)
            self.assertIn("P01", report)
            self.assertIn(str(result["duration"]["estimated_total_seconds"]), report)

    def test_action_trace_contains_arguments_observation_and_next_action(self):
        result = run_agent(MockProvider(), knowledge(), read_json(ROOT / "examples/inputs/normal.json"))
        for event in result["trace"]:
            self.assertTrue(event["parameters"])
            self.assertTrue(event["decision_basis"])
            self.assertIsNotNone(event["next_action"])
            self.assertIn("ok", event["observation"])


if __name__ == "__main__":
    unittest.main()
