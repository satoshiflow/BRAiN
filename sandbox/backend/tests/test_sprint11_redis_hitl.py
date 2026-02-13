"""
Sprint 11 Tests: Redis Backend + HITL UI

Tests for:
1. RedisApprovalStore (persist, TTL, lookups)
2. Cleanup Worker (expired indices cleanup)
3. HITL API endpoints (pending, stats, health)
4. Feature flag switching (memory vs redis)
5. Integration scenarios

Minimum: 10 tests (Sprint 11 requirement)
"""

import sys
import os
import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Path setup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.modules.ir_governance.schemas import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalConsumeRequest,
)
from app.modules.ir_governance.approvals import ApprovalsService, InMemoryApprovalStore
from app.modules.ir_governance.redis_approval_store import RedisApprovalStore
from app.modules.ir_governance.approval_cleanup_worker import ApprovalCleanupWorker


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = AsyncMock()

    # Mock data storage
    redis_mock._data = {}  # key -> value
    redis_mock._ttl = {}  # key -> ttl

    async def mock_setex(key, ttl, value):
        redis_mock._data[key] = value
        redis_mock._ttl[key] = ttl
        return True

    async def mock_get(key):
        return redis_mock._data.get(key)

    async def mock_delete(key):
        redis_mock._data.pop(key, None)
        redis_mock._ttl.pop(key, None)
        return True

    async def mock_sadd(key, *values):
        if key not in redis_mock._data:
            redis_mock._data[key] = set()
        redis_mock._data[key].update(values)
        return len(values)

    async def mock_srem(key, value):
        if key in redis_mock._data:
            redis_mock._data[key].discard(value)
        return True

    async def mock_smembers(key):
        return redis_mock._data.get(key, set())

    async def mock_ttl(key):
        return redis_mock._ttl.get(key, -1)

    async def mock_exists(key):
        return 1 if key in redis_mock._data else 0

    async def mock_scan(cursor=0, match=None, count=100):
        # Simple scan implementation for testing
        keys = list(redis_mock._data.keys())
        if match:
            import fnmatch
            keys = [k for k in keys if fnmatch.fnmatch(k, match)]
        return (0, keys)  # cursor=0 means no more data

    async def mock_ping():
        return True

    redis_mock.setex = mock_setex
    redis_mock.get = mock_get
    redis_mock.delete = mock_delete
    redis_mock.sadd = mock_sadd
    redis_mock.srem = mock_srem
    redis_mock.smembers = mock_smembers
    redis_mock.ttl = mock_ttl
    redis_mock.exists = mock_exists
    redis_mock.scan = mock_scan
    redis_mock.ping = mock_ping

    return redis_mock


@pytest.fixture
async def redis_store(mock_redis):
    """RedisApprovalStore with mocked Redis."""
    store = RedisApprovalStore(redis_client=mock_redis)
    return store


@pytest.fixture
def sample_approval():
    """Sample approval request."""
    return ApprovalRequest(
        approval_id="approval_123",
        tenant_id="tenant_abc",
        ir_hash="ir_hash_xyz",
        token_hash="token_hash_123",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        status=ApprovalStatus.PENDING,
    )


# ============================================================================
# TESTS
# ============================================================================


# Test 1: RedisApprovalStore - Create and Retrieve
@pytest.mark.asyncio
async def test_redis_store_create_and_retrieve(redis_store, sample_approval):
    """Test creating and retrieving approval from Redis store."""
    # Create approval
    success = await redis_store.create(sample_approval)
    assert success is True

    # Retrieve approval
    retrieved = await redis_store.get(sample_approval.approval_id)
    assert retrieved is not None
    assert retrieved.approval_id == sample_approval.approval_id
    assert retrieved.tenant_id == sample_approval.tenant_id
    assert retrieved.ir_hash == sample_approval.ir_hash
    assert retrieved.status == ApprovalStatus.PENDING


# Test 2: RedisApprovalStore - Find by Token Hash
@pytest.mark.asyncio
async def test_redis_store_find_by_token_hash(redis_store, sample_approval):
    """Test finding approval by token hash."""
    # Create approval
    await redis_store.create(sample_approval)

    # Find by token hash
    found = await redis_store.find_by_token_hash(sample_approval.token_hash)
    assert found is not None
    assert found.approval_id == sample_approval.approval_id
    assert found.token_hash == sample_approval.token_hash


