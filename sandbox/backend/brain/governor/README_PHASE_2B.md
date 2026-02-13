# Governor v1 Phase 2b: Constraint Reductions + Manifest-Driven Rules

**Version:** 2b.1
**Status:** ✅ Complete
**Created:** 2026-01-02
**Author:** Governor v1 System

---

## Overview

Phase 2b extends Governor v1 with **declarative, manifest-driven governance** that allows adaptive constraint reductions based on runtime conditions.

### Key Features

- **📋 Manifest-Driven Governance:** YAML-based policy configuration (no code changes required)
- **📉 Constraint Reductions:** Monotonic reductions based on conditions (customizations, risk, environment, population)
- **🔒 Monotonicity Guarantee:** Reductions can only reduce constraints, never expand
- **⚡ Deterministic:** Same input → same output (no ML, no LLMs, no interpretation)
- **📊 Complete Audit Trail:** New events for reductions and manifest application
- **🔐 Locked Fields:** Immutable safety-critical fields enforced by manifest

### Compliance

- **DSGVO Art. 25:** Privacy by Design (data minimization, least privilege)
- **EU AI Act Art. 16:** Human Oversight (immutable ethics flags)
- **EU AI Act Art. 5:** Prohibited Practices (enforced via locked fields)

---

## Architecture

### Component Overview

```
backend/brain/governor/
├── manifests/                    # Manifest System
│   ├── schema.py                 # Pydantic schema for manifests
│   ├── loader.py                 # YAML loading + validation
│   ├── defaults.yaml             # Default governance manifest
│   └── examples/
│       └── strict.yaml           # Example: High-security variant
│
├── reductions/                   # Reduction Engine
│   ├── reducer.py                # ConstraintReducer (applies reductions)
│   ├── rules.py                  # Condition-based rule evaluation
│   └── __init__.py               # Exports
│
├── governor.py                   # Governor v1 (Phase 2a + 2b)
├── events.py                     # Events (Phase 2a + 2b)
│
└── tests/
    ├── test_reduction_monotonicity.py  # Unit tests (26 tests)
    └── test_phase_2b_integration.py    # Integration tests (4 tests)
```

### Data Flow

```
1. Genesis Agent → DecisionRequest
2. Governor loads Governance Manifest (YAML)
3. Governor evaluates Policy Rules (Groups A-E)
4. Governor determines applicable reductions (via reduction rules)
5. Reduction Engine applies reductions incrementally (with monotonicity validation)
6. Governor emits events (constraints.reduced, manifest.applied)
7. Governor returns DecisionResult (with reduced constraints)
```

---

## Governance Manifest Structure

### Manifest Schema

```yaml
# Governance Manifest (YAML)

manifest_version: 1
policy_version: "2b.1"
name: "default"
description: "Default governance manifest"

# ============================================================================
# Applicability Rules
# ============================================================================
applies_to:
  agent_types: null              # null = all types
  template_names: null           # null = all templates
  has_customizations: null       # null = applies to both

# ============================================================================
# Constraint Reductions
# ============================================================================
reductions:
  on_customization:              # When agent has customizations
    max_llm_calls_per_day: "-30%"
    parallelism: "-50%"

  on_high_risk:                  # When agent is HIGH/CRITICAL risk
    network_access: "disable"
    max_credits_per_mission: "100"

  on_production:                 # When agent is deployed to production
    max_credits_per_mission: "500"
    max_llm_tokens_per_call: "2000"

  on_population_pressure:        # When population >80% of limit
    max_lifetime_seconds: "1800"

# ============================================================================
# Risk Tier Overrides
# ============================================================================
risk_overrides:
  if_customizations: "MEDIUM"              # Customizations → MEDIUM risk
  if_template_not_in_allowlist: "HIGH"     # Unknown template → HIGH risk
  if_capability_escalation: "CRITICAL"     # Escalation → CRITICAL risk

# ============================================================================
# Locked Fields
# ============================================================================
locks:
  locked_fields:
    - "ethics_flags.human_override"      # MUST be 'always_allowed'
    - "capabilities.can_create_agents"   # Only Genesis can create agents
    - "capabilities.can_modify_governor" # Prevent governance tampering
  reason: "Safety-critical invariants (EU AI Act Art. 16)"
```

