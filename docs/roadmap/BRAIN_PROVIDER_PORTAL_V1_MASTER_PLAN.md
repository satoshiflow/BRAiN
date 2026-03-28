# BRAiN Provider Portal V1 - Master Implementation Plan

Status: Planning complete, implementation-ready.

Consolidated execution alignment:
- `docs/roadmap/BRAIN_PROVIDER_PORTAL_AXE_CONVERGENCE_MASTER_PLAN.md`
- `docs/roadmap/KI1_KI2_3PHASE_EXECUTION_MASTERPLAN.md`
Scope owner: Control-plane evolution track.

## 1. Intent

Implement a production-grade provider and model governance portal for BRAiN
without introducing a parallel runtime.

This plan is explicitly convergent:
- no fourth provider truth
- no frontend secrets
- no direct UI-to-provider calls
- no runtime bypass around `provider_bindings`, capability runtime, and `SkillRun`

## 2. Architecture constraints (hard)

- `provider_bindings` remains execution-time mapping truth.
- Capability runtime and `SkillRun` remain execution path truth.
- New portal module is control-plane metadata/governance only.
- AXE remains operator/frontdoor surface, not secret truth.
- ControlDeck is admin/governance surface for provider portal operations.
- All provider/model execution traffic remains server-side via BRAiN.

## 3. Existing structures to reuse

### Backend

- `backend/app/modules/provider_bindings/*`
- `backend/app/core/capabilities/service.py`
- `backend/app/modules/skill_engine/*`
- `backend/app/core/control_plane_events.py`
- `backend/app/core/audit_bridge.py`
- `backend/app/modules/audit_logging/*`
- `backend/app/modules/axe_fusion/*`

### Frontend

- `frontend/control_deck` as primary portal surface
- existing control-deck API helpers and page shells

### Explicitly not primary for this track

- `frontend/axe_ui` for secret/provider admin logic
- `frontend/controldeck-v2` as primary implementation target

## 4. Current-state convergence map

Current parallel-ish provider realities:
1. `provider_bindings` execution mapping
2. AXE runtime provider selection
3. `llm_router` provider configuration

V1 convergence objective:
- add a governed provider control-plane above runtime
- map ProviderAccount/Model governance into existing `provider_bindings`
- avoid any new direct execution path from UI or a new runtime broker

## 5. Target V1 capability

### 5.1 Provider Registry (control-plane)

Entity: `provider_accounts`
- id, slug, display_name, provider_type, base_url, auth_mode
- is_enabled, is_local, supports_chat, supports_embeddings,
  supports_responses
- notes, created_at, updated_at

### 5.2 Secret Registry (separate)

Entity: `provider_credentials`
- provider_id, secret_ref/encrypted_secret, key_hint_last4
- is_active, created_at, updated_at

Rules:
- never return clear secret
- masked hint only
- rotation-ready lifecycle

### 5.3 Model Registry

Entity: `provider_models`
- provider_id, model_name, display_name, capabilities
- is_enabled, priority, cost_class, latency_class, quality_class
- supports_tools, supports_json, supports_streaming

### 5.4 Health/Test

Entity: `provider_health_checks` (or projection)
- provider_id, model_id(optional), status, latency/error snapshot,
  tested_at, probe metadata

### 5.5 Usage/Audit readiness

Entity (optional V1 minimal): `provider_usage_events`
- provider/model/endpoint/timestamp/success/latency/error_type/trace_id

## 6. API plan (backend)

Portal control-plane APIs:
- `GET /api/llm/providers`
- `POST /api/llm/providers`
- `PATCH /api/llm/providers/{id}`
- `POST /api/llm/providers/{id}/secret`
- `POST /api/llm/providers/{id}/test`
- `GET /api/llm/models`
- `POST /api/llm/models`
- `PATCH /api/llm/models/{id}`

Preparation endpoint:
- `POST /api/llm/run` (stub/contract-first only in V1)

Rule:
- `POST /api/llm/run` must not create a second execution runtime.

## 7. Backend module shape

New module:
- `backend/app/modules/provider_portal/`

Planned files:
- `models.py`
- `schemas.py`
- `service.py`
- `router.py`
- `credential_service.py` (or `secrets.py`)
- `adapters/` (minimal provider test adapters)

## 8. Data model strategy

Alembic migrations:
- add new control-plane tables only
- no destructive changes to `provider_bindings` in V1

`provider_bindings` integration strategy:
- keep existing schema as runtime mapping layer
- add controlled mapping fields/metadata references if needed
- no secret material in `provider_bindings.config`

## 9. Slice-based implementation plan (small tasks)

## Slice 1 - Module skeleton + schemas + migrations

