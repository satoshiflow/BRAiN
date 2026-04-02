# Paperclip Docker Installation and Validation (for BRAiN Integration)

Status: Ready  
Date: 2026-04-01

## Goal

Run a real Paperclip instance in Docker and wire BRAiN external executor calls to it for end-to-end validation.

## 1. Install / start Paperclip container

Reference upstream quickstart compose:

```bash
git clone --depth 1 https://github.com/paperclipai/paperclip.git /home/oli/dev/paperclip-upstream
cd /home/oli/dev/paperclip-upstream/docker
BETTER_AUTH_SECRET=change-me PAPERCLIP_PORT=3110 docker compose -f docker-compose.quickstart.yml up -d --build
```

Expected endpoint:

- `http://localhost:3110`

Operational handoff surface exposed by `paperclip_worker`:

- `http://localhost:3111`

Operational handoff surface exposed by `openclaw_worker`:

- `http://localhost:3112`

## 2. Configure BRAiN to reach Paperclip

In `.env.local` set:

- `PAPERCLIP_BASE_URL=http://host.docker.internal:3110`
- `PAPERCLIP_APP_BASE_URL=http://localhost:3111`
- `PAPERCLIP_EXECUTION_ENDPOINT=/api/executions`
- `BRAIN_EXTERNAL_EXECUTOR_PERMIT_SECRET=<strong-random-secret>`

Optional:

- `PAPERCLIP_API_KEY=<if your endpoint requires it>`
- `PAPERCLIP_BRAIN_SERVICE_TOKEN=<preferred worker token>`

## 3. Start BRAiN local stack with paperclip worker

```bash
cd /home/oli/dev/brain-v2
docker compose -f docker-compose.local.yml --env-file .env.local up -d --build backend openclaw paperclip_worker axe_ui
```

## 4. Runtime policy activation

Paperclip executor is intentionally disabled by default.

Enable through runtime control by approved override/registry promotion:

- `workers.external.paperclip.enabled=true`
- ensure `workers.selection.allowed_executors` includes `paperclip`
- ensure `security.allowed_connectors` includes `paperclip` when connector allowlist is active

Implementation note for local admin accounts without tenant binding:

- use `tenant_scope=system` for override request + approval
- `tenant_scope=tenant` cannot be approved when `principal.tenant_id` is null

## 5. Validation checklist

1. Trigger AXE command with paperclip worker bridge:
   - `/paperclip <your task>`
2. Verify TaskLease creation and linkage:
   - task has `skill_run_id`, `worker_target=paperclip`, `execution_permit`
3. Verify worker run transitions:
   - claim -> start -> complete/fail
4. Verify SkillRun terminalization:
   - `succeeded` or `failed` with sanitized reason
5. Verify policy guardrails:
   - `CONNECTOR_BLOCKED` when disallowed
   - `EXECUTOR_BLOCKED` when executor disabled

## 6. Operational notes

- If upstream Paperclip build is slow, keep it running persistently and only restart BRAiN containers.
- `paperclip_worker` now serves the bounded MissionCenter handoff UI on `3111` while upstream Paperclip execution can stay on `3110`.
- `paperclip_worker` includes fallback behavior if Paperclip endpoint fails; disable it with `PAPERCLIP_EXECUTION_FALLBACK_ENABLED=false` for fail-closed production posture.
- On stale local databases, missing tables may block runtime-control/audit paths. Minimum required tables for this flow include `control_plane_events` and `audit_events`.

## 7. Standard recovery + smoke flow

From repo root (`/home/oli/dev/brain-v2`):

```bash
./scripts/alembic_doctor.sh reconcile
docker exec brain-backend sh -lc "cd /app && alembic upgrade heads"
./scripts/smoke_external_executors.sh
```

What this guarantees:

1. local migration drift gets reconciled
2. backend schema is advanced to available heads
3. OpenClaw + Paperclip both execute end-to-end via SkillRun/TaskLease
4. both bounded MissionCenter handoff surfaces are reachable locally

Reference docs:

- `docs/roadmap/LOCAL_DB_MIGRATION_REPAIR_RUNBOOK.md`
- `docs/roadmap/PAPERCLIP_OPENCLAW_UNIFIED_EXECUTOR_IMPLEMENTATION_PLAN.md`
