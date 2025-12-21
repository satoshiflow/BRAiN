"""
Tests for ARO (Autonomous Repo Operator) Module

Tests cover:
- State machine transitions
- Validators
- Safety checkpoints
- Audit logging
- Service layer
- API endpoints
"""

import sys
import os
import pytest
from pathlib import Path

# Add backend to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from backend.main import app

# Import ARO components
from app.modules.aro.schemas import (
    RepoOperationType,
    OperationState,
    AuthorizationLevel,
    ProposeOperationRequest,
    AuthorizeOperationRequest,
)
from app.modules.aro.state_machine import get_state_machine, StateTransitionError
from app.modules.aro.service import get_aro_service
from app.modules.aro.validators import get_validator_manager
from app.modules.aro.safety import get_safety_manager
from app.modules.aro.audit_logger import get_audit_logger

client = TestClient(app)


# ============================================================================
# State Machine Tests
# ============================================================================


def test_state_machine_valid_transitions():
    """Test that valid state transitions are allowed"""
    state_machine = get_state_machine()

    # PROPOSED → VALIDATING
    assert state_machine.can_transition(
        OperationState.PROPOSED,
        OperationState.VALIDATING
    )

    # VALIDATING → PENDING_AUTH
    assert state_machine.can_transition(
        OperationState.VALIDATING,
        OperationState.PENDING_AUTH
    )

    # PENDING_AUTH → AUTHORIZED
    assert state_machine.can_transition(
        OperationState.PENDING_AUTH,
        OperationState.AUTHORIZED
    )

    # AUTHORIZED → EXECUTING
    assert state_machine.can_transition(
        OperationState.AUTHORIZED,
        OperationState.EXECUTING
    )

    # EXECUTING → COMPLETED
    assert state_machine.can_transition(
        OperationState.EXECUTING,
        OperationState.COMPLETED
    )


def test_state_machine_invalid_transitions():
    """Test that invalid state transitions are rejected"""
    state_machine = get_state_machine()

    # PROPOSED → COMPLETED (not allowed)
    assert not state_machine.can_transition(
        OperationState.PROPOSED,
        OperationState.COMPLETED
    )

    # COMPLETED → anything (terminal state)
    assert not state_machine.can_transition(
        OperationState.COMPLETED,
        OperationState.PROPOSED
    )

    # DENIED → anything (terminal state)
    assert not state_machine.can_transition(
        OperationState.DENIED,
        OperationState.PROPOSED
    )


def test_state_machine_integrity():
    """Test state machine integrity check"""
    state_machine = get_state_machine()
    is_valid, issues = state_machine.validate_state_machine_integrity()

    assert is_valid, f"State machine integrity check failed: {issues}"
    assert len(issues) == 0


# ============================================================================
# Validator Tests
# ============================================================================


@pytest.mark.asyncio
async def test_repository_path_validator_valid():
    """Test repository path validator with valid path"""
    from app.modules.aro.validators import RepositoryPathValidator
    from app.modules.aro.schemas import RepoOperationContext

    validator = RepositoryPathValidator()

    # Use current repository
    context = RepoOperationContext(
        operation_id="test_op",
        operation_type=RepoOperationType.READ_FILE,
        agent_id="test_agent",
        repo_path="/home/user/BRAiN",
        branch="main",
    )

    result = await validator.validate(context)

    assert result.valid, f"Validation failed: {result.issues}"
    assert result.checks_failed == 0


@pytest.mark.asyncio
async def test_repository_path_validator_invalid():
    """Test repository path validator with invalid path"""
    from app.modules.aro.validators import RepositoryPathValidator
    from app.modules.aro.schemas import RepoOperationContext

    validator = RepositoryPathValidator()

    # Use invalid path
    context = RepoOperationContext(
        operation_id="test_op",
        operation_type=RepoOperationType.READ_FILE,
        agent_id="test_agent",
        repo_path="/nonexistent/path",
        branch="main",
    )

    result = await validator.validate(context)

    assert not result.valid
    assert result.checks_failed > 0
    assert len(result.issues) > 0


@pytest.mark.asyncio
async def test_branch_name_validator_valid():
    """Test branch name validator with valid name"""
    from app.modules.aro.validators import BranchNameValidator
    from app.modules.aro.schemas import RepoOperationContext

    validator = BranchNameValidator()

    context = RepoOperationContext(
        operation_id="test_op",
        operation_type=RepoOperationType.COMMIT,
        agent_id="test_agent",
        repo_path="/home/user/BRAiN",
        branch="feature/test-branch",
    )

    result = await validator.validate(context)

    assert result.valid


