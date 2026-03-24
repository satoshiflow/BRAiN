# KI1 CP6 Final Handoff Packet - 2026-03-24

Status: Drafted for final merge readiness review.

## 1. Scope closed in this packet

- KI2 Track A provider portal backend delivery and follow-up hardening.
- KI1 Track B ControlDeck provider governance integration loop.
- KI1 Track C AXE read-only governance visibility first pass.

## 2. Canonical boundaries preserved

- `SkillRun` remains canonical execution record.
- `provider_bindings` remains execution mapping substrate.
- Provider Portal remains control-plane and governance surface.
- AXE remains operator/read-only explainability surface for governance context.
- ControlDeck remains the editable provider/governance admin surface.

## 3. Commits included for provider portal track

- `7978169` - provider portal control-plane backend slice.
- `d33b28b` - provider portal edge-case test hardening.

## 4. Verification evidence snapshot

Backend:
- `cd backend && PYTHONPATH=. pytest tests/test_provider_portal_router.py -q` -> 9 passed
- `cd backend && PYTHONPATH=. pytest tests/test_provider_portal_service.py -q` -> 11 passed
- `cd backend && PYTHONPATH=. pytest tests/test_provider_binding_service.py -q` -> 1 passed
- `cd backend && PYTHONPATH=. pytest tests/test_domain_agents_router.py tests/test_domain_agents_service.py tests/test_skill_engine.py -q` -> 44 passed

Frontend:
- `cd frontend/control_deck && npm run build` -> passed
- `cd frontend/axe_ui && npm run typecheck` -> passed

Prior gate evidence:
- `./scripts/run_rc_staging_gate.sh` previously reported full pass with critic artifact at
  `reports/critic/critic_gate_report.json`.

## 5. Changed surfaces (high-value)

Backend provider portal:
- `backend/app/modules/provider_portal/models.py`
- `backend/app/modules/provider_portal/schemas.py`
- `backend/app/modules/provider_portal/credential_service.py`
- `backend/app/modules/provider_portal/service.py`
- `backend/app/modules/provider_portal/router.py`
- `backend/alembic/versions/046_add_provider_portal_tables.py`
- `backend/tests/test_provider_portal_router.py`
- `backend/tests/test_provider_portal_service.py`
- `backend/main.py`

ControlDeck integration:
- `frontend/control_deck/app/settings/llm-providers/page.tsx`
- `frontend/control_deck/lib/providerPortalApi.ts`
- `frontend/control_deck/app/settings/page.tsx`
- `frontend/control_deck/components/layout/sidebar.tsx`

AXE read-only convergence:
- `frontend/axe_ui/app/dashboard/page.tsx`
- `frontend/axe_ui/app/chat/page.tsx`
- `frontend/axe_ui/app/settings/page.tsx`
- `frontend/axe_ui/lib/api.ts`
- `frontend/axe_ui/lib/contracts.ts`

## 6. Open risks (explicit)

- Probe path defaults to OpenAI-compatible `/chat/completions`; non-compatible providers need adapter-aware probe expansion in a follow-up slice.
- `HealthStatus.UNKNOWN` is supported as a valid control-plane state but currently not emitted by `_classify_status` directly; semantics should remain explicit.
- `frontend/control_deck` direct `tsc --noEmit` depends on generated `.next/types` and is currently environment-sensitive; `next build` remains the practical confidence gate for this lane.

## 7. Recommended immediate next action

- Finalize CP6 by producing a merge PR summary from this packet and explicitly separating KI2 backend commits from KI1 UI/docs commits in review narrative.
