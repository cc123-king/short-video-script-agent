"""Create an explicitly scoped source/evidence archive, excluding local credentials."""
import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = {"src", "tests", "data", "examples", "docs", "scripts", ".github"}
FILES = {"README.md", "requirements.txt", "pyproject.toml", "run.py", ".env.example", ".gitignore"}


def package(destination):
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    included = []
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            if relative.parts[0] not in DIRECTORIES and relative.as_posix() not in FILES:
                continue
            if any(part in {"__pycache__", "real-runs"} for part in relative.parts):
                continue
            if path.name.startswith(".env") and path.name != ".env.example":
                continue
            if path.suffix in {".pyc", ".pyo", ".zip"} or path == destination:
                continue
            archive.write(path, "short-video-script-agent/" + relative.as_posix())
            included.append(relative.as_posix())
    if any(item == ".env" for item in included):
        raise RuntimeError("凭据排除失败")
    print(f"Created archive: {destination}; {len(included)} files; .env excluded")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    package(parser.parse_args().output)
