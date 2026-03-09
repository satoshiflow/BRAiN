from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.auth_deps import Principal, PrincipalType
from app.modules.discovery_layer.service import DiscoveryLayerService


class FakeDb:
    def __init__(self) -> None:
        self.rollbacks = 0

    async def execute(self, query):
        raise RuntimeError("not used in this test")

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, item) -> None:
        return None


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
async def test_queue_for_review_uses_non_committing_evolution_create(
    monkeypatch,
) -> None:
    service = DiscoveryLayerService()
    proposal = SimpleNamespace(
        id=uuid4(),
        tenant_id="tenant-a",
        pattern_id=uuid4(),
        status="draft",
        proposal_evidence={},
        updated_at=None,
    )

    async def _get_proposal(db, proposal_id, tenant_id):
        return proposal

    service.get_proposal_by_id = _get_proposal  # type: ignore[method-assign]

    called = {"commit_flag": None}

    class FakeEvolutionService:
        async def create_from_pattern(self, db, pattern_id, principal, *, commit=True):
            called["commit_flag"] = commit
            return SimpleNamespace(id=uuid4(), status="draft")

    module = __import__(
        "app.modules.discovery_layer.service",
        fromlist=["get_evolution_control_service"],
    )
    monkeypatch.setattr(
        module, "get_evolution_control_service", lambda: FakeEvolutionService()
    )

    updated, evolution_id = await service.queue_for_review(
        FakeDb(), proposal.id, _principal()
    )

    assert updated.status == "review_queued"
    assert called["commit_flag"] is False
    assert isinstance(evolution_id, str)


@pytest.mark.asyncio
async def test_queue_for_review_rejects_non_reviewable_evolution_state(
    monkeypatch,
) -> None:
    service = DiscoveryLayerService()
    proposal = SimpleNamespace(
        id=uuid4(),
        tenant_id="tenant-a",
        pattern_id=uuid4(),
        status="draft",
        proposal_evidence={},
        updated_at=None,
    )

    async def _get_proposal(db, proposal_id, tenant_id):
        return proposal

    service.get_proposal_by_id = _get_proposal  # type: ignore[method-assign]

    class FakeEvolutionService:
        async def create_from_pattern(self, db, pattern_id, principal, *, commit=True):
            return SimpleNamespace(id=uuid4(), status="applied")

    module = __import__(
        "app.modules.discovery_layer.service",
        fromlist=["get_evolution_control_service"],
    )
    monkeypatch.setattr(
        module, "get_evolution_control_service", lambda: FakeEvolutionService()
    )

    with pytest.raises(ValueError, match="not reviewable"):
        await service.queue_for_review(FakeDb(), proposal.id, _principal())
