from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.insight_layer.service import get_insight_layer_service

from .models import PatternCandidateModel


class ConsolidationLayerService:
    async def get_by_id(self, db: AsyncSession, pattern_id, tenant_id: str) -> PatternCandidateModel | None:
        query = select(PatternCandidateModel).where(
            PatternCandidateModel.id == pattern_id,
            PatternCandidateModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_by_skill_run_id(self, db: AsyncSession, skill_run_id, tenant_id: str) -> PatternCandidateModel | None:
        query = select(PatternCandidateModel).where(
            PatternCandidateModel.skill_run_id == skill_run_id,
            PatternCandidateModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.order_by(PatternCandidateModel.created_at.desc()).limit(1))
        return result.scalar_one_or_none()

    async def derive_from_skill_run(self, db: AsyncSession, skill_run_id, principal: Principal) -> PatternCandidateModel:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")

        existing = await self.get_by_skill_run_id(db, skill_run_id, principal.tenant_id)
        if existing is not None:
            return existing

        insight = await get_insight_layer_service().derive_from_skill_run(db, skill_run_id, principal)
        recurrence_support = round(max(0.1, min(1.0, insight.confidence * 0.9)), 3)
        pattern_summary = f"Pattern from insight: {insight.hypothesis}"
        failure_modes: list[str] = []
        failure_code = insight.evidence.get("failure_code")
        if failure_code:
            failure_modes.append(str(failure_code))

        pattern = PatternCandidateModel(
            tenant_id=principal.tenant_id,
            insight_id=insight.id,
            skill_run_id=insight.skill_run_id,
            status="proposed",
            confidence=insight.confidence,
            recurrence_support=recurrence_support,
            pattern_summary=pattern_summary,
            failure_modes=failure_modes,
            evidence={
                "insight_id": str(insight.id),
                "insight_status": insight.status,
                "insight_confidence": insight.confidence,
                "insight_evidence": insight.evidence,
            },
            updated_at=datetime.now(timezone.utc),
        )
        db.add(pattern)
        await db.commit()
        await db.refresh(pattern)
        return pattern


_consolidation_layer_service: ConsolidationLayerService | None = None


def get_consolidation_layer_service() -> ConsolidationLayerService:
    global _consolidation_layer_service
    if _consolidation_layer_service is None:
        _consolidation_layer_service = ConsolidationLayerService()
    return _consolidation_layer_service
