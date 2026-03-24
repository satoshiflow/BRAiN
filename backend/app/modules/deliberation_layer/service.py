from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal

from .models import DeliberationSummaryModel, MissionTensionModel
from .schemas import DeliberationSummaryCreate, MissionTensionCreate


class DeliberationLayerService:
    async def create_summary(
        self,
        db: AsyncSession,
        mission_id: str,
        payload: DeliberationSummaryCreate,
        principal: Principal,
    ) -> DeliberationSummaryModel:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")
        item = DeliberationSummaryModel(
            tenant_id=principal.tenant_id,
            mission_id=mission_id,
            alternatives=payload.alternatives,
            rationale_summary=payload.rationale_summary,
            uncertainty=payload.uncertainty,
            open_tensions=payload.open_tensions,
            evidence=payload.evidence,
            created_by=principal.principal_id,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    async def get_latest_summary(self, db: AsyncSession, mission_id: str, tenant_id: str) -> DeliberationSummaryModel | None:
        query = select(DeliberationSummaryModel).where(
            DeliberationSummaryModel.tenant_id == tenant_id,
            DeliberationSummaryModel.mission_id == mission_id,
        )
        result = await db.execute(query.order_by(desc(DeliberationSummaryModel.created_at)).limit(1))
        return result.scalar_one_or_none()

    async def create_tension(
        self,
        db: AsyncSession,
        mission_id: str,
        payload: MissionTensionCreate,
        principal: Principal,
    ) -> MissionTensionModel:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")
        item = MissionTensionModel(
            tenant_id=principal.tenant_id,
            mission_id=mission_id,
            hypothesis=payload.hypothesis,
            perspective=payload.perspective,
            tension=payload.tension,
            status="open",
            evidence=payload.evidence,
            created_by=principal.principal_id,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    async def list_tensions(self, db: AsyncSession, mission_id: str, tenant_id: str) -> list[MissionTensionModel]:
        query = select(MissionTensionModel).where(
            MissionTensionModel.tenant_id == tenant_id,
            MissionTensionModel.mission_id == mission_id,
        )
        result = await db.execute(query.order_by(desc(MissionTensionModel.created_at)))
        return list(result.scalars().all())


_deliberation_layer_service: DeliberationLayerService | None = None


def get_deliberation_layer_service() -> DeliberationLayerService:
    global _deliberation_layer_service
    if _deliberation_layer_service is None:
        _deliberation_layer_service = DeliberationLayerService()
    return _deliberation_layer_service
