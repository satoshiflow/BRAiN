# AGENTS.md

Repository guidance for autonomous coding agents working in `BRAiN`.

## 1) Project layout (working mental model)

- Monorepo with a Python FastAPI backend and multiple Next.js frontends.
- Backend primary runtime entrypoint: `backend/main.py`.
- New backend modules live in: `backend/app/modules/*`.
- Legacy compatibility surface still exists in: `backend/modules/*`, `backend/api/routes/*`, `backend/app/compat/*`.
- Event backbone: `backend/mission_control_core/core/event_stream.py` (ADR-001 required by default).

## 2) Rule sources you must follow

- Canonical BRAiN design direction is documented in `DESIGN.md` and must be honored for identity, purpose, routing, autonomy mode, and integration boundaries.
- Copilot instructions exist at: `.github/copilot-instructions.md`.
- Cursor rules were not found (`.cursorrules` and `.cursor/rules/` absent at repo root).
- Security/architecture constraints are also documented in `CLAUDE.md` and must be honored.
- Agent operating model is documented in `docs/core/agent_operating_matrix.md`.
- Permanent agent setup guidance is documented in `docs/core/agent_cluster_setup_guide.md`.
- Mission deliberation and insight evolution architecture is documented in `docs/specs/mission_deliberation_insight_evolution.md`.
- Local micro setup (resource-efficient): `.opencode/skills/brain-local-micro/SKILL.md`

### Copilot instruction highlights (applied here)

- Prefer Docker Compose for full local stack.
- Keep route contracts stable; many APIs are consumed by UI/tests.
- Use connector/gateway abstractions instead of hardcoded provider wiring.
- When API signatures change, update backend tests and impacted frontend callers.

## 3) Build, lint, test, run commands

All commands below are from repo root unless noted.

### Backend run

- Local dev stack (recommended):
  - `docker compose -f docker-compose.local.yml --env-file .env.local up -d --build`
- Full stack with all features:
  - `docker compose up -d --build`
- Dev stack variant:
  - `docker compose -f docker-compose.dev.yml up --build`
- Production stack:
  - `docker compose -f docker-compose.prod.yml up -d --build`
- Local backend run (without Docker):
  - `cd backend && pip install -r requirements.txt`
  - `cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000`

### Backend tests

- Run all backend tests:
  - `cd backend && PYTHONPATH=. pytest`
- Run one test file:
  - `cd backend && PYTHONPATH=. pytest tests/test_module_auth.py -q`
- Run one test case:
  - `cd backend && PYTHONPATH=. pytest tests/test_module_auth.py::test_requires_auth -q`
- Run tests by expression:
  - `cd backend && PYTHONPATH=. pytest -k "auth and not slow" -q`

### RC/staging gate (important)

- Canonical pre-merge backend verification:
  - `./scripts/run_rc_staging_gate.sh`
- This script runs targeted pytest suites plus guardrail scripts:
  - `scripts/check_no_legacy_event_bus.py`
  - `scripts/check_no_utcnow_auth.py`
  - `scripts/check_no_utcnow_planning.py`
  - `scripts/critic_gate.py`

### Backend lint/type checks (used in repo docs)

- Module-level checks used in guidance (`CLAUDE.md`):
  - `ruff check backend/app/modules/<MODULE>/`
  - `black --check backend/app/modules/<MODULE>/`
  - `mypy backend/app/modules/<MODULE>/ --no-error-summary`
- If you touch a backend module, run at least targeted tests + RC gate.

### Frontend commands

- `frontend/controldeck-v2`:
  - `npm install`
  - `npm run dev`
  - `npm run build`
  - `npm run lint`
  - `npm run test`
  - Single test example: `npm run test -- src/path/to/file.test.ts`
  - E2E: `npm run test:e2e`
- `frontend/control_deck`, `frontend/axe_ui`, `frontend/brain_ui`:
  - `npm install && npm run dev`
  - `npm run build`
  - `npm run lint`
- `frontend/axe_ui` type-check:
  - `npm run typecheck`

## 4) Coding conventions (backend Python)

### Imports

- Group imports as: stdlib -> third-party -> local (`app.*`, `mission_control_core.*`).
- Prefer absolute imports from `app.*` in backend runtime code.
- Do not introduce new direct `modules.*` imports in app runtime paths.
- Legacy access should go through `backend/app/compat/*` adapters.

### Formatting and structure

- Follow Black-compatible formatting (88-char style is acceptable).
- Use explicit Pydantic models for request/response schemas.
- Keep routers thin; business logic belongs in `service.py`.
- Prefer async-first implementations in backend code.

