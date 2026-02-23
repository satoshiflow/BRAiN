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
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Rate Limiting (Task 2.3)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Core infrastructure
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.redis_client import get_redis

# Mission worker (from old backend/main.py)
from modules.missions.worker import start_mission_worker, stop_mission_worker

# Autoscaler worker (Cluster System auto-scaling)
from app.workers.autoscaler import start_autoscaler, stop_autoscaler

# Metrics collector (Cluster System metrics collection)
from app.workers.metrics_collector import start_metrics_collector, stop_metrics_collector

# Event Stream (ADR-001: REQUIRED core infrastructure)
try:
    from mission_control_core.core.event_stream import EventStream
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
from modules.supervisor.router import router as supervisor_router

# App module routers (from app/main.py)
from app.modules.dna.router import router as dna_router
from app.modules.karma.router import router as karma_router
from app.modules.immune.router import router as immune_router
from app.modules.credits.router import router as credits_router
from app.modules.policy.router import router as policy_router
from app.modules.threats.router import router as threats_router
from app.modules.supervisor.router import router as app_supervisor_router
from app.modules.foundation.router import router as foundation_router
from app.modules.sovereign_mode.router import router as sovereign_mode_router
from app.modules.dmz_control.router import router as dmz_control_router
from app.modules.course_factory.router import router as course_factory_router
from app.modules.course_factory.monetization_router import router as monetization_router
from app.modules.course_distribution.distribution_router import router as distribution_router
from app.modules.governance.governance_router import router as governance_router
from app.modules.paycore.router import router as paycore_router  # NEW: PayCore payment module

# Cluster System routers (Phase 3)
from app.modules.cluster_system.router import router as cluster_router, blueprints_router

# Chat Router (AXE UI Integration)
from api.routes.chat import router as chat_router

# Auth & Admin Routers (User Management)
from app.api.routes.auth import router as auth_router, admin_router as admin_auth_router

# NeuroRail routers (EGR v1.0 - Phase 1: Observe-only)
from app.modules.neurorail.identity.router import router as neurorail_identity_router
from app.modules.neurorail.lifecycle.router import router as neurorail_lifecycle_router
from app.modules.neurorail.audit.router import router as neurorail_audit_router
from app.modules.neurorail.telemetry.router import router as neurorail_telemetry_router
from app.modules.neurorail.execution.router import router as neurorail_execution_router
from app.modules.governor.router import router as governor_router
from app.modules.axe_fusion.router import router as axe_fusion_router
from app.modules.axe_identity.router import router as axe_identity_router
from app.modules.axe_knowledge.router import router as axe_knowledge_router

# Agent Management Router (Core Module - Phase 1)
from app.modules.agent_management.router import router as agent_management_router

