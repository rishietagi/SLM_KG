"""Entry point behind every Makefile target: python -m pipeline.cli <gen|validate|load|report|clean>."""
from __future__ import annotations

import shutil
import sys

from codegen.loader import ROOT


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "gen":
        from codegen.generate import run

        run()
        return 0
    if cmd == "validate":
        from validate.run import run

        return run()
    if cmd == "load":
        from pipeline.load import run

        run()
        return 0
    if cmd == "report":
        from pipeline.report import run

        return run()
    if cmd == "clean":
        for d in ("build", "db"):
            shutil.rmtree(ROOT / d, ignore_errors=True)
        return 0
    print(f"unknown command {cmd!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
