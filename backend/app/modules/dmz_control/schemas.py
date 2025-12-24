"""
DMZ Control Module - Data Models

Pydantic models for DMZ control operations.

Version: 1.0.0
Phase: B.3 - DMZ Control Backend
"""

from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DMZStatus(str, Enum):
    """DMZ operational status."""

    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"
    ERROR = "error"


class DMZServiceInfo(BaseModel):
    """Information about a DMZ service."""

    name: str
    status: str  # "running", "exited", etc.
    created: Optional[str] = None
    ports: List[str] = Field(default_factory=list)
    networks: List[str] = Field(default_factory=list)


class DMZStatusResponse(BaseModel):
    """DMZ status response."""

    status: DMZStatus
    services: List[DMZServiceInfo] = Field(default_factory=list)
    service_count: int = 0
    running_count: int = 0
    compose_file: str = "docker-compose.dmz.yml"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message: Optional[str] = None


class DMZControlRequest(BaseModel):
    """DMZ control request (start/stop)."""

    action: str = Field(..., description="Action to perform: start or stop")
    force: bool = Field(
        default=False,
        description="Force action even if state is unexpected"
    )
    timeout: int = Field(
        default=30,
        description="Timeout in seconds for operation"
    )


class DMZControlResponse(BaseModel):
    """DMZ control response."""

    success: bool
    action: str  # "start" or "stop"
    previous_status: DMZStatus
    current_status: DMZStatus
    services_affected: List[str] = Field(default_factory=list)
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict] = None
