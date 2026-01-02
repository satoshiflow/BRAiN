"""
Hetzner DNS Service Tests (Sprint II)

Tests for DNS automation with Hetzner DNS API integration.

Coverage:
- Allowlist enforcement
- Idempotent upsert behavior
- LOCAL-only trust tier enforcement
- DNS record creation/update/no-change logic
- Error handling and graceful degradation
"""

import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


# ============================================================================
# Test: DNS Endpoints - Trust Tier Enforcement (STRICT LOCAL ONLY)
# ============================================================================


def test_dns_apply_blocks_external():
    """Test that DNS apply endpoint blocks EXTERNAL trust tier."""
    payload = {
        "zone": "example.com",
        "record_type": "A",
        "name": "@",
        "value": "203.0.113.10",
        "ttl": 300,
    }

    # EXTERNAL request (no headers)
    response = client.post("/api/dns/hetzner/apply", json=payload)

    # Should block with 403
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "LOCAL" in str(data)


def test_dns_apply_blocks_dmz():
    """Test that DNS apply endpoint blocks DMZ trust tier."""
    headers = {
        "x-dmz-gateway-id": "test_gateway",
        "x-dmz-gateway-token": "test_token",
    }

    payload = {
        "zone": "example.com",
        "record_type": "A",
        "name": "@",
        "value": "203.0.113.10",
        "ttl": 300,
    }

    # DMZ request (should be blocked - DNS is LOCAL only)
    response = client.post("/api/dns/hetzner/apply", headers=headers, json=payload)

    # Should block with 403 (DNS requires LOCAL, not DMZ)
    assert response.status_code == 403


def test_dns_zones_list_blocks_external():
    """Test that DNS zones list endpoint blocks EXTERNAL trust tier."""
    # EXTERNAL request
    response = client.get("/api/dns/hetzner/zones")

    # Should block with 403
    assert response.status_code == 403


def test_dns_zones_list_blocks_dmz():
    """Test that DNS zones list endpoint blocks DMZ trust tier."""
    headers = {
        "x-dmz-gateway-id": "test_gateway",
        "x-dmz-gateway-token": "test_token",
    }

    # DMZ request
    response = client.get("/api/dns/hetzner/zones", headers=headers)

    # Should block with 403
    assert response.status_code == 403


# ============================================================================
# Test: DNS Record Type Enum
# ============================================================================


def test_dns_record_type_enum_values():
    """Test that DNSRecordType enum has all required values."""
    from backend.app.modules.dns_hetzner.schemas import DNSRecordType

    required_types = [
        "A",
        "AAAA",
        "CNAME",
        "MX",
        "TXT",
        "NS",
        "SRV",
        "CAA",
        "TLSA",
    ]

    for record_type in required_types:
        assert hasattr(
            DNSRecordType, record_type
        ), f"Missing record type: {record_type}"


# ============================================================================
# Test: DNS Models Validation
# ============================================================================


def test_dns_record_apply_request_model():
    """Test DNSRecordApplyRequest model validation."""
    from backend.app.modules.dns_hetzner.schemas import DNSRecordApplyRequest

    # Valid request
    request = DNSRecordApplyRequest(
        zone="example.com",
        record_type="A",
        name="@",
        value="203.0.113.10",
        ttl=300,
    )

    assert request.zone == "example.com"
    assert request.record_type == "A"
    assert request.name == "@"
    assert request.value == "203.0.113.10"
    assert request.ttl == 300


def test_dns_record_apply_request_optional_value():
    """Test that DNSRecordApplyRequest allows optional value (for ENV defaults)."""
    from backend.app.modules.dns_hetzner.schemas import DNSRecordApplyRequest

    # Value is optional (will use ENV default)
    request = DNSRecordApplyRequest(
        zone="example.com",
        record_type="A",
        name="@",
        # value not provided - should use BRAIN_PUBLIC_IPV4
    )

    assert request.value is None


def test_dns_record_apply_request_default_ttl():
    """Test that DNSRecordApplyRequest has default TTL of 300."""
    from backend.app.modules.dns_hetzner.schemas import DNSRecordApplyRequest

    request = DNSRecordApplyRequest(
        zone="example.com",
        record_type="A",
        name="@",
        value="203.0.113.10",
    )

    assert request.ttl == 300


def test_dns_apply_result_model():
    """Test DNSApplyResult model structure."""
    from backend.app.modules.dns_hetzner.schemas import DNSApplyResult

    result = DNSApplyResult(
        success=True,
        zone="example.com",
        record_type="A",
        name="@",
        value="203.0.113.10",
        ttl=300,
        action="created",
        message="DNS record created successfully",
    )

    assert result.success is True
    assert result.action == "created"


def test_dns_apply_result_action_enum():
    """Test that action field uses correct enum values."""
    from backend.app.modules.dns_hetzner.schemas import DNSApplyResult

    valid_actions = ["created", "updated", "no_change"]

    for action in valid_actions:
        result = DNSApplyResult(
            success=True,
            zone="example.com",
            record_type="A",
            name="@",
            value="203.0.113.10",
            ttl=300,
            action=action,
            message=f"Action: {action}",
        )
        assert result.action == action


