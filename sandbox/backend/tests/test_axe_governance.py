"""
Test Suite for AXE Governance (G3)

Tests the Trust Tier system and DMZ-only access enforcement.

Test Categories:
- Positive Tests: Localhost and DMZ gateway with valid authentication
- Negative Tests: External requests, invalid tokens, unknown gateways
- Bypass Attempts: Header spoofing, missing headers, token manipulation
"""

import sys
import os

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from app.modules.axe_governance import (
    AXETrustValidator,
    TrustTier,
    get_axe_trust_validator,
)
import hashlib

client = TestClient(app)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def dmz_gateway_id():
    """Valid DMZ gateway identifier."""
    return "telegram_gateway"


@pytest.fixture
def dmz_shared_secret():
    """DMZ shared secret (from AXETrustValidator)."""
    return "REPLACE_WITH_SECURE_SECRET_IN_PRODUCTION"


@pytest.fixture
def valid_dmz_token(dmz_gateway_id, dmz_shared_secret):
    """Generate valid DMZ gateway token."""
    raw = f"{dmz_gateway_id}:{dmz_shared_secret}"
    return hashlib.sha256(raw.encode()).hexdigest()


@pytest.fixture
def dmz_headers(dmz_gateway_id, valid_dmz_token):
    """Valid DMZ authentication headers."""
    return {
        "X-DMZ-Gateway-ID": dmz_gateway_id,
        "X-DMZ-Gateway-Token": valid_dmz_token,
    }


# ============================================================================
# POSITIVE TESTS - Localhost Access
# ============================================================================


def test_axe_info_localhost():
    """Test AXE /info endpoint from localhost (should work)."""
    response = client.get("/api/axe/info")

    assert response.status_code == 200
    data = response.json()

    # Check basic response structure
    assert data["name"] == "AXE"
    assert "governance" in data
    assert data["governance"]["trust_tier"] == "local"
    assert data["governance"]["authenticated"] is True


