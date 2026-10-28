"""Repository entry point; no editable install required."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from script_agent.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
