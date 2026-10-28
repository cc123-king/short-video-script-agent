"""Small, explicit validation boundary for untrusted model/tool arguments."""
import hashlib
import json
import math
from pathlib import Path


class ValidationError(ValueError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def text(value, name, maximum=200, allow_empty=False):
    if not isinstance(value, str) or (not value.strip() and not allow_empty) or len(value) > maximum:
        raise ValidationError(f"{name} 必须是长度不超过 {maximum} 的字符串")
    return value.strip()


def number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValidationError(f"{name} 必须在 {low} 到 {high} 之间")
    return value


def validate_request(request):
    if not isinstance(request, dict):
        raise ValidationError("输入必须是 JSON 对象")
    value = dict(request)
    # Missing business fields are returned to the model for clarification, not guessed.
    for name in ("theme", "audience", "platform", "style", "product_id"):
        if name in value and value[name] is not None:
            value[name] = text(value[name], name, 300, allow_empty=True)
    if value.get("target_seconds") is not None:
        number(value["target_seconds"], "target_seconds", 1, 180)
    if "initial_script" in value:
        value["initial_script"] = validate_script(value["initial_script"])
    if len(canonical(value)) > 24000:
        raise ValidationError("输入超过 24000 字符上限")
    return value


def missing_fields(request):
    return [key for key in ("theme", "audience", "platform", "style", "product_id", "target_seconds") if request.get(key) in (None, "")]


def validate_script(script):
    if not isinstance(script, dict):
        raise ValidationError("script 必须是对象")
    if set(script) != {"title", "product_id", "shots"}:
        raise ValidationError("script 字段必须为 title、product_id、shots")
    output = {"title": text(script["title"], "title", 60), "product_id": text(script["product_id"], "product_id", 40), "shots": []}
    if not isinstance(script["shots"], list) or not 1 <= len(script["shots"]) <= 12:
        raise ValidationError("shots 必须有 1–12 个分镜")
    seen = set()
    for shot in script["shots"]:
        if not isinstance(shot, dict) or set(shot) != {"id", "visual", "segments", "on_screen_text", "hold_seconds"}:
            raise ValidationError("分镜字段必须为 id、visual、segments、on_screen_text、hold_seconds")
        sid = text(shot["id"], "shot.id", 20)
        if sid in seen:
            raise ValidationError("分镜 ID 重复")
        seen.add(sid)
        segments = shot["segments"]
        if not isinstance(segments, list) or not 1 <= len(segments) <= 6:
            raise ValidationError("每个分镜必须有 1–6 个旁白片段")
        clean = []
        for segment in segments:
            if not isinstance(segment, dict) or set(segment) - {"kind", "text", "fact_id"}:
                raise ValidationError("旁白片段字段错误")
            kind = segment.get("kind")
            if kind not in ("fact", "bridge", "cta"):
                raise ValidationError("旁白片段 kind 必须为 fact、bridge 或 cta")
            clean.append({"kind": kind, "text": text(segment.get("text"), "segment.text", 160), "fact_id": text(segment.get("fact_id", ""), "fact_id", 40, allow_empty=True)})
        output["shots"].append({"id": sid, "visual": text(shot["visual"], "visual", 240), "segments": clean, "on_screen_text": text(shot["on_screen_text"], "on_screen_text", 180, allow_empty=True), "hold_seconds": number(shot["hold_seconds"], "hold_seconds", 0.5, 30)})
    return output


def narration(shot):
    return "".join(segment["text"] for segment in shot["segments"])
