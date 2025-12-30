"""
Architect Agent Blueprint

Pre-configured blueprint for architecture and compliance auditing.
"""

from backend.brain.agents.base_agent import AgentConfig
from backend.brain.agents.architect_agent import ARCHITECT_CONSTITUTIONAL_PROMPT

BLUEPRINT = {
    "id": "architect",
    "name": "ArchitectAgent",
    "role": "ARCHITECT",
    "description": "System architecture and EU compliance auditor",
    "version": "1.0.0",

    "capabilities": [
        "architecture_review",
        "eu_ai_act_compliance",
        "gdpr_compliance",
        "scalability_assessment",
        "security_audit",
    ],

    "tools": [
        "review_architecture",
        "check_eu_compliance",
        "assess_scalability",
        "audit_security",
        "recommend_improvements",
    ],

    "permissions": [
        "ARCHITECTURE_REVIEW",
        "COMPLIANCE_AUDIT",
        "RECOMMEND",
    ],

    "config": {
        "model": "phi3",
        "temperature": 0.2,  # Low for analytical thinking
        "max_tokens": 4096,  # Longer for architectural analysis
        "system_prompt": ARCHITECT_CONSTITUTIONAL_PROMPT,
    },

    "metadata": {
        "category": "architecture",
        "compliance_frameworks": ["EU AI Act", "DSGVO", "ISO 27001"],
        "assessment_areas": ["compliance", "scalability", "security", "maintainability"],
        "prohibited_practices": [
            "social_scoring",
            "subliminal_manipulation",
            "biometric_categorization"
        ],
    }
}


def get_architect_config() -> AgentConfig:
    """Get pre-configured ArchitectAgent configuration"""
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
