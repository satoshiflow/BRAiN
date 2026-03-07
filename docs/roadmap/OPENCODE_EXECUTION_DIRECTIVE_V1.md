# OpenCode Execution Directive v1

Date: 2026-03-07
Scope: Roadmap v2 autonomous execution guardrails

## Role boundaries

- OpenCode is Explorer/Dev/Repair executor.
- OpenCode is not orchestrator, not sovereign, not governance authority.
- BRAiN owns decisioning, prioritization, approvals, and stop authority.

## Mandatory implementation rules

1. Target-path only for new runtime modules: `backend/app/modules/*`.
2. Event backbone is EventStream; no legacy event bus reintroduction.
3. Security-sensitive actions require audit + correlation ID.
4. High-risk mutation/recovery actions must be governance-hook capable.
5. Migrations must be replayable on a clean dev database.
6. If blocked, skip item, log blocker with evidence, continue next item.

## Delivery artifact minimum

For each completed item:
- change summary
- files touched
- verification commands
- outcome and known residual risk

For each blocked item:
- blocker description
- failing command or log reference
- impact assessment
- next recommended unblock step