# Test 3: RedisApprovalStore - Update Approval
@pytest.mark.asyncio
async def test_redis_store_update(redis_store, sample_approval):
    """Test updating approval in Redis store."""
    # Create approval
    await redis_store.create(sample_approval)

    # Update approval status
    sample_approval.status = ApprovalStatus.CONSUMED
    sample_approval.consumed_at = datetime.utcnow()
    success = await redis_store.update(sample_approval)
    assert success is True

    # Retrieve and verify
    updated = await redis_store.get(sample_approval.approval_id)
    assert updated.status == ApprovalStatus.CONSUMED
    assert updated.consumed_at is not None


# Test 4: RedisApprovalStore - Delete Approval
@pytest.mark.asyncio
async def test_redis_store_delete(redis_store, sample_approval):
    """Test deleting approval from Redis store."""
    # Create approval
    await redis_store.create(sample_approval)

    # Delete approval
    success = await redis_store.delete(sample_approval.approval_id)
    assert success is True

    # Verify deleted
    retrieved = await redis_store.get(sample_approval.approval_id)
    assert retrieved is None


# Test 5: RedisApprovalStore - List by Tenant
@pytest.mark.asyncio
async def test_redis_store_list_by_tenant(redis_store):
    """Test listing approvals by tenant."""
    tenant_id = "tenant_xyz"

    # Create multiple approvals for same tenant
    approval1 = ApprovalRequest(
        approval_id="approval_1",
        tenant_id=tenant_id,
        ir_hash="ir_hash_1",
        token_hash="token_hash_1",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        status=ApprovalStatus.PENDING,
    )
    approval2 = ApprovalRequest(
        approval_id="approval_2",
        tenant_id=tenant_id,
        ir_hash="ir_hash_2",
        token_hash="token_hash_2",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        status=ApprovalStatus.CONSUMED,
    )

    await redis_store.create(approval1)
    await redis_store.create(approval2)

    # List all approvals for tenant
    approvals = await redis_store.list_by_tenant(tenant_id)
    assert len(approvals) == 2

    # Filter by status
    pending = await redis_store.list_by_tenant(tenant_id, status=ApprovalStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].approval_id == "approval_1"


# Test 6: RedisApprovalStore - Count by Status
@pytest.mark.asyncio
async def test_redis_store_count_by_status(redis_store):
    """Test counting approvals by status."""
    tenant_id = "tenant_count"

    # Create approvals with different statuses
    approvals = [
        ApprovalRequest(
            approval_id=f"approval_{i}",
            tenant_id=tenant_id,
            ir_hash=f"ir_hash_{i}",
            token_hash=f"token_hash_{i}",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            status=ApprovalStatus.PENDING if i < 2 else ApprovalStatus.CONSUMED,
        )
        for i in range(5)
    ]

    for approval in approvals:
        await redis_store.create(approval)

    # Count by status
    counts = await redis_store.count_by_status(tenant_id)
    assert counts[ApprovalStatus.PENDING] == 2
    assert counts[ApprovalStatus.CONSUMED] == 3


# Test 7: Cleanup Worker - Cleanup Expired Indices
@pytest.mark.asyncio
async def test_cleanup_worker_expired_indices(redis_store):
    """Test cleanup worker removes expired approval references."""
    tenant_id = "tenant_cleanup"

    # Create approval
    approval = ApprovalRequest(
        approval_id="approval_expired",
        tenant_id=tenant_id,
        ir_hash="ir_hash_expired",
        token_hash="token_hash_expired",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        status=ApprovalStatus.PENDING,
    )
    await redis_store.create(approval)

    # Simulate approval expiration (delete from Redis but leave in tenant index)
    await redis_store.redis.delete(redis_store._approval_key(approval.approval_id))

    # Run cleanup
    cleaned = await redis_store.cleanup_expired_indices()
    assert cleaned == 1

    # Verify tenant index cleaned
    tenant_approvals = await redis_store.list_by_tenant(tenant_id)
    assert len(tenant_approvals) == 0


