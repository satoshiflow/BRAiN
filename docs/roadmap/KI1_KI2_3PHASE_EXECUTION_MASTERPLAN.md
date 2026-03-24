# KI1/KI2 3-Phase Execution Masterplan

Status: Active execution plan (Phase 2 checkpoints closed through CP5; moving to Phase 3 packaging).
Roles:
- KI 1 = Orchestrator, Senior Dev, Architecture/Admin owner
- KI 2 = Junior Dev, implementation lane under frozen contracts

## 0. Open work baseline (today/yesterday carry-over)

### Already implemented

- Purpose/Routing backend core (domain agents, routing memory/adaptation,
  SkillRun upstream snapshots)
- Backend validation gates executed and evidence written
- Canonical design and specs created

### Still open

- Purpose/Routing Phase E UI (AXE + ControlDeck surfaces, partial)
- Phase 3 final packaging (CP6 evidence bundle and merge handback)

## Phase 1 - Freeze and contract audit (KI 1 only)

Goal: lock architecture boundaries and remove ambiguity before parallel coding.

### Step 1.1 - Boundary freeze

Tasks (KI 1):
- confirm role split:
  - AXE = operator/execution surface
  - ControlDeck = governance/admin surface
- lock canonical truths:
  - SkillRun runtime truth
  - provider_bindings execution mapping truth
  - provider_portal as control-plane only
- lock non-goals:
  - no frontend secrets
  - no direct provider calls from UI
  - no second runtime

Outputs:
- signed boundary/contract notes in roadmap docs

Done criteria:
- no unresolved ownership conflict across AXE/ControlDeck/provider runtime

### Step 1.2 - ControlDeck contract audit

Tasks (KI 1):
- classify governance-relevant pages as:
  - real
  - mock
  - drift
  - missing backend contract
- produce page -> API matrix for:
  - settings
  - governance
  - policy
  - provider-relevant areas

Outputs:
- prioritized audit matrix for implementation order
- Deliverable file:
  - `docs/roadmap/KI1_SLICE1_CONTROLDECK_CONTRACT_AUDIT.md`

Done criteria:
- top-priority surfaces selected for first implementation pass

### Step 1.3 - KI 2 handoff gate definition

Tasks (KI 1):
- define exact allowed scope for KI 2
- define forbidden touch zones for KI 2
- define merge checkpoints and review obligations

Outputs:
- KI 2 execution brief
- Deliverable file:
  - `docs/roadmap/KI2_PROVIDER_PORTAL_HANDOFF_BRIEF.md`

Done criteria:
- KI 2 can start without architecture decisions

### User action at end of Phase 1

- Action U1: Approve KI 2 start with frozen scope.
- What to send to KI 2:
  - only the KI 2 brief from Step 1.3
  - not the full repo-wide strategy text

## Phase 2 - Parallel implementation (KI 1 + KI 2)

Goal: build Provider Portal backend and ControlDeck surfaces in parallel,
without runtime disruption.

## Track A (KI 2) - Provider Portal backend

### Step 2A.1 - Module skeleton + migrations

Tasks:
- create `backend/app/modules/provider_portal/`
- add models/schemas/service/router skeleton
- add Alembic migrations for:
  - provider_accounts
  - provider_credentials
  - provider_models
  - optional health table

Done criteria:
- migrations up/down work
- baseline CRUD endpoints compile and are role-gated

### Step 2A.2 - Secrets lifecycle

Tasks:
- implement set/update/deactivate credential flows
- enforce masked responses only
- sanitize errors/logs
- emit audit/control-plane events for secret mutations

Done criteria:
- tests confirm no plaintext secret returned

### Step 2A.3 - Models + health/test

Tasks:
- implement model registry CRUD
- implement provider test endpoint + timeout/error mapping
- implement health projection endpoint

Done criteria:
- one cloud-compatible + one local provider test path works

### Step 2A.4 - Binding convergence prep

Tasks:
- implement deterministic mapping from portal entities to provider_bindings
- ensure no secret in provider_bindings config
- keep existing runtime behavior intact

Done criteria:
- mapping path documented and verified in tests

## Track B (KI 1) - ControlDeck governance and provider UI

### Step 2B.1 - Navigation + governance IA cleanup

