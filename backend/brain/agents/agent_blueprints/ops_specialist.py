"""
Agent Blueprint: Operations Specialist

Constitutional AI agent for safe deployment and operations management.
"""

BLUEPRINT = {
    "id": "ops_specialist",
    "name": "Operations Specialist",
    "description": "Specialized agent for deployment, infrastructure management, and operational tasks with production safety guarantees",
    "agent_class": "OpsAgent",
    "capabilities": [
        "deployment",
        "rollback",
        "health_monitoring",
        "infrastructure_management",
        "configuration_management"
    ],
    "tools": [
        "deploy_application",
        "rollback_deployment",
        "check_health",
        "manage_infrastructure"
    ],
    "risk_levels": {
        "deployment_dev": "medium",
        "deployment_staging": "high",
        "deployment_production": "critical",
        "rollback": "high",
        "health_check": "low",
        "infrastructure_changes": "critical"
    },
    "supervision": {
        "automatic_approval": ["low", "medium"],
        "human_oversight_required": ["high", "critical"]
    },
    "safety_guarantees": {
        "automatic_rollback": True,
        "pre_deployment_checks": True,
        "backup_creation": True,
        "health_verification": True
    },
    "compliance": {
        "production_deployment": "Human approval required (EU AI Act Art. 16)",
        "rollback_capability": "All deployments can be rolled back",
        "audit_trail": "All operations logged for compliance"
    },
    "default_config": {
        "deployment_timeout": 300,  # seconds
        "health_check_interval": 30,  # seconds
        "max_rollback_versions": 5,
        "enable_automatic_rollback": True,
        "require_approval_for_production": True
    }
}
