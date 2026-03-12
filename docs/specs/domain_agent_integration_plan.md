# Domain Agent Integration Plan

Status: Active planning baseline  
Scope: Non-breaking introduction of the Domain Agent layer into BRAiN.

## Objective

Introduce a `Domain Agent` layer that improves domain-aware orchestration without rebuilding the existing runtime.

This plan intentionally defines guardrails and sequencing, not a frozen low-level class design.

## Design Principles

- non-breaking introduction
- reuse existing control-plane modules first
- execution remains on canonical governed paths
- small MVP before broad domain rollout
- fail closed on uncertainty
- domain review is separate from governance review

## Phase 1: Contracts and Reference Mission

Deliverables:
- `docs/specs/domain_agent_contract.md`
- one BRAiN reference mission document under `docs/`
- targeted updates to orchestration docs

Purpose:
- fix boundaries before code spreads
- align future implementers and reviewers on shared intent

Exit criteria:
- Domain Agent role is unambiguous
- reference mission can be used as design calibration

## Phase 2: Domain Registry MVP

Recommended scope:
- domain metadata contract
- in-memory or lightweight service-backed registry for first iteration
- explicit support for:
  - domain identity
  - allowed skills/capabilities
  - allowed specialist roles
  - review profile
  - budget profile
  - escalation profile

Suggested insertion point:
- `backend/app/modules/domain_agents/`

Non-goals:
- no full tenant-admin UI yet
- no deep persistence coupling until contract stabilizes

## Phase 3: Domain Agent Base

Recommended scope:
- base schemas
- registry-backed domain resolution
- specialist/skill selection inputs and outputs
- review decision structure
- escalation recommendation structure

Expected integrations:
- `planning/` for dependency graphs or generic plan nodes
- `agent_management/` for specialist/agent metadata
- `skill_engine/` for canonical execution requests
- `supervisor/` for escalation and governance handoff

Non-goals:
- no direct router exposure if internal service flow is enough
- no multi-domain mesh in first pass

## Phase 4: First Concrete Domain

Recommended first domain:
- `programming`

Why first:
- easiest to test against current repo reality
- close to current BRAiN delivery needs
- lower legal/regulatory exposure than nutrition or finance

Expected capabilities:
- task decomposition for implementation work
- specialist routing for coding, verification, and review
- domain review before supervisor escalation

## Phase 5: Observability and Control

After the first domain works, integrate:
- domain events into EventStream
- domain health views into `system_health`
- performance attribution into `karma`
- budget pressure or credits into `credits`

This phase should remain incremental. Avoid over-coupling in MVP.

## Phase 6: Additional Domains

Possible follow-on domains:
- `research`
- `marketing`
- `infrastructure`
- `finance`
- `business`

Admission rule:
- each new domain must justify its own review profile, budget model, and escalation behavior

Supervisor handoff stub:
- escalations should produce a structured handoff payload (domain key, reasons, requested-by, risk tier, correlation id)
- this payload is the forward-compatible bridge to explicit supervisor escalation APIs

Current API contract (implemented baseline):
- `POST /api/supervisor/escalations/domain`
- `GET /api/supervisor/escalations/domain`
- `GET /api/supervisor/escalations/domain/{escalation_id}`
- `POST /api/supervisor/escalations/domain/{escalation_id}/decision`

Escalation state machine (strict):
- `queued -> in_review | cancelled`
- `in_review -> approved | denied | cancelled`
- `approved -> (terminal)`
- `denied -> (terminal)`
- `cancelled -> (terminal)`

Execution gate rule:
- Domain Agent `execute_now=true` with `supervisor_escalation_id` is allowed only when escalation state is `approved`
- non-approved state returns conflict and must not execute skills

## Safety Guardrails

- execution continues through `SkillRun` / governed job contracts only
- Domain Agent may recommend but not self-authorize policy exceptions
- domain-level spawn limits are mandatory
- no tenant-derived mutations from request body
- no reuse of deprecated `factory_executor` as orchestration core

## Review Expectations

Implementation should be reviewed for:
- boundary correctness
- governance fit
- tenant isolation
- audit/event durability
- anti-pattern drift toward recursive orchestration or hidden execution

## Recommended Implementation Order

1. reference mission document
2. domain contract and integration docs
3. module scaffold
4. registry MVP
5. base service layer
6. first concrete domain
7. tests and hardening

## Success Criteria

- Domain Agent improves orchestration clarity without creating shadow runtime paths
- first domain integrates cleanly with existing modules
- future domains can be added by extension rather than rewrite
- governance and execution boundaries remain intact
