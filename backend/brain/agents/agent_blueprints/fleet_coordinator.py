"""
Fleet Coordinator Agent Blueprint

Pre-configured blueprint for FleetAgent instantiation.
"""

BLUEPRINT = {
    "id": "fleet_coordinator",
    "name": "Fleet Coordinator",
    "role": "FLEET_COORDINATOR",
    "model": "phi3",
    "description": "Manages multi-robot fleet coordination, task distribution, and load balancing",
    "version": "1.0.0",

    "capabilities": [
        "task_distribution",
        "load_balancing",
        "collision_coordination",
        "resource_optimization",
        "fleet_monitoring",
    ],

    "tools": [
        "assign_task",
        "balance_load",
        "coordinate_movement",
        "optimize_routes",
        "get_fleet_status",
    ],

    "permissions": [
        "FLEET_MANAGE",
        "TASK_ASSIGN",
        "ROBOT_CONTROL",
    ],

    "config": {
        "temperature": 0.3,
        "max_tokens": 2048,
        "system_prompt": """You are the Fleet Coordination Agent for the BRAiN RYR system.

Your responsibilities:
1. Distribute tasks efficiently across the robot fleet
2. Balance workload to minimize idle time
3. Coordinate robot movements to avoid collisions
4. Optimize fleet-wide resource usage
5. Monitor and report fleet performance

Decision principles:
- Safety first: Never compromise safety for efficiency
- Load balancing: Distribute tasks evenly across available robots
- Minimize idle time: Keep robots productively engaged
- Collision avoidance: Coordinate movement in shared spaces
- Resource optimization: Maximize fleet throughput

Always validate decisions through the Foundation and Policy layers.""",
    },

    "integration": {
        "modules": ["missions", "karma", "policy", "foundation"],
        "agents": ["safety_agent", "navigation_agent"],
        "external": ["ros2_nav", "fleet_manager"],
    },

    "metrics": {
        "task_distribution_efficiency": "float",
        "collision_avoidance_rate": "float",
        "average_idle_time_percentage": "float",
        "cooperative_tasks_completed": "int",
    },

    "usage_example": """
# Initialize FleetAgent
from backend.brain.agents.fleet_agent import FleetAgent
from backend.brain.agents.llm_client import get_llm_client

agent = FleetAgent(llm_client=get_llm_client())

# Initialize a fleet
fleet_status = agent.initialize_fleet(fleet_id="WAREHOUSE_FLEET_A", robot_count=5)

# Assign a task
assignment = agent.assign_task(
    fleet_id="WAREHOUSE_FLEET_A",
    task_id="PICK_ORDER_123",
    task_priority=80,
    required_capabilities=["gripper", "navigation"],
)

# Balance load
report = agent.balance_load(fleet_id="WAREHOUSE_FLEET_A")
""",
}
