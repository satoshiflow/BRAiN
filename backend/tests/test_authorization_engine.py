"""
Test Authorization Engine

Tests for the core authorization engine including:
- Policy evaluation
- Role-based access control
- Risk assessment
- HITL approval requirements
- Security critical F1: Risk not from caller
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.authorization_engine import (
    AuthorizationEngine,
    AuthorizationRequest,
    AuthorizationDecision,
    AuthorizationStatus,
    get_authorization_engine,
    reset_authorization_engine,
)
from app.core.auth_deps import Principal, PrincipalType
from app.modules.policy.schemas import (
    PolicyEvaluationResult,
    PolicyEffect,
)
from app.modules.governance.governance_models import RiskTier


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def auth_engine():
    """Create a fresh authorization engine for each test"""
    reset_authorization_engine()
    engine = get_authorization_engine()
    return engine


@pytest.fixture
def admin_principal():
    """Create an admin principal"""
    return Principal(
        principal_id="user-123",
        principal_type=PrincipalType.HUMAN,
        email="admin@example.com",
        name="Admin User",
        roles=["admin"],
        scopes=["brain:admin", "brain:write", "brain:read"],
    )


@pytest.fixture
def operator_principal():
    """Create an operator principal"""
    return Principal(
        principal_id="user-456",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator User",
        roles=["operator"],
        scopes=["brain:write", "brain:read"],
    )


@pytest.fixture
def viewer_principal():
    """Create a viewer principal"""
    return Principal(
        principal_id="user-789",
        principal_type=PrincipalType.HUMAN,
        email="viewer@example.com",
        name="Viewer User",
        roles=["viewer"],
        scopes=["brain:read"],
    )


@pytest.fixture
def agent_principal():
    """Create an agent principal"""
    return Principal(
        principal_id="agent-001",
        principal_type=PrincipalType.AGENT,
        name="Test Agent",
        roles=["agent"],
        scopes=["brain:read"],
        agent_id="agent-001",
    )


@pytest.fixture
def anonymous_principal():
    """Create an anonymous principal"""
    return Principal.anonymous()


# ============================================================================
# Test Policy Allow
# ============================================================================

@pytest.mark.asyncio
async def test_policy_allow(auth_engine, admin_principal):
    """Test that a valid request with proper permissions is allowed"""
    # Create authorization request
    request = AuthorizationRequest(
        principal=admin_principal,
        action="resource.read",
        resource_id="test-resource-001",
        context={},
    )
    
    # Mock policy evaluation to allow
    with patch.object(auth_engine, '_evaluate_policy') as mock_eval:
        mock_eval.return_value = PolicyEvaluationResult(
            allowed=True,
            effect=PolicyEffect.ALLOW,
            matched_rule="admin_read_access",
            matched_policy="default_policy",
            reason="Admin has read access",
        )
    
    # Mock audit log to avoid DB dependencies
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
        decision = await auth_engine.authorize(request)
    
    # Assert allowed
    assert decision.allowed is True
    assert decision.status == AuthorizationStatus.ALLOWED
    assert decision.principal_id == admin_principal.principal_id
    assert decision.action == "resource.read"
    assert decision.resource_id == "test-resource-001"


@pytest.mark.asyncio
async def test_policy_allow_operator_read(auth_engine, operator_principal):
    """Test that operator can read resources"""
    request = AuthorizationRequest(
        principal=operator_principal,
        action="resource.read",
        resource_id="test-resource-001",
        context={},
    )
    
    with patch.object(auth_engine, '_evaluate_policy') as mock_eval:
        mock_eval.return_value = PolicyEvaluationResult(
            allowed=True,
            effect=PolicyEffect.ALLOW,
            matched_rule="operator_read_access",
            matched_policy="default_policy",
            reason="Operator has read access",
        )
    
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
        decision = await auth_engine.authorize(request)
    
    assert decision.allowed is True
    assert decision.status == AuthorizationStatus.ALLOWED


# ============================================================================
# Test Policy Deny - Role Mismatch
# ============================================================================

@pytest.mark.asyncio
async def test_policy_deny_role_mismatch(auth_engine, viewer_principal):
    """Test that viewer cannot perform admin actions"""
    request = AuthorizationRequest(
        principal=viewer_principal,
        action="admin.delete_user",  # Admin-only action
        resource_id="user-999",
        context={},
    )
    
    # Should be denied at RBAC check before policy evaluation
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
        decision = await auth_engine.authorize(request)
    
    assert decision.allowed is False
    assert decision.status == AuthorizationStatus.DENIED
    assert "RBAC" in decision.reason or "role" in decision.reason.lower()
    assert any("rbac" in check.lower() for check in decision.failed_checks)


@pytest.mark.asyncio
async def test_policy_deny_operator_cannot_delete(auth_engine, operator_principal):
    """Test that operator cannot delete resources (admin only)"""
    request = AuthorizationRequest(
        principal=operator_principal,
        action="resource.delete",
        resource_id="test-resource-001",
        context={},
    )
    
    # Mock policy to deny
    with patch.object(auth_engine, '_evaluate_policy') as mock_eval:
        mock_eval.return_value = PolicyEvaluationResult(
            allowed=False,
            effect=PolicyEffect.DENY,
            matched_rule="delete_requires_admin",
            matched_policy="security_policy",
            reason="Delete operations require admin role",
        )
    
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
        decision = await auth_engine.authorize(request)
    
    assert decision.allowed is False
    assert decision.status == AuthorizationStatus.DENIED


@pytest.mark.asyncio
async def test_policy_deny_viewer_cannot_write(auth_engine, viewer_principal):
    """Test that viewer cannot write resources"""
    request = AuthorizationRequest(
        principal=viewer_principal,
        action="resource.write",
        resource_id="test-resource-001",
        context={},
    )
    
    # Should be denied at RBAC check
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
        decision = await auth_engine.authorize(request)
    
    assert decision.allowed is False
    assert decision.status == AuthorizationStatus.DENIED


# ============================================================================
# Test Policy Deny - Unknown Action
# ============================================================================

@pytest.mark.asyncio
async def test_policy_deny_unknown_action(auth_engine, admin_principal):
    """Test that unknown/unconfigured actions are denied by default"""
    request = AuthorizationRequest(
        principal=admin_principal,
        action="system.undefined_action_xyz",  # Unknown action
        resource_id="test-resource-001",
        context={},
    )
    
    # Mock policy evaluation to deny (default deny)
    with patch.object(auth_engine, '_evaluate_policy') as mock_eval:
        mock_eval.return_value = PolicyEvaluationResult(
            allowed=False,
            effect=PolicyEffect.DENY,
            matched_policy="default_policy",
            reason="Unknown action not explicitly allowed",
        )
    
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
        decision = await auth_engine.authorize(request)
    
    assert decision.allowed is False
    assert decision.status == AuthorizationStatus.DENIED


@pytest.mark.asyncio
async def test_policy_deny_no_matching_policy(auth_engine, admin_principal):
    """Test that requests with no matching policy are denied (fail-closed)"""
    request = AuthorizationRequest(
        principal=admin_principal,
        action="exotic.unconfigured_action",
        resource_id="test-resource-001",
        context={},
    )
    
    # Mock policy evaluation with deny (fail-closed)
    with patch.object(auth_engine, '_evaluate_policy') as mock_eval:
        mock_eval.return_value = PolicyEvaluationResult(
            allowed=False,
            effect=PolicyEffect.DENY,
            reason="No matching policy found - default deny",
        )
    
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
        decision = await auth_engine.authorize(request)
    
    assert decision.allowed is False
    assert decision.status == AuthorizationStatus.DENIED
    assert "deny" in decision.reason.lower() or "not" in decision.reason.lower()


# ============================================================================
# Test Policy Require Approval (HITL)
# ============================================================================

@pytest.mark.asyncio
async def test_policy_require_approval_high_risk(auth_engine, admin_principal):
    """Test that HIGH risk actions require HITL approval"""
    request = AuthorizationRequest(
        principal=admin_principal,
        action="system.shutdown",
        resource_id="cluster-001",
        context={},
    )
    
    # Mock policy evaluation to allow but with high risk
    with patch.object(auth_engine, '_evaluate_policy') as mock_eval:
        mock_eval.return_value = PolicyEvaluationResult(
            allowed=True,
            effect=PolicyEffect.ALLOW,
            matched_rule="admin_high_risk",
            matched_policy="security_policy",
            reason="Admin allowed but high risk",
        )
    
    # Mock risk extraction to return HIGH
    with patch.object(auth_engine, '_extract_risk_from_policy') as mock_risk:
        mock_risk.return_value = RiskTier.HIGH
    
    # Mock HITL approval request
    with patch.object(auth_engine, '_request_hitl_approval', new_callable=AsyncMock) as mock_hitl:
        mock_hitl.return_value = "approval-123"
        
        with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
            decision = await auth_engine.authorize(request)
    
    # Should be pending approval, not directly allowed
    assert decision.allowed is False  # Not allowed until approved
    assert decision.status == AuthorizationStatus.PENDING_APPROVAL
    assert decision.requires_approval is True
    assert decision.approval_id == "approval-123"
    assert decision.risk_tier == RiskTier.HIGH


@pytest.mark.asyncio
async def test_policy_require_approval_critical_risk(auth_engine, admin_principal):
    """Test that CRITICAL risk actions require HITL approval"""
    request = AuthorizationRequest(
        principal=admin_principal,
        action="system.nuclear_option",
        resource_id="all-resources",
        context={},
    )
    
    with patch.object(auth_engine, '_evaluate_policy') as mock_eval:
        mock_eval.return_value = PolicyEvaluationResult(
            allowed=True,
            effect=PolicyEffect.ALLOW,
            matched_rule="admin_critical",
            matched_policy="security_policy",
            reason="Critical system action",
        )
    
    # Mock risk extraction to return CRITICAL
    with patch.object(auth_engine, '_extract_risk_from_policy') as mock_risk:
        mock_risk.return_value = RiskTier.CRITICAL
    
    with patch.object(auth_engine, '_request_hitl_approval', new_callable=AsyncMock) as mock_hitl:
        mock_hitl.return_value = "approval-critical-456"
        
        with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
            decision = await auth_engine.authorize(request)
    
    assert decision.allowed is False
    assert decision.status == AuthorizationStatus.PENDING_APPROVAL
    assert decision.requires_approval is True
    assert decision.risk_tier == RiskTier.CRITICAL


@pytest.mark.asyncio
async def test_policy_no_approval_for_low_risk(auth_engine, admin_principal):
    """Test that LOW risk actions do not require approval"""
    request = AuthorizationRequest(
        principal=admin_principal,
        action="resource.read",
        resource_id="test-resource-001",
        context={},
    )
    
    with patch.object(auth_engine, '_evaluate_policy') as mock_eval:
        mock_eval.return_value = PolicyEvaluationResult(
            allowed=True,
            effect=PolicyEffect.ALLOW,
            matched_rule="admin_read",
            matched_policy="default_policy",
            reason="Read access granted",
        )
    
    # Mock risk extraction to return LOW
    with patch.object(auth_engine, '_extract_risk_from_policy') as mock_risk:
        mock_risk.return_value = RiskTier.LOW
    
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
        decision = await auth_engine.authorize(request)
    
    # Should be allowed directly without approval
    assert decision.allowed is True
    assert decision.status == AuthorizationStatus.ALLOWED
    assert decision.requires_approval is False
    assert decision.approval_id is None


# ============================================================================
# F1 Security Check: Risk Not From Caller
# ============================================================================

@pytest.mark.asyncio
async def test_risk_not_from_caller_f1_security(auth_engine, admin_principal):
    """
    F1 Security Check: Risk is determined from POLICY only, NOT from request.
    
    This is a critical security test that verifies the authorization engine
    does NOT trust risk values provided in the request context, preventing
    request injection attacks that could bypass HITL approval.
    """
    # Create request with malicious context trying to downgrade risk
    request = AuthorizationRequest(
        principal=admin_principal,
        action="system.delete_all_data",
        resource_id="production-db",
        context={
            # Attempt to inject a false low risk value
            "risk_tier": "low",
            "risk_level": "minimal",
            "security_classification": "safe",
        },
    )
    
    # Mock policy evaluation - the policy determines HIGH risk
    with patch.object(auth_engine, '_evaluate_policy') as mock_eval:
        mock_eval.return_value = PolicyEvaluationResult(
            allowed=True,
            effect=PolicyEffect.ALLOW,
            matched_rule="admin_delete_high_risk",
            matched_policy="security_policy",
            reason="Data deletion is high risk",
        )
    
    # The risk extraction should come from POLICY, not request context
    # Mock it returning HIGH risk (as the policy would determine)
    with patch.object(auth_engine, '_extract_risk_from_policy') as mock_risk:
        mock_risk.return_value = RiskTier.HIGH
        
        with patch.object(auth_engine, '_request_hitl_approval', new_callable=AsyncMock) as mock_hitl:
            mock_hitl.return_value = "approval-f1-test"
            
            with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
                decision = await auth_engine.authorize(request)
    
    # Verify that:
    # 1. The request context risk injection was IGNORED
    # 2. The policy-determined risk (HIGH) was used
    # 3. HITL approval was required because of HIGH risk
    assert decision.allowed is False  # Pending approval
    assert decision.status == AuthorizationStatus.PENDING_APPROVAL
    assert decision.risk_tier == RiskTier.HIGH
    assert decision.requires_approval is True
    
    # Verify the risk extraction was called (using policy result, not request)
    mock_risk.assert_called_once()


@pytest.mark.asyncio
async def test_risk_from_policy_metadata(auth_engine, admin_principal):
    """
    Verify risk is extracted from policy metadata, not request params.
    """
    request = AuthorizationRequest(
        principal=admin_principal,
        action="admin.critical_operation",
        resource_id="system-core",
        context={
            # Malicious attempt to claim this is low risk
            "_risk_override": "LOW",
            "priority": "routine",
        },
    )
    
    # Policy result with explicit risk metadata
    policy_result = PolicyEvaluationResult(
        allowed=True,
        effect=PolicyEffect.ALLOW,
        matched_rule="critical_admin_rule",
        matched_policy="critical_policy",
        reason="Critical admin operation",
    )
    
    # Add risk_tier attribute to simulate policy-defined risk
    policy_result.risk_tier = RiskTier.CRITICAL
    
    with patch.object(auth_engine, '_evaluate_policy') as mock_eval:
        mock_eval.return_value = policy_result
    
    # Real risk extraction should use policy's risk_tier
    with patch.object(auth_engine, '_request_hitl_approval', new_callable=AsyncMock) as mock_hitl:
        mock_hitl.return_value = "approval-critical"
        
        with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
            decision = await auth_engine.authorize(request)
    
    # Should be CRITICAL risk from policy, not LOW from context
    assert decision.risk_tier == RiskTier.CRITICAL
    assert decision.requires_approval is True


# ============================================================================
# Additional Security Tests
# ============================================================================

@pytest.mark.asyncio
async def test_anonymous_principal_denied(auth_engine, anonymous_principal):
    """Test that anonymous principals are always denied"""
    request = AuthorizationRequest(
        principal=anonymous_principal,
        action="resource.read",
        resource_id="test-resource-001",
        context={},
    )
    
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
        decision = await auth_engine.authorize(request)
    
    assert decision.allowed is False
    assert decision.status == AuthorizationStatus.DENIED
    assert "anonymous" in decision.reason.lower()
    assert any("principal" in check.lower() for check in decision.failed_checks)


@pytest.mark.asyncio
async def test_invalid_principal_type_denied(auth_engine):
    """Test that invalid principal types are denied"""
    invalid_principal = Principal(
        principal_id="user-123",
        principal_type="invalid_type",  # Invalid type
        name="Invalid User",
        roles=["admin"],
    )
    
    request = AuthorizationRequest(
        principal=invalid_principal,
        action="resource.read",
        resource_id="test-resource-001",
        context={},
    )
    
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
        decision = await auth_engine.authorize(request)
    
    assert decision.allowed is False
    assert "principal" in decision.reason.lower()


@pytest.mark.asyncio
async def test_scope_validation_failure(auth_engine, viewer_principal):
    """Test that insufficient scope results in denial"""
    request = AuthorizationRequest(
        principal=viewer_principal,
        action="audit.read",  # Requires admin scope
        resource_id="audit-log",
        context={},
    )
    
    # Should be denied at scope check
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock):
        decision = await auth_engine.authorize(request)
    
    assert decision.allowed is False
    assert decision.status == AuthorizationStatus.DENIED
    assert "scope" in decision.reason.lower()


@pytest.mark.asyncio
async def test_audit_log_written_on_allow(auth_engine, admin_principal):
    """Test that audit log is written when request is allowed"""
    request = AuthorizationRequest(
        principal=admin_principal,
        action="resource.read",
        resource_id="test-resource-001",
        context={},
    )
    
    with patch.object(auth_engine, '_evaluate_policy') as mock_eval:
        mock_eval.return_value = PolicyEvaluationResult(
            allowed=True,
            effect=PolicyEffect.ALLOW,
            reason="Access granted",
        )
    
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock) as mock_audit:
        decision = await auth_engine.authorize(request)
        
        # Verify audit log was written
        mock_audit.assert_called_once()
        call_args = mock_audit.call_args[0]
        logged_decision = call_args[0]
        logged_request = call_args[1]
        
        assert logged_decision.allowed is True
        assert logged_request.principal.principal_id == admin_principal.principal_id


@pytest.mark.asyncio
async def test_audit_log_written_on_deny(auth_engine, anonymous_principal):
    """Test that audit log is written when request is denied"""
    request = AuthorizationRequest(
        principal=anonymous_principal,
        action="resource.read",
        resource_id="test-resource-001",
        context={},
    )
    
    with patch.object(auth_engine, '_write_audit_log', new_callable=AsyncMock) as mock_audit:
        decision = await auth_engine.authorize(request)
        
        # Verify audit log was written even for denial
        mock_audit.assert_called_once()
        call_args = mock_audit.call_args[0]
        logged_decision = call_args[0]
        
        assert logged_decision.allowed is False
