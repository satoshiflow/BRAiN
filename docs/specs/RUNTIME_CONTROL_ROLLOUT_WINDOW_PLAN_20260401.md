# Runtime Control Rollout Window Plan (Step 3)

Date: 2026-04-01
Owner: BRAiN Runtime / Platform
Scope: Runtime Control Plane + Context Readiness deployment to staging/prod candidate

## Objective

Safely roll out Runtime Control governance and AXE context/session readiness with deterministic checks, controlled promotion, and clear rollback boundaries.

## Rollout Window

- Proposed window: 90 minutes
- Recommended start: low-traffic period
- Freeze: no unrelated config/policy mutations during window

## Roles

- Release Lead: owns go/no-go and timeline
- Operator: executes API/UI validation steps
- Observer: monitors health/queues/errors and records evidence

## Pre-Window Gate (T-30 to T-5)

1. Confirm branch state and deployed artifact version.
2. Confirm runtime preflight checks are green.
3. Confirm latest RC gate baseline is green.
4. Confirm ControlDeck login and runtime-control page loads.
5. Confirm no pending emergency overrides unless intentional.

## Minute-by-Minute Execution

### T+00 to T+10: Deploy + Base Health

1. Deploy backend and ControlDeck build candidate.
2. Verify core endpoints:
   - `GET /api/health`
   - `GET /api/runtime-control/info`
   - `GET /api/runtime-control/timeline?limit=20`
3. Verify AXE chat page loads and auth works.

### T+10 to T+25: Resolver and Governance Validation

1. Call `POST /api/runtime-control/resolve` with representative contexts.
2. Validate `decision_id`, `effective_config`, policies and overrides.

### T+25 to T+45: Registry Promotion Flow

1. Create draft version.
2. Validate resolve outputs.
3. Promote draft.
4. Confirm supersede + timeline entries.

### T+45 to T+65: Override CR + Approval Drill

1. Create override request.
2. Approve request.
3. Validate active overrides.
4. Re-run resolve and confirm effect.

### T+65 to T+80: AXE Runtime Flow Smoke

1. AXE chat returns context telemetry.
2. Trigger one worker path and verify lane enforcement.
3. Validate ControlDeck runtime view reflects latest events.

### T+80 to T+90: Go/No-Go Close

1. Summarize evidence.
2. Declare GO or rollback.
3. Start 24h monitoring protocol.

## Rollback Rules

Rollback immediately on core auth/health failures, invalid resolver outputs, blocked valid worker flow, or missing governance timeline writes.

### Rollback Procedure

1. Create rollback draft registry with known-good patch.
2. Promote rollback draft.
3. Reject/expire problematic manual overrides.
4. Re-validate resolve and AXE smoke.
