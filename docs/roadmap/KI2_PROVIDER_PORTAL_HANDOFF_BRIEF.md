# KI2 Handoff Brief - Provider Portal Backend Track

Status: Dispatched and returned to KI 1 with verification evidence.
Owner: KI 1 (orchestrator) issues this brief to KI 2.

## 1. When to give this to KI 2

Give this brief only after KI 1 confirms:
- Phase 1 boundary freeze complete
- ControlDeck contract audit complete
- Provider convergence rules locked

Current status: these gates are now complete.

## 2. KI 2 mission

Implement Provider Portal backend V1 as control-plane extension, not runtime
replacement.

## 3. Allowed scope (KI 2)

- `backend/app/modules/provider_portal/` (new module)
- Alembic migrations for provider portal tables
- Tests for provider portal module
- Minimal integration touchpoints required for mapping to `provider_bindings`

## 4. Forbidden scope (KI 2)

- No AXE UI architecture changes
- No ControlDeck navigation/auth refactor
- No replacement of `provider_bindings` runtime behavior
- No direct changes to execution ownership around `SkillRun`
- No secrets in frontend or plaintext API responses

## 5. Canonical rules KI 2 must preserve

- `SkillRun` remains canonical execution record.
- `provider_bindings` remains execution mapping layer.
- Provider Portal is control-plane metadata/governance only.
- No direct provider calls from frontend.
- No secret material in `provider_bindings.config`.

## 6. KI 2 task backlog (ordered)

### Task group A - Module skeleton

1. Create `backend/app/modules/provider_portal/`:
   - `models.py`
   - `schemas.py`
   - `service.py`
   - `router.py`
   - optional `credential_service.py`
2. Add minimal router wiring with RBAC-protected endpoints.

### Task group B - Persistence

3. Add migration(s) for:
   - `provider_accounts`
   - `provider_credentials`
   - `provider_models`
   - optional `provider_health_checks`
4. Ensure upgrade/downgrade safety.

### Task group C - Secrets lifecycle

5. Implement set/update/deactivate credential flow.
6. Return only masked hints (e.g., last4), never clear secret.
7. Add audit/control-plane events for sensitive mutations.

### Task group D - Models + health

8. Implement model CRUD per provider.
9. Implement provider test endpoint with timeout/error classification.
10. Implement health status projection (`healthy/degraded/failed/unknown`).

### Task group E - Convergence helper

11. Implement deterministic mapping helper to `provider_bindings` semantics.
12. Do not break existing `provider_bindings` resolution behavior.

### Task group F - Verification

13. Add tests for:
    - schema validation
    - secret masking/no plaintext response
    - RBAC checks
    - health/test endpoint behavior
14. Run targeted backend tests and report results.

## 7. Required deliverables from KI 2

1. Short architecture note (what was reused, what was not invented)
2. File list changed/added
3. Migration notes
4. Test command list + results
5. Risks/open issues

## 8. Handoff back to KI 1

KI 2 stops after backend implementation slice and returns:
- API contracts
- migration status
- test evidence

KI 1 then integrates ControlDeck UI and cross-surface convergence.

## 9. KI 2 return package received (2026-03-24)

- Backend provider portal slice delivered under `backend/app/modules/provider_portal/`.
- Router wired into runtime via `backend/main.py` and migration `046_add_provider_portal_tables.py`.
- Reported targeted tests:
  - `PYTHONPATH=. pytest tests/test_provider_portal_router.py -q` -> 8 passed
  - `PYTHONPATH=. pytest tests/test_provider_binding_service.py -q` -> 1 passed
- RC staging gate evidence reported as full pass:
  - `./scripts/run_rc_staging_gate.sh`
  - auth + lifecycle: 48 passed
  - immune decision + event contract: 6 passed
  - recovery action flow: 40 passed
  - DNA integrity + audit: 10 passed
  - discovery + evolution + economy: 22 passed
  - health system: 23 passed
  - diagnostics: 44 passed
  - immune system: 32 passed
- Guardrails passed:
  - no legacy EventBus imports in `backend/app`
  - no guarded `datetime.utcnow()` usage in auth/planning checks
  - no deprecated-module feature creep violations
- Critic artifact path: `reports/critic/critic_gate_report.json`.