Tasks:
- fix nav mismatches for governance/settings/provider flows
- de-prioritize unfinished mock-heavy pages from primary path

Done criteria:
- clear route entry to provider/governance workflows

### Step 2B.2 - Auth/API integration hardening

Tasks:
- standardize authenticated fetch usage for governance pages
- remove ad hoc contract drift where possible

Done criteria:
- governance/provider pages use stable API client paths

### Step 2B.3 - Provider Portal UI in ControlDeck

Tasks:
- implement `/settings/llm-providers` surface:
  - provider list/create/edit
  - secret set/rotate/deactivate (masked)
  - model list/create/edit
  - provider test/health status

Done criteria:
- complete provider portal flow works against backend APIs

## Track C (KI 1) - AXE role-preserving convergence

### Step 2C.1 - AXE read-only governance visibility

Tasks:
- add read/explainability views for provider/routing context
- deep-link edits to ControlDeck

Done criteria:
- AXE informs operator; ControlDeck remains admin truth

### User action during Phase 2

- Action U2: When KI 1 requests review at CP2/CP3, do quick checkpoint approval.
- Action U3: If secrets for local test are needed, provide them out-of-band and
  rotate afterward (never commit).

## Phase 3 - Integration hardening and rollout readiness (KI 1 lead)

Goal: consolidate both tracks, run gates, prepare merge/rollout package.

### Step 3.1 - Cross-track integration

Tasks:
- integrate KI 2 backend outputs with KI 1 ControlDeck UI
- verify AXE and ControlDeck boundaries remain intact
- verify provider_bindings runtime remains canonical

Done criteria:
- no second runtime or provider truth introduced

### Step 3.2 - Verification and quality gates

Tasks:
- targeted backend tests (provider_portal + bindings + auth/rbac checks)
- targeted frontend checks:
  - control_deck lint/build
  - axe_ui lint/typecheck/build
- run RC staging gate
- collect local CI evidence

Done criteria:
- tests and gates pass with evidence artifacts

### Step 3.3 - Delivery package

Tasks:
- final architecture summary
- changed files manifest
- migration and setup notes
- rollback runbook
- open risks and V2 convergence recommendations

Done criteria:
- merge-ready delivery packet complete

### User action at end of Phase 3

- Action U4: Final acceptance sign-off for merge/promotion decision.

## Merge checkpoints

- CP1: Phase 1 complete, KI 2 authorized (done)
- CP2: Provider portal skeleton + migrations complete (done)
- CP3: Secret safety verified (done)
- CP4: ControlDeck provider UI first complete loop (done)
- CP5: Binding convergence validated (done)
- CP6: Full gates/evidence and final handoff complete

## Execution snapshot (2026-03-24)

- KI2 reported backend Provider Portal V1 slice complete with migration `046_add_provider_portal_tables.py` and router wiring.
- KI2 slice committed as `7978169` (provider portal control-plane backend).
- KI2 follow-up hardening committed as `d33b28b` (router RBAC negative path + provider portal service edge-case tests).
- KI2 reported targeted tests passing:
  - `tests/test_provider_portal_router.py` (9 passed)
  - `tests/test_provider_portal_service.py` (11 passed)
  - `tests/test_provider_binding_service.py` (1 passed)
- RC staging gate reported full pass and critic artifact generated at `reports/critic/critic_gate_report.json`.
- KI1 completed ControlDeck route and API hardening work for `/settings/llm-providers` and related settings/mission pages.
- KI1 completed AXE read-only governance first pass (dashboard/chat/settings) with ControlDeck deep-link posture.
- KI1 integration smoke checks completed:
  - `frontend/control_deck`: `npm run build` passed
  - `frontend/axe_ui`: `npm run typecheck` passed
  - `backend`: `pytest tests/test_provider_portal_router.py -q` passed
  - `backend`: `pytest tests/test_provider_portal_service.py -q` passed
  - `backend`: `pytest tests/test_provider_binding_service.py -q` passed

## KI 2 operating constraints (must follow)

- KI 2 may change only agreed backend surfaces for provider portal and tests.
- KI 2 must not refactor AXE or ControlDeck architecture.
- KI 2 must not alter canonical runtime ownership (SkillRun/provider_bindings).
- KI 2 must keep secret values server-side and masked in responses.
