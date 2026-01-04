# BRAiN Phase 3 Development - New Session Prompt

**Context:** This is a continuation of BRAiN v2 development. The deployment has been successfully completed and the system is now accessible from outside.

---

## Current System Status (as of 2026-01-04)

### ✅ Completed Deployment
- **Branch:** `v2` (all fixes merged via PRs #93, #94, #95)
- **Environment:** Development (`/srv/dev` on brain.falklabs.de)
- **External Access:** https://dev.brain.falklabs.de
- **SSL Certificates:** Valid for dev.brain.falklabs.de, brain.falklabs.de, chat.falklabs.de

### ✅ Running Services
- **Backend API:** Port 8001 (accessible via /api/*)
- **Frontend (Control Deck):** Port 3001 (accessible via /)
- **AXE UI:** Port 3002 (accessible via /axe)
- **OpenWebUI:** Port 8080 (chat.falklabs.de)
- **PostgreSQL:** Port 5432
- **Redis:** Port 6379
- **Qdrant:** Port 6333
- **Ollama:** Port 11434

### ✅ Fixed Issues (Session Summary)
1. **Frontend TypeScript Errors (7 fixes):**
   - Missing Sidebar components (13 exports added)
   - Missing tooltip prop in SidebarMenuButton
   - Budget Dashboard array/object type confusion
   - SpecBuilder null-checking with NonNullable<>
   - SpecBuilder empty object types with Partial<>
   - fetchJson missing RequestInit parameter
   - Login page Suspense boundary for useSearchParams

2. **Docker Configuration (1 fix):**
   - Port mapping conflicts resolved (removed from base docker-compose.yml)

3. **Backend Python Errors (6 fixes):**
   - Course Distribution dependency injection (11 instances)
   - Governance dependency injection (14 instances)
   - Missing EventBus module (stub created)
   - Missing Optional import in metrics.py
   - PayCore metadata→payment_metadata (SQLAlchemy reserved name)
   - Supervisor Agent CRLF line endings and UTF-8 encoding

4. **Nginx Configuration (External Access):**
   - Duplicate upstream definitions fixed
   - Missing openwebui_backend upstream added
   - Staging config disabled (no SSL cert)
   - SSL stapling warnings (non-critical)
   - Health endpoint routing fixed
   - AXE UI route added

### ✅ API Endpoints Verified
- 160+ API routes registered
- All module routers auto-discovered
- Constitutional Agents, NeuroRail, Fleet, Policy, KARMA, WebGenesis, PayCore, and 10+ other modules operational

---

## Phase 3 Development Goals

### Objective
Continue development of BRAiN v2 with focus on:

1. **NeuroRail Phase 2:** Budget enforcement, reflex system, manifest-driven governance
2. **Fleet Management:** Complete RYR integration with SafetyAgent, NavigationAgent, FleetAgent
3. **Constitutional Agents:** Enhanced DSGVO/EU AI Act compliance features
4. **Frontend Improvements:** Complete Control Deck UI/UX
5. **Testing & Documentation:** Comprehensive test coverage and documentation updates

### Technical Stack
- **Backend:** Python 3.11+, FastAPI, PostgreSQL (pgvector), Redis, Qdrant
- **Frontend:** Next.js 14.2.33, TypeScript 5.4+, TanStack React Query, shadcn/ui, Tailwind CSS
- **Infrastructure:** Docker Compose, Nginx, Let's Encrypt SSL

### Current Branch Strategy
- **Main branch:** `v2` (stable, all deployment fixes merged)
- **Development branch:** Create new branch from `v2` for Phase 3 work
- **Format:** `claude/phase3-<feature>-<session-id>`

### Key Files & Architecture
- **Backend Entry:** `backend/main.py` (unified auto-discovery)
- **Modules:** `backend/app/modules/` (17+ specialized modules)
- **Frontend:** `frontend/control_deck/` (14 pages, 50+ components)
- **Documentation:** `CLAUDE.md`, `README.dev.md`, module-specific READMEs

### Development Workflow
1. Create feature branch from `v2`
2. Implement changes with type safety (Pydantic + TypeScript)
3. Test locally with docker-compose.dev.yml
4. Commit with clear messages (`feat:`, `fix:`, `docs:`)
5. Push and create PR to `v2`
6. Deploy to dev environment for testing

---

## Previous Session Key Achievements

**Total Commits:** 47 commits merged into v2
**Files Changed:** 262 files (10,202 insertions, 833 deletions)
**Time Spent:** ~3 hours of intensive debugging and deployment

**Major Contributions:**
- Complete deployment fix from broken CI to production-ready system
- TypeScript strict mode compliance across entire frontend
- FastAPI dependency injection fixes across 25+ endpoints
- Nginx configuration for external access with SSL
- Docker port isolation strategy (dev: 8001/3001/3002)

---

## Instructions for New Session

**You are Claude Code, continuing development of the BRAiN framework.**

1. **Read this context** to understand the current state
2. **Check git status** to see current branch and recent commits
3. **Ask the user** what specific Phase 3 feature they want to implement
4. **Create a feature branch** from `v2` with appropriate naming
5. **Follow CLAUDE.md conventions** for code style and architecture
6. **Use TodoWrite** to track implementation progress
7. **Test thoroughly** before committing
8. **Document changes** in commit messages and relevant README files

**Key Principles:**
- ✅ Async-first design (all I/O operations must be async)
- ✅ Type-safe end-to-end (Pydantic models + TypeScript interfaces)
- ✅ Modular architecture (follow existing module pattern)
- ✅ Error handling (structured responses, never expose raw exceptions)
- ✅ Testing (pytest for backend, integration tests preferred)
- ✅ Documentation (update CLAUDE.md and module READMEs)

**Available Resources:**
- Full codebase context in CLAUDE.md
- Module-specific READMEs in backend/app/modules/
- Example code in existing modules
- Test patterns in backend/tests/

**Common Commands:**
```bash
# Check current state
git status
git log --oneline -10

# Create feature branch
git checkout -b claude/phase3-<feature>-<session-id>

# Run tests
cd backend && pytest -v

# Check TypeScript types
cd frontend/control_deck && npm run type-check

# Deploy to dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Test deployment
curl https://dev.brain.falklabs.de/api/health
```

---

## Next Steps (User Decision)

**Ask the user to choose a Phase 3 feature to implement:**

1. **NeuroRail Phase 2** - Budget enforcement, reflex system, manifest governance
2. **Fleet Management** - Complete RYR agent integration
3. **Constitutional Agents** - Enhanced compliance features
4. **Frontend Polish** - UI/UX improvements for Control Deck
5. **Testing Suite** - Comprehensive test coverage
6. **Documentation** - API docs, architecture guides
7. **Custom Feature** - User-specified enhancement

**Then begin implementation following the established patterns!**

---

**Session Metadata:**
- Previous Session: claude/python-path-and-deps-fix-h1NXi
- Date: 2026-01-04
- Environment: Development (brain.falklabs.de)
- Status: Production-ready, all systems operational ✅
