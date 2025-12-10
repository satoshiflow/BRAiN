from datetime import datetime, timedelta
import json

import redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.redis import get_redis
from app.core.metrics import inc_counter  # abstrakte helper-funktion


async def aggregate_mission_metrics():
    client: redis.Redis = get_redis()
    entries = client.xrevrange("brain.events.missions", count=500)
    for _id, fields in entries:
        try:
            data = json.loads(fields[b"data"].decode("utf-8"))
            status = data.get("status")
            inc_counter("mission_status_total", {"status": status})
        except Exception:
            continue


def register_jobs(scheduler: AsyncIOScheduler):
    scheduler.add_job(
        aggregate_mission_metrics,
        "interval",
        seconds=30,
        id="aggregate_mission_metrics",
    )