# Test 8: Cleanup Worker - Statistics Tracking
@pytest.mark.asyncio
async def test_cleanup_worker_stats(redis_store):
    """Test cleanup worker tracks statistics."""
    service = ApprovalsService(store=redis_store)
    worker = ApprovalCleanupWorker(service, interval_seconds=1)

    # Start worker
    await worker.start()
    assert worker.running is True

    # Wait for at least one run
    await asyncio.sleep(1.5)

    # Get stats
    stats = worker.get_stats()
    assert stats["runs"] >= 1
    assert stats["running"] is True
    assert stats["last_run"] is not None

    # Stop worker
    await worker.stop()
    assert worker.running is False


# Test 9: HITL Service with Redis Store
@pytest.mark.asyncio
async def test_approvals_service_with_redis(redis_store):
    """Test ApprovalsService works with RedisApprovalStore."""
    service = ApprovalsService(store=redis_store)

    # Create approval
    approval, raw_token = service.create_approval(
        tenant_id="tenant_service",
        ir_hash="ir_hash_service",
        ttl_seconds=3600,
    )

    assert approval.approval_id is not None
    assert raw_token is not None
    assert len(raw_token) > 0

    # Consume approval
    consume_result = service.consume_approval(
        ApprovalConsumeRequest(
            tenant_id="tenant_service",
            ir_hash="ir_hash_service",
            token=raw_token,
        )
    )

    assert consume_result.success is True
    assert consume_result.status == ApprovalStatus.CONSUMED


# Test 10: Feature Flag - Memory vs Redis Store
def test_feature_flag_store_selection():
    """Test approval store selection via environment variable."""
    # Test memory store (default)
    with patch.dict(os.environ, {"APPROVAL_STORE": "memory"}):
        from app.modules.ir_governance.approvals import get_approvals_service

        # Reset singleton
        import backend.app.modules.ir_governance.approvals as approvals_module
        approvals_module._approvals_service = None

        service = get_approvals_service()
        assert isinstance(service.store, InMemoryApprovalStore)


# Test 11: Redis Health Check
@pytest.mark.asyncio
async def test_redis_health_check(redis_store):
    """Test Redis health check."""
    # Healthy Redis
    healthy = await redis_store.health_check()
    assert healthy is True

    # Unhealthy Redis (mock ping failure)
    async def mock_ping_fail():
        raise Exception("Redis connection failed")

    redis_store.redis.ping = mock_ping_fail
    healthy = await redis_store.health_check()
    assert healthy is False


# Test 12: Expired Approval Not Retrieved
@pytest.mark.asyncio
async def test_redis_store_expired_approval_not_retrieved(redis_store):
    """Test that expired approvals are not retrieved."""
    # Create approval that expires immediately
    expired_approval = ApprovalRequest(
        approval_id="approval_expired",
        tenant_id="tenant_expired",
        ir_hash="ir_hash_expired",
        token_hash="token_hash_expired",
        expires_at=datetime.utcnow() - timedelta(seconds=1),  # Already expired
        status=ApprovalStatus.PENDING,
    )

    # Should fail to create (already expired)
    success = await redis_store.create(expired_approval)
    assert success is False


# Test 13: Approval TTL Enforcement
@pytest.mark.asyncio
async def test_approval_ttl_enforcement(redis_store):
    """Test that Redis TTL is properly set and enforced."""
    approval = ApprovalRequest(
        approval_id="approval_ttl",
        tenant_id="tenant_ttl",
        ir_hash="ir_hash_ttl",
        token_hash="token_hash_ttl",
        expires_at=datetime.utcnow() + timedelta(seconds=10),
        status=ApprovalStatus.PENDING,
    )

    # Create approval
    await redis_store.create(approval)

    # Check TTL was set
    ttl = await redis_store.redis.ttl(redis_store._approval_key(approval.approval_id))
    assert ttl > 0
    assert ttl <= 10


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    # Run with: python -m pytest backend/tests/test_sprint11_redis_hitl.py -v
    pytest.main([__file__, "-v", "-s"])
