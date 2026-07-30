"""Minimal independent Forge 2.0 establishment entry point."""

from __future__ import annotations

import json

from .establishment import establishment_status


def main() -> int:
    print(
        json.dumps(
            establishment_status().to_dict(),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
