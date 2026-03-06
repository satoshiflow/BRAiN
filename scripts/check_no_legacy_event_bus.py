#!/usr/bin/env python3
"""Guard: prevent reintroduction of legacy app.core.event_bus imports.

Scope: backend/app/**/*.py
Policy: runtime app code must not import app.core.event_bus directly or via
`from app.core import event_bus`.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path("/home/oli/dev/brain-v2/backend/app")


def has_legacy_event_bus_import(text: str) -> bool:
    """Return True when source imports legacy app.core.event_bus."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.core.event_bus":
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == "app.core.event_bus":
                return True
            if node.module == "app.core":
                for alias in node.names:
                    if alias.name == "event_bus":
                        return True

    return False


def main() -> int:
    violations: list[str] = []
    for path in ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if has_legacy_event_bus_import(text):
            violations.append(str(path))

    if violations:
        print("Legacy EventBus imports found:")
        print("\n".join(violations))
        return 1

    print("No legacy EventBus imports under backend/app.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
