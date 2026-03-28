# DESIGN.md

Canonical design brief for evolving BRAiN into a BRAiN-first, governance-first,
modular, and highly autonomous work system.

## 1. Purpose of this document

This document consolidates the active architectural direction for identity,
purpose, governance, routing, autonomy, human control, and staged
implementation.

It is the design-level source of truth for:
- BRAiN's canonical identity and operating purpose
- non-negotiable governance constraints
- the target decision flow for Purpose and Routing
- the integration boundary between BRAiN, AXE, ControlDeck, OpenCode, and
  existing runtime modules
- the phased implementation plan to be executed later by coding agents

This document does not replace module-specific runtime specs. It constrains how
new specs and implementations must fit together.

## 2. Canonical source precedence

When sources conflict, use this order:
1. `AGENTS.md`
2. `DESIGN.md`
3. `docs/governance/BRAIN_CONTROLLED_COLLABORATION.md`
4. `docs/specs/constitution_gate.md`
5. `docs/specs/policy_decision.md`
6. `docs/specs/approval_gate.md`
7. `docs/specs/opencode_permanent_dev_worker.md`
8. `docs/specs/runtime_harmonization.md`
9. `docs/specs/domain_agent_contract.md`
10. `docs/specs/mission_deliberation_insight_evolution.md`
11. `CLAUDE.md`

The following are informative but not dominant when they conflict with the
sources above:
- `README.md`
- `docs/governance/CONSTITUTIONAL_AGENTS.md`

## 3. Canonical identity

BRAiN is the sovereign, governance-guided control plane for meaningful,
traceable, and learning-capable execution.

BRAiN is not a loose collection of tools or agent prompts. It is the system
that interprets intent, applies policy and purpose, selects the appropriate
governed execution path, verifies outcomes, and accumulates learning without
losing sovereignty.

## 4. Operational purpose

BRAiN turns intent into safe, auditable, verified, and learning-producing
action.

In practice, this means:
- interpreting human, agent, or mission intent
- deciding what is meaningful and allowed
- routing work through domain-aware and governance-aware paths
- executing through canonical runtime objects
- preserving evidence, reviewability, and durable learning

## 5. Non-negotiable constraints

- `SkillRun` remains the canonical execution record.
- Governance always precedes sensitive execution.
- EventStream remains the canonical event backbone.
- AXE is the human-to-BRAiN control interface for observation, intervention,
  approval, and override when needed.
- Human involvement is optional by default, not mandatory by default.
- BRAiN operates in `brain_first` mode unless policy requires escalation.
- OpenCode is a bounded execution plane under BRAiN contracts, not a second
  sovereign brain.
- No new parallel runtime, governance system, or learning system may be
  created.
- New upper-layer routing must integrate into existing `missions -> planning ->
  domain_agents -> skill_engine -> task_queue/opencode` paths.
- Self-improvement, routing optimization, and workflow evolution must be tested
  in sandbox or replay-first workflows before production promotion.
- Sensitive and mutating operations require policy, approval when applicable,
  durable audit, and durable state progression before asynchronous publication.

## 6. BRAiN-first operating mode

The default operating model is:
- `brain_first`: BRAiN decides and acts autonomously within active governance
- `human_optional`: humans may observe, review, simulate, or override when
  allowed
- `human_required`: humans are required only for policy-defined sensitive,
  breakglass, or promotion-critical steps

This means BRAiN should not be designed as a permanently human-steered system.
Human control is a governed option, not the default execution loop.

## 7. Human surfaces

### AXE

AXE is the canonical human control surface for:
- observation
- explanation
- approval when required by policy
- override when explicitly allowed
- intervention during escalations or breakglass conditions

AXE is not the default executor for normal BRAiN decisions.

### ControlDeck

ControlDeck is the canonical administrative and governance surface for:
- configuration
- policy and governance management
- routing and worker oversight
- validation and promotion visibility
- system-wide operational settings

ControlDeck is where governed profiles and policies are edited. AXE is where a
human supervises and intervenes when needed.

## 8. Existing canonical architecture to preserve

The current canonical execution shape remains:

`Mission -> SkillRun -> TaskLease`

Where:
- `Mission` carries higher-level intent or envelope context
- `SkillRun` owns exact governed execution
- `TaskLease` owns subordinate worker dispatch only

