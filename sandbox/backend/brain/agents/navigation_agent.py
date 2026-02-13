"""
navigation_agent.py

NavigationAgent - RYR Robot Navigation and Path Planning Agent

Responsibilities:
- Path planning and route optimization
- Real-time navigation and obstacle avoidance
- Localization and mapping (SLAM)
- Goal reaching and waypoint navigation
- Dynamic replanning on obstacles
- Navigation performance monitoring

Integrates with:
- SafetyAgent for collision avoidance
- FleetAgent for coordinated movement
- KARMA system for navigation metrics
- Foundation layer for movement validation
"""

from __future__ import annotations

import asyncio
import math
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from brain.agents.base_agent import BaseAgent, AgentConfig, AgentResult, LLMClient


class NavigationState(str, Enum):
    """Navigation states."""
    IDLE = "idle"
    PLANNING = "planning"
    NAVIGATING = "navigating"
    REPLANNING = "replanning"
    STUCK = "stuck"
    GOAL_REACHED = "goal_reached"
    FAILED = "failed"


class PathPlanningAlgorithm(str, Enum):
    """Available path planning algorithms."""
    A_STAR = "a_star"
    DIJKSTRA = "dijkstra"
    RRT = "rrt"
    RRT_STAR = "rrt_star"
    TEB = "teb"  # Timed Elastic Band


@dataclass
class Coordinates:
    """2D coordinates with optional orientation."""
    x: float
    y: float
    theta: Optional[float] = None  # Orientation in radians

    def distance_to(self, other: 'Coordinates') -> float:
        """Calculate Euclidean distance to another coordinate."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class Waypoint:
    """Navigation waypoint."""
    waypoint_id: str
    coordinates: Coordinates
    tolerance_m: float = 0.2  # How close robot needs to get
    max_speed_ms: Optional[float] = None


@dataclass
class Path:
    """Planned navigation path."""
    path_id: str
    start: Coordinates
    goal: Coordinates
    waypoints: List[Waypoint]
    total_distance_m: float
    estimated_duration_s: float
    algorithm_used: PathPlanningAlgorithm
    created_at: datetime


@dataclass
class NavigationStatus:
    """Current navigation status of a robot."""
    robot_id: str
    state: NavigationState
    current_position: Coordinates
    goal_position: Optional[Coordinates]
    active_path: Optional[Path]
    distance_to_goal_m: Optional[float]
    next_waypoint: Optional[Waypoint]
    replanning_count: int
    stuck_duration_s: float
    last_update: datetime


@dataclass
class ObstacleDetection:
    """Detected obstacle."""
    obstacle_id: str
    coordinates: Coordinates
    size_estimate_m: float
    velocity_ms: Optional[Tuple[float, float]] = None  # (vx, vy) if moving
    detected_at: datetime


class NavigationAgent(BaseAgent):
    """
    Navigation and Path Planning Agent for RYR robots.

    Handles:
    - Global path planning
    - Local obstacle avoidance
    - Localization (position estimation)
    - Dynamic replanning
    - Goal reaching
    - Performance optimization
    """

    def __init__(self, llm_client: LLMClient, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="NavigationAgent",
                role="NAVIGATION_PLANNER",
                model="phi3",
                system_prompt=self._get_system_prompt(),
                temperature=0.4,  # Moderate temperature for creative path planning
                max_tokens=2048,
                tools=[
                    "plan_path",
                    "navigate_to_goal",
                    "avoid_obstacle",
                    "update_position",
                    "replan_path",
                ],
                permissions=["NAV_PLAN", "NAV_EXECUTE", "MAP_UPDATE"],
            )

        super().__init__(llm_client, config)

        # Navigation state
        self.robot_status: Dict[str, NavigationStatus] = {}
        self.obstacle_map: Dict[str, ObstacleDetection] = {}
        self.planned_paths: Dict[str, Path] = {}  # path_id -> Path

        # Navigation parameters
        self.DEFAULT_SPEED_MS = 1.0
        self.MAX_SPEED_MS = 2.5
        self.GOAL_TOLERANCE_M = 0.2
        self.STUCK_THRESHOLD_S = 30.0
        self.REPLAN_DISTANCE_THRESHOLD_M = 5.0

        # Register tools
        self.register_tool("plan_path", self.plan_path)
        self.register_tool("navigate_to_goal", self.navigate_to_goal)
        self.register_tool("avoid_obstacle", self.avoid_obstacle)
        self.register_tool("update_position", self.update_position)
        self.register_tool("replan_path", self.replan_path)
        self.register_tool("get_navigation_status", self.get_navigation_status)

    @staticmethod
    def _get_system_prompt() -> str:
        return """You are the Navigation Agent for the BRAiN RYR system.

