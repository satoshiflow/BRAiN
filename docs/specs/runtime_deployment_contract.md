# Runtime Deployment Contract

**Status**: Canonical  
**Domain**: Infrastructure & Deployment  
**Applies to**: Backend (Python), Frontend (Next.js), Local Development, Production

## Overview

This contract defines the **unified environment detection and configuration strategy** for BRAiN across all deployment modes: local laptop development, remote Coolify staging, and production.

### AXEllm Source-of-Truth

- For remote/staging/production, AXE chat runtime depends on the remote AXEllm service deployment (container image family: `ghcr.io/satoshiflow/brain/axellm`).
- Frontend and backend configuration in this contract must preserve connectivity to that remote AXEllm path; local defaults are for developer ergonomics only.

## Goals

1. **Single source of truth** for runtime mode detection
2. **Explicit override capability** via environment variables
3. **Safe defaults** (fail-closed in production, developer-friendly in local)
4. **Consistent behavior** across backend (Python) and frontend (TypeScript/Next.js)
5. **Zero hardcoded fallbacks** in production builds

## Runtime Modes

### Mode Definitions

| Mode | Description | Use Case |
|------|-------------|----------|
| `local` | Laptop development with local services | Dev iteration, testing |
| `remote` | Deployed to Coolify or production infrastructure | Staging, production |
| `auto` | Automatic detection based on environment markers | Default behavior |

### Detection Logic (Priority Order)

1. **Explicit override** (highest priority):
   - If `BRAIN_RUNTIME_MODE=local` or `BRAIN_RUNTIME_MODE=remote` is set → use that value
   - If `NEXT_PUBLIC_APP_ENV=local` or `NEXT_PUBLIC_APP_ENV=production` is set (frontend) → use that value

2. **Auto-detection** (fallback):
   - **Local markers**:
     - `hostname` in `["localhost", "127.0.0.1", "::1"]`
     - `SERVICE_FQDN_*` environment variables **not set**
     - `COOLIFY_*` environment variables **not set**
   - **Remote markers**:
     - `SERVICE_FQDN_*` environment variables present (Coolify)
     - `COOLIFY_*` environment variables present
     - Public domain in hostname (contains `.` and not localhost)

3. **Default** (if detection fails):
   - Backend: `remote` (safe default, fail-closed)
   - Frontend: `production` (safe default, fail-closed)

---

## Backend Configuration Contract

### Environment Variables (Priority Order)

#### Primary Mode Override
```bash
BRAIN_RUNTIME_MODE=auto|local|remote  # Default: auto
```

#### Local Mode Defaults (when `BRAIN_RUNTIME_MODE=local` or auto-detected local)
```bash
DATABASE_URL=postgresql+asyncpg://brain:brain_dev_pass@localhost:5433/brain_dev
REDIS_URL=redis://localhost:6380/0
QDRANT_URL=http://localhost:6334
OLLAMA_HOST=http://localhost:11434
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002,http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002
ENVIRONMENT=development
BRAIN_STARTUP_PROFILE=minimal  # Lightweight local startup
ENABLE_MISSION_WORKER=false    # Disabled in minimal mode
```

#### Remote Mode Requirements (when `BRAIN_RUNTIME_MODE=remote` or auto-detected remote)
```bash
# REQUIRED - must be set explicitly (no defaults)
DATABASE_URL=<injected-by-coolify>
REDIS_URL=<injected-by-coolify>
BRAIN_DMZ_GATEWAY_SECRET=<secret>
JWT_SECRET_KEY=<secret>
BRAIN_ADMIN_PASSWORD=<secret>

# OPTIONAL (have defaults)
QDRANT_URL=${QDRANT_URL:-http://qdrant:6333}
OLLAMA_HOST=${OLLAMA_HOST:-http://ollama:11434}
CORS_ORIGINS=https://control.brain.falklabs.de,https://axe.brain.falklabs.de
ENVIRONMENT=production
BRAIN_STARTUP_PROFILE=full
ENABLE_MISSION_WORKER=true
```

### Backend Config Loading (`backend/app/core/config.py`)

```python
import os
from typing import Literal

RuntimeMode = Literal["local", "remote", "auto"]

def detect_runtime_mode() -> Literal["local", "remote"]:
    """
    Detect runtime mode based on environment markers.
    
    Priority:
    1. Explicit BRAIN_RUNTIME_MODE
    2. Auto-detection (Coolify markers, hostname)
    3. Default: remote (safe)
    """
    explicit = os.getenv("BRAIN_RUNTIME_MODE", "auto").lower()
    if explicit in ["local", "remote"]:
        return explicit
    
    # Auto-detection
    if os.getenv("SERVICE_FQDN_BACKEND") or os.getenv("COOLIFY_APP_ID"):
        return "remote"
    
    # Check if running in local dev environment
    if os.path.exists("/.dockerenv"):
        # Inside container - check if Coolify
        if os.getenv("COOLIFY_APP_ID"):
            return "remote"
        # Local docker-compose
        return "local"
    
    # Default: remote (fail-safe)
    return "remote"

class Settings(BaseSettings):
    runtime_mode: Literal["local", "remote"] = Field(
        default_factory=detect_runtime_mode
    )
    
    # Database - required in remote, has local default
    database_url: str = Field(
        default="postgresql+asyncpg://brain:brain_dev_pass@localhost:5433/brain_dev"
        if detect_runtime_mode() == "local"
        else ...  # Required in remote
    )
    
    # Redis - required in remote, has local default
    redis_url: str = Field(
        default="redis://localhost:6380/0"
        if detect_runtime_mode() == "local"
        else ...  # Required in remote
    )
    
    # ... other settings with mode-aware defaults
```

