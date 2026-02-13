"""
Governance Storage Adapter

Sprint 16: HITL Approvals UI & Governance Cockpit
File-based atomic storage for approvals and audit trail.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import secrets
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .governance_models import (
    Approval,
    ApprovalAction,
    ApprovalStatus,
    ApprovalType,
    AuditEntry,
    RiskTier,
)


# Storage paths
STORAGE_BASE = Path("storage/governance")
APPROVALS_FILE = STORAGE_BASE / "approvals.json"
AUDIT_LOG_FILE = STORAGE_BASE / "audit.jsonl"
STATS_FILE = STORAGE_BASE / "stats.json"


@contextmanager
def file_lock(file_path: Path, mode: str = 'r'):
    """
    Atomic file operations with exclusive locking.

    Args:
        file_path: Path to file
        mode: File open mode ('r', 'a', 'w')

    Yields:
        File handle with exclusive lock
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure file exists for read mode
    if mode == 'r' and not file_path.exists():
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({} if file_path.suffix == '.json' else [], f)

    with open(file_path, mode, encoding='utf-8') as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class GovernanceStorage:
    """
    Storage adapter for governance approvals and audit trail.

    Features:
    - Atomic file operations
    - Token generation and validation
    - Audit trail (append-only)
    - Auto-expiry handling
    """

    def __init__(self, storage_path: Path = STORAGE_BASE):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialize storage files if they don't exist."""
        files = [
            (APPROVALS_FILE, {}),
            (STATS_FILE, {
                "total": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "expired": 0,
            }),
        ]
        for file_path, default_content in files:
            if not file_path.exists():
                with file_lock(file_path, 'w') as f:
                    json.dump(default_content, f, indent=2)

        if not AUDIT_LOG_FILE.exists():
            AUDIT_LOG_FILE.touch()

    # =========================================================================
    # Token Management
    # =========================================================================

    def generate_token(self) -> tuple[str, str]:
        """
        Generate single-use token.

        Returns:
            Tuple of (token, token_hash)
            - token: The actual token to return to user (ONLY ONCE)
            - token_hash: SHA-256 hash to store in database
        """
        token = secrets.token_urlsafe(32)  # 256-bit entropy
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return token, token_hash

    def verify_token(self, token: str, stored_hash: str) -> bool:
        """
        Verify token against stored hash.

        Args:
            token: Token provided by user
            stored_hash: SHA-256 hash stored in approval

        Returns:
            True if token is valid
        """
        computed_hash = hashlib.sha256(token.encode()).hexdigest()
        return computed_hash == stored_hash

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def save_approval(self, approval: Approval) -> bool:
        """
        Save or update approval.

        Args:
            approval: Approval instance

        Returns:
            True if successful
        """
        approval.updated_at = datetime.utcnow().timestamp()

        with file_lock(APPROVALS_FILE, 'r') as f:
            approvals = json.load(f)

        approvals[approval.approval_id] = approval.model_dump()

        with file_lock(APPROVALS_FILE, 'w') as f:
            json.dump(approvals, f, indent=2)

        # Update stats
        self._update_stats()

        return True

    def get_approval(self, approval_id: str) -> Optional[Approval]:
        """Get approval by ID."""
        with file_lock(APPROVALS_FILE, 'r') as f:
            approvals = json.load(f)

        data = approvals.get(approval_id)
        if not data:
            return None

        approval = Approval(**data)

        # Auto-expire if needed
        if approval.is_expired() and approval.status == ApprovalStatus.PENDING:
            approval.status = ApprovalStatus.EXPIRED
            self.save_approval(approval)
            self._log_audit(
                approval_id=approval_id,
                action=ApprovalAction.EXPIRE,
                action_description="Approval auto-expired",
                actor_id="system"
            )

        return approval

    def list_approvals(
        self,
        status: Optional[ApprovalStatus] = None,
        approval_type: Optional[ApprovalType] = None,
        requested_by: Optional[str] = None,
        risk_tier: Optional[RiskTier] = None,
        include_expired: bool = False,
    ) -> List[Approval]:
        """
        List approvals with optional filters.

        Args:
            status: Filter by status
            approval_type: Filter by type
            requested_by: Filter by requester
            risk_tier: Filter by risk tier
            include_expired: Include expired approvals

        Returns:
            List of Approval instances
        """
        with file_lock(APPROVALS_FILE, 'r') as f:
            approvals = json.load(f)

        results = []
        for data in approvals.values():
            approval = Approval(**data)

            # Auto-expire check
            if approval.is_expired() and approval.status == ApprovalStatus.PENDING:
                approval.status = ApprovalStatus.EXPIRED
                self.save_approval(approval)

            # Apply filters
            if status and approval.status != status:
                continue

            if not include_expired and approval.status == ApprovalStatus.EXPIRED:
                continue

            if approval_type and approval.approval_type != approval_type:
                continue

            if requested_by and approval.context.requested_by != requested_by:
                continue

            if risk_tier and approval.context.risk_tier != risk_tier:
                continue

            results.append(approval)

        # Sort by requested_at (newest first)
        results.sort(key=lambda x: x.context.requested_at, reverse=True)
        return results

    def delete_approval(self, approval_id: str) -> bool:
        """
        Delete approval (admin only, use with caution).

        Args:
            approval_id: Approval ID

        Returns:
            True if deleted
        """
        with file_lock(APPROVALS_FILE, 'r') as f:
            approvals = json.load(f)

        if approval_id not in approvals:
            return False

        del approvals[approval_id]

        with file_lock(APPROVALS_FILE, 'w') as f:
            json.dump(approvals, f, indent=2)

        self._update_stats()
        return True

    # =========================================================================
    # Approval Actions
    # =========================================================================

    def approve_approval(
        self,
        approval_id: str,
        actor_id: str,
        token: Optional[str] = None,
    ) -> bool:
        """
        Approve an approval request.

        Args:
            approval_id: Approval ID
            actor_id: Actor performing approval
            token: Single-use token (if required)

        Returns:
            True if approved

        Raises:
            ValueError: If approval not found, already processed, expired, or token invalid
        """
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        if not approval.is_pending():
            raise ValueError(f"Approval {approval_id} is not pending (status: {approval.status})")

        if approval.is_expired():
            raise ValueError(f"Approval {approval_id} has expired")

        # Verify token if provided and required
        if approval.token_hash:
            if not token:
                raise ValueError("Token required for this approval")
            if not self.verify_token(token, approval.token_hash):
                raise ValueError("Invalid token")
            if approval.token_used:
                raise ValueError("Token already used")

            approval.token_used = True

        # Approve
        approval.status = ApprovalStatus.APPROVED
        approval.approved_by = actor_id
        approval.approved_at = datetime.utcnow().timestamp()

        self.save_approval(approval)

        # Audit
        self._log_audit(
            approval_id=approval_id,
            action=ApprovalAction.APPROVE,
            action_description=f"Approved by {actor_id}",
            actor_id=actor_id
        )

        return True

    def reject_approval(
        self,
        approval_id: str,
        actor_id: str,
        reason: str,
    ) -> bool:
        """
        Reject an approval request.

        Args:
            approval_id: Approval ID
            actor_id: Actor performing rejection
            reason: Rejection reason (required)

        Returns:
            True if rejected

        Raises:
            ValueError: If approval not found, already processed, or expired
        """
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        if not approval.is_pending():
            raise ValueError(f"Approval {approval_id} is not pending (status: {approval.status})")

        if approval.is_expired():
            raise ValueError(f"Approval {approval_id} has expired")

        # Reject
        approval.status = ApprovalStatus.REJECTED
        approval.approved_by = actor_id
        approval.approved_at = datetime.utcnow().timestamp()
        approval.rejection_reason = reason

        self.save_approval(approval)

        # Audit
        self._log_audit(
            approval_id=approval_id,
            action=ApprovalAction.REJECT,
            action_description=f"Rejected by {actor_id}: {reason}",
            actor_id=actor_id,
            metadata={"reason": reason}
        )

        return True

    # =========================================================================
    # Audit Trail
    # =========================================================================

    def _log_audit(
        self,
        approval_id: str,
        action: ApprovalAction,
        action_description: str,
        actor_id: str,
        actor_role: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log audit entry.

        Args:
            approval_id: Approval ID
            action: Action taken
            action_description: Description of action
            actor_id: Actor ID
            actor_role: Actor role (optional)
            metadata: Additional metadata

        Returns:
            True if logged
        """
        entry = AuditEntry(
            approval_id=approval_id,
            action=action,
            action_description=action_description,
            actor_id=actor_id,
            actor_role=actor_role,
            metadata=metadata or {},
        )

        with file_lock(AUDIT_LOG_FILE, 'a') as f:
            f.write(entry.model_dump_json() + '\n')

        return True

    def get_audit_trail(self, approval_id: str) -> List[AuditEntry]:
        """
        Get audit trail for approval.

        Args:
            approval_id: Approval ID

        Returns:
            List of audit entries (chronological order)
        """
        entries = []

        with file_lock(AUDIT_LOG_FILE, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                entry = AuditEntry(**json.loads(line))
                if entry.approval_id == approval_id:
                    entries.append(entry)

        # Sort by timestamp
        entries.sort(key=lambda x: x.timestamp)
        return entries

    def export_audit_trail(
        self,
        approval_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[AuditEntry]:
        """
        Export audit trail (all or filtered).

        Args:
            approval_id: Filter by approval ID (optional)
            limit: Maximum entries to return

        Returns:
            List of audit entries
        """
        entries = []

        with file_lock(AUDIT_LOG_FILE, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                entry = AuditEntry(**json.loads(line))

                if approval_id and entry.approval_id != approval_id:
                    continue

                entries.append(entry)

        # Sort by timestamp (newest first)
        entries.sort(key=lambda x: x.timestamp, reverse=True)

        if limit:
            entries = entries[:limit]

        return entries

    # =========================================================================
    # Statistics
    # =========================================================================

    def _update_stats(self):
        """Update statistics file."""
        with file_lock(APPROVALS_FILE, 'r') as f:
            approvals = json.load(f)

        stats = {
            "total": len(approvals),
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "expired": 0,
            "by_type": {},
            "by_risk_tier": {},
        }

        for data in approvals.values():
            approval = Approval(**data)

            # Auto-expire check
            if approval.is_expired() and approval.status == ApprovalStatus.PENDING:
                approval.status = ApprovalStatus.EXPIRED

            # Count by status
            if approval.status == ApprovalStatus.PENDING:
                stats["pending"] += 1
            elif approval.status == ApprovalStatus.APPROVED:
                stats["approved"] += 1
            elif approval.status == ApprovalStatus.REJECTED:
                stats["rejected"] += 1
            elif approval.status == ApprovalStatus.EXPIRED:
                stats["expired"] += 1

            # Count by type
            type_key = approval.approval_type.value
            stats["by_type"][type_key] = stats["by_type"].get(type_key, 0) + 1

            # Count by risk tier
            tier_key = approval.context.risk_tier.value
            stats["by_risk_tier"][tier_key] = stats["by_risk_tier"].get(tier_key, 0) + 1

        with file_lock(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        with file_lock(STATS_FILE, 'r') as f:
            stats = json.load(f)

        return stats

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def expire_old_approvals(self) -> int:
        """
        Expire all pending approvals past their expiry time.

        Returns:
            Number of approvals expired
        """
        approvals = self.list_approvals(status=ApprovalStatus.PENDING)
        expired_count = 0

        for approval in approvals:
            if approval.is_expired():
                approval.status = ApprovalStatus.EXPIRED
                self.save_approval(approval)
                self._log_audit(
                    approval_id=approval.approval_id,
                    action=ApprovalAction.EXPIRE,
                    action_description="Approval auto-expired",
                    actor_id="system"
                )
                expired_count += 1

        return expired_count
