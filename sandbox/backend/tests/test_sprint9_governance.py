"""
Sprint 9 Tests: Governance, Budgets, Run Contracts, Workspace Isolation

Tests for:
- S9-A: Budget Governor (budget exceeded, approval gates, soft degradation)
- S9-B: Deterministic Replay (contract verification, hash matching)
- S9-C: Workspace Isolation (secrets leak test, storage isolation)
- S9-D: Operational Hardening (retry policy, circuit breaker)
"""

import sys
import os
import pytest
import asyncio
from pathlib import Path

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Sprint 9-A: Governor
from app.modules.autonomous_pipeline.governor_schemas import (
    ExecutionBudget,
    ExecutionPolicy,
    BudgetLimitType,
    GovernorDecisionType,
)
from app.modules.autonomous_pipeline.governor import (
    ExecutionGovernor,
    BudgetExceededException,
    ApprovalRequiredException,
)

# Sprint 9-B: Run Contracts
from app.modules.autonomous_pipeline.run_contract import (
    RunContractService,
    RunContract,
)
from app.modules.autonomous_pipeline.schemas import (
    ExecutionGraphSpec,
    ExecutionNodeSpec,
    ExecutionNodeType,
    ExecutionNodeStatus,
)

# Sprint 9-C: Workspace Isolation
from app.modules.autonomous_pipeline.workspace_schemas import (
    Workspace,
    WorkspaceStatus,
    WorkspaceCreateRequest,
    ProjectCreateRequest,
)
from app.modules.autonomous_pipeline.workspace_service import (
    WorkspaceService,
    QuotaExceededError,
)

# Sprint 9-D: Operational Hardening
from app.modules.autonomous_pipeline.operational_hardening import (
    RetryPolicy,
    CircuitBreaker,
    CircuitBreakerOpen,
    ErrorCategory,
    PipelineError,
)


# ============================================================================
# S9-A: Budget Governor Tests
# ============================================================================

