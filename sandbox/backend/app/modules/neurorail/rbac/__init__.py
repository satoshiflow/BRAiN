"""
RBAC System (Phase 3 Backend).

Role-Based Access Control for NeuroRail ControlDeck.

Exports:
- Role: Role enum (ADMIN, OPERATOR, VIEWER)
- Permission: Permission enum
- RBACService: RBAC authorization service
- require_permission: Authorization decorator
- UserContext: User context for request
"""

from app.modules.neurorail.rbac.schemas import Role, Permission, UserContext
from app.modules.neurorail.rbac.service import RBACService, get_rbac_service
from app.modules.neurorail.rbac.middleware import require_permission

__all__ = [
    "Role",
    "Permission",
    "UserContext",
    "RBACService",
    "get_rbac_service",
    "require_permission",
]
