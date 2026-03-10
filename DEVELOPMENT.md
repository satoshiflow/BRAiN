# BRAiN Development Environment Setup

**Last Updated:** 2026-02-26  
**Status:** Safe Dev Scripts (Phase 1+2 Guardrails Deployed)

---

## Quick Start

### 1️⃣ Check Ports

Before starting, verify required dev ports are available:

```bash
./scripts/check-ports.sh
```

**Output:**
```
✓ Port 8001 (Backend): Available
✓ Port 3456 (ControlDeck-v2): Available
✓ Port 3002 (AXE_UI): Available
```

If ports are in use:
```bash
# Show which PID owns each port
./scripts/check-ports.sh --verbose

# Kill a process using a port
lsof -t -i :PORT | xargs kill -9
```

### 2️⃣ Start All Services

```bash
./scripts/dev-up.sh --all
```

**Output:**
```
ℹ Starting backend (port 8001)...
✓ backend running (PID: 12345)

ℹ Starting controldeck-v2 (port 3456)...
✓ controldeck-v2 running (PID: 12346)

ℹ Starting axe_ui (port 3002)...
✓ axe_ui running (PID: 12347)

✅ BRAiN Services Started

🔗 URLs:
   Backend API:  http://127.0.0.1:8001/api/health
   ControlDeck:  http://localhost:3456
   AXE_UI:       http://localhost:3002
```

### 3️⃣ Check Status

At any time, see what's running:

```bash
./scripts/dev-status.sh
```

**Output:**
```
╔════════════════════════════════════════════════════════════╗
║          BRAiN Development Services Status                ║
╚════════════════════════════════════════════════════════════╝

Service              Status   Port     Command
---                  ---      ---      ---
backend              RUNNING  8001     uvicorn main:app
controldeck-v2       RUNNING  3456     node_modules/.bin/next
axe_ui               RUNNING  3002     node_modules/.bin/next

📁 PID files: /home/user/BRAiN/.brain/dev-pids
📁 Log files: /home/user/BRAiN/.brain/dev-logs
```

### 4️⃣ View Logs

```bash
# Show last 10 lines of each log
./scripts/dev-status.sh --logs

# Tail backend logs in real-time
tail -f .brain/dev-logs/backend.log

# Tail frontend logs
tail -f .brain/dev-logs/controldeck-v2.log
tail -f .brain/dev-logs/axe_ui.log
```

### 5️⃣ Stop All Services

```bash
./scripts/dev-down.sh
```

**Output:**
```
🛑 Stopping BRAiN services...

ℹ Stopping backend (PID 12345)...
✓ backend stopped (PID 12345)

ℹ Stopping controldeck-v2 (PID 12346)...
✓ controldeck-v2 stopped (PID 12346)

ℹ Stopping axe_ui (PID 12347)...
✓ axe_ui stopped (PID 12347)

✓ All services stopped successfully
✓ All ports are now available
```

---

## Advanced Usage

### Start Only Specific Services

```bash
# Backend only
./scripts/dev-up.sh --only backend

# ControlDeck frontend only
./scripts/dev-up.sh --only controldeck

# AXE_UI frontend only
./scripts/dev-up.sh --only axe_ui
```

### Run in Foreground (for debugging)

```bash
# Start backend in foreground (Ctrl+C to stop)
./scripts/dev-up.sh --only backend --foreground

# Useful for:
# - Seeing log output directly
# - Debugging startup issues
# - Using Python debugger (pdb)
```

### Force Kill Services

If normal shutdown hangs:

```bash
./scripts/dev-down.sh --kill
```

---

## Service Details

### Backend

| Attribute | Value |
|-----------|-------|
| **Language** | Python (FastAPI) |
| **Dev Port** | 8001 |
| **Prod Port** | 8000 |
| **Entry** | `uvicorn main:app` |
| **Directory** | `backend/` |
| **Logs** | `.brain/dev-logs/backend.log` |
| **API** | `http://127.0.0.1:8001/api/health` |

**Key Services:**
- Mission Worker (internal)
- Metrics Collector (internal)
- Autoscaler (internal)

### ControlDeck-v2 (Primary Frontend)

| Attribute | Value |
|-----------|-------|
| **Language** | Next.js 15 (TypeScript+React) |
| **Dev Port** | 3456 |
| **Prod Port** | 3000 |
| **Entry** | `npm run dev` (next dev) |
| **Directory** | `frontend/controldeck-v2/` |
| **Logs** | `.brain/dev-logs/controldeck-v2.log` |
| **URL** | `http://localhost:3456` |

**Features:**
- Main control interface
- Mission management
- Agent configuration
- Settings panel

### AXE_UI (Dashboard)

| Attribute | Value |
|-----------|-------|
| **Language** | Next.js 15 (TypeScript+React) |
| **Dev Port** | 3002 |
| **Prod Port** | 3000 |
| **Entry** | `npm run dev` (next dev) |
| **Directory** | `frontend/axe_ui/` |
| **Logs** | `.brain/dev-logs/axe_ui.log` |
| **URL** | `http://localhost:3002` |

**Features:**
- AXE intelligence dashboard
- Real-time metrics
- Agent status
- Query interface

---

## Troubleshooting

### "Port already in use"

```bash
# Identify what's using the port
lsof -i :8001  # or :3456, :3002

# Kill it
lsof -t -i :8001 | xargs kill -9

# Verify it's freed
./scripts/check-ports.sh
```

### "Process died immediately"

Check the logs:

```bash
tail -20 .brain/dev-logs/backend.log
tail -20 .brain/dev-logs/controldeck-v2.log
```

