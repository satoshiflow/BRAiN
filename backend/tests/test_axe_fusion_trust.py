from __future__ import annotations

import importlib
from starlette.requests import Request
import pytest
from fastapi import HTTPException

axe_fusion_router_module = importlib.import_module("app.modules.axe_fusion.router")

validate_axe_trust = axe_fusion_router_module.validate_axe_trust
from app.modules.axe_governance import AXERequestContext, TrustTier


def _build_request(client_host: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/axe/chat",
        "headers": [(b"user-agent", b"pytest"), (b"x-request-id", b"req-1")],
        "client": (client_host, 12345),
        "query_string": b"",
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_validate_axe_trust_allows_dmz(monkeypatch: pytest.MonkeyPatch) -> None:
    class Validator:
        async def validate_request(self, headers, client_host, request_id):  # noqa: ANN001
            return AXERequestContext(
                trust_tier=TrustTier.DMZ,
                source_service="telegram_gateway",
                source_ip=client_host,
                authenticated=True,
                request_id=request_id,
                user_agent=headers.get("user-agent"),
                rate_limit_key="dmz:telegram_gateway",
            )

        def is_request_allowed(self, _context):  # noqa: ANN001
            return True

    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: Validator())

    context = await validate_axe_trust(_build_request("10.0.0.5"), None, None)
    assert context.trust_tier == TrustTier.DMZ


@pytest.mark.asyncio
async def test_validate_axe_trust_denies_external(monkeypatch: pytest.MonkeyPatch) -> None:
    class Validator:
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

    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: Validator())

    with pytest.raises(HTTPException) as exc_info:
        await validate_axe_trust(_build_request("203.0.113.4"), None, None)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_validate_axe_trust_local_fallback_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AXE_FUSION_ALLOW_LOCAL_REQUESTS", "true")
    monkeypatch.setenv("AXE_FUSION_ALLOW_LOCAL_FALLBACK", "true")
    monkeypatch.setattr(
        axe_fusion_router_module,
        "get_axe_trust_validator",
        lambda: (_ for _ in ()).throw(ValueError("missing secret")),
    )

    context = await validate_axe_trust(_build_request("127.0.0.1"), None, None)
    assert context.trust_tier == TrustTier.LOCAL
    assert context.source_service == "localhost"


@pytest.mark.asyncio
async def test_validate_axe_trust_non_local_fails_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AXE_FUSION_ALLOW_LOCAL_REQUESTS", raising=False)
    monkeypatch.delenv("AXE_FUSION_ALLOW_LOCAL_FALLBACK", raising=False)
    monkeypatch.setattr(
        axe_fusion_router_module,
        "get_axe_trust_validator",
        lambda: (_ for _ in ()).throw(ValueError("missing secret")),
    )

    with pytest.raises(HTTPException) as exc_info:
        await validate_axe_trust(_build_request("203.0.113.4"), None, None)

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_validate_axe_trust_local_fails_without_explicit_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AXE_FUSION_ALLOW_LOCAL_REQUESTS", "true")
    monkeypatch.delenv("AXE_FUSION_ALLOW_LOCAL_FALLBACK", raising=False)
    monkeypatch.setattr(
        axe_fusion_router_module,
        "get_axe_trust_validator",
        lambda: (_ for _ in ()).throw(ValueError("missing secret")),
    )

    with pytest.raises(HTTPException) as exc_info:
        await validate_axe_trust(_build_request("127.0.0.1"), None, None)

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_validate_axe_trust_local_denied_when_not_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Validator:
        async def validate_request(self, headers, client_host, request_id):  # noqa: ANN001
            return AXERequestContext(
                trust_tier=TrustTier.LOCAL,
                source_service="localhost",
                source_ip=client_host,
                authenticated=True,
                request_id=request_id,
                user_agent=headers.get("user-agent"),
                rate_limit_key=f"local:{client_host}",
            )

        def is_request_allowed(self, _context):  # noqa: ANN001
            return True

    monkeypatch.delenv("AXE_FUSION_ALLOW_LOCAL_REQUESTS", raising=False)
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: Validator())

    with pytest.raises(HTTPException) as exc_info:
        await validate_axe_trust(_build_request("127.0.0.1"), None, None)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_validate_axe_trust_local_allowed_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Validator:
        async def validate_request(self, headers, client_host, request_id):  # noqa: ANN001
            return AXERequestContext(
                trust_tier=TrustTier.LOCAL,
                source_service="localhost",
                source_ip=client_host,
                authenticated=True,
                request_id=request_id,
                user_agent=headers.get("user-agent"),
                rate_limit_key=f"local:{client_host}",
            )

        def is_request_allowed(self, _context):  # noqa: ANN001
            return True

    monkeypatch.setenv("AXE_FUSION_ALLOW_LOCAL_REQUESTS", "true")
    monkeypatch.setattr(axe_fusion_router_module, "get_axe_trust_validator", lambda: Validator())

    context = await validate_axe_trust(_build_request("127.0.0.1"), None, None)
    assert context.trust_tier == TrustTier.LOCAL
