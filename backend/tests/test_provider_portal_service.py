from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import httpx

from app.core.auth_deps import Principal, PrincipalType
from app.modules.provider_portal.schemas import HealthStatus, ProviderCredentialSetRequest
from app.modules.provider_portal.service import ProviderPortalService


def _principal(*, tenant_id: str | None = "tenant-a") -> Principal:
    return Principal(
        principal_id="provider-portal-service-test",
        principal_type=PrincipalType.HUMAN,
        email="service-test@example.com",
        name="Service Test",
        roles=["admin"],
        scopes=["read", "write"],
        tenant_id=tenant_id,
    )


class _Result:
    def __init__(self, scalar_item=None, scalar_items=None):
        self._scalar_item = scalar_item
        self._scalar_items = scalar_items or []

    def scalar_one_or_none(self):
        return self._scalar_item

    def scalars(self):
        return self

    def all(self):
        return self._scalar_items


class _FakeDB:
    def __init__(self, provider=None):
        self.provider = provider
        self.execute_count = 0
        self.added = []
        self.commit_count = 0

    async def execute(self, query):  # noqa: ANN001
        _ = query
        self.execute_count += 1
        return _Result()

    async def get(self, model, key):  # noqa: ANN001
        _ = model
        _ = key
        return self.provider

    def add(self, item):  # noqa: ANN001
        self.added.append(item)

    async def flush(self):
        return None

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, item):  # noqa: ANN001
        _ = item
        return None


def test_binding_projection_falls_back_to_first_enabled_model() -> None:
    service = ProviderPortalService()
    provider_id = uuid4()
    provider = SimpleNamespace(
        id=provider_id,
        owner_scope="tenant",
        slug="openai",
        base_url="https://api.openai.com/v1",
        is_enabled=True,
    )

    async def _fake_get_provider(db, pid, tenant_id):  # noqa: ANN001
        _ = db
        _ = tenant_id
        return provider if pid == provider_id else None

    async def _fake_list_models(db, tenant_id, provider_id=None):  # noqa: ANN001
        _ = db
        _ = tenant_id
        _ = provider_id
        return [
            SimpleNamespace(model_name="disabled-model", is_enabled=False),
            SimpleNamespace(model_name="gpt-4o-mini", is_enabled=True),
            SimpleNamespace(model_name="gpt-4.1", is_enabled=True),
        ]

    service.get_provider = _fake_get_provider  # type: ignore[method-assign]
    service.list_models = _fake_list_models  # type: ignore[method-assign]

    projection = asyncio.run(service.binding_projection(db=object(), provider_id=provider_id, model_name=None, tenant_id="tenant-a"))
    assert projection is not None
    assert projection["model_or_tool_ref"] == "gpt-4o-mini"
    assert projection["status"] == "enabled"


def test_binding_projection_handles_disabled_provider_and_no_enabled_models() -> None:
    service = ProviderPortalService()
    provider_id = uuid4()
    provider = SimpleNamespace(
        id=provider_id,
        owner_scope="tenant",
        slug="openai",
        base_url="https://api.openai.com/v1",
        is_enabled=False,
    )

    async def _fake_get_provider(db, pid, tenant_id):  # noqa: ANN001
        _ = db
        _ = tenant_id
        return provider if pid == provider_id else None

    async def _fake_list_models(db, tenant_id, provider_id=None):  # noqa: ANN001
        _ = db
        _ = tenant_id
        _ = provider_id
        return [SimpleNamespace(model_name="disabled-a", is_enabled=False)]

    service.get_provider = _fake_get_provider  # type: ignore[method-assign]
    service.list_models = _fake_list_models  # type: ignore[method-assign]

    projection = asyncio.run(service.binding_projection(db=object(), provider_id=provider_id, model_name=None, tenant_id="tenant-a"))
    assert projection is not None
    assert projection["model_or_tool_ref"] is None
    assert projection["status"] == "disabled"


def test_binding_projection_is_deterministic_for_ollama_adapter() -> None:
    service = ProviderPortalService()
    provider_id = uuid4()
    provider = SimpleNamespace(
        id=provider_id,
        owner_scope="system",
        slug="ollama",
        base_url="http://127.0.0.1:11434/v1",
        is_enabled=True,
    )

    async def _fake_get_provider(db, pid, tenant_id):  # noqa: ANN001
        _ = db
        _ = tenant_id
        return provider if pid == provider_id else None

    service.get_provider = _fake_get_provider  # type: ignore[method-assign]

    first = asyncio.run(service.binding_projection(db=object(), provider_id=provider_id, model_name="qwen2.5:0.5b", tenant_id=None))
    second = asyncio.run(service.binding_projection(db=object(), provider_id=provider_id, model_name="qwen2.5:0.5b", tenant_id=None))
    assert first == second
    assert first is not None
    assert first["adapter_key"] == "ollama_adapter"


def test_probe_timeout_maps_to_degraded(monkeypatch) -> None:
    service = ProviderPortalService()

    class _FakeTimeoutClient:
        def __init__(self, timeout):  # noqa: ANN001
            _ = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):  # noqa: ANN001
            _ = exc_type
            _ = exc
            _ = tb
            return False

        async def post(self, url, json, headers):  # noqa: ANN001
            _ = url
            _ = json
            _ = headers
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "AsyncClient", _FakeTimeoutClient)
    status_value, error_code, error_message, latency_ms, checked_at = asyncio.run(
        service._probe_provider(
            base_url="https://example.com/v1",
            model_name="gpt-4o-mini",
            timeout_seconds=1.0,
            headers={"Content-Type": "application/json"},
        )
    )
    assert status_value == HealthStatus.DEGRADED
    assert error_code == "timeout"
    assert error_message == "Probe timed out"
    assert isinstance(latency_ms, int)
    assert isinstance(checked_at, datetime)


