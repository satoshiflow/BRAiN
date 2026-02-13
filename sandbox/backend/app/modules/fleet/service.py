"""
Fleet Service

Business logic for fleet management and multi-robot coordination.
"""

import time
from typing import Dict, List, Optional
from datetime import datetime

from app.modules.fleet.schemas import (
    FleetInfo,
    FleetCreateRequest,
    FleetUpdateRequest,
    RobotInfo,
    RobotRegisterRequest,
    RobotUpdateRequest,
    RobotState,
    FleetTask,
    TaskAssignRequest,
    TaskAssignmentResponse,
    TaskPriority,
    CoordinationZone,
    ZoneEntryRequest,
    ZoneEntryResponse,
    FleetStatistics,
)


class FleetService:
    """
    Fleet management service.

    Handles:
    - Fleet CRUD operations
    - Robot registration and status tracking
    - Task assignment and load balancing
    - Coordination zone management
    - Fleet-wide statistics
    """

    def __init__(self):
        # In-memory storage (in production: use database)
        self.fleets: Dict[str, FleetInfo] = {}
        self.robots: Dict[str, RobotInfo] = {}  # robot_id -> RobotInfo
        self.tasks: Dict[str, FleetTask] = {}  # task_id -> FleetTask
        self.zones: Dict[str, CoordinationZone] = {}  # zone_id -> CoordinationZone

        # Statistics
        self.total_tasks_assigned = 0
        self.total_tasks_completed = 0

    # ========================================================================
    # Fleet Management
    # ========================================================================

    def create_fleet(self, request: FleetCreateRequest) -> FleetInfo:
        """Create a new fleet."""
        if request.fleet_id in self.fleets:
            raise ValueError(f"Fleet {request.fleet_id} already exists")

        fleet = FleetInfo(
            fleet_id=request.fleet_id,
            name=request.name,
            description=request.description,
            total_robots=0,
            online_robots=0,
            idle_robots=0,
            busy_robots=0,
            total_tasks_queued=0,
            tasks_in_progress=0,
            tasks_completed_today=0,
            average_battery_percentage=0.0,
            robots_in_error=0,
        )

        self.fleets[request.fleet_id] = fleet
        return fleet

    def get_fleet(self, fleet_id: str) -> Optional[FleetInfo]:
        """Get fleet information."""
        return self.fleets.get(fleet_id)

    def list_fleets(self) -> List[FleetInfo]:
        """List all fleets."""
        return list(self.fleets.values())

    def update_fleet(self, fleet_id: str, request: FleetUpdateRequest) -> FleetInfo:
        """Update fleet information."""
        fleet = self.fleets.get(fleet_id)
        if not fleet:
            raise ValueError(f"Fleet {fleet_id} not found")

        if request.name is not None:
            fleet.name = request.name
        if request.description is not None:
            fleet.description = request.description

        fleet.last_updated = datetime.utcnow()
        return fleet

    def delete_fleet(self, fleet_id: str) -> bool:
        """Delete a fleet."""
        if fleet_id not in self.fleets:
            return False

        # Remove all robots from fleet
        robots_to_remove = [
            robot_id for robot_id, robot in self.robots.items()
            if robot.fleet_id == fleet_id
        ]
        for robot_id in robots_to_remove:
            del self.robots[robot_id]

        del self.fleets[fleet_id]
        return True

    # ========================================================================
    # Robot Management
    # ========================================================================

    def register_robot(self, request: RobotRegisterRequest) -> RobotInfo:
        """Register a robot to a fleet."""
        if request.robot_id in self.robots:
            raise ValueError(f"Robot {request.robot_id} already registered")

        if request.fleet_id not in self.fleets:
            raise ValueError(f"Fleet {request.fleet_id} does not exist")

        robot = RobotInfo(
            robot_id=request.robot_id,
            fleet_id=request.fleet_id,
            state=RobotState.IDLE,
            model=request.model,
            capabilities=request.capabilities,
            battery_percentage=100.0,
            position=request.initial_position,
            uptime_hours=0.0,
            tasks_completed_today=0,
        )

        self.robots[request.robot_id] = robot

        # Update fleet statistics
        self._update_fleet_stats(request.fleet_id)

        return robot

    def get_robot(self, robot_id: str) -> Optional[RobotInfo]:
        """Get robot information."""
        return self.robots.get(robot_id)

    def list_robots(self, fleet_id: Optional[str] = None) -> List[RobotInfo]:
        """List robots, optionally filtered by fleet."""
        robots = list(self.robots.values())

        if fleet_id:
            robots = [r for r in robots if r.fleet_id == fleet_id]

        return robots

    def update_robot_status(
        self,
        robot_id: str,
        request: RobotUpdateRequest,
    ) -> RobotInfo:
        """Update robot status."""
        robot = self.robots.get(robot_id)
        if not robot:
            raise ValueError(f"Robot {robot_id} not found")

        if request.state is not None:
            robot.state = request.state
        if request.battery_percentage is not None:
            robot.battery_percentage = request.battery_percentage
        if request.position is not None:
            robot.position = request.position
        if request.current_task_id is not None:
            robot.current_task_id = request.current_task_id

        robot.last_seen = datetime.utcnow()

        # Update fleet statistics
        self._update_fleet_stats(robot.fleet_id)

        return robot

    def unregister_robot(self, robot_id: str) -> bool:
        """Unregister a robot from its fleet."""
        robot = self.robots.get(robot_id)
        if not robot:
            return False

        fleet_id = robot.fleet_id
        del self.robots[robot_id]

        # Update fleet statistics
        self._update_fleet_stats(fleet_id)

        return True

    # ========================================================================
    # Task Assignment
    # ========================================================================

    def assign_task(
        self,
        fleet_id: str,
        request: TaskAssignRequest,
    ) -> TaskAssignmentResponse:
        """Assign a task to the optimal robot in the fleet."""
        fleet = self.fleets.get(fleet_id)
        if not fleet:
            raise ValueError(f"Fleet {fleet_id} not found")

        # Create task
        task_id = f"TASK-{fleet_id}-{int(time.time() * 1000)}"
        task = FleetTask(
            task_id=task_id,
            fleet_id=fleet_id,
            task_type=request.task_type,
            description=request.description,
            priority=request.priority,
            required_capabilities=request.required_capabilities,
            target_position=request.target_position,
            payload=request.payload,
            status="queued",
        )

        # Find optimal robot
        optimal_robot = self._find_optimal_robot(fleet_id, task)
        if not optimal_robot:
            raise ValueError(f"No suitable robot available in fleet {fleet_id}")

        # Assign task
        task.assigned_robot_id = optimal_robot.robot_id
        task.assigned_at = datetime.utcnow()
        task.status = "assigned"

        self.tasks[task_id] = task

        # Update robot status
        optimal_robot.current_task_id = task_id
        optimal_robot.state = RobotState.BUSY

        # Update statistics
        self.total_tasks_assigned += 1
        self._update_fleet_stats(fleet_id)

        return TaskAssignmentResponse(
            task_id=task_id,
            assigned_robot_id=optimal_robot.robot_id,
            fleet_id=fleet_id,
            estimated_start_time_s=0.0,  # Immediate start
            assignment_score=0.85,  # Placeholder score
        )

    def _find_optimal_robot(
        self,
        fleet_id: str,
        task: FleetTask,
    ) -> Optional[RobotInfo]:
        """
        Find the optimal robot for a task.

        Scoring factors:
        - Robot state (idle > busy)
        - Capability match
        - Battery level
        - Distance to task location (if known)
        """
        candidates = [
            robot for robot in self.robots.values()
            if robot.fleet_id == fleet_id and robot.state == RobotState.IDLE
        ]

        if not candidates:
            return None

        # Filter by capabilities
        if task.required_capabilities:
            candidates = [
                robot for robot in candidates
                if all(cap in robot.capabilities for cap in task.required_capabilities)
            ]

        if not candidates:
            return None

        # Score candidates (simple: highest battery)
        best_robot = max(candidates, key=lambda r: r.battery_percentage)
        return best_robot

    def get_task(self, task_id: str) -> Optional[FleetTask]:
        """Get task information."""
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        fleet_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[FleetTask]:
        """List tasks, optionally filtered by fleet and/or status."""
        tasks = list(self.tasks.values())

        if fleet_id:
            tasks = [t for t in tasks if t.fleet_id == fleet_id]

        if status:
            tasks = [t for t in tasks if t.status == status]

        return tasks

    def complete_task(self, task_id: str, success: bool = True) -> FleetTask:
        """Mark a task as completed."""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.status = "completed" if success else "failed"
        task.completed_at = datetime.utcnow()

        # Update robot status
        if task.assigned_robot_id:
            robot = self.robots.get(task.assigned_robot_id)
            if robot:
                robot.current_task_id = None
                robot.state = RobotState.IDLE
                if success:
                    robot.tasks_completed_today += 1

        # Update statistics
        if success:
            self.total_tasks_completed += 1
        self._update_fleet_stats(task.fleet_id)

        return task

    # ========================================================================
    # Coordination Zones
    # ========================================================================

    def create_zone(
        self,
        zone_id: str,
        zone_type: str,
        max_concurrent_robots: int = 1,
        coordinates: Optional[Dict] = None,
    ) -> CoordinationZone:
        """Create a coordination zone."""
        zone = CoordinationZone(
            zone_id=zone_id,
            zone_type=zone_type,
            max_concurrent_robots=max_concurrent_robots,
            coordinates=coordinates or {},
        )

        self.zones[zone_id] = zone
        return zone

    def request_zone_entry(
        self,
        request: ZoneEntryRequest,
    ) -> ZoneEntryResponse:
        """Request permission for robot to enter coordination zone."""
        zone = self.zones.get(request.zone_id)
        if not zone:
            # Zone doesn't exist - allow entry
            return ZoneEntryResponse(
                permission=True,
                wait_time_s=0.0,
                reason="Zone not restricted",
            )

        # Check if zone is at capacity
        if len(zone.current_robots) < zone.max_concurrent_robots:
            # Grant permission
            zone.current_robots.append(request.robot_id)
            return ZoneEntryResponse(
                permission=True,
                wait_time_s=0.0,
                reason="Zone available",
            )

        else:
            # Zone full - add to waiting queue
            if request.robot_id not in zone.waiting_robots:
                zone.waiting_robots.append(request.robot_id)

            position = zone.waiting_robots.index(request.robot_id) + 1
            estimated_wait = position * 30.0  # 30s per robot ahead

            return ZoneEntryResponse(
                permission=False,
                wait_time_s=estimated_wait,
                reason=f"Zone at capacity ({zone.max_concurrent_robots} robots)",
                position_in_queue=position,
            )

    def exit_zone(self, zone_id: str, robot_id: str) -> bool:
        """Robot exits coordination zone."""
        zone = self.zones.get(zone_id)
        if not zone:
            return False

        if robot_id in zone.current_robots:
            zone.current_robots.remove(robot_id)

            # Move next waiting robot into zone
            if zone.waiting_robots:
                next_robot = zone.waiting_robots.pop(0)
                zone.current_robots.append(next_robot)

            return True

        return False

    # ========================================================================
    # Statistics
    # ========================================================================

    def get_fleet_statistics(self, fleet_id: str) -> FleetStatistics:
        """Get comprehensive fleet statistics."""
        fleet = self.fleets.get(fleet_id)
        if not fleet:
            raise ValueError(f"Fleet {fleet_id} not found")

        fleet_robots = [r for r in self.robots.values() if r.fleet_id == fleet_id]
        fleet_tasks = [t for t in self.tasks.values() if t.fleet_id == fleet_id]

        # Robots by state
        robots_by_state = {}
        for state in RobotState:
            count = len([r for r in fleet_robots if r.state == state])
            if count > 0:
                robots_by_state[state.value] = count

        # Task statistics
        tasks_today = len(fleet_tasks)
        tasks_completed = len([t for t in fleet_tasks if t.status == "completed"])
        tasks_failed = len([t for t in fleet_tasks if t.status == "failed"])

        # Calculate averages
        avg_battery = (
            sum(r.battery_percentage for r in fleet_robots) / len(fleet_robots)
            if fleet_robots else 0.0
        )

        task_success_rate = tasks_completed / tasks_today if tasks_today > 0 else 0.0

        # Fleet utilization (percentage of robots busy)
        utilization = (fleet.busy_robots / fleet.total_robots * 100.0) if fleet.total_robots > 0 else 0.0

        return FleetStatistics(
            fleet_id=fleet_id,
            total_robots=len(fleet_robots),
            robots_by_state=robots_by_state,
            average_battery=avg_battery,
            total_tasks_today=tasks_today,
            tasks_completed_today=tasks_completed,
            tasks_failed_today=tasks_failed,
            average_task_duration_s=0.0,  # Would need task timing data
            fleet_utilization_percentage=utilization,
            task_success_rate=task_success_rate,
            active_zones=len([z for z in self.zones.values() if z.current_robots]),
            coordination_conflicts_today=0,  # Would need conflict tracking
        )

    def _update_fleet_stats(self, fleet_id: str):
        """Update fleet statistics after changes."""
        fleet = self.fleets.get(fleet_id)
        if not fleet:
            return

        fleet_robots = [r for r in self.robots.values() if r.fleet_id == fleet_id]

        fleet.total_robots = len(fleet_robots)
        fleet.online_robots = len([r for r in fleet_robots if r.state in [RobotState.IDLE, RobotState.BUSY]])
        fleet.idle_robots = len([r for r in fleet_robots if r.state == RobotState.IDLE])
        fleet.busy_robots = len([r for r in fleet_robots if r.state == RobotState.BUSY])
        fleet.robots_in_error = len([r for r in fleet_robots if r.state == RobotState.ERROR])

        if fleet_robots:
            fleet.average_battery_percentage = sum(r.battery_percentage for r in fleet_robots) / len(fleet_robots)
        else:
            fleet.average_battery_percentage = 0.0

        # Task counts
        fleet_tasks = [t for t in self.tasks.values() if t.fleet_id == fleet_id]
        fleet.total_tasks_queued = len([t for t in fleet_tasks if t.status == "queued"])
        fleet.tasks_in_progress = len([t for t in fleet_tasks if t.status in ["assigned", "in_progress"]])
        fleet.tasks_completed_today = len([t for t in fleet_tasks if t.status == "completed"])

        fleet.last_updated = datetime.utcnow()


# ============================================================================
# Singleton
# ============================================================================

_fleet_service: Optional[FleetService] = None


def get_fleet_service() -> FleetService:
    """Get singleton FleetService instance."""
    global _fleet_service
    if _fleet_service is None:
        _fleet_service = FleetService()
    return _fleet_service
