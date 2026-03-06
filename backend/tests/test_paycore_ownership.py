"""PayCore ownership guard tests."""

import pytest
from uuid import uuid4

from app.core.auth_deps import Principal, PrincipalType
from app.modules.paycore.router import verify_intent_ownership, verify_refund_ownership


class FakePayCoreService:
    def __init__(self, intent_tenant=None, refund_tenant=None):
        self._intent_tenant = intent_tenant
        self._refund_tenant = refund_tenant

    async def get_intent_tenant_id(self, intent_id):
        return self._intent_tenant

    async def get_refund_tenant_id(self, refund_id):
        return self._refund_tenant


def make_principal(tenant_id: str) -> Principal:
    return Principal(
        principal_id="user-123",
        principal_type=PrincipalType.HUMAN,
        email="user@example.com",
        name="Test User",
        roles=["operator"],
        scopes=["brain:read"],
        tenant_id=tenant_id,
    )


@pytest.mark.asyncio
async def test_verify_intent_ownership_allows_matching_tenant():
    principal = make_principal("tenant-a")
    service = FakePayCoreService(intent_tenant="tenant-a")

    assert await verify_intent_ownership(principal, uuid4(), service) is True


@pytest.mark.asyncio
async def test_verify_intent_ownership_denies_mismatched_tenant():
    principal = make_principal("tenant-a")
    service = FakePayCoreService(intent_tenant="tenant-b")

    assert await verify_intent_ownership(principal, uuid4(), service) is False


@pytest.mark.asyncio
async def test_verify_intent_ownership_allows_default_tenant_override():
    principal = make_principal("default")
    service = FakePayCoreService(intent_tenant="tenant-b")

    assert await verify_intent_ownership(principal, uuid4(), service) is True


@pytest.mark.asyncio
async def test_verify_refund_ownership_allows_matching_tenant():
    principal = make_principal("tenant-a")
    service = FakePayCoreService(refund_tenant="tenant-a")

    assert await verify_refund_ownership(principal, uuid4(), service) is True


@pytest.mark.asyncio
async def test_verify_refund_ownership_denies_unknown_refund():
    principal = make_principal("tenant-a")
    service = FakePayCoreService(refund_tenant=None)

    assert await verify_refund_ownership(principal, uuid4(), service) is False