class TestBudgetGovernor:
    """Tests for budget enforcement and policy governance."""

    def test_budget_creation(self):
        """Test budget creation with limits."""
        budget = ExecutionBudget(
            max_steps=10,
            max_duration_seconds=60.0,
            max_external_calls=5,
        )

        assert budget.max_steps == 10
        assert budget.max_duration_seconds == 60.0
        assert budget.max_external_calls == 5
        assert budget.step_limit_type == BudgetLimitType.HARD

    def test_policy_creation(self):
        """Test policy creation with budget and approval gates."""
        budget = ExecutionBudget(max_steps=10)
        policy = ExecutionPolicy(
            policy_id="test_policy",
            policy_name="Test Policy",
            budget=budget,
            require_approval_for_types=["dns", "deploy"],
            allow_soft_degradation=True,
        )

        assert policy.policy_id == "test_policy"
        assert policy.budget.max_steps == 10
        assert "dns" in policy.require_approval_for_types
        assert policy.allow_soft_degradation is True

    def test_governor_budget_tracking(self):
        """Test governor tracks budget consumption."""
        budget = ExecutionBudget(max_steps=5, max_duration_seconds=10.0)
        policy = ExecutionPolicy(
            policy_id="test", policy_name="Test", budget=budget
        )
        governor = ExecutionGovernor(policy)

        # Start execution
        governor.start_execution()

        # Record node execution
        governor.record_node_execution("node1", duration_seconds=2.0)
        governor.record_node_execution("node2", duration_seconds=3.0, external_calls=1)

        assert governor.steps_consumed == 2
        assert governor.duration_consumed == 5.0
        assert governor.external_calls_consumed == 1

    def test_governor_budget_exceeded_hard_limit(self):
        """Test governor raises exception when hard budget limit exceeded."""
        budget = ExecutionBudget(
            max_steps=3,
            step_limit_type=BudgetLimitType.HARD,
        )
        policy = ExecutionPolicy(
            policy_id="test", policy_name="Test", budget=budget
        )
        governor = ExecutionGovernor(policy)

        governor.start_execution()

        # Consume budget
        governor.steps_consumed = 3  # At limit

        # Create mock node spec
        node_spec = ExecutionNodeSpec(
            node_id="node4",
            node_type=ExecutionNodeType.WEBGENESIS,
            depends_on=[],
            capabilities=[],
            executor_class="MockExecutor",
            executor_params={},
        )

        # Should raise BudgetExceededException
        with pytest.raises(BudgetExceededException) as exc_info:
            governor.check_node_execution(node_spec, is_dry_run=False)

        assert "Budget exceeded" in str(exc_info.value)
        assert "max_steps" in str(exc_info.value)

    def test_governor_soft_degradation(self):
        """Test governor degrades non-critical nodes when approaching soft limit."""
        budget = ExecutionBudget(
            max_steps=10,
            step_limit_type=BudgetLimitType.SOFT,
        )
        policy = ExecutionPolicy(
            policy_id="test",
            policy_name="Test",
            budget=budget,
            allow_soft_degradation=True,
            skip_on_soft_limit=["webgenesis"],
        )
        governor = ExecutionGovernor(policy)

        governor.start_execution()

        # Consume 85% of budget (triggers soft degradation at 80%)
        governor.steps_consumed = 9  # 90% of 10

        # Create non-critical node
        node_spec = ExecutionNodeSpec(
            node_id="webgen1",
            node_type=ExecutionNodeType.WEBGENESIS,
            depends_on=[],
            capabilities=[],
            executor_class="MockExecutor",
            executor_params={},
            critical=False,
        )

        # Should return DEGRADE decision
        decision = governor.check_node_execution(node_spec, is_dry_run=False)

        assert decision.decision_type == GovernorDecisionType.DEGRADE
        assert decision.degraded is True

    def test_governor_approval_required(self):
        """Test governor blocks nodes requiring approval."""
        budget = ExecutionBudget(max_steps=100)
        policy = ExecutionPolicy(
            policy_id="test",
            policy_name="Test",
            budget=budget,
            require_approval_for_types=["dns"],
        )
        governor = ExecutionGovernor(policy)

        governor.start_execution()

        # Create DNS node (requires approval)
        node_spec = ExecutionNodeSpec(
            node_id="dns1",
            node_type=ExecutionNodeType.DNS,
            depends_on=[],
            capabilities=[],
            executor_class="MockExecutor",
            executor_params={},
        )

        # Should raise ApprovalRequiredException
        with pytest.raises(ApprovalRequiredException) as exc_info:
            governor.check_node_execution(node_spec, is_dry_run=False)

        assert "requires approval" in str(exc_info.value)

    def test_governor_dry_run_respects_limits(self):
        """Test governor enforces limits in dry-run mode if configured."""
        budget = ExecutionBudget(max_steps=3, step_limit_type=BudgetLimitType.HARD)
        policy = ExecutionPolicy(
            policy_id="test",
            policy_name="Test",
            budget=budget,
            dry_run_respects_limits=True,
        )
        governor = ExecutionGovernor(policy)

        governor.start_execution()
        governor.steps_consumed = 3

        node_spec = ExecutionNodeSpec(
            node_id="node4",
            node_type=ExecutionNodeType.WEBGENESIS,
            depends_on=[],
            capabilities=[],
            executor_class="MockExecutor",
            executor_params={},
        )

        # Should raise even in dry-run
        with pytest.raises(BudgetExceededException):
            governor.check_node_execution(node_spec, is_dry_run=True)


# ============================================================================
# S9-B: Run Contract & Deterministic Replay Tests
# ============================================================================

