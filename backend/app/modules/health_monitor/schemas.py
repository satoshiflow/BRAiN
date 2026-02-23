"""
Health Monitor System - Pydantic Schemas
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheckCreate(BaseModel):
    """Schema for registering a service to monitor"""
    service_name: str = Field(..., min_length=1, max_length=100)
    service_type: str = Field(default="internal", description="internal, external, database, cache")
    check_interval_seconds: int = Field(default=60, ge=10, le=3600)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthCheckResponse(BaseModel):
    """Schema for health check response"""
    id: UUID = Field(...)
    service_name: str = Field(...)
    service_type: str = Field(...)
    status: HealthStatus = Field(...)
    previous_status: Optional[HealthStatus] = Field(default=None)
    last_check_at: Optional[datetime] = Field(default=None)
    response_time_ms: Optional[float] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    check_output: Optional[str] = Field(default=None)
    total_checks: int = Field(default=0)
    failed_checks: int = Field(default=0)
    consecutive_failures: int = Field(default=0)
    uptime_percentage: Optional[float] = Field(default=None)
    
    class Config:
        from_attributes = True


class HealthStatusSummary(BaseModel):
    """Overall health status summary"""
    overall_status: HealthStatus = Field(...)
    total_services: int = Field(...)
    healthy_count: int = Field(...)
    degraded_count: int = Field(...)
    unhealthy_count: int = Field(...)
    unknown_count: int = Field(...)
    services: List[HealthCheckResponse] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class HealthCheckResult(BaseModel):
    """Result of a health check execution"""
    service_name: str = Field(...)
    status: HealthStatus = Field(...)
    response_time_ms: Optional[float] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    output: Optional[str] = Field(default=None)
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class HealthHistoryEntry(BaseModel):
    """Single health history entry"""
    id: UUID = Field(...)
    service_name: str = Field(...)
    status: HealthStatus = Field(...)
    response_time_ms: Optional[float] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    checked_at: datetime = Field(...)
    
    class Config:
        from_attributes = True


class HealthHistoryResponse(BaseModel):
    """Response for health history query"""
    service_name: str = Field(...)
    entries: List[HealthHistoryEntry] = Field(default_factory=list)
    total: int = Field(...)


# Event Schemas
class HealthEvent(BaseModel):
    """Base health event"""
    event_type: str = Field(...)
    service_name: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)


class HealthCheckEvent(HealthEvent):
    """Periodic health check completed"""
    event_type: str = "health.check"
    status: HealthStatus = Field(...)
    response_time_ms: Optional[float] = Field(default=None)


class HealthDegradedEvent(HealthEvent):
    """Service health degraded"""
    event_type: str = "health.degraded"
    previous_status: HealthStatus = Field(...)
    error_message: Optional[str] = Field(default=None)


class HealthRecoveredEvent(HealthEvent):
    """Service recovered"""
    event_type: str = "health.recovered"
    previous_status: HealthStatus = Field(...)
    downtime_seconds: Optional[float] = Field(default=None)


class HealthCriticalEvent(HealthEvent):
    """Service critical/unhealthy"""
    event_type: str = "health.critical"
    error_message: str = Field(...)
    consecutive_failures: int = Field(...)
