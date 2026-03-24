from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ModuleLifecycleModel
from .schemas import ModuleClassification, ModuleDecommissionLedgerEntry, ModuleLifecycleStatus


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
        if status in {ModuleLifecycleStatus.DEPRECATED, ModuleLifecycleStatus.RETIRED} and not (sunset_phase or item.sunset_phase):
            raise ValueError("sunset_phase is required for deprecated or retired modules")
        if status == ModuleLifecycleStatus.RETIRED and not item.kill_switch:
            raise ValueError("kill_switch is required before retiring a module")

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

    async def list_decommission_ledger(self, db: AsyncSession) -> list[ModuleDecommissionLedgerEntry]:
        query = select(ModuleLifecycleModel).where(
            ModuleLifecycleModel.lifecycle_status.in_(
                [ModuleLifecycleStatus.DEPRECATED.value, ModuleLifecycleStatus.RETIRED.value]
            )
        )
        result = await db.execute(query.order_by(ModuleLifecycleModel.module_id.asc()))
        items = list(result.scalars().all())

        ledger: list[ModuleDecommissionLedgerEntry] = []
        for item in items:
            blockers: list[str] = []
            if not item.replacement_target:
                blockers.append("missing_replacement_target")
            if not item.sunset_phase:
                blockers.append("missing_sunset_phase")
            if item.lifecycle_status == ModuleLifecycleStatus.RETIRED.value and not item.kill_switch:
                blockers.append("missing_kill_switch")

            ledger.append(
                ModuleDecommissionLedgerEntry(
                    module_id=item.module_id,
                    lifecycle_status=ModuleLifecycleStatus(item.lifecycle_status),
                    replacement_target=item.replacement_target,
                    kill_switch=item.kill_switch,
                    sunset_phase=item.sunset_phase,
                    migration_adapter=item.migration_adapter,
                    decommission_ready=len(blockers) == 0,
                    blockers=blockers,
                )
            )
        return ledger


_module_lifecycle_service: ModuleLifecycleService | None = None


def get_module_lifecycle_service() -> ModuleLifecycleService:
    global _module_lifecycle_service
    if _module_lifecycle_service is None:
        _module_lifecycle_service = ModuleLifecycleService()
    return _module_lifecycle_service
