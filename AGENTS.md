# AGENTS.md

Repository guidance for autonomous coding agents working in `BRAiN`.

## 1) Project layout (working mental model)

- Monorepo with a Python FastAPI backend and multiple Next.js frontends.
- Backend primary runtime entrypoint: `backend/main.py`.
- New backend modules live in: `backend/app/modules/*`.
- Legacy compatibility surface still exists in: `backend/modules/*`, `backend/api/routes/*`, `backend/app/compat/*`.
- Event backbone: `backend/mission_control_core/core/event_stream.py` (ADR-001 required by default).

## 2) Rule sources you must follow

- Copilot instructions exist at: `.github/copilot-instructions.md`.
- Cursor rules were not found (`.cursorrules` and `.cursor/rules/` absent at repo root).
- Security/architecture constraints are also documented in `CLAUDE.md` and must be honored.
- Agent operating model is documented in `docs/core/agent_operating_matrix.md`.
- Permanent agent setup guidance is documented in `docs/core/agent_cluster_setup_guide.md`.
- Mission deliberation and insight evolution architecture is documented in `docs/specs/mission_deliberation_insight_evolution.md`.

### Copilot instruction highlights (applied here)

- Prefer Docker Compose for full local stack.
- Keep route contracts stable; many APIs are consumed by UI/tests.
- Use connector/gateway abstractions instead of hardcoded provider wiring.
- When API signatures change, update backend tests and impacted frontend callers.

## 3) Build, lint, test, run commands

All commands below are from repo root unless noted.

### Backend run

- Full stack (recommended):
  - `docker compose up -d --build`
- Dev stack variant:
  - `docker compose -f docker-compose.dev.yml up --build`
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

## 6) Architecture boundaries to preserve

- New backend features should be implemented under `backend/app/modules/*`.
- Keep EventStream as the canonical event backbone.
- Treat `backend/modules/*` as legacy; migrate incrementally, do not expand.
- Keep compatibility shims concentrated in `backend/app/compat/*`.

## 7) Change workflow for agents

- Make minimal, scoped changes; avoid unrelated refactors.
- Update/add tests with behavior changes.
- For backend runtime edits, run targeted pytest and `./scripts/run_rc_staging_gate.sh`.
- If command output reveals environment blockers, document them clearly.
- Keep docs aligned when adding modules/routes/migrations.

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

## 10) Documentation cadence (execution governance)

- Keep architecture migration work documented under `docs/specs/*` and `docs/roadmap/*`.
- For skill/runtime execution work, align specs with `docs/core/brain_skill_execution_standard.md`.
- For multi-agent execution, align role usage and parallelization with `docs/core/agent_operating_matrix.md`.
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
