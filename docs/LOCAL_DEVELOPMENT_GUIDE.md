# BRAiN Local Development Guide

Quick guide for running BRAiN backend + AXE UI on your laptop.

**Runtime Mode**: `local` (auto-detected for localhost)  
**Contract**: See `docs/specs/runtime_deployment_contract.md`

---

## Quick Start (3 Commands)

```bash
# 1. Start infrastructure (Postgres, Redis, Qdrant)
./scripts/start_local_dev.sh

# 2. Start backend (Terminal 1)
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 3. Start AXE UI (Terminal 2)
cd frontend/axe_ui
npm run dev
```

**URLs**:
- Backend API: http://127.0.0.1:8000
- Backend Docs: http://127.0.0.1:8000/docs
- AXE UI: http://127.0.0.1:3002

---

## Architecture (Local Stack)

```
┌─────────────────────────────────────────────────┐
│  Laptop (127.0.0.1)                             │
├─────────────────────────────────────────────────┤
│                                                 │
│  Frontend (Next.js)                             │
│  ├─ AXE UI :3002  ──────┐                       │
│  └─ getApiBase() → local│                       │
│                         │                       │
│  Backend (FastAPI)      ▼                       │
│  └─ API :8000 ◄─────────┘                       │
│      ├─ Runtime Mode: local                     │
│      ├─ Startup: minimal                        │
│      └─ EventStream: degraded (optional)        │
│                                                 │
│  Infrastructure (Docker)                        │
│  ├─ Postgres :5433                              │
│  ├─ Redis :6380                                 │
│  └─ Qdrant :6334                                │
└─────────────────────────────────────────────────┘
```

---

## Prerequisites

1. **Docker Desktop** (for Postgres, Redis, Qdrant)
2. **Python 3.12+** (for backend)
3. **Node.js 20+** (for frontend)
4. **uv** (optional, for faster Python deps)

---

## Step-by-Step Setup

### 1. Infrastructure Services

Start Postgres, Redis, Qdrant via Docker:

```bash
./scripts/start_local_dev.sh
```

**What it does**:
- Starts `docker-compose.dev.yml` services
- Waits for health checks
- Prints service URLs

**Verify**:
```bash
docker ps  # Should show brain-dev-postgres, brain-dev-redis, brain-dev-qdrant
```

### 2. Backend Setup

**Install Dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

**Configure** (`.env.local` already set for local mode):
```bash
# Check: backend/.env.local should have:
BRAIN_RUNTIME_MODE=local
DATABASE_URL=postgresql+asyncpg://brain:brain_dev_pass@localhost:5433/brain_dev
```

**Run Migrations** (first time only):
```bash
cd backend
alembic upgrade head
```

**Start Backend**:
```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Expected Output**:
```
🧠 BRAiN Core v0.3.0 starting (env: development)
🔧 Runtime mode: local
✅ Remote mode validation passed (skipped for local)
🚀 Startup profile: minimal
✅ Redis connection established
...
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Health Check**:
```bash
curl http://127.0.0.1:8000/api/health
# Should return: {"status":"healthy"}
```

### 3. AXE UI Setup

**Install Dependencies**:
```bash
cd frontend/axe_ui
npm install
```

**Configure** (`.env.local` already set for local mode):
```bash
# Check: frontend/axe_ui/.env.local should have:
NEXT_PUBLIC_APP_ENV=local
NEXT_PUBLIC_BRAIN_API_BASE=http://127.0.0.1:8000
```

**Start Frontend**:
```bash
cd frontend/axe_ui
npm run dev
```

**Expected Output**:
```
▲ Next.js 14.x.x
- Local:        http://127.0.0.1:3002
```

**Test**:
Open http://127.0.0.1:3002/chat and send a message.

---

## Troubleshooting

### Ports Already in Use

**Symptom**: `Error: listen EADDRINUSE :::8000`

**Fix**: Check what's using the port:
```bash
# Check ports
ss -ltn | grep -E '8000|3002|5433|6380'

# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### Services Not Healthy

**Symptom**: `docker ps` shows `(unhealthy)` status

**Fix**:
```bash
# Check logs
docker logs brain-dev-postgres
docker logs brain-dev-redis

# Restart services
docker-compose -f docker-compose.dev.yml restart postgres redis

# Nuclear option: recreate
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d postgres redis qdrant
```

### CORS Errors

**Symptom**: Browser console shows CORS error

**Fix**:
1. Check backend `.env.local` has correct CORS origins:
   ```
   CORS_ORIGINS=http://localhost:3002,http://127.0.0.1:3002
   ```
2. Restart backend
3. Hard-refresh browser (Ctrl+Shift+R)

### Backend Won't Start (Missing DATABASE_URL)

**Symptom**: `RuntimeError: Remote mode requires environment variables: DATABASE_URL`

**Fix**: Backend detected `remote` mode incorrectly.
```bash
# Explicitly set local mode
export BRAIN_RUNTIME_MODE=local

# Or update backend/.env.local
echo "BRAIN_RUNTIME_MODE=local" >> backend/.env.local
```

### Frontend Shows Wrong API URL

**Symptom**: Network tab shows requests to `https://api.brain.falklabs.de` instead of `localhost`

**Fix**:
```bash
# Check frontend/.env.local
cat frontend/axe_ui/.env.local
# Should have: NEXT_PUBLIC_APP_ENV=local

# Restart frontend dev server
cd frontend/axe_ui
npm run dev
```

---

## Stopping Services

```bash
# Stop infrastructure
docker-compose -f docker-compose.dev.yml down

# Stop backend/frontend: Ctrl+C in terminals
```

---

## Running Tests

**Backend Tests**:
```bash
cd backend
PYTHONPATH=. pytest tests/ -q
```

**Frontend Tests**:
```bash
cd frontend/axe_ui
npm run test
npm run test:e2e  # Playwright E2E tests
```

---

## Next Steps

- **Production Deployment**: See `docs/specs/runtime_deployment_contract.md`
- **Architecture Docs**: See `docs/architecture/`
- **API Docs**: http://127.0.0.1:8000/docs (when backend running)

---

## Reference

- **Runtime Contract**: `docs/specs/runtime_deployment_contract.md`
- **Deployment Guide**: `docs/frontend/AXE_UI_DEPLOY_ENV_RUNBOOK.md`
- **Docker Compose**: `docker-compose.dev.yml`
- **Start Script**: `scripts/start_local_dev.sh`
