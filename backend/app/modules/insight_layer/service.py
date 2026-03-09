from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.experience_layer.service import get_experience_layer_service

from .models import InsightCandidateModel


class InsightLayerService:
    async def get_by_id(self, db: AsyncSession, insight_id, tenant_id: str) -> InsightCandidateModel | None:
        query = select(InsightCandidateModel).where(
            InsightCandidateModel.id == insight_id,
            InsightCandidateModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_by_skill_run_id(self, db: AsyncSession, skill_run_id, tenant_id: str) -> InsightCandidateModel | None:
        query = select(InsightCandidateModel).where(
            InsightCandidateModel.skill_run_id == skill_run_id,
            InsightCandidateModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.order_by(InsightCandidateModel.created_at.desc()).limit(1))
        return result.scalar_one_or_none()

    async def derive_from_skill_run(self, db: AsyncSession, skill_run_id, principal: Principal) -> InsightCandidateModel:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")

        existing = await self.get_by_skill_run_id(db, skill_run_id, principal.tenant_id)
        if existing is not None:
            return existing

        experience = await get_experience_layer_service().ingest_skill_run(db, skill_run_id, principal)

        confidence = 0.8 if experience.state == "succeeded" else 0.35
        if experience.failure_code:
            confidence = min(confidence, 0.45)

        skill_key = str(experience.signals.get("skill_key", "unknown"))
        hypothesis = (
            f"Run pattern for {skill_key}: state={experience.state}, "
            f"failure={experience.failure_code or 'none'}"
        )

        insight = InsightCandidateModel(
            tenant_id=principal.tenant_id,
            experience_id=experience.id,
            skill_run_id=experience.skill_run_id,
            status="proposed",
            confidence=confidence,
            scope="skill_run",
            hypothesis=hypothesis,
            evidence={
                "experience_id": str(experience.id),
                "experience_state": experience.state,
                "failure_code": experience.failure_code,
                "evaluation_summary": experience.evaluation_summary,
                "signals": experience.signals,
            },
            updated_at=datetime.now(timezone.utc),
        )
        db.add(insight)
        await db.commit()
        await db.refresh(insight)
        return insight


_insight_layer_service: InsightLayerService | None = None


def get_insight_layer_service() -> InsightLayerService:
    global _insight_layer_service
    if _insight_layer_service is None:
        _insight_layer_service = InsightLayerService()
    return _insight_layer_service