### Types

- Add type hints for public functions/methods.
- Use `Optional[T]` / `T | None` consistently within each file.
- Keep schema/type names explicit (`<Domain><Action>Request/Response`).

### Naming

- Files: `snake_case.py`.
- Classes: `PascalCase`.
- Functions/variables: `snake_case`.
- Constants/env flags: `UPPER_SNAKE_CASE`.
- Router objects should remain named `router`.

### Error handling

- Never leak internals in HTTP responses.
- Pattern: log full error server-side, return sanitized `HTTPException` message.
- Prefer explicit status codes and consistent response schemas.
- Avoid broad silent `except`; if fallback is intentional, log why.

### Security-critical rules

- All mutating endpoints require auth/role checks.
- Validate untrusted input with Pydantic constraints.
- No hardcoded secrets; use environment variables.
- Avoid `subprocess_shell`; prefer safe exec patterns.
- Audit/event emission required for sensitive operations.

## 5) Coding conventions (frontend TypeScript/Next.js)

- Use strict TypeScript types for props/api responses.
- Keep API clients centralized (avoid duplicate fetch logic).
- Prefer existing design system/components and current project structure.
- Run lint/build before finalizing frontend changes.
- MUST HAVE: never hardcode real deployment URLs or localhost hosts inside runtime app feature code.
  Route all AXE/control-deck/widget service resolution through the central config/runtime resolver.
  Hardcoded hosts are only acceptable in explicit test files, runbooks, or local-only examples.
- MUST HAVE: isolate Next.js runtime artifacts by execution mode (`NEXT_DIST_DIR`), and avoid concurrent
  dev/test servers writing to the same dist directory/port. E2E must use a dedicated port/distDir or
  reuse an already-running server cleanly.

## 6) Architecture boundaries to preserve

- New backend features should be implemented under `backend/app/modules/*`.
- Keep EventStream as the canonical event backbone.
- Treat `backend/modules/*` as legacy; migrate incrementally, do not expand.
- Keep compatibility shims concentrated in `backend/app/compat/*`.
- Keep `SkillRun` as the canonical execution record; do not introduce a parallel runtime object.
- Keep `backend/app/modules/domain_agents/*` as the upper routing and review spine for new purpose/routing work.
- Keep lower provider resolution in `backend/app/modules/provider_bindings/*` and `app.core.capabilities.*` rather than moving it into upper routing.
- Keep learning and evolution attached to `experience -> insight -> consolidation/pattern -> evolution` rather than creating a separate routing-learning subsystem.

## 6.1) Autonomy and control mode

- Default operating mode is `brain_first`: BRAiN decides and acts autonomously within active governance.
- Human control is optional by default and is exercised through AXE for observation, explanation, approval when policy requires it, and override when explicitly allowed.
- ControlDeck is the primary configuration and governance surface for governed-editable profiles, routing policies, and operational settings.
- Human approval is required only for policy-defined sensitive, breakglass, or promotion-critical actions.
- OpenCode must be treated as a bounded execution plane under BRAiN-issued contracts, not as an independent sovereign system.

## 7) Change workflow for agents

- Make minimal, scoped changes; avoid unrelated refactors.
- Update/add tests with behavior changes.
- For backend runtime edits, run targeted pytest and `./scripts/run_rc_staging_gate.sh`.
- If command output reveals environment blockers, document them clearly.
- Keep docs aligned when adding modules/routes/migrations.
- For purpose/routing/autonomy work, update `DESIGN.md` first or in the same change when you alter canonical boundaries or terminology.
- Prefer extending existing modules and contracts over adding new top-level systems or registries.
- Validate self-improvement, routing optimization, and workflow changes in sandbox/replay-oriented paths before enabling production promotion.

## 8) Quick checklist before handing off

- Code compiles and changed tests pass locally.
- No new unauthorized legacy imports.
- No secrets added to repository.
- New endpoints include auth + validation + sanitized errors.
- Relevant docs updated (`docs/roadmap` / `docs/architecture` when applicable).

## 9) High-value file references

- Backend entrypoint: `backend/main.py`
- Core security/auth: `backend/app/core/security.py`, `backend/app/core/auth_deps.py`
- Event contract/bridge: `backend/app/core/event_contract.py`, `backend/app/core/audit_bridge.py`
- Compatibility boundary: `backend/app/compat/*`
- RC gate script: `scripts/run_rc_staging_gate.sh`
- Copilot instructions: `.github/copilot-instructions.md`
- Neural Core (Brain 3.0): `backend/app/neural/core.py`, `backend/app/neural/router.py`
- Docker Compose: `docker-compose.local.yml`, `docker-compose.prod.yml`

