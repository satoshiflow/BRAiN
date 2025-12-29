from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...core.security import Principal, get_current_principal
from .models import (
    Mission,
    MissionCreate,
    MissionListResponse,
    MissionLogEntry,
    MissionLogResponse,
    MissionStatsResponse,
    MissionStatus,
)
from .service import (
    append_log_entry,
    create_mission,
    get_log,
    get_mission,
    get_stats,
    list_missions,
    update_status,
)
from .executor import execute_mission_by_id

router = APIRouter(
    prefix="/api/missions",
    tags=["missions"],
)


@router.get("/health")
async def missions_health() -> dict:
    return {"status": "ok"}


@router.get("", response_model=MissionListResponse)
async def list_missions_endpoint(
    status: Optional[MissionStatus] = Query(default=None),
    principal: Principal = Depends(get_current_principal),
) -> MissionListResponse:
    return await list_missions(status=status)


@router.post("", response_model=Mission, status_code=status.HTTP_201_CREATED)
async def create_mission_endpoint(
    payload: MissionCreate,
    principal: Principal = Depends(get_current_principal),
) -> Mission:
    return await create_mission(payload)


@router.get("/{mission_id}", response_model=Mission)
async def get_mission_endpoint(
    mission_id: str,
    principal: Principal = Depends(get_current_principal),
) -> Mission:
    mission = await get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
    return mission


@router.post("/{mission_id}/status", response_model=Mission)
async def update_status_endpoint(
    mission_id: str,
    mission_status: MissionStatus,
    principal: Principal = Depends(get_current_principal),
) -> Mission:
    mission = await update_status(mission_id, mission_status)
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
    if mission_status == MissionStatus.RUNNING:
        asyncio.create_task(execute_mission_by_id(mission.id))
    return mission


@router.post("/{mission_id}/log", status_code=status.HTTP_202_ACCEPTED)
async def append_log_entry_endpoint(
    mission_id: str,
    entry: MissionLogEntry,
    principal: Principal = Depends(get_current_principal),
) -> dict:
    await append_log_entry(mission_id, entry)
    return {"status": "accepted"}


@router.get("/{mission_id}/log", response_model=MissionLogResponse)
async def get_log_endpoint(
    mission_id: str,
    principal: Principal = Depends(get_current_principal),
) -> MissionLogResponse:
    return await get_log(mission_id)


@router.get("/stats/overview", response_model=MissionStatsResponse)
async def get_stats_endpoint(
    principal: Principal = Depends(get_current_principal),
) -> MissionStatsResponse:
    return await get_stats()
@router.post("/{mission_id}/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_mission_endpoint(
    mission_id: str,
    principal: Principal = Depends(get_current_principal),
) -> dict:
    mission = await get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
    asyncio.create_task(execute_mission_by_id(mission.id))
    return {"status": "accepted"}