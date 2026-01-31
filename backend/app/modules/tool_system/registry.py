"""
Tool Registry - Central tool management with versioning.

Responsibilities:
    - CRUD operations for tool definitions
    - Version management (register, upgrade, rollback)
    - Search & discovery by capability, tag, status
    - KARMA score tracking per tool
    - EventStream integration for all mutations
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from .schemas import (
    ToolAccumulationRecord,
    ToolDefinition,
    ToolListResponse,
    ToolRegisterRequest,
    ToolSearchRequest,
    ToolStatus,
    ToolSystemStats,
    ToolUpdateRequest,
    ToolVersion,
)

# EventStream integration (Event Charter v1.0)
try:
    from mission_control_core.core import EventStream, Event
except ImportError:
    EventStream = None
    Event = None


class ToolRegistry:
    """
    Central registry for all tools known to BRAIN.

    In-memory storage with EventStream event publishing.
    Tools go through a lifecycle: PENDING → VALIDATED → ACTIVE.
    """

    def __init__(self, event_stream: Optional["EventStream"] = None):
        self.event_stream = event_stream

        # Storage (in-memory; future: PostgreSQL)
        self._tools: Dict[str, ToolDefinition] = {}
        self._accumulation: Dict[str, ToolAccumulationRecord] = {}

        # Metrics
        self._total_registrations = 0
        self._total_executions = 0

        logger.info(
            "🔧 ToolRegistry initialized (EventStream: %s)",
            "enabled" if event_stream else "disabled",
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def register(self, request: ToolRegisterRequest) -> ToolDefinition:
        """Register a new tool. Starts in PENDING status until validated."""
        tool_id = f"tool_{uuid.uuid4().hex[:12]}"

        tool = ToolDefinition(
            tool_id=tool_id,
            name=request.name,
            description=request.description,
            author=request.author,
            capabilities=request.capabilities,
            tags=request.tags,
            security_level=request.security_level,
            source=request.source,
            versions=[
                ToolVersion(version=request.version, changelog="Initial registration")
            ],
            current_version=request.version,
            status=ToolStatus.PENDING,
            metadata=request.metadata,
        )

        self._tools[tool_id] = tool
        self._accumulation[tool_id] = ToolAccumulationRecord(tool_id=tool_id)
        self._total_registrations += 1

        logger.info("📦 Tool registered: %s (%s) [%s]", tool.name, tool_id, tool.status.value)

        await self._emit("tool.registered", tool_id=tool_id, name=tool.name)

        return tool

    async def get(self, tool_id: str) -> Optional[ToolDefinition]:
        return self._tools.get(tool_id)

    async def list_tools(
        self,
        status: Optional[ToolStatus] = None,
    ) -> List[ToolDefinition]:
        tools = list(self._tools.values())
        if status is not None:
            tools = [t for t in tools if t.status == status]
        return tools

    async def update(self, tool_id: str, request: ToolUpdateRequest) -> Optional[ToolDefinition]:
        tool = self._tools.get(tool_id)
        if not tool:
            return None

        if request.description is not None:
            tool.description = request.description
        if request.tags is not None:
            tool.tags = request.tags
        if request.security_level is not None:
            tool.security_level = request.security_level
        if request.status is not None:
            old_status = tool.status
            tool.status = request.status
            logger.info("Tool %s status: %s → %s", tool_id, old_status.value, request.status.value)
        if request.metadata is not None:
            tool.metadata.update(request.metadata)

        await self._emit("tool.updated", tool_id=tool_id)
        return tool

    async def delete(self, tool_id: str) -> bool:
        if tool_id not in self._tools:
            return False
        name = self._tools[tool_id].name
        del self._tools[tool_id]
        self._accumulation.pop(tool_id, None)
        logger.info("🗑️ Tool deleted: %s (%s)", name, tool_id)
        await self._emit("tool.deleted", tool_id=tool_id, name=name)
        return True

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    async def set_status(self, tool_id: str, new_status: ToolStatus, reason: str = "") -> bool:
        tool = self._tools.get(tool_id)
        if not tool:
            return False

        old = tool.status
        tool.status = new_status
        logger.info("Tool %s: %s → %s (%s)", tool_id, old.value, new_status.value, reason or "no reason")
        await self._emit(
            "tool.status_changed",
            tool_id=tool_id,
            old_status=old.value,
            new_status=new_status.value,
            reason=reason,
        )
        return True

    # ------------------------------------------------------------------
    # Version management
    # ------------------------------------------------------------------

    async def add_version(self, tool_id: str, version: str, changelog: str = "") -> bool:
        tool = self._tools.get(tool_id)
        if not tool:
            return False

        tv = ToolVersion(version=version, changelog=changelog)
        tool.versions.append(tv)
        tool.current_version = version
        logger.info("Tool %s upgraded to v%s", tool_id, version)
        await self._emit("tool.version_added", tool_id=tool_id, version=version)
        return True

    # ------------------------------------------------------------------
    # Search & Discovery
    # ------------------------------------------------------------------

    async def search(self, request: ToolSearchRequest) -> List[ToolDefinition]:
        results = list(self._tools.values())

        if request.status is not None:
            results = [t for t in results if t.status == request.status]

        if request.min_karma is not None:
            results = [t for t in results if t.karma_score >= request.min_karma]

        if request.tags:
            tag_set = set(request.tags)
            results = [t for t in results if tag_set & set(t.tags)]

        if request.capability:
            cap = request.capability.lower()
            results = [
                t for t in results
                if any(cap in c.name.lower() for c in t.capabilities)
            ]

        if request.query:
            q = request.query.lower()
            results = [
                t for t in results
                if q in t.name.lower() or q in t.description.lower()
            ]

        return results

    # ------------------------------------------------------------------
    # KARMA integration
    # ------------------------------------------------------------------

    async def update_karma(self, tool_id: str, score: float) -> bool:
        tool = self._tools.get(tool_id)
        if not tool:
            return False

        tool.karma_score = max(0.0, min(100.0, score))

        # Track trend in accumulation record
        acc = self._accumulation.get(tool_id)
        if acc:
            acc.karma_trend.append(score)
            if len(acc.karma_trend) > 50:
                acc.karma_trend = acc.karma_trend[-50:]

        return True

    # ------------------------------------------------------------------
    # Accumulation records
    # ------------------------------------------------------------------

    async def get_accumulation(self, tool_id: str) -> Optional[ToolAccumulationRecord]:
        return self._accumulation.get(tool_id)

    async def record_execution(
        self,
        tool_id: str,
        success: bool,
        duration_ms: float,
    ) -> None:
        """Record an execution in the accumulation record."""
        acc = self._accumulation.get(tool_id)
        if not acc:
            return

        acc.total_executions += 1
        self._total_executions += 1

        if success:
            acc.successful_executions += 1
        else:
            acc.failed_executions += 1

        # Running average
        if acc.total_executions == 1:
            acc.avg_duration_ms = duration_ms
        else:
            acc.avg_duration_ms = (
                acc.avg_duration_ms * (acc.total_executions - 1) + duration_ms
            ) / acc.total_executions

        # Update tool metadata
        tool = self._tools.get(tool_id)
        if tool:
            tool.use_count = acc.total_executions
            tool.last_used_at = datetime.utcnow()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(self) -> ToolSystemStats:
        tools = list(self._tools.values())
        active = [t for t in tools if t.status == ToolStatus.ACTIVE]
        scores = [t.karma_score for t in tools] if tools else [0.0]

        return ToolSystemStats(
            total_tools=len(tools),
            active_tools=len(active),
            pending_tools=sum(1 for t in tools if t.status == ToolStatus.PENDING),
            suspended_tools=sum(1 for t in tools if t.status == ToolStatus.SUSPENDED),
            rejected_tools=sum(1 for t in tools if t.status == ToolStatus.REJECTED),
            total_executions=self._total_executions,
            total_accumulated=sum(
                1 for a in self._accumulation.values() if a.total_executions > 0
            ),
            avg_karma_score=sum(scores) / len(scores),
        )

    # ------------------------------------------------------------------
    # EventStream helper
    # ------------------------------------------------------------------

    async def _emit(self, event_type: str, **payload: Any) -> None:
        if self.event_stream is None or Event is None:
            return
        try:
            payload["timestamp"] = time.time()
            event = Event(type=event_type, source="tool_registry", target=None, payload=payload)
            await self.event_stream.publish(event)
        except Exception as e:
            logger.error("[ToolRegistry] Event publish failed: %s", e)


# Any-typed import for payload kwargs
from typing import Any  # noqa: E402 (used in _emit)
