# KI1 Phase 2C.1 - AXE Read-Only Governance Visibility Brief

Status: Ready for implementation handoff.
Intent: Extend AXE as an operator/explainability surface without turning AXE
into an admin/provider-secret portal.

## 1. Scope

Allowed:
- read-only visibility for decision/runtime/governance signals
- explainability cards in operator flows
- deep links from AXE to ControlDeck governance actions

Forbidden:
- provider secret create/edit/rotate in AXE
- provider governance ownership in AXE
- direct provider endpoint calls from AXE frontend

## 2. Candidate AXE insertion points

- `frontend/axe_ui/app/dashboard/page.tsx`
  - add recent decision/routing/provider health telemetry cards
- `frontend/axe_ui/app/chat/page.tsx`
  - add lightweight decision trace panel for active session context
- `frontend/axe_ui/app/settings/page.tsx`
  - keep runtime/operator controls; add links to ControlDeck provider governance

## 3. Read APIs to consume

Existing purpose/routing APIs:
- `GET /api/domain-agents/purpose-evaluations`
- `GET /api/domain-agents/routing-decisions`
- `GET /api/domain-agents/routing-memory`
- `GET /api/domain-agents/routing-memory/replay/{task_profile_id}`

Future provider portal read APIs:
- `GET /api/llm/providers`
- `GET /api/llm/models`
- provider health read endpoint (from provider portal track)

## 4. UX expectations

- default posture remains `brain_first`
- display control mode context:
  - `brain_first`
  - `human_optional`
  - `human_required`
- keep cards concise and operational (no large governance forms)
- include clear "Manage in ControlDeck" links

## 5. Acceptance criteria

- operator can inspect why/how decisions were routed without backend logs
- AXE does not expose secret values or provider admin write controls
- ControlDeck remains the edit surface for governance/provider mutations