**Common causes:**
- Missing dependencies (run `pip install -e .` in backend, `npm install` in frontends)
- Wrong environment variables (check `.env`)
- Port conflict (run `check-ports.sh`)
- Database connection issue (check `DATABASE_URL`)

### "Stale PID files"

If a service crashed and left a stale PID:

```bash
# Clean up manually
rm -f .brain/dev-pids/*.pid

# Then start fresh
./scripts/dev-up.sh --all
```

### Frontend shows "Cannot GET /"

The frontend is running but backend isn't responding. Check:

```bash
# Backend running?
./scripts/dev-status.sh

# Backend responding?
curl http://127.0.0.1:8001/api/health

# Check frontend logs
tail -20 .brain/dev-logs/controldeck-v2.log
```

### "Too many open files"

Your system ulimit is too low. Increase it:

```bash
ulimit -n 4096
./scripts/dev-up.sh --all
```

Make it permanent in `~/.bash_profile`:

```bash
ulimit -n 4096
```

---

## Environment Variables

### Backend (`backend/.env`)

```bash
# Database
DATABASE_URL=postgresql://localhost/brain_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Features
ENABLE_MISSION_WORKER=true
BRAIN_EVENTSTREAM_MODE=required
BRAIN_LOG_LEVEL=debug
```

### Frontends

Environment variables are read from Next.js build:

```bash
# In frontend/controldeck-v2/.env.local
NEXT_PUBLIC_BRAIN_API_BASE=http://127.0.0.1:8001
NEXT_PUBLIC_APP_NAME=BRAiN Control Deck
```

---

## IMPORTANT: Never do this in Dev

### ❌ Don't Use Deprecated brain-starter.sh

```bash
# DEPRECATED - don't use
./brain-starter.sh

# USE INSTEAD
./scripts/dev-up.sh --all
```

### ❌ Don't Mix Orchestrators

```bash
# DON'T: Run multiple times
./scripts/dev-up.sh --all
./scripts/dev-up.sh --all  # Creates duplicate processes!

# DO: Use dev-status to check, then stop first
./scripts/dev-down.sh
./scripts/dev-up.sh --all
```

### ❌ Don't Kill with KILL immediately

```bash
# DON'T: Kills immediately
kill -9 12345

# DO: Allows graceful shutdown
./scripts/dev-down.sh
```

---

## Architecture: One Service = One Responsibility

```
┌─────────────────────────────────────────────┐
│ Your Terminal / IDE                         │
└─────────────────────┬───────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────────┐  ┌──────────┐  ┌──────────┐
│   Backend   │  │Frontend1 │  │Frontend2 │
│  (Port 8001)│  │(Port3456)│  │(Port3002)│
│    PID A    │  │  PID B   │  │  PID C   │
└─────────────┘  └──────────┘  └──────────┘

.brain/dev-pids/
├── backend.pid         (PID A)
├── controldeck-v2.pid  (PID B)
└── axe_ui.pid          (PID C)

.brain/dev-logs/
├── backend.log
├── controldeck-v2.log
└── axe_ui.log
```

**Key Principle:**
- Each service = separate process (separate PID)
- Each service = separate log file
- No orchestration within one service
- Services start/stop INDEPENDENTLY

---

## Sovereign Mode (Offline/Local-Only)

When testing Sovereign Mode (high-security, local-only):

```bash
# Start with Sovereign Mode
BRAIN_MODE=sovereign ./scripts/dev-up.sh --all

# Enforced constraints:
# ✓ Backend binds to 127.0.0.1 only (not 0.0.0.0)
# ✓ External connectors disabled (Telegram, WhatsApp, etc.)
# ✓ Firewall rules: egress to whitelisted endpoints only
```

See `SOVEREIGN_MODE.md` for details.

---

## FAQ

**Q: How do I switch between backend/frontend development?**

```bash
# Only develop backend
./scripts/dev-down.sh
./scripts/dev-up.sh --only backend

# Add frontend later
./scripts/dev-up.sh --only controldeck
```

**Q: Can I use Docker Compose for dev instead?**

Yes, if you prefer containers:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

But the shell scripts are lighter and faster.

**Q: How do I debug the backend?**

```bash
# Start in foreground
./scripts/dev-up.sh --only backend --foreground

# Use Python debugger (pdb)
# In your code: import pdb; pdb.set_trace()
# In terminal: Ctrl+C and debug interactively
```

**Q: Why .brain/ directory?**

- `.brain/` is gitignored (local dev state only)
- Keeps repo clean
- Safe to rm -rf (everything is recreatable)

---

## Security Notes

### Never run orchestrator scripts under systemd

```bash
# ❌ WRONG - can orphan processes
[Service]
ExecStart=/path/to/BRAiN/brain-starter.sh

# ✅ RIGHT - each service as separate unit
[Service]
ExecStart=/path/to/BRAiN/scripts/dev-up.sh --only backend
```

### Never use `next dev` in production

- `next dev` is for development only (hot reload, slow)
- Production uses `next start` (pre-built, fast)
- CI checks will fail if `next dev` appears in prod configs

---

## Next Steps

After getting comfortable with the scripts:

1. **Backend Dev:** Edit `backend/app/modules/*/` files → restart backend only
2. **Frontend Dev:** Edit `frontend/controldeck-v2/app/` files → hot reload (no restart)
3. **Full Stack:** Run both in separate terminal windows

---

## Still Need Help?

- Check logs: `./scripts/dev-status.sh --logs`
- Show status: `./scripts/dev-status.sh`
- Port debug: `./scripts/check-ports.sh --verbose`
- Kill hung process: `./scripts/dev-down.sh --kill`

---

**Questions? Open an issue or check the ARCHITECTURE.md for deeper details.**
