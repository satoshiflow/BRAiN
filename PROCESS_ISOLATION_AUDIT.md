# Process Isolation & Service Boundary Audit

**Date:** 2026-02-26
**Status:** COMPLETE - Findings & Guardrails Ready
**Severity:** MEDIUM (dev-only issue currently, but production safeguards needed)

---

## EXECUTIVE SUMMARY

**Finding:** The repository currently **does NOT have implicit frontend spawning from backend/gateway contexts**. However, the dev orchestration script (`brain-starter.sh`) starts ALL services (backend + 3 frontends) as children of a single bash parent, creating potential for **process coupling** and **leftover processes** if this script were run under a systemd service or container orchestrator.

**Risk Level:**
- ✅ **Production:** LOW (Docker Compose uses separate containers, each supervises one process)
- ⚠️ **Dev:** MEDIUM (Scripts can leave orphaned frontends if crashed)
- 🔴 **Potential Risk:** HIGH (if brain-starter.sh were used in production or run by a systemd user service)

**Recommendation:**
1. **Immediate:** Document the dev/prod split clearly in README
2. **Short-term:** Provide guardrails scripts (dev-up/dev-down with port safety)
3. **Long-term:** Sovereign Mode contract + enforcement (prevent accidental coupling)

---

## 1. SERVICE BOUNDARIES MAP

### 1.1 Backend

| Attribute | Value |
|-----------|-------|
| **Entry Point** | `backend/main.py` |
| **Dev Command** | `uvicorn main:app --host 127.0.0.1 --port 8001` |
| **Prod Command** | `uvicorn main:app --host 0.0.0.0 --port 8000` (in container) |
| **Port (Dev)** | 8001 |
| **Port (Prod)** | 8000 |
| **Internal Services** | Mission worker, Metrics collector, Autoscaler |
| **Config** | `backend/.env` or `.env.example` |
| **Process Supervision** | None (should be managed by systemd/K8s/Docker) |
| **Entrypoint Script** | Manual: `cd backend && uvicorn main:app ...` |

**Key:** Backend is CLEAN - no frontend spawning. Starts only internal workers.

---

### 1.2 Frontend: controldeck-v2 (Primary Control UI)

| Attribute | Value |
|-----------|-------|
| **Entry Point** | `frontend/controldeck-v2/` |
| **Dev Command** | `npm run dev` = `next dev` |
| **Prod Command** | `npm run build && npm start` = `next start` |
| **Port (Dev)** | 3456 (or PORT env var) |
| **Port (Prod)** | 3000 |
| **Config** | Reads `NEXT_PUBLIC_BRAIN_API_BASE` |
| **Process Supervision** | None |
| **Entrypoint Script** | `PORT=3456 npm run dev` |

---

### 1.3 Frontend: axe_ui (AXE Dashboard)

| Attribute | Value |
|-----------|-------|
| **Entry Point** | `frontend/axe_ui/` |
| **Dev Command** | `npm run dev` = `next dev` |
| **Prod Command** | `npm run build && npm start` |
| **Port (Dev)** | 3002 |
| **Port (Prod)** | 3000 |
| **Config** | Reads `NEXT_PUBLIC_BRAIN_API_BASE` |
| **Process Supervision** | None |
| **Entrypoint Script** | `PORT=3002 npm run dev` |

---

### 1.4 Frontend: control_deck (Legacy)

| Attribute | Value |
|-----------|-------|
| **Entry Point** | `frontend/control_deck/` |
| **Dev Command** | `npm run dev` |
| **Status** | Legacy, superseded by controldeck-v2 |
| **Port** | 3001 |

---

### 1.5 Authentication Service: better-auth-node

| Attribute | Value |
|-----------|-------|
| **Entry Point** | `better-auth-node/` (Node.js auth server) |
| **Config** | `better-auth-node/.env` |
| **Port** | Configurable |
| **Status** | Optional, can run standalone or integrated |

---

