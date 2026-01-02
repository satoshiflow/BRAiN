"""
RBAC Middleware (Phase 3 Backend).

FastAPI middleware and decorators for RBAC.
"""

from typing import List, Callable
from functools import wraps
from fastapi import HTTPException, status

from backend.app.modules.neurorail.rbac.schemas import Permission, UserContext, Role
from backend.app.modules.neurorail.rbac.service import get_rbac_service


def require_permission(
    *permissions: Permission,
    require_all: bool = True
):
    """
    Decorator for FastAPI endpoints to enforce RBAC.

    Args:
        *permissions: Required permissions
        require_all: If True, user must have all permissions; if False, any permission suffices

    Usage:
        @router.get("/admin/config")
        @require_permission(Permission.MANAGE_SYSTEM)
        async def get_system_config(user: UserContext = Depends(get_current_user)):
            return {"config": "..."}

    Note: In this Phase 3 implementation, we're providing the decorator structure.
          Full integration with FastAPI Depends() will be in SPRINT 5 when we add authentication.
          For now, this validates the structure and can be used with manual UserContext creation.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract user context from kwargs (passed as dependency)
            user = kwargs.get("user")

            if user is None:
                # For Phase 3: Allow operations without auth (development mode)
                # In production: raise HTTPException(status_code=401, detail="Authentication required")
                # Create default admin user for development
                user = UserContext.create(user_id="dev_user", role=Role.ADMIN)

            # Authorize
            rbac = get_rbac_service()
            decision = rbac.authorize(user, list(permissions), require_all=require_all)

            if not decision.allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "Insufficient permissions",
                        "reason": decision.reason,
                        "required_permissions": [p.value for p in decision.required_permissions],
                        "user_permissions": [p.value for p in decision.user_permissions],
                    }
                )

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extract user context from kwargs
            user = kwargs.get("user")

            if user is None:
                # Development mode: default admin
                user = UserContext.create(user_id="dev_user", role=Role.ADMIN)

            # Authorize
            rbac = get_rbac_service()
            decision = rbac.authorize(user, list(permissions), require_all=require_all)

            if not decision.allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "Insufficient permissions",
                        "reason": decision.reason,
                        "required_permissions": [p.value for p in decision.required_permissions],
                        "user_permissions": [p.value for p in decision.user_permissions],
                    }
                )

            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def get_current_user_placeholder() -> UserContext:
    """
    Placeholder dependency for current user.

    In Phase 3, returns development admin user.
    In production: Will integrate with JWT authentication.

    Returns:
        UserContext for development
    """
    return UserContext.create(user_id="dev_user", role=Role.ADMIN)
