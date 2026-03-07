"""Bridge for writing unified audit events via the existing audit logging module."""

from __future__ import annotations

import os
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.modules.audit_logging.schemas import AuditEventCreate
from app.modules.audit_logging.service import get_audit_service


async def write_unified_audit(
    *,
    event_type: str,
    action: str,
    actor: str,
    actor_type: str,
    resource_type: str,
    resource_id: str,
    severity: str,
    message: str,
    correlation_id: Optional[str],
    details: dict,
    db: AsyncSession | None = None,
) -> None:
    """Write an audit entry through the central audit logging service."""
    payload = AuditEventCreate(
        event_type=event_type,
        action=action,
        actor=actor,
        actor_type=actor_type,
        resource_type=resource_type,
        resource_id=resource_id,
        severity=severity,
        message=message,
        extra_data={**details, "correlation_id": correlation_id},
    )

    try:
        service = get_audit_service()
        if db is not None:
            await service.log_event(db, payload)
            return

        implicit_db = os.getenv("BRAIN_AUDIT_BRIDGE_IMPLICIT_DB", "false").lower() == "true"
        if not implicit_db:
            logger.debug("[AuditBridge] skipped implicit DB session for event_type=%s", event_type)
            return

        async with AsyncSessionLocal() as temp_db:
            await service.log_event(temp_db, payload)
    except Exception as exc:  # pragma: no cover
        logger.error("[AuditBridge] failed to write audit event: %s", exc)
