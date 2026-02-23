"""
Health Monitor System - Database Models

Service health monitoring and status tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum, Float, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class HealthStatus(str, Enum):
    """Health check status levels"""
    HEALTHY = "healthy"       # All checks passing
    DEGRADED = "degraded"     # Some issues but functional
    UNHEALTHY = "unhealthy"   # Critical issues
    UNKNOWN = "unknown"       # No data yet


class HealthCheckModel(Base):
    """
    Health check database model.
    
    Stores status and metrics for monitored services.
    """
    __tablename__ = "health_checks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = Column(String(100), unique=True, nullable=False, index=True)
    service_type = Column(String(50), nullable=False, default="internal")
    
    # Status
    status = Column(SQLEnum(HealthStatus), nullable=False, default=HealthStatus.UNKNOWN)
    previous_status = Column(SQLEnum(HealthStatus), nullable=True)
    status_changed_at = Column(DateTime, nullable=True)
    
    # Check Results
    last_check_at = Column(DateTime, nullable=True)
    next_check_at = Column(DateTime, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    check_interval_seconds = Column(Integer, nullable=False, default=60)
    
    # Details
    error_message = Column(Text, nullable=True)
    check_output = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=False, default=dict)
    
    # Stats
    total_checks = Column(Integer, nullable=False, default=0)
    failed_checks = Column(Integer, nullable=False, default=0)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    consecutive_successes = Column(Integer, nullable=False, default=0)
    
    # Uptime tracking
    uptime_percentage = Column(Float, nullable=True)
    last_healthy_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self) -> str:
        return f"<HealthCheck(service={self.service_name}, status={self.status})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "service_name": self.service_name,
            "service_type": self.service_type,
            "status": self.status.value if isinstance(self.status, HealthStatus) else self.status,
            "previous_status": self.previous_status.value if isinstance(self.previous_status, HealthStatus) else self.previous_status,
            "last_check_at": self.last_check_at.isoformat() if self.last_check_at else None,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "check_output": self.check_output,
            "metadata": self.metadata,
            "total_checks": self.total_checks,
            "failed_checks": self.failed_checks,
            "consecutive_failures": self.consecutive_failures,
            "uptime_percentage": self.uptime_percentage,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class HealthCheckHistoryModel(Base):
    """
    Historical health check results.
    
    Stores recent check history for trend analysis.
    """
    __tablename__ = "health_check_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = Column(String(100), nullable=False, index=True)
    status = Column(SQLEnum(HealthStatus), nullable=False)
    response_time_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    checked_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "service_name": self.service_name,
            "status": self.status.value if isinstance(self.status, HealthStatus) else self.status,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }
