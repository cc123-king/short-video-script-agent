"""Interactive local key entry. Never send a key through chat or a CLI argument."""
import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from script_agent.providers import key_plausible, local_config


def main():
    root = Path(__file__).resolve().parents[1]
    target = root / ".env"
    print("配置千问 qwen-plus。Key 不回显；仅写入本地 .env，已在 .gitignore 中排除。")
    if target.exists():
        choice = input("已有 .env，是否替换模型配置？输入 yes 才继续: ").strip()
        if choice != "yes":
            print("已保留原配置。")
            return
    default_base = local_config(root).get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    print("使用控制台显示的 Base URL；工作空间 Key 应匹配专属域名。")
    base = input(f"接口地址（回车使用 {default_base}）: ").strip() or default_base
    if not base.startswith("https://") or any(char in base for char in "\r\n\"'"):
        raise SystemExit("接口地址格式无效。")
    key = getpass.getpass("DASHSCOPE_API_KEY（输入不显示）: ").strip()
    if not key_plausible(key):
        raise SystemExit("这不像完整的百炼 API Key：应以 sk- 开头且长度至少 20。未写入，请从控制台完整复制后重新运行。")
    target.write_text(f"DASHSCOPE_API_KEY={key}\nQWEN_MODEL=qwen-plus\nQWEN_BASE_URL={base}\nQWEN_TIMEOUT_SECONDS=60\n", encoding="utf-8")
    print("已保存本地配置；未显示 Key。可执行 python run.py config-status 检查。")


if __name__ == "__main__":
    main()
