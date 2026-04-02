from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.auth_deps import Principal, PrincipalType
from app.modules.runtime_control.schemas import (
    RegistryVersionStatus,
    RuntimeRegistryVersionItem,
    RuntimeRegistryVersionListResponse,
    RuntimeRegistryVersionPromoteRequest,
)
from app.modules.runtime_control.service import RuntimeControlResolverService


def _principal() -> Principal:
    return Principal(
        principal_id="admin-1",
        principal_type=PrincipalType.HUMAN,
        email="admin@example.com",
        name="Admin",
        roles=["admin"],
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


@pytest.mark.asyncio
async def test_promote_registry_version_supersedes_existing_promoted(monkeypatch: pytest.MonkeyPatch) -> None:
    service = RuntimeControlResolverService()
    calls: list[str] = []

    first_listing = RuntimeRegistryVersionListResponse(
        items=[
            RuntimeRegistryVersionItem(
                version_id="rcv_old",
                scope="tenant",
                tenant_id="tenant-a",
                status=RegistryVersionStatus.PROMOTED,
                config_patch={"routing": {"llm": {"default_provider": "ollama"}}},
                reason="old",
                created_by="admin-0",
                created_at="2026-04-01T10:00:00+00:00",
                updated_at="2026-04-01T10:00:00+00:00",
            ),
            RuntimeRegistryVersionItem(
                version_id="rcv_new",
                scope="tenant",
                tenant_id="tenant-a",
                status=RegistryVersionStatus.DRAFT,
                config_patch={"routing": {"llm": {"default_provider": "openrouter"}}},
                reason="new",
                created_by="admin-1",
                created_at="2026-04-01T11:00:00+00:00",
                updated_at="2026-04-01T11:00:00+00:00",
            ),
        ],
        total=2,
    )
    second_listing = RuntimeRegistryVersionListResponse(
        items=[
            RuntimeRegistryVersionItem(
                version_id="rcv_new",
                scope="tenant",
                tenant_id="tenant-a",
                status=RegistryVersionStatus.PROMOTED,
                config_patch={"routing": {"llm": {"default_provider": "openrouter"}}},
                reason="new",
                created_by="admin-1",
                created_at="2026-04-01T11:00:00+00:00",
                updated_at="2026-04-01T11:05:00+00:00",
                promoted_by="admin-1",
                promoted_at="2026-04-01T11:05:00+00:00",
                promotion_reason="promote",
            )
        ],
        total=1,
    )
    listings = iter([first_listing, second_listing])

    async def _fake_list_versions(db, *, tenant_id):  # noqa: ANN001
        _ = (db, tenant_id)
        return next(listings)

    async def _fake_record_event(**kwargs):  # noqa: ANN001
        calls.append(kwargs["event_type"])
        return SimpleNamespace()

    monkeypatch.setattr(service, "list_registry_versions", _fake_list_versions)
    import app.modules.runtime_control.service as module

    monkeypatch.setattr(module, "record_control_plane_event", _fake_record_event)

    class _FakeDB:
        async def commit(self):
            return None

    result = await service.promote_registry_version(
        _FakeDB(),
        principal=_principal(),
        version_id="rcv_new",
        payload=RuntimeRegistryVersionPromoteRequest(reason="promote"),
    )

    assert result.version_id == "rcv_new"
    assert result.status == RegistryVersionStatus.PROMOTED
    assert "runtime.registry.version.superseded.v1" in calls
    assert "runtime.registry.version.promoted.v1" in calls
