"""
HITL Approvals Service - Sprint 9 (P0) + Sprint 11

Human-in-the-Loop approval workflow for high-risk IR execution.

Security Requirements:
- Single-use tokens (cannot replay)
- TTL (time-to-live) enforcement
- Token hash stored (never raw token in storage/logs)
- Tenant-bound approval validation
- IR hash matching

Stores:
- In-memory (default, no external dependencies)
- Redis (Sprint 11, feature-flagged via APPROVAL_STORE env var)

Sprint 11 Enhancements:
- Redis backend for restart-safe approval storage
- Automatic TTL cleanup via Redis expiration
- Horizontal scaling support
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import hashlib
import secrets
import time
import os
from loguru import logger

from backend.app.modules.ir_governance.schemas import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalConsumeRequest,
    ApprovalConsumeResult,
)


class ApprovalStore:
    """
    Abstract approval storage.

    Implementations:
    - InMemoryApprovalStore (default)
    - RedisApprovalStore (optional)
    """

    def create(self, approval: ApprovalRequest) -> bool:
        """Create approval request."""
        raise NotImplementedError

    def get(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID."""
        raise NotImplementedError

    def update(self, approval: ApprovalRequest) -> bool:
        """Update approval request."""
        raise NotImplementedError

    def delete(self, approval_id: str) -> bool:
        """Delete approval request."""
        raise NotImplementedError

    def find_by_token_hash(self, token_hash: str) -> Optional[ApprovalRequest]:
        """Find approval by token hash."""
        raise NotImplementedError


