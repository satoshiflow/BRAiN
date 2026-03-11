from __future__ import annotations

import importlib
import io
import pytest

from app.modules.axe_governance import AXERequestContext, TrustTier

axe_fusion_router_module = importlib.import_module("app.modules.axe_fusion.router")


def _dmz_context(source_ip: str = "10.0.0.5") -> AXERequestContext:
    return AXERequestContext(
        trust_tier=TrustTier.DMZ,
        source_service="telegram_gateway",
        source_ip=source_ip,
        authenticated=True,
        request_id="req-test",
        user_agent="pytest",
        rate_limit_key="dmz:telegram_gateway",
    )


class _AllowDmzValidator:
    async def validate_request(self, headers, client_host, request_id):  # noqa: ANN001
        return _dmz_context(source_ip=client_host or "10.0.0.5")

    def is_request_allowed(self, _context):  # noqa: ANN001
        return True


class _DenyExternalValidator:
    async def validate_request(self, headers, client_host, request_id):  # noqa: ANN001
        return AXERequestContext(
            trust_tier=TrustTier.EXTERNAL,
            source_service="unknown",
            source_ip=client_host,
            authenticated=False,
            request_id=request_id,
            user_agent=headers.get("user-agent"),
            rate_limit_key=f"external:{client_host}",
        )

    def is_request_allowed(self, _context):  # noqa: ANN001
        return False


class _FusionServiceStub:
    async def chat(self, model, messages, temperature=0.7, **kwargs):  # noqa: ANN001
        return {
            "text": "stubbed response",
            "raw": {
                "model": model,
                "temperature": temperature,
                "messages": messages,
            },
        }

    async def health_check(self):
        return {
            "status": "healthy",
            "axellm": "reachable",
        }

    def set_provider_runtime(self, provider, force_sanitization_level=None):  # noqa: ANN001
        level = force_sanitization_level.value if force_sanitization_level else "none"
        return {
            "active": {
                "provider": provider.value,
                "base_url": "http://example.local",
                "api_key_configured": False,
                "model": "mock-local",
                "timeout_seconds": 60.0,
            },
            "sanitization_level": level,
        }

    async def get_deanonymization_outcomes(self, **kwargs):  # noqa: ANN001
        return [
            {
                "request_id": "req-1",
                "provider": "groq",
                "provider_model": "llama-3.2-90b-vision-preview",
                "status": "success",
                "reason_code": None,
                "placeholder_count": 2,
                "restored_count": 2,
                "unresolved_placeholders": [],
                "created_at": "2026-03-11T10:00:00Z",
            }
        ]

    async def get_learning_candidates(self, **kwargs):  # noqa: ANN001
        return [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "provider": "groq",
                "pattern_name": "path",
                "sample_size": 1000,
                "failure_rate": 0.05,
                "confidence_score": 0.93,
                "risk_score": 0.1,
                "proposed_change": {"action": "tighten_regex"},
                "gate_state": "pending_auto_gate",
                "approved_by": None,
                "approved_at": None,
                "created_at": "2026-03-11T10:00:00Z",
            }
        ]

    async def update_learning_candidate_state(self, **kwargs):  # noqa: ANN001
        return True

    async def run_retention_cleanup(self):
        return {
            "deleted_mapping_sets": 3,
            "deleted_attempts": 5,
            "deleted_candidates": 1,
        }

    async def generate_learning_candidates(self, **kwargs):  # noqa: ANN001
        return {"created_candidates": 2}