Existing architecture that must be reused:
- `backend/app/modules/domain_agents/` as the upper routing and review spine
- `backend/app/modules/skill_engine/` as the canonical execution owner
- `backend/app/modules/policy/` and `backend/app/modules/supervisor/` as the
  governance and escalation surfaces
- `backend/app/modules/provider_bindings/` as lower provider selection
- `backend/app/modules/experience_layer/`,
  `backend/app/modules/insight_layer/`,
  `backend/app/modules/consolidation_layer/`, and
  `backend/app/modules/evolution_control/` as the learning and evolution path

## 9. Minimal new canonical artifacts

The design introduces only the minimum additional contracts needed to make
Purpose and Routing explicit.

### 9.1 Identity and purpose

- `CanonicalIdentityContract`
- `PurposeProfile`
- `GovernanceRuleSet`
- `DecisionContext`
- `PurposeEvaluation`

### 9.2 Routing

- `TaskProfile`
- `WorkerProfileProjection`
- `RoutingPolicy`
- `RoutingDecision`
- `RoutingMemoryProjection`

### 9.3 Integration

- `AttachmentFlowSpec`
- `SandboxValidationSpec`

These artifacts must be layered onto the existing system, not introduced as a
new runtime stack.

## 10. Target decision flow

The target governed flow is:

`Intent -> DecisionContext -> PurposeEvaluation -> TaskProfile -> DomainResolution -> RoutingDecision -> SkillRun -> TaskLease/JobContract -> Evaluation -> Learning`

Interpretation:
- `DecisionContext` normalizes the decision-relevant context
- `PurposeEvaluation` determines whether and how BRAiN should act
- `TaskProfile` expresses the work in routing-friendly terms
- `DomainResolution` remains the domain-aware orchestration spine
- `RoutingDecision` selects the governed worker/strategy before execution
- `SkillRun` remains the canonical runtime object
- `TaskLease` or OpenCode job contracts remain subordinate execution artifacts
- evaluation and learning remain downstream of execution

## 11. Loops

### Mission loop

`Intent -> DecisionContext -> PurposeEvaluation -> TaskProfile -> DomainResolution`

### Worker loop

`RoutingDecision -> SkillRun -> TaskLease/JobContract -> Evaluation`

### Learning loop

`Experience -> Insight -> Pattern -> Evolution`

`RoutingMemoryProjection` must feed this existing learning loop rather than
forming an isolated optimization system.

## 12. Editability and control model

### Read-only or tightly controlled

- `CanonicalIdentityContract`
- `RoutingDecision`
- raw `RoutingMemoryProjection` signals
- structural `AttachmentFlowSpec`

### Governed editable

- `PurposeProfile`
- `GovernanceRuleSet`
- `RoutingPolicy`
- worker admission and governance flags

### Operationally editable

- `TaskProfile` templates
- safe thresholds and low-risk optimization defaults
- sandbox experiment settings

### Override-only

- individual runtime outcomes through AXE when policy allows

## 13. Design rules for implementation

- Prefer reuse over invention.
- Add new contracts before adding new runtime code.
- Keep one writer per implementation surface.
- Route new upper-level autonomy through `domain_agents`, not through a new
  orchestration layer.
- Keep `SkillRun` as the single canonical execution write boundary.
- Keep provider selection below upper routing.
- Keep learning promotion behind sandbox-first validation.
- Preserve tenant, correlation, and causation continuity across every bridge.

## 14. Detailed implementation plan

This plan is intentionally small-grained so it can be executed quickly with
parallel subagents later.

### Phase 0 - Contract lock

Goal: lock vocabulary, boundaries, and invariants before runtime changes.

Sprint 0.1
- consolidate source precedence and dominance rules
- mark outdated sources as non-canonical where applicable
- confirm `brain_first` as the default operating mode

Sprint 0.2
- define the minimal field models for:
  - `PurposeProfile`
  - `DecisionContext`
  - `PurposeEvaluation`
  - `TaskProfile`
  - `WorkerProfileProjection`
  - `RoutingPolicy`
  - `RoutingDecision`
  - `RoutingMemoryProjection`

Sprint 0.3
- freeze invariants:
  - `SkillRun` canonical execution
  - governance before sensitive execution
  - no parallel runtime
  - sandbox-first self-improvement

