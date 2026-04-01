#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import sys


def _load_context_builder():
    module_path = Path("backend/app/modules/axe_fusion/context_management.py")
    spec = importlib.util.spec_from_file_location("axe_context_management", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load context_management module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.build_context_envelope


build_context_envelope = _load_context_builder()


def _long_session_profile() -> dict:
    messages = [{"role": "system", "content": "governance: tenant boundary strict"}]
    for idx in range(120):
        role = "user" if idx % 2 == 0 else "assistant"
        messages.append(
            {
                "role": role,
                "content": f"turn {idx}: working on mission planning, queue stability, policy overrides and budget handling",
            }
        )
    selected, telemetry = build_context_envelope(messages, max_prompt_tokens=8192)
    return {
        "name": "long_session_120_turns",
        "input_messages": len(messages),
        "selected_messages": len(selected),
        "telemetry": telemetry.to_dict(),
    }


def _attachment_heavy_profile() -> dict:
    messages = [{"role": "system", "content": "governance: attachment validation required"}]
    for idx in range(40):
        role = "user" if idx % 2 == 0 else "assistant"
        payload = "attached file reference artifact" if role == "user" else "processing attachment"
        messages.append({"role": role, "content": f"{payload} #{idx} with metadata and summaries"})
    selected, telemetry = build_context_envelope(messages, max_prompt_tokens=4096)
    return {
        "name": "attachment_heavy_40_turns",
        "input_messages": len(messages),
        "selected_messages": len(selected),
        "telemetry": telemetry.to_dict(),
    }


def _mixed_worker_profile() -> dict:
    messages = [{"role": "system", "content": "governance: worker routing with approvals"}]
    worker_tags = ["miniworker", "opencode", "openclaw"]
    for idx in range(60):
        role = "user" if idx % 2 == 0 else "assistant"
        worker = worker_tags[idx % len(worker_tags)]
        messages.append(
            {
                "role": role,
                "content": f"{worker} task execution trace turn={idx} with queue lease and runtime decision context",
            }
        )
    selected, telemetry = build_context_envelope(messages, max_prompt_tokens=6144)
    return {
        "name": "mixed_workers_60_turns",
        "input_messages": len(messages),
        "selected_messages": len(selected),
        "telemetry": telemetry.to_dict(),
    }


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    report_dir = Path("docs/roadmap/local_ci")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"context_soak_report_{ts}.json"

    profiles = [
        _long_session_profile(),
        _attachment_heavy_profile(),
        _mixed_worker_profile(),
    ]
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profiles": profiles,
    }
    report_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(str(report_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