def test_axe_fusion_chat_route_allows_dmz(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_fusion_service", lambda db=None: _FusionServiceStub())

    response = client.post(
        "/api/axe/chat",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 0.2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "stubbed response"
    assert "raw" in body
    assert "x-axe-request-id" in response.headers


def test_axe_fusion_chat_route_denies_external(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _DenyExternalValidator())

    response = client.post(
        "/api/axe/chat",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error"] == "Forbidden"


def test_axe_fusion_health_route_allows_dmz(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_fusion_service", lambda db=None: _FusionServiceStub())

    response = client.get("/api/axe/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["axellm"] == "reachable"


def test_axe_fusion_route_returns_503_when_governance_unconfigured(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("AXE_FUSION_ALLOW_LOCAL_REQUESTS", raising=False)
    monkeypatch.delenv("AXE_FUSION_ALLOW_LOCAL_FALLBACK", raising=False)
    monkeypatch.setattr(
        axe_fusion_router_module,
        "get_axe_trust_validator",
        lambda: (_ for _ in ()).throw(ValueError("missing secret")),
    )

    response = client.post(
        "/api/axe/chat",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "AXE_GOVERNANCE_UNAVAILABLE"


def test_axe_fusion_upload_accepts_supported_file(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())

    response = client.post(
        "/api/axe/upload",
        files={"file": ("note.txt", io.BytesIO(b"hello axe"), "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["attachment_id"].startswith("att_")
    assert body["mime_type"] == "text/plain"


def test_axe_fusion_upload_rejects_unsupported_mime(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())

    response = client.post(
        "/api/axe/upload",
        files={"file": ("payload.exe", io.BytesIO(b"MZ..."), "application/octet-stream")},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "UNSUPPORTED_ATTACHMENT_TYPE"


def test_axe_provider_runtime_read(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())
    monkeypatch.setenv("LOCAL_LLM_MODE", "mock")

    response = client.get("/api/axe/provider/runtime")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock"
    assert payload["sanitization_level"] == "none"


def test_axe_provider_runtime_update(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())
    monkeypatch.setenv("LOCAL_LLM_MODE", "mock")

    response = client.put(
        "/api/axe/provider/runtime",
        json={"provider": "groq", "force_sanitization_level": "moderate"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "groq"
    assert payload["sanitization_level"] == "moderate"


def test_axe_admin_outcomes_endpoint(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_fusion_service", lambda db=None: _FusionServiceStub())

    response = client.get("/api/axe/admin/deanonymization/outcomes")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["status"] == "success"


def test_axe_admin_insights_endpoint(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_fusion_service", lambda db=None: _FusionServiceStub())

    response = client.get("/api/axe/admin/sanitization/insights")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["provider"] == "groq"


def test_axe_admin_retention_run_endpoint(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_fusion_service", lambda db=None: _FusionServiceStub())

    response = client.post("/api/axe/admin/retention/run")

    assert response.status_code == 200
    payload = response.json()
    assert payload["deleted_mapping_sets"] == 3


def test_axe_admin_insight_approve_endpoint(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_fusion_service", lambda db=None: _FusionServiceStub())

    response = client.post("/api/axe/admin/sanitization/insights/11111111-1111-1111-1111-111111111111/approve")

    assert response.status_code == 200
    payload = response.json()
    assert payload["gate_state"] == "approved"


def test_axe_admin_insight_reject_endpoint(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_fusion_service", lambda db=None: _FusionServiceStub())

    response = client.post("/api/axe/admin/sanitization/insights/11111111-1111-1111-1111-111111111111/reject")

    assert response.status_code == 200
    payload = response.json()
    assert payload["gate_state"] == "rejected"


def test_axe_admin_generate_insights_endpoint(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_fusion_service", lambda db=None: _FusionServiceStub())

    response = client.post("/api/axe/admin/sanitization/insights/generate?window_days=7&min_sample_size=50")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created_candidates"] == 2


def test_axe_admin_actions_emit_audit(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: _AllowDmzValidator())
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_fusion_service", lambda db=None: _FusionServiceStub())

    calls = []

    async def _fake_audit(**kwargs):  # noqa: ANN003
        calls.append(kwargs)

    monkeypatch.setattr(axe_fusion_router_module, "write_unified_audit", _fake_audit)

    response = client.put(
        "/api/axe/provider/runtime",
        json={"provider": "groq", "force_sanitization_level": "moderate"},
        headers={"x-request-id": "req-audit-1"},
    )

    assert response.status_code == 200
    assert calls
    assert calls[0]["event_type"] == "axe.admin"
    assert calls[0]["action"] == "provider_runtime_update"
