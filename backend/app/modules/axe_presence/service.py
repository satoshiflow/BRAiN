"""Service layer for AXE presence surface endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
import time

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    AXEPresenceResponse,
    AXERelayResponse,
    AXERelaysListResponse,
    AXERuntimeSurfaceResponse,
)

_START_TS = time.monotonic()


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _format_uptime(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"


class AXEPresenceService:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def get_runtime_surface(
        self,
        tenant_id: str | None = None,
    ) -> AXERuntimeSurfaceResponse:
        active_agents, pending_missions, source_signal = await self._safe_runtime_counts(
            tenant_id=tenant_id,
        )
        now = _iso_now()

        status = "ok"
        signal = "ok"
        action_hint = "safe_to_operate"
        if source_signal != "ok":
            status = "degraded"
            signal = "warn"
            action_hint = "verify_runtime_signals"
        elif active_agents == 0:
            status = "degraded"
            signal = "warn"
            action_hint = "check_agent_capacity"

        return AXERuntimeSurfaceResponse(
            status=status,
            label="AXE runtime surface",
            signal=signal,
            capabilities=["presence", "relays", "runtime"],
            last_seen=now,
            action_hint=action_hint,
            active_agents=active_agents,
            pending_missions=pending_missions,
            uptime=_format_uptime(int(time.monotonic() - _START_TS)),
        )

    async def get_presence(self, tenant_id: str | None = None) -> AXEPresenceResponse:
        runtime = await self.get_runtime_surface(tenant_id=tenant_id)
        if runtime.signal == "ok":
            status = "linked"
            label = "BRAiN relay online"
            action_hint = "safe_to_operate"
        else:
            status = "degraded"
            label = "BRAiN relay degraded"
            action_hint = "check_runtime_surface"

        return AXEPresenceResponse(
            status=status,
            label=label,
            signal=runtime.signal,
            capabilities=["chat", "sessions", "runtime"],
            last_seen=runtime.last_seen,
            action_hint=action_hint,
        )

    async def get_relays(self, tenant_id: str | None = None) -> AXERelaysListResponse:
        runtime = await self.get_runtime_surface(tenant_id=tenant_id)
        now = runtime.last_seen

        relays = [
            AXERelayResponse(
                status="ready" if runtime.signal == "ok" else "degraded",
                label="External Agents",
                signal=runtime.signal,
                capabilities=["dispatch", "sync"],
                last_seen=now,
                action_hint="handoff_available" if runtime.signal == "ok" else "verify_before_handoff",
            ),
            AXERelayResponse(
                status="standby",
                label="Robot Relay",
                signal="warn" if runtime.pending_missions > 0 else "ok",
                capabilities=["queue", "simulate"],
                last_seen=now,
                action_hint="confirm_before_execute",
            ),
            AXERelayResponse(
                status="ready" if runtime.active_agents > 0 else "degraded",
                label="Knowledge Stream",
                signal="ok" if runtime.active_agents > 0 else "warn",
                capabilities=["search", "context"],
                last_seen=now,
                action_hint="inspect_context",
            ),
        ]
        return AXERelaysListResponse(relays=relays)

    async def _safe_runtime_counts(
        self,
        tenant_id: str | None = None,
    ) -> tuple[int, int, str]:
        if self.db is None:
            return 0, 0, "warn"

        active_agents = await self._safe_active_agents(tenant_id=tenant_id)
        pending_missions = await self._safe_pending_missions(tenant_id=tenant_id)
        source_signal = "ok" if active_agents is not None and pending_missions is not None else "warn"
        return active_agents or 0, pending_missions or 0, source_signal

    async def _safe_active_agents(self, tenant_id: str | None = None) -> int | None:
        try:
            from app.modules.agent_management.models import AgentModel, AgentStatus

            active_agents_query = select(func.count(AgentModel.id)).where(
                AgentModel.status.in_([AgentStatus.ACTIVE, AgentStatus.DEGRADED])
            )
            if tenant_id is not None and hasattr(AgentModel, "tenant_id"):
                active_agents_query = active_agents_query.where(AgentModel.tenant_id == tenant_id)

            return int((await self.db.execute(active_agents_query)).scalar() or 0)
        except Exception as exc:  # pragma: no cover
            logger.warning("[AXEPresence] active agents fallback: %s", exc)
            return None

    async def _safe_pending_missions(self, tenant_id: str | None = None) -> int | None:
        try:
            from app.modules.skill_engine.models import SkillRunModel

            pending_missions_query = select(func.count(SkillRunModel.id)).where(
                SkillRunModel.state.in_(["queued", "planning", "waiting_approval"])
            )
            if tenant_id is not None and hasattr(SkillRunModel, "tenant_id"):
                pending_missions_query = pending_missions_query.where(
                    SkillRunModel.tenant_id == tenant_id
                )

            return int((await self.db.execute(pending_missions_query)).scalar() or 0)
        except Exception as exc:  # pragma: no cover
            logger.warning("[AXEPresence] pending missions fallback: %s", exc)
            return None
