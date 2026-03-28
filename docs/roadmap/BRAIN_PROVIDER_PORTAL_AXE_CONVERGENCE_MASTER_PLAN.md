# BRAiN Provider Portal + AXE Convergence Master Plan

Status: Execution-ready consolidated implementation plan.
Audience: GPT Codex implementation streams (parallel, merge-safe).

Execution orchestration reference:
- `docs/roadmap/KI1_KI2_3PHASE_EXECUTION_MASTERPLAN.md`

## 1. Input consolidation

This master plan merges:
- Provider Portal V1 directive (control-plane implementation prompt)
- AXE UI deep IST analysis (operator-first surface, current strengths and gaps)
- Existing BRAiN constraints already codified in:
  - `DESIGN.md`
  - `AGENTS.md`
  - `docs/roadmap/BRAIN_PURPOSE_ROUTING_IMPLEMENTATION_PLAN.md`
  - `docs/roadmap/BRAIN_PURPOSE_ROUTING_PHASE_E_UI_TASKS.md`
  - `docs/roadmap/BRAIN_PROVIDER_PORTAL_V1_MASTER_PLAN.md`

## 2. Canonical decisions (fixed)

- BRAiN stays `brain_first` with governance gates.
- `SkillRun` remains canonical execution record.
- `provider_bindings` + capability runtime remain execution-time provider mapping.
- Provider Portal is a control-plane overlay, not a second runtime.
- AXE remains operator/frontdoor/explainability surface.
- ControlDeck remains governance/admin/provider-management surface.
- No provider/API key secrets in frontend.
- No direct UI calls to OpenAI/Anthropic/Groq/Ollama endpoints.

## 3. Problem framing to solve

Current split realities to converge (without breaking runtime):
1. `provider_bindings` execution mapping
2. AXE runtime/provider controls
3. `llm_router` provider config logic

Target:
- governed provider truth in control-plane tables
- deterministic mapping into existing `provider_bindings`
- no additional execution path

## 4. Target architecture (V1)

### Control-plane additions

- `provider_accounts`
- `provider_credentials`
- `provider_models`
- optional `provider_health_checks`
- optional `provider_usage_events`

### Runtime preservation

- `provider_bindings` untouched as runtime selection substrate
- `SkillRun` untouched as execution truth
- capability runtime untouched as gateway path

### Surface split

- AXE: read/explain/operate (chat + decision/runtime transparency)
- ControlDeck: create/update/rotate/transition governance actions

## 5. Phased execution plan

## Phase P0 - Contract lock and boundaries

Goal: prevent parallel architecture drift before coding slices.

Tasks:
- freeze field contracts and ownership boundaries
- lock source precedence and non-goals
- define mapping invariant: ProviderAccount -> ProviderModel -> ProviderBinding

Done when:
- checklist signed in docs
- no unresolved ownership ambiguity between AXE/ControlDeck/backend modules

## Phase P1 - Provider Portal backend skeleton

Goal: new module and migrations, no runtime disturbance.

Tasks:
- create `backend/app/modules/provider_portal/`
- add models/schemas/service/router skeleton
- add Alembic migrations for provider control-plane tables
- add RBAC gate scaffolding and audit event hooks

Done when:
- migrations apply/rollback cleanly
- list/create/update provider endpoints work with auth

## Phase P2 - Secret lifecycle hardening

Goal: secure secret handling with masking and rotation-ready semantics.

Tasks:
- implement set/update/deactivate provider secret endpoint
- enforce masked response only (`key_hint_last4` style)
- prevent clear secret logs and response leakage
- audit all credential mutations

Done when:
- security tests confirm no plaintext secret leaves backend APIs
- logs remain redacted

## Phase P3 - Model registry + provider health testing

Goal: governed provider model catalog + deterministic connectivity checks.

Tasks:
- model CRUD per provider
- provider test endpoint with timeout + error classification
- health projection endpoints (`healthy/degraded/failed/unknown`)
- minimal adapters:
  - openai-compatible adapter
  - ollama/local adapter

Done when:
- at least one cloud-compatible and one local provider test path pass

## Phase P4 - ControlDeck Provider Portal UI

Goal: production-grade admin surface in `frontend/control_deck`.

Tasks:
- add route (recommended): `/settings/llm-providers`
- provider overview + create/edit
- secret set/rotate/deactivate (masked-only output)
- model management
- health/test actions and result rendering

Done when:
- desktop-strong + mobile-usable
- no secret exposure in rendered state

## Phase P5 - Binding convergence integration

Goal: avoid fourth provider truth by explicit mapping into runtime bindings.

Tasks:
- implement reconciliation/sync path from portal entities to bindings
- validate no runtime break for existing bindings
- produce deterministic binding mapping contract docs

Done when:
- mapping path validated end-to-end in tests and docs

## Phase P6 - AXE convergence (read/explainability only)

Goal: AXE reflects provider/runtime/governance state without becoming admin secret surface.

Tasks:
- extend AXE contracts/api for read-only provider/routing visibility
- add decision/runtime trace surfaces in AXE dashboard/chat
- maintain operator-focused settings; deep-link governance edits to ControlDeck

Done when:
- operator can inspect purpose/routing/provider health context without backend logs

## Phase P7 - Usage/audit readiness and rollout

Goal: rollout-safe V1 with evidence and forward hooks.

Tasks:
- optional usage events structure
- final audit/event consistency checks
- run local gates and RC gate
- capture local CI evidence and rollback steps

Done when:
- rollout package complete (docs, tests, evidence, rollback)

## 6. Parallel workstreams (subagent-friendly)

After P0 lock, run these in parallel:

- WS1 `provider_portal` schemas/models/migrations (P1)
- WS2 secret lifecycle and security tests (P2)
- WS3 model registry + health adapters (P3)
- WS4 ControlDeck provider portal UI (P4)
- WS5 binding convergence service + docs (P5)
- WS6 AXE read/explainability integration (P6)
- WS7 verification/evidence lane (P7, continuous)

## 7. Merge checkpoints

- CP1: Contract/boundary lock (P0)
- CP2: Backend skeleton stable (P1)
- CP3: Secret safety lock (P2)
- CP4: Model/health lock (P3)
- CP5: ControlDeck portal usable (P4)
- CP6: Binding convergence validated (P5)
- CP7: AXE read convergence done (P6)
- CP8: Gates + evidence + rollback complete (P7)

## 8. Security and compliance checklist

- no frontend secret persistence
- no clear secret API responses
- no direct provider calls from UI
- strict RBAC on provider mutation endpoints
- audit event on all sensitive mutations
- sanitized errors for test/health endpoints
- masked secret hints only

## 9. Explicit non-goals in this track

- no full BetterAuth migration
- no replacement of provider runtime path
- no direct secret management in AXE
- no full cost/billing engine
- no autonomous routing optimization rollout

## 10. Fast start instructions for GPT Codex execution

1. Execute P0/P1 first (contract + skeleton + migration safety).
2. Branch into parallel WS2/WS3/WS4.
3. Hold WS5 until WS2+WS3 contracts stabilize.
4. Execute WS6 in parallel with late WS4 using stable read APIs.
5. Keep WS7 continuously validating; finish with RC gate and evidence.

## 11. Expected V1 output bundle

- backend module: `provider_portal`
- migration set for provider portal entities
- control-deck provider portal route and workflows
- AXE read/explainability convergence updates
- convergence docs for `provider_bindings` mapping
- test report + local CI evidence + rollback runbook
