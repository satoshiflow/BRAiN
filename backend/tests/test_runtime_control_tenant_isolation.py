from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.runtime_control.service import RuntimeControlResolverService


class _Result:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items


class _FakeDB:
    def __init__(self, events):
        self._events = events

    async def execute(self, _query):  # noqa: ANN001
        return _Result(self._events)


def _event(*, entity_type: str, event_type: str, payload: dict, tenant_id: str | None = None):
    return SimpleNamespace(
        id=uuid4(),
        entity_type=entity_type,
        entity_id=str(payload.get("request_id") or payload.get("version_id") or uuid4()),
        event_type=event_type,
        tenant_id=tenant_id,
        actor_id="tester",
        actor_type="human",
        correlation_id=payload.get("request_id") or payload.get("version_id"),
        payload=payload,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_override_request_listing_is_tenant_scoped() -> None:
    service = RuntimeControlResolverService()
    events = [
        _event(
            entity_type="runtime_override_request",
            event_type="runtime.override.request.created.v1",
            payload={
                "request_id": "rov_a",
                "tenant_scope": "tenant",
                "tenant_id": "tenant-a",
                "key": "workers.selection.default_executor",
                "value": "openclaw",
                "reason": "a",
                "created_by": "u-a",
            },
            tenant_id="tenant-a",
        ),
        _event(
            entity_type="runtime_override_request",
            event_type="runtime.override.request.created.v1",
            payload={
                "request_id": "rov_b",
                "tenant_scope": "tenant",
                "tenant_id": "tenant-b",
                "key": "workers.selection.default_executor",
                "value": "miniworker",
                "reason": "b",
                "created_by": "u-b",
            },
            tenant_id="tenant-b",
        ),
    ]

    response = await service.list_override_requests(_FakeDB(events), tenant_id="tenant-a")
    assert response.total == 1
    assert response.items[0].request_id == "rov_a"


@pytest.mark.asyncio
async def test_active_overrides_exclude_expired_items() -> None:
    service = RuntimeControlResolverService()
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    events = [
        _event(
            entity_type="runtime_override_request",
            event_type="runtime.override.request.created.v1",
            payload={
                "request_id": "rov_past",
                "tenant_scope": "tenant",
                "tenant_id": "tenant-a",
                "key": "routing.llm.default_provider",
                "value": "ollama",
                "reason": "past",
                "created_by": "u",
                "expires_at": past,
            },
            tenant_id="tenant-a",
        ),
        _event(
            entity_type="runtime_override_request",
            event_type="runtime.override.request.approved.v1",
            payload={
                "request_id": "rov_past",
                "tenant_scope": "tenant",
                "tenant_id": "tenant-a",
                "key": "routing.llm.default_provider",
                "value": "ollama",
                "reason": "past",
                "approved_by": "admin",
                "decision_reason": "ok",
                "expires_at": past,
            },
            tenant_id="tenant-a",
        ),
        _event(
            entity_type="runtime_override_request",
            event_type="runtime.override.request.created.v1",
            payload={
                "request_id": "rov_future",
                "tenant_scope": "tenant",
                "tenant_id": "tenant-a",
                "key": "workers.selection.default_executor",
                "value": "openclaw",
                "reason": "future",
                "created_by": "u",
                "expires_at": future,
            },
            tenant_id="tenant-a",
        ),
        _event(
            entity_type="runtime_override_request",
            event_type="runtime.override.request.approved.v1",
            payload={
                "request_id": "rov_future",
                "tenant_scope": "tenant",
                "tenant_id": "tenant-a",
                "key": "workers.selection.default_executor",
                "value": "openclaw",
                "reason": "future",
                "approved_by": "admin",
                "decision_reason": "ok",
                "expires_at": future,
            },
            tenant_id="tenant-a",
        ),
    ]
    active = await service.list_active_overrides(_FakeDB(events), tenant_id="tenant-a")
    assert active.total == 1
    assert active.items[0].request_id == "rov_future"


@pytest.mark.asyncio
async def test_registry_versions_are_tenant_scoped() -> None:
    service = RuntimeControlResolverService()
    events = [
        _event(
            entity_type="runtime_registry_version",
            event_type="runtime.registry.version.created.v1",
            payload={
                "version_id": "rcv_a",
                "scope": "tenant",
                "tenant_id": "tenant-a",
                "config_patch": {"routing": {"llm": {"default_provider": "ollama"}}},
                "reason": "a",
                "created_by": "u-a",
            },
            tenant_id="tenant-a",
        ),
        _event(
            entity_type="runtime_registry_version",
            event_type="runtime.registry.version.created.v1",
            payload={
                "version_id": "rcv_b",
                "scope": "tenant",
                "tenant_id": "tenant-b",
                "config_patch": {"routing": {"llm": {"default_provider": "openrouter"}}},
                "reason": "b",
                "created_by": "u-b",
            },
            tenant_id="tenant-b",
        ),
    ]
    versions = await service.list_registry_versions(_FakeDB(events), tenant_id="tenant-a")
    assert versions.total == 1
    assert versions.items[0].version_id == "rcv_a"
