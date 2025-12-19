"""
Safety Monitor Agent Blueprint

Pre-configured blueprint for SafetyAgent instantiation.
"""

BLUEPRINT = {
    "id": "safety_monitor",
    "name": "Safety Monitor",
    "role": "SAFETY_MONITOR",
    "model": "phi3",
    "description": "Real-time safety monitoring, incident reporting, and emergency response coordination",
    "version": "1.0.0",

    "capabilities": [
        "safety_monitoring",
        "incident_detection",
        "emergency_response",
        "zone_enforcement",
        "compliance_checking",
    ],

    "tools": [
        "check_safety_status",
        "trigger_emergency_stop",
        "validate_zone_entry",
        "report_incident",
        "assess_risk",
    ],

    "permissions": [
        "SAFETY_MONITOR",
        "EMERGENCY_CONTROL",
        "ZONE_ENFORCE",
    ],

    "config": {
        "temperature": 0.2,  # Very low for safety-critical decisions
        "max_tokens": 2048,
        "system_prompt": """You are the Safety Monitoring Agent for the BRAiN RYR system.

Your PRIMARY RESPONSIBILITY is ensuring the safety of:
1. Humans in the environment
2. The robots themselves
3. Equipment and infrastructure

Safety principles (in order of priority):
1. HUMAN SAFETY: Always prioritize human safety above all else
2. PREVENT HARM: Stop any action that could cause injury or damage
3. COMPLY WITH RULES: Enforce all safety zones and speed limits
4. MONITOR CONTINUOUSLY: Track sensor health, battery, and proximity
5. RESPOND IMMEDIATELY: Trigger emergency stops when necessary

Never compromise safety for efficiency or convenience.
When in doubt, err on the side of caution - stop first, analyze later.""",
    },

    "integration": {
        "modules": ["foundation", "policy", "karma", "immune"],
        "agents": ["fleet_agent", "navigation_agent"],
        "external": ["ros2_control", "safety_plc"],
    },

    "thresholds": {
        "min_obstacle_distance_m": 0.5,
        "min_human_distance_m": 1.5,
        "critical_battery_percentage": 15.0,
        "max_speed_default_ms": 2.0,
    },

    "incident_types": [
        "collision",
        "near_miss",
        "zone_violation",
        "speed_violation",
        "human_proximity",
        "emergency_stop",
        "sensor_failure",
        "battery_critical",
        "communication_loss",
    ],

    "metrics": {
        "safety_incidents_count": "int",
        "near_miss_count": "int",
        "emergency_stops_count": "int",
        "safety_zone_violations": "int",
        "obstacle_detection_rate": "float",
    },

    "usage_example": """
# Initialize SafetyAgent
from backend.brain.agents.safety_agent import SafetyAgent
from backend.brain.agents.llm_client import get_llm_client

agent = SafetyAgent(llm_client=get_llm_client())

# Define a safety zone
zone = agent.define_safety_zone(
    zone_id="RESTRICTED_AREA_1",
    zone_type="restricted",
    max_speed_ms=0.5,
    allowed_robots=["ROBOT_SUPERVISOR_001"],
)

# Check robot safety status
safety_level, issues = agent.check_safety_status(robot_id="ROBOT_001")

# Validate zone entry
permission = agent.validate_zone_entry(
    robot_id="ROBOT_001",
    zone_id="RESTRICTED_AREA_1",
    current_speed_ms=0.8,
)

# Trigger emergency stop if needed
if safety_level == "emergency":
    agent.trigger_emergency_stop(robot_id="ROBOT_001", reason="Critical safety violation")
""",
}
