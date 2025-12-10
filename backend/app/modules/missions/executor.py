from __future__ import annotations

import asyncio

from .models import Mission, MissionLogEntry, MissionStatus
from .service import append_log_entry, get_mission, update_status


class MissionExecutor:
    async def execute(self, mission: Mission) -> None:
        start_entry = MissionLogEntry(
            level="info",
            message="Mission execution started",
            data={"mission_id": mission.id, "name": mission.name},
        )
        await append_log_entry(mission.id, start_entry)

        await asyncio.sleep(1.0)
        step_entry = MissionLogEntry(
            level="info",
            message="Mission executing step 1",
            data={"payload": mission.data},
        )
        await append_log_entry(mission.id, step_entry)

        await asyncio.sleep(1.0)
        finish_entry = MissionLogEntry(
            level="info",
            message="Mission execution finished",
            data={"result": {"status": "OK"}},
        )
        await append_log_entry(mission.id, finish_entry)

        await update_status(mission.id, MissionStatus.COMPLETED)


_executor_instance: MissionExecutor | None = None


def get_executor() -> MissionExecutor:
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = MissionExecutor()
    return _executor_instance


async def execute_mission_by_id(mission_id: str) -> None:
    mission = await get_mission(mission_id)
    if not mission:
        return
    executor = get_executor()
    await executor.execute(mission)
