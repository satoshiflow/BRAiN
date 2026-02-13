"""
Tests for ArchitectAgent

Tests system architecture and EU compliance auditing.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from brain.agents.architect_agent import ArchitectAgent, ComplianceViolation
from app.modules.supervisor.schemas import RiskLevel


@pytest.fixture
def mock_llm_client():
    client = Mock()
    client.generate = AsyncMock(return_value="""
**KRITISCH:**
1. Implementiere risk_management_system (EU AI Act Art. 9)

**HOCH:**
2. Füge Privacy by Design hinzu (DSGVO Art. 25)
""")
    return client


@pytest.fixture
def architect_agent(mock_llm_client):
    return ArchitectAgent(llm_client=mock_llm_client)


# ============================================================================
# EU Compliance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_check_eu_compliance_detects_prohibited_practices(architect_agent):
    """Test detection of prohibited AI practices"""
    spec = {
        "ai_capabilities": ["social_scoring", "biometric_categorization"],
        "uses_personal_data": True,
    }

    result = await architect_agent.check_eu_compliance(spec)

    assert result["meta"]["status"] == "NON_COMPLIANT"
    violations = result["meta"]["violations"]
    assert len(violations) >= 2  # At least 2 prohibited practices
    assert any("EU AI Act Art. 5" in v["regulation"] for v in violations)


@pytest.mark.asyncio
async def test_check_eu_compliance_detects_us_data_transfer(architect_agent):
    """Test detection of US data transfers without DPA"""
    spec = {
        "external_dependencies": [
            {"name": "AWS S3", "location": "US", "has_dpa": False}
        ],
        "uses_personal_data": True,
    }

    result = await architect_agent.check_eu_compliance(spec)

    assert result["meta"]["status"] == "NON_COMPLIANT"
    violations = result["meta"]["violations"]
    assert any("DSGVO Art. 44-46" in v["regulation"] for v in violations)
    assert any("US" in v["description"] for v in violations)


@pytest.mark.asyncio
async def test_check_eu_compliance_requires_privacy_by_design(architect_agent):
    """Test Privacy by Design requirement"""
    spec = {
        "uses_personal_data": True,
        "privacy_by_design": False,
    }

    result = await architect_agent.check_eu_compliance(spec)

    violations = result["meta"]["violations"]
    assert any("DSGVO Art. 25" in v["regulation"] for v in violations)
    assert any("Privacy by Design" in v["description"] for v in violations)


@pytest.mark.asyncio
async def test_check_eu_compliance_passes_compliant_system(architect_agent):
    """Test compliant system passes"""
    spec = {
        "ai_capabilities": [],
        "external_dependencies": [
            {"name": "Hetzner", "location": "EU", "has_dpa": True}
        ],
        "uses_personal_data": True,
        "privacy_by_design": True,
    }

    result = await architect_agent.check_eu_compliance(spec)

    assert result["meta"]["status"] == "COMPLIANT"
    assert len(result["meta"]["violations"]) == 0


# ============================================================================
# Architecture Review Tests
# ============================================================================


@pytest.mark.asyncio
async def test_review_architecture_high_risk_ai_system(architect_agent):
    """Test review of high-risk AI system"""
    spec = {
        "uses_ai": True,
        "uses_personal_data": True,
        "risk_management_system": False,
        "data_governance": False,
        "human_oversight": False,
    }

    result = await architect_agent.review_architecture(
        system_name="ai-recruitment-tool",
        architecture_spec=spec,
        high_risk_ai=True
    )

    assert result["success"] is True
    assert result["meta"]["risk_level"] == "critical"
    assert result["meta"]["compliance_score"] < 60  # Low score
    violations = result["meta"]["violations"]
    assert len(violations) >= 3  # Multiple violations


@pytest.mark.asyncio
async def test_review_architecture_compliance_scoring(architect_agent):
    """Test compliance score calculation"""
    # Good architecture
    good_spec = {
        "uses_ai": False,
        "uses_personal_data": False,
        "modular_design": True,
        "vendor_independent": True,
    }

    result = await architect_agent.review_architecture(
        system_name="utility-service",
        architecture_spec=good_spec,
        high_risk_ai=False
    )

    assert result["meta"]["compliance_score"] >= 85  # High score
    assert result["meta"]["risk_level"] in ["low", "medium"]


# ============================================================================
# Scalability Assessment Tests
# ============================================================================


@pytest.mark.asyncio
async def test_assess_scalability_monolithic_issues(architect_agent):
    """Test scalability assessment detects monolithic issues"""
    spec = {
        "architecture_type": "monolithic",
        "expected_users": 50000,
        "database_replication": False,
        "caching_layer": False,
    }

    result = await architect_agent.assess_scalability(spec)

    assert result["success"] is True
    issues = result["meta"]["issues"]
    assert len(issues) >= 2  # Multiple scalability issues
    assert any("monolith" in issue.lower() for issue in issues)


@pytest.mark.asyncio
async def test_assess_scalability_good_architecture(architect_agent):
    """Test scalability assessment passes good architecture"""
    spec = {
        "architecture_type": "microservices",
        "expected_users": 10000,
        "database_replication": True,
        "caching_layer": True,
        "async_task_queue": True,
    }

    result = await architect_agent.assess_scalability(spec)

    assert result["meta"]["scalability_score"] >= 80
    assert len(result["meta"]["issues"]) == 0


# ============================================================================
# Security Audit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_audit_security_missing_authentication(architect_agent):
    """Test security audit detects missing authentication"""
    spec = {
        "authentication": False,
        "encryption_at_rest": True,
        "encryption_in_transit": True,
    }

    result = await architect_agent.audit_security(spec)

    vulnerabilities = result["meta"]["vulnerabilities"]
    assert any(v["severity"] == "CRITICAL" for v in vulnerabilities)
    assert any("authentication" in v["issue"].lower() for v in vulnerabilities)


@pytest.mark.asyncio
async def test_audit_security_missing_encryption(architect_agent):
    """Test security audit detects missing encryption"""
    spec = {
        "authentication": True,
        "encryption_at_rest": False,
        "encryption_in_transit": False,
    }

    result = await architect_agent.audit_security(spec)

    vulnerabilities = result["meta"]["vulnerabilities"]
    # Should have 2 HIGH severity issues for missing encryption
    high_severity = [v for v in vulnerabilities if v["severity"] == "HIGH"]
    assert len(high_severity) >= 2


@pytest.mark.asyncio
async def test_audit_security_complete_setup(architect_agent):
    """Test security audit passes complete setup"""
    spec = {
        "authentication": True,
        "encryption_at_rest": True,
        "encryption_in_transit": True,
        "input_validation": True,
        "rate_limiting": True,
    }

    result = await architect_agent.audit_security(spec)

    assert result["meta"]["security_score"] == 100
    assert len(result["meta"]["vulnerabilities"]) == 0


# ============================================================================
# Recommendation Generation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_recommend_improvements_generates_prioritized_list(architect_agent):
    """Test improvement recommendations are generated"""
    assessment_result = {
        "compliance_score": 45,
        "risk_level": "critical",
        "violations": [
            {"severity": "CRITICAL", "description": "Missing auth"},
            {"severity": "HIGH", "description": "No encryption"},
        ]
    }

    result = await architect_agent.recommend_improvements(assessment_result)

    assert result["success"] is True
    assert "recommendations" in result["meta"]
    # Should include prioritization (KRITISCH, HOCH, etc.)
    assert "KRITISCH" in result["raw_response"] or "HOCH" in result["raw_response"]
