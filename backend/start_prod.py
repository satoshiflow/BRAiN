#!/usr/bin/env python3
"""
Minimaler Production-Like Backend Server
Lädt Konfiguration aus .env Datei
"""
import os
import sys
from pathlib import Path

# Load .env.local (preferred) or .env if exists
from dotenv import load_dotenv
env_local_path = Path(__file__).parent / ".env.local"
env_path = Path(__file__).parent / ".env"
if env_local_path.exists():
    load_dotenv(env_local_path)
    print(f"Loaded .env.local from {env_local_path}", file=sys.stderr)
elif env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded .env from {env_path}", file=sys.stderr)
else:
    print("No .env file found, using environment variables", file=sys.stderr)

# Set defaults for local development if not in .env
os.environ.setdefault('BRAIN_RUNTIME_MODE', 'local')
os.environ.setdefault('BRAIN_EVENTSTREAM_MODE', 'disabled')
os.environ.setdefault('AXE_FUSION_ALLOW_LOCAL_REQUESTS', 'true')
os.environ.setdefault('AXE_FUSION_ALLOW_LOCAL_FALLBACK', 'true')
os.environ.setdefault('BRAIN_DMZ_GATEWAY_SECRET', 'dev-secret')
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://brain:brain_dev_pass@localhost:5432/brain_dev')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('ENABLE_MISSION_WORKER', 'false')
os.environ.setdefault('ENABLE_BUILTIN_SKILL_SEED', 'false')
os.environ.setdefault('ENABLE_AXE_TEST_MISSIONS', 'false')

# Default LLM strategy: local first, real cloud fallback, no implicit mock
os.environ.setdefault('LOCAL_LLM_MODE', 'auto')
os.environ.setdefault('OLLAMA_BASE_URL', 'http://localhost:11434/v1')
os.environ.setdefault('OLLAMA_MODEL', 'qwen2.5:0.5b')
os.environ.setdefault('OPENAI_BASE_URL', 'https://api.openai.com/v1')
os.environ.setdefault('OPENAI_MODEL', 'gpt-4o-mini')
os.environ.setdefault('AXELLM_BASE_URL', os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434/v1'))
os.environ.setdefault('AXELLM_MODEL', os.environ.get('OLLAMA_MODEL', 'qwen2.5:0.5b'))

print(f"LOCAL_LLM_MODE: {os.environ.get('LOCAL_LLM_MODE')}", file=sys.stderr)
print(f"AXELLM_BASE_URL: {os.environ.get('AXELLM_BASE_URL')}", file=sys.stderr)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings

settings = get_settings()
print(f"Settings loaded: {settings.runtime_mode}", file=sys.stderr)

# Minimaler Lifespan
@asynccontextmanager
async def minimal_lifespan(app: FastAPI):
    import logging
    logging.info("Starting BRAiN Core (minimal mode)")
    app.state.event_stream = None
    yield
    logging.info("Shutting down BRAiN Core")

# App erstellen
app = FastAPI(
    title="BRAiN Core",
    version="0.4.0",
    lifespan=minimal_lifespan
)
print("App created", file=sys.stderr)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("CORS added", file=sys.stderr)

# AXE Router inkludieren
from app.modules.axe_fusion.router import router as axe_router
from app.modules.axe_sessions.router import router as axe_sessions_router
from app.modules.axe_worker_runs.router import router as axe_worker_runs_router
from app.api.routes.auth import router as auth_router
app.include_router(axe_router, prefix="/api")  # Router hat schon /axe prefix
app.include_router(axe_sessions_router)
app.include_router(axe_worker_runs_router)
app.include_router(auth_router)
print("AXE router included", file=sys.stderr)

# Health Endpoint
@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "BRAiN Core running", "version": "0.4.0"}

# Uvicorn starten
import uvicorn
print("Starting uvicorn on http://0.0.0.0:8000", file=sys.stderr)
uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
