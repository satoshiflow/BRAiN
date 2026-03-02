# BRAiN Phase 3: Governor Phase 2c - Locked Fields Enforcement

**Session Type:** Feature Implementation
**Branch Strategy:** Create `claude/governor-phase2c-locked-fields-<session-id>` from `v2`
**Estimated Complexity:** Medium (3-4 hours)
**Prerequisites:** All deployment fixes completed, system running on dev.brain.falklabs.de

---

## 🎯 Mission Statement

Implement enforcement for locked fields in the Governor system to prevent unauthorized mutations of critical constraint fields during agent creation.

**Why this matters:**
- **Security:** Prevents privilege escalation via DNA manipulation
- **Compliance:** Enforces DSGVO Art. 22 (human override must always be allowed)
- **Governance:** Maintains system integrity through immutable safeguards

---

## 📊 Current System Status (2026-01-04)

### ✅ Deployment Complete
- **Branch:** `v2` (stable, all fixes merged)
- **Environment:** Development at https://dev.brain.falklabs.de
- **Backend:** Running on port 8001 with 160+ API endpoints
- **Frontend:** Control Deck on port 3001, AXE UI on port 3002
- **Database:** PostgreSQL with pgvector, Redis for caching/queuing
- **SSL:** Valid certificates for dev.brain.falklabs.de
- **Docker:** 8 containers running (backend, control-deck, axe-ui, postgres, redis, qdrant, ollama, openwebui)