Goal:
- provider_portal module skeleton and durable schema foundation

Tasks:
- create `provider_portal` module files
- add tables: provider accounts/credentials/models (+optional health)
- add Pydantic contracts
- add router skeleton with role guards
- add control-plane event and audit hook stubs

Done:
- migrations apply cleanly
- provider list/create/update skeleton works
- schema/router smoke tests pass

## Slice 2 - Secrets lifecycle + provider CRUD

Goal:
- secure secret write/update/deactivate with masking

Tasks:
- implement credential write/update/deactivate
- implement masked read responses (hint only)
- sanitize logs/errors around credential operations
- emit audit events for credential and provider mutations

Done:
- no clear secret returned
- mutation endpoints role-gated and audited
- tests validate no secret leakage

## Slice 3 - Model registry + provider test/health

Goal:
- model governance and health checks per provider

Tasks:
- CRUD for provider models
- provider test endpoint with timeout and error normalization
- health state recording/projection (`healthy/degraded/failed/unknown`)
- adapter abstraction for test calls:
  - openai-compatible adapter
  - local ollama adapter

Done:
- test endpoint works for at least one cloud-compatible and one local provider
- health visible via API

## Slice 4 - ControlDeck Provider Portal UI

Goal:
- production-like admin portal in `frontend/control_deck`

Tasks:
- add route (recommended): `/settings/llm-providers`
- provider list/create/edit views
- secret set/rotate/deactivate flow (masked output only)
- model management views
- test/health views

Done:
- desktop-first, mobile-usable
- no secret plaintext in browser state/rendered responses
- role-sensitive actions guarded

## Slice 5 - Binding convergence integration

Goal:
- map portal governance into existing runtime mapping path

Tasks:
- define and implement mapping path:
  - ProviderAccount -> ProviderModel -> ProviderBinding
- add sync/validation helper to ensure no drift
- preserve existing runtime behavior for non-portal-managed bindings

Done:
- documented and testable mapping path to execution
- no runtime break in `provider_bindings` resolution

## Slice 6 - Usage/Audit readiness + handoff

Goal:
- V1 readiness and future hooks for policy/routing/cost

Tasks:
- add minimal usage event model/projection if feasible
- ensure control-plane events and audit consistency
- produce runbook + bootstrap + migration notes
- document V2 convergence work with `axe_fusion` and `llm_router`

Done:
- rollout docs complete
- extension points explicit for budget/policy/routing/evaluation

## 10. Parallel execution workstreams

After Slice 1 schema lock, run in parallel:

- WS-A Backend credentials and provider CRUD (Slice 2)
- WS-B Backend models/health/adapters (Slice 3)
- WS-C ControlDeck UI shell and read views (Slice 4 partial)
- WS-D Binding convergence and compatibility checks (Slice 5 prep)
- WS-E Test and verification lane (continuous)

Merge checkpoints:
- CP1 schema/migration lock
- CP2 secrets safety lock
- CP3 model/health lock
- CP4 UI read/control lock
- CP5 binding convergence lock
- CP6 verification + RC/local evidence lock

## 11. Security and governance checklist

- no API keys in frontend payloads/storage
- no API keys in git or logs
- all mutating APIs RBAC-protected
- all sensitive mutations audited
- masked secret hints only
- timeout and sanitized errors for test/health probes
- server-side provider invocation only

## 12. Testing and gates

Backend:
- module unit tests (schemas/service/router)
- migration tests
- integration tests for CRUD + secret redaction + health

Frontend:
- ControlDeck lint/build
- targeted UI tests for forms and masking behavior

Gates:
- targeted pytest suites for touched modules
- `./scripts/run_rc_staging_gate.sh` before final merge candidate
- local CI evidence entry under `docs/roadmap/local_ci/`

## 13. Risks and mitigation

Risk: fourth provider truth emerges
- Mitigation: binding convergence checkpoint before rollout

Risk: secret leakage via API/FE logs
- Mitigation: explicit redaction tests and review checklist

Risk: runtime drift between portal and provider_bindings
- Mitigation: deterministic mapping and reconciliation utility

Risk: AXE and portal responsibilities blur
- Mitigation: keep provider admin in ControlDeck; AXE remains operator surface

## 14. Out of scope (V1)

- full BetterAuth migration
- full billing/cost engine
- automated provider routing optimization
- replacement of current runtime execution path

## 15. Deliverables at V1 close

1. Architecture summary
2. Changed file manifest
3. Migration/setup steps
4. Test runbook
5. Risks/open points
6. V2 convergence recommendations for:
   - `provider_bindings`
   - `axe_fusion`
   - `llm_router`
   - ControlDeck Provider Portal
