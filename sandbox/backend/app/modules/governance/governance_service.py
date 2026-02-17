"""
Governance Service

Sprint 16: HITL Approvals UI & Governance Cockpit
Business logic for approval workflows and audit trail.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from .governance_models import (
    Approval,
    ApprovalAction,
    ApprovalContext,
    ApprovalDetail,
    ApprovalStatus,
    ApprovalSummary,
    ApprovalType,
    AuditEntry,
    AuditExport,
    GovernanceStats,
    RiskTier,
)
from .governance_storage import GovernanceStorage


class GovernanceService:
    """
    Service layer for governance approvals.

    Responsibilities:
    - Create and manage approval requests
    - Approve/reject workflows
    - Audit trail management
    - Statistics and reporting
    """

    def __init__(self, storage: Optional[GovernanceStorage] = None):
        self.storage = storage or GovernanceStorage()

    # =========================================================================
    # Approval Lifecycle
    # =========================================================================

    async def request_approval(
        self,
        approval_type: ApprovalType,
        context: ApprovalContext,
        expires_in_hours: int = 24,
        require_token: bool = False,
    ) -> tuple[Approval, Optional[str]]:
        """
        Create new approval request.

        Args:
            approval_type: Type of approval
            context: Approval context
            expires_in_hours: Hours until expiry (1-168)
            require_token: Whether to require single-use token

        Returns:
            Tuple of (Approval, token)
            - token is only returned if require_token=True
        """
        # Calculate expiry
        expires_at = (datetime.utcnow() + timedelta(hours=expires_in_hours)).timestamp()

        # Generate token if required
        token = None
        token_hash = None
        if require_token:
            token, token_hash = self.storage.generate_token()

        # Create approval
        approval = Approval(
            approval_type=approval_type,
            context=context,
            expires_at=expires_at,
            token_hash=token_hash,
        )

        # Save
        self.storage.save_approval(approval)

        # Audit
        self.storage._log_audit(
            approval_id=approval.approval_id,
            action=ApprovalAction.VIEW,  # Initial creation
            action_description=f"Approval requested: {context.action_description}",
            actor_id=context.requested_by,
            metadata={
                "approval_type": approval_type.value,
                "risk_tier": context.risk_tier.value,
            }
        )

        logger.info(
            f"Approval requested: {approval.approval_id} "
            f"(type: {approval_type.value}, risk: {context.risk_tier.value})"
        )

        return approval, token

    async def approve_approval(
        self,
        approval_id: str,
        actor_id: str,
        token: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Approval:
        """
        Approve an approval request.

        Args:
            approval_id: Approval ID
            actor_id: Actor performing approval
            token: Single-use token (if required)
            notes: Optional approval notes

        Returns:
            Updated Approval

        Raises:
            ValueError: If approval fails validation
        """
        success = self.storage.approve_approval(approval_id, actor_id, token)

        if success:
            approval = self.storage.get_approval(approval_id)
            logger.info(f"Approval {approval_id} approved by {actor_id}")
            return approval

        raise ValueError("Approval failed")

    async def reject_approval(
        self,
        approval_id: str,
        actor_id: str,
        reason: str,
        notes: Optional[str] = None,
    ) -> Approval:
        """
        Reject an approval request.

        Args:
            approval_id: Approval ID
            actor_id: Actor performing rejection
            reason: Rejection reason (required, min 10 chars)
            notes: Optional additional notes

        Returns:
            Updated Approval

        Raises:
            ValueError: If rejection fails validation
        """
        if len(reason) < 10:
            raise ValueError("Rejection reason must be at least 10 characters")

        success = self.storage.reject_approval(approval_id, actor_id, reason)

        if success:
            approval = self.storage.get_approval(approval_id)
            logger.info(f"Approval {approval_id} rejected by {actor_id}: {reason}")
            return approval

        raise ValueError("Rejection failed")

    # =========================================================================
    # Queries
    # =========================================================================

    async def get_approval_detail(self, approval_id: str) -> Optional[ApprovalDetail]:
        """
        Get detailed approval information.

        Args:
            approval_id: Approval ID

        Returns:
            ApprovalDetail or None
        """
        approval = self.storage.get_approval(approval_id)
        if not approval:
            return None

        # Audit view
        self.storage._log_audit(
            approval_id=approval_id,
            action=ApprovalAction.VIEW,
            action_description="Approval viewed",
            actor_id="system",  # Could be parameterized
        )

        return ApprovalDetail(
            approval_id=approval.approval_id,
            approval_type=approval.approval_type,
            status=approval.status,
            context=approval.context,
            approved_by=approval.approved_by,
            approved_at=approval.approved_at,
            rejection_reason=approval.rejection_reason,
            expires_at=approval.expires_at,
            time_until_expiry=approval.time_until_expiry(),
            token_used=approval.token_used,
            created_at=approval.created_at,
            updated_at=approval.updated_at,
        )

    async def list_approvals(
        self,
        status: Optional[ApprovalStatus] = None,
        approval_type: Optional[ApprovalType] = None,
        requested_by: Optional[str] = None,
        risk_tier: Optional[RiskTier] = None,
        include_expired: bool = False,
        limit: int = 100,
    ) -> List[ApprovalSummary]:
        """
        List approvals with filters.

        Args:
            status: Filter by status
            approval_type: Filter by type
            requested_by: Filter by requester
            risk_tier: Filter by risk tier
            include_expired: Include expired approvals
            limit: Maximum results

        Returns:
            List of ApprovalSummary
        """
        approvals = self.storage.list_approvals(
            status=status,
            approval_type=approval_type,
            requested_by=requested_by,
            risk_tier=risk_tier,
            include_expired=include_expired,
        )

        # Convert to summaries
        summaries = []
        for approval in approvals[:limit]:
            summary = ApprovalSummary(
                approval_id=approval.approval_id,
                approval_type=approval.approval_type,
                status=approval.status,
                risk_tier=approval.context.risk_tier,
                requested_by=approval.context.requested_by,
                requested_at=approval.context.requested_at,
                expires_at=approval.expires_at,
                time_until_expiry=approval.time_until_expiry(),
                action_description=approval.context.action_description,
            )
            summaries.append(summary)

        return summaries

    async def get_pending_approvals(self) -> List[ApprovalSummary]:
        """Get all pending approvals."""
        return await self.list_approvals(status=ApprovalStatus.PENDING)

    async def get_approved_approvals(self) -> List[ApprovalSummary]:
        """Get all approved approvals."""
        return await self.list_approvals(status=ApprovalStatus.APPROVED)

    async def get_rejected_approvals(self) -> List[ApprovalSummary]:
        """Get all rejected approvals."""
        return await self.list_approvals(status=ApprovalStatus.REJECTED)

    async def get_expired_approvals(self) -> List[ApprovalSummary]:
        """Get all expired approvals."""
        return await self.list_approvals(
            status=ApprovalStatus.EXPIRED,
            include_expired=True
        )

    # =========================================================================
    # Audit Trail
    # =========================================================================

    async def get_audit_trail(self, approval_id: str) -> List[AuditEntry]:
        """
        Get audit trail for specific approval.

        Args:
            approval_id: Approval ID

        Returns:
            List of AuditEntry (chronological order)
        """
        return self.storage.get_audit_trail(approval_id)

    async def export_audit(
        self,
        actor_id: str,
        approval_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> AuditExport:
        """
        Export audit trail (for auditors).

        Args:
            actor_id: Actor performing export
            approval_id: Filter by approval ID (optional)
            limit: Maximum entries

        Returns:
            AuditExport with entries
        """
        entries = self.storage.export_audit_trail(approval_id, limit)

        # Log export action
        if approval_id:
            self.storage._log_audit(
                approval_id=approval_id,
                action=ApprovalAction.EXPORT,
                action_description=f"Audit trail exported by {actor_id}",
                actor_id=actor_id,
                actor_role="auditor",
            )

        export = AuditExport(
            approval_id=approval_id or "all",
            entries=entries,
            exported_by=actor_id,
        )

        logger.info(f"Audit trail exported by {actor_id} ({len(entries)} entries)")
        return export

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> GovernanceStats:
        """
        Get governance system statistics.

        Returns:
            GovernanceStats
        """
        stats_data = self.storage.get_stats()

        # Calculate average approval time
        average_time = await self._calculate_average_approval_time()

        stats = GovernanceStats(
            total_approvals=stats_data.get("total", 0),
            pending_approvals=stats_data.get("pending", 0),
            approved_count=stats_data.get("approved", 0),
            rejected_count=stats_data.get("rejected", 0),
            expired_count=stats_data.get("expired", 0),
            by_type=stats_data.get("by_type", {}),
            by_risk_tier=stats_data.get("by_risk_tier", {}),
            average_approval_time=average_time,
        )

        return stats

    async def _calculate_average_approval_time(self) -> float:
        """Calculate average time from request to approval/rejection."""
        approvals = self.storage.list_approvals()
        times = []

        for approval in approvals:
            if approval.approved_at:
                time_to_decision = approval.approved_at - approval.context.requested_at
                times.append(time_to_decision)

        if not times:
            return 0.0

        return sum(times) / len(times)

    # =========================================================================
    # Maintenance
    # =========================================================================

    async def expire_old_approvals(self) -> int:
        """
        Expire all pending approvals past their expiry time.

        Returns:
            Number of approvals expired
        """
        expired_count = self.storage.expire_old_approvals()

        if expired_count > 0:
            logger.info(f"Expired {expired_count} old approvals")

        return expired_count

    # =========================================================================
    # Specialized Approval Types
    # =========================================================================

    async def request_ir_escalation_approval(
        self,
        requested_by: str,
        ir_action: str,
        risk_tier: RiskTier,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        reason: Optional[str] = None,
    ) -> tuple[Approval, Optional[str]]:
        """Request approval for IR escalation."""
        context = ApprovalContext(
            action_type=ApprovalType.IR_ESCALATION,
            action_description=f"IR Escalation: {ir_action}",
            risk_tier=risk_tier,
            requested_by=requested_by,
            before=before_state,
            after=after_state,
            reason=reason,
        )

        # High/Critical risk requires token
        require_token = risk_tier in [RiskTier.HIGH, RiskTier.CRITICAL]

        return await self.request_approval(
            ApprovalType.IR_ESCALATION,
            context,
            expires_in_hours=24,
            require_token=require_token,
        )

    async def request_course_publish_approval(
        self,
        requested_by: str,
        course_id: str,
        course_title: str,
        risk_tier: RiskTier = RiskTier.MEDIUM,
        reason: Optional[str] = None,
    ) -> tuple[Approval, Optional[str]]:
        """Request approval for course publishing."""
        context = ApprovalContext(
            action_type=ApprovalType.COURSE_PUBLISH,
            action_description=f"Publish Course: {course_title}",
            risk_tier=risk_tier,
            requested_by=requested_by,
            reason=reason,
            metadata={"course_id": course_id},
        )

        return await self.request_approval(
            ApprovalType.COURSE_PUBLISH,
            context,
            expires_in_hours=72,  # Longer for course review
            require_token=False,
        )

    async def request_certificate_issuance_approval(
        self,
        requested_by: str,
        certificate_id: str,
        recipient: str,
        course_title: str,
        risk_tier: RiskTier = RiskTier.LOW,
    ) -> tuple[Approval, Optional[str]]:
        """Request approval for certificate issuance."""
        context = ApprovalContext(
            action_type=ApprovalType.CERTIFICATE_ISSUANCE,
            action_description=f"Issue Certificate: {course_title} to {recipient}",
            risk_tier=risk_tier,
            requested_by=requested_by,
            metadata={
                "certificate_id": certificate_id,
                "recipient": recipient,
            },
        )

        return await self.request_approval(
            ApprovalType.CERTIFICATE_ISSUANCE,
            context,
            expires_in_hours=48,
            require_token=False,
        )

    async def request_policy_override_approval(
        self,
        requested_by: str,
        policy_id: str,
        override_reason: str,
        risk_tier: RiskTier = RiskTier.HIGH,
    ) -> tuple[Approval, Optional[str]]:
        """Request approval for policy override."""
        context = ApprovalContext(
            action_type=ApprovalType.POLICY_OVERRIDE,
            action_description=f"Override Policy: {policy_id}",
            risk_tier=risk_tier,
            requested_by=requested_by,
            reason=override_reason,
            metadata={"policy_id": policy_id},
        )

        return await self.request_approval(
            ApprovalType.POLICY_OVERRIDE,
            context,
            expires_in_hours=12,  # Short expiry for overrides
            require_token=True,  # Always require token
        )
