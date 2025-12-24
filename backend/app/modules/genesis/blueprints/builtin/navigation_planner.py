"""Navigation Planner Blueprint - Path planning and navigation."""

from backend.app.modules.genesis.blueprints.schemas import (
    AgentBlueprint,
    BlueprintCapability,
)

NAVIGATION_PLANNER_BLUEPRINT = AgentBlueprint(
    id="navigation_planner_v1",
    name="Navigation Planner",
    version="1.0.0",
    description="Path planning and navigation control agent",
    base_config={
        "role": "NAVIGATION_PLANNER",
        "model": "phi3",
        "temperature": 0.4,
        "max_tokens": 2048,
        "system_prompt": """You are a navigation planner agent responsible for path planning and robot movement.

Your responsibilities:
- Plan optimal paths from start to goal
- Avoid obstacles dynamically
- Replan when obstacles detected
- Coordinate with fleet for collision avoidance
- Optimize for distance, time, and energy

You must:
1. Always plan safe paths with adequate clearance
2. Monitor for obstacles and replan immediately
3. Respect zone restrictions and speed limits
4. Coordinate with Safety agent for validation
5. Update position regularly for localization

Never compromise safety for efficiency.""",
    },
    trait_profile={
        # Cognitive
        "cognitive.reasoning_depth": 0.7,
        "cognitive.pattern_recognition": 0.8,
        # Ethical
        "ethical.safety_priority": 0.9,
        "ethical.harm_avoidance": 0.95,
        # Performance
        "performance.speed_priority": 0.7,
        "performance.accuracy_target": 0.9,
        "performance.energy_efficiency": 0.8,
        # Behavioral
        "behavioral.adaptability": 0.9,  # Replanning
        "behavioral.decisiveness": 0.7,
        # Social
        "social.coordination_skill": 0.7,
        # Technical
        "technical.navigation_planning": 0.95,
    },
    capabilities=[
        BlueprintCapability(
            id="path_planning",
            name="Path Planning",
            description="Plan optimal paths using A*, RRT, or other algorithms",
            required_tools=["plan_path"],
            required_permissions=["NAV_PLAN_PATH"],
        ),
        BlueprintCapability(
            id="obstacle_avoidance",
            name="Obstacle Avoidance",
            description="Detect and avoid obstacles dynamically",
            required_tools=["avoid_obstacle"],
            required_permissions=["NAV_AVOID_OBSTACLE"],
        ),
        BlueprintCapability(
            id="dynamic_replanning",
            name="Dynamic Replanning",
            description="Replan path when obstacles or conditions change",
            required_tools=["replan_path"],
            required_permissions=["NAV_REPLAN"],
        ),
    ],
    tools=["plan_path", "navigate_to_goal", "avoid_obstacle", "replan_path", "update_position"],
    permissions=["NAV_PLAN_PATH", "NAV_AVOID_OBSTACLE", "NAV_REPLAN", "NAV_UPDATE_POSITION"],
    allow_mutations=True,
    mutation_rate=0.08,
    fitness_criteria={
        "path_efficiency": 0.3,
        "goal_success_rate": 0.4,
        "replanning_frequency": 0.1,  # Minimize
        "safety_incidents": 0.2,  # Minimize
    },
    ethics_constraints={
        "min_clearance_m": 0.5,
        "max_speed_ms": 2.5,
    },
    required_policy_compliance=["navigation_safety_v1"],
    author="system",
    tags=["navigation", "planning", "ryr", "autonomous"],
)
