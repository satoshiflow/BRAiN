"""
RBAC API (Phase 3 Backend).

FastAPI endpoints for RBAC management.
"""

from fastapi import APIRouter
from typing import List

from app.modules.neurorail.rbac import (
    get_rbac_service,
    Role,
    Permission,
    UserContext,
    require_permission,
)

router = APIRouter(prefix="/api/neurorail/v1/rbac", tags=["neurorail-rbac"])


@router.get("/info")
async def get_rbac_info():
    """
    Get RBAC system information.

    Returns role definitions, permissions, and statistics.

    Returns:
        RBAC system information
    """
    rbac = get_rbac_service()

    return {
        "name": "NeuroRail RBAC",
        "version": "1.0.0",
        "roles": [
            {
                "role": role.value,
                "permissions": [p.value for p in rbac.get_role_permissions(role)]
            }
            for role in Role
        ],
        "permissions": [p.value for p in Permission],
        "stats": rbac.get_stats(),
    }


@router.get("/roles")
async def list_roles():
    """
    List all available roles.

    Returns:
        List of roles with descriptions
    """
    return {
        "roles": [
            {
                "role": Role.ADMIN.value,
                "description": "Full access (read, write, delete, manage)",
                "level": 3,
            },
            {
                "role": Role.OPERATOR.value,
                "description": "Write access (read, write, execute)",
                "level": 2,
            },
            {
                "role": Role.VIEWER.value,
                "description": "Read-only access",
                "level": 1,
            },
        ]
    }


@router.get("/permissions")
async def list_permissions():
    """
    List all available permissions.

    Returns:
        List of permissions with categories
    """
    return {
        "permissions": [
            # Read permissions
            {
                "permission": Permission.READ_AUDIT.value,
                "category": "read",
                "description": "Read audit events",
            },
            {
                "permission": Permission.READ_METRICS.value,
                "category": "read",
                "description": "Read telemetry metrics",
            },
            {
                "permission": Permission.READ_LIFECYCLE.value,
                "category": "read",
                "description": "Read lifecycle state",
            },
            {
                "permission": Permission.READ_REFLEX.value,
                "category": "read",
                "description": "Read reflex system state",
            },
            {
                "permission": Permission.READ_GOVERNOR.value,
                "category": "read",
                "description": "Read governor decisions",
            },
            {
                "permission": Permission.READ_ENFORCEMENT.value,
                "category": "read",
                "description": "Read enforcement state",
            },

            # Write permissions
            {
                "permission": Permission.WRITE_GOVERNOR.value,
                "category": "write",
                "description": "Modify governor manifests",
            },
            {
                "permission": Permission.WRITE_ENFORCEMENT.value,
                "category": "write",
                "description": "Modify enforcement configurations",
            },
            {
                "permission": Permission.WRITE_REFLEX.value,
                "category": "write",
                "description": "Modify reflex configurations",
            },

            # Execute permissions
            {
                "permission": Permission.EXECUTE_JOB.value,
                "category": "execute",
                "description": "Execute jobs",
            },
            {
                "permission": Permission.EXECUTE_REFLEX_ACTION.value,
                "category": "execute",
                "description": "Execute reflex actions manually",
            },

            # Manage permissions
            {
                "permission": Permission.MANAGE_RBAC.value,
                "category": "manage",
                "description": "Manage users and roles",
            },
            {
                "permission": Permission.MANAGE_SYSTEM.value,
                "category": "manage",
                "description": "System configuration",
            },
        ]
    }


@router.get("/roles/{role}/permissions")
async def get_role_permissions(role: str):
    """
    Get permissions for a specific role.

    Args:
        role: Role name (admin, operator, viewer)

    Returns:
        List of permissions for the role
    """
    try:
        role_enum = Role(role)
    except ValueError:
        return {"error": f"Invalid role: {role}"}

    rbac = get_rbac_service()
    permissions = rbac.get_role_permissions(role_enum)

    return {
        "role": role_enum.value,
        "permissions": [p.value for p in permissions],
        "permission_count": len(permissions),
    }


@router.post("/check")
async def check_permission(
    user_id: str,
    role: str,
    permissions: List[str],
    require_all: bool = True,
):
    """
    Check if user has required permissions.

    Args:
        user_id: User identifier
        role: User role
        permissions: List of required permissions
        require_all: If True, user must have all permissions

    Returns:
        Authorization decision
    """
    try:
        role_enum = Role(role)
    except ValueError:
        return {"error": f"Invalid role: {role}"}

    # Parse permissions
    required_permissions = []
    for perm_str in permissions:
        try:
            required_permissions.append(Permission(perm_str))
        except ValueError:
            return {"error": f"Invalid permission: {perm_str}"}

    # Create user context
    user = UserContext.create(user_id=user_id, role=role_enum)

    # Authorize
    rbac = get_rbac_service()
    decision = rbac.authorize(user, required_permissions, require_all=require_all)

    return {
        "allowed": decision.allowed,
        "reason": decision.reason,
        "required_permissions": [p.value for p in decision.required_permissions],
        "user_permissions": [p.value for p in decision.user_permissions],
    }


@router.get("/stats")
@require_permission(Permission.MANAGE_RBAC)
async def get_rbac_stats():
    """
    Get RBAC authorization statistics.

    **Requires:** `manage:rbac` permission

    Returns:
        Authorization statistics
    """
    rbac = get_rbac_service()
    return rbac.get_stats()
