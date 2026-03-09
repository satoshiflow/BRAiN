"""Backend package bootstrap compatibility.

Allows legacy absolute imports like `app.*`, `api.*`, and `modules.*`
to keep working when callers import `backend.main` from the repo root.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


def _alias_package(alias: str, target: str) -> None:
    if alias in sys.modules:
        return
    sys.modules[alias] = importlib.import_module(target)


def _alias_namespace(alias: str, relative_path: str) -> None:
    if alias in sys.modules:
        return
    module = types.ModuleType(alias)
    module.__path__ = [str(Path(__file__).resolve().parent / relative_path)]
    sys.modules[alias] = module


_alias_package("app", "backend.app")
_alias_package("modules", "backend.modules")
_alias_namespace("api", "api")
_alias_namespace("brain", "brain")
