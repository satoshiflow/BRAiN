"""
RBAC Service (Phase 3 Backend).

Authorization service for permission checks.
"""

from typing import List, Optional
from loguru import logger

from backend.app.modules.neurorail.rbac.schemas import (
    Role,
    Permission,
    UserContext,
    RBACDecision,
    ROLE_PERMISSIONS,
)


class RBACService:
    """
    RBAC authorization service.

    Features:
    - Permission checks
    - Role-based authorization
    - Audit logging of authorization decisions

    Usage:
        rbac = RBACService()

        user = UserContext.create(user_id="user_123", role=Role.OPERATOR)

        # Check permission
        decision = rbac.authorize(user, [Permission.EXECUTE_JOB])
        if decision.allowed:
            # Execute job
            pass
    """

    def __init__(self):
        """Initialize RBAC service."""
        self.authorization_count = 0
        self.denied_count = 0

    def authorize(
        self,
        user: UserContext,
        required_permissions: List[Permission],
        require_all: bool = True
    ) -> RBACDecision:
        """
        Authorize user for required permissions.

        Args:
            user: User context
            required_permissions: List of required permissions
            require_all: If True, user must have all permissions; if False, any permission suffices

        Returns:
            RBACDecision with authorization result
        """
        self.authorization_count += 1

        if require_all:
            allowed = user.has_all_permissions(required_permissions)
            reason = "User has all required permissions" if allowed else "User missing required permissions"
        else:
            allowed = user.has_any_permission(required_permissions)
            reason = "User has at least one required permission" if allowed else "User missing all required permissions"

        if not allowed:
            self.denied_count += 1

        decision = RBACDecision(
            allowed=allowed,
            reason=reason,
            required_permissions=required_permissions,
            user_permissions=user.permissions,
        )

        logger.debug(
            f"RBAC authorization: {user.user_id} ({user.role}) - {'ALLOWED' if allowed else 'DENIED'}",
            extra={
                "user_id": user.user_id,
                "role": user.role,
                "required_permissions": [p.value for p in required_permissions],
                "allowed": allowed,
                "require_all": require_all,
            }
        )

        return decision

    def get_role_permissions(self, role: Role) -> List[Permission]:
        """Get all permissions for a role."""
        return ROLE_PERMISSIONS.get(role, [])

    def get_stats(self) -> dict:
        """Get RBAC statistics."""
        return {
            "authorization_count": self.authorization_count,
            "denied_count": self.denied_count,
            "denial_rate": self.denied_count / self.authorization_count if self.authorization_count > 0 else 0.0,
        }


# Singleton service
_rbac_service: Optional[RBACService] = None


def get_rbac_service() -> RBACService:
    """Get or create singleton RBAC service."""
    global _rbac_service
    if _rbac_service is None:
        _rbac_service = RBACService()
    return _rbac_service