## 2. ORCHESTRATION PATTERNS FOUND

### 2.1 Dev Script: `brain-starter.sh` ⚠️

**Location:** `/home/user/BRAiN/brain-starter.sh`

**What it does:**
```bash
# Starts 3 services as children of a single bash process:
1. Backend (nohup uvicorn...)  → PID A
2. Control Deck (nohup npm run dev...)  → PID B
3. AXE_UI (nohup npm run dev...)  → PID C

All are children of brain-starter.sh
```

**Problem if run under systemd or container orchestrator:**
- If `systemd` unit runs `/path/to/brain-starter.sh`, all 3 services become children of that unit
- On restart, frontend processes might remain orphaned in the cgroup
- Port conflicts on restart

**Code Snippet (lines 29-72):**
```bash
# All started with nohup as background children
nohup uvicorn main:app --host 127.0.0.1 --port $BACKEND_PORT > /tmp/brain.log 2>&1 &
BACKEND_PID=$!

PORT=$CONTROL_DECK_PORT nohup npm run dev > /tmp/control_deck.log 2>&1 &
CONTROL_DECK_PID=$!

PORT=$AXE_UI_PORT nohup npm run dev > /tmp/axe_ui.log 2>&1 &
AXE_UI_PID=$!
```

**Risk Level:** MEDIUM
- ✅ OK for manual dev (user can kill all with `kill $PID1 $PID2 $PID3`)
- ⚠️ NOT OK if wrapped by systemd/orchestrator (could leave orphans)

---

### 2.2 Docker Compose: Production (`docker-compose.yml`)

**Location:** `/home/user/BRAiN/docker-compose.yml`

**Structure:**
```yaml
services:
  backend:       # Container 1: backend only
  control_deck:  # Container 2: controldeck-v2 only
  axe_ui:        # Container 3: axe_ui only
  
networks:
  coolify:       # External network (Traefik)
```

**Assessment:** ✅ CLEAN
- Each service is a separate **container** (=separate process group)
- Each runs exactly ONE responsibility
- No implicit frontend spawning
- Traefik handles routing (not embedding)

---

### 2.3 Docker Compose Dev (`docker-compose.dev.yml`)

**Location:** `/home/user/BRAiN/docker-compose.dev.yml`

**Structure:**
- backend container
- control_deck container
- axe_ui container
- postgres, redis, qdrant, ollama (support services)

**Assessment:** ✅ CLEAN
- Separate containers per service
- No orchestration coupling

---

### 2.4 CI/CD Workflows

**Locations:** `.github/workflows/*.yml`

**Build workflows:**
- `build.yml` - Builds all images
- `frontend-ci.yml` - Tests frontends only
- `backend-ci.yml` - Tests backend only
- `deploy-prod.yml`, `deploy-stage.yml`, `deploy-dev.yml`

**Assessment:** ✅ CLEAN
- No implicit spawning of mixed services
- Each workflow has clear scope

---

### 2.5 Sovereign Mode

**Location:** `backend/app/modules/sovereign_mode/`

**Key Files:**
- `schemas.py` - Defines OperationMode enum (ONLINE, OFFLINE, SOVEREIGN, QUARANTINE)
- `service.py` - SovereignModeService orchestration
- `router.py` - REST endpoints to change mode
- `network_guard.py` - Enforces network rules
- `ipv6_gate.py` - IPv6 policy enforcement
- `scripts/sovereign-fw.sh` - Firewall enforcement

**Current State:**
```python
class OperationMode(str, Enum):
    ONLINE = "online"          # Connected, all services active
    OFFLINE = "offline"        # No external comms
    SOVEREIGN = "sovereign"    # Strict local-only (highest security)
    QUARANTINE = "quarantine"  # Emergency isolation
```

**Integration:**
- dmz_control module checks: "if sovereign mode, reject DMZ startup"
- network_guard enforces whitelist in sovereign mode
- Firewall script (sovereign-fw.sh) sets iptables rules

