"""
Drone Agent Blueprint

Agent specialized in autonomous drone operations.

Capabilities:
- Flight control
- Mission planning
- Aerial photography/inspection
- Obstacle avoidance
- Battery management
- Emergency landing
"""

BLUEPRINT = {
    "id": "drone_agent",
    "name": "Drone Agent",
    "description": "Agent for autonomous drone operations and missions",
    "capabilities": [
        "flight_control",
        "mission_planning",
        "waypoint_navigation",
        "aerial_photography",
        "inspection",
        "obstacle_avoidance",
        "battery_management",
        "emergency_landing",
        "geofencing",
    ],
    "tools": [
        "takeoff",
        "land",
        "goto_waypoint",
        "follow_path",
        "capture_image",
        "capture_video",
        "avoid_obstacle",
        "return_to_home",
        "emergency_land",
    ],
    "protocols": [
        "ros2",
        "mavlink",
        "websocket",
    ],
    "parameters": {
        "max_altitude_m": 120.0,
        "max_velocity_mps": 15.0,
        "max_flight_time_minutes": 25.0,
        "battery_capacity_mah": 5000.0,
        "rtl_threshold_percent": 25.0,  # Return-to-launch battery threshold
        "max_wind_speed_mps": 12.0,
        "geofence_radius_m": 500.0,
    },
    "integration": {
        "physical_gateway": True,
        "fleet_manager": True,
        "ros2_bridge": True,
        "navigation_agent": True,
        "safety_agent": True,
    },
}
