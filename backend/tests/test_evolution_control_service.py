from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.auth_deps import Principal, PrincipalType
from app.modules.evolution_control.service import EvolutionControlService


class FakeDb:
    async def commit(self) -> None:
        return None

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
async def test_transition_status_rejects_invalid_transition() -> None:
    service = EvolutionControlService()
    proposal = SimpleNamespace(status="draft", tenant_id="tenant-a")

    async def _get_by_id(db, proposal_id, tenant_id):
        return proposal

    service.get_by_id = _get_by_id  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="Invalid proposal transition"):
        await service.transition_status(db=None, proposal_id=uuid4(), principal=_principal(), new_status="applied")


@pytest.mark.asyncio
async def test_transition_to_applied_requires_governance_and_validation() -> None:
    service = EvolutionControlService()
    proposal = SimpleNamespace(
        status="approved",
        tenant_id="tenant-a",
        governance_required="true",
        validation_state="required",
        proposal_metadata={},
        updated_at=None,
    )

    async def _get_by_id(db, proposal_id, tenant_id):
        return proposal

    service.get_by_id = _get_by_id  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="Governance evidence required before apply"):
        await service.transition_status(db=None, proposal_id=uuid4(), principal=_principal(), new_status="applied")


@pytest.mark.asyncio
async def test_transition_to_applied_records_transition_when_valid() -> None:
    service = EvolutionControlService()
    proposal = SimpleNamespace(
        status="approved",
        tenant_id="tenant-a",
        governance_required="true",
        validation_state="validated",
        proposal_metadata={
            "approval_id": "app-1",
            "policy_decision_id": "pol-1",
            "reviewer_id": "admin-1",
        },
        updated_at=None,
    )

    async def _get_by_id(db, proposal_id, tenant_id):
        return proposal

    service.get_by_id = _get_by_id  # type: ignore[method-assign]
    updated = await service.transition_status(db=FakeDb(), proposal_id=uuid4(), principal=_principal(), new_status="applied")

    assert updated.status == "applied"
    assert len(updated.proposal_metadata.get("transitions", [])) == 1
