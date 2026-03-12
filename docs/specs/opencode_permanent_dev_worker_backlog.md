# OpenCode Permanent Dev Worker Backlog

Version: 1.0
Status: Implementation Backlog for MVP
Parent Spec: `docs/specs/opencode_permanent_dev_worker.md`
Related:
- `docs/specs/opencode_permanent_dev_worker_interfaces.md`
- `docs/specs/opencode_permanent_dev_worker_review_briefing.md`

---

## 1 Purpose

This document converts the permanent OpenCode Dev-Worker specification into an execution backlog that a coding agent can implement incrementally.

Why: The main spec defines the target state, but delivery work needs explicit work packages, sequencing, and done criteria.

---

## 2 Delivery Rules

- Implement Control Plane foundations before mutating worker actions. Why: Safety infrastructure must exist before autonomy expands.
- Keep one writer per implementation surface at a time. Why: The repository operating model requires clear ownership boundaries.
- Preserve backward compatibility where possible and prefer additive changes first. Why: The MVP should avoid a big-bang migration.
- Treat `R4` actions as hard-blocked from the first implementation commit onward. Why: The highest-risk actions should never temporarily slip through.
- Add tests with each unit of work, not after the whole epic. Why: Governance features fail in subtle ways without immediate regression coverage.

---

## 3 Epic Map

| Epic | Goal | Priority | Depends On |
|---|---|---|---|
| E1 | Job and policy control spine | P0 | none |
| E2 | Approval, breakglass, and kill-switch | P0 | E1 |
| E3 | Audit outbox and event lifecycle | P0 | E1 |
| E4 | OpenCode worker intake and lease model | P0 | E1, E3 |
| E5 | `plan` mode | P0 | E4 |
| E6 | `build` mode | P1 | E4, E3 |
| E7 | `heal` mode | P1 | E2, E4 |
| E8 | `evolve` proposal flow | P2 | E6, E3 |
| E9 | Deployment, dashboards, and operations | P1 | E4, E6, E7 |

Why: The epic map reflects the architecture dependency order from governed control to bounded execution.

---

## 4 Sprint 1 Backlog

### E1 Job and Policy Control Spine

#### Ticket E1.1 JobContract model and persistence

- create canonical `JobContract v1` model
- persist current state plus immutable transition history
- add idempotency guard and expiry handling

Done criteria:

- valid contracts persist successfully
- invalid mode/risk combinations are rejected
- transition history is queryable by `job_id`
- duplicate idempotency requests do not create duplicate runnable jobs

Why: Contract and state are the backbone of the entire system.

#### Ticket E1.2 Risk classifier

- implement `R0-R4` classification helper
- factor action type, target environment, and blast radius into result
- emit risk result into job gate decision

Done criteria:

- same input yields same risk output
- `prod` mutations classify at least `R2`
- blocked `R4` examples are covered by tests

Why: Approval and execution behavior depend on deterministic risk classification.

#### Ticket E1.3 Policy decision engine

- implement mode allowlists
- compute `allowed_actions`, `forbidden_actions`, `approval_policy`, `verify_profile`
- reject unknown actions and invalid mode/action pairs

Done criteria:

- action subset validation is enforced
- `plan` mode results in read-only semantics
- `R4` actions always map to `blocked`

Why: Policy output is the signed boundary that OpenCode must obey.

### E2 Approval, Breakglass, and Kill-Switch

#### Ticket E2.1 Approval records for OpenCode jobs

- implement approval object bound to job intent hash and policy snapshot
- support `pending`, `approved`, `rejected`, `expired`, `cancelled`

Done criteria:

- self-approval is rejected
- expired approvals cannot be consumed
- approval emits canonical approval events

Why: Risky jobs need durable human authorization.

#### Ticket E2.2 Breakglass for heal mode

- support emergency approval path for `heal`
- enforce incident ref, justification, and TTL

Done criteria:

- breakglass works only for allowed `heal` actions
- breakglass cannot override `R4`
- all breakglass actions are separately auditable

Why: Emergency response needs speed without losing control.

#### Ticket E2.3 Kill-switch service

- add global, tenant, and mode kill-switch
- propagate cancellation to pending/running jobs

Done criteria:

- new leases are denied when switch active
- pending jobs move to `cancelled` or remain blocked
- propagation time meets the target envelope under test

Why: A permanent worker must be stoppable under incident conditions.

### E3 Audit Outbox and Event Lifecycle

#### Ticket E3.1 Durable outbox schema and writer

- create audit outbox model
- write before mutating execution starts
- mark publish success/failure and retry state

Done criteria:

- mutating job without outbox write cannot start
- outbox entries retain `job_id` and `correlation_id`
- failure state is visible to reconciliation logic

Why: Audit must be durable before side effects occur.

#### Ticket E3.2 Canonical event emission

- implement required job lifecycle events
- keep payload minima aligned with parent spec

Done criteria:

- event ordering follows spec
- missing mandatory fields fail tests
- publish failure triggers degraded-mode behavior

Why: Downstream governance and observability rely on stable events.

### E4 Worker Intake and Lease Model

#### Ticket E4.1 Signed job intake

