# Purpose/Routing Attachment Contract (v1)

Status: Draft (Phase 1 Sprint 1.3)

## Purpose

Define where purpose and upper routing contracts attach to existing BRAiN
runtime flows without creating a parallel runtime.

## Canonical Attachment Flow

`Intent -> DecisionContext -> PurposeEvaluation -> TaskProfile -> DomainResolution -> RoutingDecision -> SkillRun -> TaskLease/JobContract -> Evaluation -> Learning`

## Ownership Boundaries

- `DecisionContext`, `PurposeEvaluation`: upper decision layer (governed)
- `DomainResolution`: `backend/app/modules/domain_agents/*`
- `RoutingDecision` (upper): produced before execution handoff
- `SkillRun`: canonical execution write owner (`backend/app/modules/skill_engine/*`)
- `TaskLease`/OpenCode contracts: subordinate dispatch only
- provider selection: lower layer (`provider_bindings` + capability runtime)

## Invariants

- No path may execute business work without terminating in `SkillRun`.
- Upper routing may not replace lower provider binding resolution.
- Domain review does not equal governance approval.
- Policy and approval gates remain authoritative for sensitive actions.
- Tenant/correlation/causation continuity must be preserved across all handoffs.

## Integration Points

1. Mission/API/AXE intent ingress normalizes `DecisionContext`.
2. Purpose layer emits `PurposeEvaluation`.
3. `domain_agents` consumes context/evaluation and produces domain resolution.
4. Routing layer emits `RoutingDecision` and selected strategy.
5. `skill_engine` creates `SkillRun` with frozen upstream snapshots.
6. Execution and dispatch continue through existing `SkillRun` and task lease/job
   mechanisms.

## Validation Rules

- Every `RoutingDecision` used for execution must reference one
  `PurposeEvaluation` and one `DecisionContext`.
- Every resulting `SkillRun` must reference upstream decision artifacts in
  snapshot form.
- Sensitive-path transitions must include policy/approval evidence.

## Error Codes

- `PA-001 MISSING_PURPOSE_EVALUATION`
- `PA-002 ROUTING_WITHOUT_CONTEXT`
- `PA-003 EXECUTION_BYPASS_ATTEMPT`
- `PA-004 GOVERNANCE_EVIDENCE_MISSING`

## Event Types

- `routing.decision.created.v1`
- `routing.decision.escalated.v1`
- `routing.decision.rejected.v1`
- `routing.skillrun.handoff.created.v1`

## Storage

- PostgreSQL: durable decision and handoff records
- Redis: optional ephemeral projections for orchestration status
- EventStream: handoff and trace continuity events