### Phase 1 - Purpose layer

Goal: create a structured purpose layer without changing runtime ownership.

Sprint 1.1
- define `CanonicalIdentityContract` and `PurposeProfile` spec shapes
- define `DecisionContext` input semantics

Sprint 1.2
- define `PurposeEvaluation` outcomes:
  - `accept`
  - `reject`
  - `modified_accept`

Sprint 1.3
- define where purpose resolution attaches above `domain_agents`
- document which fields are runtime-derived versus policy-defined

### Phase 2 - Routing layer

Goal: introduce capability-based worker routing above execution.

Sprint 2.1
- define `TaskProfile` from existing skill/capability constraints
- define `WorkerProfileProjection` from existing worker/provider/adapter facts

Sprint 2.2
- define `RoutingPolicy` with:
  - hard constraints
  - soft preferences
  - scoring weights
  - fallback strategies

Sprint 2.3
- define `RoutingDecision` as a lightweight persisted decision artifact with a
  `SkillRun` reference model

### Phase 3 - Governance integration

Goal: ensure purpose and routing never bypass policy, approval, or audit.

Sprint 3.1
- map `PurposeEvaluation` and `RoutingDecision` to existing policy and approval
  semantics

Sprint 3.2
- define escalation semantics:
  - `brain_first`
  - `human_optional`
  - `human_required`

Sprint 3.3
- define audit and event requirements for upper routing decisions

### Phase 4 - Execution bridge

Goal: attach the new design to existing runtime modules.

Sprint 4.1
- connect `DecisionContext` and `PurposeEvaluation` above
  `backend/app/modules/domain_agents/`

Sprint 4.2
- connect `RoutingDecision` to `SkillRun` creation without changing `SkillRun`
  ownership

Sprint 4.3
- preserve lower provider routing through `provider_bindings`
- preserve subordinate dispatch through `task_queue` and OpenCode contracts

### Phase 5 - Learning and evolution

Goal: feed routing quality into existing learning paths.

Sprint 5.1
- define `RoutingMemoryProjection` from `Experience`, `Insight`, `Pattern`, and
  evaluation outputs

Sprint 5.2
- define routing lesson extraction and replay-based comparison

Sprint 5.3
- define promotion rules for routing changes without direct live self-tuning

### Phase 6 - UI and control surfaces

Goal: expose the right artifacts in the right human surfaces.

Sprint 6.1
- expose governed-editable artifacts in ControlDeck
- expose observation, explanation, intervention, and approvals in AXE

Sprint 6.2
- define read-only, editable, override-only, and promotion-only views

Sprint 6.3
- define simulation and sandbox validation flows for routing and purpose changes

### Phase 7 - Verification and rollout

Goal: validate the architecture before production cutover.

Sprint 7.1
- add targeted tests for purpose, routing, governance, and execution bridge

Sprint 7.2
- run replay and sandbox validation for routing/purpose changes

Sprint 7.3
- run targeted backend verification plus RC gate
- record local validation evidence and rollout notes

## 15. Parallel workstreams for later execution

These streams may run in parallel once Phase 0 is locked:

- `WS1 Contracts and docs`
- `WS2 Identity and purpose contracts`
- `WS3 Domain routing core`
- `WS4 Governance integration`
- `WS5 Mission/planning/execution bridge`
- `WS6 Learning and evolution integration`
- `WS7 UI/control surfaces`
- `WS8 Verification and hardening`

Hard rule: contracts stabilize before public runtime/API changes.

## 16. Merge checkpoints

- `CP1` contract lock complete
- `CP2` purpose layer stable
- `CP3` routing spine stable in `domain_agents`
- `CP4` governance gates verified
- `CP5` all new flows terminate in `SkillRun`
- `CP6` learning hooks defined
- `CP7` sandbox validation and promotion rules defined
- `CP8` targeted tests and RC gate passing

## 17. Out of scope for this design step

- implementing the runtime changes themselves
- creating a second orchestration engine
- replacing `SkillRun`, `ProviderBinding`, or the existing learning path
- making humans mandatory for standard BRAiN operation

## 18. Intended next executor

This design is intended to be implemented in later phases by coding-focused
agents such as GPT Codex, using this document together with `AGENTS.md` and the
dominant governance/runtime specs listed above.
