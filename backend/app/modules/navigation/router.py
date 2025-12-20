"""
Advanced Navigation API Router

REST API endpoints for social-aware navigation, dynamic obstacle avoidance,
formation control, and context-aware path planning.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional

from .schemas import (
    NavigationGoal,
    PlannedPath,
    Obstacle,
    NavigationStatus,
    SocialNavigationParams,
    FormationNavigationRequest,
    DynamicObstacleAvoidanceRequest,
    AvoidanceManeuver,
    ContextAdaptationRequest,
    AdaptedNavigationParams,
)
from .service import get_navigation_service


router = APIRouter(prefix="/api/navigation", tags=["navigation"])


# ========== Path Planning Endpoints ==========

@router.post("/plan", response_model=PlannedPath)
async def plan_path(goal: NavigationGoal):
    """
    Plan a path to the navigation goal.

    Supports multiple planning modes:
    - direct: Shortest path
    - social_aware: Respects social zones and human comfort
    - formation: Multi-robot coordinated movement
    - dynamic_window: Dynamic obstacle avoidance (DWA)
    - elastic_band: Path smoothing
    - rrt_star: Sampling-based planning
    """
    service = get_navigation_service()
    return service.plan_path(goal)


@router.get("/paths/{path_id}", response_model=PlannedPath)
async def get_planned_path(path_id: str):
    """
    Get a planned path by ID.
    """
    service = get_navigation_service()
    path = service.paths.get(path_id)

    if not path:
        raise HTTPException(status_code=404, detail=f"Path {path_id} not found")

    return path


@router.get("/goals/{goal_id}", response_model=NavigationGoal)
async def get_navigation_goal(goal_id: str):
    """
    Get a navigation goal by ID.
    """
    service = get_navigation_service()
    goal = service.goals.get(goal_id)

    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")

    return goal


# ========== Dynamic Obstacle Avoidance Endpoints ==========

@router.post("/avoid", response_model=AvoidanceManeuver)
async def compute_avoidance_maneuver(request: DynamicObstacleAvoidanceRequest):
    """
    Compute avoidance maneuver for dynamic obstacles.

    Uses specified avoidance strategy:
    - stop_and_wait: Stop until obstacle clears
    - replan: Replan entire path
    - local_deform: Local path deformation
    - social_force: Social force model (human-aware)

    Returns recommended velocity commands and safety metrics.
    """
    service = get_navigation_service()
    return service.compute_avoidance_maneuver(request)


@router.post("/obstacles/{robot_id}", status_code=200)
async def update_obstacles(robot_id: str, obstacles: List[Obstacle]):
    """
    Update detected obstacles for a robot.

    Used to inform the navigation system about current obstacles.
    """
    service = get_navigation_service()
    service.update_obstacles(robot_id, obstacles)
    return {"status": "ok", "robot_id": robot_id, "obstacle_count": len(obstacles)}


@router.get("/obstacles/{robot_id}", response_model=List[Obstacle])
async def get_obstacles(robot_id: str):
    """
    Get current obstacles for a robot.
    """
    service = get_navigation_service()
    return service.get_obstacles(robot_id)


# ========== Formation Navigation Endpoints ==========

@router.post("/formation", response_model=Dict[str, PlannedPath])
async def plan_formation_navigation(request: FormationNavigationRequest):
    """
    Plan coordinated paths for formation navigation.

    Returns individual paths for each robot in the formation.
    Supports formation types: line, column, wedge, circle, grid.
    """
    service = get_navigation_service()
    return service.plan_formation_navigation(request)


# ========== Context Adaptation Endpoints ==========

@router.post("/adapt-context", response_model=AdaptedNavigationParams)
async def adapt_to_context(request: ContextAdaptationRequest):
    """
    Adapt navigation parameters to environmental context.

    Automatically adjusts:
    - Maximum velocity
    - Social distance
    - Navigation behavior
    - Safety margins

    Based on context (hospital, warehouse, mall, street, etc.)
    and environmental factors (crowd density, humans detected, etc.)
    """
    service = get_navigation_service()
    return service.adapt_to_context(request)


# ========== Status Management Endpoints ==========

@router.post("/status", response_model=NavigationStatus)
async def update_navigation_status(status: NavigationStatus):
    """
    Update robot navigation status.

    Used to report current position, velocity, and navigation state.
    """
    service = get_navigation_service()
    service.update_status(status)
    return status


@router.get("/status/{robot_id}", response_model=NavigationStatus)
async def get_navigation_status(robot_id: str):
    """
    Get current navigation status for a robot.
    """
    service = get_navigation_service()
    status = service.get_status(robot_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"No status found for robot {robot_id}")

    return status


# ========== Social Navigation Parameters ==========

@router.get("/social-params", response_model=SocialNavigationParams)
async def get_social_params():
    """
    Get current social navigation parameters.
    """
    service = get_navigation_service()
    return service.social_params


@router.put("/social-params", response_model=SocialNavigationParams)
async def update_social_params(params: SocialNavigationParams):
    """
    Update social navigation parameters.

    Allows customization of:
    - Personal space zones
    - Behavior weights (efficiency, safety, comfort)
    - Approach angles
    - Crowd handling parameters
    """
    service = get_navigation_service()
    service.social_params = params
    return params


# ========== Module Info ==========

@router.get("/info")
async def get_navigation_info():
    """
    Get advanced navigation module information.
    """
    service = get_navigation_service()

    return {
        "module": "Advanced Navigation",
        "version": "1.0.0",
        "description": "Social-aware navigation, dynamic obstacle avoidance, and context-aware path planning",
        "features": [
            "Social-aware path planning (respects personal space)",
            "Dynamic obstacle avoidance (social force model)",
            "Formation navigation (multi-robot coordination)",
            "Context adaptation (hospital, warehouse, mall, street, etc.)",
            "Human-robot interaction during navigation",
            "Predictive collision avoidance"
        ],
        "planning_modes": [
            "direct",
            "social_aware",
            "formation",
            "dynamic_window",
            "elastic_band",
            "rrt_star"
        ],
        "avoidance_strategies": [
            "stop_and_wait",
            "replan",
            "local_deform",
            "social_force"
        ],
        "supported_contexts": [
            "hospital",
            "warehouse",
            "office",
            "street",
            "mall",
            "factory",
            "home",
            "outdoor"
        ],
        "endpoints": {
            "plan": "/api/navigation/plan",
            "avoid": "/api/navigation/avoid",
            "formation": "/api/navigation/formation",
            "adapt_context": "/api/navigation/adapt-context",
            "status": "/api/navigation/status",
            "obstacles": "/api/navigation/obstacles",
            "social_params": "/api/navigation/social-params"
        },
        "statistics": {
            "active_goals": len(service.goals),
            "planned_paths": len(service.paths),
            "tracked_robots": len(service.status),
            "total_obstacles": sum(len(obs) for obs in service.obstacles.values())
        }
    }
