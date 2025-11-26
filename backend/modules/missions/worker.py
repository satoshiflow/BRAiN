"""
BRAIN Mission System V1 - Mission Worker / Orchestrator
-------------------------------------------------------

Ein einfacher Hintergrund-Worker, der:
- regelmäßig die MissionQueue abfragt
- die nächste Mission holt
- sie "ausführt" (Stub-Executor)
- bei Fehlern optional neu enqueued
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional, Dict, Any

from .models import Mission, MissionPayload
from .queue import MissionQueue

logger = logging.getLogger(__name__)


class MissionWorker:
    def __init__(self, queue: MissionQueue, poll_interval: float = 2.0) -> None:
        self.queue = queue
        self.poll_interval = poll_interval
        self.running: bool = False
        self._task: Optional[asyncio.Task] = None

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

            try:
                await self.execute_mission(mission)
            except Exception as exc:
                logger.exception("Mission %s failed: %s", mission.id, exc)
                # einfache Retry-Logik
                mission.retry_count += 1
                if mission.retry_count <= mission.max_retries:
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
                else:
                    logger.error("❌ Mission %s permanently failed", mission.id)

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


async def start_mission_worker() -> None:
    global _worker
    if _worker is not None:
        return
    queue = _get_queue()
    poll_interval = float(os.getenv("MISSION_WORKER_POLL_INTERVAL", "2.0"))
    _worker = MissionWorker(queue=queue, poll_interval=poll_interval)
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