## 10) Documentation cadence (execution governance)

- Keep architecture migration work documented under `docs/specs/*` and `docs/roadmap/*`.
- Keep canonical identity, purpose, routing, and BRAiN-first autonomy design aligned with `DESIGN.md`.
- For skill/runtime execution work, align specs with `docs/core/brain_skill_execution_standard.md`.
- For multi-agent execution, align role usage and parallelization with `docs/core/agent_operating_matrix.md`.
- For domain-aware orchestration work, align boundaries and rollout with `docs/specs/domain_agent_contract.md` and `docs/specs/domain_agent_integration_plan.md`.
- Align long-running delivery execution with `docs/roadmap/BRAIN_SKILL_FIRST_IMPLEMENTATION_ROADMAP.md`.
- Track the parallel learning/research delivery strand in `docs/roadmap/BRAIN_MISSION_DELIBERATION_INSIGHT_ROADMAP.md`.
- For each Epic-level change, capture: scope, contracts, risks, and done criteria.
- Record major architecture observations discovered during implementation when they affect future layering, learning, mission behavior, or evolution.
- Use this review flow for spec-driven work:
  - `GROUNDING -> STRUCTURE -> CREATION -> EVALUATION -> FINALIZATION`
- When introducing new runtime contracts, specify:
  - field model, lifecycle, validation, error codes, minimal API, event types
  - PostgreSQL (durable) vs Redis (ephemeral/event) ownership
- For governance-sensitive runtime flows, also specify:
  - auth/role/scope matrix
  - tenant isolation rules
  - approval/breakglass semantics
  - audit durability and event publication ordering
- For purpose/routing/runtime integration work, also specify:
  - `DecisionContext`, `PurposeEvaluation`, `TaskProfile`, and `RoutingDecision` ownership
  - how the flow terminates in `SkillRun`
  - how AXE, ControlDeck, and OpenCode participate without creating a second runtime or second governance layer
- For registry/control-plane contracts, also specify:
  - canonical source of truth vs bootstrap/cache layers
  - deterministic resolution rules and ambiguity handling
  - activation/version invariants
  - legacy compatibility and deprecation boundaries
- For mission/knowledge/evolution work, also specify:
  - execution anchor vs deliberation artifact boundary
  - insight/pattern/knowledge promotion path
  - selection signals and governance gates
  - unresolved tensions that should remain explicit instead of being collapsed prematurely
- Keep AGENTS guidance updated when process conventions change.

## 11) Agent execution model

- Use role-based orchestration, not generic parallel prompting.
- Default working roles:
  - `brain-orchestrator`
  - `brain-architect`
  - `brain-domain-orchestrator`
  - `brain-schema-designer`
  - `brain-runtime-engineer`
  - `brain-migration-engineer`
  - `brain-security-reviewer`
  - `brain-verification-engineer`
  - `brain-repo-scout`
  - `brain-docs-scribe`
  - `brain-review-critic`
- Prefer stronger models for expensive mistakes:
  - architecture, security, migration, critical review -> strongest available model
  - implementation, tests, iterative coding -> primary coding model
  - repo exploration, summaries, inventories -> lower-cost model
- Many agents may analyze in parallel, but one writer owns a given implementation surface at a time.

## 12) GitHub specialist agent (`giti`) guidance

- `giti` is the preferred specialist for Git/GitHub workflows (branch hygiene, PR create/edit, PR metadata updates).
- Follow `docs/core/giti_playbook.md` for mandatory preflight checks and PR decision flow.
- Before any PR action, ensure:
  - `gh` is installed and available in PATH
  - `gh auth status` is authenticated for the intended account
  - existing PR state is checked to avoid duplicate PR creation
- Prefer `gh pr edit` when a PR already exists for the branch.
- Use `--body-file` for PR body updates to avoid shell quoting/substitution issues.
- For long-lived branches, summarize the intended incremental delta, not the full historical diff.

## 13) Local CI fallback mode (GitHub Actions unavailable)

Use this mode when GitHub CI cannot run (for example billing lock, runner outage, or org policy block).

### Operating principles

- Do not block implementation work only because remote CI is unavailable.
- Treat local verification as the authoritative gate until remote CI is restored.
- Keep changes scoped and incremental; avoid large mixed changesets.

### Required local verification by surface

Recommended helper script (from repo root):

