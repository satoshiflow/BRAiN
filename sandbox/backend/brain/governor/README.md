# Governor v1 - Agent Creation Governance (Phase 2a)

**Version:** 1.0.0
**Status:** Production-Ready
**Ruleset:** Phase 2a

---

## Overview

Governor v1 is the **formal decision engine** for agent creation in BRAiN. It makes deterministic, auditable decisions on whether to approve or reject agent creation requests based on **Policy Rules v1**.

> **No agent may be created without a formal Governor decision.**

---

## Architecture

```
Genesis Agent
    ↓
    → Governor.evaluate_creation(DecisionRequest)
    ↓
    [Policy Evaluation (Groups A-E)]
    ↓
    [Risk & Quarantine Computation]
    ↓
    [Constraint Application]
    ↓
    [Event Emission (dual-write)]
    ↓
    ← DecisionResult (approve/reject/approve_with_constraints)
```

---

## Key Features

✅ **Deterministic:** Same input → same output (pure functions, no ML/LLMs)
✅ **Auditable:** Complete audit trail (dual-write: Redis + Audit Log)
✅ **Charter-Strict:** No interpretation, mechanical rule evaluation only
✅ **Fail-Closed:** Event emission requires at least one write to succeed
✅ **Defense in Depth:** Validates kill switch, ethics flags, template integrity
✅ **DSGVO/EU AI Act Compliant:** Immutable ethics flags, human override always allowed

---

## Policy Rules v1

### Group A: Role & Authorization

| Rule | Description | Success Condition | Failure Code |
|------|-------------|-------------------|--------------|
| **A1** | Require SYSTEM_ADMIN role | `actor.role == "SYSTEM_ADMIN"` | `UNAUTHORIZED_ROLE` |
| **A2** | Kill switch check (Defense in Depth) | `killswitch_active == False` | `KILLSWITCH_ACTIVE` |

### Group B: Template Integrity

| Rule | Description | Success Condition | Failure Code |
|------|-------------|-------------------|--------------|
| **B1** | Template hash required | `template_hash.startswith("sha256:")` | `TEMPLATE_HASH_MISSING` |
| **B2** | Template in allowlist | `template_name in allowlist` | `TEMPLATE_NOT_IN_ALLOWLIST` |

### Group C: DNA Constraints

| Rule | Description | Success Condition | Failure Code |
|------|-------------|-------------------|--------------|
| **C1** | Ethics human_override immutable | `ethics_flags.human_override == "always_allowed"` | `CAPABILITY_ESCALATION_DENIED` |
| **C2** | Network access cap | `dna.network_access ≤ AgentType_cap` | `CAPABILITY_ESCALATION_DENIED` |
| **C3** | Autonomy level cap | `dna.autonomy_level ≤ AgentType_cap` | `CAPABILITY_ESCALATION_DENIED` |

### Group D: Budget & Population Limits

| Rule | Description | Success Condition | Failure Code |
|------|-------------|-------------------|--------------|
| **D1** | Creation cost affordable | `cost ≤ usable_budget` (with reserve protection) | `BUDGET_INSUFFICIENT` |
| **D2** | Population limit | `current_population < max_population[AgentType]` | `POPULATION_LIMIT_EXCEEDED` |

### Group E: Risk & Quarantine

| Rule | Description | Effect | Notes |
|------|-------------|--------|-------|
| **E1** | Critical agents quarantined | Sets `quarantine=True` for Genesis/Governor/Supervisor/Ligase/KARMA | Risk tier: CRITICAL |
| **E2** | Customizations increase risk | Elevates risk tier to `MEDIUM` if customizations present | Risk tier adjustment |
| **E3** | Capability escalation rejected | Rejects customizations to `capabilities.*`, `resource_limits.*`, `traits.autonomy_level`, `runtime.*` | `CAPABILITY_ESCALATION_DENIED` |

---

## Decision Flow

1. **Request Received:** Genesis calls `Governor.evaluate_creation(request)`
2. **Event: decision.requested**
3. **Evaluate Group A (Role & Auth):** If FAIL → REJECT
4. **Evaluate Group B (Template Integrity):** If FAIL → REJECT
5. **Evaluate Group C (DNA Constraints):** If FAIL → REJECT
6. **Evaluate Group D (Budget & Population):** If FAIL → REJECT
7. **Evaluate Group E (Risk & Quarantine):** Compute risk tier, quarantine status, check escalations
8. **Apply Constraints:** Get default constraints for AgentType (Phase 2a: no reductions yet)
9. **Event: decision.evaluated**
10. **Event: decision.approved** or **decision.rejected**
11. **Return DecisionResult**

