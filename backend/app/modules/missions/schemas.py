from pydantic import BaseModel
from datetime import datetime
from typing import Any

class Mission(BaseModel):
    id: str
    name: str
    status: str
    created_at: datetime

class MissionsHealth(BaseModel):
    status: str
    timestamp: datetime

class MissionsInfo(BaseModel):
    name: str
    version: str
    config: dict[str, Any] | None = None

class MissionsOverview(BaseModel):
    missions: list[Mission]