### ✅ Recent Fixes (Session Summary)
**Total:** 47 commits merged (PRs #93, #94, #95)
- 7 TypeScript errors fixed (Frontend)
- 1 Docker configuration fix (port conflicts)
- 6 Backend Python errors fixed (DI, encoding, imports)
- Nginx configuration for external access
- Health endpoint routing fixed
- AXE UI integration completed

### ✅ Active Modules
All 17+ modules operational, including:
- NeuroRail (Phase 1: observe-only)
- **Governor** (Phase 2b: reduction engine + manifests)
- Fleet Management
- Policy Engine
- Constitutional Agents
- Genesis Agent System
- Mission System
- Credits & Resource Management

---

## 🏗️ Governor System Architecture

### Already Implemented (Phase 2a + 2b)

**Phase 2a: Typed Constraints**
- ✅ 15-field typed constraints (Budget, Capabilities, Runtime, Ethics, Security)
- ✅ `EffectiveConstraints` Pydantic model
- ✅ Default baselines for Worker/Supervisor roles

**Phase 2b: Governance Manifests**
- ✅ YAML-based manifest system
- ✅ Reduction engine with 4 conditions:
  - `customization` (custom DNA mutations)
  - `high_risk` (dangerous capabilities)
  - `production` (production environment)
  - `population_pressure` (fleet size limits)
- ✅ Monotonic reduction rules (percentage, absolute, keywords)
- ✅ Event system integration (Redis + PostgreSQL)
- ✅ 72 tests passing, 6 gates validated

**Files:**
```
backend/brain/governor/
├── manifests/
│   ├── defaults.yaml          # ✅ Locked fields declared
│   ├── worker_baseline.yaml   # ✅ Worker defaults
│   └── supervisor_baseline.yaml # ✅ Supervisor defaults
├── constraints/
│   └── schema.py              # ✅ EffectiveConstraints model
├── reduction/
│   └── engine.py              # ✅ Reduction logic
├── governor.py                # ✅ Main orchestrator
├── events.py                  # ✅ Event emission
└── tests/                     # ✅ 72 tests
```

### Current Limitation (Phase 2c Gap)

**Problem:**
Locked fields are **declared** in `defaults.yaml` but **NOT enforced**. Agent DNA can mutate:
- `ethics_flags.human_override` (must be `"always_allowed"`)
- `capabilities.can_create_agents` (must be `false`, except Genesis)
- `capabilities.can_modify_governor` (must be `false`)

**Example Attack:**
```python
# This SHOULD fail but currently doesn't:
dna = {
    "ethics_flags": {"human_override": "never"}  # ❌ Mutation attempt
}
governor.evaluate_creation("worker", dna)  # Currently succeeds! 🚨
```

---

## 🎯 Task: Phase 2c - Locked Fields Enforcement

### Objective
Block agent creation when DNA attempts to mutate locked fields, emit violation events, and maintain Genesis exception.

### Implementation Plan

#### **Step 1: Create Enforcement Module**

**File:** `backend/brain/governor/enforcement/locks.py`

**Requirements:**
```python
"""
Locked Fields Enforcement Module

Validates agent DNA against immutable constraint fields.
Prevents privilege escalation and ensures compliance.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class LockedFieldViolation(BaseModel):
    """Single locked field violation"""
    field_path: str              # e.g., "ethics_flags.human_override"
    locked_value: Any            # Expected value from manifest
    attempted_value: Any         # Value in DNA
    manifest_name: str           # e.g., "defaults"

class PolicyViolationError(Exception):
    """Raised when locked field is mutated"""
    def __init__(self, violations: List[LockedFieldViolation]):
        self.violations = violations
        msg = f"Locked field violations: {[v.field_path for v in violations]}"
        super().__init__(msg)

class LockedFieldEnforcer:
    """Enforces locked field immutability"""

    def __init__(self, manifest_loader):
        self.manifest_loader = manifest_loader

    def validate_dna_against_locks(
        self,
        role: str,
        dna: Dict[str, Any],
        manifest_name: str = "defaults"
    ) -> List[LockedFieldViolation]:
        """
        Check if DNA mutates any locked fields.

        Args:
            role: Agent role (worker, supervisor, genesis)
            dna: Proposed DNA mutations
            manifest_name: Manifest to check against

        Returns:
            List of violations (empty if valid)

        Raises:
            PolicyViolationError: If violations detected
        """
        # 1. Load manifest and locked fields
        # 2. Get baseline constraints for role
        # 3. Compare DNA values against locked fields
        # 4. Collect violations
        # 5. Raise PolicyViolationError if any violations

    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """Get value from nested dict using dot notation"""
        # e.g., "ethics_flags.human_override" -> obj["ethics_flags"]["human_override"]

    def _is_genesis_exception(self, role: str, field_path: str) -> bool:
        """Check if Genesis role has exception for this field"""
        # Genesis can have can_create_agents=true
        return role == "genesis" and field_path == "capabilities.can_create_agents"
```

**Key Logic:**
1. Load locked fields from manifest (e.g., `defaults.yaml`)
2. Iterate through DNA keys, check if any match locked field paths
3. Compare DNA value with locked value
4. Collect violations
5. Raise `PolicyViolationError` with violation details

**Edge Cases:**
- ✅ Genesis role can have `can_create_agents=true`
- ✅ Nested field paths (dot notation: `ethics_flags.human_override`)
- ✅ Missing DNA fields (no mutation) = valid
- ✅ DNA field matches locked value = valid
- ❌ DNA field differs from locked value = violation

---

#### **Step 2: Integrate into Governor**

**File:** `backend/brain/governor/governor.py`

**Modify:** `evaluate_creation()` method

**Current Flow:**
```python
def evaluate_creation(self, role: str, dna: Dict) -> CreationDecision:
    # 1. Load manifest
    # 2. Get baseline constraints
    # 3. Apply reduction engine  # ← Current enforcement
    # 4. Return decision
```

**New Flow:**
```python
def evaluate_creation(self, role: str, dna: Dict) -> CreationDecision:
    # 1. Load manifest
    # 2. Get baseline constraints
    # 3. **VALIDATE LOCKED FIELDS** ← NEW STEP
    try:
        violations = self.locked_field_enforcer.validate_dna_against_locks(
            role, dna, manifest_name="defaults"
        )
        if violations:
            raise PolicyViolationError(violations)
    except PolicyViolationError as e:
        # 3a. Emit governance.locked_field_violation event
        self._emit_violation_event(e.violations, role, dna)
        # 3b. Raise exception (blocks creation)
        raise

    # 4. Apply reduction engine (existing)
    # 5. Return decision
```

**Integration Points:**
```python
# In Governor.__init__():
from backend.brain.governor.enforcement.locks import LockedFieldEnforcer

self.locked_field_enforcer = LockedFieldEnforcer(self.manifest_loader)
```

---

#### **Step 3: Event System Extension**

**File:** `backend/brain/governor/events.py`

**Add New Event Type:**
```python
class GovernanceEventType(str, Enum):
    # ... existing events ...
    LOCKED_FIELD_VIOLATION = "governance.locked_field_violation"  # NEW

def emit_locked_field_violation(
    violations: List[LockedFieldViolation],
    role: str,
    dna: Dict[str, Any],
    redis_client,
    db_session
):
    """
    Emit event when locked field is mutated.

    Event Payload:
    {
        "violations": [
            {
                "field_path": "ethics_flags.human_override",
                "locked_value": "always_allowed",
                "attempted_value": "never",
                "manifest_name": "defaults"
            }
        ],
        "role": "worker",
        "dna_hash": "sha256:abc123...",
        "timestamp": 1704384000.0
    }
    """
    # 1. Serialize violations to dict
    # 2. Create event payload
    # 3. Emit to Redis (real-time)
    # 4. Log to PostgreSQL (durable)
```

**Database Schema (if needed):**
```sql
-- No schema changes required, events table already exists from Phase 2b
-- Uses existing governance_events table
```

---

#### **Step 4: Comprehensive Testing**

**File:** `backend/brain/governor/tests/test_locked_fields_enforcement.py`

**Test Coverage (15+ Unit Tests):**

```python
import pytest
from backend.brain.governor.enforcement.locks import (
    LockedFieldEnforcer,
    PolicyViolationError,
    LockedFieldViolation
)
from backend.brain.governor.governor import Governor

# ===== UNIT TESTS: LockedFieldEnforcer =====

def test_valid_dna_no_mutations():
    """DNA with no locked field mutations should pass"""
    enforcer = LockedFieldEnforcer(manifest_loader)
    dna = {"budget.max_llm_tokens": 5000}  # Non-locked field
    violations = enforcer.validate_dna_against_locks("worker", dna)
    assert violations == []

def test_locked_field_mutation_detected():
    """Mutating human_override should be detected"""
    enforcer = LockedFieldEnforcer(manifest_loader)
    dna = {"ethics_flags.human_override": "never"}  # Locked value: "always_allowed"

    with pytest.raises(PolicyViolationError) as exc_info:
        enforcer.validate_dna_against_locks("worker", dna)

    assert len(exc_info.value.violations) == 1
    assert exc_info.value.violations[0].field_path == "ethics_flags.human_override"

def test_multiple_violations():
    """Multiple locked field mutations should all be detected"""
    enforcer = LockedFieldEnforcer(manifest_loader)
    dna = {
        "ethics_flags.human_override": "never",
        "capabilities.can_modify_governor": True
    }

    with pytest.raises(PolicyViolationError) as exc_info:
        enforcer.validate_dna_against_locks("worker", dna)

    assert len(exc_info.value.violations) == 2

def test_genesis_exception_can_create_agents():
    """Genesis role should be allowed to have can_create_agents=true"""
    enforcer = LockedFieldEnforcer(manifest_loader)
    dna = {"capabilities.can_create_agents": True}

    # Should NOT raise for Genesis
    violations = enforcer.validate_dna_against_locks("genesis", dna)
    assert violations == []

    # Should raise for Worker
    with pytest.raises(PolicyViolationError):
        enforcer.validate_dna_against_locks("worker", dna)

def test_nested_field_path_resolution():
    """Dot notation paths should resolve correctly"""
    enforcer = LockedFieldEnforcer(manifest_loader)

    # Test _get_nested_value helper
    obj = {"ethics_flags": {"human_override": "always_allowed"}}
    value = enforcer._get_nested_value(obj, "ethics_flags.human_override")
    assert value == "always_allowed"

def test_dna_matches_locked_value():
    """DNA value matching locked value should pass"""
    enforcer = LockedFieldEnforcer(manifest_loader)
    dna = {"ethics_flags.human_override": "always_allowed"}  # Matches locked value

    violations = enforcer.validate_dna_against_locks("worker", dna)
    assert violations == []

# ===== INTEGRATION TESTS: Governor =====

def test_governor_blocks_locked_mutation():
    """Governor.evaluate_creation should block locked field mutations"""
    governor = Governor(manifest_loader, event_emitter, redis, db)

    dna = {"capabilities.can_modify_governor": True}  # Locked to false

    with pytest.raises(PolicyViolationError):
        governor.evaluate_creation("worker", dna)

def test_violation_event_emitted():
    """Locked field violation should emit event"""
    governor = Governor(manifest_loader, event_emitter, redis, db)

    dna = {"ethics_flags.human_override": "never"}

    with pytest.raises(PolicyViolationError):
        governor.evaluate_creation("worker", dna)

    # Check event was emitted
    events = get_recent_events(redis, "governance.locked_field_violation")
    assert len(events) == 1
    assert events[0]["payload"]["violations"][0]["field_path"] == "ethics_flags.human_override"

def test_valid_creation_still_works():
    """Valid DNA should still allow creation"""
    governor = Governor(manifest_loader, event_emitter, redis, db)

    dna = {"budget.max_llm_tokens": 3000}  # Non-locked field

    decision = governor.evaluate_creation("worker", dna)
    assert decision.approved is True

def test_genesis_creation_with_agent_capability():
    """Genesis agent with can_create_agents=true should succeed"""
    governor = Governor(manifest_loader, event_emitter, redis, db)

    dna = {"capabilities.can_create_agents": True}

    decision = governor.evaluate_creation("genesis", dna)
    assert decision.approved is True

def test_supervisor_cannot_create_agents():
    """Supervisor role cannot have can_create_agents=true"""
    governor = Governor(manifest_loader, event_emitter, redis, db)

    dna = {"capabilities.can_create_agents": True}

    with pytest.raises(PolicyViolationError):
        governor.evaluate_creation("supervisor", dna)

# ===== ERROR HANDLING =====

def test_invalid_field_path():
    """Invalid field paths should be handled gracefully"""
    enforcer = LockedFieldEnforcer(manifest_loader)
    dna = {"nonexistent.field": "value"}

    # Should not raise, just skip validation
    violations = enforcer.validate_dna_against_locks("worker", dna)
    assert violations == []

def test_missing_manifest():
    """Missing manifest should raise clear error"""
    enforcer = LockedFieldEnforcer(manifest_loader)

    with pytest.raises(FileNotFoundError):
        enforcer.validate_dna_against_locks("worker", {}, manifest_name="nonexistent")

# ===== PERFORMANCE =====

def test_validation_performance():
    """Validation should complete in <10ms"""
    enforcer = LockedFieldEnforcer(manifest_loader)
    dna = {"budget.max_llm_tokens": 5000}

    import time
    start = time.time()
    for _ in range(100):
        enforcer.validate_dna_against_locks("worker", dna)
    duration = time.time() - start

    assert duration < 1.0  # 100 validations in <1 second
```

**Test Execution:**
```bash
# Run tests
pytest backend/brain/governor/tests/test_locked_fields_enforcement.py -v

# With coverage
pytest backend/brain/governor/tests/test_locked_fields_enforcement.py --cov=backend/brain/governor/enforcement --cov-report=term-missing

# Expected coverage: >95%
```

---

#### **Step 5: Documentation Updates**

**File:** `backend/brain/governor/README.md`

Add section:
```markdown
## Phase 2c: Locked Fields Enforcement

### Overview
Locked fields are immutable constraint fields that cannot be mutated via DNA,
ensuring critical safeguards remain in place.

### Locked Fields
| Field Path | Locked Value | Reason |
|------------|--------------|--------|
| `ethics_flags.human_override` | `"always_allowed"` | DSGVO Art. 22 compliance |
| `capabilities.can_create_agents` | `false` (except Genesis) | Prevents privilege escalation |
| `capabilities.can_modify_governor` | `false` | Protects governance integrity |

### Enforcement Flow
1. Agent creation request with DNA mutations
2. `LockedFieldEnforcer.validate_dna_against_locks()` called
3. DNA compared against locked values from manifest
4. If mutation detected → `PolicyViolationError` raised
5. Event `governance.locked_field_violation` emitted
6. Creation rejected

### Genesis Exception
Genesis role is allowed to have `can_create_agents=true` to bootstrap the fleet.

### API Usage
```python
from backend.brain.governor.governor import Governor

governor = Governor(manifest_loader, event_emitter, redis, db)

# This will raise PolicyViolationError:
try:
    governor.evaluate_creation("worker", {
        "ethics_flags.human_override": "never"
    })
except PolicyViolationError as e:
    print(f"Violations: {e.violations}")
```
```

---

## 🚀 Implementation Workflow

### Step-by-Step Instructions for Claude Code

**1. Setup**
```bash
# Ensure on v2 branch
git checkout v2
git pull origin v2

# Create feature branch
git checkout -b claude/governor-phase2c-locked-fields-$(date +%s)

# Verify system is running
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps
curl https://dev.brain.falklabs.de/api/health
```

**2. Create Enforcement Module**
```bash
# Create directory structure
mkdir -p backend/brain/governor/enforcement
touch backend/brain/governor/enforcement/__init__.py
touch backend/brain/governor/enforcement/locks.py

# Implement LockedFieldEnforcer (see Step 1 above)
# - LockedFieldViolation model
# - PolicyViolationError exception
# - LockedFieldEnforcer class
# - validate_dna_against_locks() method
# - _get_nested_value() helper
# - _is_genesis_exception() helper
```

**3. Integrate into Governor**
```bash
# Modify backend/brain/governor/governor.py
# - Import LockedFieldEnforcer
# - Initialize in __init__()
# - Add validation in evaluate_creation() BEFORE reduction
# - Add _emit_violation_event() method
```

**4. Extend Event System**
```bash
# Modify backend/brain/governor/events.py
# - Add LOCKED_FIELD_VIOLATION to GovernanceEventType enum
# - Implement emit_locked_field_violation() function
# - Ensure dual-write (Redis + PostgreSQL)
```

**5. Write Tests**
```bash
# Create test file
touch backend/brain/governor/tests/test_locked_fields_enforcement.py

# Implement 15+ tests (see Step 4 above)
# Run tests to verify:
pytest backend/brain/governor/tests/test_locked_fields_enforcement.py -v
```

**6. Update Documentation**
```bash
# Update backend/brain/governor/README.md
# - Add Phase 2c section
# - Document locked fields
# - Document enforcement flow
# - Add API usage examples
```

**7. Integration Testing**
```bash
# Test end-to-end
python -c "
from backend.brain.governor.governor import Governor
from backend.brain.governor.enforcement.locks import PolicyViolationError

# Test locked field rejection
try:
    governor.evaluate_creation('worker', {
        'ethics_flags.human_override': 'never'
    })
    print('❌ FAILED: Should have raised PolicyViolationError')
except PolicyViolationError as e:
    print(f'✅ PASSED: {e}')

# Test Genesis exception
decision = governor.evaluate_creation('genesis', {
    'capabilities.can_create_agents': True
})
print(f'✅ Genesis exception: {decision.approved}')
"
```

**8. Commit and Push**
```bash
# Add all changes
git add backend/brain/governor/enforcement/
git add backend/brain/governor/governor.py
git add backend/brain/governor/events.py
git add backend/brain/governor/tests/test_locked_fields_enforcement.py
git add backend/brain/governor/README.md

# Commit with clear message
git commit -m "feat(governor): Implement Phase 2c locked fields enforcement

- Add LockedFieldEnforcer with PolicyViolationError
- Integrate validation into Governor.evaluate_creation()
- Emit governance.locked_field_violation events
- Add 15+ comprehensive tests
- Document locked fields and enforcement flow

Locked fields:
- ethics_flags.human_override (must be 'always_allowed')
- capabilities.can_create_agents (must be false, except Genesis)
- capabilities.can_modify_governor (must be false)

Resolves: Governor Phase 2c Task 1"

# Push to remote
git push -u origin HEAD
```

**9. Verify Deployment**
```bash
# Rebuild and restart
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build backend

# Check logs
docker compose logs -f backend | grep -i "locked\|violation"

# Test API endpoint (if exposed)
curl https://dev.brain.falklabs.de/api/governor/validate-creation \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"role":"worker","dna":{"ethics_flags.human_override":"never"}}'
```

---

## ✅ Success Criteria Checklist

- [ ] `LockedFieldEnforcer` class implemented with all methods
- [ ] `PolicyViolationError` raised when locked field is mutated
- [ ] Governor integration: validation runs BEFORE reduction engine
- [ ] Event `governance.locked_field_violation` emitted with correct payload
- [ ] Genesis exception: `can_create_agents=true` allowed only for Genesis
- [ ] 15+ unit tests written and passing
- [ ] 5+ integration tests written and passing
- [ ] Test coverage >95% for enforcement module
- [ ] Documentation updated (README.md)
- [ ] All existing tests still pass
- [ ] Manual end-to-end test successful
- [ ] Code committed with clear message
- [ ] Feature branch pushed to remote

---

## 📁 File Reference

### Files to Create
```
backend/brain/governor/enforcement/
├── __init__.py                          # NEW
└── locks.py                            # NEW (LockedFieldEnforcer)

backend/brain/governor/tests/
└── test_locked_fields_enforcement.py   # NEW (15+ tests)
```

### Files to Modify
```
backend/brain/governor/
├── governor.py                         # MODIFY (integrate enforcer)
├── events.py                           # MODIFY (add violation event)
└── README.md                           # MODIFY (add Phase 2c docs)
```

### Files to Reference (Do NOT modify)
```
backend/brain/governor/
├── manifests/
│   └── defaults.yaml                   # READ ONLY (locked fields source)
├── constraints/
│   └── schema.py                       # READ ONLY (EffectiveConstraints)
└── reduction/
    └── engine.py                       # READ ONLY (existing reduction logic)
```

---

## 🔍 Code Examples

### Example 1: LockedFieldEnforcer Usage

```python
from backend.brain.governor.enforcement.locks import LockedFieldEnforcer, PolicyViolationError

enforcer = LockedFieldEnforcer(manifest_loader)

# Valid DNA
dna_valid = {"budget.max_llm_tokens": 3000}
violations = enforcer.validate_dna_against_locks("worker", dna_valid)
print(violations)  # []

# Invalid DNA (mutation)
dna_invalid = {"ethics_flags.human_override": "never"}
try:
    enforcer.validate_dna_against_locks("worker", dna_invalid)
except PolicyViolationError as e:
    print(f"Violations: {len(e.violations)}")
    for v in e.violations:
        print(f"  {v.field_path}: {v.attempted_value} != {v.locked_value}")
```

### Example 2: Governor Integration

```python
# In backend/brain/governor/governor.py

def evaluate_creation(self, role: str, dna: Dict[str, Any]) -> CreationDecision:
    """Evaluate agent creation request with locked field enforcement."""

    # 1. Load manifest
    manifest = self.manifest_loader.load("defaults")

    # 2. Get baseline constraints
    baseline = self._get_baseline_constraints(role, manifest)

    # 3. **VALIDATE LOCKED FIELDS** (NEW)
    try:
        violations = self.locked_field_enforcer.validate_dna_against_locks(
            role, dna, manifest_name="defaults"
        )
        if violations:
            raise PolicyViolationError(violations)
    except PolicyViolationError as e:
        # Emit event
        self.event_emitter.emit_locked_field_violation(
            e.violations, role, dna, self.redis, self.db
        )
        # Block creation
        raise

    # 4. Apply reduction engine (existing)
    effective = self.reduction_engine.apply(baseline, dna, context={
        "role": role,
        "high_risk": self._is_high_risk(dna),
        "production": self._is_production_env()
    })

    # 5. Return decision
    return CreationDecision(
        approved=True,
        effective_constraints=effective,
        reductions_applied=[...]
    )
```

### Example 3: Event Emission

```python
# In backend/brain/governor/events.py

def emit_locked_field_violation(
    violations: List[LockedFieldViolation],
    role: str,
    dna: Dict[str, Any],
    redis_client,
    db_session
):
    """Emit governance.locked_field_violation event."""

    event_data = {
        "event_type": "governance.locked_field_violation",
        "timestamp": time.time(),
        "payload": {
            "violations": [v.dict() for v in violations],
            "role": role,
            "dna_hash": hashlib.sha256(json.dumps(dna, sort_keys=True).encode()).hexdigest(),
            "severity": "critical"
        }
    }

    # Dual write
    redis_client.publish("governance_events", json.dumps(event_data))

    db_event = GovernanceEvent(
        event_type=event_data["event_type"],
        timestamp=event_data["timestamp"],
        payload=event_data["payload"]
    )
    db_session.add(db_event)
    db_session.commit()
```

---

## 🐛 Debugging Tips

### Issue 1: PolicyViolationError not raised
**Symptom:** Locked field mutation doesn't raise exception
**Debug:**
```python
# Add debug logging
import logging
logger = logging.getLogger(__name__)

def validate_dna_against_locks(self, role, dna, manifest_name):
    logger.debug(f"Validating DNA: {dna}")
    locked_fields = self._get_locked_fields(manifest_name)
    logger.debug(f"Locked fields: {locked_fields}")

    for field_path, locked_value in locked_fields.items():
        if field_path in dna:
            logger.debug(f"Checking {field_path}: {dna[field_path]} vs {locked_value}")
```

### Issue 2: Genesis exception not working
**Symptom:** Genesis role blocked from can_create_agents
**Debug:**
```python
# Check exception logic
def _is_genesis_exception(self, role, field_path):
    result = role == "genesis" and field_path == "capabilities.can_create_agents"
    logger.debug(f"Genesis exception check: role={role}, field={field_path}, result={result}")
    return result
```

### Issue 3: Nested paths not resolving
**Symptom:** `ethics_flags.human_override` not found
**Debug:**
```python
# Test _get_nested_value
obj = {"ethics_flags": {"human_override": "always_allowed"}}
path = "ethics_flags.human_override"
value = self._get_nested_value(obj, path)
print(f"Path {path} resolved to: {value}")
```

---

## 📚 Related Documentation

- **Governor Phase 2a:** `backend/brain/governor/docs/phase2a_typed_constraints.md`
- **Governor Phase 2b:** `backend/brain/governor/docs/phase2b_manifests.md`
- **CLAUDE.md:** `/home/user/BRAiN/CLAUDE.md` (section: Backend Architecture > Governor)
- **Constraint Schema:** `backend/brain/governor/constraints/schema.py`
- **Manifest Spec:** `backend/brain/governor/manifests/README.md`

---

## 🎯 Final Checklist

Before marking complete:
- [ ] All 15+ tests pass
- [ ] Coverage report shows >95%
- [ ] Manual end-to-end test successful
- [ ] Documentation updated
- [ ] Code follows CLAUDE.md conventions (async-first, type hints, error handling)
- [ ] No breaking changes to existing Governor API
- [ ] Events visible in Redis stream
- [ ] Events persisted in PostgreSQL
- [ ] Git commit message follows conventional commits
- [ ] Branch pushed to remote

---

**Ready to start? Create the feature branch and begin with Step 1: Enforcement Module!** 🚀
