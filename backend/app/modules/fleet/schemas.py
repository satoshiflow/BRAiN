"""
Fleet Module Schemas

Pydantic models for fleet management and multi-robot coordination.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# ROBOT STATUS
# ============================================================================

class RobotState(str, Enum):
    """Robot operational states."""
    ONLINE = "online"
    OFFLINE = "offline"
    IDLE = "idle"
    BUSY = "busy"
    CHARGING = "charging"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class RobotCapability(str, Enum):
    """Standard robot capabilities."""
    NAVIGATION = "navigation"
    MANIPULATION = "manipulation"
    GRIPPER = "gripper"
    CAMERA = "camera"
    LIDAR = "lidar"
    ULTRASONIC = "ultrasonic"
    CHARGING_AUTO = "charging_auto"


class RobotInfo(BaseModel):
    """Robot information and current status."""
    robot_id: str = Field(description="Unique robot identifier")
    fleet_id: str = Field(description="Fleet this robot belongs to")
    state: RobotState = Field(description="Current operational state")

    # Hardware info
    model: str = Field(description="Robot model/type")
    capabilities: List[RobotCapability] = Field(default_factory=list)

    # Status
    battery_percentage: float = Field(ge=0.0, le=100.0)
    position: Optional[Dict[str, float]] = Field(default=None, description="Current position {x, y, theta}")
    current_task_id: Optional[str] = None

    # Metrics
    uptime_hours: float = Field(ge=0.0)
    tasks_completed_today: int = Field(ge=0)

    # Timestamps
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    registered_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# FLEET MANAGEMENT
# ============================================================================

class FleetInfo(BaseModel):
    """Fleet information and status."""
    fleet_id: str = Field(description="Unique fleet identifier")
    name: str = Field(description="Fleet name")
    description: str = ""

    # Fleet composition
    total_robots: int = Field(ge=0)
    online_robots: int = Field(ge=0)
    idle_robots: int = Field(ge=0)
    busy_robots: int = Field(ge=0)

    # Performance
    total_tasks_queued: int = Field(ge=0)
    tasks_in_progress: int = Field(ge=0)
    tasks_completed_today: int = Field(ge=0)

    # Health
    average_battery_percentage: float = Field(ge=0.0, le=100.0)
    robots_in_error: int = Field(ge=0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class FleetCreateRequest(BaseModel):
    """Request to create a new fleet."""
    fleet_id: str = Field(description="Unique fleet identifier")
    name: str = Field(description="Fleet name")
    description: str = ""
    max_robots: int = Field(default=50, ge=1, le=1000, description="Maximum robots in fleet")


class FleetUpdateRequest(BaseModel):
    """Request to update fleet information."""
    name: Optional[str] = None
    description: Optional[str] = None
    max_robots: Optional[int] = Field(default=None, ge=1, le=1000)


# ============================================================================
# ROBOT REGISTRATION
# ============================================================================

class RobotRegisterRequest(BaseModel):
    """Request to register a robot to a fleet."""
    robot_id: str
    fleet_id: str
    model: str
    capabilities: List[RobotCapability] = Field(default_factory=list)
    initial_position: Optional[Dict[str, float]] = None


class RobotUpdateRequest(BaseModel):
    """Request to update robot status."""
    state: Optional[RobotState] = None
    battery_percentage: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    position: Optional[Dict[str, float]] = None
    current_task_id: Optional[str] = None


# ============================================================================
# TASK ASSIGNMENT
# ============================================================================

class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 10
    NORMAL = 50
    HIGH = 80
    CRITICAL = 100


class FleetTask(BaseModel):
    """Fleet task definition."""
    task_id: str
    fleet_id: str
    task_type: str = Field(description="Type of task (e.g., 'pick', 'transport', 'inspect')")
    description: str
    priority: TaskPriority

    # Assignment
    assigned_robot_id: Optional[str] = None
    assigned_at: Optional[datetime] = None

    # Requirements
    required_capabilities: List[RobotCapability] = Field(default_factory=list)
    target_position: Optional[Dict[str, float]] = None

    # Status
    status: str = Field(default="queued")  # queued, assigned, in_progress, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Metadata
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskAssignRequest(BaseModel):
    """Request to assign a task to the fleet."""
    task_type: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    required_capabilities: List[RobotCapability] = Field(default_factory=list)
    target_position: Optional[Dict[str, float]] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class TaskAssignmentResponse(BaseModel):
    """Response after task assignment."""
    task_id: str
    assigned_robot_id: str
    fleet_id: str
    estimated_start_time_s: float
    assignment_score: float = Field(description="Quality of assignment (0-1)")


# ============================================================================
# COORDINATION
# ============================================================================

class CoordinationZone(BaseModel):
    """Zone requiring coordination between robots."""
    zone_id: str
    zone_type: str = Field(description="Type of zone (e.g., 'corridor', 'intersection', 'doorway')")
    max_concurrent_robots: int = Field(default=1, ge=1)
    current_robots: List[str] = Field(default_factory=list, description="Robot IDs currently in zone")
    waiting_robots: List[str] = Field(default_factory=list, description="Robot IDs waiting for zone")
    coordinates: Dict[str, float] = Field(default_factory=dict, description="Zone boundaries")


class ZoneEntryRequest(BaseModel):
    """Request for robot to enter coordination zone."""
    robot_id: str
    zone_id: str
    estimated_duration_s: float = Field(ge=0.0, description="How long robot needs the zone")


class ZoneEntryResponse(BaseModel):
    """Response to zone entry request."""
    permission: bool
    wait_time_s: float = Field(ge=0.0)
    reason: str
    position_in_queue: Optional[int] = None


# ============================================================================
# FLEET STATISTICS
# ============================================================================

class FleetStatistics(BaseModel):
    """Comprehensive fleet performance statistics."""
    fleet_id: str

    # Robot statistics
    total_robots: int
    robots_by_state: Dict[str, int]
    average_battery: float

    # Task statistics
    total_tasks_today: int
    tasks_completed_today: int
    tasks_failed_today: int
    average_task_duration_s: float

    # Performance
    fleet_utilization_percentage: float = Field(ge=0.0, le=100.0)
    task_success_rate: float = Field(ge=0.0, le=1.0)

    # Coordination
    active_zones: int
    coordination_conflicts_today: int

    # Timestamp
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# API RESPONSES
# ============================================================================

class FleetListResponse(BaseModel):
    """Response with list of fleets."""
    total: int
    fleets: List[FleetInfo]


class RobotListResponse(BaseModel):
    """Response with list of robots."""
    total: int
    robots: List[RobotInfo]


class TaskListResponse(BaseModel):
    """Response with list of tasks."""
    total: int
    tasks: List[FleetTask]