### Reduction Syntax

| Type | Example | Meaning |
|------|---------|---------|
| **Percentage** | `"-30%"` | Reduce by 30% (multiplicative) |
| **Absolute** | `"100"` | Set to 100 (only if less than current) |
| **Keyword** | `"disable"` | Disable network access (→ `none`) |
| **Keyword** | `"single"` | Force single-threaded execution (→ `1`) |

### Reduction Sections

| Section | Condition | Priority |
|---------|-----------|----------|
| `on_customization` | Agent has DNA customizations | 1 (first) |
| `on_high_risk` | Agent is HIGH/CRITICAL risk | 2 |
| `on_production` | Agent deployed to production | 3 |
| `on_population_pressure` | Population >80% of limit | 4 (last) |

**Note:** Reductions are applied in priority order. Later reductions may further reduce already-reduced constraints.

---

## Reduction Engine

### ConstraintReducer

The `ConstraintReducer` applies manifest-defined reductions to base constraints with **monotonicity validation**.

**Key Methods:**

```python
from backend.brain.governor.reductions.reducer import ConstraintReducer
from backend.brain.governor.manifests.schema import ReductionSpec

reducer = ConstraintReducer()

# Apply reduction
spec = ReductionSpec(max_llm_calls_per_day="-30%", parallelism="-50%")
reduced = reducer.reduce(base_constraints, spec)
```

**Guarantees:**

1. **Monotonicity:** Reductions can only reduce, never expand
2. **Determinism:** Same input → same output
3. **Validation:** Violations raise `MonotonicityViolationError`
4. **Purity:** No side effects, no I/O, no randomness

### Reduction Rules

The `ReductionContext` aggregates all information needed to determine which reduction rules should be applied.

**Example:**

```python
from backend.brain.governor.reductions.rules import (
    ReductionContext,
    get_applicable_reductions,
)

# Build context
context = ReductionContext(
    has_customizations=True,
    customization_fields=["metadata.name"],
    risk_tier=RiskTier.MEDIUM,
    agent_type=AgentType.WORKER,
    agent_dna=dna_dict,
    current_population=10,
    max_population={AgentType.WORKER: 50},
    environment="production"
)

# Determine applicable reductions
applicable = get_applicable_reductions(context, manifest.reductions)

# Example result:
# [
#     ("on_customization", ReductionSpec(...)),
#     ("on_production", ReductionSpec(...))
# ]
```

---

## Integration with Governor v1

### Governor Initialization

```python
from backend.brain.governor import Governor, GovernorConfig
from backend.brain.governor.manifests.loader import get_manifest_loader

# Load manifest
loader = get_manifest_loader()
manifest = loader.get_default_manifest()

# Create Governor with manifest
governor = Governor(
    redis_client=redis,
    audit_log=audit,
    config=GovernorConfig(),
    manifest=manifest  # Phase 2b
)
```

### Decision Flow (Phase 2b)

```python
# Create request
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

# Evaluate (Phase 2b flow)
result = await governor.evaluate_creation(request)

# Result includes reduced constraints
if result.approved:
    print(f"Approved with constraints: {result.constraints}")
    # constraints['budget']['max_llm_calls_per_day'] == 700 (reduced from 1000)
    # constraints['runtime']['parallelism'] == 5 (reduced from 10)
```

### Event Emission (Phase 2b)

New events in Phase 2b:

1. **`governor.constraints.reduced`**
   ```json
   {
     "event_type": "governor.constraints.reduced",
     "timestamp": "2026-01-02T12:00:00.000000Z",
     "payload": {
       "decision_id": "dec_abc123",
       "applied_reductions": ["on_customization", "on_high_risk"],
       "reduction_summary": {
         "max_llm_calls_per_day": {"before": 1000, "after": 350},
         "network_access": {"before": "restricted", "after": "none"}
       },
       "base_constraints_hash": "sha256:abc123",
       "reduced_constraints_hash": "sha256:def456"
     }
   }
   ```

