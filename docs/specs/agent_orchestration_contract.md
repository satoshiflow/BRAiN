# Agent Orchestration Contract (v1)

Status: Draft for Epic 7  
Scope: Defines agents as orchestration/control-plane actors over `SkillRun`, not as business-logic containers.

## Purpose

This contract redefines agents as runtime coordinators that:
- select and invoke skills
- delegate work
- supervise execution
- escalate when governance requires

Agents must not remain hidden feature implementations.

## Repo Alignment

- Reuse surface: `backend/app/modules/agent_management/`, `supervisor/`, `autonomous_pipeline/`
- Execution contracts: `docs/specs/skill_run.md`, `docs/specs/constitution_gate.md`

## Ownership Boundaries

Agents own:
- registration and lifecycle
- declared capabilities/skill affinity metadata
- delegation decisions
- supervision and escalation

Agents do not own:
- core business logic
- canonical execution history
- registry truth for skills/capabilities

## Core Agent Responsibilities

- decide whether to invoke, delegate, or decline
- request `SkillRun` creation
- monitor run status
- handle escalation and approval requests
- coordinate multi-agent decomposition when needed

Tenant rule:
- `tenant_id` for agent-triggered actions is token-derived or agent-identity-derived, never request-body-derived.

## Canonical Delegation Path

`Agent -> Skill selection -> SkillRun creation -> Constitution Gate -> Skill Engine -> Evaluation -> Agent receives result`

No direct business path should bypass `SkillRun` for new architecture work.

## Repo Mapping Snapshot

Current repo surfaces to migrate first:
- `backend/app/modules/agent_management/`
  - keep registration, heartbeat, fleet metadata, and health ownership
  - add agent-facing skill invocation as a governed wrapper over `SkillRun`
- `backend/app/modules/supervisor/`
  - replace mission-stubbed execution counts with `SkillRun`-derived runtime projections
  - keep supervisor as read/coordination/escalation layer only

Immediate target-state rule:
- agent-facing execution APIs must call the Skill Engine, not embed feature execution logic inside `agent_management` or `supervisor`.

## Agent Model Requirements

Minimum agent metadata:
- `agent_id`
- `tenant_id`
- `status`
- `declared_skill_affinity`
- `trust_tier`
- `allowed_actions`
- `heartbeat_state`

## Supervisor Contract

Supervisor is the orchestration policy layer.

Supervisor responsibilities:
- monitor agent health
- coordinate delegation
- escalate risky execution
- enforce policy-aware orchestration decisions

Supervisor must not become a second execution runtime.

## Multi-Agent Coordination Rules

- Every delegated unit of work must resolve to one or more `SkillRun`s.
- Delegation edges must preserve `correlation_id`.
- Parent agent and delegated agent identity must remain auditable.
- Multi-agent decomposition must not create shadow tasks outside canonical runtime records.

## API Surface

- `GET /api/v1/agents`
- `GET /api/v1/agents/{agent_id}`
- `POST /api/v1/agents/{agent_id}/invoke-skill`
- `POST /api/v1/agents/{agent_id}/delegate`
- `GET /api/v1/agents/{agent_id}/delegations`
- `GET /api/v1/supervisor/agents`
- `GET /api/v1/supervisor/status`

## Audit and Event Requirements

- `agent.delegation.requested.v1`
- `agent.delegation.accepted.v1`
- `agent.delegation.rejected.v1`
- `agent.skillrun.requested.v1`
- `supervisor.escalation.requested.v1`

Durable audit required for:
- delegation
- escalation
- agent-triggered governed execution

Durability rule:
- durable delegation/escalation write, audit write, and outbox insert must complete before publish.

Event compatibility note:
- Existing unversioned agent events may be mirrored during transition, but `.v1` contracts are the target state.

## PostgreSQL vs Redis vs EventStream

### PostgreSQL
- agent metadata
- delegation records
- escalation records

Delegation minimum durable fields:
- `source_agent_id`
- `target_agent_id`
- `skill_run_id`
- `status`
- `correlation_id`
- `requested_by`
- `created_at`

### Redis
- heartbeats
- transient coordination hints

### EventStream
- orchestration and delegation lifecycle events

## Legacy Compatibility

- Existing agent APIs may remain as compatibility surfaces.
- New agent features must target `SkillRun` orchestration, not embed new business logic directly in agent handlers.

## Done Criteria

- agents are documented as orchestration actors
- delegation path is explicitly SkillRun-based
- supervisor role is clarified as policy-aware coordination
- no new direct business-logic ownership is assigned to agents
