import argparse
import json
import sys
from pathlib import Path

from .agent import run_agent
from .domain import ValidationError, read_json, validate_request
from .evaluation import evaluate
from .knowledge import Knowledge
from .providers import MockProvider, ProviderError, QwenProvider, key_plausible, local_config
from .report import save_result

ROOT = Path(__file__).resolve().parents[2]


def bounded_int(value):
    number = int(value)
    if not 1 <= number <= 60:
        raise argparse.ArgumentTypeError("必须在 1–60 之间")
    return number


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="有素材依据的短视频脚本 Agent（qwen-plus / 明确标记的离线 Mock）")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="执行一次脚本任务")
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--provider", choices=["mock", "qwen"], default="mock")
    run.add_argument("--output", type=Path, default=ROOT / "work/latest-run")
    run.add_argument("--catalog", type=Path, default=ROOT / "data/materials.json")
    run.add_argument("--duration-profile", type=Path, default=ROOT / "data/duration_profile.json")
    run.add_argument("--max-steps", type=bounded_int, default=14)
    run.add_argument("--max-tool-calls", type=bounded_int, default=24)
    run.add_argument("--faults", type=Path, help="仅供验证的故障计数 JSON，如 {\"search_materials\":1}")
    batch = commands.add_parser("evaluate", help="运行验收场景并保存输入、输出、Trace")
    batch.add_argument("--provider", choices=["mock", "qwen"], default="mock")
    batch.add_argument("--output", type=Path, default=ROOT / "work/evaluation")
    batch.add_argument("--only", nargs="+", help="只运行指定场景 ID")
    commands.add_parser("config-status", help="仅显示模型、接口与 Key 是否存在，不显示 Key")
    args = parser.parse_args(argv)
    try:
        if args.command == "config-status":
            config = local_config(ROOT)
            key = config.get("DASHSCOPE_API_KEY", "")
            print(json.dumps({"model": config.get("QWEN_MODEL", "qwen-plus"), "base_url": config.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"), "api_key_configured": bool(key), "api_key_format_plausible": key_plausible(key)}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "evaluate":
            summary = evaluate(ROOT, args.provider, args.output, args.only, lambda message: print(message, flush=True))
            print(f"验证结果: {summary['passed']}/{summary['total']}；模式={summary['execution_mode']}；目录={args.output.resolve()}")
            return 0 if summary["all_passed"] else 1
        request = validate_request(read_json(args.input))
        knowledge = Knowledge(args.catalog, ROOT / "data/brand_rules.json", args.duration_profile)
        provider = MockProvider() if args.provider == "mock" else QwenProvider(local_config(ROOT))
        failures = read_json(args.faults) if args.faults else {}
        if not isinstance(failures, dict) or any(k not in {"search_materials", "estimate_duration", "check_rules"} or not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 60 for k, v in failures.items()):
            raise ValidationError("故障配置须为工具名到 0–60 整数次数的映射")
        result = run_agent(provider, knowledge, request, max_steps=args.max_steps, max_tool_calls=args.max_tool_calls, failures=failures, on_event=lambda message: print(message, flush=True))
        save_result(args.output, result)
        print(f"状态={result['status']}；模式={result['execution_mode']}；结果={args.output.resolve()}")
        return 0 if result["status"] == "completed" else 2
    except (ValidationError, ProviderError, OSError, ValueError, KeyError) as exc:
        print(f"无法运行: {exc}", file=sys.stderr)
        return 3
