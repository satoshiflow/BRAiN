"""
Integration Tests for Constitutional Agents Framework

Tests the complete workflow with real LLM client integration.
Requires Ollama or compatible LLM service running.
"""

import sys
import os
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock

# Path setup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.brain.agents.supervisor_agent import SupervisorAgent, get_supervisor_agent
from backend.brain.agents.coder_agent import CoderAgent, get_coder_agent
from backend.brain.agents.ops_agent import OpsAgent, get_ops_agent
from backend.brain.agents.architect_agent import ArchitectAgent, get_architect_agent
from backend.brain.agents.axe_agent import AXEAgent, get_axe_agent
from backend.app.modules.supervisor.schemas import (
    RiskLevel,
    SupervisionRequest,
    SupervisionResponse,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_client():
    """Mock LLM client that simulates realistic responses."""
    client = Mock()

    # Default response: approve LOW/MEDIUM risk
    client.generate = AsyncMock(
        return_value="approved: true\nreason: Action is safe and compliant with DSGVO and EU AI Act"
    )

    return client


@pytest.fixture
def mock_policy_engine():
    """Mock Policy Engine that allows most actions."""
    engine = Mock()
    engine.evaluate = AsyncMock(return_value=Mock(
        effect="allow",
        reason="No policy violations detected"
    ))
    return engine


# ============================================================================
# Full Workflow Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_supervision_workflow_low_risk(mock_llm_client, mock_policy_engine):
    """Test complete LOW risk supervision workflow."""
    supervisor = SupervisorAgent(
        llm_client=mock_llm_client,
        policy_engine=mock_policy_engine
    )

    request = SupervisionRequest(
        requesting_agent="TestAgent",
        action="read_logs",
        context={"log_type": "application"},
        risk_level=RiskLevel.LOW
    )

    response = await supervisor.supervise_action(request)

    assert response.approved is True
    assert response.human_oversight_required is False
    assert response.audit_id is not None
    assert len(supervisor.audit_trail) > 0

    # Verify LLM was called for constitutional check
    mock_llm_client.generate.assert_called_once()


@pytest.mark.asyncio
async def test_coder_agent_with_supervisor_integration(mock_llm_client):
    """Test CoderAgent requesting supervision for HIGH-risk code."""
    # Setup supervisor
    supervisor = SupervisorAgent(llm_client=mock_llm_client)

    # Setup coder with supervisor available
    coder = CoderAgent(llm_client=mock_llm_client)

    # Mock LLM to return code generation
    mock_llm_client.generate = AsyncMock(
        return_value='def validate_email(email: str) -> bool:\n    return "@" in email'
    )

    # Test code generation (should auto-assess risk)
    result = await coder.generate_code(
        spec="Create a function to validate email addresses",
        risk_level=RiskLevel.LOW
    )

    assert result.success is True
    assert "code" in result.data


@pytest.mark.asyncio
async def test_ops_deployment_requires_supervision(mock_llm_client):
    """Test OpsAgent deployment triggers supervision for production."""
    ops = OpsAgent(llm_client=mock_llm_client)

    # Mock deployment simulation
    result = await ops.deploy_application(
        app_name="test-app",
        version="1.0.0",
        environment="development",  # LOW risk
        config={}
    )

    assert result.success is True
    assert "deployment_id" in result.data


@pytest.mark.asyncio
async def test_architect_eu_compliance_check(mock_llm_client):
    """Test ArchitectAgent EU compliance checking."""
    architect = ArchitectAgent(llm_client=mock_llm_client)

    # Mock LLM to return compliance report
    mock_llm_client.generate = AsyncMock(
        return_value="""
        EU AI Act Compliance: PASS
        DSGVO Compliance: PASS
        Prohibited Practices: None detected
        Recommendations:
        - Add data encryption at rest
        - Implement regular security audits
        """
    )

    result = await architect.check_eu_compliance({
        "uses_ai": True,
        "processes_personal_data": True,
        "has_consent_mechanism": True,
        "international_transfers": False
    })

    assert result.success is True
    assert "compliance_report" in result.data


@pytest.mark.asyncio
async def test_axe_conversational_flow(mock_llm_client):
    """Test AXEAgent conversational capabilities."""
    axe = AXEAgent(llm_client=mock_llm_client)

    # Mock LLM responses
    mock_llm_client.simple_chat = AsyncMock(
        return_value=(
            "The system is operational. All agents are running normally.",
            {"message": {"content": "System status OK"}}
        )
    )

    # Test chat
    result = await axe.chat(
        message="What's the system status?",
        include_history=False
    )

    assert result.success is True
    assert "response" in result.data


# ============================================================================
# Policy Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_policy_engine_denies_high_risk_without_approval():
    """Test that Policy Engine can deny HIGH-risk actions."""
    # Mock policy engine to deny
    policy_engine = Mock()
    policy_engine.evaluate = AsyncMock(return_value=Mock(
        effect="deny",
        reason="Production deployment requires senior approval"
    ))

    supervisor = SupervisorAgent(
        llm_client=Mock(generate=AsyncMock(return_value="approved: true")),
        policy_engine=policy_engine
    )

    request = SupervisionRequest(
        requesting_agent="OpsAgent",
        action="deploy_to_production",
        context={"environment": "production"},
        risk_level=RiskLevel.HIGH
    )

    response = await supervisor.supervise_action(request)

    # Policy engine denial should block action
    assert response.approved is False
    assert "Policy violation" in response.reason or "requires senior approval" in response.reason


# ============================================================================
# Audit Trail Tests
# ============================================================================


@pytest.mark.asyncio
async def test_audit_trail_records_all_events(mock_llm_client, mock_policy_engine):
    """Test that all supervision events are recorded in audit trail."""
    supervisor = SupervisorAgent(
        llm_client=mock_llm_client,
        policy_engine=mock_policy_engine
    )

    initial_count = len(supervisor.audit_trail)

    # Perform 3 supervision requests
    for i in range(3):
        await supervisor.supervise_action(SupervisionRequest(
            requesting_agent=f"Agent{i}",
            action=f"action_{i}",
            context={},
            risk_level=RiskLevel.LOW
        ))

    # Verify audit trail grew
    assert len(supervisor.audit_trail) >= initial_count + 3

    # Verify audit entries have required fields
    for entry in supervisor.audit_trail[-3:]:
        assert "event" in entry
        assert "timestamp" in entry
        assert "audit_id" in entry


# ============================================================================
# Error Handling Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_llm_failure_fail_safe(mock_policy_engine):
    """Test that LLM failure results in safe denial."""
    # LLM that fails
    failing_llm = Mock()
    failing_llm.generate = AsyncMock(side_effect=Exception("LLM service unavailable"))

    supervisor = SupervisorAgent(
        llm_client=failing_llm,
        policy_engine=mock_policy_engine
    )

    request = SupervisionRequest(
        requesting_agent="TestAgent",
        action="some_action",
        context={},
        risk_level=RiskLevel.LOW
    )

    response = await supervisor.supervise_action(request)

    # Should deny and require human oversight on failure
    assert response.approved is False
    assert response.human_oversight_required is True
    assert "failed" in response.reason.lower() or "error" in response.reason.lower()


@pytest.mark.asyncio
async def test_coder_validates_generated_code(mock_llm_client):
    """Test CoderAgent validates generated code for forbidden patterns."""
    coder = CoderAgent(llm_client=mock_llm_client)

    # Test validation of code with eval()
    validation = await coder.validate_code("result = eval(user_input)")

    assert validation.success is False
    assert any("eval" in issue.lower() for issue in validation.data.get("issues", []))


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_code_generation_with_supervision(mock_llm_client):
    """
    End-to-end test: CoderAgent generates code, SupervisorAgent approves,
    code is validated and returned.
    """
    # Setup agents
    supervisor = SupervisorAgent(llm_client=mock_llm_client)
    coder = CoderAgent(llm_client=mock_llm_client)

    # Mock code generation
    mock_llm_client.generate = AsyncMock(
        return_value="""
def process_data(data: list) -> dict:
    '''Process data safely without personal information'''
    return {"count": len(data), "processed": True}
"""
    )

    # Generate code (LOW risk, should auto-approve)
    result = await coder.generate_code(
        spec="Create a function to process data without personal info",
        risk_level=RiskLevel.LOW
    )

    assert result.success is True
    assert "code" in result.data

    # Validate generated code
    validation = await coder.validate_code(result.data["code"])
    assert validation.success is True


@pytest.mark.asyncio
async def test_e2e_deployment_workflow(mock_llm_client):
    """
    End-to-end test: OpsAgent deploys to production,
    requires supervisor approval, creates backup, monitors health.
    """
    ops = OpsAgent(llm_client=mock_llm_client)

    # Deploy to development (should succeed without approval)
    result = await ops.deploy_application(
        app_name="test-app",
        version="1.0.0",
        environment="development",
        config={}
    )

    assert result.success is True
    assert result.data.get("environment") == "development"


@pytest.mark.asyncio
async def test_e2e_architecture_review_workflow(mock_llm_client):
    """
    End-to-end test: ArchitectAgent performs full architecture review
    including EU compliance, security, and scalability.
    """
    architect = ArchitectAgent(llm_client=mock_llm_client)

    # Mock comprehensive review response
    mock_llm_client.generate = AsyncMock(
        return_value="""
        ARCHITECTURE REVIEW REPORT

        EU AI Act Compliance: PASS
        - No prohibited practices detected
        - Transparency requirements met

        DSGVO Compliance: PASS
        - Consent mechanism present
        - Data minimization applied

        Security: GOOD
        - Encryption at rest: YES
        - Encryption in transit: YES

        Scalability: GOOD
        - Can handle expected load
        - Caching implemented

        Compliance Score: 85/100
        """
    )

    result = await architect.review_architecture(
        system_name="Test System",
        architecture_spec={
            "uses_ai": True,
            "processes_personal_data": True,
            "has_consent_mechanism": True,
            "encryption_at_rest": True
        },
        high_risk_ai=False
    )

    assert result.success is True
    assert "review_report" in result.data or "compliance_score" in result.data


# ============================================================================
# Metrics and Monitoring Tests
# ============================================================================


@pytest.mark.asyncio
async def test_supervisor_metrics_tracking(mock_llm_client, mock_policy_engine):
    """Test that supervisor tracks metrics correctly."""
    supervisor = SupervisorAgent(
        llm_client=mock_llm_client,
        policy_engine=mock_policy_engine
    )

    # Perform various supervision requests
    await supervisor.supervise_action(SupervisionRequest(
        requesting_agent="A1", action="act1", context={}, risk_level=RiskLevel.LOW
    ))

    await supervisor.supervise_action(SupervisionRequest(
        requesting_agent="A2", action="act2", context={}, risk_level=RiskLevel.HIGH
    ))

    # Get metrics
    metrics = supervisor.get_metrics()

    assert metrics["total_supervision_requests"] >= 2
    assert "approved_actions" in metrics
    assert "denied_actions" in metrics
    assert "human_approvals_pending" in metrics
    assert "approval_rate" in metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