2. **`governor.manifest.applied`**
   ```json
   {
     "event_type": "governor.manifest.applied",
     "timestamp": "2026-01-02T12:00:00.000000Z",
     "payload": {
       "decision_id": "dec_abc123",
       "manifest_name": "default",
       "manifest_version": "1",
       "policy_version": "2b.1",
       "applicable_sections": ["on_customization"],
       "risk_overrides": {"if_customizations": "MEDIUM"},
       "locked_fields": ["ethics_flags.human_override"]
     }
   }
   ```

---

## Usage Examples

### Example 1: Approve with Customization Reductions

```python
# Request has customizations
request = DecisionRequest(
    ...,
    context=RequestContext(
        has_customizations=True,
        customization_fields=["metadata.name"]
    )
)

result = await governor.evaluate_creation(request)

# Outcome:
# - Decision: APPROVE_WITH_CONSTRAINTS
# - Risk Tier: MEDIUM (manifest override)
# - Reductions Applied: ["on_customization"]
# - max_llm_calls_per_day: 1000 → 700 (-30%)
# - parallelism: 10 → 5 (-50%)
```

### Example 2: Multiple Reductions (Customizations + High Risk)

```python
# Request has customizations AND high risk conditions
# Both on_customization AND on_high_risk reductions apply

result = await governor.evaluate_creation(request)

# Outcome:
# - Decision: APPROVE_WITH_CONSTRAINTS
# - Risk Tier: HIGH
# - Reductions Applied: ["on_customization", "on_high_risk"]
# - max_llm_calls_per_day:
#     Base: 1000
#     After on_customization (-30%): 700
#     After on_high_risk (-50% of 700): 350
# - network_access: restricted → none (disabled)
```

### Example 3: No Reductions (No Customizations)

```python
# Request has NO customizations
request = DecisionRequest(
    ...,
    context=RequestContext(
        has_customizations=False,
        customization_fields=[]
    )
)

result = await governor.evaluate_creation(request)

# Outcome:
# - Decision: APPROVE (not APPROVE_WITH_CONSTRAINTS)
# - Risk Tier: LOW
# - Reductions Applied: [] (none)
# - Constraints: Base defaults (unreduced)
```

---

## Testing

### Unit Tests (test_reduction_monotonicity.py)

**Coverage:** 26 tests

- ✅ Percentage reductions (`"-30%"`, `"-50%"`)
- ✅ Absolute reductions (`"100"`, `"50"`)
- ✅ Keyword reductions (`"disable"`, `"single"`)
- ✅ Network access hierarchy (`full → restricted → none`)
- ✅ Incremental reductions (cumulative effects)
- ✅ Monotonicity validation (reductions only, no expansions)
- ✅ Edge cases (zero, same value, empty spec, rounding)
- ✅ Determinism (same input → same output)

**Run Tests:**
```bash
pytest backend/brain/governor/tests/test_reduction_monotonicity.py -v
```

### Integration Tests (test_phase_2b_integration.py)

**Coverage:** 4 tests

- ✅ Approve with customization reductions
- ✅ Multiple reduction sections (incremental)
- ✅ No reductions when no customizations
- ✅ Rejection path (no reductions on reject)

**Run Tests:**
```bash
pytest backend/brain/governor/tests/test_phase_2b_integration.py -v
```

---

## Monotonicity Guarantees

### What is Monotonicity?

**Monotonicity:** Reductions can only **reduce** constraints, never **expand** them.

### Why Monotonicity?

1. **Security:** Prevents privilege escalation via manifest manipulation
2. **Predictability:** Constraints can only become more restrictive, never less
3. **Auditability:** Clear proof that governance never weakens constraints

### Enforcement

The `ConstraintReducer` validates monotonicity **before** returning reduced constraints:

```python
def _validate_monotonicity(
    self,
    base: EffectiveConstraints,
    reduced: EffectiveConstraints
) -> None:
    """Validate that all reductions are monotonic."""
    violations = []

    # Check budget constraints
    if reduced.budget.max_credits_per_mission > base.budget.max_credits_per_mission:
        violations.append("max_credits_per_mission expanded")

    # Check capability constraints
    if reduced_network_level > base_network_level:
        violations.append("network_access expanded")

    # ... (check all fields)

    if violations:
        raise MonotonicityViolationError(
            f"Monotonicity violations detected:\n" + "\n".join(violations)
        )
```

