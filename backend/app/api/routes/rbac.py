"""
RBAC (Role-Based Access Control) Management API.

Provides endpoints for managing roles, permissions, and role assignments:
- List roles and permissions
- Assign/revoke roles
- Check permissions
- Manage resource ownership

Security:
- Requires admin authentication for management operations
- All operations logged for audit trail
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from app.core.rbac import (
    RBACManager,
    get_rbac_manager,
    Role,
    Permission,
    RoleAssignment,
    PermissionCheck,
    SystemPermissions,
    SystemRoles,
)
from app.core.security import get_current_principal, require_role, Principal

router = APIRouter(prefix="/api/rbac", tags=["rbac"])


# ============================================================================
# Request/Response Models
# ============================================================================

class RoleAssignRequest(BaseModel):
    """Role assignment request."""
    principal_id: str
    role_id: str
    tenant_id: Optional[str] = None
    expires_in_days: Optional[int] = None


class RoleRevokeRequest(BaseModel):
    """Role revocation request."""
    principal_id: str
    role_id: str


class PermissionCheckRequest(BaseModel):
    """Permission check request."""
    principal_id: str
    permission: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None


class ResourceOwnershipRequest(BaseModel):
    """Resource ownership request."""
    resource_type: str
    resource_id: str
    owner_id: str
    tenant_id: Optional[str] = None


class PrincipalRolesResponse(BaseModel):
    """Principal roles response."""
    principal_id: str
    roles: List[Role]
    permissions: List[str]


class SystemPermissionsResponse(BaseModel):
    """System permissions response."""
    permissions: List[str]


class SystemRolesResponse(BaseModel):
    """System roles response."""
    roles: List[dict]


# ============================================================================
# Dependency: Require Admin
# ============================================================================

async def require_admin_role(principal: Principal = Depends(get_current_principal)):
    """
    Require admin or super_admin role for RBAC management.

    RBAC management is a privileged operation.
    """
    if not principal.has_any_role("admin", "super_admin"):
        raise HTTPException(
            status_code=403,
            detail="Admin role required for RBAC management"
        )
    return principal


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/roles", response_model=SystemRolesResponse)
async def list_system_roles(
    principal: Principal = Depends(require_admin_role)
):
    """
    List all system roles.

    Returns all predefined system roles with their permissions and hierarchy.

    **Returns:**
    - super_admin: Full system access
    - admin: Administrative access
    - moderator: Content management
    - user: Standard user
    - guest: Read-only access
    - service: Service account

    **Example:**
    ```
    GET /api/rbac/roles
    ```
    """
    return SystemRolesResponse(
        roles=SystemRoles.get_all_roles()
    )


@router.get("/permissions", response_model=SystemPermissionsResponse)
async def list_system_permissions(
    principal: Principal = Depends(require_admin_role)
):
    """
    List all system permissions.

    Returns all predefined system permissions organized by resource type.

    **Permissions Format:**
    - `{resource}:{action}` - e.g., "missions:read", "agents:create"
    - `{resource}:{action}:own` - e.g., "missions:update:own" (only own resources)
    - `{resource}:*` - e.g., "missions:*" (all actions on resource)
    - `*:*` - All permissions (super admin)

    **Example:**
    ```
    GET /api/rbac/permissions
    ```
    """
    return SystemPermissionsResponse(
        permissions=SystemPermissions.get_all_permissions()
    )


@router.post("/assign-role", response_model=RoleAssignment)
async def assign_role(
    request: RoleAssignRequest,
    rbac: RBACManager = Depends(get_rbac_manager),
    principal: Principal = Depends(require_admin_role)
):
    """
    Assign role to principal (user/service).

    **Request Body:**
    ```json
    {
        "principal_id": "user_123",
        "role_id": "moderator",
        "tenant_id": null,
        "expires_in_days": 90
    }
    ```

    **Returns:**
    Role assignment details.

    **Example:**
    ```
    POST /api/rbac/assign-role
    ```

    **Note:** Role hierarchy is automatically applied. Assigning "admin" also
    grants all permissions from "moderator", "user", and "guest".
    """
    try:
        # Calculate expiration
        expires_at = None
        if request.expires_in_days:
            from datetime import timedelta
            expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

        # Assign role
        assignment = await rbac.assign_role(
            principal_id=request.principal_id,
            role_id=request.role_id,
            granted_by=principal.principal_id,
            tenant_id=request.tenant_id,
            expires_at=expires_at
        )

        return assignment

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to assign role: {str(e)}"
        )


@router.post("/revoke-role")
async def revoke_role(
    request: RoleRevokeRequest,
    rbac: RBACManager = Depends(get_rbac_manager),
    principal: Principal = Depends(require_admin_role)
):
    """
    Revoke role from principal.

    **Request Body:**
    ```json
    {
        "principal_id": "user_123",
        "role_id": "moderator"
    }
    ```

    **Returns:**
    Success message.

    **Example:**
    ```
    POST /api/rbac/revoke-role
    ```
    """
    try:
        success = await rbac.revoke_role(
            principal_id=request.principal_id,
            role_id=request.role_id,
            revoked_by=principal.principal_id
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Role assignment not found: {request.role_id} for {request.principal_id}"
            )

        return {
            "success": True,
            "message": f"Revoked role '{request.role_id}' from principal '{request.principal_id}'"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke role: {str(e)}"
        )


@router.get("/principals/{principal_id}/roles", response_model=PrincipalRolesResponse)
async def get_principal_roles(
    principal_id: str,
    rbac: RBACManager = Depends(get_rbac_manager),
    principal: Principal = Depends(require_admin_role)
):
    """
    Get all roles and permissions for a principal.

    **Path Parameters:**
    - principal_id: User or service ID

    **Returns:**
    - All assigned roles (including inherited via hierarchy)
    - All permissions from all roles
    - Expiration dates for temporary roles

    **Example:**
    ```
    GET /api/rbac/principals/user_123/roles
    ```
    """
    try:
        # Get roles (including hierarchy)
        roles = await rbac.get_principal_roles(principal_id)

        # Get all permissions
        permissions = await rbac.get_principal_permissions(principal_id)

        return PrincipalRolesResponse(
            principal_id=principal_id,
            roles=roles,
            permissions=list(permissions)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get principal roles: {str(e)}"
        )


@router.post("/check-permission", response_model=PermissionCheck)
async def check_permission(
    request: PermissionCheckRequest,
    rbac: RBACManager = Depends(get_rbac_manager),
    principal: Principal = Depends(require_admin_role)
):
    """
    Check if principal has specific permission.

    **Request Body:**
    ```json
    {
        "principal_id": "user_123",
        "permission": "missions:update",
        "resource_type": "mission",
        "resource_id": "mission_456"
    }
    ```

    **Returns:**
    Permission check result with:
    - allowed: True/False
    - reason: Explanation
    - matched_permission: Which permission granted access (if allowed)
    - matched_role: Which role granted access (if allowed)

    **Example:**
    ```
    POST /api/rbac/check-permission
    ```

    **Permission Scopes:**
    - `missions:update` - Can update all missions
    - `missions:update:own` - Can only update own missions
    - If permission is scoped to ":own", ownership is verified
    """
    try:
        result = await rbac.check_permission(
            principal_id=request.principal_id,
            permission=request.permission,
            resource_id=request.resource_id,
            resource_type=request.resource_type
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check permission: {str(e)}"
        )


@router.post("/set-resource-owner")
async def set_resource_owner(
    request: ResourceOwnershipRequest,
    rbac: RBACManager = Depends(get_rbac_manager),
    principal: Principal = Depends(require_admin_role)
):
    """
    Set resource ownership.

    Used for tracking which principal owns a resource (e.g., mission, agent).
    Required for permission scopes like "missions:update:own".

    **Request Body:**
    ```json
    {
        "resource_type": "mission",
        "resource_id": "mission_123",
        "owner_id": "user_456",
        "tenant_id": null
    }
    ```

    **Returns:**
    Success message.

    **Example:**
    ```
    POST /api/rbac/set-resource-owner
    ```

    **Usage:**
    Call this endpoint whenever a resource is created:
    ```python
    # After creating a mission
    await rbac.set_resource_owner(
        resource_type="mission",
        resource_id=mission.id,
        owner_id=user.id
    )
    ```
    """
    try:
        await rbac.set_resource_owner(
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            owner_id=request.owner_id,
            tenant_id=request.tenant_id
        )

        return {
            "success": True,
            "message": f"Set owner of {request.resource_type}:{request.resource_id} to {request.owner_id}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set resource owner: {str(e)}"
        )


@router.get("/resource-owner/{resource_type}/{resource_id}")
async def get_resource_owner(
    resource_type: str,
    resource_id: str,
    rbac: RBACManager = Depends(get_rbac_manager),
    principal: Principal = Depends(require_admin_role)
):
    """
    Get resource owner.

    **Path Parameters:**
    - resource_type: Resource type (e.g., "mission", "agent")
    - resource_id: Resource ID

    **Returns:**
    Owner principal ID, or null if not set.

    **Example:**
    ```
    GET /api/rbac/resource-owner/mission/mission_123
    ```
    """
    try:
        owner_id = await rbac.get_resource_owner(
            resource_type=resource_type,
            resource_id=resource_id
        )

        return {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "owner_id": owner_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get resource owner: {str(e)}"
        )


@router.get("/info")
async def get_rbac_info():
    """
    Get RBAC system information.

    **Returns:**
    System information including:
    - Total system roles
    - Total system permissions
    - Role hierarchy overview

    **Example:**
    ```
    GET /api/rbac/info
    ```

    **Public endpoint** - no authentication required.
    """
    return {
        "name": "BRAiN RBAC System",
        "version": "1.0.0",
        "description": "Enterprise-grade Role-Based Access Control",
        "features": [
            "Granular permissions (resource:action format)",
            "Role hierarchy (inheritance)",
            "Scope-based permissions (:own suffix)",
            "Resource ownership tracking",
            "Multi-tenancy support",
            "Permission caching (Redis)",
            "Audit logging integration"
        ],
        "system_roles": len(SystemRoles.get_all_roles()),
        "system_permissions": len(SystemPermissions.get_all_permissions()),
        "role_hierarchy": [
            "Super Admin (1000)",
            "Admin (900)",
            "Moderator (800)",
            "Service (600)",
            "User (500)",
            "Guest (100)"
        ],
        "permission_format": "{resource}:{action}[:{scope}]",
        "examples": {
            "exact": "missions:read",
            "wildcard_action": "missions:*",
            "wildcard_resource": "*:read",
            "full_wildcard": "*:*",
            "scoped": "missions:update:own"
        }
    }
