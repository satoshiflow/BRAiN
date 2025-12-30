"""
Coder Agent Blueprint

Pre-configured blueprint for secure code generation.
"""

from backend.brain.agents.base_agent import AgentConfig
from backend.brain.agents.coder_agent import CODER_CONSTITUTIONAL_PROMPT

BLUEPRINT = {
    "id": "coder",
    "name": "CoderAgent",
    "role": "CODER",
    "description": "DSGVO-compliant code generation with supervisor integration",
    "version": "1.0.0",

    "capabilities": [
        "odoo_module_generation",
        "fastapi_endpoint_generation",
        "code_validation",
        "privacy_by_design_enforcement",
        "risk_assessment",
    ],

    "tools": [
        "generate_code",
        "generate_odoo_module",
        "generate_api_endpoint",
        "validate_code",
        "create_file",
    ],

    "permissions": [
        "CODE_GENERATE",
        "FILE_WRITE",
        "MODULE_CREATE",
    ],

    "config": {
        "model": "phi3",
        "temperature": 0.3,  # Moderate creativity
        "max_tokens": 4096,  # Longer for code generation
        "system_prompt": CODER_CONSTITUTIONAL_PROMPT,
    },

    "metadata": {
        "category": "development",
        "compliance": ["DSGVO Art. 5, 6, 17, 25", "Privacy by Design"],
        "forbidden_patterns": ["eval()", "exec()", "hardcoded_secrets"],
        "output_types": ["python", "odoo", "fastapi"],
    }
}


def get_coder_config() -> AgentConfig:
    """Get pre-configured CoderAgent configuration"""
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
