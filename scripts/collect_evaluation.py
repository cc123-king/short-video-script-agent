"""Reassess saved actual runs without repeating paid model calls."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from script_agent.domain import read_json, validate_request
from script_agent.evaluation import assess, save_summary


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--provider", choices=["mock", "qwen"], required=True)
    args = parser.parse_args()
    scenarios = read_json(ROOT / "examples/scenarios.json")["scenarios"]
    rows = []
    for scenario in scenarios:
        path = args.directory / scenario["id"] / "result.json"
        if not path.exists():
            raise SystemExit(f"缺少场景实际记录: {scenario['id']}")
        result = read_json(path)
        expected_mode = "real_model" if args.provider == "qwen" else "offline_mock"
        if result["execution_mode"] != expected_mode or result["request"] != validate_request(read_json(ROOT / scenario["input"])):
            raise SystemExit(f"输入或执行模式不一致: {scenario['id']}")
        rows.append(assess(result, scenario))
    summary = save_summary(rows, args.provider, args.directory)
    print(f"保存实际记录重新汇总: {summary['passed']}/{summary['total']}; mode={summary['execution_mode']}")
    raise SystemExit(0 if summary["all_passed"] else 1)
