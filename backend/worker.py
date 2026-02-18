"""
BRAiN Worker Service

Horizontal skalierbare Worker für Cluster-Tasks.

Dieser Worker:
- Zieht Tasks aus Redis Queue
- Verarbeitet Cluster-Operations (spawn, scale, delegate)
- Unterstützt Graceful Shutdown
- Sendet Heartbeat an Redis
- Kann als N Replicas in Coolify laufen

Usage:
    python worker.py

Environment:
    REDIS_URL - Redis connection string
    DATABASE_URL - PostgreSQL connection string
    OLLAMA_HOST - Ollama endpoint
    WORKER_ID - Unique worker ID (auto-generated)
    WORKER_CONCURRENCY - Max parallel tasks (default: 2)
"""

import asyncio
import signal
import sys
import os
from loguru import logger

from app.workers.cluster_worker import ClusterWorker


# ===== GRACEFUL SHUTDOWN =====

shutdown_event = asyncio.Event()


def signal_handler(sig, frame):
    """Handle SIGINT and SIGTERM"""
    sig_name = signal.Signals(sig).name
    logger.warning(f"Received signal {sig_name}, initiating graceful shutdown...")
    shutdown_event.set()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ===== MAIN =====

async def main():
    """Main worker loop"""

    # Worker Configuration
    worker_id = os.getenv("WORKER_ID", os.getenv("HOSTNAME", "worker-unknown"))
    concurrency = int(os.getenv("WORKER_CONCURRENCY", "2"))
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    logger.info("=" * 60)
    logger.info("🚀 Starting BRAiN Worker")
    logger.info(f"Worker ID: {worker_id}")
    logger.info(f"Concurrency: {concurrency}")
    logger.info(f"Redis: {redis_url}")
    logger.info("=" * 60)

    # Initialize Worker
    worker = ClusterWorker(
        worker_id=worker_id,
        concurrency=concurrency,
        redis_url=redis_url
    )

    try:
        # Start Worker (blocks until shutdown)
        await worker.start()

        # Wait for shutdown signal
        await shutdown_event.wait()

        logger.info("Shutdown signal received, stopping worker...")

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")

    except Exception as e:
        logger.error(f"Worker crashed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Graceful Shutdown
        logger.info("Shutting down worker...")
        await worker.stop()
        logger.info("Worker stopped gracefully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        sys.exit(0)
