"""
Agricultural Robot Agent Blueprint

Agent specialized in agricultural automation.

Capabilities:
- Crop monitoring
- Precision spraying
- Autonomous harvesting
- Soil analysis
- Irrigation control
- Pest detection
"""

BLUEPRINT = {
    "id": "agricultural_robot_agent",
    "name": "Agricultural Robot Agent",
    "description": "Agent for agricultural automation and precision farming",
    "capabilities": [
        "crop_monitoring",
        "precision_spraying",
        "autonomous_harvesting",
        "soil_analysis",
        "irrigation_control",
        "pest_detection",
        "yield_estimation",
        "field_navigation",
    ],
    "tools": [
        "monitor_crop_health",
        "spray_pesticide",
        "harvest_crop",
        "analyze_soil",
        "control_irrigation",
        "detect_pests",
        "estimate_yield",
        "navigate_field",
    ],
    "protocols": [
        "ros2",
        "rest_api",
        "modbus",
    ],
    "parameters": {
        "field_coverage_m2_per_hour": 5000.0,
        "spray_precision_cm": 5.0,
        "max_payload_kg": 200.0,
        "battery_capacity_kwh": 10.0,
        "operating_temperature_range_c": [-10.0, 45.0],
        "gps_accuracy_cm": 2.0,
    },
    "integration": {
        "physical_gateway": True,
        "fleet_manager": True,
        "ros2_bridge": True,
        "vision_agent": True,
    },
}
