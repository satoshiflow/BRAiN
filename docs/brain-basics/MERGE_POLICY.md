# Merge Policy

Status: Active
Effective date: 2026-03-06

## Core rule

No merge to `main` without a successful staging/integration run.

## Branch flow

1. Implement on `feature/*` or working branch.
2. Promote to `rc/*` (or equivalent PR branch) for validation.
3. Merge to `main` only after all merge gates pass.

## Mandatory merge gates

### Gate 1: Local validation

- Required regression tests pass.
- Required guard scripts pass.
- Required build checks pass.

### Gate 2: RC/Staging validation

- Smoke tests run in staging/integration environment.
- At least one end-to-end workflow for changed domain passes.
- Critical auth and role-protected paths pass.

### Gate 3: Risk and rollback

- Short risk note documented for the change.
- Rollback path is explicit and executable.

### Gate 4: Release decision

- Explicit "go" decision after reviewing staging results.

## Definition of done for merge

- Code, tests, and documentation updated together.
- Security-sensitive changes include auth/authorization checks.
- Observability for new behavior exists (logs/metrics/events).
- No unresolved critical test failures.

## Hard stop conditions (no merge)

- No staging/integration validation run.
- Failing critical tests or guardrails.
- Unclear security impact.
- No clear rollback path.

## Minimum staging smoke checklist

- Login, token refresh, and logout flow.
- Representative protected API endpoints.
- One primary end-to-end mission/workflow.
- Frontend critical user flow for affected area.
- Pipeline guard scripts executed in release context.

## Post-merge operational window

- Observe for 30-60 minutes after merge/deploy.
- Track error rate, auth failures, and latency.
- Roll back immediately on severe anomalies.