def test_probe_transport_failure_maps_to_failed(monkeypatch) -> None:
    service = ProviderPortalService()

    class _FakeTransportClient:
        def __init__(self, timeout):  # noqa: ANN001
            _ = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):  # noqa: ANN001
            _ = exc_type
            _ = exc
            _ = tb
            return False

        async def post(self, url, json, headers):  # noqa: ANN001
            _ = url
            _ = json
            _ = headers
            raise httpx.ConnectError("network down")

    monkeypatch.setattr(httpx, "AsyncClient", _FakeTransportClient)
    status_value, error_code, error_message, latency_ms, checked_at = asyncio.run(
        service._probe_provider(
            base_url="https://example.com/v1",
            model_name="gpt-4o-mini",
            timeout_seconds=1.0,
            headers={"Content-Type": "application/json"},
        )
    )
    assert status_value == HealthStatus.FAILED
    assert error_code == "connection_error"
    assert error_message is not None
    assert isinstance(latency_ms, int)
    assert checked_at.tzinfo is not None


def test_classify_status_maps_auth_and_upstream_conditions() -> None:
    service = ProviderPortalService()
    assert service._classify_status(200) == (HealthStatus.HEALTHY, None)
    assert service._classify_status(401) == (HealthStatus.FAILED, "auth_error")
    assert service._classify_status(503) == (HealthStatus.DEGRADED, "upstream_error")
    assert service._classify_status(302) == (HealthStatus.FAILED, "invalid_response")


def test_secret_set_activate_true_deactivates_existing_credentials() -> None:
    service = ProviderPortalService()
    provider_id = uuid4()
    provider = SimpleNamespace(id=provider_id, owner_scope="tenant", tenant_id="tenant-a")
    db = _FakeDB(provider=provider)

    async def _fake_get_provider(db_obj, pid, tenant_id):  # noqa: ANN001
        _ = db_obj
        _ = tenant_id
        return provider if pid == provider_id else None

    async def _fake_record_event(*args, **kwargs):  # noqa: ANN001
        _ = args
        _ = kwargs
        return None

    service.get_provider = _fake_get_provider  # type: ignore[method-assign]
    service._record_event = _fake_record_event  # type: ignore[method-assign]

    payload = ProviderCredentialSetRequest(api_key="sk-provider-portal-test-1234", activate=True)
    credential = asyncio.run(service.set_credential(db, provider_id, payload, _principal()))
    assert credential is not None
    assert db.execute_count == 1
    assert credential.is_active is True
    assert credential.key_hint_last4 == "****1234"


def test_secret_set_activate_false_preserves_existing_active_slot() -> None:
    service = ProviderPortalService()
    provider_id = uuid4()
    provider = SimpleNamespace(id=provider_id, owner_scope="tenant", tenant_id="tenant-a")
    db = _FakeDB(provider=provider)

    async def _fake_get_provider(db_obj, pid, tenant_id):  # noqa: ANN001
        _ = db_obj
        _ = tenant_id
        return provider if pid == provider_id else None

    async def _fake_record_event(*args, **kwargs):  # noqa: ANN001
        _ = args
        _ = kwargs
        return None

    service.get_provider = _fake_get_provider  # type: ignore[method-assign]
    service._record_event = _fake_record_event  # type: ignore[method-assign]

    payload = ProviderCredentialSetRequest(api_key="sk-provider-portal-test-5678", activate=False)
    credential = asyncio.run(service.set_credential(db, provider_id, payload, _principal()))
    assert credential is not None
    assert db.execute_count == 0
    assert credential.is_active is False
    assert credential.key_hint_last4 == "****5678"


def test_secret_deactivate_is_idempotent_on_repeat() -> None:
    service = ProviderPortalService()
    provider_id = uuid4()
    provider = SimpleNamespace(id=provider_id, owner_scope="tenant", tenant_id="tenant-a")
    db = _FakeDB(provider=provider)
    credential = SimpleNamespace(
        id=uuid4(),
        provider_id=provider_id,
        is_active=True,
        updated_by="user-a",
        updated_at=datetime.now(timezone.utc),
    )

    async def _fake_get_provider(db_obj, pid, tenant_id):  # noqa: ANN001
        _ = db_obj
        _ = tenant_id
        return provider if pid == provider_id else None

    async def _fake_active_credential(db_obj, pid):  # noqa: ANN001
        _ = db_obj
        _ = pid
        return credential if credential.is_active else None

    async def _fake_record_event(*args, **kwargs):  # noqa: ANN001
        _ = args
        _ = kwargs
        return None

    service.get_provider = _fake_get_provider  # type: ignore[method-assign]
    service._active_credential = _fake_active_credential  # type: ignore[method-assign]
    service._record_event = _fake_record_event  # type: ignore[method-assign]

    first = asyncio.run(service.deactivate_credential(db, provider_id, _principal()))
    second = asyncio.run(service.deactivate_credential(db, provider_id, _principal()))
    assert first is not None
    assert first.is_active is False
    assert second is None


def test_get_provider_rejects_cross_tenant_access() -> None:
    provider = SimpleNamespace(id=uuid4(), owner_scope="tenant", tenant_id="tenant-b")
    db = _FakeDB(provider=provider)
    service = ProviderPortalService()

    resolved = asyncio.run(service.get_provider(db, provider.id, tenant_id="tenant-a"))
    assert resolved is None


def test_health_status_unknown_remains_valid_control_plane_state() -> None:
    assert HealthStatus.UNKNOWN.value == "unknown"
