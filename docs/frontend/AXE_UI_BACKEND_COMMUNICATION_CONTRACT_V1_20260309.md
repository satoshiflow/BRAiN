# AXE UI <-> Backend Communication Contract v1 (2026-03-09)

## Purpose

Define one stable, implementation-ready communication path between AXE UI and BRAiN backend during EventStream convergence.

## Decisions

1. AXE UI talks to backend through HTTP API contracts as the primary channel.
2. EventStream remains the canonical backend event backbone and is not exposed as a direct frontend dependency.
3. AXE chat ingress follows AXE trust-tier governance (LOCAL/DMZ allowed, EXTERNAL blocked).
4. Frontend API access is centralized to remove per-page base URL drift.

## Why this fits EventStream migration

- EventStream is authoritative for runtime events and downstream workflows.
- Durable state remains in PostgreSQL and endpoint contracts.
- Frontend receives stable read/write contracts while backend internals can evolve from legacy event bus to EventStream.

## Runtime communication model

### Primary (implemented)

- `POST /api/axe/chat`
  - request: `{ model, messages[], temperature? }`
  - response: `{ text, raw }`
- `GET /api/axe/health`
  - request: none
  - response: `{ status, axellm, error? }`
- `GET /api/health` (global backend health)
  - request: none
  - response: `{ status, version? }`

### Optional real-time (already available in repo)

- `GET ws://.../api/axe/ws/{session_id}` for widget real-time chat/diff workflow.
- WebSocket remains additive and does not replace HTTP contract paths.

## Security model (implemented for AXE Fusion endpoints)

- `POST /api/axe/chat` and `GET /api/axe/health` now use trust-tier validation:
  - allow: `DMZ`
  - allow `LOCAL` only when `AXE_FUSION_ALLOW_LOCAL_REQUESTS=true`
  - deny: `EXTERNAL` (403)
- If `BRAIN_DMZ_GATEWAY_SECRET` is missing, requests fail closed with 503 by default.
- Optional local dev fallback can be enabled explicitly with:
  - `AXE_FUSION_ALLOW_LOCAL_REQUESTS=true`
  - `AXE_FUSION_ALLOW_LOCAL_FALLBACK=true`

## Frontend contract hardening (implemented)

- Added shared AXE API contracts in `frontend/axe_ui/lib/contracts.ts`.
- Refactored API calls into one client in `frontend/axe_ui/lib/api.ts`.
- Updated pages to use centralized API helpers:
  - `frontend/axe_ui/app/chat/page.tsx`
  - `frontend/axe_ui/app/page.tsx`
  - `frontend/axe_ui/app/dashboard/page.tsx`
  - `frontend/axe_ui/app/settings/page.tsx`
- Removed unused per-page API base drift in `frontend/axe_ui/app/agents/page.tsx`.

## Backend governance alignment (implemented)

- Updated `backend/app/modules/axe_fusion/router.py`:
  - removed JWT-only global dependency from AXE Fusion router
  - added trust-tier dependency (`validate_axe_trust`) for `/chat` and `/health`
  - retained fail-closed behavior for untrusted external traffic

## Implementation status

Completed in this slice:

1. AXE Fusion trust-tier contract tests are implemented in:
   - `backend/tests/test_axe_fusion_routes.py`
   - `backend/tests/test_axe_fusion_trust.py`
2. Frontend API access is centralized through:
   - `frontend/axe_ui/lib/api.ts`
   - `frontend/axe_ui/lib/contracts.ts`
3. Chat page now consumes centralized AXE API contracts and request helpers.

## Follow-up items

1. Add frontend integration tests for chat error-state mapping and retry behavior.
2. Decide whether production AXE web app ingress is DMZ-only for all user-facing traffic.

## Verification commands

- Frontend type check:
  - `cd frontend/axe_ui && npm run typecheck`
- Frontend lint:
  - `cd frontend/axe_ui && npm run lint`
- Backend targeted tests:
  - `cd backend && PYTHONPATH=. pytest tests/test_axe_fusion_* -q`

## Notes

- This contract intentionally keeps EventStream out of frontend coupling while preserving EventStream-first backend evolution.
- Frontend remains compatible with future mission/status projection APIs built on EventStream consumers.