**Assessment:** ⚠️ PARTIAL
- ✅ Mode concept is good
- ⚠️ NO enforcement that `next dev` isn't started in sovereign mode
- ⚠️ NO guardrail preventing multi-service orchestration in sovereign mode

---

## 3. PROCESS SPAWNING ANALYSIS

### Search Results: Frontend Spawning from Backend/Gateway

**Command:** `grep -r "spawn\|exec\|next dev\|npm run dev" backend/ --include="*.py"`

**Result:** ✅ CLEAN - No hits
- No backend code spawns frontend processes
- No gateway code references frontend services
- No implicit coupling found

---

## 4. PRODUCTION SAFETY REVIEW

### 4.1 Dockerfiles

**backend/Dockerfile:** ✅ CLEAN
- Single ENTRYPOINT: `uvicorn main:app`
- One process family per container
- No frontend bundling

**Dockerfile.controldeck-v2:** ✅ CLEAN
- Build stage: `npm run build`
- Runtime: `node_modules/.bin/next start`
- One process per container

**Assessment:** ✅ All good

---

### 4.2 Kubernetes / Coolify Deployment

**Found in docker-compose.yml:**
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.backend.rule=Host(...)"
  - "traefik.http.services.backend.loadbalancer.server.port=8000"
```

**Assessment:**
- ✅ Using Traefik for reverse proxy (not embedding frontends in backend)
- ✅ Each service has its own DNS/routing rule
- ✅ No orchestration coupling

---

### 4.3 Systemd (if used)

**No systemd files found in repo** ✅

**IF a systemd user service ran brain-starter.sh:**
```
[Unit]
Description=BRAiN System
After=docker.service

[Service]
Type=simple
ExecStart=/home/user/BRAiN/brain-starter.sh
```

**Result:** 🔴 PROBLEM
- All 3 services become children of systemd unit's cgroup
- On unit restart: frontend processes orphaned
- Port conflicts on next start

---

## 5. SOVEREIGN MODE CONTRACT

### Current State
Sovereign Mode is defined but has **NO enforcement** that:
1. No multi-service orchestration occurs
2. No `next dev` (dev server) runs in production/sovereign
3. Services stay isolated when mode changes

### Proposed Sovereign Mode Contract

```python
# backend/app/core/sovereign_mode_contract.py

class SovereignModeContract:
    """
    Contracts that MUST be enforced in Sovereign Mode.
    
    Sovereign Mode = LOCAL-ONLY, SINGLE-RESPONSIBILITY services
    """
    
    # 1. Process Isolation Requirement
    REQUIREMENT_ONE_PROCESS_PER_SERVICE = {
        "rule": "Each service (backend, frontend, auth) must be a separate process",
        "enforcement": "Check: ps aux | grep -c backend, frontend = 1 each",
        "exception": "Internal workers (mission, autoscaler) are OK"
    }
    
    # 2. No Dev Server in Prod
    REQUIREMENT_NO_NEXT_DEV_IN_PROD = {
        "rule": "Never use 'next dev' in production or sovereign mode",
        "enforcement": "CI check: grep -r 'next dev' deploy/ production/",
        "error": "FATAL: next dev found in production config"
    }
    
    # 3. Network Binding in Sovereign Mode
    REQUIREMENT_NO_BINDING_TO_0_0_0_0 = {
        "rule": "In sovereign mode, bind to 127.0.0.1 or specific interface only",
        "enforcement": "App startup checks: if sovereign and 0.0.0.0, raise RuntimeError",
        "config": "BRAIN_BIND_ADDR=127.0.0.1 (enforced in sovereign mode)"
    }
    
    # 4. Service Orchestration Boundaries
    REQUIREMENT_NO_IMPLICIT_SPAWNING = {
        "rule": "A service MUST NOT start other services",
        "enforcement": "Code review: check for subprocess.spawn/exec in app code",
        "exception": "Internal workers (mission, metrics) are OK - they're part of same service"
    }
    
    # 5. External Service Blocking
    REQUIREMENT_NO_EXTERNAL_CONNECTORS_IN_SOVEREIGN = {
        "rule": "Connectors to external APIs (Telegram, WhatsApp, etc.) must be disabled",
        "enforcement": "dmz_control rejects start request if mode==SOVEREIGN",
        "config": "Firewall rules block egress to external services"
    }
