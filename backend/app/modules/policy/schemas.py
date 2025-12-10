from pydantic import BaseModel
from datetime import datetime
from typing import Any

class PolicyHealth(BaseModel):
    status: str
    timestamp: datetime

class PolicyInfo(BaseModel):
    name: str
    version: str
    config: dict[str, Any] | None = None
