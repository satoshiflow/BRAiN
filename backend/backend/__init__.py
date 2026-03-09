"""Compatibility package for tests importing `backend.*` from `backend/`.

Some legacy tests add the `backend/` directory itself to `sys.path` and then
import `backend.main`. This shim redirects that import shape to the real
top-level modules.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path


_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

if str(_PARENT) not in __path__:
    __path__.append(str(_PARENT))


def _alias_namespace(alias: str, relative_path: str) -> None:
    if alias in sys.modules:
        return
    module = types.ModuleType(alias)
    module.__path__ = [str(_PARENT / relative_path)]
    sys.modules[alias] = module


_alias_namespace("app", "app")
_alias_namespace("api", "api")
_alias_namespace("modules", "modules")
_alias_namespace("brain", "brain")