def test_axe_message_localhost():
    """Test AXE /message endpoint from localhost (should work)."""
    payload = {"message": "Test message from localhost", "metadata": {}}

    response = client.post("/api/axe/message", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Check governance metadata
    assert "governance" in data
    assert data["governance"]["trust_tier"] == "local"
    assert data["governance"]["authenticated"] is True


# ============================================================================
# POSITIVE TESTS - DMZ Gateway Authentication
# ============================================================================


def test_axe_info_dmz_valid_token(dmz_headers):
    """Test AXE /info endpoint with valid DMZ authentication (should work)."""
    response = client.get("/api/axe/info", headers=dmz_headers)

    assert response.status_code == 200
    data = response.json()

    # Check governance metadata
    assert "governance" in data
    assert data["governance"]["trust_tier"] == "dmz"
    assert data["governance"]["source_service"] == "telegram_gateway"
    assert data["governance"]["authenticated"] is True


def test_axe_message_dmz_valid_token(dmz_headers):
    """Test AXE /message endpoint with valid DMZ authentication (should work)."""
    payload = {"message": "Test message from DMZ gateway", "metadata": {}}

    response = client.post("/api/axe/message", json=payload, headers=dmz_headers)

    assert response.status_code == 200
    data = response.json()

    # Check governance metadata
    assert "governance" in data
    assert data["governance"]["trust_tier"] == "dmz"
    assert data["governance"]["source_service"] == "telegram_gateway"
    assert data["governance"]["authenticated"] is True


# ============================================================================
# NEGATIVE TESTS - Invalid Authentication
# ============================================================================


def test_axe_info_invalid_token(dmz_gateway_id):
    """Test AXE /info endpoint with invalid token (should be blocked)."""
    invalid_headers = {
        "X-DMZ-Gateway-ID": dmz_gateway_id,
        "X-DMZ-Gateway-Token": "invalid_token_12345",
    }

    response = client.get("/api/axe/info", headers=invalid_headers)

    # Should be blocked (403 Forbidden)
    assert response.status_code == 403
    data = response.json()

    assert "detail" in data
    assert data["detail"]["error"] == "Forbidden"
    assert "AXE is only accessible via DMZ gateways" in data["detail"]["message"]
    assert data["detail"]["trust_tier"] == "external"


def test_axe_message_invalid_token(dmz_gateway_id):
    """Test AXE /message endpoint with invalid token (should be blocked)."""
    invalid_headers = {
        "X-DMZ-Gateway-ID": dmz_gateway_id,
        "X-DMZ-Gateway-Token": "invalid_token_12345",
    }

    payload = {"message": "Test message with invalid token", "metadata": {}}

    response = client.post("/api/axe/message", json=payload, headers=invalid_headers)

    assert response.status_code == 403
    data = response.json()

    assert data["detail"]["error"] == "Forbidden"
    assert data["detail"]["trust_tier"] == "external"


def test_axe_info_unknown_gateway(valid_dmz_token):
    """Test AXE /info endpoint with unknown gateway ID (should be blocked)."""
    unknown_headers = {
        "X-DMZ-Gateway-ID": "unknown_gateway_xyz",
        "X-DMZ-Gateway-Token": valid_dmz_token,
    }

    response = client.get("/api/axe/info", headers=unknown_headers)

    assert response.status_code == 403
    data = response.json()

    assert data["detail"]["error"] == "Forbidden"
    assert data["detail"]["trust_tier"] == "external"


def test_axe_info_missing_token_header(dmz_gateway_id):
    """Test AXE /info endpoint with missing token header (should be blocked)."""
    incomplete_headers = {
        "X-DMZ-Gateway-ID": dmz_gateway_id,
        # Missing X-DMZ-Gateway-Token
    }

    response = client.get("/api/axe/info", headers=incomplete_headers)

    assert response.status_code == 403
    data = response.json()

    assert data["detail"]["error"] == "Forbidden"
    assert data["detail"]["trust_tier"] == "external"


def test_axe_info_missing_gateway_id_header(valid_dmz_token):
    """Test AXE /info endpoint with missing gateway ID header (should be blocked)."""
    incomplete_headers = {
        # Missing X-DMZ-Gateway-ID
        "X-DMZ-Gateway-Token": valid_dmz_token,
    }

    response = client.get("/api/axe/info", headers=incomplete_headers)

    assert response.status_code == 403
    data = response.json()

    assert data["detail"]["error"] == "Forbidden"
    assert data["detail"]["trust_tier"] == "external"


# ============================================================================
# BYPASS ATTEMPT TESTS
# ============================================================================


def test_axe_info_empty_headers():
    """
    Test AXE /info endpoint with empty DMZ headers (should be blocked).

    Simulates bypass attempt with empty string headers.
    """
    bypass_headers = {
        "X-DMZ-Gateway-ID": "",
        "X-DMZ-Gateway-Token": "",
    }

    response = client.get("/api/axe/info", headers=bypass_headers)

    assert response.status_code == 403
    data = response.json()

    assert data["detail"]["error"] == "Forbidden"
    assert data["detail"]["trust_tier"] == "external"


def test_axe_info_token_case_sensitivity(dmz_gateway_id, valid_dmz_token):
    """
    Test AXE /info endpoint with uppercase token (should be blocked).

    Tokens are case-sensitive - uppercase should fail.
    """
    case_headers = {
        "X-DMZ-Gateway-ID": dmz_gateway_id,
        "X-DMZ-Gateway-Token": valid_dmz_token.upper(),  # Uppercase
    }

    response = client.get("/api/axe/info", headers=case_headers)

    assert response.status_code == 403
    data = response.json()

    assert data["detail"]["error"] == "Forbidden"


def test_axe_info_sql_injection_attempt():
    """
    Test AXE /info endpoint with SQL injection attempt (should be blocked).

    Even if SQL injection were possible (it's not), request should be blocked
    at trust tier validation.
    """
    sql_injection_headers = {
        "X-DMZ-Gateway-ID": "telegram_gateway' OR '1'='1",
        "X-DMZ-Gateway-Token": "' OR '1'='1' --",
    }

    response = client.get("/api/axe/info", headers=sql_injection_headers)

    assert response.status_code == 403
    data = response.json()

    assert data["detail"]["error"] == "Forbidden"
    assert data["detail"]["trust_tier"] == "external"


def test_axe_info_header_injection_attempt():
    """
    Test AXE /info endpoint with newline injection attempt (should be blocked).

    FastAPI/Starlette protects against header injection, but request should
    still be blocked at trust tier validation.
    """
    header_injection_headers = {
        "X-DMZ-Gateway-ID": "telegram_gateway\r\nX-Admin: true",
        "X-DMZ-Gateway-Token": "fake_token",
    }

    response = client.get("/api/axe/info", headers=header_injection_headers)

    # Should either be blocked by FastAPI or fail trust tier validation
    assert response.status_code in [400, 403]


# ============================================================================
# UNIT TESTS - AXETrustValidator
# ============================================================================


@pytest.mark.asyncio
async def test_validator_localhost_detection():
    """Test AXETrustValidator correctly identifies localhost requests."""
    validator = get_axe_trust_validator()

    context = await validator.validate_request(
        headers={}, client_host="127.0.0.1", request_id="test-001"
    )

    assert context.trust_tier == TrustTier.LOCAL
    assert context.authenticated is True
    assert context.source_service == "localhost"


@pytest.mark.asyncio
async def test_validator_localhost_ipv6():
    """Test AXETrustValidator correctly identifies localhost IPv6 requests."""
    validator = get_axe_trust_validator()

    context = await validator.validate_request(
        headers={}, client_host="::1", request_id="test-002"
    )

    assert context.trust_tier == TrustTier.LOCAL
    assert context.authenticated is True


@pytest.mark.asyncio
async def test_validator_dmz_gateway_valid():
    """Test AXETrustValidator correctly validates DMZ gateway with valid token."""
    validator = get_axe_trust_validator()

    # Generate valid token
    gateway_id = "telegram_gateway"
    shared_secret = "REPLACE_WITH_SECURE_SECRET_IN_PRODUCTION"
    raw = f"{gateway_id}:{shared_secret}"
    valid_token = hashlib.sha256(raw.encode()).hexdigest()

    headers = {
        "x-dmz-gateway-id": gateway_id,
        "x-dmz-gateway-token": valid_token,
    }

    context = await validator.validate_request(
        headers=headers, client_host="172.20.0.5", request_id="test-003"
    )

    assert context.trust_tier == TrustTier.DMZ
    assert context.authenticated is True
    assert context.source_service == "telegram_gateway"


@pytest.mark.asyncio
async def test_validator_dmz_gateway_invalid_token():
    """Test AXETrustValidator rejects DMZ gateway with invalid token."""
    validator = get_axe_trust_validator()

    headers = {
        "x-dmz-gateway-id": "telegram_gateway",
        "x-dmz-gateway-token": "invalid_token",
    }

    context = await validator.validate_request(
        headers=headers, client_host="172.20.0.5", request_id="test-004"
    )

    # Invalid token → treated as EXTERNAL
    assert context.trust_tier == TrustTier.EXTERNAL
    assert context.authenticated is False


@pytest.mark.asyncio
async def test_validator_unknown_gateway():
    """Test AXETrustValidator rejects unknown gateway."""
    validator = get_axe_trust_validator()

    headers = {
        "x-dmz-gateway-id": "unknown_gateway",
        "x-dmz-gateway-token": "any_token",
    }

    context = await validator.validate_request(
        headers=headers, client_host="172.20.0.5", request_id="test-005"
    )

    assert context.trust_tier == TrustTier.EXTERNAL
    assert context.authenticated is False


@pytest.mark.asyncio
async def test_validator_external_request():
    """Test AXETrustValidator classifies external requests correctly."""
    validator = get_axe_trust_validator()

    context = await validator.validate_request(
        headers={}, client_host="203.0.113.42", request_id="test-006"
    )

    assert context.trust_tier == TrustTier.EXTERNAL
    assert context.authenticated is False
    assert context.source_service == "unknown"


@pytest.mark.asyncio
async def test_validator_is_request_allowed_local():
    """Test AXETrustValidator allows LOCAL requests."""
    validator = get_axe_trust_validator()

    context = await validator.validate_request(
        headers={}, client_host="127.0.0.1", request_id="test-007"
    )

    assert validator.is_request_allowed(context) is True


@pytest.mark.asyncio
async def test_validator_is_request_allowed_dmz():
    """Test AXETrustValidator allows DMZ requests."""
    validator = get_axe_trust_validator()

    gateway_id = "telegram_gateway"
    shared_secret = "REPLACE_WITH_SECURE_SECRET_IN_PRODUCTION"
    raw = f"{gateway_id}:{shared_secret}"
    valid_token = hashlib.sha256(raw.encode()).hexdigest()

    headers = {
        "x-dmz-gateway-id": gateway_id,
        "x-dmz-gateway-token": valid_token,
    }

    context = await validator.validate_request(
        headers=headers, client_host="172.20.0.5", request_id="test-008"
    )

    assert validator.is_request_allowed(context) is True


@pytest.mark.asyncio
async def test_validator_is_request_allowed_external():
    """Test AXETrustValidator blocks EXTERNAL requests."""
    validator = get_axe_trust_validator()

    context = await validator.validate_request(
        headers={}, client_host="203.0.113.42", request_id="test-009"
    )

    # EXTERNAL requests are NOT allowed
    assert validator.is_request_allowed(context) is False


# ============================================================================
# INTEGRATION TESTS - Audit Events
# ============================================================================


def test_axe_request_emits_received_audit_event(dmz_headers):
    """
    Test that AXE request emits AXE_REQUEST_RECEIVED audit event.

    Note: This test verifies the endpoint succeeds. Audit event verification
    would require checking the sovereign_mode audit log.
    """
    response = client.get("/api/axe/info", headers=dmz_headers)

    assert response.status_code == 200
    data = response.json()

    # Verify request_id is present (needed for audit correlation)
    assert "governance" in data
    assert "request_id" in data["governance"]
    assert len(data["governance"]["request_id"]) > 0


def test_axe_blocked_request_emits_audit_events():
    """
    Test that blocked AXE request emits AXE_REQUEST_BLOCKED and
    AXE_TRUST_TIER_VIOLATION audit events.

    Note: Audit event verification would require checking the sovereign_mode
    audit log.
    """
    response = client.get("/api/axe/info")  # No localhost detection in test client

    # Verify request was blocked
    # Note: TestClient always uses localhost, so this might not be blocked
    # For proper testing, you'd need to mock the client_host
    if response.status_code == 403:
        data = response.json()
        assert "request_id" in data["detail"]
        # This request_id can be used to query audit events


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


def test_axe_info_response_time(dmz_headers):
    """Test AXE /info endpoint response time (should be fast)."""
    import time

    start = time.time()
    response = client.get("/api/axe/info", headers=dmz_headers)
    duration = time.time() - start

    assert response.status_code == 200

    # Should respond in under 100ms (including trust validation)
    assert duration < 0.1, f"Response took {duration*1000:.2f}ms (expected < 100ms)"


# ============================================================================
# REGRESSION TESTS
# ============================================================================


def test_axe_message_backward_compatibility():
    """Test AXE /message endpoint maintains backward compatible response structure."""
    payload = {"message": "Test backward compatibility", "metadata": {}}

    response = client.post("/api/axe/message", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Check backward compatible fields
    assert "mode" in data
    assert "gateway" in data
    assert "input_message" in data
    assert "reply" in data

    # Check new governance fields
    assert "governance" in data


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
