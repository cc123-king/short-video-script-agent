"""Qwen native function calling; explicitly labelled deterministic offline fixture."""
import copy
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .domain import missing_fields, narration


class ProviderError(RuntimeError):
    pass


def key_plausible(value):
    # Workspace keys can contain dots. Reject masked display values and newlines.
    return isinstance(value, str) and value.startswith("sk-") and len(value) >= 20 and value.isascii() and all(33 <= ord(char) <= 126 and char not in "\"'\\*" for char in value)


def local_config(root):
    keys = {"DASHSCOPE_API_KEY", "QWEN_MODEL", "QWEN_BASE_URL", "QWEN_TIMEOUT_SECONDS"}
    values = {}
    path = Path(root) / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() in keys:
                values[key.strip()] = value.strip().strip("\"'")
    values.update({key: os.environ[key] for key in keys if os.environ.get(key)})
    return values


class QwenProvider:
    mode = "real_model"

    def __init__(self, config):
        self.key = config.get("DASHSCOPE_API_KEY", "")
        if not self.key:
            raise ProviderError("未配置 DASHSCOPE_API_KEY。请在本地执行 python scripts/configure.py，或设置环境变量。")
        if not key_plausible(self.key):
            raise ProviderError("本地 Key 长度或格式异常，请重新执行 python scripts/configure.py 完整输入 Key；Key 未显示。")
        self.model = config.get("QWEN_MODEL", "qwen-plus")
        base = config.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
        url = urllib.parse.urlsplit(base)
        if url.scheme != "https" or not url.netloc or url.username or url.password or url.query or url.fragment:
            raise ProviderError("QWEN_BASE_URL 必须是无凭据、查询参数或片段的 HTTPS 接口地址")
        self.url = base + "/chat/completions"
        try:
            self.timeout = float(config.get("QWEN_TIMEOUT_SECONDS", "60"))
            if not 1 <= self.timeout <= 120:
                raise ValueError()
        except ValueError as exc:
            raise ProviderError("QWEN_TIMEOUT_SECONDS 必须在 1–120 秒之间") from exc
        self.calls = []

    def respond(self, messages, tools):
        payload = {"model": self.model, "messages": messages, "tools": tools, "tool_choice": "auto", "parallel_tool_calls": False, "enable_thinking": False, "temperature": 0.2, "max_tokens": 5000, "stream": False}
        request = urllib.request.Request(self.url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"}, method="POST")
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ProviderError("模型响应超过大小上限")
                data = json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Never print request headers, key, or the server's echoed request body.
            hints = {401: "Key 无效或地域不匹配", 403: "模型权限或工作空间配置受限", 429: "限流或配额不足", 400: "请求参数、模型或地域接口不匹配"}
            raise ProviderError(f"千问 HTTP {exc.code}: {hints.get(exc.code, '服务端请求失败')}；本次未自动重试") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderError("模型网络连接失败或超时；本次未自动重试") from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ProviderError("模型接口返回非有效 JSON") from None
        try:
            message = data["choices"][0]["message"]
            if not isinstance(message, dict):
                raise TypeError()
        except (KeyError, IndexError, TypeError):
            raise ProviderError("模型响应缺少有效 assistant message") from None
        self.calls.append({"model": data.get("model", self.model), "response_id": data.get("id"), "usage": data.get("usage", {}), "latency_seconds": round(time.monotonic() - started, 3)})
        return {"role": "assistant", "content": message.get("content") or "", **({"tool_calls": message["tool_calls"]} if message.get("tool_calls") else {})}


def make_demo_script(request, materials, compact=False):
    facts = [f for material in materials for f in material["facts"]]
    if compact and request["target_seconds"] < 15:
        facts = facts[:1]
    shots = []
    use_bridge = not compact or request["target_seconds"] >= 8
    if use_bridge:
        shots.append({"id": "S1", "visual": "创作者打开一段待编辑视频，切到工作台。", "segments": [{"kind": "bridge", "text": "你的视频，想表达什么？", "fact_id": ""}], "on_screen_text": "你的视频，想表达什么？", "hold_seconds": 3})
    for fact in facts:
        line = fact["approved_lines"][0]
        shots.append({"id": f"S{len(shots) + 1}", "visual": "镜头展示该素材描述的操作界面。", "segments": [{"kind": "fact", "text": line, "fact_id": fact["id"]}], "on_screen_text": line, "hold_seconds": 2 if compact else 3})
    if use_bridge:
        shots.append({"id": f"S{len(shots) + 1}", "visual": "镜头回到创作者和当前视频预览。", "segments": [{"kind": "cta", "text": "试着剪出你的下一条视频。", "fact_id": ""}], "on_screen_text": "试着剪出你的下一条视频。", "hold_seconds": 3})
    hold = max(0.5, min(30, round(request["target_seconds"] * 0.9 / len(shots), 1)))
    for shot in shots:
        shot["hold_seconds"] = hold
    return {"title": "把想法放进画面", "product_id": request["product_id"], "shots": shots}


class MockProvider:
    """Scripted fixture for reproducible tool and boundary tests; not LLM evidence."""
    mode = "offline_mock"
    model = "deterministic-offline-fixture-v1"

    def __init__(self):
        self.calls = []
        self.serial = 0

    def call(self, name, **arguments):
        self.serial += 1
        return {"role": "assistant", "content": "", "tool_calls": [{"id": f"mock-{self.serial}", "type": "function", "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)}}]}

    def respond(self, messages, tools):
        self.calls.append({"model": self.model, "usage": {}, "latency_seconds": 0})
        request = json.loads(messages[1]["content"])["request"]
        if missing_fields(request):
            return self.call("finish", status="needs_input", message="关键输入不足，请补充后再生成。", missing_information=missing_fields(request), reason="离线测试分支：不猜测缺失条件")
        results = [(m["name"], json.loads(m["content"])) for m in messages if m["role"] == "tool"]
        searches = [value for name, value in results if name == "search_materials"]
        materials = [material for value in searches if value.get("ok") for material in value["materials"]]
        unique = {material["id"]: material for material in materials}
        materials = list(unique.values())
        if results and not results[-1][1].get("ok"):
            name, error = results[-1]
            errors = sum(1 for n, value in results if n == name and not value.get("ok"))
            if error.get("error", {}).get("retryable") and errors < 2:
                previous = next(tc["function"] for m in reversed(messages) if m["role"] == "assistant" for tc in m.get("tool_calls", []) if tc["function"]["name"] == name)
                args = json.loads(previous["arguments"])
                args["reason"] = "离线测试分支：观察到暂时性故障，有限重试一次"
                return self.call(name, **args)
            return self.call("finish", status="tool_failed", message="工具无法完成，未宣称脚本成功。", reason="离线测试分支：工具持续失败")
        if not materials:
            if len(searches) >= 2:
                return self.call("finish", status="needs_input", message="资料中没有可用产品事实，请补充素材。", missing_information=["产品事实与素材"], reason="离线测试分支：两次检索无结果")
            query = request["theme"] if not searches else ("轻剪" if request["product_id"] == "clip-demo" else request["product_id"])
            return self.call("search_materials", query=query, reason="离线测试分支：查找素材" if not searches else "离线测试分支：改写检索词")
        estimates = [v for n, v in results if n == "estimate_duration" and v.get("ok")]
        if not estimates:
            script = request.get("initial_script") or make_demo_script(request, materials)
            return self.call("estimate_duration", script=script, reason="离线测试分支：估算输入初稿或合成脚本")
        latest = estimates[-1]
        if not latest["within_limit"]:
            if len(estimates) >= 3:
                return self.call("finish", status="blocked", revision_id=latest["revision_id"], message="现有内容不能满足目标时长，请调整要求。", reason="离线测试分支：有限修正后仍超时")
            return self.call("estimate_duration", script=make_demo_script(request, materials, compact=True), reason="离线测试分支：缩减实际旁白和分镜后重新估算")
        rules = [v for n, v in results if n == "check_rules" and v.get("ok") and v["revision_id"] == latest["revision_id"]]
        if not rules:
            return self.call("check_rules", revision_id=latest["revision_id"], reason="离线测试分支：检查同版本事实与品牌规则")
        if not rules[-1]["passed"]:
            return self.call("estimate_duration", script=make_demo_script(request, materials, compact=True), reason="离线测试分支：改用核准表达并重新检查")
        return self.call("finish", status="completed", revision_id=latest["revision_id"], message="脚本通过文本时长估算和合成规则检查；实际成片需复核。", reason="离线测试分支：最新版本两项检查均通过")
