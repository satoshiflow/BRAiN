"""
System Event Models

Tracks system events, health checks, deployments, errors, etc.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class EventSeverity(str, Enum):
    """Event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SystemEventCreate(BaseModel):
    """Create a new system event"""
    event_type: str = Field(..., min_length=1, max_length=50, description="Type of event (e.g., 'health_check', 'deployment')")
    severity: EventSeverity = Field(..., description="Event severity level")
    message: str = Field(..., min_length=1, description="Event message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional event details (JSON)")
    source: Optional[str] = Field(None, max_length=100, description="Event source (e.g., 'backend', 'nginx')")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "event_type": "health_check",
                    "severity": "info",
                    "message": "System health check passed",
                    "details": {"postgres": "connected", "redis": "connected"},
                    "source": "backend"
                }
            ]
        }
    }


class SystemEventUpdate(BaseModel):
    """Update an existing system event"""
    event_type: Optional[str] = Field(None, min_length=1, max_length=50)
    severity: Optional[EventSeverity] = None
    message: Optional[str] = Field(None, min_length=1)
    details: Optional[Dict[str, Any]] = None
    source: Optional[str] = Field(None, max_length=100)


class SystemEventResponse(BaseModel):
    """System event response model"""
    id: int
    event_type: str
    severity: EventSeverity
    message: str
    details: Optional[Dict[str, Any]]
    source: Optional[str]
    timestamp: datetime
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "event_type": "health_check",
                    "severity": "info",
                    "message": "System health check passed",
                    "details": {"postgres": "connected", "redis": "connected"},
                    "source": "backend",
                    "timestamp": "2026-01-02T22:00:00Z",
                    "created_at": "2026-01-02T22:00:00Z"
                }
            ]
        }
    }


class EventStats(BaseModel):
    """Event statistics"""
    total_events: int
    events_by_severity: Dict[str, int]
    events_by_type: Dict[str, int]
    recent_events: int  # Last 24 hours
    last_event_timestamp: Optional[datetime]
