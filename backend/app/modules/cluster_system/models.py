"""
SQLAlchemy Models for Cluster System

Models:
- Cluster: Main cluster entity with lifecycle management
- ClusterAgent: Agents within a cluster with hierarchy
- ClusterBlueprint: Reusable cluster templates (YAML-based)
- ClusterMetrics: Time-series metrics for monitoring
"""

from sqlalchemy import Column, String, Integer, Float, ForeignKey, JSON, Enum, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import enum


class ClusterType(str, enum.Enum):
    """Type of cluster organization"""
    DEPARTMENT = "department"      # Long-lived department (Marketing, Einkauf)
    PROJECT = "project"            # Project-specific temporary cluster
    TEMPORARY = "temporary"        # One-off task execution
    PERSISTENT = "persistent"      # Always-on cluster


class ClusterStatus(str, enum.Enum):
    """Cluster lifecycle status"""
    PLANNING = "planning"          # Blueprint being created
    SPAWNING = "spawning"          # Agents being instantiated
    ACTIVE = "active"              # Running normally
    SCALING_UP = "scaling_up"      # Growing (adding workers)
    SCALING_DOWN = "scaling_down"  # Shrinking (removing workers)
    HIBERNATED = "hibernated"      # 0 workers, can be reactivated
    DESTROYING = "destroying"      # Being torn down
    DESTROYED = "destroyed"        # Deleted


class AgentRole(str, enum.Enum):
    """Agent role within cluster hierarchy"""
    SUPERVISOR = "supervisor"      # 1 per cluster - department head
    LEAD = "lead"                  # 0-N team leads
    SPECIALIST = "specialist"      # Expert agents (analyst, creator)
    WORKER = "worker"              # Task executors (scalable)


class Cluster(Base):
    """
    Main cluster entity representing a group of agents working together.

    Supports dynamic scaling, hibernation, and blueprint-based creation.
    """
    __tablename__ = "clusters"

    # Identity
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    type = Column(Enum(ClusterType), nullable=False, index=True)
    status = Column(Enum(ClusterStatus), default=ClusterStatus.PLANNING, index=True)

    # Blueprint Reference
    blueprint_id = Column(String, nullable=False, index=True)
    blueprint_version = Column(String, default="1.0.0")

    # Hierarchy (clusters can be nested)
    parent_cluster_id = Column(String, ForeignKey("clusters.id"), nullable=True, index=True)

    # Scaling Configuration
    min_workers = Column(Integer, default=1)
    max_workers = Column(Integer, default=10)
    current_workers = Column(Integer, default=0)
    target_workers = Column(Integer, default=1)

    # Health & Performance
    health_score = Column(Float, default=1.0)  # 0.0 - 1.0
    load_percentage = Column(Float, default=0.0)  # 0.0 - 100.0
    tasks_completed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)

    # Lifecycle Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    hibernated_at = Column(DateTime, nullable=True)
    destroyed_at = Column(DateTime, nullable=True)
    last_active = Column(DateTime, default=datetime.utcnow)

    # Metadata
    description = Column(Text)
    tags = Column(JSON, default=list)  # ["marketing", "content", "q1-2024"]
    config = Column(JSON, default=dict)  # Custom configuration

    # Relationships
    agents = relationship(
        "ClusterAgent",
        back_populates="cluster",
        cascade="all, delete-orphan"
    )
    parent = relationship(
        "Cluster",
        remote_side=[id],
        backref="children"
    )
    metrics = relationship(
        "ClusterMetrics",
        back_populates="cluster",
        cascade="all, delete-orphan"
    )


class ClusterAgent(Base):
    """
    Agent within a cluster with hierarchical relationships.

    Supports Supervisor → Lead → Specialist → Worker hierarchy.
    """
    __tablename__ = "cluster_agents"

    # Identity
    id = Column(String, primary_key=True)
    cluster_id = Column(String, ForeignKey("clusters.id"), nullable=False, index=True)

    # Agent Reference (Genesis Agent ID)
    agent_id = Column(String, nullable=False, index=True)
    role = Column(Enum(AgentRole), nullable=False, index=True)

    # Hierarchy
    supervisor_id = Column(String, ForeignKey("cluster_agents.id"), nullable=True, index=True)

    # Capabilities & Skills
    capabilities = Column(JSON, default=list)  # ["image_generation", "video_editing"]
    skills = Column(JSON, default=list)  # Skill IDs from skills module

    # Status
    status = Column(String, default="active", index=True)  # active, idle, busy, failed, stopped
    health_score = Column(Float, default=1.0)

    # Performance Metrics
    tasks_completed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)
    avg_task_duration = Column(Float, default=0.0)  # seconds
    last_error = Column(String, nullable=True)

    # Lifecycle
    spawned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active = Column(DateTime, default=datetime.utcnow)
    stopped_at = Column(DateTime, nullable=True)

    # Relationships
    cluster = relationship("Cluster", back_populates="agents")
    supervisor = relationship(
        "ClusterAgent",
        remote_side=[id],
        backref="subordinates"
    )


class ClusterBlueprint(Base):
    """
    Reusable cluster template (YAML-based).

    Defines agent hierarchy, scaling rules, and resource requirements.
    """
    __tablename__ = "cluster_blueprints"

    # Identity
    id = Column(String, primary_key=True)  # e.g., "marketing-v1"
    name = Column(String, nullable=False, index=True)
    version = Column(String, default="1.0.0", nullable=False)

    # Blueprint Content
    blueprint_yaml = Column(Text, nullable=False)  # Full YAML content
    manifest_path = Column(String, nullable=True)  # Path to generated manifests

    # Metadata
    description = Column(Text)
    author = Column(String, default="brain-system")
    tags = Column(JSON, default=list)

    # Versioning
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)

    # Usage Statistics
    instances_created = Column(Integer, default=0)
    instances_active = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # Percentage of successful clusters


class ClusterMetrics(Base):
    """
    Time-series metrics for cluster monitoring and auto-scaling decisions.
    """
    __tablename__ = "cluster_metrics"

    # Identity
    id = Column(String, primary_key=True)
    cluster_id = Column(String, ForeignKey("clusters.id"), nullable=False, index=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Resource Metrics
    cpu_usage = Column(Float, default=0.0)     # 0.0 - 100.0
    memory_usage = Column(Float, default=0.0)  # 0.0 - 100.0

    # Performance Metrics
    tasks_per_minute = Column(Float, default=0.0)
    avg_response_time = Column(Float, default=0.0)  # milliseconds
    error_rate = Column(Float, default=0.0)         # 0.0 - 100.0

    # Agent State
    active_agents = Column(Integer, default=0)
    idle_agents = Column(Integer, default=0)
    busy_agents = Column(Integer, default=0)
    failed_agents = Column(Integer, default=0)

    # Queue Metrics (for scaling decisions)
    queue_length = Column(Integer, default=0)
    queue_wait_time = Column(Float, default=0.0)  # seconds

    # Relationships
    cluster = relationship("Cluster", back_populates="metrics")
