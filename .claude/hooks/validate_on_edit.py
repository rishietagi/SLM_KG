"""PostToolUse hook: run `make validate` after an edit under ontology/ or reference/.

Reads the hook JSON on stdin. Exit 2 (stderr fed back to Claude) when validation fails.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WATCHED = ("ontology", "reference")
MAKE_FALLBACK = Path(sys.executable).parent / "Library" / "bin" / "make.exe"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    path = (payload.get("tool_input") or {}).get("file_path") or ""
    try:
        rel = Path(path).resolve().relative_to(ROOT)
    except ValueError:
        return 0
    if not rel.parts or rel.parts[0] not in WATCHED:
        return 0

    make = shutil.which("make") or (str(MAKE_FALLBACK) if MAKE_FALLBACK.exists() else None)
    cmd = [make, "validate", f"PYTHON={Path(sys.executable).as_posix()}"] if make else \
          [sys.executable, "-m", "pipeline.cli", "validate"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if proc.returncode != 0:
        hint = "\n(ontology edited: run `make gen` first)" if rel.parts[0] == "ontology" else ""
        sys.stderr.write(f"make validate failed after editing {rel.as_posix()}:\n{proc.stdout[-4000:]}{proc.stderr[-2000:]}{hint}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
