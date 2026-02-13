"""
Agent Blueprint: Default Agent

General-purpose constitutional AI agent template.
"""

BLUEPRINT = {
    "id": "default",
    "name": "Default Agent",
    "description": "General-purpose agent with basic constitutional AI framework integration",
    "agent_class": "BaseAgent",
    "capabilities": [
        "task_execution",
        "llm_interaction",
        "tool_registration"
    ],
    "tools": [],
    "risk_levels": {
        "read_operations": "low",
        "write_operations": "medium",
        "system_changes": "high",
        "production_changes": "critical"
    },
    "supervision": {
        "automatic_approval": ["low", "medium"],
        "human_oversight_required": ["high", "critical"]
    },
    "compliance": {
        "constitutional_ai": "All actions validated through constitutional framework",
        "risk_assessment": "Automatic risk-based supervision",
        "audit_trail": "All operations logged"
    },
    "default_config": {
        "enable_supervision": True,
        "enable_audit_logging": True,
        "max_retries": 3,
        "timeout": 300  # seconds
    },
    "usage_note": "This is a template blueprint. Extend it for specific agent implementations."
}