# ============================================================================
# Test: Hetzner DNS Config Model
# ============================================================================


def test_hetzner_dns_config_model():
    """Test HetznerDNSConfig model with defaults."""
    from backend.app.modules.dns_hetzner.schemas import HetznerDNSConfig

    config = HetznerDNSConfig(
        api_token="test_token",
        allowed_zones=["example.com", "test.com"],
    )

    assert config.api_token == "test_token"
    assert config.allowed_zones == ["example.com", "test.com"]
    assert config.default_ttl == 300  # Default value
    assert config.timeout == 30  # Default value


# ============================================================================
# Test: DNS Service - Allowlist Enforcement
# ============================================================================


@pytest.mark.asyncio
async def test_dns_service_enforces_allowlist():
    """Test that DNS service blocks zones not in allowlist."""
    from backend.app.modules.dns_hetzner.service import HetznerDNSService
    from backend.app.modules.dns_hetzner.schemas import (
        HetznerDNSConfig,
        DNSRecordType,
    )

    # Config with specific allowlist
    config = HetznerDNSConfig(
        api_token="test_token",
        allowed_zones=["example.com"],  # Only example.com allowed
    )

    service = HetznerDNSService(config=config)

    # Try to apply record for non-allowed zone
    result = await service.apply_dns_record(
        zone="evil.com",  # NOT in allowlist
        record_type=DNSRecordType.A,
        name="@",
        value="203.0.113.10",
    )

    # Should fail with allowlist error
    assert result.success is False
    assert "not in allowlist" in result.message.lower() or any(
        "not allowed" in err.lower() for err in result.errors
    )


@pytest.mark.asyncio
async def test_dns_service_allows_allowlisted_zones():
    """Test that DNS service allows zones in allowlist."""
    from backend.app.modules.dns_hetzner.service import HetznerDNSService
    from backend.app.modules.dns_hetzner.schemas import (
        HetznerDNSConfig,
        DNSRecordType,
        DNSZone,
    )

    config = HetznerDNSConfig(
        api_token="test_token",
        allowed_zones=["example.com"],
    )

    service = HetznerDNSService(config=config)

    # Mock the client to avoid real API calls
    with patch.object(service.client, "get_zone_by_name") as mock_get_zone:
        with patch.object(service.client, "find_record") as mock_find_record:
            with patch.object(service.client, "create_record") as mock_create_record:
                # Setup mocks
                mock_get_zone.return_value = DNSZone(
                    id="zone123",
                    name="example.com",
                    ttl=3600,
                )
                mock_find_record.return_value = None  # Record doesn't exist
                mock_create_record.return_value = MagicMock(
                    id="rec123",
                    zone_id="zone123",
                    type=DNSRecordType.A,
                    name="@",
                    value="203.0.113.10",
                    ttl=300,
                )

                # Apply record for allowed zone
                result = await service.apply_dns_record(
                    zone="example.com",  # In allowlist
                    record_type=DNSRecordType.A,
                    name="@",
                    value="203.0.113.10",
                )

                # Should succeed
                assert result.success is True


# ============================================================================
# Test: DNS Service - Idempotent Upsert Behavior
# ============================================================================


@pytest.mark.asyncio
async def test_dns_service_creates_new_record():
    """Test that DNS service creates record if it doesn't exist."""
    from backend.app.modules.dns_hetzner.service import HetznerDNSService
    from backend.app.modules.dns_hetzner.schemas import (
        HetznerDNSConfig,
        DNSRecordType,
        DNSZone,
        DNSRecord,
    )

    config = HetznerDNSConfig(
        api_token="test_token",
        allowed_zones=["example.com"],
    )

    service = HetznerDNSService(config=config)

    with patch.object(service.client, "get_zone_by_name") as mock_get_zone:
        with patch.object(service.client, "find_record") as mock_find_record:
            with patch.object(service.client, "create_record") as mock_create_record:
                # Setup mocks
                mock_get_zone.return_value = DNSZone(
                    id="zone123", name="example.com", ttl=3600
                )
                mock_find_record.return_value = None  # Record doesn't exist

                created_record = DNSRecord(
                    id="rec123",
                    zone_id="zone123",
                    type=DNSRecordType.A,
                    name="@",
                    value="203.0.113.10",
                    ttl=300,
                    created="2025-01-01T12:00:00Z",
                    modified="2025-01-01T12:00:00Z",
                )
                mock_create_record.return_value = created_record

                # Apply record
                result = await service.apply_dns_record(
                    zone="example.com",
                    record_type=DNSRecordType.A,
                    name="@",
                    value="203.0.113.10",
                )

                # Should create new record
                assert result.success is True
                assert result.action == "created"
                mock_create_record.assert_called_once()