class TestRunContracts:
    """Tests for run contracts and deterministic replay."""

    def test_contract_creation(self):
        """Test run contract creation with hashing."""
        service = RunContractService()

        graph_spec = ExecutionGraphSpec(
            graph_id="test_graph",
            business_intent_id="test_intent",
            nodes=[],
            dry_run=True,
        )

        contract = service.create_contract(
            graph_spec=graph_spec,
            dry_run=True,
        )

        assert contract.contract_id.startswith("contract_")
        assert contract.graph_spec.graph_id == "test_graph"
        assert contract.dry_run is True
        assert len(contract.input_hash) == 64  # SHA256 hex
        assert len(contract.graph_hash) == 64
        assert len(contract.contract_hash) == 64

    def test_contract_deterministic_hashing(self):
        """Test contract hashes are deterministic."""
        service = RunContractService()

        graph_spec = ExecutionGraphSpec(
            graph_id="test_graph",
            business_intent_id="test_intent",
            nodes=[],
            dry_run=True,
        )

        # Create two contracts with same spec
        contract1 = service.create_contract(graph_spec=graph_spec, dry_run=True)
        contract2 = service.create_contract(graph_spec=graph_spec, dry_run=True)

        # Graph hashes should match (deterministic)
        assert contract1.graph_hash == contract2.graph_hash
        assert contract1.policy_hash == contract2.policy_hash

    def test_contract_verification(self):
        """Test contract integrity verification."""
        service = RunContractService()

        graph_spec = ExecutionGraphSpec(
            graph_id="test_graph",
            business_intent_id="test_intent",
            nodes=[],
            dry_run=True,
        )

        contract = service.create_contract(graph_spec=graph_spec, dry_run=True)

        # Verify contract
        is_valid = service.verify_contract(contract)
        assert is_valid is True

    def test_contract_tampering_detection(self):
        """Test contract detects tampering."""
        service = RunContractService()

        graph_spec = ExecutionGraphSpec(
            graph_id="test_graph",
            business_intent_id="test_intent",
            nodes=[],
            dry_run=True,
        )

        contract = service.create_contract(graph_spec=graph_spec, dry_run=True)

        # Tamper with contract
        contract.dry_run = False  # Change field

        # Verification should fail
        is_valid = service.verify_contract(contract)
        assert is_valid is False


# ============================================================================
# S9-C: Workspace Isolation Tests
# ============================================================================

class TestWorkspaceIsolation:
    """Tests for workspace and project isolation."""

    def test_default_workspace_exists(self):
        """Test default workspace is created automatically."""
        service = WorkspaceService()

        default_ws = service.get_workspace("default")

        assert default_ws.workspace_id == "default"
        assert default_ws.name == "Default Workspace"
        assert default_ws.status == WorkspaceStatus.ACTIVE

    def test_workspace_creation(self):
        """Test workspace creation with isolation."""
        service = WorkspaceService()

        request = WorkspaceCreateRequest(
            name="Test Workspace",
            slug="test-workspace",
            description="Test workspace for isolation",
            max_projects=10,
        )

        workspace = service.create_workspace(request)

        assert workspace.name == "Test Workspace"
        assert workspace.slug == "test-workspace"
        assert workspace.max_projects == 10
        assert workspace.storage_path is not None

        # Verify isolated storage path exists
        storage_path = Path(workspace.storage_path)
        assert storage_path.exists()
        assert (storage_path / "secrets").exists()
        assert (storage_path / "evidence").exists()
        assert (storage_path / "contracts").exists()

    def test_workspace_slug_uniqueness(self):
        """Test workspace slug must be unique."""
        service = WorkspaceService()

        request1 = WorkspaceCreateRequest(name="WS 1", slug="unique-slug")
        service.create_workspace(request1)

        request2 = WorkspaceCreateRequest(name="WS 2", slug="unique-slug")

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            service.create_workspace(request2)

        assert "slug already exists" in str(exc_info.value)

    def test_storage_path_isolation(self):
        """Test each workspace gets isolated storage paths."""
        service = WorkspaceService()

        ws1_request = WorkspaceCreateRequest(name="WS1", slug="ws1")
        ws2_request = WorkspaceCreateRequest(name="WS2", slug="ws2")

        ws1 = service.create_workspace(ws1_request)
        ws2 = service.create_workspace(ws2_request)

        # Get isolated storage paths
        ws1_secrets = service.get_isolated_storage_path(ws1.workspace_id, "secrets")
        ws2_secrets = service.get_isolated_storage_path(ws2.workspace_id, "secrets")

        # Paths must be different
        assert ws1_secrets != ws2_secrets
        assert str(ws1.workspace_id) in str(ws1_secrets)
        assert str(ws2.workspace_id) in str(ws2_secrets)

    def test_project_quota_enforcement(self):
        """Test project creation respects workspace quotas."""
        service = WorkspaceService()

        # Create workspace with max_projects=2
        ws_request = WorkspaceCreateRequest(
            name="Limited WS",
            slug="limited-ws",
            max_projects=2,
        )
        workspace = service.create_workspace(ws_request)

        # Create 2 projects (at limit)
        project1_request = ProjectCreateRequest(name="Project 1", slug="proj1")
        project2_request = ProjectCreateRequest(name="Project 2", slug="proj2")

        service.create_project(workspace.workspace_id, project1_request)
        service.create_project(workspace.workspace_id, project2_request)

        # Try to create 3rd project (should fail)
        project3_request = ProjectCreateRequest(name="Project 3", slug="proj3")

        with pytest.raises(QuotaExceededError) as exc_info:
            service.create_project(workspace.workspace_id, project3_request)

        assert "max projects limit" in str(exc_info.value)


