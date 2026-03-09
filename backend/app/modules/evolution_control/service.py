from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.consolidation_layer.service import get_consolidation_layer_service

from .models import EvolutionProposalModel


_ALLOWED_STATUSES = {"draft", "review", "approved", "rejected", "applied", "rolled_back"}
_ALLOWED_TRANSITIONS = {
    "draft": {"review", "rejected"},
    "review": {"approved", "rejected"},
    "approved": {"applied", "rolled_back"},
    "rejected": set(),
    "applied": {"rolled_back"},
    "rolled_back": set(),
}


class EvolutionControlService:
    async def get_by_id(self, db: AsyncSession, proposal_id, tenant_id: str) -> EvolutionProposalModel | None:
        query = select(EvolutionProposalModel).where(
            EvolutionProposalModel.id == proposal_id,
            EvolutionProposalModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_by_pattern_id(self, db: AsyncSession, pattern_id, tenant_id: str) -> EvolutionProposalModel | None:
        query = select(EvolutionProposalModel).where(
            EvolutionProposalModel.pattern_id == pattern_id,
            EvolutionProposalModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.order_by(EvolutionProposalModel.created_at.desc()).limit(1))
        return result.scalar_one_or_none()

    async def create_from_pattern(self, db: AsyncSession, pattern_id, principal: Principal) -> EvolutionProposalModel:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")

        existing = await self.get_by_pattern_id(db, pattern_id, principal.tenant_id)
        if existing is not None:
            return existing

        pattern = await get_consolidation_layer_service().get_by_id(db, pattern_id, principal.tenant_id)
        if pattern is None:
            raise ValueError("Pattern candidate not found")

        insight_evidence = pattern.evidence.get("insight_evidence", {})
        signals = insight_evidence.get("signals", {}) if isinstance(insight_evidence, dict) else {}
        skill_key = str(signals.get("skill_key", "unknown"))

        proposal = EvolutionProposalModel(
            tenant_id=principal.tenant_id,
            pattern_id=pattern.id,
            skill_run_id=pattern.skill_run_id,
            status="draft",
            target_skill_key=skill_key,
            summary=f"Evolution proposal from pattern {pattern.id} for {skill_key}",
            governance_required="true",
            validation_state="required",
            proposal_metadata={
                "pattern_confidence": pattern.confidence,
                "pattern_recurrence_support": pattern.recurrence_support,
                "failure_modes": pattern.failure_modes,
            },
            updated_at=datetime.now(timezone.utc),
        )
        db.add(proposal)
        await db.commit()
        await db.refresh(proposal)
        return proposal

    async def transition_status(self, db: AsyncSession, proposal_id, principal: Principal, new_status: str) -> EvolutionProposalModel:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")
        if new_status not in _ALLOWED_STATUSES:
            raise ValueError("Invalid proposal status")

        proposal = await self.get_by_id(db, proposal_id, principal.tenant_id)
        if proposal is None:
            raise ValueError("Evolution proposal not found")

        if new_status not in _ALLOWED_TRANSITIONS.get(proposal.status, set()):
            raise ValueError("Invalid proposal transition")

        metadata = dict(proposal.proposal_metadata or {})
        if new_status == "applied":
            if proposal.governance_required == "true":
                required_refs = {"approval_id", "policy_decision_id", "reviewer_id"}
                if not required_refs.issubset(set(metadata.keys())):
                    raise ValueError("Governance evidence required before apply")
            if proposal.validation_state != "validated":
                raise ValueError("Validation state must be 'validated' before apply")

        transitions = list(metadata.get("transitions", []))
        transitions.append(
            {
                "from": proposal.status,
                "to": new_status,
                "actor": principal.principal_id,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        metadata["transitions"] = transitions

        proposal.status = new_status
        proposal.proposal_metadata = metadata
        proposal.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(proposal)
        return proposal


_evolution_control_service: EvolutionControlService | None = None


def get_evolution_control_service() -> EvolutionControlService:
    global _evolution_control_service
    if _evolution_control_service is None:
        _evolution_control_service = EvolutionControlService()
    return _evolution_control_service