- add internal endpoint or queue consumer for signed jobs
- verify signature and policy snapshot presence

Done criteria:

- unsigned jobs are rejected
- malformed signatures are rejected
- accepted jobs transition to runnable state only after full validation

Why: OpenCode must never execute unauthenticated work.

#### Ticket E4.2 Lease, heartbeat, and stuck-job recovery

- add lease acquisition and renewal
- mark stale jobs for recovery
- prevent double-running active jobs

Done criteria:

- only one worker can hold a mutating lease
- heartbeat expiry is detectable
- stale running jobs enter recoverable control state

Why: Permanent workers require strong duplicate-execution protection.

### E5 `plan` Mode

#### Ticket E5.1 Read-only workspace execution

- create read-only workspace handling
- support repo/log/metric/health inspection actions
- produce plan artifact

Done criteria:

- write attempts fail in `plan` mode
- plan artifact includes evidence refs
- end-to-end `plan` job reaches terminal success state

Why: `plan` mode is the safest first production capability.

---

## 5 Sprint 2 Backlog

### E6 `build` Mode

#### Ticket E6.1 Isolated mutable workspace

- create branch-scoped mutable workspace
- support patch application and cleanup

Done criteria:

- workspaces are tenant/job isolated
- failed runs discard or quarantine workspace
- branch naming is deterministic and traceable to job id

Why: Build mode needs controlled mutation without contaminating the repo.

#### Ticket E6.2 Build actions and evidence collection

- implement lint, test, build, artifact packaging, PR prep
- capture outputs as evidence refs

Done criteria:

- failing lint/test/build blocks `succeeded`
- evidence refs include outputs and resulting SHA or patch
- no direct merge behavior exists

Why: Build mode should generate reviewable change candidates, not silent repository mutations.

#### Ticket E6.3 Verification coordinator integration

- add verify phase and failure mapping
- move failed builds into `rollback_pending` or `failed`

Done criteria:

- verification failure prevents completion
- verify outputs are queryable
- test matrix covers pass/fail/inconclusive outcomes

Why: Build mutations are only valid after verification.

### E7 `heal` Mode

#### Ticket E7.1 Healing action adapters

- implement allowlisted adapters for `service_restart`, `config_restore`, `artifact_rollback`, `queue_unstick`, `cache_clear_scoped`

Done criteria:

- each adapter validates target scope
- each adapter emits action execution evidence
- unsupported heal action requests are rejected

Why: Healing power must be narrow and explicit.

#### Ticket E7.2 Heal verification and rollback

- run post-action health checks
- trigger rollback when verify fails and rollback exists

Done criteria:

- before/after health state is captured
- rollback path executes for failed verification
- unresolved failures escalate cleanly

Why: Healing without verification can worsen incidents invisibly.

### E8 `evolve` Proposal Flow

#### Ticket E8.1 EvolutionProposal creation

- create proposal object and proposal events
- tie proposal to evidence package and validation plan

Done criteria:

- no proposal can directly activate changes
- proposal records preserve provenance

Why: Evolution should start as governed proposal, not direct mutation.

#### Ticket E8.2 ValidationRun orchestration

- run benchmark or validation suite on proposal branch
- attach results to proposal package

Done criteria:

- validation failure blocks promotion readiness
- outputs are reviewable without reproducing the run manually

Why: Promotion quality depends on reproducible evidence.

### E9 Deployment, Dashboards, and Ops

#### Ticket E9.1 Compose and Coolify profiles

- add service definition, networking, env wiring, and health checks

Done criteria:

- local and remote topologies are equivalent in role separation
- worker readiness depends on control dependencies

Why: Deployment drift between environments causes governance and reliability gaps.

#### Ticket E9.2 Operational dashboards and alerts

- expose job state, stuck jobs, approval aging, rollback outcomes, audit failures

Done criteria:

- operators can identify blocked/stuck/degraded execution quickly
- required alerts trigger from test fixtures or simulated conditions

Why: A permanent worker without observability creates opaque risk.

---

## 6 API and Model Mapping

Use `docs/specs/opencode_permanent_dev_worker_interfaces.md` as the implementation contract for:

- API endpoints
- persistence models
- event names
- error codes
- state transition invariants

Why: The backlog should point the coding agent to the authoritative low-level interface definitions.

---

## 7 Review Gates Per Epic

| Epic | Mandatory Review |
|---|---|
| E1 | contract and lifecycle review |
| E2 | security/governance review |
| E3 | audit/event ordering review |
| E4 | execution isolation review |
| E5 | read-only enforcement review |
| E6 | verification and no-direct-merge review |
| E7 | fail-safe healing review |
| E8 | anti-drift evolution review |
| E9 | deployment and ops review |

Why: Review should happen continuously, not only after the whole initiative is complete.

---

## 8 Coding Agent Hand-Off

Implement in this order:

1. E1
2. E2
3. E3
4. E4
5. E5
6. E6
7. E7
8. E8
9. E9

After each epic:

- run the relevant targeted tests
- update audit/event fixtures if contracts changed
- prepare a concise review package for Mecker Agent and `brain-review-critic`

Why: This sequence preserves the governance-first architecture and simplifies second-pass review.

---

End of backlog.