---

## Usage

### Basic Usage (via Genesis Integration)

Governor v1 is automatically integrated into Genesis Agent:

```python
from backend.brain.agents.genesis_agent import GenesisAgent

# Genesis automatically uses Governor v1
genesis = GenesisAgent(
    registry=registry,
    redis_client=redis,
    audit_log=audit,
    budget=budget
)

# Agent creation is now governed
dna = await genesis.create_agent(
    request_id="req-123",
    template_name="worker_base",
    customizations={"metadata.name": "worker_01"}
)
# → Governor evaluates before creation
```

### Direct Usage (Advanced)

```python
from backend.brain.governor import (
    Governor,
    GovernorConfig,
    DecisionRequest,
    ActorContext,
    RequestContext
)

# Initialize Governor
governor = Governor(
    redis_client=redis,
    audit_log=audit,
    config=GovernorConfig(
        template_allowlist=["worker_base", "analyst_base"],
        reserve_ratio=0.2
    )
)

# Build request
request = DecisionRequest(
    request_id="req-123",
    actor=ActorContext(
        user_id="admin-001",
        role="SYSTEM_ADMIN",
        source="genesis_api"
    ),
    agent_dna=dna_dict,
    dna_hash="hash123",
    template_name="worker_base",
    template_hash="sha256:abc123",
    context=RequestContext(
        has_customizations=True,
        customization_fields=["metadata.name"]
    )
)

# Evaluate
result = await governor.evaluate_creation(request)

if result.approved:
    print(f"Approved: {result.decision_type}")
    print(f"Constraints: {result.constraints}")
else:
    print(f"Rejected: {result.reason_code} - {result.reason_detail}")
```

---

## Decision Types

| Decision Type | Description | Constraints |
|---------------|-------------|-------------|
| `APPROVE` | Approved with default constraints | Default constraints for AgentType |
| `APPROVE_WITH_CONSTRAINTS` | Approved with additional constraints | Default + customization reductions |
| `REJECT` | Rejected | None (no constraints on rejection) |

---

## Risk Tiers

| Risk Tier | Description | Quarantine | Examples |
|-----------|-------------|------------|----------|
| `LOW` | Standard agents, no customizations | No | Worker, Analyst (default) |
| `MEDIUM` | Agents with customizations | No | Worker with custom name |
| `HIGH` | Agents with elevated capabilities | TBD (Phase 3) | - |
| `CRITICAL` | System agents | **Yes** | Genesis, Governor, Supervisor, Ligase, KARMA |

---

## Constraints

### Default Constraints per AgentType

| AgentType | Credits/Mission | Daily Credits | LLM Calls/Day | Network Access | Max Parallel Tasks | Autonomy Cap |
|-----------|-----------------|---------------|---------------|----------------|-------------------|--------------|
| **Worker** | 100 | 1000 | 500 | restricted | 2 | 3 |
| **Analyst** | 150 | 1500 | 750 | restricted | 3 | 3 |
| **Builder** | 200 | 2000 | 1000 | restricted | 2 | 2 |
| **Memory** | 50 | 500 | 250 | none | 5 | 1 |
| **Supervisor** | 500 | 5000 | 2000 | full | 10 | 5 |
| **Ligase** | 300 | 3000 | 1500 | full | 20 | 4 |
| **Karma** | 400 | 4000 | 2000 | restricted | 5 | 5 |
| **Governor** | 600 | 6000 | 3000 | full | 10 | 5 |
| **Genesis** | 1000 | 10000 | 5000 | full | 5 | 5 |

### Constraint Categories

1. **Budget:** `max_credits_per_mission`, `max_daily_credits`, `max_llm_calls_per_day`
2. **Capabilities:** `tools_allowed`, `connectors_allowed`, `network_access`, `max_parallel_tasks`
3. **Runtime:** `allowed_models`, `max_tokens_cap`, `temperature_cap`
4. **Lifecycle:** `initial_status`, `requires_human_activation`
5. **Locks:** `locked_fields`, `no_escalation` (IMMUTABLE for Phase 2a)

---

## Events

All events are emitted via dual-write (Redis + Audit Log):

