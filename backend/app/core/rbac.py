"""
Enhanced Role-Based Access Control (RBAC) System for BRAiN Core.

Provides enterprise-grade authorization with:
- Granular permissions (not just roles)
- Role hierarchy (admin > moderator > user)
- Resource-level permissions (can edit own vs. all)
- Permission inheritance
- Dynamic permission checks

Features:
- Multi-tenancy support
- Resource ownership tracking
- Permission caching (Redis)
- Audit logging integration
- Flexible permission model

Usage:
    from app.core.rbac import rbac, Permission, check_permission

    # Check permission
    has_permission = await rbac.check_permission(
        principal_id="user_123",
        permission="missions:update",
        resource_id="mission_456"
    )

    # Decorator for endpoint protection
    @require_permission("missions:delete")
    async def delete_mission(mission_id: str):
        # Only users with missions:delete permission can access
        pass
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta

import redis.asyncio as redis
from pydantic import BaseModel, Field
from loguru import logger


# ============================================================================
# Models
# ============================================================================

class Permission(BaseModel):
    """Permission model."""
    id: str
    name: str
    description: str
    resource_type: Optional[str] = None  # e.g., "mission", "agent", "*"
    action: str  # e.g., "read", "write", "delete", "*"
    scope: str = "all"  # "own", "tenant", "all"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Role(BaseModel):
    """Role model with permission assignments."""
    id: str
    name: str
    description: str
    permissions: List[str] = Field(default_factory=list)  # Permission IDs
    parent_role: Optional[str] = None  # For hierarchy
    priority: int = 0  # Higher priority = more powerful
    is_system: bool = False  # System roles cannot be deleted
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RoleAssignment(BaseModel):
    """Role assignment to a principal (user/service)."""
    principal_id: str
    role_id: str
    tenant_id: Optional[str] = None
    granted_by: str
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class ResourceOwnership(BaseModel):
    """Resource ownership tracking."""
    resource_type: str  # e.g., "mission", "agent"
    resource_id: str
    owner_id: str
    tenant_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PermissionCheck(BaseModel):
    """Permission check result."""
    allowed: bool
    reason: str
    matched_permission: Optional[str] = None
    matched_role: Optional[str] = None
    principal_id: str
    permission: str
    resource_id: Optional[str] = None


# ============================================================================
# System Permissions
# ============================================================================

class SystemPermissions:
    """Predefined system permissions."""

    # Missions
    MISSIONS_READ = "missions:read"
    MISSIONS_READ_OWN = "missions:read:own"
    MISSIONS_CREATE = "missions:create"
    MISSIONS_UPDATE = "missions:update"
    MISSIONS_UPDATE_OWN = "missions:update:own"
    MISSIONS_DELETE = "missions:delete"
    MISSIONS_DELETE_OWN = "missions:delete:own"
    MISSIONS_ALL = "missions:*"

    # Agents
    AGENTS_READ = "agents:read"
    AGENTS_CREATE = "agents:create"
    AGENTS_UPDATE = "agents:update"
    AGENTS_DELETE = "agents:delete"
    AGENTS_EXECUTE = "agents:execute"
    AGENTS_ALL = "agents:*"

    # Users
    USERS_READ = "users:read"
    USERS_READ_OWN = "users:read:own"
    USERS_UPDATE = "users:update"
    USERS_UPDATE_OWN = "users:update:own"
    USERS_DELETE = "users:delete"
    USERS_ALL = "users:*"

    # Roles & Permissions
    ROLES_READ = "roles:read"
    ROLES_CREATE = "roles:create"
    ROLES_UPDATE = "roles:update"
    ROLES_DELETE = "roles:delete"
    ROLES_ASSIGN = "roles:assign"
    ROLES_ALL = "roles:*"

    # API Keys
    API_KEYS_READ = "api_keys:read"
    API_KEYS_CREATE = "api_keys:create"
    API_KEYS_REVOKE = "api_keys:revoke"
    API_KEYS_ALL = "api_keys:*"

    # Audit Logs
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    AUDIT_DELETE = "audit:delete"
    AUDIT_ALL = "audit:*"

    # System
    SYSTEM_READ = "system:read"
    SYSTEM_CONFIGURE = "system:configure"
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_ALL = "system:*"

    # Wildcard
    ALL = "*:*"

    @classmethod
    def get_all_permissions(cls) -> List[str]:
        """Get list of all system permissions."""
        return [
            value for name, value in vars(cls).items()
            if not name.startswith("_") and isinstance(value, str)
        ]


# ============================================================================
# System Roles
# ============================================================================

class SystemRoles:
    """Predefined system roles with hierarchical permissions."""

    # Super Admin (highest privilege)
    SUPER_ADMIN = {
        "id": "super_admin",
        "name": "Super Admin",
        "description": "Full system access (all permissions)",
        "permissions": [SystemPermissions.ALL],
        "priority": 1000,
        "is_system": True,
    }

    # Admin
    ADMIN = {
        "id": "admin",
        "name": "Administrator",
        "description": "Administrative access to most resources",
        "permissions": [
            SystemPermissions.MISSIONS_ALL,
            SystemPermissions.AGENTS_ALL,
            SystemPermissions.USERS_READ,
            SystemPermissions.USERS_UPDATE,
            SystemPermissions.ROLES_READ,
            SystemPermissions.ROLES_ASSIGN,
            SystemPermissions.API_KEYS_ALL,
            SystemPermissions.AUDIT_READ,
            SystemPermissions.SYSTEM_READ,
        ],
        "parent_role": "super_admin",
        "priority": 900,
        "is_system": True,
    }

    # Moderator
    MODERATOR = {
        "id": "moderator",
        "name": "Moderator",
        "description": "Can manage content and users",
        "permissions": [
            SystemPermissions.MISSIONS_READ,
            SystemPermissions.MISSIONS_UPDATE,
            SystemPermissions.MISSIONS_DELETE,
            SystemPermissions.AGENTS_READ,
            SystemPermissions.AGENTS_EXECUTE,
            SystemPermissions.USERS_READ,
            SystemPermissions.USERS_UPDATE_OWN,
        ],
        "parent_role": "admin",
        "priority": 800,
        "is_system": True,
    }

    # User (standard user)
    USER = {
        "id": "user",
        "name": "User",
        "description": "Standard user with basic permissions",
        "permissions": [
            SystemPermissions.MISSIONS_READ_OWN,
            SystemPermissions.MISSIONS_CREATE,
            SystemPermissions.MISSIONS_UPDATE_OWN,
            SystemPermissions.MISSIONS_DELETE_OWN,
            SystemPermissions.AGENTS_READ,
            SystemPermissions.AGENTS_EXECUTE,
            SystemPermissions.USERS_READ_OWN,
            SystemPermissions.USERS_UPDATE_OWN,
        ],
        "parent_role": "moderator",
        "priority": 500,
        "is_system": True,
    }

    # Guest (read-only)
    GUEST = {
        "id": "guest",
        "name": "Guest",
        "description": "Read-only access",
        "permissions": [
            SystemPermissions.MISSIONS_READ_OWN,
            SystemPermissions.AGENTS_READ,
            SystemPermissions.USERS_READ_OWN,
        ],
        "parent_role": "user",
        "priority": 100,
        "is_system": True,
    }

    # Service Account
    SERVICE = {
        "id": "service",
        "name": "Service Account",
        "description": "For automated services and integrations",
        "permissions": [
            SystemPermissions.MISSIONS_CREATE,
            SystemPermissions.MISSIONS_READ,
            SystemPermissions.AGENTS_EXECUTE,
        ],
        "priority": 600,
        "is_system": True,
    }

    @classmethod
    def get_all_roles(cls) -> List[Dict[str, Any]]:
        """Get list of all system roles."""
        return [
            value for name, value in vars(cls).items()
            if not name.startswith("_") and isinstance(value, dict)
        ]


# ============================================================================
# RBAC Manager
# ============================================================================

class RBACManager:
    """
    Role-Based Access Control manager.

    Features:
    - Granular permission checks
    - Role hierarchy (inheritance)
    - Resource ownership validation
    - Permission caching (Redis)
    - Audit logging integration
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize RBAC manager.

        Args:
            redis_client: Async Redis client for caching
        """
        self._redis: Optional[redis.Redis] = redis_client
        self._initialized = False

        # In-memory storage (for development)
        # In production, use PostgreSQL or similar
        self._roles: Dict[str, Role] = {}
        self._permissions: Dict[str, Permission] = {}
        self._role_assignments: Dict[str, List[RoleAssignment]] = {}  # {principal_id: [assignments]}
        self._resource_ownership: Dict[str, ResourceOwnership] = {}  # {resource_type:resource_id: ownership}

    async def _ensure_initialized(self):
        """Lazy initialization."""
        if not self._initialized:
            if self._redis is None:
                from app.core.redis_client import get_redis
                self._redis = await get_redis()

            # Initialize system roles and permissions
            await self._initialize_system_roles()
            self._initialized = True

    async def _initialize_system_roles(self):
        """Initialize system roles and permissions."""
        # Create system roles
        for role_data in SystemRoles.get_all_roles():
            role = Role(**role_data)
            self._roles[role.id] = role
            logger.debug(f"Initialized system role: {role.name} (priority: {role.priority})")

        logger.info(f"Initialized {len(self._roles)} system roles")

    def _make_cache_key(self, key_type: str, identifier: str) -> str:
        """Generate Redis cache key."""
        return f"brain:rbac:{key_type}:{identifier}"

    async def assign_role(
        self,
        principal_id: str,
        role_id: str,
        granted_by: str,
        tenant_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> RoleAssignment:
        """
        Assign role to principal (user/service).

        Args:
            principal_id: User/service ID
            role_id: Role ID to assign
            granted_by: Principal ID who granted this role
            tenant_id: Optional tenant ID (multi-tenancy)
            expires_at: Optional expiration date

        Returns:
            Role assignment

        Raises:
            ValueError: If role doesn't exist
        """
        await self._ensure_initialized()

        # Validate role exists
        if role_id not in self._roles:
            raise ValueError(f"Role not found: {role_id}")

        # Create assignment
        assignment = RoleAssignment(
            principal_id=principal_id,
            role_id=role_id,
            tenant_id=tenant_id,
            granted_by=granted_by,
            expires_at=expires_at
        )

        # Store assignment
        if principal_id not in self._role_assignments:
            self._role_assignments[principal_id] = []
        self._role_assignments[principal_id].append(assignment)

        # Invalidate permission cache
        cache_key = self._make_cache_key("permissions", principal_id)
        await self._redis.delete(cache_key)

        # Log assignment (audit)
        try:
            from app.core.audit import audit_log, AuditAction
            await audit_log.log(
                action=AuditAction.ROLE_ASSIGN,
                user_id=granted_by,
                resource_type="role",
                resource_id=role_id,
                metadata={
                    "principal_id": principal_id,
                    "role_id": role_id,
                    "tenant_id": tenant_id,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log role assignment: {e}")

        logger.info(f"Assigned role '{role_id}' to principal '{principal_id}'")
        return assignment

    async def revoke_role(
        self,
        principal_id: str,
        role_id: str,
        revoked_by: str
    ) -> bool:
        """
        Revoke role from principal.

        Args:
            principal_id: User/service ID
            role_id: Role ID to revoke
            revoked_by: Principal ID who revoked this role

        Returns:
            True if role was revoked, False if not found
        """
        await self._ensure_initialized()

        if principal_id not in self._role_assignments:
            return False

        # Find and remove assignment
        assignments = self._role_assignments[principal_id]
        for i, assignment in enumerate(assignments):
            if assignment.role_id == role_id:
                assignments.pop(i)

                # Invalidate cache
                cache_key = self._make_cache_key("permissions", principal_id)
                await self._redis.delete(cache_key)

                # Log revocation (audit)
                try:
                    from app.core.audit import audit_log, AuditAction
                    await audit_log.log(
                        action=AuditAction.ROLE_REVOKE,
                        user_id=revoked_by,
                        resource_type="role",
                        resource_id=role_id,
                        metadata={
                            "principal_id": principal_id,
                            "role_id": role_id,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log role revocation: {e}")

                logger.info(f"Revoked role '{role_id}' from principal '{principal_id}'")
                return True

        return False

    async def get_principal_roles(self, principal_id: str) -> List[Role]:
        """
        Get all roles assigned to principal.

        Args:
            principal_id: User/service ID

        Returns:
            List of roles (including inherited via hierarchy)
        """
        await self._ensure_initialized()

        # Get direct assignments
        assignments = self._role_assignments.get(principal_id, [])

        # Filter expired assignments
        now = datetime.utcnow()
        active_assignments = [
            a for a in assignments
            if a.expires_at is None or a.expires_at > now
        ]

        # Get roles (including parent roles via hierarchy)
        roles = set()
        for assignment in active_assignments:
            role = self._roles.get(assignment.role_id)
            if role:
                roles.add(role)

                # Add parent roles (hierarchy)
                current_role = role
                while current_role.parent_role:
                    parent_role = self._roles.get(current_role.parent_role)
                    if parent_role:
                        roles.add(parent_role)
                        current_role = parent_role
                    else:
                        break

        return list(roles)

    async def get_principal_permissions(self, principal_id: str) -> Set[str]:
        """
        Get all permissions for principal (from all assigned roles).

        Includes permission expansion and wildcards.

        Args:
            principal_id: User/service ID

        Returns:
            Set of permission strings
        """
        await self._ensure_initialized()

        # Check cache
        cache_key = self._make_cache_key("permissions", principal_id)
        cached = await self._redis.get(cache_key)
        if cached:
            return set(json.loads(cached))

        # Get all roles
        roles = await self.get_principal_roles(principal_id)

        # Collect permissions from all roles
        permissions = set()
        for role in roles:
            permissions.update(role.permissions)

        # Cache for 5 minutes
        await self._redis.setex(
            cache_key,
            300,
            json.dumps(list(permissions))
        )

        return permissions

    def _permission_matches(
        self,
        required: str,
        granted: str,
        resource_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        principal_id: Optional[str] = None
    ) -> bool:
        """
        Check if granted permission matches required permission.

        Supports:
        - Exact match: "missions:read" == "missions:read"
        - Wildcard resource: "missions:*" grants "missions:read", "missions:update", etc.
        - Wildcard action: "*:read" grants "missions:read", "agents:read", etc.
        - Full wildcard: "*:*" grants everything
        - Scope-based: "missions:update:own" only grants if principal owns resource

        Args:
            required: Required permission (e.g., "missions:update")
            granted: Granted permission (e.g., "missions:*" or "missions:update:own")
            resource_id: Optional resource ID (for ownership check)
            owner_id: Optional resource owner ID
            principal_id: Principal requesting permission

        Returns:
            True if permission matches
        """
        # Full wildcard
        if granted == "*:*":
            return True

        # Parse permission strings
        req_parts = required.split(":")
        grant_parts = granted.split(":")

        if len(req_parts) < 2 or len(grant_parts) < 2:
            return False

        req_resource, req_action = req_parts[0], req_parts[1]
        grant_resource, grant_action = grant_parts[0], grant_parts[1]

        # Check scope (own vs. all)
        scope = "all"  # default
        if len(grant_parts) >= 3:
            scope = grant_parts[2]

        # If scope is "own", verify ownership
        if scope == "own":
            if not resource_id or not owner_id or not principal_id:
                # Can't verify ownership without context
                return False

            if owner_id != principal_id:
                # Principal doesn't own this resource
                return False

        # Check resource match
        resource_match = (
            grant_resource == req_resource or
            grant_resource == "*"
        )

        # Check action match
        action_match = (
            grant_action == req_action or
            grant_action == "*"
        )

        return resource_match and action_match

    async def check_permission(
        self,
        principal_id: str,
        permission: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> PermissionCheck:
        """
        Check if principal has permission.

        Args:
            principal_id: User/service ID
            permission: Required permission (e.g., "missions:update")
            resource_id: Optional resource ID (for ownership check)
            resource_type: Optional resource type (for ownership lookup)

        Returns:
            Permission check result

        Example:
            result = await rbac.check_permission(
                principal_id="user_123",
                permission="missions:update",
                resource_id="mission_456",
                resource_type="mission"
            )

            if result.allowed:
                # Proceed with action
            else:
                # Deny access
                raise PermissionError(result.reason)
        """
        await self._ensure_initialized()

        # Get all principal permissions
        granted_permissions = await self.get_principal_permissions(principal_id)

        # Get resource owner (if resource specified)
        owner_id = None
        if resource_id and resource_type:
            ownership_key = f"{resource_type}:{resource_id}"
            ownership = self._resource_ownership.get(ownership_key)
            if ownership:
                owner_id = ownership.owner_id

        # Check each granted permission
        for granted in granted_permissions:
            if self._permission_matches(
                required=permission,
                granted=granted,
                resource_id=resource_id,
                owner_id=owner_id,
                principal_id=principal_id
            ):
                return PermissionCheck(
                    allowed=True,
                    reason="Permission granted",
                    matched_permission=granted,
                    principal_id=principal_id,
                    permission=permission,
                    resource_id=resource_id
                )

        # Permission denied
        return PermissionCheck(
            allowed=False,
            reason="Permission denied: insufficient privileges",
            principal_id=principal_id,
            permission=permission,
            resource_id=resource_id
        )

    async def set_resource_owner(
        self,
        resource_type: str,
        resource_id: str,
        owner_id: str,
        tenant_id: Optional[str] = None
    ):
        """
        Set resource ownership.

        Args:
            resource_type: Resource type (e.g., "mission", "agent")
            resource_id: Resource ID
            owner_id: Principal ID who owns this resource
            tenant_id: Optional tenant ID
        """
        ownership = ResourceOwnership(
            resource_type=resource_type,
            resource_id=resource_id,
            owner_id=owner_id,
            tenant_id=tenant_id
        )

        ownership_key = f"{resource_type}:{resource_id}"
        self._resource_ownership[ownership_key] = ownership

        logger.debug(f"Set owner of {resource_type}:{resource_id} to {owner_id}")

    async def get_resource_owner(
        self,
        resource_type: str,
        resource_id: str
    ) -> Optional[str]:
        """
        Get resource owner.

        Args:
            resource_type: Resource type
            resource_id: Resource ID

        Returns:
            Owner principal ID, or None if not found
        """
        ownership_key = f"{resource_type}:{resource_id}"
        ownership = self._resource_ownership.get(ownership_key)
        return ownership.owner_id if ownership else None


# ============================================================================
# Global RBAC Manager
# ============================================================================

_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Get global RBAC manager instance."""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


# Convenience global instance
rbac = get_rbac_manager()
