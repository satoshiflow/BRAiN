"""
API Key Management Endpoints.

Provides CRUD operations for API keys:
- Create API keys
- List API keys
- Revoke API keys
- Rotate API keys
- Get key details

Security:
- Requires admin authentication
- Plaintext keys only returned on creation
- All operations logged for audit
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from app.core.api_keys import (
    APIKeyManager,
    APIKeyCreate,
    APIKeyResponse,
    Scopes,
    get_api_key_manager,
)
from app.core.security import get_current_principal, Principal

router = APIRouter(prefix="/api/keys", tags=["api-keys"])


# ============================================================================
# Request/Response Models
# ============================================================================

class KeyCreateRequest(BaseModel):
    """API key creation request."""
    name: str
    scopes: List[str] = []
    expires_in_days: Optional[int] = None
    ip_whitelist: Optional[List[str]] = None
    metadata: dict = {}


class KeyRotateResponse(BaseModel):
    """API key rotation response."""
    old_key_id: str
    new_key: APIKeyResponse


class ScopesListResponse(BaseModel):
    """Available scopes response."""
    scopes: List[str]


# ============================================================================
# Dependency: Require Admin
# ============================================================================

async def require_admin(principal: Principal = Depends(get_current_principal)):
    """
    Require admin role for API key management.

    API key management is a privileged operation.
    """
    if "admin" not in principal.roles:
        raise HTTPException(
            status_code=403,
            detail="Admin role required for API key management"
        )
    return principal


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/", response_model=APIKeyResponse)
async def create_api_key(
    request: KeyCreateRequest,
    manager: APIKeyManager = Depends(get_api_key_manager),
    principal: Principal = Depends(require_admin)
):
    """
    Create new API key.

    **Security Note:** The plaintext API key is only returned in this response.
    Store it securely - it cannot be retrieved again.

    Args:
        request: API key creation request

    Returns:
        API key response with plaintext key

    Example:
        POST /api/keys/
        {
            "name": "Production API",
            "scopes": ["missions:read", "agents:read"],
            "expires_in_days": 90,
            "ip_whitelist": ["203.0.113.1"]
        }

        Response:
        {
            "id": "abc123",
            "name": "Production API",
            "key": "brain_a1b2c3d4e5f6...",  # ⚠️ Only shown once!
            "prefix": "a1b2c3d4",
            "scopes": ["missions:read", "agents:read"],
            "created_at": "2025-12-20T10:30:00",
            "expires_at": "2026-03-20T10:30:00",
            "is_active": true,
            "usage_count": 0
        }
    """
    try:
        api_key = await manager.create_key(
            name=request.name,
            scopes=request.scopes,
            expires_in_days=request.expires_in_days,
            ip_whitelist=request.ip_whitelist,
            metadata=request.metadata,
        )

        return api_key

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create API key: {str(e)}"
        )


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    include_inactive: bool = False,
    manager: APIKeyManager = Depends(get_api_key_manager),
    principal: Principal = Depends(require_admin)
):
    """
    List all API keys.

    Args:
        include_inactive: Include inactive/revoked keys (default: False)

    Returns:
        List of API keys (without plaintext keys)

    Example:
        GET /api/keys/?include_inactive=true
    """
    try:
        keys = await manager.list_keys(include_inactive=include_inactive)
        return keys

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list API keys: {str(e)}"
        )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    manager: APIKeyManager = Depends(get_api_key_manager),
    principal: Principal = Depends(require_admin)
):
    """
    Get API key by ID.

    Args:
        key_id: API key ID

    Returns:
        API key details (without plaintext key)

    Example:
        GET /api/keys/abc123
    """
    try:
        api_key = await manager.get_key_by_id(key_id)

        if not api_key:
            raise HTTPException(
                status_code=404,
                detail=f"API key not found: {key_id}"
            )

        return api_key

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get API key: {str(e)}"
        )


@router.post("/{key_id}/revoke")
async def revoke_api_key(
    key_id: str,
    manager: APIKeyManager = Depends(get_api_key_manager),
    principal: Principal = Depends(require_admin)
):
    """
    Revoke API key.

    Marks the key as inactive. It can no longer be used for authentication.

    Args:
        key_id: API key ID

    Returns:
        Success message

    Example:
        POST /api/keys/abc123/revoke
    """
    try:
        success = await manager.revoke_key(key_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"API key not found: {key_id}"
            )

        return {
            "success": True,
            "message": f"API key revoked: {key_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke API key: {str(e)}"
        )


@router.post("/{key_id}/rotate", response_model=KeyRotateResponse)
async def rotate_api_key(
    key_id: str,
    manager: APIKeyManager = Depends(get_api_key_manager),
    principal: Principal = Depends(require_admin)
):
    """
    Rotate API key.

    Creates a new key with the same settings and revokes the old one.

    **Security Note:** The plaintext API key is only returned in this response.
    Store it securely - it cannot be retrieved again.

    Args:
        key_id: API key ID to rotate

    Returns:
        Old key ID and new key response

    Example:
        POST /api/keys/abc123/rotate

        Response:
        {
            "old_key_id": "abc123",
            "new_key": {
                "id": "def456",
                "name": "Production API (rotated)",
                "key": "brain_x1y2z3...",  # ⚠️ Only shown once!
                "prefix": "x1y2z3",
                ...
            }
        }
    """
    try:
        new_key = await manager.rotate_key(key_id)

        if not new_key:
            raise HTTPException(
                status_code=404,
                detail=f"API key not found: {key_id}"
            )

        return KeyRotateResponse(
            old_key_id=key_id,
            new_key=new_key,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rotate API key: {str(e)}"
        )


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    manager: APIKeyManager = Depends(get_api_key_manager),
    principal: Principal = Depends(require_admin)
):
    """
    Delete API key permanently.

    ⚠️ This operation cannot be undone. Consider revoking instead.

    Args:
        key_id: API key ID

    Returns:
        Success message

    Example:
        DELETE /api/keys/abc123
    """
    # For now, same as revoke (can implement hard delete later)
    try:
        success = await manager.revoke_key(key_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"API key not found: {key_id}"
            )

        return {
            "success": True,
            "message": f"API key deleted: {key_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete API key: {str(e)}"
        )


@router.get("/scopes/available", response_model=ScopesListResponse)
async def list_available_scopes(
    principal: Principal = Depends(require_admin)
):
    """
    List all available API key scopes.

    Returns:
        List of scope strings

    Example:
        GET /api/keys/scopes/available

        Response:
        {
            "scopes": [
                "missions:read",
                "missions:write",
                "missions:delete",
                "missions:*",
                "agents:read",
                ...
            ]
        }
    """
    return ScopesListResponse(
        scopes=Scopes.get_all_scopes()
    )
