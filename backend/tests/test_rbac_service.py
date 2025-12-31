"""
Unit tests for RBAC Service (Phase 3 Backend).

Tests role-based authorization and permission checks.
"""

import pytest
from backend.app.modules.neurorail.rbac.service import RBACService
from backend.app.modules.neurorail.rbac.schemas import (
    Role,
    Permission,
    UserContext,
    ROLE_PERMISSIONS,
)


# ============================================================================
# Tests: Role Permissions
# ============================================================================

def test_rbac_admin_has_all_permissions():
    """Test ADMIN role has all permissions."""
    admin_permissions = ROLE_PERMISSIONS[Role.ADMIN]

    # Check has all permission types
    assert Permission.READ_AUDIT in admin_permissions
    assert Permission.WRITE_GOVERNOR in admin_permissions
    assert Permission.EXECUTE_JOB in admin_permissions
    assert Permission.MANAGE_RBAC in admin_permissions
    assert Permission.MANAGE_SYSTEM in admin_permissions


def test_rbac_operator_has_limited_permissions():
    """Test OPERATOR role has limited permissions."""
    operator_permissions = ROLE_PERMISSIONS[Role.OPERATOR]

    # Has read and execute
    assert Permission.READ_AUDIT in operator_permissions
    assert Permission.EXECUTE_JOB in operator_permissions

    # Does NOT have manage
    assert Permission.MANAGE_RBAC not in operator_permissions
    assert Permission.MANAGE_SYSTEM not in operator_permissions


def test_rbac_viewer_readonly():
    """Test VIEWER role is read-only."""
    viewer_permissions = ROLE_PERMISSIONS[Role.VIEWER]

    # Has read permissions
    assert Permission.READ_AUDIT in viewer_permissions
    assert Permission.READ_METRICS in viewer_permissions

    # Does NOT have write, execute, or manage
    assert Permission.WRITE_GOVERNOR not in viewer_permissions
    assert Permission.EXECUTE_JOB not in viewer_permissions
    assert Permission.MANAGE_RBAC not in viewer_permissions


# ============================================================================
# Tests: User Context
# ============================================================================

def test_user_context_create_admin():
    """Test creating admin user context."""
    user = UserContext.create(user_id="admin_123", role=Role.ADMIN)

    assert user.user_id == "admin_123"
    assert user.role == Role.ADMIN
    assert len(user.permissions) > 0
    assert Permission.MANAGE_SYSTEM in user.permissions


def test_user_context_create_operator():
    """Test creating operator user context."""
    user = UserContext.create(user_id="op_456", role=Role.OPERATOR)

    assert user.user_id == "op_456"
    assert user.role == Role.OPERATOR
    assert Permission.EXECUTE_JOB in user.permissions
    assert Permission.MANAGE_SYSTEM not in user.permissions


def test_user_context_has_permission():
    """Test has_permission check."""
    user = UserContext.create(user_id="user_1", role=Role.ADMIN)

    assert user.has_permission(Permission.MANAGE_SYSTEM) is True
    assert user.has_permission(Permission.READ_AUDIT) is True


def test_user_context_has_any_permission():
    """Test has_any_permission check."""
    user = UserContext.create(user_id="user_1", role=Role.VIEWER)

    # Has READ_AUDIT but not MANAGE_SYSTEM
    assert user.has_any_permission([Permission.READ_AUDIT, Permission.MANAGE_SYSTEM]) is True
    assert user.has_any_permission([Permission.MANAGE_SYSTEM, Permission.MANAGE_RBAC]) is False


def test_user_context_has_all_permissions():
    """Test has_all_permissions check."""
    admin = UserContext.create(user_id="admin_1", role=Role.ADMIN)
    viewer = UserContext.create(user_id="viewer_1", role=Role.VIEWER)

    # Admin has all
    assert admin.has_all_permissions([Permission.READ_AUDIT, Permission.MANAGE_SYSTEM]) is True

    # Viewer does not have MANAGE_SYSTEM
    assert viewer.has_all_permissions([Permission.READ_AUDIT, Permission.MANAGE_SYSTEM]) is False


