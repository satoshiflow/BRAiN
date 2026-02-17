"""
Redis Queue Utilities

Helper functions for task queue operations.
"""

import redis.asyncio as redis
import json
from typing import Dict, Any
from datetime import datetime
import uuid
from loguru import logger


class TaskQueue:
    """
    Task queue interface for BRAiN workers.

    Usage:
        queue = TaskQueue(redis_url)
        await queue.push_task("spawn_agent", {"cluster_id": "..."})
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis: redis.Redis = None

    async def connect(self):
        """Connect to Redis"""
        if not self.redis:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            logger.info("TaskQueue connected to Redis")

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()

    async def push_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        queue_name: str = "brain:cluster_tasks"
    ) -> str:
        """
        Push task to queue.

        Args:
            task_type: Type of task (e.g., "spawn_agent")
            payload: Task payload
            queue_name: Target queue

        Returns:
            str: Task ID
        """
        if not self.redis:
            await self.connect()

        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "type": task_type,
            "payload": payload,
            "created_at": datetime.utcnow().isoformat()
        }

        # Push to queue (RPUSH = append to right)
        await self.redis.rpush(queue_name, json.dumps(task))

        logger.info(f"Task {task_id} ({task_type}) pushed to {queue_name}")
        return task_id

    async def get_queue_length(self, queue_name: str = "brain:cluster_tasks") -> int:
        """Get number of tasks waiting in queue"""
        if not self.redis:
            await self.connect()

        return await self.redis.llen(queue_name)

    async def get_task_result(
        self,
        task_id: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Wait for task result (blocking).

        Args:
            task_id: Task ID
            timeout: Max wait time in seconds

        Returns:
            dict: Task result

        Raises:
            TimeoutError: If result not received within timeout
        """
        if not self.redis:
            await self.connect()

        result_key = f"brain:task:{task_id}:result"

        # Poll for result
        for i in range(timeout):
            result_json = await self.redis.get(result_key)
            if result_json:
                return json.loads(result_json)

            await asyncio.sleep(1)

        raise TimeoutError(f"Task {task_id} result not received within {timeout}s")
