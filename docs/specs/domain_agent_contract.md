# Domain Agent Contract (v1)

Status: Draft for high-priority implementation  
Scope: Defines `Domain Agent` as BRAiN's domain-aware orchestration layer between governance and execution.

## Purpose

`Domain Agent` is the technical control-plane abstraction for domain-specific reasoning.

It exists to prevent generic orchestration from becoming chaotic once BRAiN must handle
multi-domain missions such as product delivery, research, growth, finance, or infrastructure.

`Domain Agent` is the runtime expression of the "Cardinal" metaphor.

## Why This Layer Exists

Current repo surfaces already cover parts of the stack:
- governance and escalation in `supervisor/`
- planning primitives in `planning/`
- domain-specific planning in `business_factory/`
- governed execution in `skill_engine/`
- agent lifecycle and delegation in `agent_management/`

What is missing is a domain-owned coordination layer that can:
- decompose work according to domain logic
- select suitable specialists and skills
- keep domain-level review and plausibility checks separate from governance review
- enforce domain budgets and spawn discipline
- report upward to supervisor without becoming a second supervisor

## Position in the Stack

Canonical stack:

`User intent/mission -> Governance/Supervisor -> Domain Agent -> Specialist/Skill selection -> SkillRun -> Skill Engine/OpenCode -> Evaluation -> Domain review -> Supervisor escalation if required`

Metaphor mapping:
- User = God
- Governance/Supervisor = Pope
- Domain Agent = Cardinal
- Specialist agents = Priests
- Workers/OpenCode/Skill Engine = Executors

## Ownership Boundaries

`Domain Agent` owns:
- domain-aware task decomposition
- domain-specific specialist, capability, and skill selection
- domain review and plausibility checks
- domain-local budgets, quotas, and spawn limits
- domain-local escalation preparation
- domain telemetry for health, learning, and performance attribution

`Domain Agent` reads but does not own:
- global governance policy
- skill and capability canonical definitions
- agent lifecycle truth
- mission source records
- final execution history

`Domain Agent` must not own:
- direct business execution
- final approval authority
- canonical `SkillRun` runtime state
- provider binding or tool credentials
- global mission governance

## Core Responsibilities

- classify incoming work into a domain or domain bundle
- convert mission/intent/task into domain-shaped execution plans
- choose specialists, skills, and sequencing strategy
- decide when to parallelize and when to gate for review
- score plausibility before and after execution
- escalate to supervisor when risk, ambiguity, or policy thresholds are crossed

## Non-Responsibilities

- no direct execution of user/business actions
- no bypass of `SkillRun`
- no second control plane parallel to supervisor
- no reintroduction of `factory_executor` patterns as a general runtime

## Domain Model Requirements

Minimum durable or reconstructable metadata per domain:
- `domain_key`
- `display_name`
- `status`
- `allowed_skill_keys`
- `allowed_capability_keys`
- `allowed_specialist_roles`
- `review_profile`
- `budget_profile`
- `risk_profile`
- `escalation_profile`

Recommended runtime fields:
- `active_runs`
- `spawn_count`
- `health_score`
- `last_reviewed_at`
- `last_escalation_at`

## Canonical Runtime Rules

- every domain-owned action that needs execution must resolve to one or more `SkillRun`s
- all execution delegation must preserve `tenant_id`, `correlation_id`, and `causation_id`
- domain review must not be treated as governance approval
- domain routing must fail closed when no eligible path exists
- domain spawn limits must be enforced before delegated execution begins

## Integration Points

Primary integration surfaces:
- `backend/app/modules/agent_management/`
- `backend/app/modules/supervisor/`
- `backend/app/modules/planning/`
- `backend/app/modules/skill_engine/`
- `backend/mission_control_core/core/event_stream.py`

Secondary integration surfaces:
- `backend/app/modules/business_factory/`
- `backend/app/modules/autonomous_pipeline/`
- `backend/app/modules/dna/`
- `backend/app/modules/karma/`
- `backend/app/modules/credits/`
- `backend/app/modules/system_health/`

## Relationship to Existing Modules

### Supervisor
- remains policy-aware governance coordinator
- may approve, deny, degrade, or escalate
- does not perform domain decomposition

### Planning
- remains generic decomposition and dependency engine
- may be reused by Domain Agent
- does not become the domain truth layer

### Skill Engine
- remains canonical execution surface
- Domain Agent selects and requests runs, but does not execute work directly

### Business Factory
- remains a useful example of domain-specific planning and risk shaping
- must not become the generic implementation base for Domain Agent runtime

### Factory Executor
- remains deprecated
- may inform anti-pattern review only

## Minimal API Expectations

Suggested internal service surface:
- `resolve_domain(...)`
- `decompose_for_domain(...)`
- `select_specialists(...)`
- `select_skills(...)`
- `review_domain_result(...)`
- `should_escalate(...)`

External API is optional for MVP. If exposed, keep it narrow and read/governance safe.

## Event Requirements

Target event family:
- `domain.agent.resolved.v1`
- `domain.agent.decomposed.v1`
- `domain.agent.specialists.selected.v1`
- `domain.agent.review.completed.v1`
- `domain.agent.escalation.requested.v1`

Durability rule:
- domain decision records, audit writes, and outbox insert must complete before publish.

## Security and Governance Rules

- `tenant_id` is always auth-derived or identity-derived
- domain policy cannot override global governance policy
- health/nutrition/finance/legal domains must support stricter review profiles
- credentials and payment secrets remain outside domain logic objects
- domain escalation must be explicit and auditable

## First MVP Rule

MVP should introduce:
- one Domain Registry
- one generic Domain Agent base layer
- one concrete reference domain: `programming`

Do not start with a broad domain fleet.

## Done Criteria

- Domain Agent is explicitly documented as a domain-aware orchestration layer
- boundaries vs supervisor, planning, and skill engine are clear
- no new execution path bypasses `SkillRun`
- deprecated execution modules are not reused as the new runtime pattern
- implementation leaves room for additional domains without forcing a full rewrite
