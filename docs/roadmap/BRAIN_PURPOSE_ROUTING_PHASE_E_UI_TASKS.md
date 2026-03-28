# BRAiN Purpose/Routing - Phase E UI Tasks (AXE + ControlDeck)

Status: Rebased to current AXE UI state (2026-03-24).

Master consolidation reference:
- `docs/roadmap/BRAIN_PROVIDER_PORTAL_AXE_CONVERGENCE_MASTER_PLAN.md`

## Why this plan was updated

AXE UI has been substantially updated and is no longer a placeholder surface.
Phase E must therefore extend existing AXE surfaces rather than creating a
parallel AXE governance app.

## Grounded inputs used for this plan

- AXE auth/runtime hardening decision:
  - `docs/roadmap/BETTERAUTH_AXE_AUDIT_20260324.md`
- Existing AXE surfaces:
  - `frontend/axe_ui/app/chat/page.tsx`
  - `frontend/axe_ui/app/dashboard/page.tsx`
  - `frontend/axe_ui/app/settings/page.tsx`
  - `frontend/axe_ui/components/Navigation.tsx`
  - `frontend/axe_ui/components/auth/LoginGateway.tsx`
  - `frontend/axe_ui/lib/api.ts`
  - `frontend/axe_ui/lib/contracts.ts`
- Existing ControlDeck governance entry points:
  - `frontend/control_deck/app/governance/page.tsx`
  - `frontend/control_deck/lib/api.ts`

## Core principles (must hold)

- Keep `brain_first` as the default posture in UI language and interaction.
- AXE is primarily explainability, observation, and optional intervention.
- ControlDeck is primarily governed configuration and transitions.
- Do not mix BetterAuth migration into this phase.
- Keep immutable decision artifacts read-only.

## Workstream E-A - AXE read/explainability surfaces

### E-A1 Shared AXE contracts and API client additions

- [ ] Add AXE contract types for:
  - purpose evaluation
  - routing decision
  - routing memory projection
  - routing replay comparison
- [ ] Add AXE API client methods for read paths:
  - `GET /api/domain-agents/purpose-evaluations`
  - `GET /api/domain-agents/purpose-evaluations/{evaluation_id}`
  - `GET /api/domain-agents/routing-decisions`
  - `GET /api/domain-agents/routing-decisions/{routing_decision_id}`
  - `GET /api/domain-agents/routing-memory`
  - `GET /api/domain-agents/routing-memory/replay/{task_profile_id}`

Primary files:
- `frontend/axe_ui/lib/contracts.ts`
- `frontend/axe_ui/lib/api.ts`

### E-A2 AXE decision trace in chat/dashboard

- [ ] Add read-only purpose/routing trace card(s) in AXE chat or adjacent panel.
- [ ] Add dashboard tiles for recent purpose/routing outcomes and control mode
      distribution (`brain_first`, `human_optional`, `human_required`).
- [ ] Show governance snapshot highlights (`requires_human_review`,
      `control_mode`) without edit affordances.

Primary files:
- `frontend/axe_ui/app/chat/page.tsx`
- `frontend/axe_ui/app/dashboard/page.tsx`

Acceptance:
- operator can follow `context -> purpose -> routing` without backend logs.

### E-A3 AXE navigation and settings integration

- [ ] Add navigation entry for decision trace if needed.
- [ ] Keep AXE settings focused on runtime/admin operations already present.
- [ ] Add deep-links from AXE to ControlDeck governance for editable actions.

Primary files:
- `frontend/axe_ui/components/Navigation.tsx`
- `frontend/axe_ui/app/settings/page.tsx`

## Workstream E-B - ControlDeck governance surfaces

### E-B1 Governance read views

- [ ] Replace governance placeholder with routing governance overview.
- [ ] Add read-only views for:
  - routing memory projections
  - replay comparison
  - adaptation proposal queue

Primary files:
- `frontend/control_deck/app/governance/page.tsx`
- `frontend/control_deck/lib/api.ts`

### E-B2 Governed actions for routing adaptation

- [ ] Add proposal creation form:
  - `POST /api/domain-agents/routing-adaptations/proposals`
- [ ] Add proposal transition controls:
  - `POST /api/domain-agents/routing-adaptations/proposals/{proposal_id}/transition`
- [ ] Add proposal list/detail views:
  - `GET /api/domain-agents/routing-adaptations/proposals`
  - `GET /api/domain-agents/routing-adaptations/proposals/{proposal_id}`
- [ ] Show explicit block reasons (`sandbox_mode_required`,
      `sandbox_validation_required`, `adaptive_frozen`, etc.).

Primary files:
- `frontend/control_deck/app/governance/page.tsx`
- `frontend/control_deck/lib/api.ts`

### E-B3 Simulation-before-proposal workflow

- [ ] Add simulation panel in governance flow:
  - `POST /api/domain-agents/routing-adaptations/simulate`
- [ ] Require simulation result acknowledgement before proposal submit.

Primary files:
- `frontend/control_deck/app/governance/page.tsx`
- `frontend/control_deck/lib/api.ts`

## Workstream E-C - Cross-surface consistency

- [ ] Align labels between AXE and ControlDeck:
  - read-only vs governed-editable vs sandbox-only
- [ ] Ensure no UI path implies humans are always required by default.
- [ ] Ensure transition actions remain role-gated to admin/system-admin roles.

## Suggested execution order

1. E-A1 (shared AXE API/contracts)
2. E-B1 (ControlDeck governance read views)
3. E-A2 (AXE trace surfaces)
4. E-B3 (simulation UX)
5. E-B2 (proposal/transition controls)
6. E-A3 + E-C polish

## Validation checklist

- [ ] `frontend/axe_ui`: `npm run lint`
- [ ] `frontend/axe_ui`: `npm run typecheck`
- [ ] `frontend/axe_ui`: `npm run build`
- [ ] `frontend/control_deck`: `npm run lint`
- [ ] `frontend/control_deck`: `npm run build`
- [ ] manual smoke: AXE read paths render with real backend responses
- [ ] manual smoke: ControlDeck governance actions enforce role and sandbox
      semantics