class InMemoryApprovalStore(ApprovalStore):
    """
    In-memory approval storage.

    Suitable for single-instance deployments.
    No external dependencies.
    """

    def __init__(self):
        """Initialize in-memory store."""
        self._approvals: Dict[str, ApprovalRequest] = {}
        self._token_hash_index: Dict[str, str] = {}  # token_hash -> approval_id

    def create(self, approval: ApprovalRequest) -> bool:
        """Create approval request."""
        self._approvals[approval.approval_id] = approval
        self._token_hash_index[approval.token_hash] = approval.approval_id
        return True

    def get(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID."""
        return self._approvals.get(approval_id)

    def update(self, approval: ApprovalRequest) -> bool:
        """Update approval request."""
        if approval.approval_id not in self._approvals:
            return False
        self._approvals[approval.approval_id] = approval
        return True

    def delete(self, approval_id: str) -> bool:
        """Delete approval request."""
        approval = self._approvals.pop(approval_id, None)
        if approval:
            self._token_hash_index.pop(approval.token_hash, None)
            return True
        return False

    def find_by_token_hash(self, token_hash: str) -> Optional[ApprovalRequest]:
        """Find approval by token hash."""
        approval_id = self._token_hash_index.get(token_hash)
        if approval_id:
            return self._approvals.get(approval_id)
        return None


class ApprovalsService:
    """
    HITL approvals service.

    Lifecycle:
    1. Create approval request (returns token)
    2. User approves (external flow)
    3. Consume approval (validates token, marks consumed)

    Security:
    - Token is single-use
    - Token has TTL
    - Token hash stored (not raw token)
    - Tenant-bound validation
    - IR hash matching
    """

    # Default TTL: 1 hour
    DEFAULT_TTL_SECONDS = 3600

    def __init__(self, store: Optional[ApprovalStore] = None):
        """
        Initialize approvals service.

        Args:
            store: Approval storage (default: InMemoryApprovalStore)
        """
        self.store = store or InMemoryApprovalStore()

    def create_approval(
        self,
        tenant_id: str,
        ir_hash: str,
        ttl_seconds: Optional[int] = None,
        created_by: Optional[str] = None,
    ) -> tuple[ApprovalRequest, str]:
        """
        Create approval request.

        Args:
            tenant_id: Tenant ID
            ir_hash: IR hash to approve
            ttl_seconds: Time-to-live in seconds (default: 1 hour)
            created_by: User/role creating approval

        Returns:
            (ApprovalRequest, raw_token) - token is returned ONCE, never stored raw

        Audit events:
        - ir.approval_created
        """
        # Generate secure random token
        raw_token = secrets.token_urlsafe(32)  # 256 bits
        token_hash = self._hash_token(raw_token)

        # Calculate expiration
        ttl = ttl_seconds or self.DEFAULT_TTL_SECONDS
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)

        # Create approval request
        approval = ApprovalRequest(
            tenant_id=tenant_id,
            ir_hash=ir_hash,
            token_hash=token_hash,
            expires_at=expires_at,
            created_by=created_by,
        )

        # Store approval
        self.store.create(approval)

        # Emit audit event (NO RAW TOKEN in logs)
        logger.info(
            f"[Approvals] ir.approval_created: "
            f"approval_id={approval.approval_id}, "
            f"tenant_id={tenant_id}, "
            f"ir_hash={ir_hash[:16]}..., "
            f"expires_in={ttl}s, "
            f"created_by={created_by or 'system'}"
        )

        # Return approval and raw token (ONLY TIME raw token is exposed)
        return approval, raw_token

    def consume_approval(
        self,
        request: ApprovalConsumeRequest,
        consumed_by: Optional[str] = None,
    ) -> ApprovalConsumeResult:
        """
        Consume approval token.

        Validates:
        - Token exists
        - Not expired
        - Not already consumed
        - Matches tenant_id
        - Matches ir_hash

        Args:
            request: Consume request
            consumed_by: User/role consuming approval

        Returns:
            ApprovalConsumeResult

        Audit events:
        - ir.approval_consumed (success)
        - ir.approval_expired (if expired)
        - ir.approval_invalid (if invalid)
        """
        # Hash token
        token_hash = self._hash_token(request.token)

        # Find approval by token hash
        approval = self.store.find_by_token_hash(token_hash)

        # Check: approval exists
        if not approval:
            logger.warning(
                f"[Approvals] ir.approval_invalid: token not found "
                f"(tenant_id={request.tenant_id}, ir_hash={request.ir_hash[:16]}...)"
            )
            return ApprovalConsumeResult(
                success=False,
                status=ApprovalStatus.INVALID,
                message="Invalid approval token",
            )

        # Check: tenant_id matches
        if approval.tenant_id != request.tenant_id:
            logger.warning(
                f"[Approvals] ir.approval_invalid: tenant_id mismatch "
                f"(approval={approval.approval_id}, "
                f"expected={approval.tenant_id}, got={request.tenant_id})"
            )
            return ApprovalConsumeResult(
                success=False,
                status=ApprovalStatus.INVALID,
                message="Tenant ID mismatch",
            )

        # Check: ir_hash matches
        if approval.ir_hash != request.ir_hash:
            logger.warning(
                f"[Approvals] ir.approval_invalid: ir_hash mismatch "
                f"(approval={approval.approval_id}, "
                f"expected={approval.ir_hash[:16]}..., got={request.ir_hash[:16]}...)"
            )
            return ApprovalConsumeResult(
                success=False,
                status=ApprovalStatus.INVALID,
                message="IR hash mismatch",
            )

        # Check: not expired
        if datetime.utcnow() > approval.expires_at:
            approval.status = ApprovalStatus.EXPIRED
            self.store.update(approval)

            logger.warning(
                f"[Approvals] ir.approval_expired: "
                f"approval_id={approval.approval_id}, "
                f"tenant_id={approval.tenant_id}, "
                f"ir_hash={approval.ir_hash[:16]}..., "
                f"expired_at={approval.expires_at.isoformat()}"
            )
            return ApprovalConsumeResult(
                success=False,
                status=ApprovalStatus.EXPIRED,
                message=f"Approval expired at {approval.expires_at.isoformat()}",
            )

        # Check: not already consumed
        if approval.status == ApprovalStatus.CONSUMED:
            logger.warning(
                f"[Approvals] ir.approval_invalid: already consumed "
                f"(approval={approval.approval_id}, "
                f"consumed_at={approval.consumed_at.isoformat() if approval.consumed_at else 'unknown'})"
            )
            return ApprovalConsumeResult(
                success=False,
                status=ApprovalStatus.CONSUMED,
                message="Approval already consumed (single-use token)",
            )

        # SUCCESS: Consume approval
        approval.status = ApprovalStatus.CONSUMED
        approval.consumed_at = datetime.utcnow()
        approval.consumed_by = consumed_by
        self.store.update(approval)

        logger.info(
            f"[Approvals] ir.approval_consumed: "
            f"approval_id={approval.approval_id}, "
            f"tenant_id={approval.tenant_id}, "
            f"ir_hash={approval.ir_hash[:16]}..., "
            f"consumed_by={consumed_by or 'system'}"
        )

        return ApprovalConsumeResult(
            success=True,
            status=ApprovalStatus.CONSUMED,
            message="Approval consumed successfully",
            approval_id=approval.approval_id,
        )

    def get_approval_status(
        self,
        approval_id: str,
    ) -> Optional[ApprovalRequest]:
        """
        Get approval status by ID.

        Args:
            approval_id: Approval ID

        Returns:
            ApprovalRequest or None
        """
        approval = self.store.get(approval_id)

        # Check expiration
        if approval and approval.status == ApprovalStatus.PENDING:
            if datetime.utcnow() > approval.expires_at:
                approval.status = ApprovalStatus.EXPIRED
                self.store.update(approval)

        return approval

    def cleanup_expired(self) -> int:
        """
        Cleanup expired approvals.

        Returns:
            Number of approvals cleaned up
        """
        # This is a simple implementation for in-memory store
        # In production, use a background task or TTL in Redis
        count = 0
        now = datetime.utcnow()

        # Note: This modifies the store during iteration, so we need to be careful
        # For production, use proper cleanup with locks or atomic operations
        if isinstance(self.store, InMemoryApprovalStore):
            expired_ids = [
                approval_id
                for approval_id, approval in self.store._approvals.items()
                if approval.status == ApprovalStatus.PENDING and now > approval.expires_at
            ]

            for approval_id in expired_ids:
                approval = self.store.get(approval_id)
                if approval:
                    approval.status = ApprovalStatus.EXPIRED
                    self.store.update(approval)
                    count += 1

        return count

    def _hash_token(self, token: str) -> str:
        """
        Hash token for storage.

        Never store raw tokens. Always hash.

        Args:
            token: Raw token

        Returns:
            SHA256 hash (hex)
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


# Singleton
_approvals_service: Optional[ApprovalsService] = None


def get_approvals_service() -> ApprovalsService:
    """
    Get singleton approvals service.

    Store selection (Sprint 11):
    - APPROVAL_STORE=redis -> RedisApprovalStore
    - APPROVAL_STORE=memory (or not set) -> InMemoryApprovalStore

    Environment variables:
    - APPROVAL_STORE: Store type (redis|memory, default: memory)
    - REDIS_URL: Redis connection URL (default: redis://localhost:6379/0)
    """
    global _approvals_service

    if _approvals_service is None:
        # Determine store type from environment
        store_type = os.getenv("APPROVAL_STORE", "memory").lower()

        if store_type == "redis":
            # Import Redis store
            try:
                from backend.app.modules.ir_governance.redis_approval_store import (
                    RedisApprovalStore,
                )

                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                store = RedisApprovalStore(redis_url=redis_url)
                logger.info(
                    f"[ApprovalsService] Using RedisApprovalStore (url={redis_url})"
                )
            except ImportError as e:
                logger.error(
                    f"[ApprovalsService] Failed to import RedisApprovalStore: {e}. "
                    f"Falling back to InMemoryApprovalStore"
                )
                store = InMemoryApprovalStore()
        else:
            # Default to in-memory store
            store = InMemoryApprovalStore()
            logger.info("[ApprovalsService] Using InMemoryApprovalStore")

        _approvals_service = ApprovalsService(store=store)

    return _approvals_service
