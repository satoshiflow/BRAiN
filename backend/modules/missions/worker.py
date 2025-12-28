"""
BRAIN Mission System V1 - Mission Worker / Orchestrator
-------------------------------------------------------

Ein einfacher Hintergrund-Worker, der:
- regelmäßig die MissionQueue abfragt
- die nächste Mission holt
- sie "ausführt" (Stub-Executor)
- bei Fehlern optional neu enqueued

Sprint 2 EventStream Integration:
- TASK_STARTED: When mission picked from queue
- TASK_COMPLETED: When mission succeeds
- TASK_FAILED: When mission fails (with/without retry)
- TASK_RETRYING: When mission re-enqueued for retry
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional, Dict, Any

from .models import Mission, MissionPayload
from .queue import MissionQueue

# EventStream integration (Sprint 2)
try:
    from backend.mission_control_core.core import EventStream, Event, EventType, emit_task_event
except ImportError:
    EventStream = None
    Event = None
    EventType = None
    emit_task_event = None
    import warnings
    warnings.warn(
        "[MissionWorker] EventStream not available (mission_control_core not installed)",
        RuntimeWarning
    )

logger = logging.getLogger(__name__)


class MissionWorker:
    def __init__(
        self,
        queue: MissionQueue,
        poll_interval: float = 2.0,
        event_stream: Optional["EventStream"] = None,
    ) -> None:
        self.queue = queue
        self.poll_interval = poll_interval
        self.event_stream = event_stream
        self.running: bool = False
        self._task: Optional[asyncio.Task] = None

    async def _emit_event_safe(
        self,
        event_type: "EventType",
        mission: Mission,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit event with error handling (non-blocking).

        Charter v1.0 Compliance:
        - Event publishing MUST NOT block business logic
        - Failures are logged but NOT raised
        """
        if self.event_stream is None or emit_task_event is None:
            logger.debug("[MissionWorker] EventStream not available, skipping event")
            return

        try:
            await emit_task_event(
                self.event_stream,
                task_id=mission.id,
                event_type=event_type,
                source="mission_worker",
                mission_id=mission.id,
                extra_data=extra_data or {},
            )
            logger.debug(
                "[MissionWorker] Event published: %s (mission_id=%s)",
                event_type.value if hasattr(event_type, 'value') else event_type,
                mission.id,
            )
        except Exception as e:
            logger.error(
                "[MissionWorker] Event publishing failed: %s (mission_id=%s)",
                event_type.value if hasattr(event_type, 'value') else event_type,
                mission.id,
                exc_info=True,
            )
            # DO NOT raise - business logic must continue

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        await self.queue.connect()
        logger.info("🚀 MissionWorker started (poll_interval=%ss)", self.poll_interval)
        self._task = asyncio.create_task(self._run_loop(), name="mission-worker-loop")

    async def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 MissionWorker stopped")

    async def _run_loop(self) -> None:
        while self.running:
            job = await self.queue.pop_next()
            if not job:
                await asyncio.sleep(self.poll_interval)
                continue

            mission, score = job
            logger.info(
                "⚙️  Executing mission %s (type=%s, priority=%s, score=%.1f)",
                mission.id,
                mission.type,
                mission.priority,
                score,
            )

            # EVENT: TASK_STARTED
            start_time = time.time()
            if EventType is not None:
                await self._emit_event_safe(
                    EventType.TASK_STARTED,
                    mission,
                    extra_data={
                        "mission_type": mission.type,
                        "priority": mission.priority.name,
                        "score": score,
                        "retry_count": mission.retry_count,
                        "started_at": time.time(),
                    },
                )

            try:
                await self.execute_mission(mission)

                # EVENT: TASK_COMPLETED
                duration_ms = (time.time() - start_time) * 1000
                if EventType is not None:
                    await self._emit_event_safe(
                        EventType.TASK_COMPLETED,
                        mission,
                        extra_data={
                            "mission_type": mission.type,
                            "duration_ms": duration_ms,
                            "completed_at": time.time(),
                        },
                    )

            except Exception as exc:
                logger.exception("Mission %s failed: %s", mission.id, exc)

                # EVENT: TASK_FAILED (initial failure, may retry)
                duration_ms = (time.time() - start_time) * 1000
                mission.retry_count += 1
                will_retry = mission.retry_count <= mission.max_retries

                if EventType is not None:
                    await self._emit_event_safe(
                        EventType.TASK_FAILED,
                        mission,
                        extra_data={
                            "mission_type": mission.type,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                            "retry_count": mission.retry_count,
                            "max_retries": mission.max_retries,
                            "will_retry": will_retry,
                            "duration_ms": duration_ms,
                            "failed_at": time.time(),
                        },
                    )

                # einfache Retry-Logik
                if will_retry:
                    logger.info(
                        "🔁 Re-enqueue mission %s (retry %s/%s)",
                        mission.id,
                        mission.retry_count,
                        mission.max_retries,
                    )
                    payload = MissionPayload(
                        type=mission.type,
                        payload=mission.payload,
                        priority=mission.priority,
                    )
                    await self.queue.enqueue(payload)

                    # EVENT: TASK_RETRYING
                    if EventType is not None:
                        await self._emit_event_safe(
                            EventType.TASK_RETRYING,
                            mission,
                            extra_data={
                                "mission_type": mission.type,
                                "retry_count": mission.retry_count,
                                "max_retries": mission.max_retries,
                                "next_attempt": mission.retry_count + 1,
                                "retried_at": time.time(),
                            },
                        )
                else:
                    logger.error("❌ Mission %s permanently failed", mission.id)
                    # EVENT: TASK_FAILED already emitted above with will_retry=False

    async def execute_mission(self, mission: Mission) -> None:
        """
        Hier später echte Orchestrierung (Agenten aufrufen, Connectors triggern, etc.).
        Für V1 loggen wir nur – aber hier ist der zentrale Hook.
        """
        # Beispiel: einfache Routing-Logik nach Typ
        if mission.type == "agent.chat":
            await self._execute_agent_chat(mission)
        else:
            await self._execute_generic(mission)

    async def _execute_agent_chat(self, mission: Mission) -> None:
        message = mission.payload.get("message", "")
        agent_id = mission.payload.get("agent_id", "default")
        logger.info("💬 [agent.chat] agent=%s message=%r", agent_id, message)
        # TODO: hier später direkt Agent-Subsystem aufrufen
        await asyncio.sleep(0.1)

    async def _execute_generic(self, mission: Mission) -> None:
        logger.info("📦 [generic] mission=%s payload=%r", mission.id, mission.payload)
        await asyncio.sleep(0.05)