# ============================================================================
# S9-D: Operational Hardening Tests
# ============================================================================

class TestRetryPolicy:
    """Tests for retry policy with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Test retry succeeds on transient errors."""
        policy = RetryPolicy(max_retries=3, base_delay=0.1)

        attempt_count = 0

        async def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Transient error")
            return "success"

        result = await policy.execute_with_retry(flaky_function)

        assert result == "success"
        assert attempt_count == 3  # Failed twice, succeeded on 3rd

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry gives up after max retries."""
        policy = RetryPolicy(max_retries=2, base_delay=0.1)

        attempt_count = 0

        async def always_fail():
            nonlocal attempt_count
            attempt_count += 1
            raise ConnectionError("Persistent error")

        with pytest.raises(ConnectionError):
            await policy.execute_with_retry(always_fail)

        assert attempt_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(self):
        """Test retry skips non-retryable errors."""
        policy = RetryPolicy(max_retries=3, base_delay=0.1)

        attempt_count = 0

        async def non_retryable_error():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Invalid input")  # Not retryable

        with pytest.raises(ValueError):
            await policy.execute_with_retry(non_retryable_error)

        assert attempt_count == 1  # No retries


class TestCircuitBreaker:
    """Tests for circuit breaker."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after failure threshold."""
        breaker = CircuitBreaker(
            service_name="test_service",
            failure_threshold=3,
            recovery_timeout=1.0,
        )

        async def failing_function():
            raise Exception("Service error")

        # First 3 failures should go through
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_function)

        # Circuit should now be OPEN
        assert breaker.state.value == "open"

        # Next call should be rejected
        with pytest.raises(CircuitBreakerOpen):
            await breaker.call(failing_function)

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker transitions to half-open and recovers."""
        breaker = CircuitBreaker(
            service_name="test_service",
            failure_threshold=2,
            recovery_timeout=0.2,  # 200ms
        )

        call_count = 0

        async def function_with_recovery():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Failing")
            return "success"

        # Cause 2 failures (opens circuit)
        for i in range(2):
            with pytest.raises(Exception):
                await breaker.call(function_with_recovery)

        assert breaker.state.value == "open"

        # Wait for recovery timeout
        await asyncio.sleep(0.3)

        # Should transition to HALF_OPEN and allow call
        result = await breaker.call(function_with_recovery)
        assert result == "success"


# ============================================================================
# Error Taxonomy Tests
# ============================================================================

class TestErrorTaxonomy:
    """Tests for unified error taxonomy."""

    def test_pipeline_error_categories(self):
        """Test all error categories are defined."""
        categories = [
            ErrorCategory.GOVERNANCE_VIOLATION,
            ErrorCategory.BUDGET_EXCEEDED,
            ErrorCategory.EXTERNAL_DEPENDENCY_FAILED,
            ErrorCategory.NETWORK_TIMEOUT,
            ErrorCategory.INVALID_INPUT,
        ]

        for category in categories:
            assert isinstance(category, ErrorCategory)

    def test_pipeline_error_retryable_flag(self):
        """Test PipelineError carries retryable flag."""
        error = PipelineError(
            message="Test error",
            category=ErrorCategory.NETWORK_TIMEOUT,
            retryable=True,
        )

        assert error.retryable is True
        assert error.category == ErrorCategory.NETWORK_TIMEOUT
