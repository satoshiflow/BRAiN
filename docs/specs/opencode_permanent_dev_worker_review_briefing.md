# OpenCode Permanent Dev Worker Review Briefing

Version: 1.0
Status: Review Companion
Parent Spec: `docs/specs/opencode_permanent_dev_worker.md`
Related:
- `docs/specs/opencode_permanent_dev_worker_backlog.md`
- `docs/specs/opencode_permanent_dev_worker_interfaces.md`

---

## 1 Purpose

This document defines the expected review scope and attack angles for Mecker Agent, `brain-review-critic`, and any security/governance reviewer.

Why: Strong reviews are more effective when they are pointed at the likely failure surfaces instead of producing generic critique.

---

## 2 Review Objective

Review whether the implementation preserves the core rule:

`BRAiN is the only Control Plane; OpenCode is only the Execution Plane.`

Why: This is the most important architectural invariant in the entire design.

---

## 3 Required Input Set

Always review these files together:

- `docs/specs/opencode_permanent_dev_worker.md`
- `docs/specs/opencode_permanent_dev_worker_backlog.md`
- `docs/specs/opencode_permanent_dev_worker_interfaces.md`
- implementation diffs and tests

Optional context:

- `docs/specs/approval_gate.md`
- `docs/specs/self_healing_control_loop.md`
- `docs/specs/runtime_deployment_contract.md`

Why: The main spec alone is not enough to catch interface or backlog drift.

---

## 4 Reviewer Roles

### Mecker Agent

Focus on:

- missing edge cases
- hidden complexity
- vague failure handling
- implementation shortcuts that weaken safety

Why: The Mecker Agent is most useful when it attacks sloppy assumptions.

### `brain-review-critic`

Focus on:

- architecture drift
- contract gaps
- lifecycle inconsistencies
- governance blind spots

Why: The critic should challenge whether the solution is complete and internally consistent.

### Security/Governance Reviewer

Focus on:

- fail-closed behavior
- approval bypasses
- tenant isolation
- audit durability
- breakglass misuse

Why: Security review should inspect the control boundary, not just code style.

---

## 5 Mandatory Review Questions

1. Can any path reach execution without a valid BRAiN-issued signed job? Why: That would create a shadow control plane.
2. Can any `R4` action be executed through bug, fallback, or alternate adapter path? Why: MVP safety depends on hard technical block.
3. Can `plan` mode mutate anything under any failure or adapter shortcut? Why: Read-only must be technically guaranteed.
4. Can a mutating job succeed without verification? Why: Success without verify is a broken control loop.
5. Can approval, breakglass, or kill-switch decisions be replayed or bypassed? Why: Governance artifacts must be single-use and authoritative.
6. Can one tenant access another tenant's workspace, cache, lease, or evidence? Why: Tenant isolation is a hard boundary.
7. Can EventStream or audit failure still allow further mutating steps? Why: Evidence loss must halt escalation.
8. Can healing actions worsen incidents without forced rollback or escalation? Why: Self-healing must stay bounded.
9. Can evolution flows directly activate changes without PromotionDecision? Why: Evolution must not bypass governance.
10. Are there hidden direct paths to `main`, prod deploy, schema migration, or secret rotation? Why: These are explicitly forbidden in the MVP.

---

## 6 Specific Failure Modes to Hunt

- unsigned internal queue messages accepted as trusted
- stale approval reused on modified job intent
- kill-switch blocks new jobs but not already queued adapter steps
- verification errors logged but ignored
- alternate endpoint exposes worker action without full gate evaluation
- workspace permissions differ between local and Coolify deployments
- approval policy says `blocked` but retry path still executes
- rollback code exists but is not mandatory where required
- event ordering differs under retry, timeout, or degraded mode
- worker receives broad secret scope because adapter scoping was skipped

Why: These are realistic ways governed execution systems fail in practice.

---

## 7 Required Review Outputs

Each reviewer should return:

- `role`
- `review_scope`
- `findings`
- `must_fix`
- `optional_improvements`
- `blocking_decision`
- `recommended_next_action`

Why: Standardized output makes multi-review consolidation easier.

---

## 8 Blocking Conditions

The review must block release if any of the following is true:

- unsigned job execution is possible
- `R4` action execution is possible
- mutating job can complete without verification
- approval or breakglass can be replayed or self-approved
- audit durability is not guaranteed before mutation
- tenant isolation is not technically enforced
- kill-switch cannot stop new execution quickly enough

Why: These issues break the central safety model, not just implementation quality.

---

## 9 Suggested Review Prompt

Use this prompt for adversarial review:

```text
Review the OpenCode permanent dev worker implementation against:
- docs/specs/opencode_permanent_dev_worker.md
- docs/specs/opencode_permanent_dev_worker_backlog.md
- docs/specs/opencode_permanent_dev_worker_interfaces.md

Act as a strict critical reviewer.

Your task:
1. Find any path where OpenCode can behave as a shadow control plane.
2. Find any missing contract fields, lifecycle gaps, or ambiguous state transitions.
3. Find any approval, breakglass, audit, verification, rollback, or kill-switch bypass.
4. Find any tenant isolation or secret scoping weakness.
5. Verify that `R4` actions are technically blocked in the MVP.

Return:
- role
- review_scope
- findings
- must_fix
- optional_improvements
- blocking_decision
- recommended_next_action
```

Why: A precise review prompt increases the chance of high-value criticism instead of generic commentary.

---

## 10 Hand-Off Note

If only one file can be passed initially, pass:

- `docs/specs/opencode_permanent_dev_worker.md`

That file now explicitly links to the backlog, interfaces, and review briefing companion docs.

Why: This preserves your intended hand-off flow while still letting downstream agents discover the full review set.

---

End of review briefing.
