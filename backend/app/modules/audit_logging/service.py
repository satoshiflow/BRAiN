"""Audit Logging - Service"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Optional
from loguru import logger
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import AuditEventModel
from .schemas import AuditEventCreate, AuditEventResponse

class AuditLoggingService:
    def __init__(self, event_stream=None):
        self.event_stream = event_stream
        logger.info("📋 Audit Logging Service initialized")
    
    async def log_event(
        self,
        db: AsyncSession,
        event_data: AuditEventCreate,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditEventModel:
        """Log an audit event."""
        event = AuditEventModel(
            event_type=event_data.event_type,
            action=event_data.action,
            actor=event_data.actor,
            actor_type=event_data.actor_type,
            resource_type=event_data.resource_type,
            resource_id=event_data.resource_id,
            old_values=event_data.old_values,
            new_values=event_data.new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            severity=event_data.severity,
            message=event_data.message,
            metadata=event_data.metadata,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        
        # Publish to EventStream
        if self.event_stream:
            try:
                await self.event_stream.publish({
                    "type": f"audit.{event_data.event_type}",
                    "action": event_data.action,
                    "actor": event_data.actor,
                    "resource": event_data.resource_type,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to publish audit event: {e}")
        
        return event
    
    async def get_events(
        self,
        db: AsyncSession,
        event_type: Optional[str] = None,
        action: Optional[str] = None,
        actor: Optional[str] = None,
        resource_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEventModel]:
        """Get audit events with filtering."""
        query = select(AuditEventModel).order_by(desc(AuditEventModel.created_at))
        
        if event_type:
            query = query.where(AuditEventModel.event_type == event_type)
        if action:
            query = query.where(AuditEventModel.action == action)
        if actor:
            query = query.where(AuditEventModel.actor == actor)
        if resource_type:
            query = query.where(AuditEventModel.resource_type == resource_type)
        if severity:
            query = query.where(AuditEventModel.severity == severity)
        
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_events_for_resource(
        self,
        db: AsyncSession,
        resource_type: str,
        resource_id: str,
        limit: int = 100
    ) -> List[AuditEventModel]:
        """Get events for a specific resource."""
        result = await db.execute(
            select(AuditEventModel)
            .where(AuditEventModel.resource_type == resource_type)
            .where(AuditEventModel.resource_id == resource_id)
            .order_by(desc(AuditEventModel.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_events_for_user(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 100
    ) -> List[AuditEventModel]:
        """Get events for a specific user."""
        result = await db.execute(
            select(AuditEventModel)
            .where(AuditEventModel.actor == user_id)
            .order_by(desc(AuditEventModel.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_stats(self, db: AsyncSession) -> dict:
        """Get audit statistics."""
        total = await db.execute(select(func.count(AuditEventModel.id)))
        total_count = total.scalar() or 0
        
        by_type = await db.execute(
            select(AuditEventModel.event_type, func.count(AuditEventModel.id))
            .group_by(AuditEventModel.event_type)
        )
        
        by_action = await db.execute(
            select(AuditEventModel.action, func.count(AuditEventModel.id))
            .group_by(AuditEventModel.action)
        )
        
        by_severity = await db.execute(
            select(AuditEventModel.severity, func.count(AuditEventModel.id))
            .group_by(AuditEventModel.severity)
        )
        
        return {
            "total_events": total_count,
            "by_type": {row[0]: row[1] for row in by_type.all()},
            "by_action": {row[0]: row[1] for row in by_action.all()},
            "by_severity": {row[0]: row[1] for row in by_severity.all()},
        }

_service = None

def get_audit_service(event_stream=None):
    global _service
    if _service is None:
        _service = AuditLoggingService(event_stream=event_stream)
    return _service
