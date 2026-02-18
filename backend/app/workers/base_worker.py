"""
Base Worker Class

Provides common functionality for all worker types:
- Redis queue connection
- Task dequeuing
- Concurrency control
- Heartbeat
- Graceful shutdown
"""

import asyncio
import redis.asyncio as redis
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
import json


class BaseWorker:
    """
    Base class for all BRAiN workers.

    Subclasses must implement:
    - process_task(task: dict) -> dict
    """

    def __init__(
        self,
        worker_id: str,
        concurrency: int = 2,
        redis_url: str = "redis://localhost:6379/0",
        queue_name: str = "brain:tasks"
    ):
        self.worker_id = worker_id
        self.concurrency = concurrency
        self.redis_url = redis_url
        self.queue_name = queue_name

        # State
        self.redis: Optional[redis.Redis] = None
        self.is_running = False
        self.tasks_processed = 0
        self.tasks_failed = 0

        # Concurrency control
        self.semaphore = asyncio.Semaphore(concurrency)

        logger.info(f"Initialized {self.__class__.__name__}: {worker_id}")

    # ===== LIFECYCLE =====

    async def start(self):
        """Start worker (blocking)"""
        logger.info(f"Starting worker {self.worker_id}...")

        # Connect to Redis
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis.ping()
        logger.info("Redis connection established")

        self.is_running = True

        # Start background tasks
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        process_task = asyncio.create_task(self._process_loop())

        # Run until stopped
        await asyncio.gather(heartbeat_task, process_task)

    async def stop(self):
        """Graceful shutdown"""
        logger.info(f"Stopping worker {self.worker_id}...")
        self.is_running = False

        # Wait for current tasks to finish (max 30 seconds)
        for i in range(30):
            if self.semaphore._value == self.concurrency:
                logger.info("All tasks completed")
                break
            logger.info(f"Waiting for {self.concurrency - self.semaphore._value} tasks to complete...")
            await asyncio.sleep(1)

        # Close Redis connection
        if self.redis:
            await self.redis.close()

        logger.info(f"Worker stopped. Processed: {self.tasks_processed}, Failed: {self.tasks_failed}")

    # ===== TASK PROCESSING =====

    async def _process_loop(self):
        """Main task processing loop"""
        logger.info(f"Worker {self.worker_id} ready to process tasks")

        while self.is_running:
            try:
                # Blocking pop with timeout (BLPOP)
                result = await self.redis.blpop(self.queue_name, timeout=5)

                if not result:
                    # Timeout, no tasks in queue
                    continue

                # Parse task
                _, task_json = result
                task = json.loads(task_json)

                # Process with concurrency limit
                async with self.semaphore:
                    await self._handle_task(task)

            except asyncio.CancelledError:
                logger.info("Process loop cancelled")
                break

            except Exception as e:
                logger.error(f"Process loop error: {e}", exc_info=True)
                await asyncio.sleep(1)  # Backoff

    async def _handle_task(self, task: Dict[str, Any]):
        """Handle single task with error handling"""
        task_id = task.get("id", "unknown")
        task_type = task.get("type", "unknown")

        logger.info(f"Processing task {task_id} (type: {task_type})")

        try:
            # Call subclass implementation
            result = await self.process_task(task)

            self.tasks_processed += 1
            logger.info(f"Task {task_id} completed successfully")

            # Publish success event
            await self._publish_result(task_id, result, success=True)

        except Exception as e:
            self.tasks_failed += 1
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)

            # Publish failure event
            await self._publish_result(task_id, {"error": str(e)}, success=False)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process single task (MUST be implemented by subclass).

        Args:
            task: Task dictionary with id, type, payload

        Returns:
            dict: Task result

        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError(f"{self.__class__.__name__}.process_task must be implemented")

    # ===== HEARTBEAT =====

    async def _heartbeat_loop(self):
        """Send heartbeat to Redis every 30 seconds"""
        while self.is_running:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                logger.info("Heartbeat loop cancelled")
                break

            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)

    async def _send_heartbeat(self):
        """Send heartbeat to Redis"""
        heartbeat_data = {
            "worker_id": self.worker_id,
            "timestamp": datetime.utcnow().isoformat(),
            "tasks_processed": self.tasks_processed,
            "tasks_failed": self.tasks_failed,
            "active_tasks": self.concurrency - self.semaphore._value
        }

        # Store with 60 second TTL
        await self.redis.setex(
            f"brain:worker:{self.worker_id}:heartbeat",
            60,
            json.dumps(heartbeat_data)
        )

    # ===== RESULTS =====

    async def _publish_result(
        self,
        task_id: str,
        result: Dict[str, Any],
        success: bool
    ):
        """Publish task result to Redis"""
        result_data = {
            "task_id": task_id,
            "worker_id": self.worker_id,
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
            "result": result
        }

        # Publish to results channel
        await self.redis.publish(
            "brain:task_results",
            json.dumps(result_data)
        )

        # Store result with 1 hour TTL
        await self.redis.setex(
            f"brain:task:{task_id}:result",
            3600,
            json.dumps(result_data)
        )
