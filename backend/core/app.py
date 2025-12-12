# backend/core/app.py

from fastapi import FastAPI

from backend.core.module_loader import load_modules
from backend.api import api_router  # zentraler API-Router (agents, axe, ...)

app = FastAPI(title="BRAIN Core")


@app.get("/api/health")
def root_health():
    return {"status": "ok"}


# 1) Core-APIs (Agents, AXE usw.)
app.include_router(api_router)

# 2) Plug-in-Module registrieren (Mission System, Connector Hub, ...)
load_modules(app)
