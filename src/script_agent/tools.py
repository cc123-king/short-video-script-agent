"""Business tools and hard checks; these do not choose the next model action."""
import copy
import math
import re

from .domain import ValidationError, digest, missing_fields, narration, text, validate_script
from .content_policy import NEUTRAL_TITLES, NEUTRAL_VISUALS, POLICY_ID, creative_options, fact_visual


def speech_units(value):
    chinese = len(re.findall(r"[\u4e00-\u9fff]", value))
    words = len(re.findall(r"[a-zA-Z]+(?:['’-][a-zA-Z]+)*", value))
    numbers = len(re.findall(r"\d+(?:[.:]\d+)*", value))
    return chinese + words * 1.8 + numbers * 2


def estimate(script, target, profile):
    cursor, rows = 0.0, []
    for shot in script["shots"]:
        voice = speech_units(narration(shot)) / profile["speech_units_per_second"]
        voice = voice * profile["speech_safety_factor"] + profile["pause_seconds_per_shot"]
        caption = speech_units(shot["on_screen_text"]) / profile["subtitle_units_per_second"]
        seconds = math.ceil(max(shot["hold_seconds"], voice, caption) * 10 - 1e-9) / 10
        rows.append({"shot_id": shot["id"], "start_seconds": round(cursor, 1), "end_seconds": round(cursor + seconds, 1), "estimated_seconds": seconds, "speech_seconds": round(voice, 2), "visual_hold_seconds": shot["hold_seconds"], "subtitle_seconds": round(caption, 2)})
        cursor = round(cursor + seconds, 1)
    return {"profile_id": profile["id"], "estimated_total_seconds": cursor, "target_seconds": target, "within_limit": cursor <= target, "over_by_seconds": round(max(0, cursor - target), 1), "shots": rows, "method": "逐镜取画面停留、含安全系数的口播、字幕阅读三者最大值后相加", "limitation": "启发式文本估算，非配音或成片实测"}


def inspect_rules(script, facts, brand, product_id):
    issues, citations, pending = [], [], []
    approved_all = set(brand["bridge_lines"] + brand["cta_lines"])
    if script["title"] not in NEUTRAL_TITLES:
        issues.append({"code": "UNAPPROVED_TITLE", "field": "title", "message": "标题须从不包含产品能力宣称的核准标题中选择", "allowed_titles": list(NEUTRAL_TITLES)})
    if script["product_id"] != product_id:
        issues.append({"code": "PRODUCT_MISMATCH", "field": "product_id", "message": "脚本产品与用户请求不一致"})
    for shot in script["shots"]:
        if re.search(r"界面|按钮|菜单|图标|弹出|选项|时间线|双指|拖|窗口|点击|右上|左下|顶部|底部|输入|样式|位置|App|LOGO", shot["visual"], re.IGNORECASE):
            pending.append({"shot_id": shot["id"], "field": "visual", "status": "needs_confirmation", "reason": "素材只证明产品能力，未提供具体界面、控件位置或操作手势的证据", "required_material": "与该镜头对应的产品截图/录屏或经确认的界面说明"})
        allowed_screen = set(approved_all)
        allowed_screen.add(narration(shot))
        allowed_visuals = set(NEUTRAL_VISUALS)
        for segment in shot["segments"]:
            field = f"shots.{shot['id']}.segments"
            if segment["kind"] == "fact":
                fact = facts.get(segment["fact_id"])
                if fact is None:
                    issues.append({"code": "UNSEEN_FACT", "field": field, "message": f"未检索到的事实 ID: {segment['fact_id']}"})
                elif segment["text"] not in [fact["text"], *fact["approved_lines"]]:
                    issues.append({"code": "UNSUPPORTED_CLAIM", "field": field, "message": "产品旁白必须使用该事实的核准表达", "fact_id": segment["fact_id"]})
                else:
                    allowed_screen.update([fact["text"], *fact["approved_lines"]])
                    allowed_visuals.add(fact_visual(fact))
                    citations.append({"shot_id": shot["id"], "fact_id": fact["id"], "material_id": fact["material_id"], "version": fact["version"], "quote": fact["text"], "used_text": segment["text"]})
            else:
                group = brand["bridge_lines"] if segment["kind"] == "bridge" else brand["cta_lines"]
                if segment["text"] not in group or segment["fact_id"]:
                    issues.append({"code": "UNAPPROVED_COPY", "field": field, "message": "过渡语/行动语必须使用品牌核准表达且不带事实 ID"})
        if shot["visual"] not in allowed_visuals:
            issues.append({"code": "UNSUPPORTED_VISUAL", "field": f"shots.{shot['id']}.visual", "message": "画面只能使用中性镜头、界面占位或本镜已引用事实的原文文字卡；待确认标签不能授权新增产品能力", "allowed_visuals": sorted(allowed_visuals)})
        if shot["on_screen_text"] and shot["on_screen_text"] not in allowed_screen:
            issues.append({"code": "UNSUPPORTED_CAPTION", "field": f"shots.{shot['id']}.on_screen_text", "message": "屏幕文字须为本镜完整旁白或本镜已引用的核准表达"})
    if not citations:
        issues.append({"code": "NO_FACT", "field": "shots", "message": "至少需要一个已检索、经核准的产品事实"})
    fields = [("title", script["title"])]
    for shot in script["shots"]:
        fields.extend([(f"shots.{shot['id']}.visual", shot["visual"]), (f"shots.{shot['id']}.narration", narration(shot)), (f"shots.{shot['id']}.on_screen_text", shot["on_screen_text"])])
    for field, content in fields:
        for pattern in brand["forbidden_patterns"]:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append({"code": "BRAND_RISK", "field": field, "message": f"命中合成品牌限制: {pattern}"})
    return {"passed": not issues, "issues": issues, "citations": citations, "pending_confirmations": pending, "brand_rule_id": brand["id"], "brand_version": brand["version"], "creative_policy_id": POLICY_ID, "manual_review_required": ["实际成片、真实品牌合规及素材原文本身仍需人工复核", "界面占位须补充真实截图或录屏后再细化；不能从占位推断产品功能"]}


