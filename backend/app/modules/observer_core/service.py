from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ObserverSignalModel, ObserverStateModel


class ObserverCoreService:
    async def list_signals(
        self,
        db: AsyncSession,
        tenant_id: str,
        source_module: str | None = None,
        severity: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 50,
    ) -> list[ObserverSignalModel]:
        query = select(ObserverSignalModel).where(ObserverSignalModel.tenant_id == tenant_id)
        if source_module:
            query = query.where(ObserverSignalModel.source_module == source_module)
        if severity:
            query = query.where(ObserverSignalModel.severity == severity)
        if entity_type:
            query = query.where(ObserverSignalModel.entity_type == entity_type)
        if entity_id:
            query = query.where(ObserverSignalModel.entity_id == entity_id)
        query = query.order_by(desc(ObserverSignalModel.occurred_at)).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_signal(self, db: AsyncSession, signal_id, tenant_id: str) -> ObserverSignalModel | None:
        query = select(ObserverSignalModel).where(
            ObserverSignalModel.id == signal_id,
            ObserverSignalModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_tenant_state(self, db: AsyncSession, tenant_id: str) -> ObserverStateModel | None:
        query = select(ObserverStateModel).where(
            ObserverStateModel.tenant_id == tenant_id,
            ObserverStateModel.scope_type == "tenant_global",
            ObserverStateModel.scope_entity_type == "",
            ObserverStateModel.scope_entity_id == "",
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_entity_state(
        self,
        db: AsyncSession,
        tenant_id: str,
        entity_type: str,
        entity_id: str,
    ) -> ObserverStateModel | None:
        query = select(ObserverStateModel).where(
            ObserverStateModel.tenant_id == tenant_id,
            ObserverStateModel.scope_type == "entity",
            ObserverStateModel.scope_entity_type == entity_type,
            ObserverStateModel.scope_entity_id == entity_id,
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()


_observer_core_service: ObserverCoreService | None = None


def get_observer_core_service() -> ObserverCoreService:
    global _observer_core_service
    if _observer_core_service is None:
        _observer_core_service = ObserverCoreService()
    return _observer_core_service