### Backend Startup Validation

```python
# In backend/main.py lifespan
if settings.runtime_mode == "remote":
    # Validate required secrets are present
    required = [
        "DATABASE_URL",
        "REDIS_URL",
        "BRAIN_DMZ_GATEWAY_SECRET",
        "JWT_SECRET_KEY"
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(
            f"Remote mode requires: {', '.join(missing)}"
        )
```

---

## Frontend Configuration Contract

### Environment Variables (Priority Order)

#### Primary Mode Override
```bash
NEXT_PUBLIC_APP_ENV=auto|local|production  # Default: auto
```

#### Local Mode Defaults (when `NEXT_PUBLIC_APP_ENV=local` or auto-detected local)
```bash
NEXT_PUBLIC_BRAIN_API_BASE=http://127.0.0.1:8000
NEXT_PUBLIC_AXE_DEFAULT_MODEL=qwen2.5:0.5b
```

#### Remote Mode Defaults (when `NEXT_PUBLIC_APP_ENV=production` or auto-detected remote)
```bash
NEXT_PUBLIC_BRAIN_API_BASE=https://api.brain.falklabs.de  # Or from SERVICE_FQDN_BACKEND
NEXT_PUBLIC_AXE_DEFAULT_MODEL=qwen2.5:1.5b
```

### Frontend Config Loading (`frontend/axe_ui/lib/config.ts`)

```typescript
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

type RuntimeMode = "local" | "production";

function detectRuntimeMode(): RuntimeMode {
  // 1. Explicit override
  const explicit = process.env.NEXT_PUBLIC_APP_ENV;
  if (explicit === "local" || explicit === "production") {
    return explicit;
  }
  
  // 2. Auto-detection (browser only)
  if (typeof window !== "undefined") {
    return LOCAL_HOSTS.has(window.location.hostname) ? "local" : "production";
  }
  
  // 3. Default (SSR safe)
  return "production";
}

function getApiBase(mode: RuntimeMode): string {
  // Explicit override always wins
  const explicit = process.env.NEXT_PUBLIC_BRAIN_API_BASE;
  if (explicit) {
    return explicit;
  }
  
  // Mode-based defaults
  if (mode === "local") {
    return "http://127.0.0.1:8000";
  }
  
  // Remote default
  return "https://api.brain.falklabs.de";
}

export const config = {
  runtimeMode: detectRuntimeMode(),
  api: {
    base: getApiBase(detectRuntimeMode()),
  },
  // ... rest of config
};
```

### Frontend Build-Time Validation

```typescript
// In next.config.js or build script
if (process.env.NODE_ENV === "production") {
  const apiBase = process.env.NEXT_PUBLIC_BRAIN_API_BASE;
  
  // Fail build if production points to localhost
  if (apiBase && (apiBase.includes("localhost") || apiBase.includes("127.0.0.1"))) {
    throw new Error(
      "Production build cannot use localhost API. Set NEXT_PUBLIC_BRAIN_API_BASE to production URL."
    );
  }
}
```

---

## Unified Environment Variable Naming

### Standardized Keys

| Purpose | Backend Key | Frontend Key | Notes |
|---------|-------------|--------------|-------|
| Runtime Mode | `BRAIN_RUNTIME_MODE` | `NEXT_PUBLIC_APP_ENV` | `auto`, `local`, `remote`/`production` |
| API Base URL | `BRAIN_API_BASE` | `NEXT_PUBLIC_BRAIN_API_BASE` | Backend self-reference, Frontend → Backend |
| Environment | `ENVIRONMENT` | `NODE_ENV` | `development`, `staging`, `production` |
| Database URL | `DATABASE_URL` | N/A | |
| Redis URL | `REDIS_URL` | N/A | |
| Startup Profile | `BRAIN_STARTUP_PROFILE` | N/A | `minimal`, `full` |

### Deprecated Keys (to be removed)

- `NEXT_PUBLIC_API_URL` → use `NEXT_PUBLIC_BRAIN_API_BASE`
- `APP_ENV` → use `ENVIRONMENT` (backend) or `NEXT_PUBLIC_APP_ENV` (frontend)

---

## Local Development Setup

### Laptop Setup (Minimal Stack)

**Required Services** (via `docker-compose.dev.yml`):
- PostgreSQL (port 5433)
- Redis (port 6380)
- Qdrant (port 6334)
- Mock-LLM (port 8081, optional)

