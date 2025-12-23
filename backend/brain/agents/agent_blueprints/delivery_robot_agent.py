"""
Delivery Robot Agent Blueprint

Agent specialized in autonomous delivery operations.

Capabilities:
- Navigation and path planning
- Package handling
- Obstacle avoidance
- Elevator/door control
- Multi-floor operation
- Delivery verification
"""

BLUEPRINT = {
    "id": "delivery_robot_agent",
    "name": "Delivery Robot Agent",
    "description": "Agent for autonomous delivery robot operations",
    "capabilities": [
        "autonomous_navigation",
        "path_planning",
        "obstacle_avoidance",
        "package_handling",
        "elevator_control",
        "door_interaction",
        "delivery_verification",
        "multi_floor_operation",
    ],
    "tools": [
        "navigate_to_location",
        "plan_path",
        "avoid_obstacles",
        "load_package",
        "unload_package",
        "call_elevator",
        "verify_delivery",
        "return_to_base",
    ],
    "protocols": [
        "ros2",
        "rest_api",
        "websocket",
    ],
    "parameters": {
        "max_payload_kg": 50.0,
        "max_velocity_mps": 1.5,
        "battery_capacity_wh": 500.0,
        "charging_threshold_percent": 20.0,
        "navigation_accuracy_m": 0.05,
        "obstacle_detection_range_m": 3.0,
    },
    "integration": {
        "physical_gateway": True,
        "fleet_manager": True,
        "ros2_bridge": True,
        "navigation_agent": True,
        "safety_agent": True,
    },
}
