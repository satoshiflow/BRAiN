from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.skill_engine.service import get_skill_engine_service

from .models import KnowledgeItemModel
from .schemas import KnowledgeItemCreate, KnowledgeSearchQuery


class KnowledgeLayerService:
    async def create_item(self, db: AsyncSession, payload: KnowledgeItemCreate, principal: Principal) -> KnowledgeItemModel:
        item = KnowledgeItemModel(
            tenant_id=principal.tenant_id,
            type=payload.type,
            title=payload.title,
            source=payload.source,
            version=payload.version,
            owner=principal.principal_id,
            module=payload.module,
            tags=payload.tags,
            content=payload.content,
            provenance_refs=payload.provenance_refs,
            valid_until=payload.valid_until,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    async def get_item(self, db: AsyncSession, item_id, tenant_id: str | None) -> KnowledgeItemModel | None:
        query = select(KnowledgeItemModel).where(KnowledgeItemModel.id == item_id)
        if tenant_id:
            query = query.where(KnowledgeItemModel.tenant_id == tenant_id)
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def search(self, db: AsyncSession, tenant_id: str | None, payload: KnowledgeSearchQuery) -> list[KnowledgeItemModel]:
        query = select(KnowledgeItemModel)
        if tenant_id:
            query = query.where(KnowledgeItemModel.tenant_id == tenant_id)
        if payload.type:
            query = query.where(KnowledgeItemModel.type == payload.type)
        if payload.module:
            query = query.where(KnowledgeItemModel.module == payload.module)
        term = f"%{payload.query}%"
        query = query.where(
            or_(
                KnowledgeItemModel.title.ilike(term),
                KnowledgeItemModel.content.ilike(term),
            )
        ).order_by(KnowledgeItemModel.created_at.desc()).limit(payload.limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def ingest_run_lesson(self, db: AsyncSession, skill_run_id, principal: Principal) -> KnowledgeItemModel:
        run = await get_skill_engine_service().get_run(db, skill_run_id, principal.tenant_id)
        if run is None:
            raise ValueError("Skill run not found")
        content = (
            f"SkillRun {run.skill_key} v{run.skill_version} finished in state {run.state}. "
            f"Failure code: {run.failure_code or 'none'}. Evaluation: {run.evaluation_summary or {}}."
        )
        item = KnowledgeItemModel(
            tenant_id=principal.tenant_id,
            type="run_lesson",
            title=f"Run lesson: {run.skill_key}",
            source="skill_run",
            version=1,
            owner=principal.principal_id,
            module="skill_engine",
            tags=[run.skill_key, run.state],
            content=content,
            provenance_refs=[
                {"type": "skill_run", "id": str(run.id)},
                {"type": "evaluation_result", "id": run.evaluation_summary.get("evaluation_result_id")},
            ],
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item


_knowledge_layer_service: KnowledgeLayerService | None = None


def get_knowledge_layer_service() -> KnowledgeLayerService:
    global _knowledge_layer_service
    if _knowledge_layer_service is None:
        _knowledge_layer_service = KnowledgeLayerService()
    return _knowledge_layer_service
