from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, or_, select
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

    async def get_incident_timeline(
        self,
        db: AsyncSession,
        tenant_id: str,
        correlation_id: str | None = None,
        skill_run_id: str | None = None,
        mission_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        time_window_minutes: int = 60,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Retrieve incident timeline for operator diagnostics.

        Returns chronological sequence of signals related to an incident,
        supporting correlation by correlation_id, skill_run_id, mission_id,
        or entity context.

        Args:
            db: Database session
            tenant_id: Tenant context
            correlation_id: Filter by correlation ID
            skill_run_id: Filter by skill run ID (extracted from correlation_id pattern)
            mission_id: Filter by mission ID (extracted from correlation_id pattern)
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            time_window_minutes: Time window to search (default 60 minutes)
            limit: Maximum number of signals to return

        Returns:
            dict with:
                - signals: list of ObserverSignalModel instances
                - correlation_groups: dict mapping correlation_id -> signal count
                - severity_distribution: dict mapping severity -> count
                - timeline_start: earliest signal timestamp
                - timeline_end: latest signal timestamp
                - total_signals: total count
        """
        # Build base query
        query = select(ObserverSignalModel).where(ObserverSignalModel.tenant_id == tenant_id)

        # Apply correlation filters
        correlation_filters = []
        if correlation_id:
            correlation_filters.append(ObserverSignalModel.correlation_id == correlation_id)
        if skill_run_id:
            # Match correlation IDs that contain skill_run_id pattern
            correlation_filters.append(ObserverSignalModel.correlation_id.like(f"%{skill_run_id}%"))
        if mission_id:
            # Match correlation IDs that contain mission_id pattern
            correlation_filters.append(ObserverSignalModel.correlation_id.like(f"%{mission_id}%"))

        if correlation_filters:
            query = query.where(or_(*correlation_filters))

        # Apply entity filters
        if entity_type:
            query = query.where(ObserverSignalModel.entity_type == entity_type)
        if entity_id:
            query = query.where(ObserverSignalModel.entity_id == entity_id)

        # Apply time window
        if time_window_minutes > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
            query = query.where(ObserverSignalModel.occurred_at >= cutoff)

        # Order chronologically and limit
        query = query.order_by(ObserverSignalModel.occurred_at).limit(limit)

        # Execute query
        result = await db.execute(query)
        signals = list(result.scalars().all())

        # Compute timeline analytics
        if not signals:
            return {
                "signals": [],
                "correlation_groups": {},
                "severity_distribution": {},
                "timeline_start": None,
                "timeline_end": None,
                "total_signals": 0,
            }

        # Group by correlation_id
        correlation_groups: dict[str, int] = {}
        for sig in signals:
            if sig.correlation_id:
                correlation_groups[sig.correlation_id] = correlation_groups.get(sig.correlation_id, 0) + 1

        # Severity distribution
        severity_distribution: dict[str, int] = {}
        for sig in signals:
            severity_distribution[sig.severity] = severity_distribution.get(sig.severity, 0) + 1

        # Timeline bounds
        timeline_start = min(sig.occurred_at for sig in signals)
        timeline_end = max(sig.occurred_at for sig in signals)

        return {
            "signals": signals,
            "correlation_groups": correlation_groups,
            "severity_distribution": severity_distribution,
            "timeline_start": timeline_start,
            "timeline_end": timeline_end,
            "total_signals": len(signals),
        }


_observer_core_service: ObserverCoreService | None = None


def get_observer_core_service() -> ObserverCoreService:
    global _observer_core_service
    if _observer_core_service is None:
        _observer_core_service = ObserverCoreService()
    return _observer_core_service
