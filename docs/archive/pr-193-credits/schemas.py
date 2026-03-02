from pydantic import BaseModel
from datetime import datetime
from typing import Any

class CreditsHealth(BaseModel):
    status: str
    timestamp: datetime

class CreditsInfo(BaseModel):
    name: str
    version: str
    config: dict[str, Any] | None = None
