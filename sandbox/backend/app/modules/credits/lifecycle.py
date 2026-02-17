"""
Credits Module Lifecycle Management.

Handles startup and shutdown of the Credits module, including:
- Event Sourcing initialization
- Event replay (crash recovery)
- Graceful shutdown

Usage (in main.py):
    from app.modules.credits.lifecycle import (
        startup_credits_module,
        shutdown_credits_module,
    )

    @app.on_event("startup")
    async def startup():
        await startup_credits_module()

    @app.on_event("shutdown")
    async def shutdown():
        await shutdown_credits_module()
"""

from __future__ import annotations

from loguru import logger

from app.modules.credits.service import initialize_event_sourcing


async def startup_credits_module() -> None:
    """
    Initialize Credits module on app startup.

    Steps:
    1. Initialize Event Sourcing system
    2. Replay existing events (crash recovery)
    3. Log startup metrics

    Note:
        - Gracefully handles missing Event Sourcing
        - Safe to call multiple times (idempotent)
        - Non-blocking (errors logged but don't crash app)
    """
    logger.info("Starting Credits module initialization...")

    try:
        # Initialize Event Sourcing (includes replay)
        await initialize_event_sourcing()
        logger.info("Credits module initialized successfully")

    except Exception as e:
        logger.error(
            f"Credits module initialization failed: {e}",
            exc_info=True,
        )
        # Don't crash app - Credits module is optional


async def shutdown_credits_module() -> None:
    """
    Shutdown Credits module gracefully.

    Note:
        - Currently no cleanup needed (in-memory projections)
        - Future: Close file handles, flush buffers, etc.
    """
    logger.info("Shutting down Credits module...")
    # Future: Add cleanup logic here
    logger.info("Credits module shut down successfully")
