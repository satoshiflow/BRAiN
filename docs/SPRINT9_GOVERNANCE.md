# Sprint 9-A: Policy & Budget Governor

**Version:** 1.0.0
**Sprint:** Sprint 9-A
**Status:** ✅ Complete
**Author:** BRAiN Development Team

---

## Overview

The **Policy & Budget Governor** is a critical component that enforces execution policies and budget constraints across all pipeline runs in BRAiN. It prevents cost explosion, uncontrolled resource usage, and ensures compliance with governance rules.

**Core Principle:** Fail-closed everywhere. Invalid state → error, not degraded behavior.

---

## Key Features

### 1. Execution Budgets

Every pipeline run can have configurable budget limits:

```python
ExecutionBudget(
    max_steps=50,              # Maximum number of nodes to execute
    max_duration_seconds=300,  # Maximum execution time (5 minutes)
    max_external_calls=10,     # Maximum external API calls
    max_cost_usd=100.0,        # Optional cost limit
)
```

### 2. Limit Types

Each budget constraint can have different enforcement levels:

- **HARD** (`BudgetLimitType.HARD`): Immediate failure when exceeded
- **SOFT** (`BudgetLimitType.SOFT`): Trigger degradation mode (skip non-critical nodes)
- **WARN** (`BudgetLimitType.WARN`): Log warning only, continue execution

### 3. Approval Gates

Critical operations can require manual approval before execution:

```python
ExecutionPolicy(
    policy_id="prod_policy",
    policy_name="Production Policy",
    budget=budget,
    require_approval_for_types=["dns", "deploy", "odoo_module"],
    require_approval_for_nodes=["prod_deployment"],
)
```

### 4. Soft Degradation

When approaching budget limits (80% threshold), the governor can automatically skip non-critical nodes:

```python
ExecutionPolicy(
    ...
    allow_soft_degradation=True,
    skip_on_soft_limit=["webgenesis", "odoo_module"],
    critical_nodes=["dns", "deploy"],  # Never skip these
)
```

---

## Architecture

### Components

```
┌─────────────────────────────────────┐
│     ExecutionGraph                  │
│  (Pipeline Orchestrator)            │
└──────────────┬──────────────────────┘
               │
               ├─── check_node_execution()
               ▼
┌─────────────────────────────────────┐
│     ExecutionGovernor               │
│  (Budget & Policy Enforcement)      │
└──────────────┬──────────────────────┘
               │
               ├─── GovernorDecision
               │    - ALLOW
               │    - DENY
               │    - REQUIRE_APPROVAL
               │    - DEGRADE
               ▼
┌─────────────────────────────────────┐
│     Node Execution                  │
│  (Actual Work)                      │
└─────────────────────────────────────┘
```

### Decision Flow

```
Start Execution
     │
     ▼
┌──────────────────────┐
│ Start Governor       │
│ (Record start time)  │
└──────────────────────┘
     │
     ▼
For Each Node:
     │
     ├─── Check Budget Limits
     │    ├─── Steps exceeded? → HARD: FAIL / SOFT: DEGRADE / WARN: LOG
     │    ├─── Duration exceeded? → HARD: FAIL / SOFT: DEGRADE / WARN: LOG
     │    └─── External calls exceeded? → HARD: FAIL / SOFT: DEGRADE / WARN: LOG
     │
     ├─── Check Approval Gates
     │    └─── Requires approval? → BLOCK (wait for approval)
     │
     ├─── Check Soft Degradation
     │    └─── At 80% limit + non-critical? → DEGRADE (skip node)
     │
     └─── ALLOW Execution
          │
          ▼
     Execute Node
          │
          ▼
     Record Execution
     (steps++, duration+=Δt, external_calls+=N)
```

---

## API Integration

### Example: Create Graph with Governor

```python
from backend.app.modules.autonomous_pipeline.governor import ExecutionGovernor
from backend.app.modules.autonomous_pipeline.governor_schemas import (
    ExecutionBudget,
    ExecutionPolicy,
)
from backend.app.modules.autonomous_pipeline.execution_graph import create_execution_graph

# Define budget
budget = ExecutionBudget(
    max_steps=50,
    max_duration_seconds=300.0,
    max_external_calls=10,
)

# Define policy
policy = ExecutionPolicy(
    policy_id="my_policy",
    policy_name="My Policy",
    budget=budget,
    require_approval_for_types=["dns"],
    allow_soft_degradation=True,
)

# Create governor
governor = ExecutionGovernor(policy)

# Create graph with governor
graph = create_execution_graph(graph_spec, governor=governor)

# Execute (governor enforces all policies)
result = await graph.execute()
```

