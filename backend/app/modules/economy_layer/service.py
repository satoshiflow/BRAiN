from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.discovery_layer.service import get_discovery_layer_service
from app.modules.evolution_control.service import get_evolution_control_service

from .models import EconomyAssessmentModel


def _evidence_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


class EconomyLayerService:
    async def get_assessment_by_id(
        self, db: AsyncSession, assessment_id, tenant_id: str
    ) -> EconomyAssessmentModel | None:
        query = select(EconomyAssessmentModel).where(
            EconomyAssessmentModel.id == assessment_id,
            EconomyAssessmentModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_assessment_by_proposal_id(
        self, db: AsyncSession, proposal_id, tenant_id: str
    ) -> EconomyAssessmentModel | None:
        query = select(EconomyAssessmentModel).where(
            EconomyAssessmentModel.discovery_proposal_id == proposal_id,
            EconomyAssessmentModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def analyze_proposal(
        self, db: AsyncSession, proposal_id, principal: Principal
    ) -> tuple[EconomyAssessmentModel, Any]:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")

        proposal = await get_discovery_layer_service().get_proposal_by_id(
            db, proposal_id, principal.tenant_id
        )
        if proposal is None:
            raise ValueError("Skill proposal not found")

        existing = await self.get_assessment_by_proposal_id(
            db, proposal_id, principal.tenant_id
        )
        if existing is not None:
            return existing, proposal

        evidence = _evidence_dict(getattr(proposal, "proposal_evidence", {}))
        observer_count = int(evidence.get("observer_signal_count", 0) or 0)
        knowledge_count = int(evidence.get("knowledge_item_count", 0) or 0)
        discovery_evidence_score = float(
            getattr(proposal, "evidence_score", 0.0) or 0.0
        )
        discovery_priority = float(getattr(proposal, "priority_score", 0.0) or 0.0)

        confidence_score = _clamp_score(discovery_evidence_score)
        frequency_score = _clamp_score((observer_count + knowledge_count) / 10)
        impact_score = _clamp_score(
            (discovery_priority * 0.6) + (confidence_score * 0.4)
        )
        cost_score = _clamp_score(max(0.0, 1.0 - (confidence_score * 0.7)))
        weighted_score = _clamp_score(
            (confidence_score * 0.35)
            + (frequency_score * 0.25)
            + (impact_score * 0.3)
            + ((1.0 - cost_score) * 0.1)
        )

        assessment = EconomyAssessmentModel(
            tenant_id=principal.tenant_id,
            discovery_proposal_id=proposal.id,
            skill_run_id=proposal.skill_run_id,
            status="draft",
            confidence_score=confidence_score,
            frequency_score=frequency_score,
            impact_score=impact_score,
            cost_score=cost_score,
            weighted_score=weighted_score,
            score_breakdown={
                "dimensions": {
                    "confidence": confidence_score,
                    "frequency": frequency_score,
                    "impact": impact_score,
                    "cost": cost_score,
                },
                "weights": {
                    "confidence": 0.35,
                    "frequency": 0.25,
                    "impact": 0.3,
                    "cost_inverse": 0.1,
                },
            },
            updated_at=datetime.now(timezone.utc),
        )
        db.add(assessment)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            existing = await self.get_assessment_by_proposal_id(
                db, proposal_id, principal.tenant_id
            )
            if existing is None:
                raise
            return existing, proposal

        proposal_evidence = dict(evidence)
        proposal_evidence["economy_assessment_id"] = str(assessment.id)
        proposal_evidence["economy_weighted_score"] = weighted_score
        setattr(proposal, "proposal_evidence", proposal_evidence)
        setattr(
            proposal,
            "priority_score",
            _clamp_score((discovery_priority * 0.7) + (weighted_score * 0.3)),
        )
        setattr(proposal, "updated_at", datetime.now(timezone.utc))

        evolution_proposal = await get_evolution_control_service().get_by_pattern_id(
            db,
            proposal.pattern_id,
            principal.tenant_id,
        )
        if evolution_proposal is not None:
            metadata = _evidence_dict(
                getattr(evolution_proposal, "proposal_metadata", {})
            )
            metadata["economy_weighted_score"] = weighted_score
            metadata["economy_assessment_id"] = str(assessment.id)
            setattr(evolution_proposal, "proposal_metadata", metadata)
            setattr(evolution_proposal, "updated_at", datetime.now(timezone.utc))

        await db.commit()
        await db.refresh(assessment)
        await db.refresh(proposal)
        return assessment, proposal

    async def queue_for_review(
        self, db: AsyncSession, assessment_id, principal: Principal
    ) -> EconomyAssessmentModel:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")

        assessment = await self.get_assessment_by_id(
            db, assessment_id, principal.tenant_id
        )
        if assessment is None:
            raise ValueError("Economy assessment not found")

        setattr(assessment, "status", "review_queued")
        setattr(assessment, "updated_at", datetime.now(timezone.utc))
        await db.commit()
        await db.refresh(assessment)
        return assessment


_economy_layer_service: EconomyLayerService | None = None


def get_economy_layer_service() -> EconomyLayerService:
    global _economy_layer_service
    if _economy_layer_service is None:
        _economy_layer_service = EconomyLayerService()
    return _economy_layer_service
