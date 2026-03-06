#!/usr/bin/env python3
"""Guard: prevent datetime.utcnow() usage in auth-critical paths."""

from __future__ import annotations

import sys
from pathlib import Path


FILES = [
    Path("/home/oli/dev/brain-v2/backend/app/core/jwt_middleware.py"),
    Path("/home/oli/dev/brain-v2/backend/app/services/auth_service.py"),
    Path("/home/oli/dev/brain-v2/backend/app/models/token.py"),
    Path("/home/oli/dev/brain-v2/backend/app/api/routes/auth.py"),
    Path("/home/oli/dev/brain-v2/backend/tests/test_auth_flow.py"),
]


def main() -> int:
    violations: list[str] = []
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        if "datetime.utcnow(" in text:
            violations.append(str(path))

    if violations:
        print("datetime.utcnow() found in auth-critical files:")
        print("\n".join(violations))
        return 1

    print("No datetime.utcnow() usage in auth-critical files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
