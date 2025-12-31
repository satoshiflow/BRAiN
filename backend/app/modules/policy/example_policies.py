"""
Example Policy Rules for Constitutional Agents Framework

Pre-configured policies for common governance scenarios.
Load these policies into the Policy Engine for testing and production use.
"""

from typing import List, Dict, Any
from backend.app.modules.policy.schemas import PolicyRule, PolicyEffect


# ============================================================================
# Production Deployment Policies
# ============================================================================

PRODUCTION_DEPLOYMENT_POLICY = PolicyRule(
    id="prod-deploy-senior-only",
    name="Production Deployment - Senior Approval Required",
    description="Only senior agents or human operators can deploy to production",
    effect=PolicyEffect.DENY,
    priority=200,  # High priority
    conditions={
        "action": {"==": "deploy_application"},
        "context.environment": {"==": "production"},
        "agent_role": {"!=": "senior"}
    },
    enabled=True,
    metadata={
        "compliance": ["EU AI Act Art. 16"],
        "category": "deployment"
    }
)

DATABASE_MODIFICATION_POLICY = PolicyRule(
    id="db-modify-backup-required",
    name="Database Modification - Backup Required",
    description="Database modifications require backup verification",
    effect=PolicyEffect.WARN,
    priority=150,
    conditions={
        "action": {"matches": ".*database.*"},
        "context.has_backup": {"!=": True}
    },
    enabled=True,
    metadata={
        "category": "data_safety"
    }
)


# ============================================================================
# DSGVO / Personal Data Policies
# ============================================================================

PERSONAL_DATA_PROCESSING_POLICY = PolicyRule(
    id="personal-data-consent-required",
    name="Personal Data Processing - Consent Required",
    description="Processing personal data requires explicit user consent (DSGVO Art. 6)",
    effect=PolicyEffect.DENY,
    priority=250,  # Very high priority
    conditions={
        "action": {"matches": ".*(process|store|collect).*data.*"},
        "context.data_type": {"contains": "personal"},
        "context.has_consent": {"!=": True}
    },
    enabled=True,
    metadata={
        "compliance": ["DSGVO Art. 6", "DSGVO Art. 7"],
        "category": "privacy"
    }
)

INTERNATIONAL_TRANSFER_POLICY = PolicyRule(
    id="international-transfer-restricted",
    name="International Data Transfer - Restricted",
    description="International data transfers require adequacy decision (DSGVO Art. 44-49)",
    effect=PolicyEffect.DENY,
    priority=240,
    conditions={
        "action": {"matches": ".*transfer.*"},
        "context.destination": {"not in": ["EU", "EEA"]},
        "context.adequacy_decision": {"!=": True}
    },
    enabled=True,
    metadata={
        "compliance": ["DSGVO Art. 44", "DSGVO Art. 45"],
        "category": "privacy"
    }
)

DATA_MINIMIZATION_POLICY = PolicyRule(
    id="data-minimization-check",
    name="Data Minimization Principle",
    description="Warn if data collection exceeds necessary scope (DSGVO Art. 5)",
    effect=PolicyEffect.WARN,
    priority=100,
    conditions={
        "action": {"matches": ".*collect.*data.*"},
        "context.data_fields": {">": 10}  # More than 10 fields
    },
    enabled=True,
    metadata={
        "compliance": ["DSGVO Art. 5(1)(c)"],
        "category": "privacy"
    }
)


# ============================================================================
# EU AI Act Policies
# ============================================================================

SOCIAL_SCORING_PROHIBITION = PolicyRule(
    id="ai-act-social-scoring-prohibited",
    name="Social Scoring - Prohibited Practice",
    description="Social scoring systems are prohibited (EU AI Act Art. 5)",
    effect=PolicyEffect.DENY,
    priority=300,  # Maximum priority
    conditions={
        "action": {"matches": ".*social.*scor.*"},
    },
    enabled=True,
    metadata={
        "compliance": ["EU AI Act Art. 5(1)(c)"],
        "category": "prohibited_practice"
    }
)

SUBLIMINAL_MANIPULATION_PROHIBITION = PolicyRule(
    id="ai-act-manipulation-prohibited",
    name="Subliminal Manipulation - Prohibited",
    description="Subliminal manipulation is prohibited (EU AI Act Art. 5)",
    effect=PolicyEffect.DENY,
    priority=300,
    conditions={
        "action": {"matches": ".*manipulat.*|.*subliminal.*"},
        "context.purpose": {"contains": "behavior modification"}
    },
    enabled=True,
    metadata={
        "compliance": ["EU AI Act Art. 5(1)(a)"],
        "category": "prohibited_practice"
    }
)

HIGH_RISK_AI_HUMAN_OVERSIGHT = PolicyRule(
    id="ai-act-high-risk-oversight",
    name="High-Risk AI - Human Oversight Required",
    description="High-risk AI systems require human oversight (EU AI Act Art. 14)",
    effect=PolicyEffect.DENY,
    priority=220,
    conditions={
        "context.high_risk_ai": {"==": True},
        "context.human_oversight": {"!=": True}
    },
    enabled=True,
    metadata={
        "compliance": ["EU AI Act Art. 14"],
        "category": "high_risk_ai"
    }
)


# ============================================================================
# Security Policies
# ============================================================================

