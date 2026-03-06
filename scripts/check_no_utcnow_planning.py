#!/usr/bin/env python3
"""Guard: prevent datetime.utcnow() usage in planning module."""

from __future__ import annotations

import sys
from pathlib import Path


FILES = [
    Path("/home/oli/dev/brain-v2/backend/app/modules/planning/schemas.py"),
    Path("/home/oli/dev/brain-v2/backend/app/modules/planning/service.py"),
    Path("/home/oli/dev/brain-v2/backend/app/modules/planning/failure_recovery.py"),
]


def main() -> int:
    violations: list[str] = []
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        if "datetime.utcnow(" in text:
            violations.append(str(path))

    if violations:
        print("datetime.utcnow() found in planning module files:")
        print("\n".join(violations))
        return 1

    print("No datetime.utcnow() usage in planning module files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
