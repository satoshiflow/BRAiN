from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List

from pydantic import BaseModel


class ImmuneSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ImmuneEventType(str, Enum):
    POLICY_VIOLATION = "POLICY_VIOLATION"
    ERROR_SPIKE = "ERROR_SPIKE"
    SELF_HEALING_ACTION = "SELF_HEALING_ACTION"


class ImmuneEvent(BaseModel):
    id: Optional[int] = None
    agent_id: Optional[str] = None
    module: Optional[str] = None
    severity: ImmuneSeverity
    type: ImmuneEventType
    message: str
    meta: Dict[str, Any] = {}
    created_at: datetime


class ImmuneHealthSummary(BaseModel):
    active_issues: int
    critical_issues: int
    last_events: List[ImmuneEvent]