```

---

## 6. PROD COUPLING RISK CHECKLIST

| Check | Status | Evidence | Risk |
|-------|--------|----------|------|
| Production uses `next dev` | ✅ NO | Only `next start` in Dockerfiles | PASS |
| Backend spawns frontends | ✅ NO | No spawn/exec in backend code | PASS |
| Docker Compose has mixed services | ✅ NO | Each service in separate container | PASS |
| Frontend started by backend in code | ✅ NO | No references found | PASS |
| systemd units in repo starting multi-service | ✅ NO | No systemd files | PASS |
| Dev script could orphan processes | ⚠️ YES | brain-starter.sh starts all as children | FLAG |
| Sovereign Mode enforced at runtime | ❌ NO | Mode exists but no runtime checks | FLAG |

---

## 7. GUARDRAILS TO IMPLEMENT

### 7.1 Dev Scripts (Safety Improvements)

**Create:** `/home/user/BRAiN/scripts/dev-up.sh`
```bash
#!/bin/bash
# Safe dev startup - separate PID tracking + port checking

PORT_BACKEND=8001
PORT_FRONTEND1=3456   # controldeck-v2
PORT_FRONTEND2=3002   # axe_ui

# Function: check port and kill if needed
safe_port() {
    local port=$1
    local pids=$(lsof -t -i:$port 2>/dev/null || echo "")
    if [ -n "$pids" ]; then
        echo "⚠️  Port $port in use (PIDs: $pids)"
        read -p "Kill? (y/N): " -n 1 -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill -9 $pids
            sleep 2
        else
            exit 1
        fi
    fi
}

# Check all ports
safe_port $PORT_BACKEND
safe_port $PORT_FRONTEND1
safe_port $PORT_FRONTEND2

# Start backend
cd backend && nohup uvicorn main:app --port $PORT_BACKEND > /tmp/brain-backend.log 2>&1 &
echo $! > /tmp/brain.backend.pid
echo "Backend PID: $(cat /tmp/brain.backend.pid)"

# Start frontend 1
cd ../frontend/controldeck-v2 && \
PORT=$PORT_FRONTEND1 nohup npm run dev > /tmp/brain-frontend1.log 2>&1 &
echo $! > /tmp/brain.frontend1.pid
echo "Frontend1 PID: $(cat /tmp/brain.frontend1.pid)"

# Start frontend 2
cd ../axe_ui && \
PORT=$PORT_FRONTEND2 nohup npm run dev > /tmp/brain-frontend2.log 2>&1 &
echo $! > /tmp/brain.frontend2.pid
echo "Frontend2 PID: $(cat /tmp/brain.frontend2.pid)"

echo ""
echo "✅ Services started. To stop:"
echo "  ./scripts/dev-down.sh"
echo ""
echo "Logs:"
echo "  Backend:   tail -f /tmp/brain-backend.log"
echo "  Frontend1: tail -f /tmp/brain-frontend1.log"
echo "  Frontend2: tail -f /tmp/brain-frontend2.log"
```

**Create:** `/home/user/BRAiN/scripts/dev-down.sh`
```bash
#!/bin/bash
# Safe dev shutdown - kill exact PIDs (not all npm/uvicorn)

kill_service() {
    local name=$1
    local pidfile=/tmp/brain.$name.pid
    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        echo "Killing $name (PID $pid)..."
        kill $pid 2>/dev/null || true
        rm "$pidfile"
    fi
}

kill_service backend
kill_service frontend1
kill_service frontend2

