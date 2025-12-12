<!--
Purpose: Short, actionable instructions for AI coding agents working in this repository.
Keep concise and reference concrete files/commands discovered by static inspection.
-->

# Copilot instructions for contributors and AI agents

This file gives focused, repo-specific guidance to help AI coding agents be productive immediately.

1. Purpose & Big picture

- **What:** Monorepo for BRAIN: a FastAPI-based Python backend, a mission system, connector modules, and two Next.js frontends.
- **Layout:** Key folders: `backend/` (FastAPI app + `backend/api/routes`), `mission_system/` (mission logic), `modules/connector_hub` (connectors registry/gateway), `core/` (module loader & orchestration helpers), `frontend/` (Next.js apps), and `data/` (Postgres/Redis/Qdrant volumes).
- **Why it looks like this:** backend exposes lightweight stubs for mission & connector subsystems (see `backend/main.py` and `backend/app_entry.py`) so developers can iterate UI and tests before deep integrations.

2. Runtime & local-dev commands (concrete)

- Start all services (recommended):
  - `docker compose up -d` (root-compose) or `docker compose -f docker-compose.dev.yml up --build` for dev flags.
- Backend dev with reload (mounts current tree):
  - `docker compose -f docker-compose.dev.yml up --build backend` (or run locally: `pip install -r backend/requirements.txt` then `uvicorn backend.app_entry:app --reload --port 8000`).
- Inspect routes (quick): `GET /debug/routes` (the FastAPI app exposes it in `backend/main.py`).

3. Tests & quick checks

- Unit tests (inside backend container): `docker compose exec backend pytest` or locally `pytest backend/tests`.
- Health endpoints used by CI/UI: `GET /api/health`, `GET /api/missions/health` (stubs in `backend/main.py` and `backend/app_entry.py`).

4. Patterns & conventions to follow (concrete)

- API routers: place endpoints under `backend/api/routes/` and register them via `app.include_router(...)` (see `backend/main.py`).
- Pydantic models: use simple `BaseModel` classes for request/response shapes (example: `ChatRequest` in `backend/api/routes/agent_manager.py`).
- Connector/Agent pattern: use the connector registry / gateway abstraction from `modules/connector_hub` — call `registry.summary()` and `get_gateway()` as shown in `agent_manager.py` rather than hard-coding gateways.
- Stubs are expected: many endpoints are placeholders that echo input (so tests/UI depend on stable stubs). Avoid removing or radically changing stub signatures without updating tests and UI.

5. External services and envs (concrete)

- Expected services (see `docker-compose.yml`): Postgres (pgvector image), Redis, Qdrant, and an Nginx reverse proxy. Local ports: Postgres 5432, Redis 6379, Qdrant 6333, Backend 8000 (dev may map 8010).
- Environment: copy `.env.example` → `.env`. The docker-compose files expect `DATABASE_URL`, `REDIS_URL`, `QDRANT_URL` to be provided.

6. Dependency & build notes

- Python dependencies for backend live in `backend/requirements.txt` (FastAPI, uvicorn, pydantic, redis, httpx, loguru). To add a dependency: update that file and rebuild the backend container.
- Frontend apps are Next.js (see `frontend/brain_control_ui` and `frontend/control_deck`) — use `npm install` and `npm run dev` per each frontend's README.

7. Small examples (copy-paste)

- Agent chat request (endpoint `POST /api/agents/chat` — `backend/api/routes/agent_manager.py`):
  - Request body: `{ "message": "Hello", "agent_id": "default" }`
  - Response: a placeholder JSON including `reply`, `used_gateway`, `meta_echo`.
- List registered routes (debug): `curl http://localhost:8000/debug/routes`

8. When editing code — practical checklist

- If you change an API route signature, update: `backend/api/routes/*`, tests under `backend/tests/`, and the debug `/debug/routes` expectations.
- If you touch connectors/gateway code, also update `modules/connector_hub` registry usage and any front-end mocks.
- For dependency changes: edit `backend/requirements.txt` and rebuild Docker (see section 2).

9. Where to look next (important files)

- `backend/main.py`, `backend/app_entry.py` — app entrypoints and route registration
- `backend/api/routes/agent_manager.py` — agent & connector usage example
- `backend/requirements.txt` — backend deps
- `docker-compose.yml`, `docker-compose.dev.yml` — service composition & dev overrides
- `modules/connector_hub` — connector registry and gateway implementations

10. Ask me if any area is unclear

- If a route, env var, or service is missing from your local environment, tell me which error you see and I will suggest the minimal change to fix or stub it.

-- End of instructions --
