"""
Agent Management System - Service Layer

Business logic for agent lifecycle management with EventStream integration.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AgentModel, AgentStatus
from .schemas import (
    AgentRegister, AgentUpdate, AgentHeartbeat,
    AgentResponse, AgentStats
)


class AgentService:
    """
    Agent management service with EventStream integration.
    
    Handles:
    - Agent registration and lifecycle
    - Heartbeat processing
    - Status monitoring and transitions
    - Event publishing
    """
    
    def __init__(self, event_stream=None):
        """Initialize agent service with optional EventStream"""
        self.event_stream = event_stream
        self._offline_threshold = 3  # Missed heartbeats before marking offline
        logger.info("🤖 Agent Service initialized")
    
    async def _publish_event(self, event_type: str, agent_id: str, data: Dict[str, Any] = None):
        """Publish event to EventStream if available"""
        if self.event_stream is None:
            return
        
        try:
            await self.event_stream.publish({
                "type": event_type,
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data or {}
            })
        except Exception as e:
            logger.warning(f"Failed to publish event {event_type}: {e}")
    
    # ========================================================================
    # Registration
    # ========================================================================
    
    async def register_agent(
        self,
        db: AsyncSession,
        registration: AgentRegister,
        host: Optional[str] = None,
        pid: Optional[int] = None
    ) -> AgentModel:
        """
        Register a new agent.
        
        Args:
            db: Database session
            registration: Agent registration data
            host: Agent host/IP
            pid: Agent process ID
            
        Returns:
            Registered agent model
        """
        # Check for existing agent with same ID
        result = await db.execute(
            select(AgentModel).where(AgentModel.agent_id == registration.agent_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning(f"Agent {registration.agent_id} already exists, updating registration")
            # Update existing agent
            existing.name = registration.name
            existing.description = registration.description
            existing.agent_type = registration.agent_type
            existing.version = registration.version
            existing.capabilities = registration.capabilities
            existing.config = registration.config
            existing.heartbeat_interval = registration.heartbeat_interval
            existing.status = AgentStatus.REGISTERED
            existing.missed_heartbeats = 0
            existing.host = host
            existing.pid = pid
            existing.registered_at = datetime.now(timezone.utc)
            existing.activated_at = None
            existing.terminated_at = None
            
            await db.commit()
            await db.refresh(existing)
            
            logger.info(f"🔄 Re-registered agent: {registration.agent_id}")
            await self._publish_event("agent.registered", registration.agent_id, {
                "name": registration.name,
                "type": registration.agent_type,
                "re_register": True
            })
            
            return existing
        
        # Create new agent
        agent = AgentModel(
            agent_id=registration.agent_id,
            name=registration.name,
            description=registration.description,
            status=AgentStatus.REGISTERED,
            agent_type=registration.agent_type,
            version=registration.version,
            capabilities=registration.capabilities,
            config=registration.config,
            heartbeat_interval=registration.heartbeat_interval,
            host=host,
            pid=pid,
        )
        
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        logger.info(f"✅ Registered new agent: {registration.agent_id} ({registration.name})")
        await self._publish_event("agent.registered", registration.agent_id, {
            "name": registration.name,
            "type": registration.agent_type,
            "capabilities": registration.capabilities
        })
        
        return agent
    
    # ========================================================================
    # Heartbeat & Status
    # ========================================================================
    
    async def process_heartbeat(
        self,
        db: AsyncSession,
        heartbeat: AgentHeartbeat,
        host: Optional[str] = None
    ) -> Optional[AgentModel]:
        """
        Process agent heartbeat.
        
        Args:
            db: Database session
            heartbeat: Heartbeat data
            host: Agent host/IP
            
        Returns:
            Updated agent model or None if not found
        """
        result = await db.execute(
            select(AgentModel).where(AgentModel.agent_id == heartbeat.agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            logger.warning(f"Heartbeat from unknown agent: {heartbeat.agent_id}")
            return None
        
        now = datetime.now(timezone.utc)
        previous_status = agent.status
        
        # Update heartbeat info
        agent.last_heartbeat = now
        agent.last_active_at = now
        agent.missed_heartbeats = 0
        agent.host = host or agent.host
        
        # Update metrics if provided
        if heartbeat.tasks_completed is not None:
            agent.tasks_completed = heartbeat.tasks_completed
        if heartbeat.tasks_failed is not None:
            agent.tasks_failed = heartbeat.tasks_failed
        if heartbeat.avg_task_duration_ms is not None:
            agent.avg_task_duration_ms = heartbeat.avg_task_duration_ms
        
        # Handle status transitions
        if previous_status == AgentStatus.REGISTERED:
            # First heartbeat - activate agent
            agent.status = AgentStatus.ACTIVE
            agent.activated_at = now
            logger.info(f"🚀 Agent {heartbeat.agent_id} activated")
            await self._publish_event("agent.activated", heartbeat.agent_id)
            
        elif previous_status in (AgentStatus.OFFLINE, AgentStatus.DEGRADED):
            # Recovery
            agent.status = AgentStatus.ACTIVE
            logger.info(f"✅ Agent {heartbeat.agent_id} recovered from {previous_status.value}")
            await self._publish_event("agent.recovered", heartbeat.agent_id, {
                "previous_status": previous_status.value
            })
            
        elif heartbeat.status != agent.status:
            # Agent reports different status
            agent.status = heartbeat.status
            if heartbeat.status == AgentStatus.DEGRADED:
                logger.warning(f"⚠️ Agent {heartbeat.agent_id} reports degraded status")
                await self._publish_event("agent.degraded", heartbeat.agent_id)
        
        await db.commit()
        await db.refresh(agent)
        
        # Publish heartbeat event (throttled - every 10th heartbeat)
        if agent.tasks_completed % 10 == 0:
            await self._publish_event("agent.heartbeat", heartbeat.agent_id, {
                "tasks_completed": agent.tasks_completed,
                "tasks_failed": agent.tasks_failed
            })
        
        return agent
    
    async def check_offline_agents(self, db: AsyncSession) -> List[AgentModel]:
        """
        Check for agents that have missed heartbeats.
        Marks them as offline if threshold exceeded.
        
        Returns:
            List of agents marked as offline
        """
        now = datetime.now(timezone.utc)
        offline_agents = []
        
        # Get all active/degraded agents
        result = await db.execute(
            select(AgentModel).where(
                AgentModel.status.in_([AgentStatus.ACTIVE, AgentStatus.DEGRADED])
            )
        )
        agents = result.scalars().all()
        
        for agent in agents:
            if agent.last_heartbeat is None:
                # Never sent a heartbeat since registration
                continue
                
            # Calculate expected heartbeat count since last heartbeat
            time_since_last = (now - agent.last_heartbeat).total_seconds()
            expected_heartbeats = time_since_last / agent.heartbeat_interval
            
            if expected_heartbeats > self._offline_threshold:
                # Agent missed too many heartbeats
                agent.status = AgentStatus.OFFLINE
                agent.missed_heartbeats = int(expected_heartbeats)
                offline_agents.append(agent)
                
                logger.warning(
                    f"🚫 Agent {agent.agent_id} marked offline "
                    f"(missed {int(expected_heartbeats)} heartbeats)"
                )
                await self._publish_event("agent.offline", agent.agent_id, {
                    "missed_heartbeats": int(expected_heartbeats),
                    "last_heartbeat": agent.last_heartbeat.isoformat()
                })
        
        if offline_agents:
            await db.commit()
        
        return offline_agents
    
    # ========================================================================
    # CRUD Operations
    # ========================================================================
    
    async def get_agents(
        self,
        db: AsyncSession,
        status: Optional[AgentStatus] = None,
        agent_type: Optional[str] = None,
    ) -> List[AgentModel]:
        """Get all agents with optional filtering"""
        query = select(AgentModel)
        
        if status:
            query = query.where(AgentModel.status == status)
        if agent_type:
            query = query.where(AgentModel.agent_type == agent_type)
        
        query = query.order_by(AgentModel.registered_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_agent(self, db: AsyncSession, agent_id: str) -> Optional[AgentModel]:
        """Get agent by agent_id"""
        result = await db.execute(
            select(AgentModel).where(AgentModel.agent_id == agent_id)
        )
        return result.scalar_one_or_none()
    
    async def get_agent_by_uuid(self, db: AsyncSession, uuid: UUID) -> Optional[AgentModel]:
        """Get agent by UUID"""
        result = await db.execute(
            select(AgentModel).where(AgentModel.id == uuid)
        )
        return result.scalar_one_or_none()
    
    async def update_agent(
        self,
        db: AsyncSession,
        agent_id: str,
        update: AgentUpdate
    ) -> Optional[AgentModel]:
        """Update agent properties"""
        agent = await self.get_agent(db, agent_id)
        if not agent:
            return None
        
        # Update fields
        if update.name is not None:
            agent.name = update.name
        if update.description is not None:
            agent.description = update.description
        if update.capabilities is not None:
            agent.capabilities = update.capabilities
        if update.config is not None:
            agent.config = update.config
        if update.heartbeat_interval is not None:
            agent.heartbeat_interval = update.heartbeat_interval
        
        await db.commit()
        await db.refresh(agent)
        
        logger.info(f"🔄 Updated agent: {agent_id}")
        return agent
    
    async def terminate_agent(
        self,
        db: AsyncSession,
        agent_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Gracefully terminate an agent.
        
        Args:
            db: Database session
            agent_id: Agent identifier
            reason: Termination reason
            
        Returns:
            True if terminated, False if not found
        """
        agent = await self.get_agent(db, agent_id)
        if not agent:
            return False
        
        agent.status = AgentStatus.TERMINATED
        agent.terminated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        logger.info(f"🛑 Terminated agent: {agent_id} - {reason or 'No reason given'}")
        await self._publish_event("agent.terminated", agent_id, {"reason": reason})
        
        return True
    
    async def delete_agent(self, db: AsyncSession, agent_id: str) -> bool:
        """Hard delete an agent (use with caution)"""
        agent = await self.get_agent(db, agent_id)
        if not agent:
            return False
        
        await db.delete(agent)
        await db.commit()
        
        logger.info(f"🗑️ Deleted agent: {agent_id}")
        return True
    
    # ========================================================================
    # Statistics
    # ========================================================================
    
    async def get_stats(self, db: AsyncSession) -> AgentStats:
        """Get agent statistics"""
        # Total count
        result = await db.execute(select(func.count(AgentModel.id)))
        total = result.scalar() or 0
        
        # By status
        result = await db.execute(
            select(AgentModel.status, func.count(AgentModel.id))
            .group_by(AgentModel.status)
        )
        status_counts = {row[0].value: row[1] for row in result.all()}
        
        # Task totals
        result = await db.execute(
            select(
                func.sum(AgentModel.tasks_completed),
                func.sum(AgentModel.tasks_failed)
            )
        )
        task_totals = result.one()
        
        return AgentStats(
            total_agents=total,
            active_count=status_counts.get("active", 0),
            offline_count=status_counts.get("offline", 0),
            degraded_count=status_counts.get("degraded", 0),
            total_tasks_completed=task_totals[0] or 0,
            total_tasks_failed=task_totals[1] or 0,
            avg_uptime_percent=None  # TODO: Calculate from heartbeat history
        )


# Singleton instance
_agent_service: Optional[AgentService] = None


def get_agent_service(event_stream=None) -> AgentService:
    """Get or create the agent service singleton"""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService(event_stream=event_stream)
    return _agent_service
