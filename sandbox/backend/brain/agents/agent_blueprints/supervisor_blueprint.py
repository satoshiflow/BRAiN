"""
Supervisor Agent Blueprint

Pre-configured blueprint for the Constitutional Framework Guardian.
"""

from brain.agents.base_agent import AgentConfig
from brain.agents.supervisor_agent import CONSTITUTIONAL_PROMPT

BLUEPRINT = {
    "id": "supervisor",
    "name": "SupervisorAgent",
    "role": "SUPERVISOR",
    "description": "Constitutional framework guardian for ethical oversight",
    "version": "1.0.0",

    "capabilities": [
        "risk_assessment",
        "policy_evaluation",
        "human_in_the_loop_trigger",
        "audit_trail_management",
        "constitutional_compliance_check",
    ],

    "tools": [
        "supervise_action",
        "trigger_human_approval",
        "audit_log",
    ],

    "permissions": [
        "SUPERVISE_ALL",
        "HUMAN_APPROVAL_TRIGGER",
        "AUDIT_WRITE",
    ],

    "config": {
        "model": "phi3",
        "temperature": 0.1,  # Very low for deterministic decisions
        "max_tokens": 1024,
        "system_prompt": CONSTITUTIONAL_PROMPT,
    },

    "metadata": {
        "category": "governance",
        "compliance": ["DSGVO Art. 22", "EU AI Act Art. 16"],
        "risk_levels": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        "integration_points": ["PolicyEngine", "FoundationLayer"],
    }
}


def get_supervisor_config() -> AgentConfig:
    """Get pre-configured SupervisorAgent configuration"""
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
