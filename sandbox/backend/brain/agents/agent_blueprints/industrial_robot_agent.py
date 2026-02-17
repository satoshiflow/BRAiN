"""
Industrial Robot Agent Blueprint

Agent specialized in controlling industrial robots.

Capabilities:
- Motion planning and execution
- Trajectory optimization
- Collision avoidance
- Tool path generation
- Safety monitoring
- Force/torque control
"""

BLUEPRINT = {
    "id": "industrial_robot_agent",
    "name": "Industrial Robot Agent",
    "description": "Agent for industrial robot control and coordination",
    "capabilities": [
        "motion_planning",
        "trajectory_execution",
        "collision_avoidance",
        "tool_path_generation",
        "force_control",
        "safety_monitoring",
        "position_control",
        "velocity_control",
    ],
    "tools": [
        "plan_motion",
        "execute_trajectory",
        "check_collisions",
        "generate_tool_path",
        "read_force_torque",
        "emergency_stop",
        "get_joint_states",
        "move_to_pose",
    ],
    "protocols": [
        "ros2",
        "modbus",
        "opcua",
        "profinet",
    ],
    "parameters": {
        "degrees_of_freedom": 6,
        "max_velocity_mps": 2.0,
        "max_acceleration_mps2": 1.0,
        "max_force_n": 500.0,
        "safety_zone_radius_m": 1.5,
        "control_frequency_hz": 125.0,
    },
    "integration": {
        "physical_gateway": True,
        "fleet_manager": True,
        "ros2_bridge": True,
        "safety_agent": True,
    },
}
