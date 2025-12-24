"""
IoT Gateway Agent Blueprint

Agent specialized in managing and coordinating IoT devices.

Capabilities:
- Device discovery and registration
- Multi-protocol communication (MQTT, REST, Modbus)
- Sensor data aggregation
- Device health monitoring
- Alert generation
"""

BLUEPRINT = {
    "id": "iot_gateway_agent",
    "name": "IoT Gateway Agent",
    "description": "Agent for IoT device management and coordination",
    "capabilities": [
        "device_discovery",
        "multi_protocol_communication",
        "sensor_data_aggregation",
        "device_health_monitoring",
        "alert_generation",
        "data_filtering",
        "protocol_translation",
    ],
    "tools": [
        "discover_devices",
        "register_device",
        "read_sensor_data",
        "write_actuator_command",
        "monitor_device_health",
        "generate_alert",
        "aggregate_data",
    ],
    "protocols": [
        "mqtt",
        "rest_api",
        "modbus",
        "opcua",
    ],
    "parameters": {
        "max_devices": 1000,
        "polling_interval_seconds": 5.0,
        "alert_threshold": "configurable",
        "data_retention_hours": 24,
    },
    "integration": {
        "physical_gateway": True,
        "fleet_manager": False,
        "ros2_bridge": False,
    },
}
