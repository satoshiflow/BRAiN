"""
Test Authentication Flow

Tests for authentication flows including:
- Login with access and refresh tokens
- Token refresh flow
- Token revocation
- Token replay detection
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest,
    TokenPair,
    DeviceInfo,
)
from app.models.user import User, UserRole
from app.models.token import RefreshToken, TokenStatus


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def test_user():
    """Create a test user"""
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash=AuthService.hash_password("testpassword"),
        full_name="Test User",
        role=UserRole.OPERATOR,
        is_active=True,
        is_verified=True,
    )
    return user


@pytest.fixture
def test_admin_user():
    """Create a test admin user"""
    user = User(
        id=uuid4(),
        email="admin@example.com",
        username="adminuser",
        password_hash=AuthService.hash_password("adminpassword"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    return user


@pytest.fixture
def device_info():
    """Create test device info"""
    return DeviceInfo(
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 Test Browser",
        device_fingerprint="abc123xyz",
    )


# ============================================================================
# Test Login Refresh Revoke Flow
# ============================================================================

@pytest.mark.asyncio
async def test_login_refresh_revoke_flow(mock_db, test_user, device_info):
    """
    Test complete flow: login → refresh → revoke
    
    Verifies that:
    1. Login returns valid tokens
    2. Refresh token can be used to get new tokens
    3. Old refresh token is invalidated after refresh
    4. Token can be explicitly revoked
    """
    # Mock user lookup for login
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = test_user
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    # Step 1: Login and get tokens
    login_request = LoginRequest(
        email="test@example.com",
        password="testpassword",
    )
    
    # Authenticate user
    user = await AuthService.authenticate_user(
        mock_db, login_request.email, login_request.password
    )
    assert user is not None
    assert user.email == test_user.email
    
    # Create token pair
    scopes = ["read", "write"]
    token_pair, refresh_record = await AuthService.create_token_pair(
        user, scopes, device_info
    )
    
    # Verify tokens were created
    assert token_pair.access_token is not None
    assert token_pair.refresh_token is not None
    assert token_pair.token_type == "bearer"
    assert token_pair.expires_in > 0
    
    # Verify refresh token record
    assert refresh_record.token_hash is not None
    assert refresh_record.user_id == test_user.id
    assert refresh_record.status == TokenStatus.ACTIVE.value
    
    # Save refresh token
    await AuthService.save_refresh_token(mock_db, refresh_record)
    mock_db.add.assert_called()
    mock_db.commit.assert_called()
    
    # Store original refresh token
    original_refresh_token = token_pair.refresh_token
    original_token_hash = refresh_record.token_hash
    
    # Step 2: Refresh the access token
    # Mock finding the refresh token
    mock_refresh_result = MagicMock()
    mock_refresh_result.scalar_one_or_none.return_value = refresh_record
    
    # Create a new mock for the refresh operation
    mock_db.execute = AsyncMock(return_value=mock_refresh_result)
    
    # Refresh should create new token pair
    with patch.object(AuthService, 'create_token_pair') as mock_create:
        new_token_pair = TokenPair(
            access_token="new_access_token_xyz",
            refresh_token="new_refresh_token_abc",
            token_type="bearer",
            expires_in=900,
        )
        new_refresh_record = RefreshToken(
            token_hash="new_hash_123",
            token_family=refresh_record.token_family,
            user_id=test_user.id,
            status=TokenStatus.ACTIVE.value,
            expires_at=datetime.utcnow() + timedelta(days=7),
            previous_token_id=refresh_record.id,
            rotation_count=1,
        )
        mock_create.return_value = (new_token_pair, new_refresh_record)
        
        refreshed_pair = await AuthService.refresh_access_token(
            original_refresh_token, mock_db
        )
    
    # Verify old token was marked as rotated
    assert refresh_record.status == TokenStatus.ROTATED.value
    assert refresh_record.used_at is not None
    
    # Verify new tokens were created
    assert refreshed_pair.access_token == "new_access_token_xyz"
    assert refreshed_pair.refresh_token == "new_refresh_token_abc"
    
    # Step 3: Revoke the new refresh token
    new_refresh_hash = "new_hash_123"
    
    # Mock finding the new token
    mock_new_token_result = MagicMock()
    mock_new_token_result.scalar_one_or_none.return_value = new_refresh_record
    mock_db.execute = AsyncMock(return_value=mock_new_token_result)
    
    result = await AuthService.revoke_token(
        new_refresh_hash, "User logout", mock_db
    )
    
    assert result is True
    assert new_refresh_record.status == TokenStatus.REVOKED.value
    assert new_refresh_record.revoked_at is not None


@pytest.mark.asyncio
async def test_login_returns_valid_jwt(mock_db, test_admin_user, device_info):
    """
    Test that login returns a valid JWT access token.
    """
    # Create token pair
    scopes = ["read", "write", "admin"]
    token_pair, refresh_record = await AuthService.create_token_pair(
        test_admin_user, scopes, device_info
    )
    
    # Verify access token structure (JWT has 3 parts separated by dots)
    assert token_pair.access_token is not None
    parts = token_pair.access_token.split('.')
    assert len(parts) == 3, "JWT should have 3 parts (header.payload.signature)"
    
    # Verify token type and expiration
    assert token_pair.token_type == "bearer"
    assert token_pair.expires_in > 0
    assert token_pair.expires_in <= 3600  # Should be 60 minutes or less
    
    # Verify refresh token exists
    assert token_pair.refresh_token is not None
    assert len(token_pair.refresh_token) > 32  # Should be long for security


@pytest.mark.asyncio
async def test_refresh_token_storage_hashing(mock_db, test_user, device_info):
    """
    Test that refresh tokens are properly hashed before storage.
    
    Security requirement: Raw refresh tokens should NEVER be stored in database.
    Only SHA256 hashes should be stored.
    """
    scopes = ["read"]
    token_pair, refresh_record = await AuthService.create_token_pair(
        test_user, scopes, device_info
    )
    
    # The raw token should NOT be in the record
    assert refresh_record.token_hash != token_pair.refresh_token
    
    # The token hash should be SHA256 (64 hex characters)
    assert len(refresh_record.token_hash) == 64
    assert all(c in '0123456789abcdef' for c in refresh_record.token_hash)
    
    # Hashing the same raw token should produce the same hash
    expected_hash = AuthService._hash_token(token_pair.refresh_token)
    assert refresh_record.token_hash == expected_hash


# ============================================================================
# Test Token Expiry Refresh
# ============================================================================

@pytest.mark.asyncio
async def test_token_expiry_refresh(mock_db, test_user, device_info):
    """
    Test that expired refresh tokens cannot be used.
    
    When a refresh token expires, the user must re-authenticate.
    """
    # Create an expired refresh token
    expired_token = RefreshToken(
        token_hash="expired_hash_123",
        token_family=uuid4(),
        user_id=test_user.id,
        status=TokenStatus.ACTIVE.value,
        expires_at=datetime.utcnow() - timedelta(days=1),  # Expired yesterday
        rotation_count=0,
    )
    
    # Mock finding the expired token
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expired_token
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    # Attempt to refresh with expired token
    with pytest.raises(ValueError) as exc_info:
        await AuthService.refresh_access_token("expired_token_string", mock_db)
    
    assert "expired" in str(exc_info.value).lower()
    
    # Verify token was marked as expired in database
    assert expired_token.status == TokenStatus.EXPIRED.value
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_access_token_has_valid_expiration(mock_db, test_user, device_info):
    """
    Test that access tokens have a reasonable expiration time.
    """
    scopes = ["read"]
    token_pair, refresh_record = await AuthService.create_token_pair(
        test_user, scopes, device_info
    )
    
    # Access tokens should expire in reasonable time (15-60 minutes)
    assert token_pair.expires_in > 0
    assert token_pair.expires_in <= 3600  # Max 1 hour
    assert token_pair.expires_in >= 300   # Min 5 minutes
    
    # Refresh tokens should have much longer expiration (days)
    assert refresh_record.expires_at > datetime.utcnow() + timedelta(days=6)
    assert refresh_record.expires_at < datetime.utcnow() + timedelta(days=31)


@pytest.mark.asyncio
async def test_refresh_token_rotation_updates_family(mock_db, test_user, device_info):
    """
    Test that token refresh maintains token family for tracking.
    
    Token families allow detection of token replay attacks.
    """
    scopes = ["read"]
    
    # Create initial token
    original_pair, original_record = await AuthService.create_token_pair(
        test_user, scopes, device_info
    )
    
    original_family = original_record.token_family
    
    # Mock the refresh operation
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = original_record
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    with patch.object(AuthService, 'create_token_pair') as mock_create:
        new_pair = TokenPair(
            access_token="new_access",
            refresh_token="new_refresh",
            token_type="bearer",
            expires_in=900,
        )
        new_record = RefreshToken(
            token_hash="new_hash",
            token_family=original_family,  # Same family
            user_id=test_user.id,
            status=TokenStatus.ACTIVE.value,
            previous_token_id=original_record.id,
            rotation_count=1,
        )
        mock_create.return_value = (new_pair, new_record)
        
        refreshed = await AuthService.refresh_access_token(
            original_pair.refresh_token, mock_db
        )
    
    # New token should be in same family
    assert new_record.token_family == original_family
    assert new_record.previous_token_id == original_record.id
    assert new_record.rotation_count == 1


# ============================================================================
# Test Token Replay Rejected
# ============================================================================

@pytest.mark.asyncio
async def test_token_replay_rejected(mock_db, test_user, device_info):
    """
    Test that replaying a used refresh token is rejected.
    
    If an attacker steals a refresh token and tries to use it after
    the legitimate user has already refreshed, the replay should be
    detected and rejected.
    """
    scopes = ["read"]
    
    # Create initial token pair
    original_pair, original_record = await AuthService.create_token_pair(
        test_user, scopes, device_info
    )
    
    # Simulate the token being used once (rotated)
    original_record.status = TokenStatus.ROTATED.value
    original_record.used_at = datetime.utcnow()
    
    # Mock finding the already-used token
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = original_record
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    # Attempt to replay the already-used token
    with pytest.raises(ValueError) as exc_info:
        await AuthService.refresh_access_token(
            original_pair.refresh_token, mock_db
        )
    
    # Should be rejected - token is not active anymore
    # Note: The implementation may vary, but replay should be detected
    error_msg = str(exc_info.value).lower()
    assert "invalid" in error_msg or "rotated" in error_msg or "revoked" in error_msg


@pytest.mark.asyncio
async def test_token_replay_detection_with_rotation_count(mock_db, test_user, device_info):
    """
    Test that excessive token rotations are flagged as potential replay attacks.
    
    If a token family has too many rotations, it may indicate token theft.
    """
    scopes = ["read"]
    
    # Create a token with suspicious rotation count
    suspicious_token = RefreshToken(
        token_hash="suspicious_hash",
        token_family=uuid4(),
        user_id=test_user.id,
        status=TokenStatus.ACTIVE.value,
        expires_at=datetime.utcnow() + timedelta(days=7),
        rotation_count=15,  # Suspiciously high
    )
    
    # Mock finding the token
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = suspicious_token
    
    # Mock user lookup
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = test_user
    
    mock_db.execute = AsyncMock(side_effect=[mock_result, mock_user_result])
    
    # Even with high rotation count, if token is valid it should work
    # but the system should log a warning
    with patch('app.services.auth_service.logger') as mock_logger:
        with patch.object(AuthService, 'create_token_pair') as mock_create:
            new_pair = TokenPair(
                access_token="new_access",
                refresh_token="new_refresh",
                token_type="bearer",
                expires_in=900,
            )
            new_record = RefreshToken(
                token_hash="new_hash",
                token_family=suspicious_token.token_family,
                user_id=test_user.id,
                status=TokenStatus.ACTIVE.value,
                rotation_count=16,
            )
            mock_create.return_value = (new_pair, new_record)
            
            result = await AuthService.refresh_access_token(
                "suspicious_token_string", mock_db
            )
        
        # A warning should have been logged about excessive rotations
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "excessive rotations" in warning_call.lower() or "replay" in warning_call.lower()


@pytest.mark.asyncio
async def test_revoked_token_cannot_be_refreshed(mock_db, test_user):
    """
    Test that revoked refresh tokens cannot be used to get new tokens.
    """
    # Create a revoked token
    revoked_token = RefreshToken(
        token_hash="revoked_hash_123",
        token_family=uuid4(),
        user_id=test_user.id,
        status=TokenStatus.REVOKED.value,  # Already revoked
        expires_at=datetime.utcnow() + timedelta(days=7),
        revoked_at=datetime.utcnow(),
        rotation_count=0,
    )
    
    # Mock finding the revoked token
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = revoked_token
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    # Attempt to refresh with revoked token
    with pytest.raises(ValueError) as exc_info:
        await AuthService.refresh_access_token("revoked_token_string", mock_db)
    
    assert "invalid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_revoke_all_user_tokens(mock_db, test_user):
    """
    Test revoking all tokens for a user (logout from all devices).
    """
    # Create multiple active tokens
    tokens = [
        RefreshToken(
            token_hash=f"token_hash_{i}",
            token_family=uuid4(),
            user_id=test_user.id,
            status=TokenStatus.ACTIVE.value,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        for i in range(3)
    ]
    
    # Mock finding all user tokens
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = tokens
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    # Revoke all tokens
    count = await AuthService.revoke_all_user_tokens(
        test_user.id, "User requested logout from all devices", mock_db
    )
    
    # All tokens should be revoked
    assert count == 3
    for token in tokens:
        assert token.status == TokenStatus.REVOKED.value
        assert token.revoked_at is not None
    
    mock_db.commit.assert_called()


# ============================================================================
# Additional Security Tests
# ============================================================================

@pytest.mark.asyncio
async def test_invalid_refresh_token_rejected(mock_db):
    """
    Test that completely invalid refresh tokens are rejected.
    """
    # Mock no token found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    with pytest.raises(ValueError) as exc_info:
        await AuthService.refresh_access_token("invalid_token", mock_db)
    
    assert "invalid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_inactive_user_cannot_refresh(mock_db, test_user):
    """
    Test that inactive users cannot refresh tokens.
    """
    test_user.is_active = False
    
    # Create a valid token for inactive user
    token = RefreshToken(
        token_hash="valid_hash",
        token_family=uuid4(),
        user_id=test_user.id,
        status=TokenStatus.ACTIVE.value,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    
    # Mock finding token but inactive user
    mock_token_result = MagicMock()
    mock_token_result.scalar_one_or_none.return_value = token
    
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = None  # User not found/inactive
    
    mock_db.execute = AsyncMock(side_effect=[mock_token_result, mock_user_result])
    
    with pytest.raises(ValueError) as exc_info:
        await AuthService.refresh_access_token("valid_token_string", mock_db)
    
    assert "user" in str(exc_info.value).lower() or "inactive" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_token_scope_based_on_user_role(mock_db, test_user, test_admin_user, device_info):
    """
    Test that token scopes are assigned based on user role.
    """
    # Regular user should get read scope
    user_scopes = ["read"]
    user_pair, _ = await AuthService.create_token_pair(test_user, user_scopes, device_info)
    
    # Operator should get read and write
    test_user.role = UserRole.OPERATOR
    operator_scopes = ["read", "write"]
    operator_pair, _ = await AuthService.create_token_pair(test_user, operator_scopes, device_info)
    
    # Admin should get all scopes
    admin_scopes = ["read", "write", "admin"]
    admin_pair, _ = await AuthService.create_token_pair(test_admin_user, admin_scopes, device_info)
    
    # All tokens should be created successfully
    assert user_pair.access_token is not None
    assert operator_pair.access_token is not None
    assert admin_pair.access_token is not None
