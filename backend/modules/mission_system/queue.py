"""
BRAIN Mission System V1 - Queue Management
==========================================

Redis-based queue system for mission orchestration and task distribution.
Implements priority queues with support for delayed execution and agent affinity.

Key Features:
- Priority-based task scheduling
- Agent assignment tracking
- Dead letter queue for failed missions
- Mission state persistence
- Real-time queue monitoring

Architecture:
- Redis Streams for reliable message delivery
- Sorted sets for priority queuing
- Hash maps for mission state storage
- Pub/Sub for real-time notifications

Author: Claude (Chief Developer)
Project: BRAIN Framework by FalkLabs / Olaf Falk
"""

import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import redis.asyncio as redis
from redis.exceptions import RedisError

from .models import (
    Mission, MissionQueue, MissionStatus, MissionPriority, 
    MissionTask, MissionLog
)


logger = logging.getLogger(__name__)


class MissionQueueManager:
    """
    Manages mission queues using Redis as the backend storage.
    Provides reliable, priority-based task distribution.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize the queue manager with Redis connection.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
        # Queue names following BRAIN naming convention
        self.MISSION_QUEUE = "brain:missions:queue"
        self.MISSION_STATE = "brain:missions:state"
        self.MISSION_STREAM = "brain:missions:stream"
        self.AGENT_ASSIGNMENTS = "brain:agents:assignments"
        self.DEAD_LETTER_QUEUE = "brain:missions:dlq"
        self.QUEUE_STATS = "brain:missions:stats"
        
        # Configuration
        self.MAX_RETRIES = 3
        self.VISIBILITY_TIMEOUT = 300  # 5 minutes
        self.DLQ_THRESHOLD = 5  # Move to DLQ after 5 failures
        
    async def connect(self) -> None:
        """Establish connection to Redis"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis_client.ping()
            logger.info("Successfully connected to Redis")
            
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def enqueue_mission(self, mission: Mission) -> bool:
        """
        Add a mission to the queue with priority ordering.
        
        Args:
            mission: Mission to enqueue
            
        Returns:
            True if successfully enqueued
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            # Create queue entry
            queue_entry = MissionQueue(
                mission_id=mission.id,
                priority=mission.priority,
                estimated_start=datetime.utcnow() + timedelta(seconds=30)
            )
            
            # Store mission state
            await self.redis_client.hset(
                self.MISSION_STATE,
                mission.id,
                mission.json()
            )
            
            # Add to priority queue (higher priority = lower score for Redis)
            priority_score = 10 - mission.priority.value
            await self.redis_client.zadd(
                self.MISSION_QUEUE,
                {mission.id: priority_score}
            )
            
            # Add to stream for real-time processing
            stream_data = {
                "mission_id": mission.id,
                "priority": mission.priority.value,
                "type": mission.mission_type.value,
                "created_at": mission.created_at.isoformat(),
                "agent_requirements": json.dumps(mission.agent_requirements.dict())
            }
            
            await self.redis_client.xadd(self.MISSION_STREAM, stream_data)
            
            # Update statistics
            await self._update_queue_stats("enqueued", mission.mission_type.value)
            
            # Log the enqueue operation
            await self._log_mission_event(
                mission.id,
                "INFO",
                f"Mission {mission.name} enqueued with priority {mission.priority.value}"
            )
            
            logger.info(f"Mission {mission.id} enqueued successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue mission {mission.id}: {e}")
            return False
    
    async def dequeue_mission(self, agent_id: str, agent_capabilities: List[str]) -> Optional[Mission]:
        """
        Get the highest priority mission that matches agent capabilities.
        
        Args:
            agent_id: ID of the requesting agent
            agent_capabilities: List of agent's capabilities
            
        Returns:
            Mission object if found and assigned, None otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            # Get highest priority missions (lowest scores)
            mission_candidates = await self.redis_client.zrange(
                self.MISSION_QUEUE, 0, 9, withscores=True
            )
            
            for mission_id, priority_score in mission_candidates:
                # Get full mission data
                mission_data = await self.redis_client.hget(self.MISSION_STATE, mission_id)
                if not mission_data:
                    # Clean up orphaned queue entry
                    await self.redis_client.zrem(self.MISSION_QUEUE, mission_id)
                    continue
                
                try:
                    mission = Mission.parse_raw(mission_data)
                except Exception as e:
                    logger.error(f"Failed to parse mission {mission_id}: {e}")
                    continue
                
                # Check if agent meets requirements
                if self._agent_matches_requirements(agent_capabilities, mission.agent_requirements):
                    # Try to assign mission atomically
                    assigned = await self._assign_mission_to_agent(mission.id, agent_id)
                    if assigned:
                        # Remove from queue
                        await self.redis_client.zrem(self.MISSION_QUEUE, mission_id)
                        
                        # Update mission status
                        mission.status = MissionStatus.ASSIGNED
                        mission.assigned_agent_id = agent_id
                        mission.assigned_agents = [agent_id]
                        mission.updated_at = datetime.utcnow()
                        
                        # Store updated mission state
                        await self.redis_client.hset(
                            self.MISSION_STATE,
                            mission.id,
                            mission.json()
                        )
                        
                        # Update statistics
                        await self._update_queue_stats("assigned", mission.mission_type.value)
                        
                        # Log assignment
                        await self._log_mission_event(
                            mission.id,
                            "INFO",
                            f"Mission assigned to agent {agent_id}"
                        )
                        
                        logger.info(f"Mission {mission.id} assigned to agent {agent_id}")
                        return mission
            
            # No suitable missions found
            return None
            
        except Exception as e:
            logger.error(f"Failed to dequeue mission for agent {agent_id}: {e}")
            return None
    
    async def update_mission_status(
        self, 
        mission_id: str, 
        status: MissionStatus, 
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update mission status and store results.
        
        Args:
            mission_id: Mission to update
            status: New status
            result: Mission result data
            error_message: Error details if failed
            
        Returns:
            True if successfully updated
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            # Get current mission
            mission_data = await self.redis_client.hget(self.MISSION_STATE, mission_id)
            if not mission_data:
                logger.warning(f"Mission {mission_id} not found in state store")
                return False
            
            mission = Mission.parse_raw(mission_data)
            
            # Update status and timing
            old_status = mission.status
            mission.status = status
            mission.updated_at = datetime.utcnow()
            
            if status == MissionStatus.RUNNING and not mission.started_at:
                mission.started_at = datetime.utcnow()
            elif status in [MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED]:
                mission.completed_at = datetime.utcnow()
                
                # Remove from agent assignments
                if mission.assigned_agent_id:
                    await self.redis_client.hdel(
                        self.AGENT_ASSIGNMENTS, 
                        mission.assigned_agent_id
                    )
            
            # Store results
            if result:
                mission.result = result
            if error_message:
                mission.error_message = error_message
            
            # Handle failures - implement retry logic
            if status == MissionStatus.FAILED:
                await self._handle_mission_failure(mission)
            
            # Store updated mission
            await self.redis_client.hset(
                self.MISSION_STATE,
                mission_id,
                mission.json()
            )
            
            # Update statistics
            await self._update_queue_stats("status_change", mission.mission_type.value)
            await self._update_queue_stats(status.value, mission.mission_type.value)
            
            # Log status change
            await self._log_mission_event(
                mission_id,
                "INFO",
                f"Mission status changed from {old_status.value} to {status.value}"
            )
            
            logger.info(f"Mission {mission_id} status updated to {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update mission {mission_id} status: {e}")
            return False
    
    async def get_queue_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive queue statistics.
        
        Returns:
            Dictionary containing queue metrics
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            # Queue lengths
            pending_count = await self.redis_client.zcard(self.MISSION_QUEUE)
            dlq_count = await self.redis_client.zcard(self.DEAD_LETTER_QUEUE)
            
            # Active assignments
            active_assignments = await self.redis_client.hlen(self.AGENT_ASSIGNMENTS)
            
            # Stream length
            stream_info = await self.redis_client.xinfo_stream(self.MISSION_STREAM)
            stream_length = stream_info.get("length", 0)
            
            # Get stored statistics
            stats_data = await self.redis_client.hgetall(self.QUEUE_STATS)
            
            return {
                "queue_lengths": {
                    "pending": pending_count,
                    "dead_letter": dlq_count,
                    "stream": stream_length
                },
                "active_assignments": active_assignments,
                "statistics": stats_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue statistics: {e}")
            return {}
    
    async def get_mission_logs(self, mission_id: str, limit: int = 100) -> List[MissionLog]:
        """
        Get logs for a specific mission.
        
        Args:
            mission_id: Mission to get logs for
            limit: Maximum number of logs to return
            
        Returns:
            List of mission logs
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            # Get logs from stream
            log_key = f"brain:missions:logs:{mission_id}"
            logs = await self.redis_client.xrevrange(log_key, count=limit)
            
            mission_logs = []
            for log_id, fields in logs:
                log_entry = MissionLog(
                    log_id=log_id,
                    mission_id=mission_id,
                    task_id=fields.get("task_id"),
                    timestamp=datetime.fromisoformat(fields.get("timestamp", datetime.utcnow().isoformat())),
                    level=fields.get("level", "INFO"),
                    message=fields.get("message", ""),
                    agent_id=fields.get("agent_id"),
                    data=json.loads(fields.get("data", "{}")) if fields.get("data") else None
                )
                mission_logs.append(log_entry)
            
            return mission_logs
            
        except Exception as e:
            logger.error(f"Failed to get logs for mission {mission_id}: {e}")
            return []
    
    def _agent_matches_requirements(
        self, 
        agent_capabilities: List[str], 
        requirements: Any
    ) -> bool:
        """
        Check if agent capabilities match mission requirements.
        
        Args:
            agent_capabilities: Agent's capabilities
            requirements: Mission requirements
            
        Returns:
            True if agent is suitable
        """
        # Simple capability matching - can be enhanced with KARMA scoring
        required_skills = getattr(requirements, 'skills_required', [])
        
        if not required_skills:
            return True  # No specific requirements
        
        # Check if agent has all required skills
        return all(skill in agent_capabilities for skill in required_skills)
    
    async def _assign_mission_to_agent(self, mission_id: str, agent_id: str) -> bool:
        """
        Atomically assign mission to agent.
        
        Args:
            mission_id: Mission to assign
            agent_id: Agent to assign to
            
        Returns:
            True if successfully assigned
        """
        try:
            # Use Redis transaction to ensure atomicity
            async with self.redis_client.pipeline(transaction=True) as pipe:
                # Check if agent is already assigned to another mission
                current_assignment = await pipe.hget(self.AGENT_ASSIGNMENTS, agent_id)
                if current_assignment:
                    return False  # Agent is busy
                
                # Assign mission
                await pipe.hset(self.AGENT_ASSIGNMENTS, agent_id, mission_id)
                await pipe.execute()
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to assign mission {mission_id} to agent {agent_id}: {e}")
            return False
    
    async def _handle_mission_failure(self, mission: Mission) -> None:
        """
        Handle mission failure with retry logic.
        
        Args:
            mission: Failed mission
        """
        # Increment failure count
        failure_key = f"brain:missions:failures:{mission.id}"
        failure_count = await self.redis_client.incr(failure_key)
        
        if failure_count >= self.DLQ_THRESHOLD:
            # Move to dead letter queue
            await self.redis_client.zadd(
                self.DEAD_LETTER_QUEUE,
                {mission.id: datetime.utcnow().timestamp()}
            )
            
            await self._log_mission_event(
                mission.id,
                "ERROR",
                f"Mission moved to dead letter queue after {failure_count} failures"
            )
            
        else:
            # Re-queue for retry after delay
            retry_delay = 60 * (2 ** failure_count)  # Exponential backoff
            retry_score = datetime.utcnow().timestamp() + retry_delay
            
            await self.redis_client.zadd(
                self.MISSION_QUEUE,
                {mission.id: retry_score}
            )
            
            await self._log_mission_event(
                mission.id,
                "WARNING",
                f"Mission requeued for retry #{failure_count} after {retry_delay}s delay"
            )
    
    async def _update_queue_stats(self, stat_name: str, mission_type: str) -> None:
        """
        Update queue statistics.
        
        Args:
            stat_name: Name of the statistic to update
            mission_type: Type of mission for categorization
        """
        try:
            # Overall stats
            await self.redis_client.hincrby(self.QUEUE_STATS, f"total_{stat_name}", 1)
            
            # Type-specific stats
            await self.redis_client.hincrby(
                self.QUEUE_STATS, 
                f"{mission_type}_{stat_name}", 
                1
            )
            
            # Update timestamp
            await self.redis_client.hset(
                self.QUEUE_STATS,
                "last_updated",
                datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to update queue stats: {e}")
    
    async def _log_mission_event(
        self, 
        mission_id: str, 
        level: str, 
        message: str,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log mission events to Redis stream.
        
        Args:
            mission_id: Mission ID
            level: Log level
            message: Log message
            agent_id: Agent involved (optional)
            task_id: Task involved (optional)
            data: Additional data (optional)
        """
        try:
            log_key = f"brain:missions:logs:{mission_id}"
            log_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": level,
                "message": message
            }
            
            if agent_id:
                log_data["agent_id"] = agent_id
            if task_id:
                log_data["task_id"] = task_id
            if data:
                log_data["data"] = json.dumps(data)
            
            await self.redis_client.xadd(log_key, log_data)
            
            # Set TTL for log cleanup (30 days)
            await self.redis_client.expire(log_key, 30 * 24 * 60 * 60)
            
        except Exception as e:
            logger.error(f"Failed to log mission event: {e}")


# Global queue manager instance
queue_manager = MissionQueueManager()


# Helper functions for easy access
async def enqueue_mission(mission: Mission) -> bool:
    """Convenience function to enqueue a mission"""
    return await queue_manager.enqueue_mission(mission)


async def dequeue_mission(agent_id: str, capabilities: List[str]) -> Optional[Mission]:
    """Convenience function to dequeue a mission"""
    return await queue_manager.dequeue_mission(agent_id, capabilities)


async def update_mission_status(
    mission_id: str, 
    status: MissionStatus,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> bool:
    """Convenience function to update mission status"""
    return await queue_manager.update_mission_status(mission_id, status, result, error_message)
