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
from app.core.db import close_db_connections
from app.core.middleware import (
    GlobalExceptionMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    SimpleRateLimitMiddleware,
    PrometheusMiddleware,
)

# Mission worker (from old backend/main.py)
from backend.modules.missions.worker import start_mission_worker, stop_mission_worker

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

logger = logging.getLogger(__name__)
settings = get_settings()


# -------------------------------------------------------
# Unified Lifespan (Startup + Shutdown)
# -------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Unified lifespan management with graceful shutdown.

    Startup Phase:
    - Configure logging
    - Initialize Redis connection
    - Start mission worker
    - Verify all systems operational

    Shutdown Phase (graceful):
    - Stop accepting new requests (handled by FastAPI)
    - Allow in-flight requests to complete (with timeout)
    - Stop mission worker gracefully
    - Close all database connections
    - Close Redis connection
    - Log shutdown completion

    The shutdown sequence ensures:
    1. No data loss (in-flight requests complete)
    2. Clean resource cleanup
    3. Proper signal handling (SIGTERM/SIGINT)
    4. Observable shutdown (detailed logging)
    """
    # ===== STARTUP PHASE =====
    configure_logging()

    # Initialize Sentry error tracking (Phase 2)
    from app.core.sentry import init_sentry
    init_sentry()

    logger.info("=" * 60)
    logger.info(f"🧠 BRAiN Core v0.3.0 starting (env: {settings.environment})")
    logger.info("=" * 60)

    # Initialize Redis
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {e}")
        raise

    # Start mission worker (if enabled)
    mission_worker_task = None
    try:
        if os.getenv("ENABLE_MISSION_WORKER", "true").lower() == "true":
            mission_worker_task = await start_mission_worker()
            logger.info("✅ Mission worker started")
    except Exception as e:
        logger.error(f"❌ Failed to start mission worker: {e}")
        # Continue startup even if mission worker fails
        # (non-critical component)

    logger.info("=" * 60)
    logger.info("✅ All systems operational - ready to serve requests")
    logger.info("=" * 60)

    yield  # Application runs here

    # ===== SHUTDOWN PHASE (GRACEFUL) =====
    logger.info("=" * 60)
    logger.info("🛑 Initiating graceful shutdown...")
    logger.info("=" * 60)

    # Step 1: Stop mission worker (allow current missions to complete)
    if mission_worker_task:
        try:
            logger.info("🛑 Stopping mission worker...")
            await stop_mission_worker()
            logger.info("✅ Mission worker stopped gracefully")
        except Exception as e:
            logger.error(f"⚠️ Error stopping mission worker: {e}")

    # Step 2: Close database connections
    try:
        logger.info("🛑 Closing database connections...")
        await close_db_connections()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"⚠️ Error closing database connections: {e}")

    # Step 3: Close Redis connection
    try:
        logger.info("🛑 Closing Redis connection...")
        await redis.close()
        logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.error(f"⚠️ Error closing Redis connection: {e}")

    # Step 4: Flush Sentry events (Phase 2)
    try:
        from app.core.sentry import is_enabled, flush
        if is_enabled():
            logger.info("🛑 Flushing Sentry events...")
            flush(timeout=5.0)  # Wait up to 5 seconds for events to be sent
            logger.info("✅ Sentry events flushed")
    except Exception as e:
        logger.error(f"⚠️ Error flushing Sentry events: {e}")

    logger.info("=" * 60)
    logger.info("✅ BRAiN Core shutdown complete")
    logger.info("=" * 60)


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
    # Production Middleware (Phase 1 + Phase 2)
    # -------------------------------------------------------
    # Order matters: First middleware registered = Last to execute
    # Execution order: Request → Logging → Prometheus → Rate Limit → Request ID → Security → Exception → Route → Exception → ...

    # 1. Global Exception Handler (catches all unhandled exceptions)
    app.add_middleware(GlobalExceptionMiddleware)

    # 2. Security Headers (adds security headers to all responses)
    hsts_enabled = settings.environment == "production"
    app.add_middleware(SecurityHeadersMiddleware, hsts_enabled=hsts_enabled)

    # 3. Request ID Tracking (adds unique ID to each request)
    app.add_middleware(RequestIDMiddleware)

    # 4. Rate Limiting (basic protection - upgrade to Redis-based for production)
    if settings.environment != "development":
        app.add_middleware(SimpleRateLimitMiddleware, max_requests=100, window_seconds=60)

    # 5. Prometheus Metrics (Phase 2 - tracks HTTP requests)
    app.add_middleware(PrometheusMiddleware)

    # 6. Request Logging (logs all requests with timing)
    app.add_middleware(RequestLoggingMiddleware)

    logger.info("✅ Production middleware registered (Phase 1 + Phase 2)")

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
        log_level="info",
        # Graceful shutdown configuration
        timeout_keep_alive=5,        # Keep-alive timeout (seconds)
        timeout_graceful_shutdown=30, # Graceful shutdown timeout (seconds)
        # Signal handling (SIGTERM, SIGINT)
        # Uvicorn handles signals automatically and triggers lifespan shutdown
    )