class ToolSession:
    def __init__(self, knowledge, request, failures=None):
        self.knowledge, self.request = knowledge, request
        self.failures = dict(failures or {})
        self.facts, self.revisions = {}, {}
        self.latest_revision = None
        self.final = None
        self.observed_failures = []

    def execute(self, name, arguments):
        allowed = {"search_materials", "estimate_duration", "check_rules", "finish"}
        if name not in allowed:
            return {"ok": False, "error": {"code": "UNKNOWN_TOOL", "message": "未知工具"}}
        try:
            if not isinstance(arguments, dict):
                raise ValidationError("工具参数必须是对象")
            text(arguments.get("reason"), "reason", 300)
            if self.failures.get(name, 0) > 0:
                self.failures[name] -= 1
                self.observed_failures.append({"tool": name, "code": "INJECTED_TOOL_FAILURE"})
                return {"ok": False, "error": {"code": "INJECTED_TOOL_FAILURE", "message": f"{name} 测试故障；工具未完成，本次没有成功结果", "retryable": True}}
            return getattr(self, name)(**{k: v for k, v in arguments.items() if k != "reason"})
        except (ValidationError, TypeError, KeyError, ValueError) as exc:
            return {"ok": False, "error": {"code": "INVALID_ARGUMENTS", "message": str(exc)[:300], "retryable": False}}

    def search_materials(self, query):
        query = text(query, "query", 240)
        results = self.knowledge.search(query, self.request.get("product_id", ""))
        for material in results:
            for fact in material["facts"]:
                self.facts[fact["id"]] = {**copy.deepcopy(fact), "material_id": material["id"], "version": material["version"]}
        return {"ok": True, "query": query, "materials": results, "count": len(results), "notice": self.knowledge.catalog["notice"], "creative_options": creative_options(self.facts)}

    def estimate_duration(self, script):
        if missing_fields(self.request):
            raise ValidationError("请先补充关键输入: " + ", ".join(missing_fields(self.request)))
        script = validate_script(script)
        if not self.revisions and self.request.get("initial_script") and script != validate_script(self.request["initial_script"]):
            raise ValidationError("首次提交必须原样使用 initial_script，取得工具反馈后再实际改写，以保留可核对的修正证据")
        revision_id = "rev-" + digest(script)[:16]
        duration = estimate(script, self.request["target_seconds"], self.knowledge.duration)
        self.revisions.setdefault(revision_id, {"script": copy.deepcopy(script), "script_sha256": digest(script), "rules": None})
        self.revisions[revision_id]["duration"] = duration
        self.latest_revision = revision_id
        return {"ok": True, "revision_id": revision_id, "script_sha256": digest(script), **duration}

    def check_rules(self, revision_id):
        if revision_id not in self.revisions:
            raise ValidationError("未知脚本版本；先调用 estimate_duration 提交完整脚本")
        revision = self.revisions[revision_id]
        rules = inspect_rules(revision["script"], self.facts, self.knowledge.brand, self.request["product_id"])
        revision["rules"] = rules
        return {"ok": True, "revision_id": revision_id, "script_sha256": revision["script_sha256"], **rules}

    def finish(self, status, message, revision_id=None, missing_information=None):
        if status not in {"completed", "needs_input", "blocked", "incomplete", "tool_failed"}:
            raise ValidationError("未知任务状态")
        message = text(message, "message", 800)
        if missing_information is None:
            missing_information = []
        if not isinstance(missing_information, list) or len(missing_information) > 12:
            raise ValidationError("missing_information 必须是最多 12 项的数组")
        missing_information = [text(item, "missing_information.item", 200) for item in missing_information]
        if status == "needs_input" and not missing_information:
            raise ValidationError("needs_input 必须说明待补充项")
        if status == "tool_failed" and not self.observed_failures:
            raise ValidationError("没有实际工具执行故障，不能标为 tool_failed。输入无解或时长无法满足应选 blocked/incomplete，并说明约束；参数校验失败不等于业务工具故障")
        if revision_id is not None and revision_id not in self.revisions:
            raise ValidationError("不能结束于未知版本")
        if status == "completed":
            if missing_fields(self.request):
                raise ValidationError("关键输入缺失，不能完成")
            if revision_id is None or revision_id != self.latest_revision:
                raise ValidationError("完成状态必须引用最新提交的脚本版本")
            revision = self.revisions[revision_id]
            if not revision["duration"]["within_limit"] or not revision["rules"] or not revision["rules"]["passed"]:
                raise ValidationError("最新脚本必须通过时长与规则检查，才能标为 completed")
        self.final = {"status": status, "message": message, "revision_id": revision_id, "missing_information": missing_information}
        return {"ok": True, "accepted": True, **self.final}