### Example: Budget Exceeded

```python
# Budget: max_steps=5
governor.steps_consumed = 5  # At limit

# Next node execution will fail
try:
    decision = governor.check_node_execution(node_spec, is_dry_run=False)
except BudgetExceededException as e:
    print(f"Budget exceeded: {e}")
    # Auto-rollback triggered (if configured)
```

### Example: Approval Gate

```python
# Policy requires approval for DNS operations
policy = ExecutionPolicy(
    ...
    require_approval_for_types=["dns"],
)

# DNS node execution blocked until approval
try:
    decision = governor.check_node_execution(dns_node_spec)
except ApprovalRequiredException as e:
    print(f"Approval required: {e}")
    # Notify admin, wait for approval
```

---

## Governance Decisions

The governor returns structured decisions:

```python
class GovernorDecision(BaseModel):
    decision_type: GovernorDecisionType  # ALLOW, DENY, REQUIRE_APPROVAL, DEGRADE
    node_id: str
    allow_reason: Optional[str]
    deny_reason: Optional[str]
    budget_consumed: Dict[str, Any]
    budget_remaining: Dict[str, Any]
    requires_approval: bool = False
    degraded: bool = False
```

**Decision Types:**

1. **ALLOW**: Node execution permitted
2. **DENY**: Node execution denied (budget exceeded, policy violation)
3. **REQUIRE_APPROVAL**: Waiting for manual approval
4. **DEGRADE**: Node skipped due to soft degradation

---

## Testing

### Test: Budget Exceeded → FAIL + Rollback

```python
def test_governor_budget_exceeded_hard_limit():
    budget = ExecutionBudget(max_steps=3, step_limit_type=BudgetLimitType.HARD)
    policy = ExecutionPolicy(policy_id="test", policy_name="Test", budget=budget)
    governor = ExecutionGovernor(policy)

    governor.start_execution()
    governor.steps_consumed = 3  # At limit

    # Should raise BudgetExceededException
    with pytest.raises(BudgetExceededException):
        governor.check_node_execution(node_spec, is_dry_run=False)
```

### Test: Approval Required → BLOCK

```python
def test_governor_approval_required():
    policy = ExecutionPolicy(
        ...
        require_approval_for_types=["dns"],
    )
    governor = ExecutionGovernor(policy)

    # Should raise ApprovalRequiredException
    with pytest.raises(ApprovalRequiredException):
        governor.check_node_execution(dns_node_spec)
```

---

## Backward Compatibility

**All Sprint 8 code remains functional without governor.**

The governor is **optional**:

```python
# Without governor (Sprint 8 behavior)
graph = create_execution_graph(graph_spec)
result = await graph.execute()

# With governor (Sprint 9 enforcement)
graph = create_execution_graph(graph_spec, governor=governor)
result = await graph.execute()
```

Implementation uses try/except imports:

```python
try:
    from backend.app.modules.autonomous_pipeline.governor import ExecutionGovernor
    GOVERNOR_AVAILABLE = True
except ImportError:
    GOVERNOR_AVAILABLE = False

# Optional governor checks
if self.governor and GOVERNOR_AVAILABLE:
    decision = self.governor.check_node_execution(node_spec)
```

---

## Files

| File | Description |
|------|-------------|
| `governor_schemas.py` | Budget, Policy, Decision models |
| `governor.py` | ExecutionGovernor service |
| `execution_graph.py` | Integration (optional governor parameter) |

---

## Key Takeaways

✅ **No run without budget awareness** – Every execution has defined limits
✅ **Fail-closed by default** – Invalid state triggers failure, not silent degradation
✅ **Approval gates for critical operations** – DNS, Deploy, Odoo require approval
✅ **Soft degradation available** – Skip non-critical nodes when approaching limits
✅ **Dry-run respects limits** – No cost surprises even in simulation
✅ **Backward compatible** – Sprint 8 code unchanged and functional

---

**Next:** [Sprint 9-B: Run Contracts](./SPRINT9_RUN_CONTRACTS.md)
