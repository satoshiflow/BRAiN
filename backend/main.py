# backend/main.py
"""
BRAiN Core Backend v0.3.0
Unified entry point - consolidates previous backend/main.py and backend/app/main.py

CHANGELOG v0.3.0:
- Merged dual entry points into single main.py
- Modern lifespan context manager (replaces deprecated @app.on_event)
- Unified auto-discovery for both backend/api/routes/* and app/api/routes/*
- Explicit inclusion of all app module routers
- Mission worker integrated into lifespan
- Settings-based configuration
"""

from __future__ import annotations

import os
import importlib
import pkgutil
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

# Core infrastructure
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.redis_client import get_redis

# Mission worker (from old backend/main.py)
from backend.modules.missions.worker import start_mission_worker, stop_mission_worker

# Event Stream (ADR-001: REQUIRED core infrastructure)
try:
    from backend.mission_control_core.core.event_stream import EventStream
except ImportError as e:
    # Check if degraded mode is explicitly allowed (Dev/CI only)
    if os.getenv("BRAIN_EVENTSTREAM_MODE", "required").lower() == "degraded":
        EventStream = None  # type: ignore
        import warnings
        warnings.warn(
            "DEGRADED MODE: EventStream unavailable. This violates ADR-001 in production.",
            RuntimeWarning
        )
    else:
        # FATAL: EventStream is required per ADR-001
        raise RuntimeError(
            f"EventStream is required core infrastructure (ADR-001). "
            f"mission_control_core must be available. ImportError: {e}"
        ) from e

# Legacy supervisor router (from old backend/main.py)
from backend.modules.supervisor.router import router as supervisor_router

# App module routers (from app/main.py)
from app.modules.dna.router import router as dna_router
from app.modules.karma.router import router as karma_router
from app.modules.immune.router import router as immune_router
from app.modules.credits.router import router as credits_router
from app.modules.policy.router import router as policy_router
from app.modules.threats.router import router as threats_router
from app.modules.supervisor.router import router as app_supervisor_router
from app.modules.missions.router import router as app_missions_router
from app.modules.foundation.router import router as foundation_router
from app.modules.sovereign_mode.router import router as sovereign_mode_router
from app.modules.dmz_control.router import router as dmz_control_router
from app.modules.course_factory.router import router as course_factory_router
from app.modules.course_factory.monetization_router import router as monetization_router
from app.modules.course_distribution.distribution_router import router as distribution_router
from app.modules.governance.governance_router import router as governance_router

logger = logging.getLogger(__name__)
settings = get_settings()