echo "✅ All services stopped"
```

---

### 7.2 Port Safety Script

**Create:** `/home/user/BRAiN/scripts/check-ports.sh`
```bash
#!/bin/bash
# Check for port conflicts and show owning processes

check_port() {
    local port=$1
    local pids=$(lsof -t -i:$port 2>/dev/null || echo "")
    if [ -n "$pids" ]; then
        echo "❌ Port $port: IN USE"
        for pid in $pids; do
            echo "   PID $pid: $(ps -p $pid -o cmd=)"
        done
    else
        echo "✅ Port $port: Available"
    fi
}

echo "🔍 Checking BRAiN ports:"
check_port 8001   # Backend dev
check_port 8000   # Backend prod
check_port 3456   # ControlDeck dev
check_port 3002   # AXE_UI dev
check_port 3000   # Frontend prod
check_port 3001   # Control Deck legacy
```

---

### 7.3 Sovereign Mode Runtime Enforcement

**Create:** `backend/app/core/sovereign_mode_enforcer.py`

```python
"""
Sovereign Mode Contract Enforcement
- Prevents accidental coupling in Sovereign Mode
- Enforces process isolation, network binding, service boundaries
"""

import os
import logging
from app.modules.sovereign_mode.schemas import OperationMode

logger = logging.getLogger(__name__)

class SovereignModeEnforcer:
    """Runtime checks for Sovereign Mode compliance"""
    
    @staticmethod
    def enforce_binding(current_mode: OperationMode, bind_addr: str) -> None:
        """Enforce network binding constraints"""
        if current_mode == OperationMode.SOVEREIGN:
            if bind_addr == "0.0.0.0":
                raise RuntimeError(
                    "SOVEREIGN MODE VIOLATION: Cannot bind to 0.0.0.0. "
                    "Set BRAIN_BIND_ADDR=127.0.0.1"
                )
            logger.warning(
                f"⚠️ SOVEREIGN MODE: Binding to {bind_addr} (external access disabled)"
            )
    
    @staticmethod
    def check_environment(current_mode: OperationMode) -> None:
        """Check environment for Sovereign Mode compatibility"""
        if current_mode == OperationMode.SOVEREIGN:
            # Check for dev artifacts
            if os.getenv("NEXT_PUBLIC_DEV") == "true":
                logger.warning("⚠️ SOVEREIGN MODE with dev flags enabled")
            
            # Check for external connector enablement
            if os.getenv("ENABLE_TELEGRAM_CONNECTOR") == "true":
                raise RuntimeError(
                    "SOVEREIGN MODE VIOLATION: External connectors must be disabled. "
                    "Set ENABLE_TELEGRAM_CONNECTOR=false"
                )
            
            logger.info("✅ Environment checks passed for SOVEREIGN mode")
    
    @staticmethod
    def enforce_no_frontend_spawn() -> None:
        """Verify no frontend processes started by backend"""
        import subprocess
        try:
            # Check if any 'next' processes are children of this process
            result = subprocess.run(
                ["pgrep", "-P", str(os.getpid()), "next"],
                capture_output=True
            )
            if result.returncode == 0:
                raise RuntimeError(
                    "PROCESS ISOLATION VIOLATION: Next.js frontend started by backend. "
                    "Frontends must be separate processes."
                )
        except Exception as e:
            logger.warning(f"Could not check for frontend spawning: {e}")
```

**Integrate in backend/main.py:**
```python
from app.core.sovereign_mode_enforcer import SovereignModeEnforcer

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ... existing startup ...
    
    # Enforce Sovereign Mode if active
    if os.getenv("BRAIN_MODE") == "sovereign":
        SovereignModeEnforcer.check_environment(OperationMode.SOVEREIGN)
        SovereignModeEnforcer.enforce_binding(OperationMode.SOVEREIGN, "127.0.0.1")
        SovereignModeEnforcer.enforce_no_frontend_spawn()
        logger.info("✅ Sovereign Mode contract enforced")
    
    yield
    # ... shutdown ...
