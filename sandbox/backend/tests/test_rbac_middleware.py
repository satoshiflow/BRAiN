"""
Unit tests for RBAC Middleware (Phase 3 Backend).

Tests authorization decorator and middleware.
"""

import pytest
from fastapi import HTTPException
from app.modules.neurorail.rbac.middleware import require_permission, get_current_user_placeholder
from app.modules.neurorail.rbac.schemas import Role, Permission, UserContext


# ============================================================================
# Tests: Decorator Functionality
# ============================================================================

@pytest.mark.asyncio
async def test_require_permission_allowed():
    """Test decorator allows authorized user."""

    @require_permission(Permission.READ_AUDIT)
    async def protected_endpoint(user: UserContext):
        return {"data": "success"}

    # Admin user has all permissions
    admin_user = UserContext.create(user_id="admin_1", role=Role.ADMIN)

    result = await protected_endpoint(user=admin_user)
    assert result["data"] == "success"


@pytest.mark.asyncio
async def test_require_permission_denied():
    """Test decorator denies unauthorized user."""

    @require_permission(Permission.MANAGE_SYSTEM)
    async def protected_endpoint(user: UserContext):
        return {"data": "success"}

    # Viewer does not have MANAGE_SYSTEM
    viewer_user = UserContext.create(user_id="viewer_1", role=Role.VIEWER)

    with pytest.raises(HTTPException) as exc_info:
        await protected_endpoint(user=viewer_user)

    assert exc_info.value.status_code == 403
    assert "Insufficient permissions" in exc_info.value.detail["error"]


@pytest.mark.asyncio
async def test_require_permission_multiple_permissions():
    """Test decorator with multiple required permissions."""

    @require_permission(Permission.READ_AUDIT, Permission.READ_METRICS, require_all=True)
    async def protected_endpoint(user: UserContext):
        return {"data": "success"}

    # Admin has all permissions
    admin_user = UserContext.create(user_id="admin_1", role=Role.ADMIN)
    result = await protected_endpoint(user=admin_user)
    assert result["data"] == "success"

    # Viewer has READ permissions but not WRITE
    viewer_user = UserContext.create(user_id="viewer_1", role=Role.VIEWER)
    result = await protected_endpoint(user=viewer_user)
    assert result["data"] == "success"


@pytest.mark.asyncio
async def test_require_permission_require_any():
    """Test decorator with require_all=False (any permission suffices)."""

    @require_permission(
        Permission.EXECUTE_JOB,
        Permission.MANAGE_SYSTEM,
        require_all=False
    )
    async def protected_endpoint(user: UserContext):
        return {"data": "success"}

    # Operator has EXECUTE_JOB but not MANAGE_SYSTEM
    operator_user = UserContext.create(user_id="op_1", role=Role.OPERATOR)

    result = await protected_endpoint(user=operator_user)
    assert result["data"] == "success"  # Has at least one permission


# ============================================================================
# Tests: Development Mode (No User)
# ============================================================================

@pytest.mark.asyncio
async def test_require_permission_dev_mode_no_user():
    """Test decorator allows access in dev mode when no user provided."""

    @require_permission(Permission.MANAGE_SYSTEM)
    async def protected_endpoint():
        return {"data": "dev_success"}

    # Call without user (development mode)
    result = await protected_endpoint()
    assert result["data"] == "dev_success"


# ============================================================================
# Tests: Sync Functions
# ============================================================================

def test_require_permission_sync_allowed():
    """Test decorator works with sync functions."""

    @require_permission(Permission.READ_AUDIT)
    def protected_endpoint(user: UserContext):
        return {"data": "sync_success"}

    admin_user = UserContext.create(user_id="admin_1", role=Role.ADMIN)

    result = protected_endpoint(user=admin_user)
    assert result["data"] == "sync_success"


def test_require_permission_sync_denied():
    """Test decorator denies sync functions for unauthorized users."""

    @require_permission(Permission.MANAGE_SYSTEM)
    def protected_endpoint(user: UserContext):
        return {"data": "sync_success"}

    viewer_user = UserContext.create(user_id="viewer_1", role=Role.VIEWER)

    with pytest.raises(HTTPException) as exc_info:
        protected_endpoint(user=viewer_user)

    assert exc_info.value.status_code == 403


# ============================================================================
# Tests: Error Details
# ============================================================================

@pytest.mark.asyncio
async def test_require_permission_error_details():
    """Test error response includes detailed permission info."""

    @require_permission(Permission.WRITE_GOVERNOR, Permission.WRITE_ENFORCEMENT)
    async def protected_endpoint(user: UserContext):
        return {"data": "success"}

    viewer_user = UserContext.create(user_id="viewer_1", role=Role.VIEWER)

    with pytest.raises(HTTPException) as exc_info:
        await protected_endpoint(user=viewer_user)

    error_detail = exc_info.value.detail

    assert "error" in error_detail
    assert "reason" in error_detail
    assert "required_permissions" in error_detail
    assert "user_permissions" in error_detail

    # Check required permissions listed
    assert "write:governor" in error_detail["required_permissions"]
    assert "write:enforcement" in error_detail["required_permissions"]


# ============================================================================
# Tests: Placeholder User
# ============================================================================

def test_get_current_user_placeholder():
    """Test placeholder user dependency returns dev admin."""
    user = get_current_user_placeholder()

    assert user.user_id == "dev_user"
    assert user.role == Role.ADMIN
    assert len(user.permissions) > 0


# ============================================================================
# Tests: Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_require_permission_no_permissions_required():
    """Test decorator with no permissions (edge case)."""

    @require_permission()  # No permissions specified
    async def protected_endpoint(user: UserContext):
        return {"data": "success"}

    viewer_user = UserContext.create(user_id="viewer_1", role=Role.VIEWER)

    # Should allow (no permissions required)
    result = await protected_endpoint(user=viewer_user)
    assert result["data"] == "success"


@pytest.mark.asyncio
async def test_require_permission_preserves_function_metadata():
    """Test decorator preserves original function metadata."""

    @require_permission(Permission.READ_AUDIT)
    async def my_endpoint(user: UserContext):
        """My endpoint docstring."""
        return {"data": "success"}

    # Check metadata preserved
    assert my_endpoint.__name__ == "my_endpoint"
    assert my_endpoint.__doc__ == "My endpoint docstring."
