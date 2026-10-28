"""Run required unittest suite and preserve actual output under examples/."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    destination = ROOT / "examples/test-results.txt"
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    with destination.open("w", encoding="utf-8") as stream:
        stream.write(f"Executed at {datetime.now(timezone.utc).isoformat()}\nPython {sys.version}\n\n")
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    print(f"Tests: {result.testsRun}; failures: {len(result.failures)}; errors: {len(result.errors)}; evidence: {destination}")
    raise SystemExit(0 if result.wasSuccessful() else 1)
