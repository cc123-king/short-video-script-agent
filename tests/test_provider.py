import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from script_agent.providers import ProviderError, QwenProvider, key_plausible


class ProviderTests(unittest.TestCase):
    def test_workspace_key_with_dot_is_supported_but_masked_value_is_not(self):
        self.assertTrue(key_plausible("sk-ws-H.placeholder-not-a-real-key"))
        self.assertFalse(key_plausible("sk-ws-H.*****masked-display"))
        self.assertFalse(key_plausible("sk-ws-H.placeholder\nunsafe"))

    def test_missing_key_is_actionable(self):
        with self.assertRaisesRegex(ProviderError, "DASHSCOPE_API_KEY"):
            QwenProvider({})

    def test_credentials_cannot_be_embedded_in_endpoint(self):
        for url in ("http://example.test", "https://name:secret@example.test", "https://example.test?key=secret"):
            with self.subTest(url=url), self.assertRaises(ProviderError):
                QwenProvider({"DASHSCOPE_API_KEY": "sk-test-secret-placeholder", "QWEN_BASE_URL": url})

    def test_incomplete_key_is_rejected_before_network_call(self):
        with patch("urllib.request.urlopen") as open_url:
            with self.assertRaisesRegex(ProviderError, "格式异常"):
                QwenProvider({"DASHSCOPE_API_KEY": "x"})
            open_url.assert_not_called()

    def test_native_tool_call_request_and_usage_are_preserved(self):
        fixture = {"id": "response-fixture", "model": "qwen-plus", "usage": {"total_tokens": 123}, "choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{"id": "a", "type": "function", "function": {"name": "search_materials", "arguments": '{"query":"字幕","reason":"检索"}'}}]}}]}
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(fixture).encode())) as open_url:
            provider = QwenProvider({"DASHSCOPE_API_KEY": "sk-test-secret-placeholder"})
            result = provider.respond([{"role": "user", "content": "测试"}], [])
            request = open_url.call_args.args[0]
            body = json.loads(request.data)
            self.assertEqual(body["model"], "qwen-plus")
            self.assertFalse(body["enable_thinking"])
            self.assertNotIn("sk-test-secret-placeholder", json.dumps(body))
            self.assertEqual(result["tool_calls"][0]["function"]["name"], "search_materials")
            self.assertEqual(provider.calls[0]["usage"]["total_tokens"], 123)
            self.assertNotIn("sk-test-secret-placeholder", json.dumps(provider.calls))

    def test_http_errors_do_not_leak_key_or_echoed_body(self):
        error = urllib.error.HTTPError("https://example.test", 401, "echo test-secret", {}, io.BytesIO(b"test-secret"))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ProviderError) as caught:
                QwenProvider({"DASHSCOPE_API_KEY": "sk-test-secret-placeholder"}).respond([], [])
            self.assertIn("401", str(caught.exception))
            self.assertNotIn("test-secret", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