@pytest.mark.asyncio
async def test_branch_name_validator_invalid():
    """Test branch name validator with invalid characters"""
    from app.modules.aro.validators import BranchNameValidator
    from app.modules.aro.schemas import RepoOperationContext

    validator = BranchNameValidator()

    # Invalid branch name with special characters
    context = RepoOperationContext(
        operation_id="test_op",
        operation_type=RepoOperationType.COMMIT,
        agent_id="test_agent",
        repo_path="/home/user/BRAiN",
        branch="feature@invalid!branch",
    )

    result = await validator.validate(context)

    assert not result.valid


@pytest.mark.asyncio
async def test_operation_type_validator_sufficient_auth():
    """Test operation type validator with sufficient authorization"""
    from app.modules.aro.validators import OperationTypeValidator
    from app.modules.aro.schemas import RepoOperationContext

    validator = OperationTypeValidator()

    # READ operation with READ_ONLY authorization
    context = RepoOperationContext(
        operation_id="test_op",
        operation_type=RepoOperationType.READ_FILE,
        agent_id="test_agent",
        repo_path="/home/user/BRAiN",
        branch="main",
        granted_auth_level=AuthorizationLevel.READ_ONLY,
    )

    result = await validator.validate(context)

    assert result.valid


@pytest.mark.asyncio
async def test_operation_type_validator_insufficient_auth():
    """Test operation type validator with insufficient authorization"""
    from app.modules.aro.validators import OperationTypeValidator
    from app.modules.aro.schemas import RepoOperationContext

    validator = OperationTypeValidator()

    # PUSH operation with READ_ONLY authorization (insufficient)
    context = RepoOperationContext(
        operation_id="test_op",
        operation_type=RepoOperationType.PUSH,
        agent_id="test_agent",
        repo_path="/home/user/BRAiN",
        branch="main",
        granted_auth_level=AuthorizationLevel.READ_ONLY,
    )

    result = await validator.validate(context)

    assert not result.valid
    assert any("Insufficient authorization" in issue for issue in result.issues)


# ============================================================================
# Safety Checkpoint Tests
# ============================================================================


@pytest.mark.asyncio
async def test_branch_protection_checkpoint():
    """Test branch protection checkpoint"""
    from app.modules.aro.safety import BranchProtectionCheckpoint
    from app.modules.aro.schemas import RepoOperationContext

    checkpoint = BranchProtectionCheckpoint()

    # Force push to main (should be blocked)
    context = RepoOperationContext(
        operation_id="test_op",
        operation_type=RepoOperationType.FORCE_PUSH,
        agent_id="test_agent",
        repo_path="/home/user/BRAiN",
        branch="main",
    )

    result = await checkpoint.check(context)

    assert not result.safe
    assert result.risk_score == 1.0
    assert len(result.blocked_reasons) > 0


@pytest.mark.asyncio
async def test_file_system_checkpoint_path_traversal():
    """Test file system checkpoint blocks path traversal"""
    from app.modules.aro.safety import FileSystemCheckpoint
    from app.modules.aro.schemas import RepoOperationContext

    checkpoint = FileSystemCheckpoint()

    # Attempt path traversal
    context = RepoOperationContext(
        operation_id="test_op",
        operation_type=RepoOperationType.READ_FILE,
        agent_id="test_agent",
        repo_path="/home/user/BRAiN",
        branch="main",
        params={"file_path": "../../etc/passwd"},
    )

    result = await checkpoint.check(context)

    assert not result.safe
    assert any("outside repository" in reason for reason in result.blocked_reasons)


# ============================================================================
# Audit Logger Tests
# ============================================================================


@pytest.mark.asyncio
async def test_audit_logger_append_only():
    """Test that audit logger is append-only"""
    audit_logger = get_audit_logger()

    initial_count = audit_logger.entry_count

    # Log an entry
    entry = await audit_logger.log(
        operation_id="test_op",
        operation_type=RepoOperationType.COMMIT,
        agent_id="test_agent",
        event_type="test",
        message="Test audit entry",
    )

    # Verify entry was added
    assert audit_logger.entry_count == initial_count + 1
    assert entry.entry_id in audit_logger.entries

    # Verify entry is immutable (frozen)
    with pytest.raises(Exception):
        entry.message = "Modified"


@pytest.mark.asyncio
async def test_audit_logger_chain_integrity():
    """Test audit log chain integrity"""
    audit_logger = get_audit_logger()

    # Verify chain integrity
    is_valid, issues = audit_logger.verify_chain_integrity()

    assert is_valid, f"Audit log chain integrity check failed: {issues}"


# ============================================================================
# Service Layer Tests
# ============================================================================


@pytest.mark.asyncio
async def test_service_propose_operation():
    """Test proposing an operation"""
    service = get_aro_service()

    request = ProposeOperationRequest(
        operation_type=RepoOperationType.COMMIT,
        agent_id="test_agent",
        repo_path="/home/user/BRAiN",
        branch="claude/aro-phase-1",
        params={"message": "Test commit"},
        requested_auth_level=AuthorizationLevel.COMMIT,
    )

    operation = await service.propose_operation(request)

    assert operation.current_state == OperationState.PROPOSED
    assert operation.operation_id.startswith("op_")
    assert operation.context.operation_type == RepoOperationType.COMMIT


