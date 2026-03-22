from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from app.core.audit_bridge import write_unified_audit


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ControlPlaneEventModel(Base):
    __tablename__ = "control_plane_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(160), nullable=False, index=True)
    event_type = Column(String(160), nullable=False, index=True)
    correlation_id = Column(String(160), nullable=True, index=True)
    mission_id = Column(String(120), nullable=True, index=True)
    actor_id = Column(String(120), nullable=True)
    actor_type = Column(String(32), nullable=True)
    payload = Column(JSONB, nullable=False, default=dict)
    audit_required = Column(Boolean, nullable=False, default=False)
    published = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    published_at = Column(DateTime(timezone=True), nullable=True)


async def record_control_plane_event(
    *,
    db: AsyncSession,
    tenant_id: str | None,
    entity_type: str,
    entity_id: str,
    event_type: str,
    correlation_id: str | None,
    mission_id: str | None,
    actor_id: str | None,
    actor_type: str | None,
    payload: dict[str, Any],
    audit_required: bool = False,
    audit_action: str | None = None,
    audit_message: str | None = None,
    severity: str = "info",
) -> ControlPlaneEventModel:
    event = ControlPlaneEventModel(
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        correlation_id=correlation_id,
        mission_id=mission_id,
        actor_id=actor_id,
        actor_type=actor_type,
        payload=payload,
        audit_required=audit_required,
    )
    db.add(event)
    if audit_required and actor_id and actor_type and audit_action and audit_message:
        await write_unified_audit(
            event_type=event_type,
            action=audit_action,
            actor=actor_id,
            actor_type=actor_type,
            resource_type=entity_type,
            resource_id=entity_id,
            severity=severity,
            message=audit_message,
            correlation_id=correlation_id,
            details=payload,
            db=db,
        )
    return event


class SkillRunTransitionModel(Base):
    __tablename__ = "skill_run_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    transition_index = Column(Integer, nullable=False, default=0)
    from_state = Column(String(32), nullable=True)
    to_state = Column(String(32), nullable=False, index=True)
    event_type = Column(String(160), nullable=False)
    correlation_id = Column(String(160), nullable=True, index=True)
    actor_id = Column(String(120), nullable=True)
    actor_type = Column(String(32), nullable=True)
    reason = Column(Text, nullable=True)
    transition_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
