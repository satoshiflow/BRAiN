# backend/main.py
"""
BRAIN Backend – FastAPI Application
Haupt-Einstiegspunkt für das BRAIN Core Backend.
"""

from __future__ import annotations

import os
import importlib
import pkgutil
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from backend.modules.missions.worker import start_mission_worker, stop_mission_worker
from backend.modules.supervisor.router import router as supervisor_router

# -------------------------------------------------------
# FastAPI App
# -------------------------------------------------------
app = FastAPI(
    title="BRAIN Core",
    version="0.2.0",
    description="BRAIN Backend – unified main app (Agents, Missions, AXE, Debug).",
)

# -------------------------------------------------------
# CORS (für lokale Entwicklung großzügig)
# -------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "*",  # später in Production einschränken
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------
# Supervisor-Router
# -------------------------------------------------------
# Wichtig: nur "/api" als Prefix, damit die finalen Pfade
# /api/supervisor/status
# /api/supervisor/agents
# /api/supervisor/control
# lauten (siehe router.prefix = "/supervisor").
app.include_router(
    supervisor_router,
    prefix="/api",
)


# -------------------------------------------------------
# Basis-Health & Root
# -------------------------------------------------------
@app.get("/", tags=["default"])
async def root() -> dict:
    """
    Root-Endpoint – gibt Basisinfos zum BRAIN Backend zurück.
    """
    return {
        "name": "BRAIN Core Backend",
        "version": "0.2.0",
        "docs": "/docs",
        "api_health": "/api/health",
    }


@app.get("/api/health", tags=["default"])
async def api_health() -> dict:
    """
    Globaler Healthcheck des Backends.
    (Details für einzelne Komponenten kommen aus den jeweiligen Routern.)
    """
    return {
        "status": "ok",
        "message": "BRAIN Core Backend is running",
        "version": "0.2.0",
    }


# -------------------------------------------------------
# Mission-Worker Lifecycle
# -------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    # Mission-Worker nur starten, wenn nicht explizit deaktiviert
    if os.getenv("ENABLE_MISSION_WORKER", "true").lower() == "true":
        await start_mission_worker()


@app.on_event("shutdown")
async def on_shutdown():
    await stop_mission_worker()


# -------------------------------------------------------
# Router-Autodiscovery
# -------------------------------------------------------
def include_all_routers(app: FastAPI) -> None:
    """
    Findet alle Module in backend.api.routes.*, die ein 'router'-Attribut haben,
    und hängt sie automatisch an die App.

    Erwartete Struktur:
        backend/
          api/
            __init__.py
            routes/
              __init__.py
              agent_manager.py   -> router = APIRouter(prefix="/api/agents", ...)
              missions.py        -> router = APIRouter(prefix="/api/missions", ...)
              axe.py             -> router = APIRouter(prefix="/api/axe", ...)
              debug_llm.py       -> router = APIRouter(prefix="/api/debug", ...)
              ...
    """
    from backend.api import routes as routes_pkg  # type: ignore[import]

    package_path = routes_pkg.__path__  # type: ignore[attr-defined]
    package_name = routes_pkg.__name__

    for _, module_name, _ in pkgutil.iter_modules(package_path):
        module_full_name = f"{package_name}.{module_name}"
        module = importlib.import_module(module_full_name)
        router = getattr(module, "router", None)
        if router is not None:
            app.include_router(router)


# beim Start alle API-Router registrieren
include_all_routers(app)


# -------------------------------------------------------
# Route-Debugger
# -------------------------------------------------------
@app.get("/debug/routes", tags=["default"])
async def list_routes() -> dict:
    """
    Debug-Endpoint: listet alle registrierten Pfade auf.
    Sehr hilfreich, um zu prüfen, ob Autodiscovery & Prefixes korrekt greifen.
    """
    paths: List[str] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            paths.append(f"{route.path} [{','.join(route.methods)}]")
    return {"routes": paths}

# End of file
