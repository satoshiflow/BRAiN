"""
BRAiN Minimal Backend v3 - With Events CRUD System
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from pydantic import BaseModel
from typing import Optional
import asyncpg
import redis.asyncio as redis
import os
import time
from contextlib import asynccontextmanager

from models.system_event import SystemEventCreate, EventSeverity
from services.system_events import SystemEventsService
from api.routes import events as events_router

# Configuration from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://brain:brain@dev-postgres:5432/brain_dev"
)
REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://dev-redis:6379/0"
)

# Global connection pools
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[redis.Redis] = None
events_service: Optional[SystemEventsService] = None


async def log_system_event(event_type: str, severity: str, message: str, details: dict = None):
    """Helper to log system events"""
    if events_service:
        try:
            await events_service.create_event(SystemEventCreate(
                event_type=event_type,
                severity=EventSeverity(severity),
                message=message,
                details=details,
                source="backend"
            ))
        except Exception as e:
            print(f"Failed to log event: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global db_pool, redis_client, events_service

    # Startup
    startup_time = time.time()
    startup_success = True
    startup_errors = []

    try:
        # PostgreSQL connection pool
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        print("✅ PostgreSQL connection pool created")

    except Exception as e:
        print(f"⚠️  Warning: PostgreSQL connection failed: {e}")
        startup_errors.append(f"PostgreSQL: {str(e)}")
        startup_success = False

    try:
        # Redis connection
        redis_client = await redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        print("✅ Redis connection established")

    except Exception as e:
        print(f"⚠️  Warning: Redis connection failed: {e}")
        startup_errors.append(f"Redis: {str(e)}")
        startup_success = False

    # Initialize events service if DB is available
    if db_pool and redis_client:
        events_service = SystemEventsService(db_pool, redis_client)
        print("✅ Events service initialized")

        # Log startup event
        await log_system_event(
            event_type="system_startup",
            severity="info",
            message="Backend v3 started successfully",
            details={
                "startup_time_ms": round((time.time() - startup_time) * 1000, 2),
                "database": "connected",
                "redis": "connected"
            }
        )
    else:
        print("⚠️  Events service not initialized (degraded mode)")

    if not startup_success:
        print(f"⚠️  Backend started in degraded mode. Errors: {startup_errors}")

    yield

    # Shutdown
    if events_service:
        try:
            await log_system_event(
                event_type="system_shutdown",
                severity="info",
                message="Backend v3 shutting down",
                details={}
            )
        except Exception:
            pass

    if db_pool:
        await db_pool.close()
        print("🔌 PostgreSQL connection pool closed")

    if redis_client:
        await redis_client.close()
        print("🔌 Redis connection closed")


# FastAPI app
app = FastAPI(
    title="BRAiN Minimal API v3",
    version="0.3.0-minimal",
    description="Minimal backend with Events CRUD system",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware to ensure UTF-8 encoding in all responses
class UTF8Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Ensure Content-Type has charset=utf-8
        if "application/json" in response.headers.get("content-type", ""):
            response.headers["content-type"] = "application/json; charset=utf-8"
        return response

app.add_middleware(UTF8Middleware)


# Dependency injection for events service
def get_events_service() -> SystemEventsService:
    """Get events service instance"""
    if not events_service:
        raise HTTPException(
            status_code=503,
            detail="Events service not available (database not connected)"
        )
    return events_service


# Override the dependency in events router
events_router.get_events_service = get_events_service

# Include events router
app.include_router(events_router.router)


# Models
class HealthResponse(BaseModel):
    status: str
    mode: str
    timestamp: float
    version: str


class DBHealthResponse(BaseModel):
    status: str
    postgres: dict
    redis: dict
    timestamp: float


# Routes
@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "BRAiN Minimal Backend v3",
        "version": "0.3.0-minimal",
        "features": ["postgres", "redis", "events_crud", "caching"],
        "endpoints": {
            "health": "/api/health",
            "db_health": "/api/db/health",
            "events": "/api/events",
            "events_stats": "/api/events/stats",
            "docs": "/docs"
        }
    }


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Basic health check"""
    # Log health check event
    await log_system_event(
        event_type="health_check",
        severity="info",
        message="Health check performed",
        details={"endpoint": "/api/health"}
    )

    return HealthResponse(
        status="healthy",
        mode="minimal-v3",
        timestamp=time.time(),
        version="0.3.0"
    )


@app.get("/api/db/health", response_model=DBHealthResponse)
async def db_health():
    """Database health check"""
    postgres_status = {"connected": False, "error": None}
    redis_status = {"connected": False, "error": None}

    # Check PostgreSQL
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                postgres_status = {
                    "connected": True,
                    "result": result,
                    "pool_size": db_pool.get_size(),
                    "pool_free": db_pool.get_idle_size()
                }
        except Exception as e:
            postgres_status = {"connected": False, "error": str(e)}
    else:
        postgres_status = {"connected": False, "error": "Pool not initialized"}

    # Check Redis
    if redis_client:
        try:
            pong = await redis_client.ping()
            redis_status = {
                "connected": True,
                "ping": pong
            }
        except Exception as e:
            redis_status = {"connected": False, "error": str(e)}
    else:
        redis_status = {"connected": False, "error": "Client not initialized"}

    # Overall status
    overall_status = "healthy" if (
        postgres_status["connected"] and redis_status["connected"]
    ) else "degraded"

    # Log DB health check
    await log_system_event(
        event_type="db_health_check",
        severity="info" if overall_status == "healthy" else "warning",
        message=f"Database health check: {overall_status}",
        details={
            "postgres": postgres_status["connected"],
            "redis": redis_status["connected"]
        }
    )

    return DBHealthResponse(
        status=overall_status,
        postgres=postgres_status,
        redis=redis_status,
        timestamp=time.time()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