- `./scripts/local_ci_gate.sh <backend|backend-fast|axe|axe-fast|all>`
- The script writes a timestamped evidence report under `docs/roadmap/local_ci/`.
- Optional automation: `./scripts/install_git_hooks.sh` to enable pre-push local CI checks.

Backend changes:

- Minimum loop verification:
  - `cd backend && PYTHONPATH=. pytest <targeted suites> -q`
- Pre-handoff and merge-candidate verification:
  - `./scripts/run_rc_staging_gate.sh`

AXE UI changes:

- Run in `frontend/axe_ui`:
  - `npm run lint`
  - `npm run typecheck`
  - `npm run build`
  - `npm run test:e2e`
- During intermediate loops, chromium-only E2E is acceptable; run full matrix before phase close.

### Evidence requirements

For each delivery slice, record:

- commands executed
- pass/fail result
- notable warnings or blockers
- timestamp

Store evidence in handoff notes or roadmap/progress docs so status remains auditable without GitHub checks.

### Branch and PR behavior while CI is blocked

- Continue normal branch hygiene and small commits.
- Keep PRs as coordination artifacts, but do not rely on GitHub check status while blocked.
- If branch protection blocks merge on required checks, continue local-verified branch progression until CI is restored.

### Re-entry when GitHub CI is restored

1. Rebase or merge latest `main` into the working branch.
2. Re-run full local verification gates.
3. Re-run GitHub Actions checks.
4. Resolve drift and only then merge.

## 14) AXE Streaming + Self-Healing Tools

This section documents the machine-readable tools available for AXE streaming and self-healing integration.

### AXE Stream Events

- **Module**: `backend/app/modules/axe_streams/`
- **Endpoint**: `GET /api/axe/runs/{run_id}/events` (SSE)
- **Events emitted**:
  - `axe.run.created` - Run was created
  - `axe.run.state_changed` - Run state transitioned (queued → planning → running → succeeded/failed)
  - `axe.run.succeeded` - Run completed successfully
  - `axe.run.failed` - Run failed
  - `axe.token.stream` - Token delta (when streaming enabled)
  - `axe.error` - Error occurred

### Self-Healing Integration

- **Module**: `backend/app/modules/skill_engine/service.py`
- **On Failure**: SkillEngine automatically triggers Immune Orchestrator with appropriate severity
- **Failure Mapping**:
  - timeout failures → WARNING severity, MEDIUM blast radius
  - provider failures → CRITICAL severity, HIGH blast radius
  - approval denials → WARNING severity, LOW blast radius

### Available Tool Schemas

```json
{
  "tool": "skill_run_retry",
  "description": "Retry a failed SkillRun with exponential backoff",
  "parameters": {
    "run_id": "UUID of failed run",
    "max_attempts": 3,
    "backoff_multiplier": 2.0
  }
}
```

```json
{
  "tool": "axe_stream_health",
  "description": "Check health of AXE streaming subsystem",
  "parameters": {}
}
```

### For Agents

When handling AXE chat failures:
1. Query the run status via `GET /api/axe/runs/{run_id}`
2. Subscribe to events via `GET /api/axe/runs/{run_id}/events`
3. On failure, the system automatically triggers self-healing via Immune Orchestrator
4. Recovery decisions (RETRY/ESCALATE/ISOLATE) come from `recovery_policy_engine`

## 15) Brain 3.0 - Neural Core Architecture

This section documents the Brain 3.0 Neural Core - a data-first architecture where the database is the brain and code is the executor.

### Core Concept

- **Database as Brain**: Parameters and weights are stored in the database, changeable at runtime without redeployment
- **Code as Executor**: The neural network logic executes based on DB-stored parameters
- **Runtime Parameter Changes**: Modify behavior instantly via API without redeploy

### Module Location

