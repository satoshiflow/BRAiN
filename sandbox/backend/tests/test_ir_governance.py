"""
IR Governance Tests - Sprint 9 (P0)

Deterministic tests for IR governance kernel.

Test Coverage:
1. Canonicalization stable hash
2. Schema forbids extra fields
3. Reject missing idempotency_key
4. Reject unknown action/provider (fail-closed)
5. PASS for safe Tier 0/1 IR
6. ESCALATE for Tier 2 IR requiring approval
7. Approval token single-use + TTL
8. Diff-audit rejects extra DAG node
9. Diff-audit rejects hash mismatch
"""

import sys
import os
import pytest
import time
from datetime import datetime, timedelta

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.modules.ir_governance.schemas import (
    IR,
    IRStep,
    IRAction,
    IRProvider,
    RiskTier,
    IRValidationStatus,
    ApprovalConsumeRequest,
    ApprovalStatus,
)
from app.modules.ir_governance.canonicalization import (
    canonical_json,
    ir_hash,
    step_hash,
)
from app.modules.ir_governance.validator import IRValidator
from app.modules.ir_governance.approvals import ApprovalsService
from app.modules.ir_governance.diff_audit import DiffAuditGate


# ============================================================================
# Test 1: Canonicalization Stable Hash
# ============================================================================

def test_canonicalization_stable_hash():
    """Test 1: Canonicalization produces stable, deterministic hashes."""

    step1 = IRStep(
        action=IRAction.DEPLOY_WEBSITE,
        provider=IRProvider.DEPLOY_PROVIDER_V1,
        resource="site:staging",
        params={"repo": "https://example.com/repo.git"},
        idempotency_key="deploy-staging-001",
    )

    step2 = IRStep(
        action=IRAction.DEPLOY_WEBSITE,
        provider=IRProvider.DEPLOY_PROVIDER_V1,
        resource="site:staging",
        params={"repo": "https://example.com/repo.git"},
        idempotency_key="deploy-staging-001",
    )

    # Same step → same hash
    hash1 = step_hash(step1)
    hash2 = step_hash(step2)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex length


def test_canonicalization_different_hash_on_change():
    """Test that changing a field changes the hash."""

    step1 = IRStep(
        action=IRAction.DEPLOY_WEBSITE,
        provider=IRProvider.DEPLOY_PROVIDER_V1,
        resource="site:staging",
        params={"repo": "https://example.com/repo.git"},
        idempotency_key="deploy-staging-001",
    )

    step2 = IRStep(
        action=IRAction.DEPLOY_WEBSITE,
        provider=IRProvider.DEPLOY_PROVIDER_V1,
        resource="site:production",  # Changed
        params={"repo": "https://example.com/repo.git"},
        idempotency_key="deploy-staging-001",
    )

    hash1 = step_hash(step1)
    hash2 = step_hash(step2)

    assert hash1 != hash2


# ============================================================================
# Test 2: Schema Forbids Extra Fields
# ============================================================================

def test_schema_forbids_extra_fields():
    """Test 2: Schema rejects unknown fields (fail-closed)."""

    with pytest.raises(ValueError) as exc_info:
        IRStep(
            action=IRAction.DEPLOY_WEBSITE,
            provider=IRProvider.DEPLOY_PROVIDER_V1,
            resource="site:staging",
            idempotency_key="deploy-001",
            params={},
            unknown_field="should_fail",  # Extra field
        )

    assert "extra" in str(exc_info.value).lower() or "forbidden" in str(exc_info.value).lower()


# ============================================================================
# Test 3: Reject Missing Idempotency Key
# ============================================================================

def test_reject_missing_idempotency_key():
    """Test 3: Schema requires non-empty idempotency_key."""

    with pytest.raises(ValueError) as exc_info:
        IRStep(
            action=IRAction.DEPLOY_WEBSITE,
            provider=IRProvider.DEPLOY_PROVIDER_V1,
            resource="site:staging",
            params={},
            idempotency_key="",  # Empty
        )

    assert "idempotency" in str(exc_info.value).lower()


def test_reject_whitespace_only_idempotency_key():
    """Test that whitespace-only idempotency_key is rejected."""

    with pytest.raises(ValueError) as exc_info:
        IRStep(
            action=IRAction.DEPLOY_WEBSITE,
            provider=IRProvider.DEPLOY_PROVIDER_V1,
            resource="site:staging",
            params={},
            idempotency_key="   ",  # Whitespace only
        )

    assert "idempotency" in str(exc_info.value).lower()


# ============================================================================
# Test 4: Reject Unknown Action/Provider (Fail-Closed)
# ============================================================================