@pytest.mark.asyncio
async def test_service_full_lifecycle():
    """Test full operation lifecycle"""
    service = get_aro_service()

    # Step 1: Propose
    request = ProposeOperationRequest(
        operation_type=RepoOperationType.READ_FILE,
        agent_id="test_agent",
        repo_path="/home/user/BRAiN",
        branch="main",
        params={"file_path": "README.md"},
        requested_auth_level=AuthorizationLevel.READ_ONLY,
    )

    operation = await service.propose_operation(request)
    assert operation.current_state == OperationState.PROPOSED

    # Step 2: Validate
    operation = await service.validate_operation(operation.operation_id)
    assert operation.current_state in [OperationState.PENDING_AUTH, OperationState.DENIED]

    # If validation passed, continue
    if operation.current_state == OperationState.PENDING_AUTH:
        # Step 3: Authorize
        auth_request = AuthorizeOperationRequest(
            operation_id=operation.operation_id,
            authorized_by="admin_agent",
            grant_level=AuthorizationLevel.READ_ONLY,
        )

        operation = await service.authorize_operation(auth_request)
        assert operation.current_state in [OperationState.AUTHORIZED, OperationState.DENIED]

        # If authorized, execute
        if operation.current_state == OperationState.AUTHORIZED:
            # Step 4: Execute
            operation = await service.execute_operation(operation.operation_id)
            assert operation.current_state in [
                OperationState.COMPLETED,
                OperationState.FAILED
            ]


# ============================================================================
# API Endpoint Tests
# ============================================================================


def test_api_info_endpoint():
    """Test ARO info endpoint"""
    response = client.get("/api/aro/info")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "BRAiN Autonomous Repo Operator (ARO)"
    assert data["version"] == "1.0.0"
    assert "features" in data


def test_api_health_endpoint():
    """Test ARO health endpoint"""
    response = client.get("/api/aro/health")

    assert response.status_code == 200
    data = response.json()
    assert data["operational"] is True
    assert "audit_log_integrity" in data


def test_api_stats_endpoint():
    """Test ARO stats endpoint"""
    response = client.get("/api/aro/stats")

    assert response.status_code == 200
    data = response.json()
    assert "total_operations" in data
    assert "operations_by_state" in data
    assert "total_audit_entries" in data


def test_api_propose_operation():
    """Test API endpoint for proposing operation"""
    payload = {
        "operation_type": "read_file",
        "agent_id": "test_agent",
        "repo_path": "/home/user/BRAiN",
        "branch": "main",
        "params": {"file_path": "README.md"},
        "requested_auth_level": "read_only",
    }

    response = client.post("/api/aro/operations", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["current_state"] == "proposed"
    assert "operation_id" in data


def test_api_list_operations():
    """Test API endpoint for listing operations"""
    response = client.get("/api/aro/operations")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_audit_log():
    """Test API endpoint for audit log"""
    response = client.get("/api/aro/audit")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_audit_integrity():
    """Test API endpoint for audit integrity check"""
    response = client.get("/api/aro/audit/integrity")

    assert response.status_code == 200
    data = response.json()
    assert "valid" in data
    assert "total_entries" in data


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_integration_deny_dangerous_operation():
    """Test that dangerous operations are properly denied"""
    service = get_aro_service()

    # Propose force push to main
    request = ProposeOperationRequest(
        operation_type=RepoOperationType.FORCE_PUSH,
        agent_id="test_agent",
        repo_path="/home/user/BRAiN",
        branch="main",
        params={},
        requested_auth_level=AuthorizationLevel.PUSH,  # Not sufficient for force push
    )

    operation = await service.propose_operation(request)

    # Validate
    operation = await service.validate_operation(operation.operation_id)

    # Should be denied due to insufficient authorization
    # (FORCE_PUSH requires ADMIN, not PUSH)
    assert operation.current_state == OperationState.DENIED


@pytest.mark.asyncio
async def test_integration_audit_trail_complete():
    """Test that all operations are logged to audit trail"""
    service = get_aro_service()
    audit_logger = get_audit_logger()

    initial_entry_count = audit_logger.entry_count

    # Propose operation
    request = ProposeOperationRequest(
        operation_type=RepoOperationType.COMMIT,
        agent_id="test_agent",
        repo_path="/home/user/BRAiN",
        branch="test-branch",
        params={"message": "Test"},
        requested_auth_level=AuthorizationLevel.COMMIT,
    )

    operation = await service.propose_operation(request)

    # Verify audit entry was created
    assert audit_logger.entry_count > initial_entry_count

    # Get entries for this operation
    entries = audit_logger.get_entries_for_operation(operation.operation_id)
    assert len(entries) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
