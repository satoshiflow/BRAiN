"""
Tests for SupervisorAgent

Tests the constitutional framework guardian including:
- Risk-based supervision
- Policy Engine integration
- Human-in-the-loop workflows
- Audit trail
- LLM constitutional checks
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from brain.agents.supervisor_agent import (
    SupervisorAgent,
    get_supervisor_agent,
    CONSTITUTIONAL_PROMPT,
)
from app.modules.supervisor.schemas import (
    RiskLevel,
    SupervisionRequest,
    SupervisionResponse,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    client = Mock()
    client.generate = AsyncMock(return_value="approved: true\nreason: Action is safe and compliant")
    return client


@pytest.fixture
def mock_policy_engine():
    """Mock Policy Engine"""
    engine = Mock()
    engine.evaluate = AsyncMock(return_value=Mock(
        effect="allow",
        reason="Policy allows this action"
    ))
    return engine


@pytest.fixture
def supervisor_agent(mock_llm_client, mock_policy_engine):
    """Create SupervisorAgent instance for testing"""
    return SupervisorAgent(
        llm_client=mock_llm_client,
        policy_engine=mock_policy_engine,
    )


# ============================================================================
# SupervisorAgent Initialization Tests
# ============================================================================


def test_supervisor_agent_initialization(supervisor_agent):
    """Test SupervisorAgent initializes correctly"""
    assert supervisor_agent.config.name == "SupervisorAgent"
    assert supervisor_agent.config.role == "SUPERVISOR"
    assert supervisor_agent.config.temperature == 0.1  # Low for deterministic
    assert CONSTITUTIONAL_PROMPT in supervisor_agent.config.system_prompt
    assert supervisor_agent.total_supervision_requests == 0


def test_supervisor_singleton():
    """Test supervisor singleton pattern"""
    supervisor1 = get_supervisor_agent()
    supervisor2 = get_supervisor_agent()
    assert supervisor1 is supervisor2  # Same instance


# ============================================================================
# Risk-Based Supervision Tests
# ============================================================================


@pytest.mark.asyncio
async def test_low_risk_auto_approval(supervisor_agent, mock_llm_client):
    """Test LOW risk actions get LLM evaluation"""
    request = SupervisionRequest(
        requesting_agent="TestAgent",
        action="read_logs",
        context={"type": "read_only"},
        risk_level=RiskLevel.LOW,
    )

    response = await supervisor_agent.supervise_action(request)

    assert response.approved is True
    assert response.human_oversight_required is False
    assert response.audit_id is not None
    assert supervisor_agent.total_supervision_requests == 1
    assert supervisor_agent.approved_actions == 1


@pytest.mark.asyncio
async def test_high_risk_requires_human_approval(supervisor_agent):
    """Test HIGH risk actions trigger human approval"""
    request = SupervisionRequest(
        requesting_agent="CoderAgent",
        action="generate_odoo_module",
        context={"uses_personal_data": True},
        risk_level=RiskLevel.HIGH,
    )

    response = await supervisor_agent.supervise_action(request)

    assert response.approved is False
    assert response.human_oversight_required is True
    assert response.human_oversight_token is not None
    assert response.human_oversight_token.startswith("HITL-")
    assert "EU AI Act Art. 16" in response.reason or "DSGVO Art. 22" in response.reason
    assert supervisor_agent.human_approvals_pending == 1


@pytest.mark.asyncio
async def test_critical_risk_requires_human_approval(supervisor_agent):
    """Test CRITICAL risk actions always require human approval"""
    request = SupervisionRequest(
        requesting_agent="OpsAgent",
        action="deploy_to_production",
        context={"environment": "production"},
        risk_level=RiskLevel.CRITICAL,
    )

    response = await supervisor_agent.supervise_action(request)

    assert response.approved is False
    assert response.human_oversight_required is True
    assert response.human_oversight_token is not None


# ============================================================================
# Policy Engine Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_policy_engine_deny(supervisor_agent, mock_policy_engine):
    """Test policy engine denial blocks action"""
    # Mock policy engine to deny
    mock_policy_engine.evaluate = AsyncMock(return_value=Mock(
        effect="deny",
        reason="Policy violation: insufficient permissions"
    ))

    request = SupervisionRequest(
        requesting_agent="TestAgent",
        action="delete_database",
        context={},
        risk_level=RiskLevel.MEDIUM,
    )

    response = await supervisor_agent.supervise_action(request)

    assert response.approved is False
    assert "Policy violation" in response.reason
    assert supervisor_agent.denied_actions == 1


@pytest.mark.asyncio
async def test_policy_engine_warn(supervisor_agent, mock_policy_engine):
    """Test policy engine warning is recorded"""
    # Mock policy engine to warn
    mock_policy_engine.evaluate = AsyncMock(return_value=Mock(
        effect="warn",
        reason="Warning: potentially risky operation"
    ))

    request = SupervisionRequest(
        requesting_agent="TestAgent",
        action="modify_config",
        context={},
        risk_level=RiskLevel.LOW,
    )

    response = await supervisor_agent.supervise_action(request)

    # Should proceed but with warning recorded
    assert len(response.policy_violations) > 0
    assert "potentially risky" in response.policy_violations[0]


# ============================================================================
# LLM Constitutional Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_llm_denies_action(supervisor_agent, mock_llm_client):
    """Test LLM constitutional check can deny action"""
    # Mock LLM to deny
    mock_llm_client.generate = AsyncMock(
        return_value="approved: false\nreason: Violates DSGVO Art. 6 - no legal basis\nhuman_oversight_required: false"
    )

    request = SupervisionRequest(
        requesting_agent="CoderAgent",
        action="store_user_data",
        context={"without_consent": True},
        risk_level=RiskLevel.MEDIUM,
    )

    response = await supervisor_agent.supervise_action(request)

    assert response.approved is False
    assert "DSGVO" in response.reason
    assert supervisor_agent.denied_actions == 1


@pytest.mark.asyncio
async def test_llm_approves_compliant_action(supervisor_agent, mock_llm_client):
    """Test LLM approves DSGVO-compliant action"""
    mock_llm_client.generate = AsyncMock(
        return_value="approved: true\nreason: Compliant with DSGVO Art. 6 - legitimate interest"
    )

    request = SupervisionRequest(
        requesting_agent="CoderAgent",
        action="generate_api_endpoint",
        context={"purpose": "public API", "no_personal_data": True},
        risk_level=RiskLevel.LOW,
    )

    response = await supervisor_agent.supervise_action(request)

    assert response.approved is True
    assert "Compliant" in response.reason


# ============================================================================
# Audit Trail Tests
# ============================================================================


@pytest.mark.asyncio
async def test_audit_trail_records_decisions(supervisor_agent):
    """Test all decisions are recorded in audit trail"""
    initial_audit_count = len(supervisor_agent.audit_trail)

    request = SupervisionRequest(
        requesting_agent="TestAgent",
        action="test_action",
        context={},
        risk_level=RiskLevel.LOW,
    )

    await supervisor_agent.supervise_action(request)

    assert len(supervisor_agent.audit_trail) == initial_audit_count + 1

    latest_audit = supervisor_agent.audit_trail[-1]
    assert latest_audit["event"] == "supervision_completed"
    assert "audit_id" in latest_audit
    assert "timestamp" in latest_audit


@pytest.mark.asyncio
async def test_human_approval_token_generation(supervisor_agent):
    """Test human approval token is generated and logged"""
    request = SupervisionRequest(
        requesting_agent="OpsAgent",
        action="production_deployment",
        context={},
        risk_level=RiskLevel.CRITICAL,
    )

    response = await supervisor_agent.supervise_action(request)

    # Find token generation in audit trail
    token_audit = [
        entry for entry in supervisor_agent.audit_trail
        if entry.get("event") == "human_approval_token_generated"
    ]

    assert len(token_audit) > 0
    assert token_audit[0]["token"] == response.human_oversight_token


# ============================================================================
# Metrics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_supervision_metrics(supervisor_agent, mock_llm_client):
    """Test supervision metrics are tracked correctly"""
    # Approve one
    mock_llm_client.generate = AsyncMock(return_value="approved: true\nreason: OK")

    await supervisor_agent.supervise_action(SupervisionRequest(
        requesting_agent="TestAgent",
        action="safe_action",
        context={},
        risk_level=RiskLevel.LOW,
    ))

    # Deny one
    mock_llm_client.generate = AsyncMock(return_value="approved: false\nreason: Not OK")

    await supervisor_agent.supervise_action(SupervisionRequest(
        requesting_agent="TestAgent",
        action="unsafe_action",
        context={},
        risk_level=RiskLevel.MEDIUM,
    ))

    # Require human approval
    await supervisor_agent.supervise_action(SupervisionRequest(
        requesting_agent="TestAgent",
        action="critical_action",
        context={},
        risk_level=RiskLevel.HIGH,
    ))

    metrics = supervisor_agent.get_metrics()

    assert metrics["total_supervision_requests"] == 3
    assert metrics["approved_actions"] == 1
    assert metrics["denied_actions"] == 1
    assert metrics["human_approvals_pending"] == 1
    assert metrics["approval_rate"] == 1/3


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_llm_failure_denies_action(supervisor_agent, mock_llm_client):
    """Test LLM failure results in denial (fail-safe)"""
    mock_llm_client.generate = AsyncMock(side_effect=Exception("LLM service down"))

    request = SupervisionRequest(
        requesting_agent="TestAgent",
        action="some_action",
        context={},
        risk_level=RiskLevel.LOW,
    )

    response = await supervisor_agent.supervise_action(request)

    assert response.approved is False
    assert "Constitutional check failed" in response.reason
    assert response.human_oversight_required is True  # Escalate on error


@pytest.mark.asyncio
async def test_policy_engine_failure_continues(supervisor_agent, mock_policy_engine):
    """Test policy engine failure doesn't block (continues to LLM)"""
    mock_policy_engine.evaluate = AsyncMock(side_effect=Exception("Policy engine error"))

    request = SupervisionRequest(
        requesting_agent="TestAgent",
        action="some_action",
        context={},
        risk_level=RiskLevel.LOW,
    )

    # Should not raise exception, continues to LLM check
    response = await supervisor_agent.supervise_action(request)

    # LLM should still evaluate
    assert response.audit_id is not None


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_supervision_workflow():
    """Test complete supervision workflow from request to response"""
    # Create supervisor with real config but mocked LLM
    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value="approved: true\nreason: All checks passed")

    supervisor = SupervisorAgent(llm_client=mock_llm)

    request = SupervisionRequest(
        requesting_agent="CoderAgent",
        action="generate_code",
        context={"language": "python", "purpose": "utility function"},
        risk_level=RiskLevel.LOW,
        reason="Generate helper function for data processing",
    )

    response = await supervisor.supervise_action(request)

    # Verify complete workflow
    assert isinstance(response, SupervisionResponse)
    assert response.approved is True
    assert response.audit_id is not None
    assert len(supervisor.audit_trail) > 0
    assert supervisor.total_supervision_requests == 1
    assert supervisor.approved_actions == 1
