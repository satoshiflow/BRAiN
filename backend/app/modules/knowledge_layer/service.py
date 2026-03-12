from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.experience_layer.service import get_experience_layer_service

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

    async def get_item(self, db: AsyncSession, item_id, tenant_id: str) -> KnowledgeItemModel | None:
        query = select(KnowledgeItemModel).where(
            KnowledgeItemModel.id == item_id,
            KnowledgeItemModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def search(self, db: AsyncSession, tenant_id: str, payload: KnowledgeSearchQuery) -> list[KnowledgeItemModel]:
        query = select(KnowledgeItemModel).where(KnowledgeItemModel.tenant_id == tenant_id)
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
        if not principal.tenant_id:
            raise PermissionError("Tenant context required")

        experience = await get_experience_layer_service().ingest_skill_run(db, skill_run_id, principal)
        skill_key = str(experience.signals.get("skill_key", "unknown"))
        content = (
            f"Experience lesson for SkillRun {skill_key}: {experience.summary} "
            f"Evaluation: {experience.evaluation_summary or {}}."
        )
        item = KnowledgeItemModel(
            tenant_id=principal.tenant_id,
            type="run_lesson",
            title=f"Run lesson: {skill_key}",
            source="experience_record",
            version=1,
            owner=principal.principal_id,
            module="experience_layer",
            tags=[skill_key, experience.state],
            content=content,
            provenance_refs=[
                {"type": "skill_run", "id": str(experience.skill_run_id)},
                {"type": "experience_record", "id": str(experience.id)},
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