| Event Type | When | Payload |
|------------|------|---------|
| `governor.decision.requested` | Decision request received | `decision_id`, `template_name`, `actor_role` |
| `governor.decision.evaluated` | Rule evaluation complete | `decision_id`, `evaluation_duration_ms`, `evaluated_rules` |
| `governor.decision.approved` | Decision approved | `decision_id`, `decision_type`, `risk_tier`, `quarantine` |
| `governor.decision.rejected` | Decision rejected | `decision_id`, `reason_code`, `reason_detail`, `triggered_rules` |
| `governor.constraints.applied` | Constraints applied to agent | `decision_id`, `agent_id`, `constraints_summary` |

---

## Testing

### Run Unit Tests

```bash
cd /home/user/BRAiN/backend
pytest brain/governor/tests/test_policy_rules.py -v
```

**Coverage:**
- Group A: Role & Authorization (2 tests per rule)
- Group B: Template Integrity (3 tests per rule)
- Group C: DNA Constraints (3 tests per rule)
- Group D: Budget & Population (2 tests per rule)
- Group E: Risk & Quarantine (3 tests per rule)
- Determinism tests (3 tests)

### Run Integration Tests

```bash
pytest brain/governor/tests/test_integration.py -v
```

**Scenarios:**
- Approve path (default constraints)
- Approve path (with constraints)
- Reject path (unauthorized role)
- Reject path (capability escalation)
- Quarantine path (critical agent)
- GovernorApproval wrapper

---

## Configuration

### GovernorConfig

```python
GovernorConfig(
    policy_version="1.0.0",           # Policy version
    ruleset_version="2a",              # Ruleset version
    template_allowlist=[               # Allowed templates
        "worker_base",
        "analyst_base"
    ],
    reserve_ratio=0.2,                 # Budget reserve (20%)
    max_population={                   # Population limits
        AgentType.GENESIS: 1,
        AgentType.WORKER: 50
    }
)
```

---

## Compliance

### DSGVO (EU GDPR)

✅ **Art. 22 (Human Oversight):** `ethics_flags.human_override` is IMMUTABLE and always `"always_allowed"`
✅ **Art. 25 (Privacy by Design):** Constraints enforce data minimization and access controls

### EU AI Act

✅ **Art. 5 (Prohibited Practices):** Governor checks for prohibited uses (social scoring, biometric categorization)
✅ **Art. 16 (Human Oversight):** CRITICAL agents require human activation (`requires_human_activation=True`)

---

## Limitations (Phase 2a)

❌ **No ML/LLMs:** Pure rule-based decisions (mechanical only)
❌ **No Runtime Governance:** Governor only evaluates at creation time (no execution governance)
❌ **No Constraint Reductions:** Phase 2a uses defaults only (reductions coming in Phase 2b)
❌ **No Shadow Evaluation:** No manifest A/B testing yet

---

## Roadmap

### Phase 2b (Planned)

- ⏳ Constraint reductions based on customizations
- ⏳ Shadow evaluation (manifest A/B testing)
- ⏳ Manifest-driven rules (replace hard-coded rules)

### Phase 3 (Planned)

- ⏳ Runtime governance (budget enforcement during execution)
- ⏳ WebDev integration
- ⏳ ControlDeck UI for Governor decisions

---

## Troubleshooting

### Issue: "Governor v1 not available, using stub"

**Cause:** Import error (missing dependencies)
**Fix:** Ensure `backend/brain/governor/` is properly installed

### Issue: "Decision rejected: UNAUTHORIZED_ROLE"

**Cause:** Actor role is not `SYSTEM_ADMIN`
**Fix:** Only SYSTEM_ADMIN can create agents

### Issue: "Decision rejected: CAPABILITY_ESCALATION_DENIED"

**Cause:** Customization attempts to escalate capabilities (Phase 2a: forbidden)
**Fix:** Remove customizations to `capabilities.*`, `resource_limits.*`, `traits.autonomy_level`, `runtime.*`

### Issue: "Decision rejected: BUDGET_INSUFFICIENT"

**Cause:** Insufficient budget (with reserve protection)
**Fix:** Increase available credits or reduce reserve ratio

---

## Definition of Done (Phase 2a)

✅ Governor-Stub vollständig entfernt
✅ Governor v1 aktiv & deterministisch
✅ Constraints Schema + Defaults vorhanden
✅ Audit-Events vollständig (dual-write)
✅ Tests grün (≥95% coverage)
✅ README vorhanden (Policy Rules v1)

**Phase 2a ist abgeschlossen.**

---

## Contact & Support

**Maintainer:** Governor v1 System
**Version:** 1.0.0
**Last Updated:** 2026-01-02

**Issues:** Please report bugs or feature requests via GitHub Issues.