def test_reject_unknown_action():
    """Test 4a: Unknown action is rejected (fail-closed)."""

    with pytest.raises((ValueError, KeyError)) as exc_info:
        IRStep(
            action="unknown.action",  # Not in IRAction enum
            provider=IRProvider.DEPLOY_PROVIDER_V1,
            resource="site:staging",
            idempotency_key="test-001",
            params={},
        )

    # Should fail validation


def test_reject_unknown_provider():
    """Test 4b: Unknown provider is rejected (fail-closed)."""

    with pytest.raises((ValueError, KeyError)) as exc_info:
        IRStep(
            action=IRAction.DEPLOY_WEBSITE,
            provider="unknown.provider",  # Not in IRProvider enum
            resource="site:staging",
            idempotency_key="test-001",
            params={},
        )

    # Should fail validation


# ============================================================================
# Test 5: PASS for Safe Tier 0/1 IR
# ============================================================================

def test_pass_for_safe_ir():
    """Test 5: Safe IR (Tier 0/1) passes validation."""

    validator = IRValidator()

    ir = IR(
        tenant_id="tenant_test",
        steps=[
            IRStep(
                action=IRAction.DEPLOY_WEBSITE,
                provider=IRProvider.DEPLOY_PROVIDER_V1,
                resource="site:dev",
                params={"repo": "https://example.com/repo.git"},
                constraints={"environment": "dev"},
                idempotency_key="deploy-dev-001",
            )
        ],
    )

    result = validator.validate_ir(ir)

    assert result.status == IRValidationStatus.PASS
    assert result.risk_tier <= RiskTier.TIER_1
    assert result.requires_approval is False
    assert len(result.violations) == 0


# ============================================================================
# Test 6: ESCALATE for Tier 2 IR Requiring Approval
# ============================================================================

def test_escalate_for_tier2_ir():
    """Test 6: Tier 2 IR (requires approval) triggers ESCALATE."""

    validator = IRValidator()

    ir = IR(
        tenant_id="tenant_test",
        steps=[
            IRStep(
                action=IRAction.DNS_UPDATE_RECORDS,  # Tier 2 action
                provider=IRProvider.DNS_HETZNER,
                resource="zone:example.com",
                params={"records": [{"type": "A", "name": "@", "value": "192.0.2.1"}]},
                constraints={"environment": "production"},  # Production scope
                idempotency_key="dns-prod-001",
            )
        ],
    )

    result = validator.validate_ir(ir)

    assert result.status == IRValidationStatus.ESCALATE
    assert result.risk_tier >= RiskTier.TIER_2
    assert result.requires_approval is True


def test_escalate_for_destructive_action():
    """Test that destructive actions trigger ESCALATE."""

    validator = IRValidator()

    ir = IR(
        tenant_id="tenant_test",
        steps=[
            IRStep(
                action=IRAction.DNS_DELETE_ZONE,  # Destructive
                provider=IRProvider.DNS_HETZNER,
                resource="zone:example.com",
                params={},
                idempotency_key="dns-delete-001",
            )
        ],
    )

    result = validator.validate_ir(ir)

    assert result.status == IRValidationStatus.ESCALATE
    assert result.risk_tier == RiskTier.TIER_3
    assert result.requires_approval is True


# ============================================================================
# Test 7: Approval Token Single-Use + TTL
# ============================================================================

def test_approval_token_single_use():
    """Test 7a: Approval token is single-use."""

    service = ApprovalsService()

    # Create approval
    approval, token = service.create_approval(
        tenant_id="tenant_test",
        ir_hash="abc123",
        ttl_seconds=3600,
    )

    # Consume once
    consume_request = ApprovalConsumeRequest(
        tenant_id="tenant_test",
        ir_hash="abc123",
        token=token,
    )
    result1 = service.consume_approval(consume_request)

    assert result1.success is True
    assert result1.status == ApprovalStatus.CONSUMED

    # Try to consume again (should fail)
    result2 = service.consume_approval(consume_request)

    assert result2.success is False
    assert result2.status == ApprovalStatus.CONSUMED
    assert "already consumed" in result2.message.lower()


def test_approval_token_ttl():
    """Test 7b: Approval token respects TTL."""

    service = ApprovalsService()

    # Create approval with 1-second TTL
    approval, token = service.create_approval(
        tenant_id="tenant_test",
        ir_hash="abc123",
        ttl_seconds=1,
    )

    # Wait for expiration
    time.sleep(1.5)

    # Try to consume (should fail - expired)
    consume_request = ApprovalConsumeRequest(
        tenant_id="tenant_test",
        ir_hash="abc123",
        token=token,
    )
    result = service.consume_approval(consume_request)

    assert result.success is False
    assert result.status == ApprovalStatus.EXPIRED
    assert "expired" in result.message.lower()


