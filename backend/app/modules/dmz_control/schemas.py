"""
DMZ Control Schemas

Data models for DMZ gateway status and control.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class DMZContainer(BaseModel):
    """DMZ container status."""

    name: str
    status: Literal["running", "stopped", "restarting", "unknown"] = "unknown"
    health: Optional[Literal["healthy", "unhealthy", "starting"]] = None
    ports: List[str] = Field(default_factory=list)


class DMZStatus(BaseModel):
    """DMZ gateway status."""

    enabled: bool = False
    running: bool = False
    containers: List[DMZContainer] = Field(default_factory=list)
    error: Optional[str] = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class DMZControlResponse(BaseModel):
    """Response from DMZ control operations."""

    success: bool
    message: str
    status: Optional[DMZStatus] = None
