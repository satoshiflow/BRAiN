from __future__ import annotations

import importlib
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
    async def chat(self, model, messages, temperature=0.7):  # noqa: ANN001
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