- **Module**: `backend/app/neural/`
- **Entry**: `backend/app/neural/core.py` (NeuralCore service)
- **Router**: `backend/app/neural/router.py` (REST API)
- **Database Tables**:
  - `neural_synapses` - Connections between modules
  - `brain_parameters` - Runtime parameters (creativity, caution, speed, etc.)
  - `brain_states` - Pre-configured parameter combinations
  - `synapse_executions` - Execution logging for analytics

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/neural/health` | Health check |
| `GET /api/neural/parameters` | List all parameters |
| `GET /api/neural/parameters/{key}` | Get single parameter |
| `POST /api/neural/parameters` | Update parameter |
| `GET /api/neural/states` | List all states |
| `GET /api/neural/states/{state_name}` | Get single state |
| `POST /api/neural/states` | Update state |
| `GET /api/neural/synapses` | List synapses (filter by capability) |
| `GET /api/neural/synapses/{synapse_id}` | Get synapse details |
| `POST /api/neural/execute` | Execute action through neural network |
| `GET /api/neural/stats` | Execution statistics |

### Key Parameters (stored in DB)

- `creativity` - Creativity weight (0.0-1.0)
- `caution` - Caution weight (0.0-1.0)
- `speed` - Execution speed (0.0-1.0)
- `learning_rate` - Learning rate for auto-tuning
- `execution_timeout` - Max execution time in seconds
- `max_retries` - Max retry attempts

### Pre-configured States

- `default` - Standard behavior (creativity=0.7, caution=0.5, speed=0.8)
- `creative` - High creativity mode (creativity=0.95, caution=0.2, speed=0.6)
- `fast` - Fast execution mode (creativity=0.4, caution=0.7, speed=0.95)
- `safe` - Safe mode (creativity=0.3, caution=0.95, speed=0.5)

### Synapses (routing connections)

- `skill_execute` → routes to skill_engine
- `skill_list` → routes to skill_engine
- `memory_store` → routes to memory module
- `memory_recall` → routes to memory module
- `planning_decompose` → routes to planning module
- `policy_evaluate` → routes to policy module

### Testing the Neural Core

```bash
# Local Docker stack
docker compose -f docker-compose.local.yml --env-file .env.local up -d

# Test endpoints
curl http://localhost:8000/api/neural/health
curl http://localhost:8000/api/neural/parameters
curl http://localhost:8000/api/neural/states
curl http://localhost:8000/api/neural/synapses

# Update parameter (runtime change)
curl -X POST http://localhost:8000/api/neural/parameters \
  -H "Content-Type: application/json" \
  -d '{"key": "creativity", "value": 0.95}'

# Execute action (uses current parameters)
curl -X POST http://localhost:8000/api/neural/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "execute", "payload": {"skill": "test"}, "context": {}}'

# Get execution stats
curl "http://localhost:8000/api/neural/stats?hours=24"
```

### Architecture Principles

1. **Data-first**: All weights/parameters in DB, not hardcoded
2. **Runtime mutability**: Parameters can change without redeploy
3. **Execution logging**: Every execution is logged for analytics
4. **State presets**: Pre-configured parameter combinations for common modes
5. **Synapse routing**: Actions map to modules via synapse connections

### For Agents

When working on Neural Core:
- Always use the NeuralCore service methods, not direct DB queries
- Parameters are cached with 60s TTL; cache clears on update
- Execution logs feed into the learning loop for auto-tuning
- New synapses can be registered via the API for module connections

## 16) Odoo 19 Connector Integration

This section documents the Odoo 19 integration for BRAiN as ERP backend.

### Overview

- **Odoo Version**: Only Version 19 (JSON-2 API preferred)
- **Hosting**: Self-hosted on Hetzner
- **Access Method**: Direct PostgreSQL (recommended) + External JSON-2 API as fallback
- **Architecture**: Brain 3 (Neural Core) → Odoo Connector → PostgreSQL
- **Multi-Company**: Support for 20-30 companies in holding structure

### Module Location

- **Module**: `backend/app/modules/odoo_adapter/`
- **Documentation**: `docs/specs/odoo_connector_master_plan.md`

### Key Components

1. **Connection Pool**: Thread-safe PostgreSQL connections
2. **Company Resolver**: Multi-company context handling
3. **Domain Adapters**:
   - Accounting (invoices, payments, journal entries)
   - Sales (orders, quotes, customers)
   - Manufacturing (workorders, BoM)
   - Inventory (stock, transfers)
   - Purchase (orders, vendors)

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/odoo/companies` | List all companies |
| `POST /api/odoo/invoices` | Create invoice |
| `GET /api/odoo/invoices` | List invoices |
| `POST /api/odoo/orders` | Create sales order |
| `POST /api/odoo/production` | Create manufacturing order |

### Odoo Skills

All Odoo operations are exposed as BRAiN skills:
- `odoo.invoice.create`
- `odoo.invoice.send`
- `odoo.order.confirm`
- `odoo.workorder.start`
- etc.

### Direct SQL vs API

- **Direct SQL (recommended)**: Best performance, full control
- **JSON-2 API**: For compatibility and standard operations
- **XML-RPC**: DEPRECATED - avoid

### For Agents

When working on Odoo Connector:
- Always use the OdooAdapter service, not direct DB queries
- Respect company context (company_id) in all operations
- Use transactions for multi-step operations
- Log all Odoo executions for learning loop
