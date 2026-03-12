"""FastAPI routes for AXE user-scoped chat sessions."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, require_auth
from app.core.database import get_db

from .schemas import (
    AXEChatMessageCreateRequest,
    AXEChatMessageResponse,
    AXEChatSessionCreateRequest,
    AXEChatSessionDetailResponse,
    AXEChatSessionSummaryResponse,
    AXEChatSessionUpdateRequest,
)
from .service import AXESessionService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/axe/sessions",
    tags=["axe-sessions"],
    dependencies=[Depends(require_auth)],
)


def get_service(db: AsyncSession = Depends(get_db)) -> AXESessionService:
    return AXESessionService(db)


def _serialize_message(message) -> AXEChatMessageResponse:
    return AXEChatMessageResponse(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        attachments=message.attachments_json or [],
        metadata=message.message_metadata or {},
        created_at=message.created_at,
    )


@router.get("", response_model=list[AXEChatSessionSummaryResponse])
async def list_sessions(
    principal: Principal = Depends(require_auth),
    service: AXESessionService = Depends(get_service),
):
    sessions = await service.list_sessions(
        principal_id=principal.principal_id,
        tenant_id=principal.tenant_id,
    )
    return sessions


@router.post("", response_model=AXEChatSessionSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: AXEChatSessionCreateRequest,
    principal: Principal = Depends(require_auth),
    service: AXESessionService = Depends(get_service),
):
    return await service.create_session(
        principal_id=principal.principal_id,
        tenant_id=principal.tenant_id,
        payload=payload,
    )


@router.get("/{session_id}", response_model=AXEChatSessionDetailResponse)
async def get_session_detail(
    session_id: UUID,
    principal: Principal = Depends(require_auth),
    service: AXESessionService = Depends(get_service),
):
    session = await service.get_session_detail(
        principal_id=principal.principal_id,
        tenant_id=principal.tenant_id,
        session_id=session_id,
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return AXEChatSessionDetailResponse(
        id=session.id,
        title=session.title,
        preview=session.preview,
        status=session.status,
        message_count=session.message_count,
        created_at=session.created_at,
        updated_at=session.updated_at,
        last_message_at=session.last_message_at,
        messages=[_serialize_message(message) for message in session.messages],
    )


@router.patch("/{session_id}", response_model=AXEChatSessionSummaryResponse)
async def rename_session(
    session_id: UUID,
    payload: AXEChatSessionUpdateRequest,
    principal: Principal = Depends(require_auth),
    service: AXESessionService = Depends(get_service),
):
    try:
        session = await service.update_session_title(
            principal_id=principal.principal_id,
            tenant_id=principal.tenant_id,
            session_id=session_id,
            payload=payload,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    principal: Principal = Depends(require_auth),
    service: AXESessionService = Depends(get_service),
):
    deleted = await service.delete_session(
        principal_id=principal.principal_id,
        tenant_id=principal.tenant_id,
        session_id=session_id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


@router.post("/{session_id}/messages", response_model=AXEChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def append_message(
    session_id: UUID,
    payload: AXEChatMessageCreateRequest,
    principal: Principal = Depends(require_auth),
    service: AXESessionService = Depends(get_service),
):
    message = await service.append_message(
        principal_id=principal.principal_id,
        tenant_id=principal.tenant_id,
        session_id=session_id,
        payload=payload,
    )
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return _serialize_message(message)
