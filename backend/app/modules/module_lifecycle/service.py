from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ModuleLifecycleModel


class ModuleLifecycleService:
    async def list_modules(self, db: AsyncSession) -> list[ModuleLifecycleModel]:
        result = await db.execute(select(ModuleLifecycleModel).order_by(ModuleLifecycleModel.module_id.asc()))
        return list(result.scalars().all())

    async def get_module(self, db: AsyncSession, module_id: str) -> ModuleLifecycleModel | None:
        result = await db.execute(select(ModuleLifecycleModel).where(ModuleLifecycleModel.module_id == module_id).limit(1))
        return result.scalar_one_or_none()

    async def set_status(self, db: AsyncSession, module_id: str, status: str, replacement_target: str | None, sunset_phase: str | None, notes: str | None) -> ModuleLifecycleModel | None:
        item = await self.get_module(db, module_id)
        if item is None:
            return None
        item.lifecycle_status = status
        if replacement_target is not None:
            item.replacement_target = replacement_target
        if sunset_phase is not None:
            item.sunset_phase = sunset_phase
        if notes is not None:
            item.notes = notes
        await db.commit()
        await db.refresh(item)
        return item


_module_lifecycle_service: ModuleLifecycleService | None = None


def get_module_lifecycle_service() -> ModuleLifecycleService:
    global _module_lifecycle_service
    if _module_lifecycle_service is None:
        _module_lifecycle_service = ModuleLifecycleService()
    return _module_lifecycle_service
