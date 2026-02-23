"""Audit Logging - Router"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.core.auth_deps import require_auth, require_role, get_current_principal, Principal
from app.core.security import UserRole
from .schemas import AuditEventCreate, AuditEventResponse, AuditEventListResponse, AuditStats
from .service import get_audit_service

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("/events", response_model=AuditEventListResponse, dependencies=[Depends(require_auth)])
async def list_events(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    resource_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """List audit events with filtering."""
    service = get_audit_service()
    events = await service.get_events(
        db, event_type=event_type, action=action, actor=actor,
        resource_type=resource_type, severity=severity, limit=limit, offset=offset
    )
    return AuditEventListResponse(
        items=[AuditEventResponse.model_validate(e) for e in events],
        total=len(events)
    )

@router.get("/events/{event_id}", response_model=AuditEventResponse, dependencies=[Depends(require_auth)])
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get a specific audit event."""
    from uuid import UUID
    from sqlalchemy import select
    from .models import AuditEventModel
    
    result = await db.execute(
        select(AuditEventModel).where(AuditEventModel.id == UUID(event_id))
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return AuditEventResponse.model_validate(event)

@router.get("/resource/{resource_type}/{resource_id}", response_model=AuditEventListResponse, dependencies=[Depends(require_auth)])
async def get_resource_events(
    resource_type: str,
    resource_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get events for a specific resource."""
    service = get_audit_service()
    events = await service.get_events_for_resource(db, resource_type, resource_id, limit)
    return AuditEventListResponse(
        items=[AuditEventResponse.model_validate(e) for e in events],
        total=len(events)
    )

@router.get("/user/{user_id}", response_model=AuditEventListResponse, dependencies=[Depends(require_auth)])
async def get_user_events(
    user_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get events for a specific user."""
    service = get_audit_service()
    events = await service.get_events_for_user(db, user_id, limit)
    return AuditEventListResponse(
        items=[AuditEventResponse.model_validate(e) for e in events],
        total=len(events)
    )

@router.get("/stats", response_model=AuditStats, dependencies=[Depends(require_auth)])
async def get_stats(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get audit statistics."""
    service = get_audit_service()
    stats = await service.get_stats(db)
    return AuditStats(**stats)

@router.post("/events", response_model=AuditEventResponse, dependencies=[Depends(require_auth)])
async def create_event(
    event_data: AuditEventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Manually log an audit event."""
    service = get_audit_service()
    event = await service.log_event(
        db,
        event_data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    return AuditEventResponse.model_validate(event)