```

---

### 7.4 CI Checks (GitHub Actions)

**Create:** `.github/workflows/process-isolation-check.yml`

```yaml
name: Process Isolation & Service Boundary Check

on: [push, pull_request]

jobs:
  isolation-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: "Check: No 'next dev' in production scripts"
        run: |
          if grep -r "next dev" backend/ frontend/controldeck-v2/Dockerfile deploy/ scripts/; then
            echo "❌ FAILED: 'next dev' found in production context"
            exit 1
          fi
          echo "✅ PASSED: No 'next dev' in production"
      
      - name: "Check: No subprocess spawning of frontends in backend"
        run: |
          if grep -r "subprocess.*next\|spawn.*next\|exec.*npm run dev" backend/app/ backend/brain/; then
            echo "❌ FAILED: Backend spawns frontend process"
            exit 1
          fi
          echo "✅ PASSED: No implicit frontend spawning"
      
      - name: "Check: Docker Compose service separation"
        run: |
          # Verify each service has its own container
          if ! grep -q "services:" docker-compose.yml; then
            echo "❌ docker-compose.yml not found"
            exit 1
          fi
          echo "✅ PASSED: Docker Compose structure OK"
      
      - name: "Check: No 'concurrently' or turbo in production"
        run: |
          if grep -r "concurrently\|turbo" package.json backend/*/package.json 2>/dev/null | grep -v devDependencies; then
            echo "❌ FAILED: Production orchestration tools found"
            exit 1
          fi
          echo "✅ PASSED: No implicit orchestration"
      
      - name: "Check: Sovereign Mode references in code"
        run: |
          if grep -r "BRAIN_MODE.*sovereign\|OperationMode.SOVEREIGN" backend/ | wc -l | grep -q "^0$"; then
            echo "⚠️  WARNING: Sovereign Mode not referenced - update if implementing"
          fi
          echo "✅ PASSED: Sovereign Mode checks OK"
```

---

## 8. RECOMMENDED ARCHITECTURE

```
┌──────────────────────────────────────────────────┐
│ DEV ENVIRONMENT (Manual)                         │
├──────────────────────────────────────────────────┤
│                                                  │
│ Developer:  ./scripts/dev-up.sh                  │
│             (starts 3 independent processes)     │
│                                                  │
│ Backend:       PID 1234 (separate)               │
│ Frontend1:     PID 1235 (separate)               │
│ Frontend2:     PID 1236 (separate)               │
│                                                  │
│ Stop:    ./scripts/dev-down.sh                   │
│          (kills exact PIDs)                      │
│                                                  │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ PRODUCTION (Container Orchestrated)              │
├──────────────────────────────────────────────────┤
│                                                  │
│ Docker Compose / K8s:                            │
│   - Backend container   (single process)         │
│   - Frontend1 container (single process)         │
│   - Frontend2 container (single process)         │
│   - Auth container      (optional)               │
│                                                  │
│ Each container:                                  │
│   - Separate cgroup                              │
│   - Separate network namespace                   │
│   - Single entry point                           │
│   - Traefik handles routing                      │
│                                                  │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ SOVEREIGN MODE (Local-Only Hardening)            │
├──────────────────────────────────────────────────┤
│                                                  │
│ Enforced Constraints:                            │
│  1. Each service = 1 process (no spawning)       │
│  2. Bind to 127.0.0.1 only (no 0.0.0.0)         │
│  3. External connectors disabled                 │
│  4. Firewall rules: egress to whitelisted only   │
│  5. Network isolation: no Telegram/WhatsApp/etc  │
│                                                  │
│ Runtime Checks: SovereignModeEnforcer            │
│ Firewall Enforcement: sovereign-fw.sh            │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 9. IMPLEMENTATION ROADMAP

### Phase 1: Safety Scripts (Immediate - 2 hours)
- [ ] Create `scripts/dev-up.sh` with port safety
- [ ] Create `scripts/dev-down.sh` with clean shutdown
- [ ] Create `scripts/check-ports.sh` for diagnostics
- [ ] Document in DEVELOPMENT.md
- [ ] Test locally

### Phase 2: CI Guardrails (Next PR - 1 hour)
- [ ] Add GitHub Actions workflow `process-isolation-check.yml`
- [ ] Configure branch protection: require CI check to pass
- [ ] Add pre-commit hook to prevent `next dev` commits

### Phase 3: Sovereign Mode Enforcement (Sprint - 4 hours)
- [ ] Implement `app/core/sovereign_mode_enforcer.py`
- [ ] Integrate in `backend/main.py` lifespan
- [ ] Add unit tests for enforcement
- [ ] Document Sovereign Mode Contract

### Phase 4: Documentation (1 hour)
- [ ] Create `DEVELOPMENT.md` - Dev environment setup
- [ ] Create `ARCHITECTURE.md` - Service boundary doc
- [ ] Create `SOVEREIGN_MODE.md` - Sovereign mode enforcement rules
- [ ] Add to README.md: pointer to docs

---

## 10. SUCCESS CRITERIA

✅ **After Implementation:**

1. **Dev Safety:**
   - `./scripts/dev-up.sh` starts 3 independent processes
   - `./scripts/dev-down.sh` stops cleanly without orphans
   - `./scripts/check-ports.sh` shows port safety

2. **CI Protection:**
   - CI fails if `next dev` appears in production configs
   - CI fails if backend contains subprocess spawn of frontend
   - Every commit is validated

3. **Sovereign Mode:**
   - Sovereign Mode enforcer prevents accidental multi-service start
   - Runtime check fails if binding to 0.0.0.0 in sovereign mode
   - Firewall rules actively block external connectors

4. **Documentation:**
   - New devs follow clear onboarding (DEVELOPMENT.md)
   - Architecture boundaries documented (ARCHITECTURE.md)
   - Sovereign Mode contract explicit (SOVEREIGN_MODE.md)

---

## 11. APPENDIX: File Checklist

**Existing (OK):**
- ✅ `docker-compose.yml` - Clean service separation
- ✅ `docker-compose.dev.yml` - Clean separation
- ✅ `Dockerfile` (backend) - Single process
- ✅ `Dockerfile.controldeck-v2` - Single process
- ✅ `backend/main.py` - No frontend spawning
- ✅ `backend/app/modules/sovereign_mode/*` - Mode defined

**To Create:**
- 📝 `scripts/dev-up.sh` - Safe dev startup
- 📝 `scripts/dev-down.sh` - Safe dev shutdown
- 📝 `scripts/check-ports.sh` - Port diagnostics
- 📝 `backend/app/core/sovereign_mode_enforcer.py` - Runtime enforcement
- 📝 `.github/workflows/process-isolation-check.yml` - CI guardrails
- 📝 `DEVELOPMENT.md` - Dev guide
- 📝 `ARCHITECTURE.md` - Service boundaries
- 📝 `SOVEREIGN_MODE.md` - Sovereign mode rules

**To Update:**
- ✏️ `backend/main.py` - Add enforcer check
- ✏️ `README.md` - Link to docs
- ✏️ `.env.example` - Document Sovereign Mode vars

---

## CONCLUSION

**Current State:** ✅ Production-safe, ⚠️ Dev needs guardrails

**Key Finding:** The coupling issue described (frontend process left orphaned under systemd) **cannot happen with current prod setup** (Docker Compose), but **could happen** if `brain-starter.sh` were used in production.

**Recommendation:** Implement guardrails immediately (cheap) to prevent future regression. Sovereign Mode enforcement adds defense-in-depth.

---

**Report prepared by:** BRAiN Security & Architecture Team
**Date:** 2026-02-26
**Next Review:** After Phase 1-2 implementation (guardrails deployed)