def tool_definitions():
    def function(name, description, properties, required):
        return {"type": "function", "function": {"name": name, "description": description, "parameters": {"type": "object", "properties": {**properties, "reason": {"type": "string", "description": "根据可见结果给出一句简要行动依据，非内部思维过程"}}, "required": [*required, "reason"], "additionalProperties": False}}}
    segment = {"type": "object", "properties": {"kind": {"type": "string", "enum": ["fact", "bridge", "cta"]}, "text": {"type": "string"}, "fact_id": {"type": "string"}}, "required": ["kind", "text", "fact_id"], "additionalProperties": False}
    shot = {"type": "object", "properties": {"id": {"type": "string"}, "visual": {"type": "string"}, "segments": {"type": "array", "items": segment}, "on_screen_text": {"type": "string"}, "hold_seconds": {"type": "number", "minimum": 0.5, "maximum": 30}}, "required": ["id", "visual", "segments", "on_screen_text", "hold_seconds"], "additionalProperties": False}
    script = {"type": "object", "properties": {"title": {"type": "string"}, "product_id": {"type": "string"}, "shots": {"type": "array", "items": shot, "minItems": 1, "maxItems": 12}}, "required": ["title", "product_id", "shots"], "additionalProperties": False}
    return [function("search_materials", "检索当前产品的合成资料。无结果时可改写 query；结果中的 facts 和 approved_lines 是产品旁白的依据。", {"query": {"type": "string"}}, ["query"]), function("estimate_duration", "提交完整脚本并估时。script 仅有 title/product_id/shots 三个字段。有 initial_script 时首次原样提交；任何修改后重新调用。", {"script": script}, ["script"]), function("check_rules", "检查已提交版本的事实引用与品牌规则，返回逐镜问题和引用。", {"revision_id": {"type": "string"}}, ["revision_id"]), function("finish", "结束任务。最新版本两项检查通过才可 completed。编辑/补镜头由你实际执行，不得当作缺失用户信息。", {"status": {"type": "string", "enum": ["completed", "needs_input", "blocked", "incomplete", "tool_failed"]}, "message": {"type": "string"}, "revision_id": {"type": ["string", "null"]}, "missing_information": {"type": "array", "items": {"type": "string"}}}, ["status", "message"])]
