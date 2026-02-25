"""
Fleet Module - SQLAlchemy ORM Models

Database models for fleet management, robot coordination, and task assignment.
"""

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import Column, String, DateTime, Float, Integer, JSON, ForeignKey, Index, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class FleetORM(Base):
    """Fleet management model."""

    __tablename__ = "fleets"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fleet_id = Column(String(100), unique=True, nullable=False, index=True)
    owner_id = Column(String(100), nullable=False, index=True)  # For ownership verification

    # Fleet information
    name = Column(String(255), nullable=False)
    description = Column(String(5000), nullable=True)
    max_robots = Column(Integer, default=50, nullable=False)

    # Statistics (denormalized for performance)
    total_robots = Column(Integer, default=0, nullable=False)
    online_robots = Column(Integer, default=0, nullable=False)
    idle_robots = Column(Integer, default=0, nullable=False)
    busy_robots = Column(Integer, default=0, nullable=False)
    robots_in_error = Column(Integer, default=0, nullable=False)
    average_battery_percentage = Column(Float, default=0.0, nullable=False)

    # Task statistics
    total_tasks_queued = Column(Integer, default=0, nullable=False)
    tasks_in_progress = Column(Integer, default=0, nullable=False)
    tasks_completed_today = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    robots = relationship("RobotORM", back_populates="fleet", cascade="all, delete-orphan")
    tasks = relationship("FleetTaskORM", back_populates="fleet", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FleetORM(fleet_id={self.fleet_id}, owner={self.owner_id})>"


class RobotORM(Base):
    """Robot model - represents a single robot in a fleet."""

    __tablename__ = "robots"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    robot_id = Column(String(100), unique=True, nullable=False, index=True)

    # Fleet relationship
    fleet_id = Column(String(100), ForeignKey("fleets.fleet_id"), nullable=False, index=True)

    # Robot information
    model = Column(String(100), nullable=False)
    capabilities = Column(JSON, default=list, nullable=False)  # List of capabilities

    # Status
    state = Column(
        String(50),
        nullable=False,
        index=True,
        default="idle",
    )  # online, offline, idle, busy, charging, error, maintenance

    battery_percentage = Column(Float, default=100.0, nullable=False)
    position = Column(JSON, nullable=True)  # {x, y, theta}
    current_task_id = Column(String(100), nullable=True)

    # Metrics
    uptime_hours = Column(Float, default=0.0, nullable=False)
    tasks_completed_today = Column(Integer, default=0, nullable=False)

    # Timestamps
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    fleet = relationship("FleetORM", back_populates="robots")

    def __repr__(self):
        return f"<RobotORM(robot_id={self.robot_id}, fleet={self.fleet_id}, state={self.state})>"


class FleetTaskORM(Base):
    """Fleet task model - represents a task assigned to robots in a fleet."""

    __tablename__ = "fleet_tasks"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(100), unique=True, nullable=False, index=True)

    # Fleet relationship
    fleet_id = Column(String(100), ForeignKey("fleets.fleet_id"), nullable=False, index=True)

    # Task information
    task_type = Column(String(100), nullable=False)
    description = Column(String(5000), nullable=False)
    priority = Column(Integer, default=50, nullable=False)

    # Assignment
    assigned_robot_id = Column(String(100), nullable=True, index=True)

    # Requirements
    required_capabilities = Column(JSON, default=list, nullable=False)  # List of required capabilities
    target_position = Column(JSON, nullable=True)  # {x, y, theta}

    # Status
    status = Column(
        String(50),
        nullable=False,
        index=True,
        default="queued",
    )  # queued, assigned, in_progress, completed, failed

    # Metadata
    payload = Column(JSON, default=dict, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    fleet = relationship("FleetORM", back_populates="tasks")

    def __repr__(self):
        return f"<FleetTaskORM(task_id={self.task_id}, status={self.status})>"


class CoordinationZoneORM(Base):
    """Coordination zone model - represents a zone where robots need coordination."""

    __tablename__ = "coordination_zones"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(String(100), unique=True, nullable=False, index=True)

    # Zone information
    zone_type = Column(String(100), nullable=False)
    max_concurrent_robots = Column(Integer, default=1, nullable=False)
    coordinates = Column(JSON, default=dict, nullable=False)  # Zone boundaries

    # Robot lists
    current_robots = Column(JSON, default=list, nullable=False)  # List of robot IDs currently in zone
    waiting_robots = Column(JSON, default=list, nullable=False)  # List of robot IDs waiting

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CoordinationZoneORM(zone_id={self.zone_id}, type={self.zone_type})>"


# Create indexes for common query patterns
Index("ix_fleets_owner_id", FleetORM.owner_id)
Index("ix_robots_fleet_state", RobotORM.fleet_id, RobotORM.state)
Index("ix_tasks_fleet_status", FleetTaskORM.fleet_id, FleetTaskORM.status)
Index("ix_tasks_robot_id", FleetTaskORM.assigned_robot_id)
