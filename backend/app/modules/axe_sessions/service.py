"""Business logic for AXE user-scoped chat sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import AXEChatMessageORM, AXEChatSessionORM
from .schemas import (
    AXEChatMessageCreateRequest,
    AXEChatSessionCreateRequest,
    AXEChatSessionUpdateRequest,
)


DEFAULT_SESSION_TITLE = "New Chat"


def _normalize_text(text: str, limit: int) -> str:
    compact = " ".join(text.strip().split())
    if len(compact) <= limit:
        return compact
    return compact[: max(limit - 1, 1)].rstrip() + "..."


def generate_session_title(content: str) -> str:
    normalized = _normalize_text(content, 60)
    return normalized or DEFAULT_SESSION_TITLE


def generate_preview(content: str) -> str:
    return _normalize_text(content, 120)


class AXESessionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _tenant_matches(principal_tenant_id: str | None, session_tenant_id: str | None) -> bool:
        return principal_tenant_id == session_tenant_id

    def _owned_sessions_query(self, principal_id: str) -> Select[tuple[AXEChatSessionORM]]:
        return (
            select(AXEChatSessionORM)
            .where(
                AXEChatSessionORM.principal_id == principal_id,
                AXEChatSessionORM.status == "active",
            )
            .order_by(desc(AXEChatSessionORM.last_message_at), desc(AXEChatSessionORM.updated_at))
        )

    async def list_sessions(self, *, principal_id: str, tenant_id: str | None) -> list[AXEChatSessionORM]:
        rows: Sequence[AXEChatSessionORM] = (await self.db.execute(self._owned_sessions_query(principal_id))).scalars().all()
        return [row for row in rows if self._tenant_matches(tenant_id, row.tenant_id)]

    async def create_session(
        self,
        *,
        principal_id: str,
        tenant_id: str | None,
        payload: AXEChatSessionCreateRequest,
    ) -> AXEChatSessionORM:
        title = payload.title.strip() if payload.title else DEFAULT_SESSION_TITLE
        if not title:
            title = DEFAULT_SESSION_TITLE
        session = AXEChatSessionORM(
            principal_id=principal_id,
            tenant_id=tenant_id,
            title=title,
            preview=None,
            status="active",
            message_count=0,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session_detail(
        self,
        *,
        principal_id: str,
        tenant_id: str | None,
        session_id: UUID,
    ) -> AXEChatSessionORM | None:
        query = (
            select(AXEChatSessionORM)
            .options(selectinload(AXEChatSessionORM.messages))
            .where(
                AXEChatSessionORM.id == session_id,
                AXEChatSessionORM.principal_id == principal_id,
                AXEChatSessionORM.status == "active",
            )
        )
        session = (await self.db.execute(query)).scalars().first()
        if session is None:
            return None
        if not self._tenant_matches(tenant_id, session.tenant_id):
            return None
        session.messages.sort(key=lambda message: message.created_at)
        return session

    async def update_session_title(
        self,
        *,
        principal_id: str,
        tenant_id: str | None,
        session_id: UUID,
        payload: AXEChatSessionUpdateRequest,
    ) -> AXEChatSessionORM | None:
        session = await self.get_session_detail(
            principal_id=principal_id,
            tenant_id=tenant_id,
            session_id=session_id,
        )
        if session is None:
            return None

        updated_title = payload.title.strip()
        if not updated_title:
            raise ValueError("Session title cannot be empty")

        session.title = updated_title
        session.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def delete_session(
        self,
        *,
        principal_id: str,
        tenant_id: str | None,
        session_id: UUID,
    ) -> bool:
        session = await self.get_session_detail(
            principal_id=principal_id,
            tenant_id=tenant_id,
            session_id=session_id,
        )
        if session is None:
            return False

        session.status = "deleted"
        session.updated_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def append_message(
        self,
        *,
        principal_id: str,
        tenant_id: str | None,
        session_id: UUID,
        payload: AXEChatMessageCreateRequest,
    ) -> AXEChatMessageORM | None:
        session = await self.get_session_detail(
            principal_id=principal_id,
            tenant_id=tenant_id,
            session_id=session_id,
        )
        if session is None:
            return None

        message = AXEChatMessageORM(
            session_id=session.id,
            role=payload.role,
            content=payload.content,
            attachments_json=list(payload.attachments),
            message_metadata=dict(payload.metadata),
        )
        self.db.add(message)

        session.message_count = (session.message_count or 0) + 1
        session.preview = generate_preview(payload.content)
        session.last_message_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()

        if payload.role == "user" and session.message_count == 1 and session.title == DEFAULT_SESSION_TITLE:
            session.title = generate_session_title(payload.content)

        await self.db.commit()
        await self.db.refresh(message)
        return message