# -------------------------------------------------------
# Unified Lifespan (Startup + Shutdown)
# -------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Unified lifespan management combining:
    - Core infrastructure (logging, redis) from app.core.lifecycle
    - Mission worker from backend.modules.missions
    """
    # Startup
    configure_logging()
    logger.info(f"🧠 BRAiN Core v0.3.0 starting (env: {settings.environment})")

    # Initialize Redis
    redis = await get_redis()
    await redis.ping()
    logger.info("✅ Redis connection established")

    # Start Event Stream (ADR-001: required by default)
    event_stream = None
    eventstream_mode = os.getenv("BRAIN_EVENTSTREAM_MODE", "required").lower()

    if eventstream_mode == "required":
        # REQUIRED MODE: EventStream MUST start
        if EventStream is None:
            raise RuntimeError(
                "EventStream is None in required mode. This should not happen. "
                "Check import logic."
            )

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        event_stream = EventStream(redis_url)
        await event_stream.initialize()
        await event_stream.start()
        logger.info("✅ Event Stream started (required mode)")
        app.state.event_stream = event_stream

    elif eventstream_mode == "degraded":
        # DEGRADED MODE: EventStream disabled, explicit log
        logger.warning(
            "⚠️ DEGRADED MODE: EventStream disabled. "
            "This violates ADR-001 and should ONLY be used in Dev/CI."
        )
        event_stream = None
        app.state.event_stream = None

    else:
        raise ValueError(
            f"Invalid BRAIN_EVENTSTREAM_MODE='{eventstream_mode}'. "
            f"Must be 'required' (default) or 'degraded' (Dev/CI only)."
        )

    # Start mission worker (if enabled)
    mission_worker_task = None
    if os.getenv("ENABLE_MISSION_WORKER", "true").lower() == "true":
        mission_worker_task = await start_mission_worker()
        logger.info("✅ Mission worker started")

    logger.info("✅ All systems operational")

    yield

    # Shutdown
    if event_stream:
        await event_stream.stop()
        logger.info("🛑 Event Stream stopped")

    if mission_worker_task:
        await stop_mission_worker()
        logger.info("🛑 Mission worker stopped")

    await redis.close()
    logger.info("🛑 BRAiN Core shutdown complete")


# -------------------------------------------------------
# App Factory
# -------------------------------------------------------
def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.

    Combines functionality from:
    - backend/main.py: Auto-discovery of backend/api/routes/*, mission worker
    - app/main.py: Settings-based config, app module routers, lifespan
    """
    app = FastAPI(
        title="BRAiN Core",
        version="0.3.0",
        description="Business Reasoning and Intelligence Network - Unified Backend",
        lifespan=lifespan,
    )

    # CORS (from settings for production, with fallback)
    cors_origins = settings.cors_origins if hasattr(settings, 'cors_origins') else [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "*",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -------------------------------------------------------
    # Root & Health Endpoints
    # -------------------------------------------------------
    @app.get("/", tags=["default"])
    async def root() -> dict:
        """Root endpoint with system information"""
        return {
            "name": "BRAiN Core Backend",
            "version": "0.3.0",
            "status": "operational",
            "docs": "/docs",
            "api_health": "/api/health",
        }

    @app.get("/api/health", tags=["default"])
    async def api_health() -> dict:
        """Global health check"""
        return {
            "status": "ok",
            "message": "BRAiN Core Backend is running",
            "version": "0.3.0",
        }

    @app.get("/debug/routes", tags=["default"])
    async def list_routes() -> dict:
        """Debug endpoint: List all registered routes"""
        paths: List[str] = []
        for route in app.routes:
            if isinstance(route, APIRoute):
                paths.append(f"{route.path} [{','.join(route.methods)}]")
        return {"routes": sorted(paths)}

    # -------------------------------------------------------
    # Include Routers
    # -------------------------------------------------------

    # 1. Legacy supervisor router (from backend/modules)
    app.include_router(supervisor_router, prefix="/api", tags=["legacy-supervisor"])

    # 2. App module routers (from app/modules) - Main API
    app.include_router(foundation_router, tags=["foundation"])  # NEW: Foundation module
    app.include_router(sovereign_mode_router, tags=["sovereign-mode"])  # NEW: Sovereign Mode
    app.include_router(dmz_control_router, tags=["dmz-control"])  # NEW: DMZ Control
    app.include_router(course_factory_router, tags=["course-factory"])  # NEW: CourseFactory (Sprint 12)
    app.include_router(monetization_router, tags=["course-monetization"])  # NEW: CourseFactory Monetization (Sprint 14)
    app.include_router(distribution_router, tags=["course-distribution"])  # NEW: Course Distribution (Sprint 15)
    app.include_router(governance_router, tags=["governance"])  # NEW: Governance & HITL Approvals (Sprint 16)
    app.include_router(dna_router, tags=["dna"])
    app.include_router(karma_router, tags=["karma"])
    app.include_router(immune_router, tags=["immune"])
    app.include_router(credits_router, tags=["credits"])
    app.include_router(policy_router, tags=["policy"])
    app.include_router(threats_router, tags=["threats"])
    app.include_router(app_supervisor_router, tags=["supervisor"])
    app.include_router(app_missions_router, tags=["missions"])

    # 3. Auto-discover routes from backend/api/routes/*
    _include_legacy_routers(app)

    # 4. Auto-discover routes from app/api/routes/*
    _include_app_routers(app)

    logger.info("✅ App created, all routers registered")
    return app


# -------------------------------------------------------
# Auto-Discovery Functions
# -------------------------------------------------------
def _include_legacy_routers(app: FastAPI) -> None:
    """
    Auto-discover and include routers from backend/api/routes/*
    (Legacy router discovery from original backend/main.py)
    """
    try:
        from backend.api import routes as routes_pkg  # type: ignore[import]

        package_path = routes_pkg.__path__  # type: ignore[attr-defined]
        package_name = routes_pkg.__name__

        for _, module_name, _ in pkgutil.iter_modules(package_path):
            if module_name.startswith("_"):
                continue

            module_full_name = f"{package_name}.{module_name}"
            module = importlib.import_module(module_full_name)
            router = getattr(module, "router", None)

            if router is not None:
                app.include_router(router, tags=[f"legacy-{module_name}"])
                logger.debug(f"✅ Included legacy router: {module_name}")
    except ImportError as e:
        logger.warning(f"⚠️ Could not import backend.api.routes: {e}")


def _include_app_routers(app: FastAPI) -> None:
    """
    Auto-discover and include routers from app/api/routes/*
    (App router discovery from original app/main.py)
    """
    try:
        from app.api import routes

        for _, module_name, _ in pkgutil.iter_modules(routes.__path__):
            if module_name.startswith("_"):
                continue

            module = importlib.import_module(f"app.api.routes.{module_name}")
            router = getattr(module, "router", None)

            if router is not None:
                app.include_router(router, tags=[f"app-{module_name}"])
                logger.debug(f"✅ Included app router: {module_name}")
    except ImportError as e:
        logger.warning(f"⚠️ Could not import app.api.routes: {e}")


# -------------------------------------------------------
# App Instance
# -------------------------------------------------------
app = create_app()


# -------------------------------------------------------
# Development Server (if run directly)
# -------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
