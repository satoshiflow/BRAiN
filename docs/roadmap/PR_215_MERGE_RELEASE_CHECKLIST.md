# PR 215 Merge And Release Checklist

PR: `#215`
URL: `https://github.com/satoshiflow/BRAiN/pull/215`
Branch: `feat/paperclip-governed-ops-supervisor`

## Scope

This PR delivers:

- governed external-app handoff for `paperclip` and `openclaw`
- bounded MissionCenter surfaces in `paperclip_worker` and `openclaw_worker`
- canonical execution context and bounded action requests
- ControlDeck inbox and supervisor triage flows
- retry materialization and supervisor escalation handoff
- external-ops observability alerts and dashboard notification routing

## Merge Preconditions

- Review complete for:
  - `backend/app/modules/external_apps/*`
  - `backend/app/modules/runtime_control/*`
  - `backend/app/modules/supervisor/service.py`
  - `frontend/controldeck-v3/src/app/(protected)/external-operations/*`
  - `frontend/controldeck-v3/src/app/(protected)/supervisor/*`
  - `paperclip_worker/main.py`
  - `openclaw_worker/main.py`
- Local verification rerun on merge candidate:
  - `cd frontend/controldeck-v3 && npm run lint`
  - `cd frontend/controldeck-v3 && npm run build`
  - `cd frontend/controldeck-v3 && npm run test`
  - `cd frontend/controldeck-v3 && npm run test:e2e`
  - `cd backend && PYTHONPATH=. pytest tests/test_external_apps_service.py tests/test_external_apps_router.py tests/test_runtime_control_tenant_isolation.py tests/test_task_queue_tenant_reads.py -q`
  - `cd backend && PYTHONPATH=. pytest tests/test_supervisor_table_bootstrap.py tests/test_supervisor_escalations_router.py -q`
  - `cd paperclip_worker && python3 -m pytest tests/test_worker_app.py -q`
  - `cd openclaw_worker && python3 -m pytest tests/test_worker_app.py -q`
  - `./scripts/run_rc_staging_gate.sh`
- If GitHub Actions remains blocked by billing, treat local verification evidence as the authoritative gate.
- Confirm branch still fast-forwards cleanly against `main`.

## Environment And Config Checks

- Production secrets set:
  - `BRAIN_EXTERNAL_APP_HANDOFF_SECRET`
  - `BRAIN_EXTERNAL_EXECUTOR_PERMIT_SECRET`
- External app URLs set correctly:
  - `PAPERCLIP_BASE_URL`
  - `PAPERCLIP_APP_BASE_URL`
  - `OPENCLAW_BASE_URL`
  - `OPENCLAW_APP_BASE_URL`
  - `CONTROLDECK_BASE_URL`
- Fail-closed posture enabled in production:
  - `PAPERCLIP_EXECUTION_FALLBACK_ENABLED=false`
  - `OPENCLAW_EXECUTION_FALLBACK_ENABLED=false`
- Confirm auth/session behavior for ControlDeck, backend and external app surfaces in the target environment.

## Release Steps

1. Merge PR `#215` into `main`.
2. Deploy backend, `paperclip_worker`, `openclaw_worker` and `controldeck-v3` together.
3. Ensure target database schema is available.
   Note: supervisor reads now self-bootstrap `domain_escalations` for older persisted local databases, but production rollout should still use the normal schema management path.
4. Verify runtime config in deployed environment:
   - `paperclip` enabled only where intended
   - `openclaw` enabled only where intended
   - allowed connectors/executors align with policy

## Post-Deploy Smoke Checks

### ControlDeck

- Open `/external-operations`
- Confirm both executor cards render:
  - `Paperclip`
  - `OpenClaw`
- Confirm `External Ops Alerts & SLOs` section renders
- Confirm Supervisor preview panel renders

### External Apps

- Open a Paperclip task via `Open in Paperclip`
- Open an OpenClaw task via `Open in OpenClaw`
- Confirm both handoff pages resolve and show governed context

### Action Requests

- Trigger one bounded action request from Paperclip or OpenClaw
- Approve or reject it in ControlDeck
- Confirm timeline and inbox update

### Supervisor

- Approve one escalation request
- Confirm supervisor handoff appears in `/supervisor`
- Open detail page and submit a supervisor decision

### Dashboard

- Open `/dashboard`
- Confirm `External Ops Notifications` block is visible
- Confirm active alert count/signal appears when test data exists

## Rollback Considerations

- If rollout fails in external-app flow only, first disable executor access through runtime policy before reverting code.
- If operator surfaces are degraded but backend runtime is healthy, prefer hiding the UI surface over leaving half-working action paths exposed.
- If supervisor escalation reads fail unexpectedly, inspect `domain_escalations` schema state first.

## Operational Watchlist After Release

Watch for 24h after deploy:

- rising `handoff exchange failed` events
- stale external action requests older than 30 minutes
- stale supervisor escalations older than 30 minutes
- retry spikes on one executor only
- mismatched executor routing between runtime decision and actual worker target

## Done Criteria

- Merge completed
- Deployment completed
- Smoke checks passed
- No critical external-ops alerts after release stabilization window
