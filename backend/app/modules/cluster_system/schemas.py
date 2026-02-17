"""
Pydantic Schemas for Cluster System API

Request/Response models for:
- Cluster CRUD operations
- Blueprint management
- Scaling operations
- Metrics queries
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ===== ENUMS (matching SQLAlchemy) =====

class ClusterType(str, Enum):
    DEPARTMENT = "department"
    PROJECT = "project"
    TEMPORARY = "temporary"
    PERSISTENT = "persistent"


class ClusterStatus(str, Enum):
    PLANNING = "planning"
    SPAWNING = "spawning"
    ACTIVE = "active"
    SCALING_UP = "scaling_up"
    SCALING_DOWN = "scaling_down"
    HIBERNATED = "hibernated"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"


class AgentRole(str, Enum):
    SUPERVISOR = "supervisor"
    LEAD = "lead"
    SPECIALIST = "specialist"
    WORKER = "worker"


# ===== CLUSTER SCHEMAS =====

class ClusterCreate(BaseModel):
    """Request to create cluster from blueprint"""
    blueprint_id: str = Field(..., min_length=3, max_length=100)
    name: str = Field(..., min_length=3, max_length=200)
    type: Optional[ClusterType] = ClusterType.DEPARTMENT

    # Optional overrides
    min_workers: Optional[int] = Field(None, ge=0, le=100)
    max_workers: Optional[int] = Field(None, ge=1, le=1000)
    target_workers: Optional[int] = Field(None, ge=0, le=1000)

    description: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator('name')
    @classmethod
    def name_alphanumeric(cls, v: str) -> str:
        if not v.replace('-', '').replace('_', '').replace(' ', '').isalnum():
            raise ValueError('name must contain only alphanumeric characters, spaces, hyphens, underscores')
        return v


class ClusterUpdate(BaseModel):
    """Update cluster configuration"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    min_workers: Optional[int] = Field(None, ge=0, le=100)
    max_workers: Optional[int] = Field(None, ge=1, le=1000)
    config: Optional[Dict[str, Any]] = None


class ClusterScale(BaseModel):
    """Manual scaling request"""
    target_workers: int = Field(..., ge=0, le=1000)
    reason: Optional[str] = None


class ClusterResponse(BaseModel):
    """Cluster details response"""
    id: str
    name: str
    type: ClusterType
    status: ClusterStatus
    blueprint_id: str
    blueprint_version: str

    # Scaling
    min_workers: int
    max_workers: int
    current_workers: int
    target_workers: int

    # Health
    health_score: float
    load_percentage: float
    tasks_completed: int
    tasks_failed: int

    # Timestamps
    created_at: datetime
    started_at: Optional[datetime]
    hibernated_at: Optional[datetime]
    last_active: datetime

    # Metadata
    description: Optional[str]
    tags: List[str]

    # Relationships (optional, loaded separately)
    agents_count: Optional[int] = None

    model_config = {"from_attributes": True}


class ClusterListResponse(BaseModel):
    """List of clusters with pagination"""
    clusters: List[ClusterResponse]
    total: int
    page: int
    page_size: int


# ===== CLUSTER AGENT SCHEMAS =====

class ClusterAgentCreate(BaseModel):
    """Add agent to cluster"""
    agent_id: str
    role: AgentRole
    supervisor_id: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)


class ClusterAgentResponse(BaseModel):
    """Agent within cluster"""
    id: str
    cluster_id: str
    agent_id: str
    role: AgentRole
    supervisor_id: Optional[str]

    capabilities: List[str]
    skills: List[str]

    status: str
    health_score: float

    tasks_completed: int
    tasks_failed: int
    avg_task_duration: float

    spawned_at: datetime
    last_active: datetime

    model_config = {"from_attributes": True}


# ===== BLUEPRINT SCHEMAS =====

class BlueprintCreate(BaseModel):
    """Upload new blueprint"""
    id: str = Field(..., pattern=r'^[a-z0-9-]+$')
    name: str = Field(..., min_length=3, max_length=200)
    version: str = Field(default="1.0.0", pattern=r'^\d+\.\d+\.\d+$')
    blueprint_yaml: str = Field(..., min_length=10)
    description: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)


class BlueprintUpdate(BaseModel):
    """Update blueprint (creates new version)"""
    name: Optional[str] = None
    blueprint_yaml: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class BlueprintResponse(BaseModel):
    """Blueprint details"""
    id: str
    name: str
    version: str
    description: Optional[str]
    author: str
    tags: List[str]

    created_at: datetime
    updated_at: datetime
    is_active: bool

    instances_created: int
    instances_active: int
    success_rate: float

    # Optional: full YAML (can be large)
    blueprint_yaml: Optional[str] = None

    model_config = {"from_attributes": True}


# ===== METRICS SCHEMAS =====

class ClusterMetricsResponse(BaseModel):
    """Cluster metrics snapshot"""
    id: str
    cluster_id: str
    timestamp: datetime

    # Resources
    cpu_usage: float
    memory_usage: float

    # Performance
    tasks_per_minute: float
    avg_response_time: float
    error_rate: float

    # Agents
    active_agents: int
    idle_agents: int
    busy_agents: int
    failed_agents: int

    # Queue
    queue_length: int
    queue_wait_time: float

    model_config = {"from_attributes": True}


class MetricsQuery(BaseModel):
    """Query metrics with time range"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)


# ===== HIERARCHY SCHEMA =====

class ClusterHierarchyResponse(BaseModel):
    """Recursive agent hierarchy"""
    agent: ClusterAgentResponse
    subordinates: List['ClusterHierarchyResponse'] = Field(default_factory=list)

# Enable forward references
ClusterHierarchyResponse.model_rebuild()
