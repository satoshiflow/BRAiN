"""
Deployment Status Schemas

Pydantic models for deployment status information.
"""

from typing import Dict, Literal, Optional
from pydantic import BaseModel, Field


class GitInfo(BaseModel):
    """Git repository information"""
    branch: str = Field(..., description="Current git branch")
    commit: str = Field(..., description="Current commit hash (short)")
    dirty: bool = Field(..., description="Whether working directory has uncommitted changes")
    behind_remote: int = Field(default=0, description="Number of commits behind remote")


class ContainerInfo(BaseModel):
    """Docker container information"""
    status: Literal["running", "stopped", "not_found", "unknown"] = Field(
        ..., description="Container status"
    )
    container_id: Optional[str] = Field(None, description="Container ID (short)")


class ConnectivityResult(BaseModel):
    """Service connectivity test result"""
    status: Literal["reachable", "unreachable", "error"] = Field(
        ..., description="Connectivity status"
    )
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if unreachable")


class ServiceInfo(BaseModel):
    """External service connectivity information"""
    api: ConnectivityResult = Field(..., description="Backend API connectivity")
    postgres: ConnectivityResult = Field(..., description="PostgreSQL connectivity")
    redis: ConnectivityResult = Field(..., description="Redis connectivity")
    qdrant: ConnectivityResult = Field(..., description="Qdrant connectivity")


class DeploymentStatus(BaseModel):
    """Complete deployment status"""
    git: GitInfo = Field(..., description="Git repository information")
    containers: Dict[str, ContainerInfo] = Field(
        default_factory=dict, description="Docker container statuses"
    )
    services: ServiceInfo = Field(..., description="Service connectivity tests")
    environment: str = Field(..., description="Current environment (development/staging/production)")
    version: str = Field(..., description="Application version")
