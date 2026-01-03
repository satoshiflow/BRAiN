"""
Redis Approval Store - Sprint 11

Persistent approval storage using Redis.
Solves Sprint 10 limitation: approvals lost on service restart.

Features:
- Persistent storage (survives restart)
- Automatic TTL cleanup via Redis expiration
- Atomic operations
- Horizontal scaling ready
- Fast token_hash lookups via Redis hash

Redis Schema:
- approval:{approval_id} -> JSON (approval object) [TTL = expires_at]
- approval:token_hash:{token_hash} -> approval_id [TTL = expires_at]
- approval:tenant:{tenant_id} -> Set[approval_id] (for listing)
"""

from typing import Optional
import json
from datetime import datetime, timedelta
from loguru import logger

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

from app.modules.ir_governance.schemas import ApprovalRequest, ApprovalStatus


class RedisApprovalStore:
    """
    Redis-based approval storage.

    Advantages over InMemoryApprovalStore:
    - Survives service restarts
    - Automatic TTL cleanup (no manual cleanup_expired needed)
    - Horizontal scaling (multiple instances can share state)
    - Fast lookups via Redis hash structures

    Redis Keys:
    - approval:{approval_id} -> JSON serialized ApprovalRequest
    - approval:token_hash:{token_hash} -> approval_id (for fast lookups)
    - approval:tenant:{tenant_id} -> Set of approval_ids (for listing)
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None, redis_url: Optional[str] = None):
        """
        Initialize Redis approval store.

        Args:
            redis_client: Existing Redis client (optional)
            redis_url: Redis URL (default: redis://localhost:6379/0)
        """
        if redis is None:
            raise ImportError(
                "redis.asyncio not installed. Install with: pip install redis[hiredis]"
            )

        if redis_client:
            self.redis = redis_client
        else:
            url = redis_url or "redis://localhost:6379/0"
            self.redis = redis.from_url(url, decode_responses=True)

        self.key_prefix = "brain:approval"

    def _approval_key(self, approval_id: str) -> str:
        """Get Redis key for approval."""
        return f"{self.key_prefix}:{approval_id}"

    def _token_hash_key(self, token_hash: str) -> str:
        """Get Redis key for token hash index."""
        return f"{self.key_prefix}:token_hash:{token_hash}"

    def _tenant_key(self, tenant_id: str) -> str:
        """Get Redis key for tenant index."""
        return f"{self.key_prefix}:tenant:{tenant_id}"

    def _serialize_approval(self, approval: ApprovalRequest) -> str:
        """Serialize approval to JSON."""
        data = approval.model_dump()
        # Convert datetime objects to ISO strings
        data["expires_at"] = approval.expires_at.isoformat()
        if approval.created_at:
            data["created_at"] = approval.created_at.isoformat()
        if approval.consumed_at:
            data["consumed_at"] = approval.consumed_at.isoformat()
        return json.dumps(data)

    def _deserialize_approval(self, json_str: str) -> ApprovalRequest:
        """Deserialize approval from JSON."""
        data = json.loads(json_str)
        # Convert ISO strings back to datetime
        data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("consumed_at"):
            data["consumed_at"] = datetime.fromisoformat(data["consumed_at"])
        return ApprovalRequest(**data)

    async def create(self, approval: ApprovalRequest) -> bool:
        """
        Create approval request.

        Redis operations:
        1. SET approval:{approval_id} = JSON [EX ttl]
        2. SET approval:token_hash:{token_hash} = approval_id [EX ttl]
        3. SADD approval:tenant:{tenant_id} approval_id

        Args:
            approval: Approval request

        Returns:
            True if created successfully
        """
        try:
            # Calculate TTL in seconds
            ttl_seconds = int((approval.expires_at - datetime.utcnow()).total_seconds())
            if ttl_seconds <= 0:
                logger.warning(
                    f"[RedisApprovalStore] Approval already expired: "
                    f"approval_id={approval.approval_id}, expires_at={approval.expires_at.isoformat()}"
                )
                return False

            # Serialize approval
            json_data = self._serialize_approval(approval)

            # Store approval with TTL
            await self.redis.setex(
                self._approval_key(approval.approval_id),
                ttl_seconds,
                json_data
            )

            # Store token hash index with TTL
            await self.redis.setex(
                self._token_hash_key(approval.token_hash),
                ttl_seconds,
                approval.approval_id
            )

            # Add to tenant index (set, no TTL - cleaned up by cleanup worker)
            await self.redis.sadd(
                self._tenant_key(approval.tenant_id),
                approval.approval_id
            )

            logger.debug(
                f"[RedisApprovalStore] Created approval: "
                f"approval_id={approval.approval_id}, ttl={ttl_seconds}s"
            )
            return True

        except Exception as e:
            logger.error(f"[RedisApprovalStore] Failed to create approval: {e}")
            return False

    async def get(self, approval_id: str) -> Optional[ApprovalRequest]:
        """
        Get approval request by ID.

        Args:
            approval_id: Approval ID

        Returns:
            ApprovalRequest or None if not found/expired
        """
        try:
            json_data = await self.redis.get(self._approval_key(approval_id))
            if not json_data:
                return None

            approval = self._deserialize_approval(json_data)

            # Check expiration (Redis TTL should handle this, but double-check)
            if datetime.utcnow() > approval.expires_at:
                logger.debug(
                    f"[RedisApprovalStore] Approval expired: approval_id={approval_id}"
                )
                return None

            return approval

        except Exception as e:
            logger.error(f"[RedisApprovalStore] Failed to get approval: {e}")
            return None

    async def update(self, approval: ApprovalRequest) -> bool:
        """
        Update approval request.

        Preserves original TTL.

        Args:
            approval: Approval request

        Returns:
            True if updated successfully
        """
        try:
            # Get current TTL
            key = self._approval_key(approval.approval_id)
            ttl = await self.redis.ttl(key)

            if ttl <= 0:
                # Approval expired or doesn't exist
                logger.warning(
                    f"[RedisApprovalStore] Cannot update expired/missing approval: "
                    f"approval_id={approval.approval_id}"
                )
                return False

            # Update approval with preserved TTL
            json_data = self._serialize_approval(approval)
            await self.redis.setex(key, ttl, json_data)

            logger.debug(
                f"[RedisApprovalStore] Updated approval: "
                f"approval_id={approval.approval_id}, remaining_ttl={ttl}s"
            )
            return True

        except Exception as e:
            logger.error(f"[RedisApprovalStore] Failed to update approval: {e}")
            return False

    async def delete(self, approval_id: str) -> bool:
        """
        Delete approval request.

        Args:
            approval_id: Approval ID

        Returns:
            True if deleted successfully
        """
        try:
            # Get approval to get token_hash and tenant_id
            approval = await self.get(approval_id)
            if not approval:
                return False

            # Delete approval
            await self.redis.delete(self._approval_key(approval_id))

            # Delete token hash index
            await self.redis.delete(self._token_hash_key(approval.token_hash))

            # Remove from tenant index
            await self.redis.srem(
                self._tenant_key(approval.tenant_id),
                approval_id
            )

            logger.debug(
                f"[RedisApprovalStore] Deleted approval: approval_id={approval_id}"
            )
            return True

        except Exception as e:
            logger.error(f"[RedisApprovalStore] Failed to delete approval: {e}")
            return False

    async def find_by_token_hash(self, token_hash: str) -> Optional[ApprovalRequest]:
        """
        Find approval by token hash.

        Args:
            token_hash: Token hash (SHA256)

        Returns:
            ApprovalRequest or None if not found
        """
        try:
            # Lookup approval_id from token hash index
            approval_id = await self.redis.get(self._token_hash_key(token_hash))
            if not approval_id:
                return None

            # Get approval
            return await self.get(approval_id)

        except Exception as e:
            logger.error(
                f"[RedisApprovalStore] Failed to find approval by token hash: {e}"
            )
            return None

    async def list_by_tenant(
        self,
        tenant_id: str,
        status: Optional[ApprovalStatus] = None,
        limit: int = 100
    ) -> list[ApprovalRequest]:
        """
        List approvals for a tenant.

        Args:
            tenant_id: Tenant ID
            status: Filter by status (optional)
            limit: Maximum number of approvals to return

        Returns:
            List of approvals (most recent first)
        """
        try:
            # Get all approval_ids for tenant
            approval_ids = await self.redis.smembers(self._tenant_key(tenant_id))

            approvals = []
            for approval_id in approval_ids:
                approval = await self.get(approval_id)
                if approval:
                    # Filter by status if specified
                    if status is None or approval.status == status:
                        approvals.append(approval)

                    # Stop if we hit limit
                    if len(approvals) >= limit:
                        break

            # Sort by created_at descending (most recent first)
            approvals.sort(key=lambda a: a.created_at or datetime.min, reverse=True)

            return approvals[:limit]

        except Exception as e:
            logger.error(
                f"[RedisApprovalStore] Failed to list approvals for tenant: {e}"
            )
            return []

    async def count_by_status(self, tenant_id: str) -> dict[str, int]:
        """
        Count approvals by status for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Dict of status -> count
        """
        try:
            approvals = await self.list_by_tenant(tenant_id, limit=1000)

            counts = {
                ApprovalStatus.PENDING: 0,
                ApprovalStatus.CONSUMED: 0,
                ApprovalStatus.EXPIRED: 0,
            }

            for approval in approvals:
                counts[approval.status] = counts.get(approval.status, 0) + 1

            return counts

        except Exception as e:
            logger.error(
                f"[RedisApprovalStore] Failed to count approvals by status: {e}"
            )
            return {}

    async def cleanup_expired_indices(self) -> int:
        """
        Cleanup expired approval references in tenant indices.

        Redis TTL handles automatic deletion of approval:{approval_id} keys,
        but tenant index sets (approval:tenant:{tenant_id}) need manual cleanup
        since they don't have TTL.

        Returns:
            Number of expired references cleaned up
        """
        try:
            count = 0

            # Scan all tenant keys
            cursor = 0
            pattern = f"{self.key_prefix}:tenant:*"

            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )

                for tenant_key in keys:
                    # Get all approval_ids in set
                    approval_ids = await self.redis.smembers(tenant_key)

                    for approval_id in approval_ids:
                        # Check if approval exists
                        exists = await self.redis.exists(
                            self._approval_key(approval_id)
                        )

                        if not exists:
                            # Remove expired reference from tenant index
                            await self.redis.srem(tenant_key, approval_id)
                            count += 1

                if cursor == 0:
                    break

            if count > 0:
                logger.info(
                    f"[RedisApprovalStore] Cleaned up {count} expired approval references"
                )

            return count

        except Exception as e:
            logger.error(
                f"[RedisApprovalStore] Failed to cleanup expired indices: {e}"
            )
            return 0

    async def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if Redis is accessible
        """
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"[RedisApprovalStore] Health check failed: {e}")
            return False
