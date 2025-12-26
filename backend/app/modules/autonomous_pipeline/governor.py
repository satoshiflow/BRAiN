"""
Execution Governor (Sprint 9-A)

Controls autonomous pipeline execution through budget enforcement,
approval gates, and policy-based decision making.
"""

from typing import Dict, List, Optional, Any
import time
from datetime import datetime, timedelta
from loguru import logger

from backend.app.modules.autonomous_pipeline.governor_schemas import (
    ExecutionBudget,
    ExecutionPolicy,
    GovernorDecision,
    GovernorDecisionType,
    ApprovalRequest,
    ApprovalStatus,
    BudgetViolation,
    BudgetLimitType,
)
from backend.app.modules.autonomous_pipeline.schemas import ExecutionNodeSpec


class BudgetExceededException(Exception):
    """Raised when budget limit is exceeded (hard limit)."""
    pass


class ApprovalRequiredException(Exception):
    """Raised when node requires approval but has none."""
    pass


class ExecutionGovernor:
    """
    Execution governor for autonomous pipeline.

    Features:
    - Budget tracking (steps, duration, external calls)
    - Approval gates for critical nodes
    - Soft degradation (skip non-critical nodes)
    - Hard limits (fail-closed)
    - Policy-based decision making
    """

    def __init__(self, policy: ExecutionPolicy):
        """
        Initialize governor with execution policy.

        Args:
            policy: Execution policy with budget and rules
        """
        self.policy = policy
        self.budget = policy.budget

        # Budget tracking
        self.steps_consumed = 0
        self.duration_consumed = 0.0
        self.external_calls_consumed = 0
        self.start_time: Optional[float] = None

        # Decisions log
        self.decisions: List[GovernorDecision] = []

        # Violations log
        self.violations: List[BudgetViolation] = []

        # Approval requests
        self.approval_requests: Dict[str, ApprovalRequest] = {}

        logger.info(
            f"[Governor] Initialized with policy '{self.policy.policy_name}' "
            f"(budget: {self.budget.max_steps} steps, "
            f"{self.budget.max_duration_seconds}s, "
            f"{self.budget.max_external_calls} calls)"
        )

    def start_execution(self):
        """Mark execution start (for duration tracking)."""
        self.start_time = time.time()
        logger.info("[Governor] Execution started")

    def check_node_execution(
        self,
        node_spec: ExecutionNodeSpec,
        is_dry_run: bool = False,
    ) -> GovernorDecision:
        """
        Check if node can execute.

        Args:
            node_spec: Node specification
            is_dry_run: Whether this is a dry-run

        Returns:
            GovernorDecision with ALLOW/DENY/REQUIRE_APPROVAL/DEGRADE

        Raises:
            BudgetExceededException: If hard limit exceeded
            ApprovalRequiredException: If approval required but missing
        """
        node_id = node_spec.node_id
        node_type = node_spec.node_type.value if hasattr(node_spec.node_type, 'value') else str(node_spec.node_type)

        logger.info(f"[Governor] Checking node: {node_id} (type={node_type}, dry_run={is_dry_run})")

        # 1. Check if dry-run should respect limits
        if is_dry_run and not self.policy.dry_run_respects_limits:
            decision = GovernorDecision(
                decision_type=GovernorDecisionType.ALLOW,
                node_id=node_id,
                allow_reason="Dry-run mode with limits disabled",
                budget_consumed=self._get_budget_consumed(),
                budget_remaining=self._get_budget_remaining(),
            )
            self.decisions.append(decision)
            return decision

        # 2. Check budget limits
        try:
            self._check_budget_limits(node_id)
        except BudgetExceededException as e:
            # Hard limit exceeded
            decision = GovernorDecision(
                decision_type=GovernorDecisionType.DENY,
                node_id=node_id,
                deny_reason=str(e),
                budget_consumed=self._get_budget_consumed(),
                budget_remaining=self._get_budget_remaining(),
            )
            self.decisions.append(decision)
            raise

        # 3. Check for soft degradation
        if self._should_degrade(node_spec):
            decision = GovernorDecision(
                decision_type=GovernorDecisionType.DEGRADE,
                node_id=node_id,
                deny_reason="Soft degradation: non-critical node skipped to conserve budget",
                budget_consumed=self._get_budget_consumed(),
                budget_remaining=self._get_budget_remaining(),
                degraded=True,
            )
            self.decisions.append(decision)
            logger.warning(f"[Governor] Node {node_id} DEGRADED (soft limit)")
            return decision

        # 4. Check approval gates
        if self._requires_approval(node_spec):
            # Check if approval exists
            approval = self._get_approval(node_id)

            if approval is None:
                # No approval request yet - create one
                approval = self._create_approval_request(node_spec)
                decision = GovernorDecision(
                    decision_type=GovernorDecisionType.REQUIRE_APPROVAL,
                    node_id=node_id,
                    deny_reason=f"Approval required for {node_type}",
                    budget_consumed=self._get_budget_consumed(),
                    budget_remaining=self._get_budget_remaining(),
                    requires_approval=True,
                    approval_request_id=approval.request_id,
                    approval_status=ApprovalStatus.PENDING,
                )
                self.decisions.append(decision)
                raise ApprovalRequiredException(
                    f"Node {node_id} requires approval (request: {approval.request_id})"
                )

            elif approval.status == ApprovalStatus.PENDING:
                # Still waiting for approval
                decision = GovernorDecision(
                    decision_type=GovernorDecisionType.REQUIRE_APPROVAL,
                    node_id=node_id,
                    deny_reason="Approval pending",
                    budget_consumed=self._get_budget_consumed(),
                    budget_remaining=self._get_budget_remaining(),
                    requires_approval=True,
                    approval_request_id=approval.request_id,
                    approval_status=ApprovalStatus.PENDING,
                )
                self.decisions.append(decision)
                raise ApprovalRequiredException(
                    f"Node {node_id} approval still pending (request: {approval.request_id})"
                )

            elif approval.status == ApprovalStatus.REJECTED:
                # Approval rejected
                decision = GovernorDecision(
                    decision_type=GovernorDecisionType.DENY,
                    node_id=node_id,
                    deny_reason=f"Approval rejected: {approval.rejection_reason}",
                    budget_consumed=self._get_budget_consumed(),
                    budget_remaining=self._get_budget_remaining(),
                    requires_approval=True,
                    approval_request_id=approval.request_id,
                    approval_status=ApprovalStatus.REJECTED,
                )
                self.decisions.append(decision)
                raise ApprovalRequiredException(f"Node {node_id} approval rejected")

            # Approval granted - continue

        # 5. ALLOW execution
        decision = GovernorDecision(
            decision_type=GovernorDecisionType.ALLOW,
            node_id=node_id,
            allow_reason="All checks passed",
            budget_consumed=self._get_budget_consumed(),
            budget_remaining=self._get_budget_remaining(),
        )
        self.decisions.append(decision)
        logger.info(f"[Governor] Node {node_id} ALLOWED")
        return decision

    def record_node_execution(
        self,
        node_id: str,
        duration_seconds: float,
        external_calls: int = 0,
    ):
        """
        Record node execution (consume budget).

        Args:
            node_id: Node ID
            duration_seconds: Execution duration
            external_calls: Number of external API calls made
        """
        self.steps_consumed += 1
        self.duration_consumed += duration_seconds
        self.external_calls_consumed += external_calls

        logger.info(
            f"[Governor] Node {node_id} executed: "
            f"+{duration_seconds:.2f}s, +{external_calls} calls "
            f"(total: {self.steps_consumed} steps, "
            f"{self.duration_consumed:.2f}s, "
            f"{self.external_calls_consumed} calls)"
        )

    def _check_budget_limits(self, node_id: str):
        """
        Check if budget limits are exceeded.

        Args:
            node_id: Node being checked

        Raises:
            BudgetExceededException: If hard limit exceeded
        """
        # Check steps
        if self.steps_consumed >= self.budget.max_steps:
            if self.budget.step_limit_type == BudgetLimitType.HARD:
                violation = BudgetViolation(
                    violation_type="max_steps",
                    limit_type=BudgetLimitType.HARD,
                    current_value=float(self.steps_consumed),
                    limit_value=float(self.budget.max_steps),
                    exceeded_by=float(self.steps_consumed - self.budget.max_steps),
                    exceeded_by_percent=float(
                        (self.steps_consumed - self.budget.max_steps) / self.budget.max_steps * 100
                    ),
                    action_taken="failed",
                )
                self.violations.append(violation)
                raise BudgetExceededException(
                    f"Step limit exceeded: {self.steps_consumed}/{self.budget.max_steps}"
                )

        # Check duration
        if self.start_time:
            current_duration = time.time() - self.start_time
            if current_duration >= self.budget.max_duration_seconds:
                if self.budget.duration_limit_type == BudgetLimitType.HARD:
                    violation = BudgetViolation(
                        violation_type="max_duration_seconds",
                        limit_type=BudgetLimitType.HARD,
                        current_value=current_duration,
                        limit_value=self.budget.max_duration_seconds,
                        exceeded_by=current_duration - self.budget.max_duration_seconds,
                        exceeded_by_percent=(
                            (current_duration - self.budget.max_duration_seconds)
                            / self.budget.max_duration_seconds * 100
                        ),
                        action_taken="failed",
                    )
                    self.violations.append(violation)
                    raise BudgetExceededException(
                        f"Duration limit exceeded: {current_duration:.2f}s/{self.budget.max_duration_seconds}s"
                    )

        # Check external calls
        if self.external_calls_consumed >= self.budget.max_external_calls:
            if self.budget.external_call_limit_type == BudgetLimitType.HARD:
                violation = BudgetViolation(
                    violation_type="max_external_calls",
                    limit_type=BudgetLimitType.HARD,
                    current_value=float(self.external_calls_consumed),
                    limit_value=float(self.budget.max_external_calls),
                    exceeded_by=float(
                        self.external_calls_consumed - self.budget.max_external_calls
                    ),
                    exceeded_by_percent=float(
                        (self.external_calls_consumed - self.budget.max_external_calls)
                        / self.budget.max_external_calls * 100
                    ),
                    action_taken="failed",
                )
                self.violations.append(violation)
                raise BudgetExceededException(
                    f"External call limit exceeded: "
                    f"{self.external_calls_consumed}/{self.budget.max_external_calls}"
                )

    def _should_degrade(self, node_spec: ExecutionNodeSpec) -> bool:
        """
        Check if node should be degraded (skipped due to soft limit).

        Args:
            node_spec: Node specification

        Returns:
            True if node should be skipped
        """
        if not self.policy.allow_soft_degradation:
            return False

        # Don't degrade critical nodes
        if node_spec.node_id in self.policy.critical_nodes:
            return False

        if node_spec.critical:
            return False

        # Check if approaching soft limits
        node_type = node_spec.node_type.value if hasattr(node_spec.node_type, 'value') else str(node_spec.node_type)

        # Check if this node type should be skipped on soft limit
        if node_type not in self.policy.skip_on_soft_limit:
            return False

        # Check soft limits (80% threshold)
        steps_usage = self.steps_consumed / self.budget.max_steps
        if steps_usage >= 0.8 and self.budget.step_limit_type == BudgetLimitType.SOFT:
            return True

        if self.start_time:
            duration_usage = (time.time() - self.start_time) / self.budget.max_duration_seconds
            if duration_usage >= 0.8 and self.budget.duration_limit_type == BudgetLimitType.SOFT:
                return True

        calls_usage = self.external_calls_consumed / max(self.budget.max_external_calls, 1)
        if calls_usage >= 0.8 and self.budget.external_call_limit_type == BudgetLimitType.SOFT:
            return True

        return False

    def _requires_approval(self, node_spec: ExecutionNodeSpec) -> bool:
        """
        Check if node requires approval.

        Args:
            node_spec: Node specification

        Returns:
            True if approval required
        """
        # Check by node ID
        if node_spec.node_id in self.policy.require_approval_for_nodes:
            return True

        # Check by node type
        node_type = node_spec.node_type.value if hasattr(node_spec.node_type, 'value') else str(node_spec.node_type)
        if node_type in self.policy.require_approval_for_types:
            return True

        return False

    def _get_approval(self, node_id: str) -> Optional[ApprovalRequest]:
        """Get approval request for node."""
        return self.approval_requests.get(node_id)

    def _create_approval_request(self, node_spec: ExecutionNodeSpec) -> ApprovalRequest:
        """
        Create approval request for node.

        Args:
            node_spec: Node specification

        Returns:
            ApprovalRequest
        """
        request_id = f"approval_{node_spec.node_id}_{int(time.time())}"

        request = ApprovalRequest(
            request_id=request_id,
            graph_id="unknown",  # Will be set by caller
            node_id=node_spec.node_id,
            node_type=node_spec.node_type.value if hasattr(node_spec.node_type, 'value') else str(node_spec.node_type),
            node_params=node_spec.executor_params,
            expires_at=datetime.utcnow() + timedelta(minutes=15),  # 15 minute expiry
        )

        self.approval_requests[node_spec.node_id] = request

        logger.warning(
            f"[Governor] Approval request created: {request_id} for node {node_spec.node_id}"
        )

        return request

    def approve_node(self, node_id: str, approved_by: str):
        """
        Approve node execution.

        Args:
            node_id: Node to approve
            approved_by: Who approved it
        """
        approval = self.approval_requests.get(node_id)
        if not approval:
            raise ValueError(f"No approval request for node: {node_id}")

        approval.status = ApprovalStatus.APPROVED
        approval.approved_by = approved_by
        approval.approved_at = datetime.utcnow()

        logger.info(f"[Governor] Node {node_id} APPROVED by {approved_by}")

    def reject_node(self, node_id: str, rejected_by: str, reason: str):
        """
        Reject node execution.

        Args:
            node_id: Node to reject
            rejected_by: Who rejected it
            reason: Rejection reason
        """
        approval = self.approval_requests.get(node_id)
        if not approval:
            raise ValueError(f"No approval request for node: {node_id}")

        approval.status = ApprovalStatus.REJECTED
        approval.approved_by = rejected_by
        approval.approved_at = datetime.utcnow()
        approval.rejection_reason = reason

        logger.warning(f"[Governor] Node {node_id} REJECTED by {rejected_by}: {reason}")

    def _get_budget_consumed(self) -> Dict[str, Any]:
        """Get consumed budget."""
        return {
            "steps": self.steps_consumed,
            "duration_seconds": self.duration_consumed,
            "external_calls": self.external_calls_consumed,
        }

    def _get_budget_remaining(self) -> Dict[str, Any]:
        """Get remaining budget."""
        duration_remaining = self.budget.max_duration_seconds - self.duration_consumed
        if self.start_time:
            elapsed = time.time() - self.start_time
            duration_remaining = min(duration_remaining, self.budget.max_duration_seconds - elapsed)

        return {
            "steps": self.budget.max_steps - self.steps_consumed,
            "duration_seconds": max(0.0, duration_remaining),
            "external_calls": self.budget.max_external_calls - self.external_calls_consumed,
        }

    def get_summary(self) -> Dict[str, Any]:
        """
        Get governor execution summary.

        Returns:
            Summary dict with decisions, violations, approvals
        """
        return {
            "policy_id": self.policy.policy_id,
            "policy_name": self.policy.policy_name,
            "budget_consumed": self._get_budget_consumed(),
            "budget_remaining": self._get_budget_remaining(),
            "decisions_count": len(self.decisions),
            "decisions": [d.model_dump() for d in self.decisions],
            "violations_count": len(self.violations),
            "violations": [v.model_dump() for v in self.violations],
            "approval_requests_count": len(self.approval_requests),
            "approval_requests": [a.model_dump() for a in self.approval_requests.values()],
        }