# ============================================================================
# Tests: Authorization
# ============================================================================

def test_rbac_authorize_admin_allowed():
    """Test ADMIN authorized for all permissions."""
    rbac = RBACService()
    user = UserContext.create(user_id="admin_1", role=Role.ADMIN)

    decision = rbac.authorize(user, [Permission.MANAGE_SYSTEM])

    assert decision.allowed is True
    assert decision.reason == "User has all required permissions"


def test_rbac_authorize_viewer_denied_write():
    """Test VIEWER denied for write permissions."""
    rbac = RBACService()
    user = UserContext.create(user_id="viewer_1", role=Role.VIEWER)

    decision = rbac.authorize(user, [Permission.WRITE_GOVERNOR])

    assert decision.allowed is False
    assert decision.reason == "User missing required permissions"
    assert Permission.WRITE_GOVERNOR in decision.required_permissions
    assert Permission.WRITE_GOVERNOR not in decision.user_permissions


def test_rbac_authorize_require_all():
    """Test authorize with require_all=True."""
    rbac = RBACService()
    user = UserContext.create(user_id="op_1", role=Role.OPERATOR)

    # Operator has EXECUTE_JOB but not MANAGE_SYSTEM
    decision = rbac.authorize(
        user,
        [Permission.EXECUTE_JOB, Permission.MANAGE_SYSTEM],
        require_all=True
    )

    assert decision.allowed is False  # Missing MANAGE_SYSTEM


def test_rbac_authorize_require_any():
    """Test authorize with require_all=False."""
    rbac = RBACService()
    user = UserContext.create(user_id="op_1", role=Role.OPERATOR)

    # Operator has EXECUTE_JOB but not MANAGE_SYSTEM
    decision = rbac.authorize(
        user,
        [Permission.EXECUTE_JOB, Permission.MANAGE_SYSTEM],
        require_all=False  # Any permission suffices
    )

    assert decision.allowed is True  # Has EXECUTE_JOB


# ============================================================================
# Tests: Statistics
# ============================================================================

def test_rbac_stats_tracking():
    """Test RBAC statistics tracking."""
    rbac = RBACService()
    admin = UserContext.create(user_id="admin_1", role=Role.ADMIN)
    viewer = UserContext.create(user_id="viewer_1", role=Role.VIEWER)

    # Perform authorizations
    rbac.authorize(admin, [Permission.MANAGE_SYSTEM])  # Allowed
    rbac.authorize(viewer, [Permission.READ_AUDIT])    # Allowed
    rbac.authorize(viewer, [Permission.MANAGE_SYSTEM]) # Denied

    stats = rbac.get_stats()

    assert stats["authorization_count"] == 3
    assert stats["denied_count"] == 1
    assert stats["denial_rate"] == pytest.approx(1/3)


# ============================================================================
# Tests: Get Role Permissions
# ============================================================================

def test_rbac_get_role_permissions():
    """Test getting permissions for a role."""
    rbac = RBACService()

    admin_perms = rbac.get_role_permissions(Role.ADMIN)
    viewer_perms = rbac.get_role_permissions(Role.VIEWER)

    assert len(admin_perms) > len(viewer_perms)
    assert Permission.MANAGE_SYSTEM in admin_perms
    assert Permission.MANAGE_SYSTEM not in viewer_perms


# ============================================================================
# Tests: Edge Cases
# ============================================================================

def test_rbac_empty_required_permissions():
    """Test authorization with empty required permissions list."""
    rbac = RBACService()
    user = UserContext.create(user_id="user_1", role=Role.VIEWER)

    decision = rbac.authorize(user, [])

    # No permissions required = always allowed
    assert decision.allowed is True


def test_user_context_metadata():
    """Test user context with metadata."""
    user = UserContext.create(
        user_id="user_1",
        role=Role.ADMIN,
        metadata={"ip": "127.0.0.1", "session_id": "sess_123"}
    )

    assert user.metadata["ip"] == "127.0.0.1"
    assert user.metadata["session_id"] == "sess_123"