ENCRYPTION_REQUIRED_POLICY = PolicyRule(
    id="security-encryption-required",
    name="Encryption Required for Sensitive Data",
    description="Sensitive data must be encrypted at rest and in transit",
    effect=PolicyEffect.DENY,
    priority=180,
    conditions={
        "action": {"matches": ".*(store|transmit).*"},
        "context.data_sensitivity": {"==": "high"},
        "context.encrypted": {"!=": True}
    },
    enabled=True,
    metadata={
        "compliance": ["ISO 27001"],
        "category": "security"
    }
)

AUTHENTICATION_REQUIRED_POLICY = PolicyRule(
    id="security-auth-required",
    name="Authentication Required for Sensitive Operations",
    description="Sensitive operations require authenticated user",
    effect=PolicyEffect.DENY,
    priority=190,
    conditions={
        "action": {"matches": ".*(delete|modify|deploy).*"},
        "context.authenticated": {"!=": True}
    },
    enabled=True,
    metadata={
        "category": "security"
    }
)


# ============================================================================
# Development & Testing Policies
# ============================================================================

TEST_ENVIRONMENT_POLICY = PolicyRule(
    id="dev-test-environment-isolation",
    name="Test Environment Isolation",
    description="Test environments should not access production data",
    effect=PolicyEffect.WARN,
    priority=120,
    conditions={
        "context.environment": {"in": ["development", "testing"]},
        "context.data_source": {"contains": "production"}
    },
    enabled=True,
    metadata={
        "category": "development"
    }
)


# ============================================================================
# Resource Management Policies
# ============================================================================

RATE_LIMIT_POLICY = PolicyRule(
    id="resource-rate-limit",
    name="API Rate Limiting",
    description="Prevent excessive API calls",
    effect=PolicyEffect.DENY,
    priority=110,
    conditions={
        "action": {"matches": ".*api.*call.*"},
        "context.requests_per_minute": {">": 1000}
    },
    enabled=True,
    metadata={
        "category": "resource_management"
    }
)


# ============================================================================
# Policy Collections
# ============================================================================

def get_all_example_policies() -> List[PolicyRule]:
    """Get all example policies as a list."""
    return [
        # Production
        PRODUCTION_DEPLOYMENT_POLICY,
        DATABASE_MODIFICATION_POLICY,

        # DSGVO
        PERSONAL_DATA_PROCESSING_POLICY,
        INTERNATIONAL_TRANSFER_POLICY,
        DATA_MINIMIZATION_POLICY,

        # EU AI Act
        SOCIAL_SCORING_PROHIBITION,
        SUBLIMINAL_MANIPULATION_PROHIBITION,
        HIGH_RISK_AI_HUMAN_OVERSIGHT,

        # Security
        ENCRYPTION_REQUIRED_POLICY,
        AUTHENTICATION_REQUIRED_POLICY,

        # Development
        TEST_ENVIRONMENT_POLICY,

        # Resources
        RATE_LIMIT_POLICY,
    ]


def get_policies_by_category(category: str) -> List[PolicyRule]:
    """Get policies filtered by category."""
    return [
        policy for policy in get_all_example_policies()
        if policy.metadata.get("category") == category
    ]


def get_compliance_policies(framework: str) -> List[PolicyRule]:
    """Get policies related to a specific compliance framework."""
    return [
        policy for policy in get_all_example_policies()
        if framework in policy.metadata.get("compliance", [])
    ]


def load_policies_into_engine(policy_service):
    """
    Load all example policies into a PolicyService instance.

    Usage:
        from backend.app.modules.policy.service import PolicyService
        from backend.app.modules.policy.example_policies import load_policies_into_engine

        service = PolicyService()
        load_policies_into_engine(service)
    """
    policies = get_all_example_policies()
    for policy in policies:
        policy_service.add_policy(policy)

    return len(policies)


# ============================================================================
# Policy Scenarios for Testing
# ============================================================================

TEST_SCENARIOS = {
    "allowed_dev_deployment": {
        "agent_id": "ops_agent",
        "action": "deploy_application",
        "context": {
            "environment": "development",
            "version": "1.0.0"
        },
        "expected_effect": "allow"
    },

    "denied_prod_deployment_junior": {
        "agent_id": "ops_agent",
        "action": "deploy_application",
        "context": {
            "environment": "production",
            "version": "1.0.0",
            "agent_role": "junior"
        },
        "expected_effect": "deny"
    },

    "denied_personal_data_no_consent": {
        "agent_id": "coder_agent",
        "action": "process_personal_data",
        "context": {
            "data_type": "personal",
            "has_consent": False
        },
        "expected_effect": "deny"
    },

    "denied_social_scoring": {
        "agent_id": "ml_agent",
        "action": "create_social_scoring_system",
        "context": {},
        "expected_effect": "deny"
    },

    "warn_data_minimization": {
        "agent_id": "api_agent",
        "action": "collect_user_data",
        "context": {
            "data_fields": 15
        },
        "expected_effect": "warn"
    }
}


if __name__ == "__main__":
    # Print policy summary
    policies = get_all_example_policies()
    print(f"Total example policies: {len(policies)}\n")

    categories = set(p.metadata.get("category") for p in policies if p.metadata.get("category"))
    print(f"Categories: {', '.join(sorted(categories))}\n")

    print("Policies by priority:")
    for policy in sorted(policies, key=lambda p: p.priority, reverse=True):
        print(f"  [{policy.priority}] {policy.name} ({policy.effect})")
