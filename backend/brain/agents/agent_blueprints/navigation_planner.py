"""
Navigation Planner Agent Blueprint

Pre-configured blueprint for NavigationAgent instantiation.
"""

BLUEPRINT = {
    "id": "navigation_planner",
    "name": "Navigation Planner",
    "role": "NAVIGATION_PLANNER",
    "model": "phi3",
    "description": "Path planning, obstacle avoidance, and autonomous navigation for robots",
    "version": "1.0.0",

    "capabilities": [
        "path_planning",
        "obstacle_avoidance",
        "localization",
        "goal_reaching",
        "dynamic_replanning",
    ],

    "tools": [
        "plan_path",
        "navigate_to_goal",
        "avoid_obstacle",
        "update_position",
        "replan_path",
        "get_navigation_status",
    ],

    "permissions": [
        "NAV_PLAN",
        "NAV_EXECUTE",
        "MAP_UPDATE",
    ],

    "config": {
        "temperature": 0.4,  # Moderate for creative path planning
        "max_tokens": 2048,
        "system_prompt": """You are the Navigation Agent for the BRAiN RYR system.

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

All navigation decisions must respect safety constraints.""",
    },

    "algorithms": {
        "global_planning": ["a_star", "dijkstra", "rrt", "rrt_star"],
        "local_planning": ["dwa", "teb", "mpc"],
        "localization": ["amcl", "ekf", "particle_filter"],
    },

    "integration": {
        "modules": ["karma", "foundation", "policy"],
        "agents": ["safety_agent", "fleet_agent"],
        "external": ["ros2_nav2", "slam_toolbox", "move_base"],
    },

    "parameters": {
        "default_speed_ms": 1.0,
        "max_speed_ms": 2.5,
        "goal_tolerance_m": 0.2,
        "stuck_threshold_s": 30.0,
        "replan_distance_threshold_m": 5.0,
    },

    "metrics": {
        "path_planning_success_rate": "float",
        "path_deviation_avg_m": "float",
        "replanning_frequency": "float",
        "goal_reach_accuracy_m": "float",
        "navigation_time_efficiency": "float",
        "stuck_recovery_time_avg_s": "float",
        "localization_accuracy_m": "float",
    },

    "usage_example": """
# Initialize NavigationAgent
from backend.brain.agents.navigation_agent import NavigationAgent, Coordinates
from backend.brain.agents.llm_client import get_llm_client

agent = NavigationAgent(llm_client=get_llm_client())

# Plan a path
path = agent.plan_path(
    robot_id="ROBOT_001",
    start=Coordinates(x=0.0, y=0.0, theta=0.0),
    goal=Coordinates(x=10.0, y=15.0, theta=1.57),
    algorithm="a_star",
)

# Navigate to goal
result = agent.navigate_to_goal(
    robot_id="ROBOT_001",
    goal=Coordinates(x=10.0, y=15.0),
)

# Update position (from localization system)
agent.update_position(
    robot_id="ROBOT_001",
    position=Coordinates(x=2.3, y=4.5, theta=0.8),
)

# Replan if obstacle detected
new_path = agent.replan_path(
    robot_id="ROBOT_001",
    reason="obstacle_detected",
)
""",
}