@pytest.mark.asyncio
async def test_dns_service_updates_existing_record():
    """Test that DNS service updates record if value changed."""
    from backend.app.modules.dns_hetzner.service import HetznerDNSService
    from backend.app.modules.dns_hetzner.schemas import (
        HetznerDNSConfig,
        DNSRecordType,
        DNSZone,
        DNSRecord,
    )

    config = HetznerDNSConfig(
        api_token="test_token",
        allowed_zones=["example.com"],
    )

    service = HetznerDNSService(config=config)

    with patch.object(service.client, "get_zone_by_name") as mock_get_zone:
        with patch.object(service.client, "find_record") as mock_find_record:
            with patch.object(service.client, "update_record") as mock_update_record:
                # Setup mocks
                mock_get_zone.return_value = DNSZone(
                    id="zone123", name="example.com", ttl=3600
                )

                # Existing record with different value
                existing_record = DNSRecord(
                    id="rec123",
                    zone_id="zone123",
                    type=DNSRecordType.A,
                    name="@",
                    value="203.0.113.1",  # OLD value
                    ttl=300,
                    created="2025-01-01T12:00:00Z",
                    modified="2025-01-01T12:00:00Z",
                )
                mock_find_record.return_value = existing_record

                updated_record = DNSRecord(
                    id="rec123",
                    zone_id="zone123",
                    type=DNSRecordType.A,
                    name="@",
                    value="203.0.113.10",  # NEW value
                    ttl=300,
                    created="2025-01-01T12:00:00Z",
                    modified="2025-01-01T13:00:00Z",
                )
                mock_update_record.return_value = updated_record

                # Apply record with new value
                result = await service.apply_dns_record(
                    zone="example.com",
                    record_type=DNSRecordType.A,
                    name="@",
                    value="203.0.113.10",  # Different from existing
                )

                # Should update record
                assert result.success is True
                assert result.action == "updated"
                mock_update_record.assert_called_once()


@pytest.mark.asyncio
async def test_dns_service_no_change_if_same():
    """Test that DNS service returns no_change if record identical."""
    from backend.app.modules.dns_hetzner.service import HetznerDNSService
    from backend.app.modules.dns_hetzner.schemas import (
        HetznerDNSConfig,
        DNSRecordType,
        DNSZone,
        DNSRecord,
    )

    config = HetznerDNSConfig(
        api_token="test_token",
        allowed_zones=["example.com"],
    )

    service = HetznerDNSService(config=config)

    with patch.object(service.client, "get_zone_by_name") as mock_get_zone:
        with patch.object(service.client, "find_record") as mock_find_record:
            with patch.object(service.client, "update_record") as mock_update_record:
                # Setup mocks
                mock_get_zone.return_value = DNSZone(
                    id="zone123", name="example.com", ttl=3600
                )

                # Existing record with SAME value and TTL
                existing_record = DNSRecord(
                    id="rec123",
                    zone_id="zone123",
                    type=DNSRecordType.A,
                    name="@",
                    value="203.0.113.10",  # SAME value
                    ttl=300,  # SAME TTL
                    created="2025-01-01T12:00:00Z",
                    modified="2025-01-01T12:00:00Z",
                )
                mock_find_record.return_value = existing_record

                # Apply record with same value and TTL
                result = await service.apply_dns_record(
                    zone="example.com",
                    record_type=DNSRecordType.A,
                    name="@",
                    value="203.0.113.10",  # Same as existing
                    ttl=300,  # Same as existing
                )

                # Should return no_change
                assert result.success is True
                assert result.action == "no_change"
                mock_update_record.assert_not_called()  # Should NOT update


# ============================================================================
# Test: DNS Service - ENV Default Values
# ============================================================================


@pytest.mark.asyncio
async def test_dns_service_uses_env_default_for_ipv4():
    """Test that DNS service uses BRAIN_PUBLIC_IPV4 when value not provided."""
    from backend.app.modules.dns_hetzner.service import HetznerDNSService
    from backend.app.modules.dns_hetzner.schemas import (
        HetznerDNSConfig,
        DNSRecordType,
    )

    config = HetznerDNSConfig(
        api_token="test_token",
        allowed_zones=["example.com"],
        public_ipv4="203.0.113.100",  # ENV default
    )

    service = HetznerDNSService(config=config)

    with patch.object(service.client, "get_zone_by_name") as mock_get_zone:
        with patch.object(service.client, "find_record") as mock_find_record:
            with patch.object(service.client, "create_record") as mock_create_record:
                from backend.app.modules.dns_hetzner.schemas import DNSZone, DNSRecord

                mock_get_zone.return_value = DNSZone(
                    id="zone123", name="example.com", ttl=3600
                )
                mock_find_record.return_value = None

                created_record = DNSRecord(
                    id="rec123",
                    zone_id="zone123",
                    type=DNSRecordType.A,
                    name="@",
                    value="203.0.113.100",  # ENV default used
                    ttl=300,
                    created="2025-01-01T12:00:00Z",
                    modified="2025-01-01T12:00:00Z",
                )
                mock_create_record.return_value = created_record

                # Apply without value (should use ENV default)
                result = await service.apply_dns_record(
                    zone="example.com",
                    record_type=DNSRecordType.A,
                    name="@",
                    value=None,  # No value - should use ENV
                )

                # Should use ENV default
                assert result.success is True
                assert result.value == "203.0.113.100"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
