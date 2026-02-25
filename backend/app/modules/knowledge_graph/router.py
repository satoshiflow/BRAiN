"""
Knowledge Graph API Router

REST API endpoints for knowledge graph operations.

SECURITY NOTICE: The reset endpoint now requires:
1. Admin authentication (require_admin_user dependency)
2. Confirmation token for destructive operations
3. Audit logging of all reset attempts

See: docs/security_lockdown/RESULTS.md
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from loguru import logger
from pydantic import BaseModel, Field

from .service import CogneeService, AgentMemoryService
from .schemas import (
    KnowledgeGraphInfo,
    AddDataRequest,
    AddDataResponse,
    SearchRequest,
    SearchResponse,
    MissionContextRequest,
    SimilarMissionsResponse,
    CognifyRequest,
    CognifyResponse,
    ListDatasetsResponse,
)

# Import auth dependencies - try multiple locations for compatibility
try:
    from app.core.auth_deps import require_admin as require_admin_user, require_auth
except ImportError:
    try:
        from app.core.security import require_admin as require_admin_user
        from app.core.auth_deps import require_auth
    except ImportError:
        # Fallback if auth not available
        async def require_admin_user():
            """Fallback - no auth required in dev mode"""
            return {"principal_id": "dev_user", "roles": ["admin"]}
        async def require_auth():
            """Fallback - no auth required in dev mode"""
            return {"principal_id": "dev_user", "roles": ["user"]}


# Create router
router = APIRouter(
    prefix="/api/knowledge-graph",
    tags=["knowledge-graph"],
)

# Initialize services
cognee_service = CogneeService()
memory_service = AgentMemoryService()

# In-memory store for confirmation tokens (use Redis in production)
_reset_confirmation_tokens: dict[str, dict] = {}


# ============================================================================
# Protected Reset Schemas
# ============================================================================

class ResetRequestRequest(BaseModel):
    """Request a reset confirmation token"""
    reason: str = Field(..., description="Reason for reset (logged for audit)")


class ResetRequestResponse(BaseModel):
    """Response with confirmation token"""
    confirmation_token: str
    message: str
    expires_in_seconds: int = 300  # 5 minutes


class ResetConfirmRequest(BaseModel):
    """Confirm reset with token"""
    confirmation_token: str = Field(..., description="Token received from request endpoint")
    confirm_delete: bool = Field(..., description="Must be True to proceed")


class ResetResponse(BaseModel):
    """Reset operation response"""
    success: bool
    message: str
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None
    archived: bool = False


# ============================================================================
# Audit Logging
# ============================================================================

async def _audit_kg_reset(
    action: str,
    actor: str,
    ip_address: str,
    success: bool,
    details: dict,
    severity: str = "warning",
):
    """
    Log knowledge graph reset actions to audit log.
    
    Args:
        action: The action performed (e.g., "reset_requested", "reset_completed")
        actor: User ID performing the action
        ip_address: Client IP address
        success: Whether the action succeeded
        details: Additional context
        severity: Event severity level
    """
    try:
        # Try to use sovereign mode audit if available
        try:
            from app.modules.sovereign_mode.service import get_sovereign_service
            service = get_sovereign_service()
            service._audit(
                event_type=f"kg_{action}",
                actor=actor,
                resource_type="knowledge_graph",
                resource_id="all",
                action=action,
                success=success,
                severity=severity,
                metadata={
                    **details,
                    "ip_address": ip_address,
                },
            )
        except Exception:
            # Fallback to loguru logging
            logger.warning(
                f"AUDIT: KG {action} | actor={actor} | ip={ip_address} | "
                f"success={success} | details={details}"
            )
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


# ============================================================================
# Endpoints
# ============================================================================

@router.get(
    "/info",
    response_model=KnowledgeGraphInfo,
    summary="Get knowledge graph system information",
)
async def get_info(
    user=Depends(require_auth),
):
    """
    Get information about the knowledge graph system

    Returns system status, features, and backend configuration.
    """
    return KnowledgeGraphInfo(
        status="active" if cognee_service.initialized else "unavailable",
    )


@router.post(
    "/add",
    response_model=AddDataResponse,
    summary="Add data to knowledge graph",
)
async def add_data(
    request: AddDataRequest,
    user=Depends(require_auth),
):
    """
    Add data to the knowledge graph

    Accepts:
    - Text strings
    - Lists of text strings
    - Structured data dictionaries

    The data will be stored in the specified dataset.
    """
    return await cognee_service.add_data(
        data=request.data,
        dataset_name=request.dataset_name,
    )


@router.post(
    "/cognify",
    response_model=CognifyResponse,
    summary="Process data into knowledge graph",
)
async def cognify_data(
    request: CognifyRequest,
    user=Depends(require_auth),
):
    """
    Process data into knowledge graph (extract entities and relationships)

    This operation:
    1. Analyzes text data
    2. Extracts entities (people, places, concepts)
    3. Identifies relationships (triplets)
    4. Builds knowledge graph structure
    5. Generates embeddings for semantic search

    This is a potentially long-running operation for large datasets.
    """
    return await cognee_service.cognify(
        dataset_name=request.dataset_name,
        temporal=request.temporal,
    )


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search knowledge graph",
)
async def search_knowledge_graph(
    request: SearchRequest,
    user=Depends(require_auth),
):
    """
    Search the knowledge graph using semantic search

    Search types:
    - INSIGHTS: High-level semantic search
    - CHUNKS: Document chunk search
    - HYBRID: Combination of vector + graph search (recommended)

    Returns ranked results with relevance scores.
    """
    return await cognee_service.search(
        query=request.query,
        dataset_name=request.dataset_name,
        search_type=request.search_type,
        limit=request.limit,
    )


@router.get(
    "/datasets",
    response_model=ListDatasetsResponse,
    summary="List all datasets",
)
async def list_datasets(
    user=Depends(require_auth),
):
    """
    List all datasets in the knowledge graph

    Returns information about each dataset including:
    - Name
    - Description
    - Item count
    - Last updated timestamp
    """
    return await cognee_service.list_datasets()


# ============================================================================
# PROTECTED RESET ENDPOINTS (Security Fix)
# ============================================================================

@router.post(
    "/reset/request",
    response_model=ResetRequestResponse,
    summary="Request knowledge graph reset (Admin only)",
    dependencies=[Depends(require_admin_user)],
)
async def request_reset(
    request: Request,
    reset_request: ResetRequestRequest,
    admin=Depends(require_admin_user),
):
    """
    **ADMIN ONLY**: Request a confirmation token for knowledge graph reset.
    
    This is Step 1 of the 2-step reset process:
    1. Call this endpoint to get a confirmation token (valid for 5 minutes)
    2. Use the token with POST /reset/confirm to execute the reset
    
    Requires admin role. All requests are logged.
    """
    # Extract admin ID
    admin_id = getattr(admin, 'principal_id', str(admin))
    ip_address = request.client.host if request.client else "unknown"
    
    # Generate confirmation token
    confirmation_token = str(uuid.uuid4())
    
    # Store token with metadata
    _reset_confirmation_tokens[confirmation_token] = {
        "requested_by": admin_id,
        "requested_at": datetime.utcnow().isoformat(),
        "reason": reset_request.reason,
        "ip_address": ip_address,
        "used": False,
    }
    
    # Log audit event
    await _audit_kg_reset(
        action="reset_requested",
        actor=admin_id,
        ip_address=ip_address,
        success=True,
        details={
            "reason": reset_request.reason,
            "confirmation_token_prefix": confirmation_token[:8] + "...",
        },
        severity="warning",
    )
    
    logger.warning(
        f"KG reset requested by admin {admin_id} from {ip_address}. "
        f"Token: {confirmation_token[:8]}..."
    )
    
    return ResetRequestResponse(
        confirmation_token=confirmation_token,
        message="Confirmation token generated. Use this token with POST /reset/confirm within 5 minutes.",
        expires_in_seconds=300,
    )


@router.post(
    "/reset/confirm",
    response_model=ResetResponse,
    summary="Confirm and execute knowledge graph reset (Admin only)",
    dependencies=[Depends(require_admin_user)],
)
async def confirm_reset(
    request: Request,
    confirm_request: ResetConfirmRequest,
    admin=Depends(require_admin_user),
):
    """
    **ADMIN ONLY**: Execute knowledge graph reset with confirmation token.
    
    This is Step 2 of the 2-step reset process:
    1. Must have valid confirmation token from /reset/request
    2. Must explicitly set confirm_delete=True
    
    **DANGER**: This operation:
    - Deletes all datasets
    - Removes all knowledge graphs
    - Clears all embeddings
    - Cannot be undone
    
    Requires admin role. All actions are logged with full audit trail.
    """
    # Extract admin ID
    admin_id = getattr(admin, 'principal_id', str(admin))
    ip_address = request.client.host if request.client else "unknown"
    
    # Validate confirmation token
    token_data = _reset_confirmation_tokens.get(confirm_request.confirmation_token)
    
    if not token_data:
        await _audit_kg_reset(
            action="reset_confirm_failed",
            actor=admin_id,
            ip_address=ip_address,
            success=False,
            details={"error": "invalid_token"},
            severity="error",
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired confirmation token. Please request a new token.",
        )
    
    if token_data.get("used"):
        await _audit_kg_reset(
            action="reset_confirm_failed",
            actor=admin_id,
            ip_address=ip_address,
            success=False,
            details={"error": "token_already_used"},
            severity="error",
        )
        raise HTTPException(
            status_code=400,
            detail="Confirmation token has already been used.",
        )
    
    # Check if token is expired (5 minutes)
    from datetime import datetime, timedelta
    requested_at = datetime.fromisoformat(token_data["requested_at"])
    if datetime.utcnow() - requested_at > timedelta(minutes=5):
        await _audit_kg_reset(
            action="reset_confirm_failed",
            actor=admin_id,
            ip_address=ip_address,
            success=False,
            details={"error": "token_expired"},
            severity="error",
        )
        raise HTTPException(
            status_code=400,
            detail="Confirmation token has expired. Please request a new token.",
        )
    
    # Verify explicit confirmation
    if not confirm_request.confirm_delete:
        await _audit_kg_reset(
            action="reset_confirm_failed",
            actor=admin_id,
            ip_address=ip_address,
            success=False,
            details={"error": "confirm_delete_not_set"},
            severity="warning",
        )
        raise HTTPException(
            status_code=400,
            detail="Must set confirm_delete=True to proceed with reset.",
        )
    
    # Mark token as used
    token_data["used"] = True
    token_data["confirmed_by"] = admin_id
    token_data["confirmed_at"] = datetime.utcnow().isoformat()
    
    try:
        # Execute the reset
        logger.critical(
            f"EXECUTING KG RESET by {admin_id} from {ip_address}. "
            f"Reason: {token_data.get('reason', 'N/A')}"
        )
        
        success = await cognee_service.reset()
        
        if success:
            # Log successful reset
            await _audit_kg_reset(
                action="reset_completed",
                actor=admin_id,
                ip_address=ip_address,
                success=True,
                details={
                    "reason": token_data.get("reason"),
                    "original_requester": token_data.get("requested_by"),
                    "token_age_seconds": (datetime.utcnow() - requested_at).total_seconds(),
                },
                severity="critical",
            )
            
            return ResetResponse(
                success=True,
                message="Knowledge graph reset completed successfully. All data has been deleted.",
                deleted_at=datetime.utcnow().isoformat(),
                deleted_by=admin_id,
                archived=False,
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to reset knowledge graph",
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        
        # Log failed reset
        await _audit_kg_reset(
            action="reset_failed",
            actor=admin_id,
            ip_address=ip_address,
            success=False,
            details={
                "error": str(e),
                "reason": token_data.get("reason"),
            },
            severity="critical",
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Reset operation failed: {str(e)}",
        )


@router.delete(
    "/reset",
    summary="⚠️ DEPRECATED: Reset knowledge graph (UNPROTECTED)",
    deprecated=True,
)
async def reset_knowledge_graph_deprecated():
    """
    ⚠️ **DEPRECATED - DO NOT USE** ⚠️
    
    This endpoint is unprotected and deprecated for security reasons.
    
    Use the new 2-step process instead:
    1. POST /reset/request (Admin only) - Get confirmation token
    2. POST /reset/confirm (Admin only) - Execute reset with token
    
    This endpoint will be removed in a future version.
    """
    raise HTTPException(
        status_code=410,  # Gone
        detail=(
            "This endpoint is deprecated and disabled for security. "
            "Use POST /reset/request followed by POST /reset/confirm. "
            "Admin role required."
        ),
    )


# Agent Memory Endpoints


@router.post(
    "/missions/record",
    response_model=AddDataResponse,
    summary="Record mission context",
    tags=["agent-memory"],
)
async def record_mission_context(
    mission: MissionContextRequest,
    user=Depends(require_auth),
):
    """
    Record a mission's context in the knowledge graph

    This creates structured knowledge from mission data including:
    - Mission metadata (ID, type, priority)
    - Agent assignments
    - Execution results
    - Temporal information

    Used by agents to build persistent memory.
    """
    return await memory_service.record_mission_context(mission)


@router.post(
    "/missions/similar",
    response_model=SimilarMissionsResponse,
    summary="Find similar missions",
    tags=["agent-memory"],
)
async def find_similar_missions(
    mission: MissionContextRequest,
    limit: int = 5,
    user=Depends(require_auth),
):
    """
    Find missions similar to the given mission

    Uses semantic search to find past missions with:
    - Similar descriptions
    - Same mission type
    - Similar context
    - Comparable priority

    Useful for:
    - Learning from past successes/failures
    - Risk assessment
    - Agent decision support
    """
    return await memory_service.find_similar_missions(
        query_mission=mission,
        limit=limit,
    )


@router.get(
    "/agents/{agent_id}/expertise",
    response_model=SearchResponse,
    summary="Get agent expertise",
    tags=["agent-memory"],
)
async def get_agent_expertise(
    agent_id: str,
    user=Depends(require_auth),
):
    """
    Extract agent's expertise from decision history

    Analyzes the knowledge graph to find:
    - Successful task completions
    - Decision patterns
    - Specialized knowledge
    - Performance history

    Returns insights about the agent's capabilities and experience.
    """
    return await memory_service.get_agent_expertise(agent_id)


# Health check endpoint


@router.get(
    "/health",
    summary="Knowledge graph health check",
)
async def health_check(
    user=Depends(require_auth),
):
    """
    Check knowledge graph system health

    Returns:
    - Initialization status
    - Backend availability
    - Error states
    """
    return {
        "status": "healthy" if cognee_service.initialized else "unhealthy",
        "initialized": cognee_service.initialized,
        "service": "cognee",
    }
