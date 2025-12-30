"""
Agent Blueprint: Code Specialist

Constitutional AI agent for DSGVO-compliant code generation.
"""

BLUEPRINT = {
    "id": "code_specialist",
    "name": "Code Specialist",
    "description": "Specialized agent for secure code generation with DSGVO compliance and privacy by design",
    "agent_class": "CoderAgent",
    "capabilities": [
        "code_generation",
        "odoo_module_generation",
        "dsgvo_compliance",
        "privacy_by_design",
        "code_review"
    ],
    "tools": [
        "generate_code",
        "generate_odoo_module",
        "detect_personal_data",
        "validate_dsgvo_compliance"
    ],
    "risk_levels": {
        "code_generation_basic": "low",
        "code_generation_with_personal_data": "high",
        "odoo_module_generation": "medium",
        "odoo_module_with_personal_data": "high",
        "production_code": "critical"
    },
    "supervision": {
        "automatic_approval": ["low", "medium"],
        "human_oversight_required": ["high", "critical"]
    },
    "dsgvo_compliance": {
        "articles": [
            "Art. 5 (Data Minimization)",
            "Art. 6 (Legal Basis)",
            "Art. 7 (Consent)",
            "Art. 25 (Privacy by Design)",
            "Art. 30 (Records of Processing)"
        ],
        "features": [
            "Personal data detection",
            "Consent mechanism generation",
            "Data minimization validation",
            "Encryption requirements",
            "Access control generation"
        ]
    },
    "forbidden_patterns": [
        "eval(",
        "exec(",
        "os.system(",
        "subprocess.call(",
        "__import__('os')",
        "hardcoded_password",
        "hardcoded_secret"
    ],
    "default_config": {
        "enforce_type_hints": True,
        "require_docstrings": True,
        "max_function_length": 50,
        "enable_dsgvo_checks": True,
        "detect_personal_data": True,
        "require_encryption_for_pii": True
    }
}
