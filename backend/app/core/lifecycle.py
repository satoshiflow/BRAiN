import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .logging import configure_logging
from .config import get_settings
from .redis_client import get_redis

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    logger.info("Starting BRAiN Core", extra={"env": settings.environment})

    # Trigger lazy init for Redis
    redis = await get_redis()
    await redis.ping()
    logger.info("Redis connection established")

    yield

    # Shutdown
    await redis.close()
    logger.info("BRAiN Core shutdown complete")
