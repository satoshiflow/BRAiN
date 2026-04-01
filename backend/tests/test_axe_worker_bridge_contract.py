from __future__ import annotations

import re
import importlib


axe_fusion_router_module = importlib.import_module("app.modules.axe_fusion.router")


def test_worker_command_pattern_includes_paperclip() -> None:
    match = re.match(axe_fusion_router_module.WORKER_COMMAND_PATTERN, "/paperclip run growth workflow", re.IGNORECASE)
    assert match is not None
    assert match.group(1).lower() == "paperclip"


def test_worker_command_pattern_keeps_openclaw() -> None:
    match = re.match(axe_fusion_router_module.WORKER_COMMAND_PATTERN, "/openclaw patch this", re.IGNORECASE)
    assert match is not None
    assert match.group(1).lower() == "openclaw"
