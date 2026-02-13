"""
🎯 BRAIN Mission Control - Task Queue System
Bio-Inspired Multi-Agent Task Management

Philosophy: Myzelkapitalismus
- Fair resource distribution through priority queues
- Cooperative task delegation based on agent capabilities
- Self-healing task recovery and retry mechanisms
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import logging
from dataclasses import dataclass, asdict
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task lifecycle states"""
    PENDING = "pending"      # Created, waiting to be queued
    QUEUED = "queued"        # In priority queue, waiting for agent
    ASSIGNED = "assigned"    # Assigned to agent, not yet started
    RUNNING = "running"      # Currently being executed
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"        # Failed execution
    CANCELLED = "cancelled"  # Manually cancelled
    RETRYING = "retrying"    # Failed but retrying


class TaskPriority(str, Enum):
    """Task priority levels - Myzel-inspired fair distribution"""
    LOW = "low"         # Background tasks (weight: 1)
    NORMAL = "normal"   # Standard tasks (weight: 10)
    HIGH = "high"       # Important tasks (weight: 100)
    URGENT = "urgent"   # Critical tasks (weight: 1000)


@dataclass
class Task:
    """Task data structure"""
    id: str
    mission_id: str
    task_type: str
    agent_type: Optional[str]
    payload: Dict[str, Any]
    priority: TaskPriority
    status: TaskStatus
    assigned_agent_id: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    dependencies: List[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        if self.dependencies is None:
            self.dependencies = []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task for Redis storage"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Deserialize task from Redis"""
        # Convert ISO strings back to datetime objects
        datetime_fields = ['created_at', 'updated_at', 'started_at', 'completed_at']
        for field in datetime_fields:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        return cls(**data)

    def can_retry(self) -> bool:
        """Check if task can be retried"""
        return self.retry_count < self.max_retries and self.status == TaskStatus.FAILED


class TaskQueue:
    """
    Redis-based Task Queue with Myzelkapitalismus principles
    - Fair distribution through weighted priority queues
    - Agent capability matching
    - Self-healing retry mechanisms
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self._initialized = False
        
        # Redis key patterns
        self.keys = {
            'task': 'brain:task:{}',                    # Individual task data
            'queue': 'brain:queue:{}',                  # Priority queues (sorted sets)
            'assigned': 'brain:assigned:{}',            # Agent assigned tasks
            'running': 'brain:running',                 # Currently running tasks
            'completed': 'brain:completed',             # Completed tasks (TTL)
            'failed': 'brain:failed',                   # Failed tasks (TTL)
            'mission_tasks': 'brain:mission:{}:tasks',  # Tasks per mission
            'dependencies': 'brain:dependencies:{}',    # Task dependencies
            'agent_tasks': 'brain:agent:{}:tasks',      # Tasks per agent
        }

    async def initialize(self) -> None:
        """Initialize Redis connection and create indices"""
        if self._initialized:
            return
            
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            await self.redis.ping()
            logger.info("Task Queue initialized successfully")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Task Queue: {e}")
            raise

    async def enqueue_task(self, task: Task) -> bool:
        """
        Add task to priority queue
        Returns True if successfully queued
        """
        try:
            # Store task data
            task_key = self.keys['task'].format(task.id)
            await self.redis.hset(task_key, mapping=task.to_dict())
            
            # Add to priority queue with weight-based scoring
            priority_weights = {
                TaskPriority.LOW: 1,
                TaskPriority.NORMAL: 10, 
                TaskPriority.HIGH: 100,
                TaskPriority.URGENT: 1000
            }
            score = priority_weights[task.priority] + int(task.created_at.timestamp())
            
            queue_key = self.keys['queue'].format(task.priority.value)
            await self.redis.zadd(queue_key, {task.id: score})
            
            # Add to mission tasks index
            mission_key = self.keys['mission_tasks'].format(task.mission_id)
            await self.redis.sadd(mission_key, task.id)
            
            # Update task status
            task.status = TaskStatus.QUEUED
            task.updated_at = datetime.utcnow()
            await self._update_task(task)
            
            logger.info(f"Task {task.id} queued with priority {task.priority.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue task {task.id}: {e}")
            return False

    async def dequeue_task(self, agent_id: str, agent_capabilities: Set[str]) -> Optional[Task]:
        """
        Dequeue highest priority task matching agent capabilities
        Myzel principle: Optimal resource allocation
        """
        try:
            # Check priority queues in order (URGENT -> HIGH -> NORMAL -> LOW)
            for priority in [TaskPriority.URGENT, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
                queue_key = self.keys['queue'].format(priority.value)
                
                # Get tasks from this priority level
                task_ids = await self.redis.zrange(queue_key, 0, 9)  # Top 10 tasks
                
                for task_id in task_ids:
                    task = await self.get_task(task_id)
                    if not task:
                        continue
                        
                    # Check if agent can handle this task type
                    if task.agent_type and task.agent_type not in agent_capabilities:
                        continue
                        
                    # Check dependencies
                    if not await self._dependencies_met(task):
                        continue
                        
                    # Assign task to agent
                    if await self._assign_task_to_agent(task, agent_id):
                        return task
                        
            return None  # No suitable tasks found
            
        except Exception as e:
            logger.error(f"Failed to dequeue task for agent {agent_id}: {e}")
            return None

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task by ID"""
        try:
            task_key = self.keys['task'].format(task_id)
            task_data = await self.redis.hgetall(task_key)
            
            if not task_data:
                return None
                
            return Task.from_dict(task_data)
            
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    async def update_task_status(self, task_id: str, status: TaskStatus, 
                               result: Optional[Dict[str, Any]] = None,
                               error: Optional[str] = None) -> bool:
        """Update task status and optional result/error"""
        try:
            task = await self.get_task(task_id)
            if not task:
                return False
                
            old_status = task.status
            task.status = status
            task.updated_at = datetime.utcnow()
            
            if status == TaskStatus.RUNNING and old_status == TaskStatus.ASSIGNED:
                task.started_at = datetime.utcnow()
                
            elif status == TaskStatus.COMPLETED:
                task.completed_at = datetime.utcnow()
                task.result = result
                
            elif status == TaskStatus.FAILED:
                task.completed_at = datetime.utcnow()
                task.error = error
                
            await self._update_task(task)
            
            # Update indices based on status
            await self._update_task_indices(task, old_status)
            
            logger.info(f"Task {task_id} status updated: {old_status} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id} status: {e}")
            return False

    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        try:
            task = await self.get_task(task_id)
            if not task or not task.can_retry():
                return False
                
            # Increment retry count
            task.retry_count += 1
            task.status = TaskStatus.RETRYING
            task.assigned_agent_id = None
            task.error = None
            task.updated_at = datetime.utcnow()
            
            await self._update_task(task)
            
            # Re-queue the task
            await self.enqueue_task(task)
            
            logger.info(f"Task {task_id} retry {task.retry_count}/{task.max_retries}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry task {task_id}: {e}")
            return False

    async def get_mission_tasks(self, mission_id: str) -> List[Task]:
        """Get all tasks for a mission"""
        try:
            mission_key = self.keys['mission_tasks'].format(mission_id)
            task_ids = await self.redis.smembers(mission_key)
            
            tasks = []
            for task_id in task_ids:
                task = await self.get_task(task_id)
                if task:
                    tasks.append(task)
                    
            return sorted(tasks, key=lambda t: t.created_at)
            
        except Exception as e:
            logger.error(f"Failed to get tasks for mission {mission_id}: {e}")
            return []

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics for monitoring"""
        try:
            stats = {}
            
            for priority in TaskPriority:
                queue_key = self.keys['queue'].format(priority.value)
                count = await self.redis.zcard(queue_key)
                stats[f"{priority.value}_queue"] = count
                
            stats['running_tasks'] = await self.redis.scard(self.keys['running'])
            stats['completed_tasks'] = await self.redis.scard(self.keys['completed'])
            stats['failed_tasks'] = await self.redis.scard(self.keys['failed'])
            stats['timestamp'] = datetime.utcnow().isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}

    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed tasks (Myzel principle: Resource efficiency)"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
            cutoff_timestamp = cutoff.isoformat()
            cleaned = 0
            
            # Clean completed tasks
            completed_tasks = await self.redis.smembers(self.keys['completed'])
            for task_id in completed_tasks:
                task = await self.get_task(task_id)
                if task and task.completed_at and task.completed_at < cutoff:
                    await self._delete_task(task_id)
                    cleaned += 1
                    
            # Clean failed tasks
            failed_tasks = await self.redis.smembers(self.keys['failed'])
            for task_id in failed_tasks:
                task = await self.get_task(task_id)
                if task and task.completed_at and task.completed_at < cutoff:
                    await self._delete_task(task_id)
                    cleaned += 1
                    
            logger.info(f"Cleaned up {cleaned} old tasks")
            return cleaned
            
        except Exception as e:
            logger.error(f"Failed to cleanup old tasks: {e}")
            return 0

    # Private helper methods
    
    async def _update_task(self, task: Task) -> None:
        """Update task data in Redis"""
        task_key = self.keys['task'].format(task.id)
        await self.redis.hset(task_key, mapping=task.to_dict())

    async def _assign_task_to_agent(self, task: Task, agent_id: str) -> bool:
        """Assign task to agent atomically"""
        try:
            # Remove from queue
            queue_key = self.keys['queue'].format(task.priority.value)
            removed = await self.redis.zrem(queue_key, task.id)
            
            if removed == 0:
                return False  # Task was already taken
                
            # Assign to agent
            task.assigned_agent_id = agent_id
            task.status = TaskStatus.ASSIGNED
            task.updated_at = datetime.utcnow()
            
            await self._update_task(task)
            
            # Add to agent's assigned tasks
            agent_key = self.keys['agent_tasks'].format(agent_id)
            await self.redis.sadd(agent_key, task.id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign task {task.id} to agent {agent_id}: {e}")
            return False

    async def _dependencies_met(self, task: Task) -> bool:
        """Check if all task dependencies are completed"""
        if not task.dependencies:
            return True
            
        for dep_task_id in task.dependencies:
            dep_task = await self.get_task(dep_task_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
                
        return True

    async def _update_task_indices(self, task: Task, old_status: TaskStatus) -> None:
        """Update Redis indices based on status changes"""
        # Remove from old status set
        if old_status == TaskStatus.RUNNING:
            await self.redis.srem(self.keys['running'], task.id)
        elif old_status == TaskStatus.COMPLETED:
            await self.redis.srem(self.keys['completed'], task.id)
        elif old_status == TaskStatus.FAILED:
            await self.redis.srem(self.keys['failed'], task.id)
            
        # Add to new status set
        if task.status == TaskStatus.RUNNING:
            await self.redis.sadd(self.keys['running'], task.id)
        elif task.status == TaskStatus.COMPLETED:
            await self.redis.sadd(self.keys['completed'], task.id)
        elif task.status == TaskStatus.FAILED:
            await self.redis.sadd(self.keys['failed'], task.id)

    async def _delete_task(self, task_id: str) -> None:
        """Completely remove task from Redis"""
        task = await self.get_task(task_id)
        if not task:
            return
            
        # Remove from all possible sets/indices
        await self.redis.delete(self.keys['task'].format(task_id))
        await self.redis.srem(self.keys['running'], task_id)
        await self.redis.srem(self.keys['completed'], task_id)
        await self.redis.srem(self.keys['failed'], task_id)
        
        if task.assigned_agent_id:
            agent_key = self.keys['agent_tasks'].format(task.assigned_agent_id)
            await self.redis.srem(agent_key, task_id)
            
        mission_key = self.keys['mission_tasks'].format(task.mission_id)
        await self.redis.srem(mission_key, task_id)


# Export public interface
__all__ = ['TaskQueue', 'Task', 'TaskStatus', 'TaskPriority']
