from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.auth_deps import Principal
from app.modules.skill_engine.service import get_skill_engine_service

from .models import ExperienceRecordModel


class ExperienceLayerService:
    async def get_by_id(self, db: AsyncSession, experience_id, tenant_id: str) -> ExperienceRecordModel | None:
        query = select(ExperienceRecordModel).where(ExperienceRecordModel.id == experience_id)
        query = query.where(ExperienceRecordModel.tenant_id == tenant_id)
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_by_skill_run_id(self, db: AsyncSession, skill_run_id, tenant_id: str) -> ExperienceRecordModel | None:
        query = select(ExperienceRecordModel).where(ExperienceRecordModel.skill_run_id == skill_run_id)
        query = query.where(ExperienceRecordModel.tenant_id == tenant_id)
        result = await db.execute(query.order_by(ExperienceRecordModel.created_at.desc()).limit(1))
        return result.scalar_one_or_none()

    async def ingest_skill_run(self, db: AsyncSession, skill_run_id, principal: Principal) -> ExperienceRecordModel:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")
        existing = await self.get_by_skill_run_id(db, skill_run_id, principal.tenant_id)
        if existing is not None:
            return existing

        run = await get_skill_engine_service().get_run(db, skill_run_id, principal.tenant_id)
        if run is None:
            raise ValueError("Skill run not found")

        summary = (
            f"SkillRun {run.skill_key} v{run.skill_version} finished in state {run.state}. "
            f"Failure code: {run.failure_code or 'none'}."
        )

        record = ExperienceRecordModel(
            tenant_id=principal.tenant_id,
            skill_run_id=run.id,
            idempotency_key=f"experience:{principal.tenant_id or 'global'}:{run.id}",
            state=run.state,
            failure_code=run.failure_code,
            summary=summary,
            evaluation_summary=run.evaluation_summary or {},
            signals={
                "skill_key": run.skill_key,
                "skill_version": run.skill_version,
                "cost_actual": run.cost_actual,
                "retry_count": run.retry_count,
            },
        )
        db.add(record)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            existing_after_race = await self.get_by_skill_run_id(db, skill_run_id, principal.tenant_id)
            if existing_after_race is not None:
                return existing_after_race
            raise
        await db.refresh(record)
        return record


_experience_layer_service: ExperienceLayerService | None = None


def get_experience_layer_service() -> ExperienceLayerService:
    global _experience_layer_service
    if _experience_layer_service is None:
        _experience_layer_service = ExperienceLayerService()
    return _experience_layer_service
