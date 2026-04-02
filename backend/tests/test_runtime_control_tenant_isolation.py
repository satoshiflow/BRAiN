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


@pytest.mark.asyncio
async def test_timeline_includes_external_handoffs_for_same_tenant() -> None:
    service = RuntimeControlResolverService()
    events = [
        _event(
            entity_type="external_handoff",
            event_type="external.handoff.paperclip.created.v1",
            payload={
                "jti": "handoff_a",
                "tenant_id": "tenant-a",
            },
            tenant_id="tenant-a",
        ),
        _event(
            entity_type="external_handoff",
            event_type="external.handoff.paperclip.created.v1",
            payload={
                "jti": "handoff_b",
                "tenant_id": "tenant-b",
            },
            tenant_id="tenant-b",
        ),
    ]

    timeline = await service.list_timeline(_FakeDB(events), tenant_id="tenant-a")

    assert timeline.total == 1
    assert timeline.items[0].entity_type == "external_handoff"
    assert timeline.items[0].tenant_id == "tenant-a"


@pytest.mark.asyncio
async def test_external_ops_observability_aggregates_pending_requests_and_failures() -> None:
    service = RuntimeControlResolverService()
    stale_time = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    events = [
        SimpleNamespace(
            id=uuid4(),
            entity_type="external_action_request",
            entity_id="actreq_1",
            event_type="external.action_request.paperclip.requested.v1",
            tenant_id="tenant-a",
            actor_id="operator-1",
            actor_type="human",
            correlation_id="corr-1",
            payload={
                "request_id": "actreq_1",
                "app_slug": "paperclip",
                "target_ref": "task-1",
                "skill_run_id": "run-1",
            },
            created_at=stale_time,
        ),
        SimpleNamespace(
            id=uuid4(),
            entity_type="external_handoff",
            entity_id="handoff_1",
            event_type="external.handoff.openclaw.exchange_failed.v1",
            tenant_id="tenant-a",
            actor_id="operator-1",
            actor_type="human",
            correlation_id="corr-2",
            payload={"app_slug": "openclaw"},
            created_at=recent_time,
        ),
        SimpleNamespace(
            id=uuid4(),
            entity_type="external_action_request",
            entity_id="actreq_2",
            event_type="external.action_request.openclaw.approved.v1",
            tenant_id="tenant-a",
            actor_id="admin-1",
            actor_type="human",
            correlation_id="corr-3",
            payload={
                "request_id": "actreq_2",
                "app_slug": "openclaw",
                "action": "request_retry",
                "execution_result": {"new_task_id": "task-2"},
            },
            created_at=recent_time,
        ),
        SimpleNamespace(
            id=uuid4(),
            entity_type="external_action_request",
            entity_id="actreq_3",
            event_type="external.action_request.paperclip.approved.v1",
            tenant_id="tenant-a",
            actor_id="admin-1",
            actor_type="human",
            correlation_id="corr-4",
            payload={
                "request_id": "actreq_3",
                "app_slug": "paperclip",
                "target_ref": "task-3",
                "execution_result": {"supervisor_escalation_id": "esc_123"},
            },
            created_at=stale_time,
        ),
    ]

    response = await service.get_external_ops_observability(_FakeDB(events), tenant_id="tenant-a")

    assert response.metrics.pending_action_requests == 1
    assert response.metrics.stale_action_requests == 1
    assert response.metrics.handoff_failures_24h == 1
    assert response.metrics.retry_approvals_24h == 1
    assert response.metrics.stale_supervisor_escalations == 1
    assert any(alert.category == "pending_action_request" for alert in response.alerts)
    assert any(alert.category == "handoff_failures" for alert in response.alerts)
