# Epic 2 Operations Runbook

Status: Active
Date: 2026-03-22

## Purpose

Operational handling for governed learning, adaptive freeze, and proposal lifecycle health in Epic 2.

## Core endpoints

- `GET /api/evolution/ops/summary`
  - tenant-scoped proposal status counts
  - adaptive freeze state
  - review queue and blocked/applied counters
  - recent learning control-plane events

- `GET /api/evolution/adaptive-freeze/status`
- `POST /api/evolution/adaptive-freeze/enable`
- `POST /api/evolution/adaptive-freeze/disable`

## Incident handling

### 1. Suspected unsafe self-optimization

1. Enable adaptive freeze:
   - `POST /api/evolution/adaptive-freeze/enable`
2. Verify freeze state:
   - `GET /api/evolution/adaptive-freeze/status`
3. Inspect current queue and blocked/applied counters:
   - `GET /api/evolution/ops/summary`

### 2. Global emergency stop

1. Enable system safe mode:
   - `POST /api/safe-mode/enable`
2. Any `applied` evolution transitions are blocked while safe mode is active.

### 3. Controlled resume

1. Keep safe mode disabled only after review and mitigation.
2. Disable adaptive freeze once governance approves restart:
   - `POST /api/evolution/adaptive-freeze/disable`
3. Continue with proposal review; apply still requires:
   - governance evidence
   - `validation_state=validated`
   - rollback plan metadata

## Required apply metadata

For transition to `applied`, proposal metadata must include:

- `approval_id`
- `policy_decision_id`
- `reviewer_id`
- `rollback_plan_id`
- `rollback_steps`
- `rollback_owner`

Missing metadata causes fail-closed rejection.

## Local verification

- `PYTHONPATH=. pytest tests/test_evolution_control.py -q`
- `./scripts/local_ci_gate.sh backend-fast`
