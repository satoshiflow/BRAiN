"""
Ops Agent Blueprint

Pre-configured blueprint for operations and deployment.
"""

from backend.brain.agents.base_agent import AgentConfig
from backend.brain.agents.ops_agent import OPS_CONSTITUTIONAL_PROMPT

BLUEPRINT = {
    "id": "ops",
    "name": "OpsAgent",
    "role": "OPS",
    "description": "Safe deployment orchestration with risk assessment",
    "version": "1.0.0",

    "capabilities": [
        "deployment_orchestration",
        "database_migrations",
        "service_configuration",
        "health_monitoring",
        "automatic_rollback",
    ],

    "tools": [
        "deploy_application",
        "configure_service",
        "run_migration",
        "health_check",
        "rollback_deployment",
    ],

    "permissions": [
        "DEPLOY",
        "CONFIGURE",
        "MIGRATE",
        "ROLLBACK",
    ],

    "config": {
        "model": "phi3",
        "temperature": 0.1,  # Very low for deterministic operations
        "max_tokens": 2048,
        "system_prompt": OPS_CONSTITUTIONAL_PROMPT,
    },

    "metadata": {
        "category": "operations",
        "environments": ["development", "staging", "production"],
        "risk_mapping": {
            "production": "CRITICAL",
            "staging": "HIGH",
            "development": "MEDIUM"
        },
    }
}


def get_ops_config() -> AgentConfig:
    """Get pre-configured OpsAgent configuration"""
    return AgentConfig(
        name=BLUEPRINT["name"],
        role=BLUEPRINT["role"],
        model=BLUEPRINT["config"]["model"],
        system_prompt=BLUEPRINT["config"]["system_prompt"],
        temperature=BLUEPRINT["config"]["temperature"],
        max_tokens=BLUEPRINT["config"]["max_tokens"],
        tools=BLUEPRINT["tools"],
        permissions=BLUEPRINT["permissions"],
        metadata=BLUEPRINT["metadata"],
    )