# Task Queue Router (Core Module - Phase 2)
from app.modules.task_queue.router import router as task_queue_router

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
    - Mission worker from modules.missions
    """
    # Startup
    configure_logging()
    logger.info(f"🧠 BRAiN Core v0.3.0 starting (env: {settings.environment})")

    # Initialize Redis (optional - skip if not available)
    redis = None
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.warning(f"⚠️ Redis not available: {e}")
        logger.warning("⚠️ Running without Redis (EventStream and Mission Worker disabled)")

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
        # DISABLED MODE: Skip EventStream if Redis not available
        if redis is None:
            logger.warning("⚠️ EventStream disabled (Redis not available)")
            event_stream = None
            app.state.event_stream = None
        else:
            raise ValueError(
                f"Invalid BRAIN_EVENTSTREAM_MODE='{eventstream_mode}'. "
                f"Must be 'required' (default) or 'degraded' (Dev/CI only)."
            )

    # Start mission worker (if enabled) with EventStream integration (Sprint 2)
    mission_worker_task = None
    if os.getenv("ENABLE_MISSION_WORKER", "true").lower() == "true":
        mission_worker_task = await start_mission_worker(event_stream=event_stream)
        logger.info("✅ Mission worker started (EventStream: %s)", "enabled" if event_stream else "disabled")

    # Start metrics collector worker (Cluster System metrics)
    metrics_collector_task = None
    if os.getenv("ENABLE_METRICS_COLLECTOR", "true").lower() == "true":
        metrics_collector_task = asyncio.create_task(start_metrics_collector(collection_interval=30))
        logger.info("✅ Metrics collector started (interval: 30s)")

    # Start autoscaler worker (Cluster System auto-scaling)
    autoscaler_task = None
    if os.getenv("ENABLE_AUTOSCALER", "true").lower() == "true":
        autoscaler_task = asyncio.create_task(start_autoscaler(check_interval=60))
        logger.info("✅ Autoscaler worker started (interval: 60s)")

    # Seed built-in skills
    try:
        from app.modules.skills.builtins_seeder import seed_builtin_skills
        from app.core.database import async_session_maker
        async with async_session_maker() as db:
            await seed_builtin_skills(db)
    except Exception as e:
        logger.warning(f"⚠️ Could not seed built-in skills: {e}")

    logger.info("✅ All systems operational")

    yield

    # Shutdown
    if event_stream:
        await event_stream.stop()
        logger.info("🛑 Event Stream stopped")

    if mission_worker_task:
        await stop_mission_worker()
        logger.info("🛑 Mission worker stopped")

    if metrics_collector_task:
        stop_metrics_collector()
        logger.info("🛑 Metrics collector stopped")

    if autoscaler_task:
        stop_autoscaler()
        logger.info("🛑 Autoscaler worker stopped")

    if redis:
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
        version="0.4.0",
        description="Business Reasoning and Intelligence Network - Unified Backend",
        lifespan=lifespan,
    )

    # Rate Limiter Setup (Task 2.3 - DoS Protection)
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["100/minute"],  # Global default: 100 requests per minute
        storage_uri=settings.redis_url,  # Use Redis for distributed rate limiting
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS (from settings for production, with fallback)
    cors_origins = settings.cors_origins if hasattr(settings, 'cors_origins') and settings.cors_origins else [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://axe.brain.falklabs.de",
        "https://control.brain.falklabs.de",
        "https://n8n.brain.falklabs.de",
        "*",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # UTF-8 Middleware - Ensures all JSON responses have charset=utf-8
    class UTF8Middleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            # Ensure Content-Type has charset=utf-8
            if "application/json" in response.headers.get("content-type", ""):
                response.headers["content-type"] = "application/json; charset=utf-8"
            return response

    app.add_middleware(UTF8Middleware)

    # Security Headers Middleware (OWASP Recommendations - Task 2.2)
    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)

            # OWASP Security Headers
            response.headers.update({
                "X-Content-Type-Options": "nosniff",  # Prevent MIME sniffing
                "X-Frame-Options": "DENY",  # Prevent clickjacking
                "X-XSS-Protection": "1; mode=block",  # Enable XSS filter
                "Referrer-Policy": "strict-origin-when-cross-origin",  # Privacy
                "Permissions-Policy": "geolocation=(), microphone=(), camera=()",  # Disable sensitive APIs
            })

            # HSTS only in production (enforce HTTPS)
            if settings.environment == "production":
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

            return response

    app.add_middleware(SecurityHeadersMiddleware)

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
    app.include_router(agent_management_router, tags=["agents"])  # NEW: Agent Management (Core)
    app.include_router(task_queue_router, tags=["tasks"])  # NEW: Task Queue (Core)
    app.include_router(foundation_router, tags=["foundation"])  # NEW: Foundation module
    app.include_router(sovereign_mode_router, tags=["sovereign-mode"])  # NEW: Sovereign Mode
    app.include_router(dmz_control_router, tags=["dmz-control"])  # NEW: DMZ Control
    app.include_router(course_factory_router, tags=["course-factory"])  # NEW: CourseFactory (Sprint 12)
    app.include_router(monetization_router, tags=["course-monetization"])  # NEW: CourseFactory Monetization (Sprint 14)
    app.include_router(distribution_router, tags=["course-distribution"])  # NEW: Course Distribution (Sprint 15)
    app.include_router(governance_router, tags=["governance"])  # NEW: Governance & HITL Approvals (Sprint 16)
    app.include_router(paycore_router, tags=["paycore"])  # NEW: PayCore payment module
    app.include_router(dna_router, tags=["dna"])
    app.include_router(karma_router, tags=["karma"])
    app.include_router(immune_router, tags=["immune"])
    app.include_router(credits_router, tags=["credits"])
    app.include_router(policy_router, tags=["policy"])
    app.include_router(threats_router, tags=["threats"])
    app.include_router(app_supervisor_router, tags=["supervisor"])

    # NeuroRail routers (EGR v1.0 - Phase 1: Observe-only)
    app.include_router(neurorail_identity_router, tags=["neurorail-identity"])
    app.include_router(neurorail_lifecycle_router, tags=["neurorail-lifecycle"])
    app.include_router(neurorail_audit_router, tags=["neurorail-audit"])
    app.include_router(neurorail_telemetry_router, tags=["neurorail-telemetry"])
    app.include_router(neurorail_execution_router, tags=["neurorail-execution"])
    app.include_router(governor_router, tags=["governor"])

    # Cluster System routers (Phase 3)
    app.include_router(cluster_router, tags=["clusters"])
    app.include_router(blueprints_router, tags=["blueprints"])

    # AXE Fusion Router (AXEllm Integration)
    app.include_router(axe_fusion_router, prefix="/api", tags=["axe-fusion"])

    # AXE Identity Router (Identity Management)
    app.include_router(axe_identity_router, tags=["axe-identity"])

    # AXE Knowledge Router (Knowledge Base - TASK-003)
    app.include_router(axe_knowledge_router, tags=["axe-knowledge"])

    # Chat Router (AXE UI Integration)
    app.include_router(chat_router, prefix="/api", tags=["chat"])

    # Auth & Admin Routers (User Management)
    app.include_router(auth_router)
    app.include_router(admin_auth_router)

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
        from api import routes as routes_pkg  # type: ignore[import]

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
