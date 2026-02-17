from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.agent_manager import router as agent_router
from backend.api.routes.axe import router as axe_router


app = FastAPI(
    title="BRAIN Core (Direct Entry)",
    version="1.0.0",
    description="BRAIN+ Backend – direkter Einstieg ohne core.app",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # später einschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health ---
@app.get("/api/health")
def health():
    return {"status": "ok", "core": "online"}


# --- Mission-System Stub (für Tests & UI) ---
@app.get("/api/missions/info")
def missions_info():
    return {
        "name": "Mission System",
        "version": "1.0.0",
        "orchestrator": {"orchestrator": "initialized"},
    }


@app.get("/api/missions/health")
def missions_health():
    return {
        "status": "ok",
        "system": "missions",
    }


# --- Connector-Hub Stub ---
@app.get("/api/connectors/info")
def connectors_info():
    return {
        "name": "Connector Hub",
        "version": "1.0.0",
    }


@app.get("/api/connectors/list")
def connectors_list():
    # später: echte Konnektoren
    return {
        "connectors": [],
    }


# --- Agenten-Info ---
@app.get("/api/agents/info")
def agents_info():
    return {
        "name": "Agent Manager",
        "version": "1.0",
        "status": "online",
        "description": "Handles agent chat input and routing.",
    }


# --- Router für Agents & Axe ---
app.include_router(agent_router, prefix="/api/agents", tags=["agents"])
app.include_router(axe_router, prefix="/api/axe", tags=["axe"])