Your responsibilities:
1. Plan optimal paths from start to goal positions
2. Navigate robots safely through dynamic environments
3. Detect and avoid obstacles in real-time
4. Replan paths when obstacles block the route
5. Ensure accurate localization and positioning
6. Optimize navigation efficiency

Navigation principles:
1. SAFETY FIRST: Never plan paths that risk collisions
2. EFFICIENCY: Minimize distance and time while maintaining safety
3. ADAPTABILITY: Replan when environment changes
4. PRECISION: Reach goals within tolerance limits
5. SMOOTHNESS: Generate smooth, executable paths

Path planning considerations:
- Shortest path vs. safest path trade-off
- Dynamic obstacles (humans, other robots)
- Static obstacles (walls, furniture, equipment)
- Speed limits in different zones
- Robot kinematic constraints
- Energy consumption optimization

Obstacle avoidance strategies:
- Stop and wait if obstacle is temporary
- Replan if obstacle blocks path significantly
- Local avoidance for small deviations
- Request fleet coordination for shared spaces

When stuck:
- Try alternative maneuvers
- Request human assistance if timeout exceeded
- Never force through obstacles

All navigation decisions must respect safety constraints."""

    # ========================================================================
    # Path Planning Tools
    # ========================================================================

    def plan_path(
        self,
        robot_id: str,
        start: Coordinates,
        goal: Coordinates,
        algorithm: PathPlanningAlgorithm = PathPlanningAlgorithm.A_STAR,
    ) -> Path:
        """
        Plan a path from start to goal position.

        Args:
            robot_id: Robot for which to plan
            start: Starting coordinates
            goal: Goal coordinates
            algorithm: Path planning algorithm to use

        Returns:
            Planned Path with waypoints
        """
        self.logger.info(
            "Planning path for robot %s from (%.2f, %.2f) to (%.2f, %.2f) using %s",
            robot_id,
            start.x,
            start.y,
            goal.x,
            goal.y,
            algorithm,
        )

        # Simple straight-line path (in production, use actual path planning algorithms)
        distance = start.distance_to(goal)

        # Generate waypoints (divide path into segments)
        num_waypoints = max(2, int(distance / 2.0))  # Waypoint every 2m
        waypoints = []

        for i in range(1, num_waypoints + 1):
            t = i / num_waypoints
            wp_x = start.x + t * (goal.x - start.x)
            wp_y = start.y + t * (goal.y - start.y)

            waypoint = Waypoint(
                waypoint_id=f"WP-{i}",
                coordinates=Coordinates(x=wp_x, y=wp_y),
                tolerance_m=self.GOAL_TOLERANCE_M,
            )
            waypoints.append(waypoint)

        # Estimate duration (distance / speed)
        estimated_duration = distance / self.DEFAULT_SPEED_MS

        path = Path(
            path_id=f"PATH-{robot_id}-{datetime.utcnow().timestamp()}",
            start=start,
            goal=goal,
            waypoints=waypoints,
            total_distance_m=distance,
            estimated_duration_s=estimated_duration,
            algorithm_used=algorithm,
            created_at=datetime.utcnow(),
        )

        self.planned_paths[path.path_id] = path
        self.logger.info(
            "Path planned: %s (%.2fm, ~%.1fs, %d waypoints)",
            path.path_id,
            distance,
            estimated_duration,
            len(waypoints),
        )

        return path

    def navigate_to_goal(
        self,
        robot_id: str,
        goal: Coordinates,
    ) -> Dict[str, Any]:
        """
        Start navigation to goal position.

        High-level command that:
        1. Plans path from current position to goal
        2. Starts navigation execution
        3. Monitors progress

        Args:
            robot_id: Robot to navigate
            goal: Destination coordinates

        Returns:
            Navigation start confirmation
        """
        status = self.robot_status.get(robot_id)
        if not status:
            return {
                "success": False,
                "error": f"Robot {robot_id} status not available",
            }

        # Plan path
        path = self.plan_path(
            robot_id=robot_id,
            start=status.current_position,
            goal=goal,
        )

        # Update status
        status.state = NavigationState.NAVIGATING
        status.goal_position = goal
        status.active_path = path
        status.distance_to_goal_m = status.current_position.distance_to(goal)
        status.next_waypoint = path.waypoints[0] if path.waypoints else None
        status.last_update = datetime.utcnow()

        self.logger.info(
            "Robot %s starting navigation to goal (%.2f, %.2f)",
            robot_id,
            goal.x,
            goal.y,
        )

        return {
            "success": True,
            "robot_id": robot_id,
            "path_id": path.path_id,
            "distance_m": path.total_distance_m,
            "estimated_duration_s": path.estimated_duration_s,
            "waypoints_count": len(path.waypoints),
        }

    def avoid_obstacle(
        self,
        robot_id: str,
        obstacle: ObstacleDetection,
    ) -> Dict[str, Any]:
        """
        Perform local obstacle avoidance maneuver.

        Strategies:
        - If obstacle is far: continue on path
        - If obstacle is close: slow down and prepare to stop
        - If obstacle is blocking: stop and replan

        Args:
            robot_id: Robot to maneuver
            obstacle: Detected obstacle

        Returns:
            Avoidance action taken
        """
        status = self.robot_status.get(robot_id)
        if not status:
            return {"action": "none", "error": "Robot status not available"}

        # Calculate distance to obstacle
        distance = status.current_position.distance_to(obstacle.coordinates)

        # Determine action based on distance
        if distance > 5.0:
            # Far away - monitor but continue
            return {
                "action": "monitor",
                "reason": f"Obstacle {distance:.1f}m away - monitoring",
            }

        elif distance > 2.0:
            # Getting close - slow down
            return {
                "action": "slow_down",
                "reason": f"Obstacle {distance:.1f}m away - reducing speed",
                "recommended_speed_ms": self.DEFAULT_SPEED_MS * 0.5,
            }

        elif distance > 0.5:
            # Very close - prepare to stop
            return {
                "action": "prepare_stop",
                "reason": f"Obstacle {distance:.1f}m away - preparing to stop",
                "recommended_speed_ms": self.DEFAULT_SPEED_MS * 0.2,
            }

        else:
            # Too close - stop immediately
            self.logger.warning(
                "Robot %s: Obstacle too close (%.2fm) - stopping",
                robot_id,
                distance,
            )
            status.state = NavigationState.STUCK
            return {
                "action": "emergency_stop",
                "reason": f"Obstacle {distance:.1f}m away - STOP",
                "recommended_speed_ms": 0.0,
                "requires_replan": True,
            }

    def update_position(
        self,
        robot_id: str,
        position: Coordinates,
    ) -> NavigationStatus:
        """
        Update robot's current position (localization update).

        Args:
            robot_id: Robot ID
            position: New position estimate

        Returns:
            Updated NavigationStatus
        """
        status = self.robot_status.get(robot_id)
        if not status:
            # Initialize new status
            status = NavigationStatus(
                robot_id=robot_id,
                state=NavigationState.IDLE,
                current_position=position,
                goal_position=None,
                active_path=None,
                distance_to_goal_m=None,
                next_waypoint=None,
                replanning_count=0,
                stuck_duration_s=0.0,
                last_update=datetime.utcnow(),
            )
            self.robot_status[robot_id] = status

        # Update position
        old_position = status.current_position
        status.current_position = position
        status.last_update = datetime.utcnow()

        # Update distance to goal if navigating
        if status.goal_position:
            status.distance_to_goal_m = position.distance_to(status.goal_position)

            # Check if goal reached
            if status.distance_to_goal_m <= self.GOAL_TOLERANCE_M:
                self.logger.info(
                    "Robot %s reached goal! (distance: %.3fm)",
                    robot_id,
                    status.distance_to_goal_m,
                )
                status.state = NavigationState.GOAL_REACHED

        self.logger.debug(
            "Robot %s position updated: (%.2f, %.2f) -> (%.2f, %.2f)",
            robot_id,
            old_position.x,
            old_position.y,
            position.x,
            position.y,
        )

        return status

    def replan_path(
        self,
        robot_id: str,
        reason: str = "obstacle_detected",
    ) -> Optional[Path]:
        """
        Replan path to goal due to changed conditions.

        Args:
            robot_id: Robot that needs replanning
            reason: Reason for replanning

        Returns:
            New Path or None if replanning failed
        """
        status = self.robot_status.get(robot_id)
        if not status or not status.goal_position:
            self.logger.error("Cannot replan: no active navigation for robot %s", robot_id)
            return None

        self.logger.info(
            "Replanning path for robot %s (reason: %s)",
            robot_id,
            reason,
        )

        status.state = NavigationState.REPLANNING
        status.replanning_count += 1

        # Plan new path from current position to goal
        new_path = self.plan_path(
            robot_id=robot_id,
            start=status.current_position,
            goal=status.goal_position,
            algorithm=PathPlanningAlgorithm.A_STAR,
        )

        # Update status
        status.active_path = new_path
        status.next_waypoint = new_path.waypoints[0] if new_path.waypoints else None
        status.state = NavigationState.NAVIGATING

        self.logger.info(
            "Replanning complete for robot %s (attempt #%d)",
            robot_id,
            status.replanning_count,
        )

        return new_path

    def get_navigation_status(self, robot_id: str) -> Optional[NavigationStatus]:
        """
        Get current navigation status of a robot.

        Returns:
            NavigationStatus or None if robot not found
        """
        return self.robot_status.get(robot_id)

    # ========================================================================
    # Agent Interface
    # ========================================================================

    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Execute navigation task.

        Examples:
        - "Plan path for robot ROBOT-001 to coordinates (10.5, 20.3)"
        - "Navigate robot ROBOT-002 to goal (5.0, 15.0)"
        - "Avoid obstacle detected at (7.2, 8.4) for robot ROBOT-003"
        - "Replan path for robot ROBOT-004 due to blocked route"

        The LLM will analyze the task and select appropriate navigation tools.
        """
        self.logger.info("NavigationAgent executing task: %s", task)

        try:
            # Add context about navigation tools
            tools_context = f"""
Available navigation tools:
- plan_path(robot_id, start, goal, algorithm)
- navigate_to_goal(robot_id, goal)
- avoid_obstacle(robot_id, obstacle)
- update_position(robot_id, position)
- replan_path(robot_id, reason)
- get_navigation_status(robot_id)

Robots under navigation: {list(self.robot_status.keys())}
Active paths: {len(self.planned_paths)}
Known obstacles: {len(self.obstacle_map)}

Context: {context or 'None'}

Planning algorithms available: {[a.value for a in PathPlanningAlgorithm]}
"""

            # Call LLM with navigation context
            llm_response = await self.call_llm(
                user_message=task,
                extra_messages=[{"role": "system", "content": tools_context}],
            )

            # In production, would parse LLM response and execute navigation tools
            return {
                "id": f"nav_task_{id(task)}",
                "success": True,
                "message": llm_response,
                "raw_response": llm_response,
                "used_tools": [],
                "meta": {
                    "agent_name": "NavigationAgent",
                    "task": task,
                },
            }

        except Exception as e:
            self.logger.exception("NavigationAgent task failed: %s", e)
            return {
                "id": f"nav_task_{id(task)}",
                "success": False,
                "message": "Navigation task failed",
                "error": str(e),
                "used_tools": [],
                "meta": {
                    "agent_name": "NavigationAgent",
                    "task": task,
                },
            }