---

## Locked Fields

### Purpose

Locked fields are **immutable** safety-critical fields that CANNOT be modified, even by SYSTEM_ADMIN.

### Example

```yaml
locks:
  locked_fields:
    - "ethics_flags.human_override"      # MUST be 'always_allowed'
    - "capabilities.can_create_agents"   # Only Genesis can create agents
  reason: "EU AI Act Art. 16 (Human Oversight)"
```

### Enforcement

Locked fields are checked **after** reductions are applied. Violations result in immediate rejection.

---

## Future Enhancements (Phase 2c+)

Potential future additions:

1. **Applies-To Filters:**
   - Manifest applicability based on `agent_types`, `template_names`, `has_customizations`
   - Example: "Apply strict manifest only to Worker agents with customizations"

2. **More Reduction Conditions:**
   - `on_budget_pressure`: When budget <20% remaining
   - `on_time_of_day`: Different constraints for night vs. day
   - `on_user_tier`: Different constraints per user tier

3. **Risk Overrides:**
   - `if_template_not_in_allowlist`: Elevate risk for unknown templates
   - `if_capability_escalation`: Detect and elevate risk for escalations

4. **Manifest Versioning:**
   - A/B testing of governance policies
   - Gradual rollout of new manifests
   - Manifest history and rollback

5. **ControlDeck UI:**
   - Visual manifest editor
   - Live reduction preview
   - Manifest validation and testing

---

## Migration from Phase 2a

### Backward Compatibility

Phase 2b is **100% backward compatible** with Phase 2a:

- **Governor v1 API:** Unchanged
- **Genesis Integration:** Unchanged
- **Policy Rules:** Unchanged (Groups A-E still evaluated)
- **Events:** Phase 2a events still emitted

### New Capabilities

Phase 2b **extends** Governor v1 with:

- **Manifest-driven governance** (optional, defaults to base constraints if manifest missing)
- **Constraint reductions** (only applied if manifest defines reductions)
- **New events** (`constraints.reduced`, `manifest.applied`)

### Migration Steps

1. **No code changes required** (manifest system is automatically enabled)
2. **Default manifest** is loaded on Governor initialization
3. **Custom manifests** can be provided via `manifest` parameter:

```python
# Phase 2a (still works)
governor = Governor(
    redis_client=redis,
    audit_log=audit
)

# Phase 2b (with custom manifest)
custom_manifest = loader.load_from_file("manifests/strict.yaml")
governor = Governor(
    redis_client=redis,
    audit_log=audit,
    manifest=custom_manifest
)
```

---

## Summary

Phase 2b delivers **declarative, manifest-driven governance** that enables adaptive constraint reductions with strong monotonicity guarantees.

### Key Achievements

| Feature | Status | Details |
|---------|--------|---------|
| Manifest Schema | ✅ Complete | Pydantic validation, YAML support |
| Manifest Loader | ✅ Complete | Load from file/dict, caching, singleton |
| Default Manifest | ✅ Complete | Baseline governance rules |
| Reduction Engine | ✅ Complete | Monotonicity validation, pure functions |
| Reduction Rules | ✅ Complete | Condition-based, priority-ordered |
| Governor Integration | ✅ Complete | Seamless Phase 2a + 2b |
| Events | ✅ Complete | constraints.reduced, manifest.applied |
| Unit Tests | ✅ Complete | 26 tests, monotonicity coverage |
| Integration Tests | ✅ Complete | 4 tests, end-to-end flow |
| Documentation | ✅ Complete | This README |

### Next Steps

- **Phase 2c:** Manifest versioning, A/B testing, gradual rollout
- **Phase 3:** ControlDeck UI for manifest editing and testing
- **Phase 4:** Advanced reduction conditions (budget pressure, time-based, user tiers)

---

**Version:** 2b.1
**Status:** ✅ Production-Ready
**Date:** 2026-01-02
**License:** Internal - BRAiN Project
