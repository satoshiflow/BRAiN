# Runtime Control Post-Rollout 24h Monitoring (Step 4)

Date: 2026-04-01
Duration: First 24h after rollout
Owner: Platform + Runtime Ops

## Purpose

Detect regressions early and enforce fast containment via registry rollback and override governance.

## Monitoring Cadence

- 0-2h: every 15 minutes
- 2-8h: every 30 minutes
- 8-24h: every hour

## Core Signals

1. Health/availability (`/api/health`, ControlDeck runtime page)
2. Resolver quality (validation rate, unusual route/model/worker shifts)
3. Queue/worker stability (stuck claims, lease drift)
4. Governance integrity (override lifecycle + timeline continuity)
5. AXE context behavior (context_mode distribution, trim rate, token trends)
6. Provider/connector posture (timeouts, fallback behavior, blocked connector events)

## Checkpoint Procedure

At each checkpoint:

1. Verify health and auth reachability.
2. Validate runtime-control page timeline + active overrides.
3. Run one representative `resolve` call and verify `validation.valid=true`.
4. Run one AXE smoke message and confirm context telemetry returned.
5. Inspect worker/task progression for stuck states.
6. Record evidence snapshot.

## Alert Thresholds

Trigger immediate incident handling if:

- health fails in 2 consecutive checkpoints
- sustained stuck queued/claimed task growth
- repeated invalid resolver outputs for stable contexts
- missing timeline events after mutation calls
- critical provider failures without fallback

## Containment Actions

1. Apply emergency/manual override to force safe worker/provider.
2. Promote rollback registry version.
3. Temporarily block risky connectors via runtime policy.
4. Freeze additional runtime mutations until stable.

## 24h Exit Criteria

Downgrade elevated monitoring when all are true:

- no critical incidents in the last 8h
- stable queue/lease behavior
- stable resolver validation and expected routing
- no unresolved override approval backlog
- no unexplained timeline gaps
