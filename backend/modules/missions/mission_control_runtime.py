# backend/modules/missions/mission_control_runtime.py
"""
MissionControlRuntime
---------------------

Integration-Layer zwischen:

- unserem einfachen MissionQueue-System (Redis ZSET)
- dem EventStream für Mission-Events

Phase 2:
- enqueue_mission() nutzt MissionQueue
- EventStream erzeugt TASK_CREATED-Events
- API kann Event-Historie & Stats abfragen
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from .event_stream import (
    EventStream,
    Event,
    EventType,
    emit_task_event,
)

from .models import MissionPayload, MissionQueueEntry, MissionEnqueueResult
from .queue import MissionQueue

logger = logging.getLogger(__name__)


class MissionControlRuntime:
    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379/0")

        self.queue: Optional[MissionQueue] = None
        self.event_stream: Optional[EventStream] = None

        self._initialized: bool = False
        self._init_lock = asyncio.Lock()

    async def ensure_initialized(self) -> None:
        """
        Stellt sicher, dass Queue und EventStream initialisiert sind.
        Idempotent – kann beliebig oft aufgerufen werden.
        """
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            # MissionQueue
            self.queue = MissionQueue(redis_url=self.redis_url)
            await self.queue.connect()

            # EventStream
            self.event_stream = EventStream(redis_url=self.redis_url)
            await self.event_stream.initialize()
            # In Phase 2 starten wir keinen Listener-Loop (nur publish + read)

            self._initialized = True
            logger.info(
                "MissionControlRuntime initialized (redis_url=%s)", self.redis_url
            )

    # -------------------------------------------------------------------------
    # High-Level API: Mission/Queue
    # -------------------------------------------------------------------------

    async def enqueue_mission(
        self,
        payload: MissionPayload,
        created_by: str = "api",
    ) -> MissionEnqueueResult:
        """
        Legt eine Mission in die Queue und erzeugt ein TASK_CREATED-Event.
        """
        await self.ensure_initialized()
        assert self.queue is not None
        assert self.event_stream is not None

        result = await self.queue.enqueue(payload)

        try:
            await emit_task_event(
                self.event_stream,
                task_id=result.mission_id,
                event_type=EventType.TASK_CREATED,
                source=created_by,
                mission_id=result.mission_id,
                extra_data={
                    "mission_type": payload.type,
                    "priority": payload.priority.name,
                },
            )
        except Exception as exc:
            logger.error("Failed to emit TASK_CREATED event: %s", exc)

        return result

    async def get_queue_preview(self, limit: int = 20) -> List[MissionQueueEntry]:
        await self.ensure_initialized()
        assert self.queue is not None
        return await self.queue.get_queue_preview(limit=limit)

    async def get_queue_stats(self, preview_limit: int = 10) -> Dict[str, Any]:
        await self.ensure_initialized()
        assert self.queue is not None
        return await self.queue.get_queue_stats(preview_limit=preview_limit)

    async def get_queue_health(self) -> bool:
        await self.ensure_initialized()
        assert self.queue is not None
        return await self.queue.health()

    # -------------------------------------------------------------------------
    # Event-API: History & Stats
    # -------------------------------------------------------------------------

    async def get_event_history(
        self,
        *,
        limit: int = 100,
        agent_id: Optional[str] = None,
    ) -> List[Event]:
        """
        Liefert Event-Historie als Liste von Event-Objekten.
        """
        await self.ensure_initialized()
        assert self.event_stream is not None

        events = await self.event_stream.get_event_history(
            agent_id=agent_id,
            event_types=None,
            limit=limit,
        )
        return events

    async def get_event_stats(self) -> Dict[str, Any]:
        await self.ensure_initialized()
        assert self.event_stream is not None
        return await self.event_stream.get_stream_stats()


# -----------------------------------------------------------------------------
# Singleton-Access für Router / Services
# -----------------------------------------------------------------------------

_runtime: Optional[MissionControlRuntime] = None


def get_mission_runtime() -> MissionControlRuntime:
    global _runtime
    if _runtime is None:
        _runtime = MissionControlRuntime()
    return _runtime
