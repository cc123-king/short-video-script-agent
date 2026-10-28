"""Replay deterministic tool observations without calling a model or spending tokens."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from script_agent.domain import read_json
from script_agent.knowledge import Knowledge
from script_agent.tools import ToolSession


def verify(directory):
    scenarios = {s["id"]: s for s in read_json(ROOT / "examples/scenarios.json")["scenarios"]}
    files = sorted(Path(directory).glob("*/result.json"))
    if not files:
        raise ValueError("目录中没有 场景/result.json")
    for path in files:
        result = read_json(path)
        scenario = scenarios.get(path.parent.name, {})
        knowledge = Knowledge(ROOT / scenario.get("catalog", "data/materials.json"), ROOT / "data/brand_rules.json", ROOT / "data/duration_profile.json")
        if result["knowledge_sha256"] != knowledge.fingerprint:
            raise ValueError(f"{path.parent.name}: 当前数据/规则快照不同，不能按当前资料回放")
        session = ToolSession(knowledge, result["request"], scenario.get("failures"))
        for step in result["trace"]:
            if session.final is not None:
                raise ValueError(f"{path.parent.name}: 结束后仍有工具执行")
            observed = session.execute(step["tool"], step["parameters"])
            if observed != step["observation"]:
                raise ValueError(f"{path.parent.name}: 第 {step['step']} 步返回不能复现")
        if session.final and session.final["status"] != result["status"]:
            raise ValueError(f"{path.parent.name}: 终态不一致")
        if session.revisions != result["revisions"]:
            raise ValueError(f"{path.parent.name}: 脚本版本或检查结果不一致")
        print(f"PASS {path.parent.name}: {len(result['trace'])} 步工具返回可回放")
    print("回放只验证工具证据一致性，不证明模型身份、语义质量或决策真实性。")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    arguments = parser.parse_args()
    try:
        verify(arguments.directory)
    except (ValueError, KeyError) as exc:
        raise SystemExit(str(exc))
