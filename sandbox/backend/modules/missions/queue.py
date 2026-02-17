"""
BRAIN Mission System V1 - Redis Priority Queue (Lightweight)
------------------------------------------------------------

Einfacher Redis-basierter Mission-Queue-Wrapper.
Nutzt ein ZSET, in dem Missions als JSON gespeichert werden.

Key-Layout:
- missions:queue         -> ZSET(JSON, SCORE)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as redis

from .models import (
    Mission,
    MissionPayload,
    MissionQueueEntry,
    MissionEnqueueResult,
    MissionPriority,
)

logger = logging.getLogger(__name__)


class MissionQueue:
    MAIN_QUEUE_KEY = "missions:queue"

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            raise RuntimeError("MissionQueue not connected – call connect() first")
        return self._redis

    async def connect(self) -> None:
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            try:
                await self._redis.ping()
                logger.info("✅ MissionQueue connected to Redis at %s", self.redis_url)
            except Exception as exc:
                logger.error("❌ MissionQueue Redis connection failed: %s", exc)
                self._redis = None
                raise

    async def health(self) -> bool:
        try:
            await self.connect()
            await self.redis.ping()
            return True
        except Exception as exc:
            logger.error("MissionQueue health check failed: %s", exc)
            return False

    # ---------- Scoring ----------

    @staticmethod
    def _priority_score(priority: MissionPriority) -> int:
        """
        Höherer Priority → höherer Score.
        Einfaches Mapping:
        LOW=10, NORMAL=20, HIGH=30, CRITICAL=40
        """
        return int(priority)

    # ---------- API: enqueue / preview ----------

    async def enqueue(self, payload: MissionPayload) -> MissionEnqueueResult:
        await self.connect()

        mission = Mission(
            type=payload.type,
            payload=payload.payload,
            priority=payload.priority,
        )
        mission.mark_queued()

        score = float(self._priority_score(mission.priority))

        mission_json = mission.model_dump_json()

        # In ZSET einfügen
        await self.redis.zadd(self.MAIN_QUEUE_KEY, {mission_json: score})

        return MissionEnqueueResult(mission_id=mission.id, status=mission.status)

    async def get_queue_preview(self, limit: int = 20) -> List[MissionQueueEntry]:
        """
        Liefert die Queue-Inhalte sortiert nach Score (höchstes zuerst).
        Nur Preview: es wird nichts aus der Queue entfernt.
        """
        await self.connect()

        # ZRANGE mit WITHSCORES
        raw = await self.redis.zrevrange(
            self.MAIN_QUEUE_KEY,
            0,
            max(0, limit - 1),
            withscores=True,
        )

        entries: List[MissionQueueEntry] = []
        for mission_json, score in raw:
            try:
                mission_dict = json.loads(mission_json)
                mission = Mission(**mission_dict)
                entries.append(
                    MissionQueueEntry.from_mission(
                        mission,
                        score=float(score),
                    )
                )
            except Exception as exc:
                logger.warning("Failed to decode mission from queue: %s", exc)
                continue

        return entries

    # ---------- API: pop_next für Worker ----------

    async def pop_next(self) -> Optional[Tuple[Mission, float]]:
        """
        Holt die höchste Mission aus der Queue (höchster Score) und entfernt sie.
        Wird vom MissionWorker genutzt.
        """
        await self.connect()

        raw = await self.redis.zrevrange(
            self.MAIN_QUEUE_KEY,
            0,
            0,
            withscores=True,
        )

        if not raw:
            return None

        mission_json, score = raw[0]

        # Eintrag aus dem Set entfernen
        await self.redis.zrem(self.MAIN_QUEUE_KEY, mission_json)

        try:
            mission_dict = json.loads(mission_json)
            mission = Mission(**mission_dict)
        except Exception as exc:
            logger.warning("Failed to decode mission on pop_next: %s", exc)
            return None

        return mission, float(score)

    # ---------- Stats / Utilities ----------

    async def get_queue_length(self) -> int:
        """
        Liefert die Anzahl der Missions in der Queue.
        """
        await self.connect()
        return int(await self.redis.zcard(self.MAIN_QUEUE_KEY))

    async def get_queue_stats(self, preview_limit: int = 10) -> Dict[str, Any]:
        """
        Liefert einfache Queue-Statistiken für das Control Deck.
        """
        await self.connect()
        length = int(await self.redis.zcard(self.MAIN_QUEUE_KEY))
        preview = await self.get_queue_preview(limit=preview_limit)

        return {
            "length": length,
            "preview_limit": preview_limit,
            "preview": [entry.model_dump() for entry in preview],
        }

    async def get_health_metrics(self) -> Dict[str, Any]:
        """
        Get health metrics for SystemHealthService.
        Returns current queue status including depth and mission counts by status.
        """
        await self.connect()

        queue_length = await self.get_queue_length()
        preview = await self.get_queue_preview(limit=100)

        # Count by status
        running = len([m for m in preview if m.status == "RUNNING"])
        pending = len([m for m in preview if m.status == "QUEUED"])

        # TODO: Get completed/failed counts from mission history/database
        # For now, return zeros for these
        return {
            "queue_depth": queue_length,
            "running_missions": running,
            "pending_missions": pending,
            "completed_today": 0,  # Placeholder until mission history implemented
            "failed_today": 0,     # Placeholder until mission history implemented
        }