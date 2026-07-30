#!/usr/bin/env python3
"""Run the verifier controlling current Forge 2 source."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(
        ROOT / "src"
    )
    environment[
        "PYTHONDONTWRITEBYTECODE"
    ] = "1"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/"
            "verify_phase1_build_006a.py",
            "--mode",
            "committed",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    print(result.stdout, end="")
    print(
        result.stderr,
        end="",
        file=sys.stderr,
    )

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
