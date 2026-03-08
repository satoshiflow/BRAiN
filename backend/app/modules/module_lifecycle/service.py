from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ModuleLifecycleModel
from .schemas import ModuleClassification, ModuleLifecycleStatus


ALLOWED_TRANSITIONS: dict[ModuleLifecycleStatus, set[ModuleLifecycleStatus]] = {
    ModuleLifecycleStatus.EXPERIMENTAL: {
        ModuleLifecycleStatus.STABLE,
        ModuleLifecycleStatus.DEPRECATED,
        ModuleLifecycleStatus.RETIRED,
    },
    ModuleLifecycleStatus.STABLE: {
        ModuleLifecycleStatus.DEPRECATED,
        ModuleLifecycleStatus.RETIRED,
    },
    ModuleLifecycleStatus.DEPRECATED: {
        ModuleLifecycleStatus.RETIRED,
    },
    ModuleLifecycleStatus.RETIRED: set(),
}


class ModuleLifecycleService:
    async def list_modules(
        self,
        db: AsyncSession,
        *,
        classification: ModuleClassification | None = None,
        lifecycle_status: ModuleLifecycleStatus | None = None,
    ) -> list[ModuleLifecycleModel]:
        query = select(ModuleLifecycleModel)
        if classification is not None:
            query = query.where(ModuleLifecycleModel.classification == classification.value)
        if lifecycle_status is not None:
            query = query.where(ModuleLifecycleModel.lifecycle_status == lifecycle_status.value)
        result = await db.execute(query.order_by(ModuleLifecycleModel.module_id.asc()))
        return list(result.scalars().all())

    async def get_module(self, db: AsyncSession, module_id: str) -> ModuleLifecycleModel | None:
        result = await db.execute(select(ModuleLifecycleModel).where(ModuleLifecycleModel.module_id == module_id).limit(1))
        return result.scalar_one_or_none()

    async def set_status(
        self,
        db: AsyncSession,
        module_id: str,
        status: ModuleLifecycleStatus,
        replacement_target: str | None,
        sunset_phase: str | None,
        notes: str | None,
    ) -> ModuleLifecycleModel | None:
        item = await self.get_module(db, module_id)
        if item is None:
            return None

        current_status = ModuleLifecycleStatus(item.lifecycle_status)
        if status == current_status:
            return item
        if status not in ALLOWED_TRANSITIONS[current_status]:
            raise ValueError(f"Invalid lifecycle transition: {current_status.value} -> {status.value}")
        if status in {ModuleLifecycleStatus.DEPRECATED, ModuleLifecycleStatus.RETIRED} and not (replacement_target or item.replacement_target):
            raise ValueError("replacement_target is required for deprecated or retired modules")

        setattr(item, "lifecycle_status", status.value)
        if replacement_target is not None:
            setattr(item, "replacement_target", replacement_target)
        if sunset_phase is not None:
            setattr(item, "sunset_phase", sunset_phase)
        if notes is not None:
            setattr(item, "notes", notes)
        setattr(item, "updated_at", datetime.now(timezone.utc))
        await db.commit()
        await db.refresh(item)
        return item


_module_lifecycle_service: ModuleLifecycleService | None = None


def get_module_lifecycle_service() -> ModuleLifecycleService:
    global _module_lifecycle_service
    if _module_lifecycle_service is None:
        _module_lifecycle_service = ModuleLifecycleService()
    return _module_lifecycle_service
