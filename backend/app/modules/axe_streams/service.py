import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from .schemas import (
    AXEEvent,
    AXEEventType,
    AXERunState,
    AXERunStateChangedEventData,
    AXETokenStreamEventData,
)

logger = logging.getLogger(__name__)

SUBSCRIPTION_TTL_SECONDS = 3600
CHANNEL_PREFIX = "axe:stream:"


class AXEStreamService:
    def __init__(self) -> None:
        self._subscribers: dict[UUID, asyncio.Queue[AXEEvent | None]] = {}
        self._sequence_counters: dict[UUID, int] = {}
        self._lock = asyncio.Lock()
        self._redis_pubsub_task: asyncio.Task | None = None
        self._redis = None
        self._pubsub = None

    async def _get_redis(self):
        if self._redis is None:
            from app.core.redis_client import get_redis
            self._redis = await get_redis()
        return self._redis

    async def _ensure_pubsub(self):
        if self._pubsub is None:
            redis = await self._get_redis()
            self._pubsub = redis.pubsub()
            self._redis_pubsub_task = asyncio.create_task(self._pubsub_listener())
            logger.info("AXEStreamService Redis pubsub listener started")

    async def _pubsub_listener(self):
        while True:
            try:
                if self._pubsub is None:
                    await asyncio.sleep(1)
                    continue
                async for message in self._pubsub.listen():
                    if message["type"] != "message":
                        continue
                    try:
                        data = json.loads(message["data"])
                        run_id = UUID(data["run_id"])
                        event = AXEEvent(
                            event_type=AXEEventType(data["event_type"]),
                            run_id=run_id,
                            sequence=data["sequence"],
                            timestamp=data["timestamp"],
                            data=data["data"],
                        )
                        async with self._lock:
                            if run_id in self._subscribers:
                                try:
                                    self._subscribers[run_id].put_nowait(event)
                                except asyncio.QueueFull:
                                    logger.warning(f"AXE stream queue full for run {run_id}, dropping event")
                    except Exception as exc:
                        logger.warning(f"Failed to process Redis pubsub message: {exc}")
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Redis pubsub listener error: {exc}")
                await asyncio.sleep(1)

    async def subscribe(self, run_id: UUID) -> asyncio.Queue[AXEEvent | None]:
        async with self._lock:
            if run_id not in self._subscribers:
                self._subscribers[run_id] = asyncio.Queue(maxsize=100)
                self._sequence_counters[run_id] = 0
                await self._subscribe_to_redis(run_id)
            return self._subscribers[run_id]

    async def _subscribe_to_redis(self, run_id: UUID):
        try:
            await self._ensure_pubsub()
            channel = f"{CHANNEL_PREFIX}{run_id}"
            await self._pubsub.subscribe(channel)
            logger.debug(f"Subscribed to Redis channel {channel}")
            
            try:
                redis = await self._get_redis()
                await redis.expire(f"{CHANNEL_PREFIX}active:{run_id}", SUBSCRIPTION_TTL_SECONDS)
            except Exception:
                pass
        except Exception as exc:
            logger.warning(f"Failed to subscribe to Redis channel for run {run_id}: {exc}")

    async def unsubscribe(self, run_id: UUID) -> None:
        async with self._lock:
            if run_id in self._subscribers:
                await self._subscribers[run_id].put(None)
                del self._subscribers[run_id]
                del self._sequence_counters[run_id]
                try:
                    if self._pubsub:
                        channel = f"{CHANNEL_PREFIX}{run_id}"
                        await self._pubsub.unsubscribe(channel)
                except Exception as exc:
                    logger.debug(f"Failed to unsubscribe from Redis channel: {exc}")

    async def emit(self, run_id: UUID, event_type: AXEEventType, data: dict[str, Any]) -> None:
        async with self._lock:
            self._sequence_counters[run_id] += 1
            sequence = self._sequence_counters[run_id]
            event = AXEEvent(
                event_type=event_type,
                run_id=run_id,
                sequence=sequence,
                timestamp=datetime.now(timezone.utc).isoformat(),
                data=data,
            )
            
            if run_id in self._subscribers:
                try:
                    self._subscribers[run_id].put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(f"AXE stream queue full for run {run_id}, dropping event")
            else:
                logger.debug(f"No local subscribers for run {run_id}, event will be broadcast via Redis")

        await self._publish_to_redis(event)

    async def _publish_to_redis(self, event: AXEEvent) -> None:
        try:
            redis = await self._get_redis()
            channel = f"{CHANNEL_PREFIX}{event.run_id}"
            message = json.dumps({
                "event_type": event.event_type.value,
                "run_id": str(event.run_id),
                "sequence": event.sequence,
                "timestamp": event.timestamp,
                "data": event.data,
            })
            await redis.publish(channel, message)
        except Exception as exc:
            logger.warning(f"Failed to publish event to Redis: {exc}")

    async def emit_state_changed(
        self,
        run_id: UUID,
        previous_state: AXERunState | None,
        current_state: AXERunState,
        reason: str | None = None,
    ) -> None:
        data = AXERunStateChangedEventData(
            previous_state=previous_state,
            current_state=current_state,
            reason=reason,
        )
        await self.emit(run_id, AXEEventType.RUN_STATE_CHANGED, data.model_dump())

    async def emit_token_stream(self, run_id: UUID, delta: str, finish_reason: str | None = None) -> None:
        data = AXETokenStreamEventData(delta=delta, finish_reason=finish_reason)
        event_type = AXEEventType.TOKEN_COMPLETE if finish_reason else AXEEventType.TOKEN_STREAM
        await self.emit(run_id, event_type, data.model_dump())

    async def emit_run_created(self, run_id: UUID, skill_key: str) -> None:
        await self.emit(run_id, AXEEventType.RUN_CREATED, {"skill_key": skill_key})

    async def emit_run_succeeded(self, run_id: UUID, output: dict[str, Any]) -> None:
        await self.emit(run_id, AXEEventType.RUN_SUCCEEDED, output)

    async def emit_run_failed(self, run_id: UUID, error_code: str, message: str) -> None:
        await self.emit(run_id, AXEEventType.RUN_FAILED, {"code": error_code, "message": message})

    async def shutdown(self) -> None:
        if self._redis_pubsub_task:
            self._redis_pubsub_task.cancel()
            try:
                await self._redis_pubsub_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.close()


_axe_stream_service: AXEStreamService | None = None


def get_axe_stream_service() -> AXEStreamService:
    global _axe_stream_service
    if _axe_stream_service is None:
        _axe_stream_service = AXEStreamService()
    return _axe_stream_service