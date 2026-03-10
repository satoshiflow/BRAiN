"""
Fred Bridge API Router

REST API endpoints for the Fred Bridge system.
Provides ticket ingestion and patch artifact management.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_deps import require_auth, require_role
from app.modules.fred_bridge.schemas import (
    FredTicket,
    FredTicketCreate,
    FredTicketUpdate,
    PatchArtifact,
    PatchArtifactCreate,
    PatchArtifactUpdate,
    TicketListResponse,
    PatchListResponse,
    MockPatchConfig,
)
from app.modules.fred_bridge.service import FredBridgeService, get_bridge_service

router = APIRouter(
    prefix="/api/fred-bridge",
    tags=["fred-bridge"],
)


# =============================================================================
# Ticket Endpoints
# =============================================================================

@router.post("/tickets", response_model=FredTicket)
async def create_ticket(
    ticket_data: FredTicketCreate,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_role("admin")),  # Only admin for MVP
):
    """
    Create a new ticket in the Fred Bridge.
    
    Tickets represent requests for development intelligence (bugs, features, refactors).
    """
    service = await get_bridge_service(db)
    ticket = await service.create_ticket(ticket_data)
    return ticket


@router.get("/tickets", response_model=TicketListResponse)
async def list_tickets(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    component: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_role("admin")),
):
    """
    List tickets with optional filtering.
    
    Returns paginated list of tickets sorted by creation date (newest first).
    """
    service = await get_bridge_service(db)
    tickets = await service.list_tickets(
        status=status,
        severity=severity,
        component=component,
        limit=limit,
        offset=offset,
    )
    
    # For MVP, total count is len(tickets) + offset (approximate)
    # In production, use count query
    total = len(tickets) + offset
    
    return TicketListResponse(
        tickets=tickets,
        total=total,
        page=offset // limit + 1,
        page_size=limit,
    )


@router.get("/tickets/{ticket_id}", response_model=FredTicket)
async def get_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_role("admin")),
):
    """Get a single ticket by ID"""
    service = await get_bridge_service(db)
    ticket = await service.get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    
    return ticket


@router.patch("/tickets/{ticket_id}", response_model=FredTicket)
async def update_ticket(
    ticket_id: str,
    update_data: FredTicketUpdate,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_role("admin")),
):
    """Update a ticket (status, severity, etc.)"""
    service = await get_bridge_service(db)
    ticket = await service.update_ticket(ticket_id, update_data)
    
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    
    return ticket


# =============================================================================
# Patch Artifact Endpoints
# =============================================================================

@router.post("/patches", response_model=PatchArtifact)
async def submit_patch(
    patch_data: PatchArtifactCreate,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_role("admin")),
):
    """
    Submit a patch artifact (typically by Fred).
    
    Patch artifacts contain code changes, tests, risk assessment, and deployment plan.
    """
    service = await get_bridge_service(db)
    
    try:
        patch = await service.create_patch(patch_data)
        return patch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/patches", response_model=PatchListResponse)
async def list_patches(
    ticket_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_role("admin")),
):
    """List patches with optional filtering"""
    service = await get_bridge_service(db)
    patches = await service.list_patches(
        ticket_id=ticket_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    
    total = len(patches) + offset
    
    return PatchListResponse(
        patches=patches,
        total=total,
        page=offset // limit + 1,
        page_size=limit,
    )


@router.get("/patches/{patch_id}", response_model=PatchArtifact)
async def get_patch(
    patch_id: str,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_role("admin")),
):
    """Get a single patch by ID"""
    service = await get_bridge_service(db)
    patch = await service.get_patch(patch_id)
    
    if not patch:
        raise HTTPException(status_code=404, detail=f"Patch {patch_id} not found")
    
    return patch


@router.patch("/patches/{patch_id}", response_model=PatchArtifact)
async def update_patch(
    patch_id: str,
    update_data: PatchArtifactUpdate,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_role("admin")),
):
    """Update a patch (status change, etc.)"""
    service = await get_bridge_service(db)
    patch = await service.update_patch(patch_id, update_data)
    
    if not patch:
        raise HTTPException(status_code=404, detail=f"Patch {patch_id} not found")
    
    return patch


@router.post("/patches/{patch_id}/request-approval", response_model=PatchArtifact)
async def request_patch_approval(
    patch_id: str,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_role("admin")),
):
    """
    Request approval for a patch.
    
    This notifies the Governor and moves patch to IN_REVIEW status.
    Control Deck can only REQUEST approval, not directly approve.
    """
    service = await get_bridge_service(db)
    
    patch = await service.request_approval(
        patch_id=patch_id,
        requester=principal.email if hasattr(principal, 'email') else 'unknown',
    )
    
    if not patch:
        raise HTTPException(status_code=404, detail=f"Patch {patch_id} not found")
    
    return patch


# =============================================================================
# Mock Fred Endpoints
# =============================================================================

@router.post("/mock/create-patch", response_model=PatchArtifact)
async def create_mock_patch(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_role("admin")),
):
    """
    Create a mock/synthetic patch for testing.
    
    This simulates Fred proposing a patch without actual Fred running.
    Useful for CI testing, demos, and pipeline validation.
    """
    service = await get_bridge_service(db)
    
    try:
        patch = await service.create_mock_patch(ticket_id)
        return patch
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Health & Status
# =============================================================================

@router.get("/health")
async def bridge_health(
    db: AsyncSession = Depends(get_db),
    principal = Depends(require_auth),
):
    """Get Bridge system health status"""
    service = await get_bridge_service(db)
    
    # Get counts
    open_tickets = await service.list_tickets(status="open", limit=1)
    proposed_patches = await service.list_patches(status="proposed", limit=1)
    
    return {
        "status": "healthy",
        "open_tickets": len(open_tickets),
        "proposed_patches": len(proposed_patches),
        "mode": "development",  # development | production
        "fred_connection": "polling",  # polling | websocket | disconnected
    }
