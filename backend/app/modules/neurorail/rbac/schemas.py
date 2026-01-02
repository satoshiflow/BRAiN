"""
RBAC Schemas (Phase 3 Backend).

Data structures for Role-Based Access Control.
"""

from enum import Enum
from typing import List, Optional
from dataclasses import dataclass


class Role(str, Enum):
    """User roles with hierarchical permissions."""

    ADMIN = "admin"          # Full access (read, write, delete, manage)
    OPERATOR = "operator"    # Write access (read, write, execute)
    VIEWER = "viewer"        # Read-only access


class Permission(str, Enum):
    """Granular permissions for RBAC."""

    # Read permissions
    READ_AUDIT = "read:audit"
    READ_METRICS = "read:metrics"
    READ_LIFECYCLE = "read:lifecycle"
    READ_REFLEX = "read:reflex"
    READ_GOVERNOR = "read:governor"
    READ_ENFORCEMENT = "read:enforcement"

    # Write permissions
    WRITE_GOVERNOR = "write:governor"           # Modify governor manifests
    WRITE_ENFORCEMENT = "write:enforcement"     # Modify enforcement configs
    WRITE_REFLEX = "write:reflex"               # Modify reflex configs

    # Execute permissions
    EXECUTE_JOB = "execute:job"                 # Execute jobs
    EXECUTE_REFLEX_ACTION = "execute:reflex"    # Execute reflex actions manually

    # Management permissions
    MANAGE_RBAC = "manage:rbac"                 # Manage users and roles
    MANAGE_SYSTEM = "manage:system"             # System configuration


# Role-to-Permission mapping
ROLE_PERMISSIONS: dict[Role, List[Permission]] = {
    Role.ADMIN: [
        # All permissions
        Permission.READ_AUDIT,
        Permission.READ_METRICS,
        Permission.READ_LIFECYCLE,
        Permission.READ_REFLEX,
        Permission.READ_GOVERNOR,
        Permission.READ_ENFORCEMENT,
        Permission.WRITE_GOVERNOR,
        Permission.WRITE_ENFORCEMENT,
        Permission.WRITE_REFLEX,
        Permission.EXECUTE_JOB,
        Permission.EXECUTE_REFLEX_ACTION,
        Permission.MANAGE_RBAC,
        Permission.MANAGE_SYSTEM,
    ],
    Role.OPERATOR: [
        # Read all
        Permission.READ_AUDIT,
        Permission.READ_METRICS,
        Permission.READ_LIFECYCLE,
        Permission.READ_REFLEX,
        Permission.READ_GOVERNOR,
        Permission.READ_ENFORCEMENT,
        # Write limited
        Permission.WRITE_ENFORCEMENT,
        Permission.WRITE_REFLEX,
        # Execute
        Permission.EXECUTE_JOB,
        Permission.EXECUTE_REFLEX_ACTION,
    ],
    Role.VIEWER: [
        # Read-only
        Permission.READ_AUDIT,
        Permission.READ_METRICS,
        Permission.READ_LIFECYCLE,
        Permission.READ_REFLEX,
        Permission.READ_GOVERNOR,
        Permission.READ_ENFORCEMENT,
    ],
}


@dataclass
class UserContext:
    """
    User context for authorization.

    Attributes:
        user_id: User identifier
        role: User role
        permissions: List of granted permissions (derived from role)
        metadata: Optional metadata (e.g., IP, session ID)
    """

    user_id: str
    role: Role
    permissions: List[Permission]
    metadata: Optional[dict] = None

    @classmethod
    def create(cls, user_id: str, role: Role, metadata: Optional[dict] = None) -> "UserContext":
        """
        Create user context from role.

        Args:
            user_id: User identifier
            role: User role
            metadata: Optional metadata

        Returns:
            UserContext with permissions derived from role
        """
        permissions = ROLE_PERMISSIONS.get(role, [])
        return cls(
            user_id=user_id,
            role=role,
            permissions=permissions,
            metadata=metadata or {}
        )

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions

    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(p in self.permissions for p in permissions)

    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if user has all of the specified permissions."""
        return all(p in self.permissions for p in permissions)


@dataclass
class RBACDecision:
    """
    RBAC authorization decision.

    Attributes:
        allowed: Whether access is granted
        reason: Reason for decision
        required_permissions: List of required permissions
        user_permissions: List of user's permissions
    """

    allowed: bool
    reason: str
    required_permissions: List[Permission]
    user_permissions: List[Permission]