# ---------- Globale Worker-Verwaltung für FastAPI ----------

_worker: Optional[MissionWorker] = None
_queue: Optional[MissionQueue] = None


def _get_queue() -> MissionQueue:
    global _queue
    if _queue is None:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _queue = MissionQueue(redis_url=redis_url)
    return _queue


async def start_mission_worker(event_stream: Optional["EventStream"] = None) -> None:
    """
    Start mission worker with optional EventStream integration.

    Args:
        event_stream: EventStream instance for event publishing (Sprint 2)
    """
    global _worker
    if _worker is not None:
        return
    queue = _get_queue()
    poll_interval = float(os.getenv("MISSION_WORKER_POLL_INTERVAL", "2.0"))
    _worker = MissionWorker(
        queue=queue,
        poll_interval=poll_interval,
        event_stream=event_stream,
    )
    await _worker.start()


async def stop_mission_worker() -> None:
    global _worker
    if _worker is None:
        return
    await _worker.stop()
    _worker = None


def get_worker_status() -> Dict[str, Any]:
    """
    Kleine Status-Ansicht, damit das Control Deck sehen kann,
    ob der Worker läuft.
    """
    global _worker, _queue
    return {
        "running": bool(_worker and _worker.running),
        "poll_interval": getattr(_worker, "poll_interval", None),
        "redis_url": getattr(_queue, "redis_url", None) if _queue else None,
    }