def test_approval_tenant_id_mismatch():
    """Test that approval validates tenant_id match."""

    service = ApprovalsService()

    # Create approval
    approval, token = service.create_approval(
        tenant_id="tenant_a",
        ir_hash="abc123",
        ttl_seconds=3600,
    )

    # Try to consume with wrong tenant_id
    consume_request = ApprovalConsumeRequest(
        tenant_id="tenant_b",  # Wrong tenant
        ir_hash="abc123",
        token=token,
    )
    result = service.consume_approval(consume_request)

    assert result.success is False
    assert result.status == ApprovalStatus.INVALID
    assert "mismatch" in result.message.lower()


def test_approval_ir_hash_mismatch():
    """Test that approval validates ir_hash match."""

    service = ApprovalsService()

    # Create approval
    approval, token = service.create_approval(
        tenant_id="tenant_test",
        ir_hash="abc123",
        ttl_seconds=3600,
    )

    # Try to consume with wrong ir_hash
    consume_request = ApprovalConsumeRequest(
        tenant_id="tenant_test",
        ir_hash="def456",  # Wrong hash
        token=token,
    )
    result = service.consume_approval(consume_request)

    assert result.success is False
    assert result.status == ApprovalStatus.INVALID
    assert "mismatch" in result.message.lower()


# ============================================================================
# Test 8: Diff-Audit Rejects Extra DAG Node
# ============================================================================

def test_diff_audit_rejects_extra_dag_node():
    """Test 8: Diff-audit rejects DAG with extra nodes not in IR."""

    gate = DiffAuditGate()

    ir = IR(
        tenant_id="tenant_test",
        steps=[
            IRStep(
                action=IRAction.DEPLOY_WEBSITE,
                provider=IRProvider.DEPLOY_PROVIDER_V1,
                resource="site:staging",
                params={},
                idempotency_key="deploy-001",
                step_id="step_0",
            )
        ],
    )

    # DAG has extra node
    dag_nodes = [
        {
            "ir_step_id": "step_0",
            "ir_step_hash": step_hash(ir.steps[0]),
        },
        {
            "ir_step_id": "step_1",  # Extra node not in IR
            "ir_step_hash": "fake_hash",
        },
    ]

    result = gate.audit_ir_dag_mapping(ir, dag_nodes)

    assert result.success is False
    assert len(result.extra_dag_nodes) == 1
    assert "step_1" in result.extra_dag_nodes


# ============================================================================
# Test 9: Diff-Audit Rejects Hash Mismatch
# ============================================================================

def test_diff_audit_rejects_hash_mismatch():
    """Test 9: Diff-audit rejects DAG with mismatched step hashes."""

    gate = DiffAuditGate()

    ir = IR(
        tenant_id="tenant_test",
        steps=[
            IRStep(
                action=IRAction.DEPLOY_WEBSITE,
                provider=IRProvider.DEPLOY_PROVIDER_V1,
                resource="site:staging",
                params={},
                idempotency_key="deploy-001",
                step_id="step_0",
            )
        ],
    )

    # DAG has wrong hash
    dag_nodes = [
        {
            "ir_step_id": "step_0",
            "ir_step_hash": "wrong_hash_not_matching",  # Wrong hash
        },
    ]

    result = gate.audit_ir_dag_mapping(ir, dag_nodes)

    assert result.success is False
    assert len(result.hash_mismatches) == 1


def test_diff_audit_success():
    """Test that diff-audit passes with correct IR ↔ DAG mapping."""

    gate = DiffAuditGate()

    ir = IR(
        tenant_id="tenant_test",
        steps=[
            IRStep(
                action=IRAction.DEPLOY_WEBSITE,
                provider=IRProvider.DEPLOY_PROVIDER_V1,
                resource="site:staging",
                params={},
                idempotency_key="deploy-001",
                step_id="step_0",
            )
        ],
    )

    # DAG matches IR exactly
    dag_nodes = [
        {
            "ir_step_id": "step_0",
            "ir_step_hash": step_hash(ir.steps[0]),
        },
    ]

    result = gate.audit_ir_dag_mapping(ir, dag_nodes)

    assert result.success is True
    assert len(result.missing_ir_steps) == 0
    assert len(result.extra_dag_nodes) == 0
    assert len(result.hash_mismatches) == 0
