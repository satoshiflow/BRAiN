"""Human Approval Gates - Governance for structural changes.

Implements Myzel-Hybrid-Charta principles:
- Human-in-the-loop for irreversible actions
- Transparent approval process
- Fail-closed (require approval by default)
- Audit trail for all decisions
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass
from uuid import uuid4

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """Approval request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ActionSeverity(str, Enum):
    """Action severity level (determines approval requirements)."""

    LOW = "low"              # Auto-approved after notification
    MEDIUM = "medium"        # Requires single approval
    HIGH = "high"            # Requires approval + justification
    CRITICAL = "critical"    # Requires multiple approvals + review period


@dataclass
class ApprovalRequest:
    """Human approval request."""

    request_id: str
    action_type: str
    action_description: str
    severity: ActionSeverity
    requested_by: str  # System component requesting approval
    context: Dict
    reasoning: str

    # Approval requirements
    required_approvals: int
    approval_timeout_hours: float

    # Status tracking
    status: ApprovalStatus
    created_at: datetime
    expires_at: datetime

    # Approvals received
    approvals: List[Dict]  # [{approver_id, timestamp, justification}]
    rejections: List[Dict]  # [{approver_id, timestamp, reason}]

    # Decision
    final_decision: Optional[str] = None
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None


class HumanApprovalGates:
    """Human approval gates for structural changes.

    Myzel-Hybrid Principles:
    - Human oversight for irreversible actions (EU AI Act Art. 16, DSGVO Art. 22)
    - Transparent decision-making process
    - Fail-closed (deny by default if uncertain)
    - Comprehensive audit trail

    Approval Tiers:
    - LOW: Auto-approved with notification (e.g., credit adjustment < 10%)
    - MEDIUM: Single approval required (e.g., agent skill update)
    - HIGH: Approval + justification (e.g., add/remove agent)
    - CRITICAL: Multiple approvals + review period (e.g., system architecture change)
    """

    # Approval timeouts by severity
    APPROVAL_TIMEOUTS = {
        ActionSeverity.LOW: 1.0,       # 1 hour
        ActionSeverity.MEDIUM: 24.0,   # 24 hours
        ActionSeverity.HIGH: 48.0,     # 48 hours
        ActionSeverity.CRITICAL: 72.0, # 72 hours
    }

    # Required approvals by severity
    REQUIRED_APPROVALS = {
        ActionSeverity.LOW: 0,          # Auto-approved
        ActionSeverity.MEDIUM: 1,       # Single approval
        ActionSeverity.HIGH: 1,         # Single approval (but with justification)
        ActionSeverity.CRITICAL: 2,     # Multiple approvals
    }

    def __init__(self):
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        self.completed_requests: List[ApprovalRequest] = []

        logger.info("[HumanApprovalGates] Initialized")

    def request_approval(
        self,
        action_type: str,
        action_description: str,
        severity: ActionSeverity,
        requested_by: str,
        context: Dict,
        reasoning: str,
    ) -> ApprovalRequest:
        """Request human approval for action.

        Args:
            action_type: Type of action (e.g., "add_agent", "adjust_credits")
            action_description: Human-readable description
            severity: Action severity level
            requested_by: System component requesting approval
            context: Additional context
            reasoning: Reason for action

        Returns:
            ApprovalRequest instance
        """
        request_id = f"APPROVAL_{uuid4().hex[:12]}"
        timeout_hours = self.APPROVAL_TIMEOUTS[severity]
        required_approvals = self.REQUIRED_APPROVALS[severity]

        # Auto-approve LOW severity actions
        if severity == ActionSeverity.LOW:
            status = ApprovalStatus.APPROVED
            final_decision = "Auto-approved (LOW severity)"
            decided_at = datetime.now(timezone.utc)
            decided_by = "system"
        else:
            status = ApprovalStatus.PENDING
            final_decision = None
            decided_at = None
            decided_by = None

        request = ApprovalRequest(
            request_id=request_id,
            action_type=action_type,
            action_description=action_description,
            severity=severity,
            requested_by=requested_by,
            context=context,
            reasoning=reasoning,
            required_approvals=required_approvals,
            approval_timeout_hours=timeout_hours,
            status=status,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=timeout_hours),
            approvals=[],
            rejections=[],
            final_decision=final_decision,
            decided_at=decided_at,
            decided_by=decided_by,
        )

        if status == ApprovalStatus.PENDING:
            self.pending_requests[request_id] = request
            logger.warning(
                f"[HumanApprovalGates] Approval requested: {action_type} "
                f"({severity.value}, ID: {request_id}) - {action_description}"
            )
        else:
            self.completed_requests.append(request)
            logger.info(
                f"[HumanApprovalGates] Auto-approved: {action_type} "
                f"(ID: {request_id}) - {action_description}"
            )

        return request

    def approve(
        self,
        request_id: str,
        approver_id: str,
        justification: Optional[str] = None,
    ) -> Dict:
        """Approve pending request.

        Args:
            request_id: Approval request ID
            approver_id: Approver identifier
            justification: Optional justification (required for HIGH/CRITICAL)

        Returns:
            Approval result

        Raises:
            ValueError: If request not found or already decided
        """
        if request_id not in self.pending_requests:
            raise ValueError(f"Approval request {request_id} not found or already decided")

        request = self.pending_requests[request_id]

        # Check if expired
        if datetime.now(timezone.utc) > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            request.final_decision = "Expired - timeout exceeded"
            request.decided_at = datetime.now(timezone.utc)
            self._complete_request(request_id)
            raise ValueError(f"Approval request {request_id} has expired")

        # Validate justification for HIGH/CRITICAL
        if request.severity in [ActionSeverity.HIGH, ActionSeverity.CRITICAL]:
            if not justification:
                raise ValueError(
                    f"{request.severity.value.upper()} severity action requires justification"
                )

        # Record approval
        approval = {
            "approver_id": approver_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "justification": justification,
        }
        request.approvals.append(approval)

        logger.info(
            f"[HumanApprovalGates] Approval received for {request_id} "
            f"from {approver_id} ({len(request.approvals)}/{request.required_approvals})"
        )

        # Check if all approvals received
        if len(request.approvals) >= request.required_approvals:
            request.status = ApprovalStatus.APPROVED
            request.final_decision = f"Approved by {len(request.approvals)} approver(s)"
            request.decided_at = datetime.now(timezone.utc)
            request.decided_by = approver_id
            self._complete_request(request_id)

            logger.info(
                f"[HumanApprovalGates] Request {request_id} APPROVED - {request.action_type}"
            )

        return {
            "request_id": request_id,
            "status": request.status.value,
            "approvals_received": len(request.approvals),
            "approvals_required": request.required_approvals,
            "is_approved": request.status == ApprovalStatus.APPROVED,
        }

    def reject(
        self,
        request_id: str,
        approver_id: str,
        reason: str,
    ) -> Dict:
        """Reject pending request.

        Args:
            request_id: Approval request ID
            approver_id: Approver identifier
            reason: Rejection reason (required)

        Returns:
            Rejection result

        Raises:
            ValueError: If request not found or already decided
        """
        if request_id not in self.pending_requests:
            raise ValueError(f"Approval request {request_id} not found or already decided")

        request = self.pending_requests[request_id]

        if not reason:
            raise ValueError("Rejection reason is required")

        # Record rejection
        rejection = {
            "approver_id": approver_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        }
        request.rejections.append(rejection)

        # Single rejection is sufficient to deny (fail-closed)
        request.status = ApprovalStatus.REJECTED
        request.final_decision = f"Rejected by {approver_id}: {reason}"
        request.decided_at = datetime.now(timezone.utc)
        request.decided_by = approver_id
        self._complete_request(request_id)

        logger.warning(
            f"[HumanApprovalGates] Request {request_id} REJECTED by {approver_id} - "
            f"{request.action_type} ({reason})"
        )

        return {
            "request_id": request_id,
            "status": request.status.value,
            "rejected_by": approver_id,
            "reason": reason,
        }

    def check_status(self, request_id: str) -> Dict:
        """Check approval request status.

        Args:
            request_id: Approval request ID

        Returns:
            Status information

        Raises:
            ValueError: If request not found
        """
        # Check pending requests
        if request_id in self.pending_requests:
            request = self.pending_requests[request_id]

            # Check if expired
            if datetime.now(timezone.utc) > request.expires_at:
                request.status = ApprovalStatus.EXPIRED
                request.final_decision = "Expired - timeout exceeded"
                request.decided_at = datetime.now(timezone.utc)
                self._complete_request(request_id)

            return self._format_request_status(request)

        # Check completed requests
        for request in self.completed_requests:
            if request.request_id == request_id:
                return self._format_request_status(request)

        raise ValueError(f"Approval request {request_id} not found")

    def get_pending_approvals(
        self,
        severity: Optional[ActionSeverity] = None,
    ) -> List[Dict]:
        """Get pending approval requests.

        Args:
            severity: Optional severity filter

        Returns:
            List of pending requests
        """
        requests = list(self.pending_requests.values())

        if severity:
            requests = [r for r in requests if r.severity == severity]

        return [self._format_request_status(r) for r in requests]

    def _complete_request(self, request_id: str):
        """Move request from pending to completed.

        Args:
            request_id: Approval request ID
        """
        if request_id in self.pending_requests:
            request = self.pending_requests.pop(request_id)
            self.completed_requests.append(request)

    def _format_request_status(self, request: ApprovalRequest) -> Dict:
        """Format request status for API response.

        Args:
            request: ApprovalRequest instance

        Returns:
            Formatted status dictionary
        """
        return {
            "request_id": request.request_id,
            "action_type": request.action_type,
            "action_description": request.action_description,
            "severity": request.severity.value,
            "status": request.status.value,
            "requested_by": request.requested_by,
            "created_at": request.created_at.isoformat(),
            "expires_at": request.expires_at.isoformat(),
            "approvals_received": len(request.approvals),
            "approvals_required": request.required_approvals,
            "rejections_received": len(request.rejections),
            "final_decision": request.final_decision,
            "decided_at": request.decided_at.isoformat() if request.decided_at else None,
            "decided_by": request.decided_by,
            "is_approved": request.status == ApprovalStatus.APPROVED,
            "is_rejected": request.status == ApprovalStatus.REJECTED,
            "is_expired": request.status == ApprovalStatus.EXPIRED,
            "is_pending": request.status == ApprovalStatus.PENDING,
        }

    def get_audit_trail(self, limit: int = 50) -> List[Dict]:
        """Get approval audit trail.

        Args:
            limit: Maximum number of entries

        Returns:
            List of completed requests (newest first)
        """
        return [
            self._format_request_status(r)
            for r in reversed(self.completed_requests[-limit:])
        ]


# Global approval gates instance
_approval_gates: Optional[HumanApprovalGates] = None


def get_approval_gates() -> HumanApprovalGates:
    """Get global human approval gates instance.

    Returns:
        HumanApprovalGates instance
    """
    global _approval_gates
    if _approval_gates is None:
        _approval_gates = HumanApprovalGates()
    return _approval_gates
