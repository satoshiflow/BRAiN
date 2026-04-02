from __future__ import annotations

import hashlib
import hmac
import importlib
import json


axe_fusion_router_module = importlib.import_module("app.modules.axe_fusion.router")


def test_build_execution_permit_signs_payload(monkeypatch) -> None:
    monkeypatch.setenv("BRAIN_EXTERNAL_EXECUTOR_PERMIT_SECRET", "permit-secret")

    permit = axe_fusion_router_module._build_execution_permit(  # noqa: SLF001
        executor_type="paperclip",
        skill_run_id="run-1",
        task_id="task-1",
        correlation_id="corr-1",
        ttl_seconds=120,
    )

    signed_payload = {
        "executor_type": permit["executor_type"],
        "skill_run_id": permit["skill_run_id"],
        "allowed_actions": permit["allowed_actions"],
        "allowed_connectors": permit["allowed_connectors"],
        "issued_at": permit["issued_at"],
        "expires_at": permit["expires_at"],
        "task_id": permit["task_id"],
        "correlation_id": permit["correlation_id"],
    }
    message = json.dumps(signed_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    expected = hmac.new(b"permit-secret", message, hashlib.sha256).hexdigest()

    assert permit["signature"] == expected
