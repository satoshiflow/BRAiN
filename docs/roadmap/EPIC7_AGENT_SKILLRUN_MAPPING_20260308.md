# Epic 7 Agent-to-SkillRun Mapping (2026-03-08)

Status: Grounding and structure pass started  
Scope: Map current `agent_management` and `supervisor` runtime surfaces onto canonical `SkillRun` orchestration.

## Why this mapping exists

Epic 5 made `SkillRun` the canonical execution anchor.
Epic 6 made terminal outcomes measurable through evaluation and optimizer records.
Epic 7 now needs agent-facing orchestration surfaces to stop behaving like potential alternate runtimes.

## Current repo state

### `agent_management`

Current owned behavior in `backend/app/modules/agent_management/`:
- agent registration
- heartbeats and status transitions
- offline detection
- agent metadata CRUD
- agent statistics
- SSE event surface

Current gap:
- no first-class `SkillRun` invocation path
- capabilities are stored as agent metadata, not governed execution intent
- no durable delegation record linked to `SkillRun`

### `supervisor`

Current owned behavior in `backend/app/modules/supervisor/`:
- health endpoint
- status endpoint
- list-agents endpoint

Current gap:
- status is still mission-stubbed
- no aggregation over canonical `SkillRun`
- no policy-aware escalation surface tied to execution records

## Mapping principles

1. agents remain lifecycle/control-plane objects
2. `SkillRun` remains the only canonical execution record
3. supervisor becomes orchestration and escalation policy, not a second runtime
4. tenant, actor, correlation, and delegation edges must remain auditable

## Mapping table

| Existing surface | Current role | Target role after Epic 7 |
|---|---|---|
| `POST /api/agents/register` | register agent metadata | unchanged |
| `POST /api/agents/heartbeat` | update liveness/status | unchanged |
| `GET /api/agents` | read agent fleet state | unchanged |
| `POST /api/agents/{agent_id}/invoke-skill` | missing | create governed `SkillRun` on behalf of agent |
| `POST /api/agents/{agent_id}/delegate` | missing | create delegation record plus downstream `SkillRun` request |
| `GET /api/supervisor/status` | stubbed mission counters | aggregate `SkillRun` state + agent fleet status |
| `GET /api/supervisor/agents` | list agent state | keep read-only fleet view |
| `GET /api/supervisor/escalations` | missing | read policy/escalation records linked to runs |

## Required runtime linkages

### Agent -> SkillRun

For every agent-triggered execution request, persist at minimum:
- `skill_key`
- resolved `skill_version`
- `requested_by` = agent identity or authenticated principal
- `requested_by_type`
- `trigger_type = mission|api|retry` as applicable
- `mission_id` when orchestration is mission-bound
- `correlation_id`
- delegation metadata in audit/event trail

### Supervisor -> SkillRun

Supervisor read models should derive from:
- `SkillRun.state`
- `SkillRun.risk_tier`
- `SkillRun.policy_decision`
- evaluation non-compliance signals
- optimizer recommendation backlog for advisory follow-up

Supervisor should eventually expose:
- active governed execution count
- failed and non-compliant run counts
- waiting-approval queue depth
- agent-to-run correlation visibility

## Minimal implementation sequence

### Step 1
- add `agent invoke skill` service path that wraps `SkillEngineService.create_run`
- keep request actor derived from authenticated principal or bound agent identity

### Step 2
- add a small delegation record contract before any true multi-agent fan-out
- delegation must point to produced `skill_run_id`

### Step 3
- rework supervisor status to aggregate canonical `SkillRun` counts instead of mission stubs

### Step 4
- add escalation/read models linked to approval and policy outcomes

## Current implementation slice completed

Implemented now:
- `agent_management` can request canonical `SkillRun` creation through an agent-facing invoke path
- delegation now creates a durable `agent_delegations` record linked to `skill_run_id`
- supervisor runtime reads canonical `SkillRun` state for status projections

New runtime surfaces:
- `POST /api/agents/{agent_id}/invoke-skill`
- `POST /api/agents/{agent_id}/delegate`
- `GET /api/agents/{agent_id}/delegations`

## Next implementation slice

Recommended next slice after this pass:

1. add target-agent acknowledgement lifecycle for delegation records
   - `requested -> accepted|rejected -> completed`
2. add delegation-to-execution read model joins
   - agent can inspect downstream `SkillRun` terminal state without rebuilding hidden task graphs
3. add supervisor escalation view over:
   - `waiting_approval` runs
   - non-compliant evaluations
   - open optimizer recommendations linked to delegated execution
4. add durable audit bridge for agent invoke/delegate actions so governance ordering is explicit

## Key risks

- agent capability metadata can be mistaken for execution authorization; it is only affinity metadata
- supervisor can drift into a shadow runtime if it directly executes work instead of requesting `SkillRun`
- delegation without durable linkage will recreate hidden task graphs outside canonical execution history

## Done criteria for the first Epic 7 slice

- one agent-facing invocation path creates `SkillRun`
- one supervisor-facing status path reads from `SkillRun`
- no new direct business logic is added to agent or supervisor modules
- correlation and actor identity remain preserved across orchestration boundaries