**Backend `.env.local`**:
```bash
BRAIN_RUNTIME_MODE=local
DATABASE_URL=postgresql+asyncpg://brain:brain_dev_pass@localhost:5433/brain_dev
REDIS_URL=redis://localhost:6380/0
QDRANT_URL=http://localhost:6334
OLLAMA_HOST=http://localhost:11434
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002,http://127.0.0.1:3002
ENVIRONMENT=development
BRAIN_STARTUP_PROFILE=minimal
ENABLE_MISSION_WORKER=false
BRAIN_EVENTSTREAM_MODE=degraded  # Optional: skip EventStream for faster startup
```

**Frontend `.env.local`** (`frontend/axe_ui/.env.local`):
```bash
NEXT_PUBLIC_APP_ENV=local
NEXT_PUBLIC_BRAIN_API_BASE=http://127.0.0.1:8000
NEXT_PUBLIC_AXE_DEFAULT_MODEL=qwen2.5:0.5b
```

**Start Commands**:
```bash
# Terminal 1: Start infrastructure
docker-compose -f docker-compose.dev.yml up -d postgres redis qdrant

# Terminal 2: Start backend
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Terminal 3: Start AXE UI
cd frontend/axe_ui
npm run dev
```

---

## Remote Deployment (Coolify/Production)

### Environment Injection

Coolify automatically injects:
- `SERVICE_FQDN_BACKEND=api.brain.falklabs.de`
- `SERVICE_FQDN_AXE_UI=axe.brain.falklabs.de`
- `COOLIFY_APP_ID=<app-id>`
- Database/Redis URLs from connected services

**Backend** (Coolify env vars):
```bash
# Auto-detected as remote due to SERVICE_FQDN_* presence
DATABASE_URL=${DATABASE_URL}  # Injected by Coolify
REDIS_URL=${REDIS_URL}        # Injected by Coolify
BRAIN_DMZ_GATEWAY_SECRET=${BRAIN_DMZ_GATEWAY_SECRET}  # Set in Coolify
JWT_SECRET_KEY=${JWT_SECRET_KEY}  # Set in Coolify
CORS_ORIGINS=https://control.brain.falklabs.de,https://axe.brain.falklabs.de
ENVIRONMENT=production
BRAIN_STARTUP_PROFILE=full
```

**Frontend** (Coolify env vars):
```bash
# Auto-detected as remote due to public domain
NEXT_PUBLIC_BRAIN_API_BASE=https://${SERVICE_FQDN_BACKEND}
NEXT_PUBLIC_APP_ENV=production
```

---

## Migration Path

### Phase 1: Add Runtime Mode Detection (Non-Breaking)
- Add `detect_runtime_mode()` to backend/frontend
- Add `runtime_mode` field to config (read-only, logging only)
- No behavior changes yet

### Phase 2: Consolidate Config Keys
- Add new standardized keys alongside old keys
- Deprecation warnings for old keys
- Update documentation

### Phase 3: Switch to Mode-Based Defaults
- Apply mode-aware defaults in `Settings` classes
- Remove hardcoded fallbacks in components
- Update `.env.example` files

### Phase 4: Cleanup (Breaking)
- Remove deprecated keys
- Fail build on production+localhost
- Enforce required secrets in remote mode

---

## Validation Checklist

### Local Mode
- [ ] Backend starts with `BRAIN_RUNTIME_MODE=local` or auto-detect
- [ ] Frontend detects `localhost` and uses `http://127.0.0.1:8000`
- [ ] No secrets required (uses local defaults)
- [ ] CORS allows localhost origins
- [ ] Startup profile `minimal` by default

### Remote Mode
- [ ] Backend fails if required secrets missing
- [ ] Frontend uses HTTPS API URL
- [ ] No localhost in CORS origins
- [ ] Startup profile `full` by default
- [ ] Trust-tier validation active

### Auto-Detection
- [ ] Coolify deployment auto-detects `remote`
- [ ] Local laptop auto-detects `local`
- [ ] SSR builds default to `production` (safe)

---

## Troubleshooting

### Backend starts in wrong mode
- Check: `BRAIN_RUNTIME_MODE` env var
- Check: `SERVICE_FQDN_*` or `COOLIFY_*` vars present
- Check: `detect_runtime_mode()` logs

### Frontend uses wrong API URL
- Check: `NEXT_PUBLIC_APP_ENV` env var
- Check: Browser console → `config.runtimeMode`
- Check: `NEXT_PUBLIC_BRAIN_API_BASE` explicit override

### CORS errors in local dev
- Ensure `CORS_ORIGINS` includes `http://localhost:3002` and `http://127.0.0.1:3002`
- Check backend logs for CORS rejection reason

### Production build contains localhost
- Run build-time validation script
- Check `.env.production` has remote API URL
- Ensure `NODE_ENV=production` during build

---

## References

- Backend config: `backend/app/core/config.py`
- Frontend config: `frontend/axe_ui/lib/config.ts`
- Docker Compose: `docker-compose.dev.yml` (local), `docker-compose.yml` (Coolify)
- Deployment guide: `docs/frontend/AXE_UI_DEPLOY_ENV_RUNBOOK.md`
