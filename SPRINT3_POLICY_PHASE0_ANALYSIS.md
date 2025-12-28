# Sprint 3 - Policy Module: Phase 0 Analysis

**Module:** `backend/app/modules/policy/`
**Analysis Date:** 2024-12-28
**Estimated Migration Effort:** 4-5 hours

---

## 1. Module Structure

### File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `service.py` | 561 | Core PolicyEngine with evaluation logic |
| `router.py` | 290 | FastAPI REST endpoints (12 routes) |
| `schemas.py` | 284 | Pydantic models (16 schemas) |
| `__init__.py` | - | Module exports |

**Total Size:** ~1,135 lines
**Complexity:** HIGH (rule evaluation engine, condition matching, operators)

---

## 2. Core Functionality Analysis

### 2.1 PolicyEngine Service (service.py)

**Singleton Pattern:**
- `get_policy_engine()` - Returns singleton instance (line 540)
- Stores policies in-memory: `self.policies: Dict[str, Policy] = {}`
- Tracks metrics: evaluations, allows, denies, warnings

**Key Methods:**

| Method | Lines | Purpose | Event Trigger Point |
|--------|-------|---------|-------------------|
| `evaluate()` | 162-245 | Main policy evaluation logic | ✅ policy.evaluated |
| `_apply_effect()` | 359-412 | Apply rule effect (ALLOW/DENY/WARN/AUDIT) | ✅ policy.warning_triggered<br>✅ policy.audit_required |
| `create_policy()` | 453-470 | Create new policy | ✅ policy.created |
| `update_policy()` | 480-503 | Update existing policy | ✅ policy.updated |
| `delete_policy()` | 505-511 | Delete policy | ✅ policy.deleted |
| `get_stats()` | 517-530 | Get statistics | (read-only) |

**Evaluation Flow:**
```
evaluate(context)
  ├─ Collect active policies
  ├─ Evaluate rules (priority order)
  ├─ Find first matching rule
  │   └─ _rule_matches(rule, context)
  │       └─ _condition_matches(condition, context)
  ├─ _apply_effect(effect, policy, rule, context)
  │   ├─ ALLOW → return result (allowed=true)
  │   ├─ DENY → return result (allowed=false) ← EVENT: policy.denied
  │   ├─ WARN → return result (allowed=true, warnings=[]) ← EVENT: policy.warning_triggered
  │   └─ AUDIT → return result (allowed=true, requires_audit=true) ← EVENT: policy.audit_required
  └─ Return result ← EVENT: policy.evaluated
```

**Foundation Integration:**
- Optional double-check with Foundation layer (line 214-226)
- If Foundation denies, overrides policy ALLOW → DENY

---

### 2.2 API Routes (router.py)

**12 Endpoints:**

| Method | Path | Handler | Event Impact |
|--------|------|---------|-------------|
| GET | `/api/policy/health` | `policy_health()` | None |
| GET | `/api/policy/info` | `policy_info()` | None |
| GET | `/api/policy/stats` | `get_policy_stats()` | None (read-only) |
| POST | `/api/policy/evaluate` | `evaluate_policy()` | ✅ Triggers policy.evaluated |
| GET | `/api/policy/policies` | `list_policies()` | None (read-only) |
| GET | `/api/policy/policies/{id}` | `get_policy()` | None (read-only) |
| POST | `/api/policy/policies` | `create_policy()` | ✅ Triggers policy.created |
| PUT | `/api/policy/policies/{id}` | `update_policy()` | ✅ Triggers policy.updated |
| DELETE | `/api/policy/policies/{id}` | `delete_policy()` | ✅ Triggers policy.deleted |
| POST | `/api/policy/test-rule` | `test_policy_rule()` | ✅ Triggers policy.evaluated (test mode) |
| GET | `/api/policy/default-policies` | `list_default_policies()` | None (read-only) |

**Key Observation:**
- Router delegates to PolicyEngine service methods
- EventStream integration should happen in **service.py**, not router.py
- Router remains unchanged (events emitted from service layer)

---

### 2.3 Data Models (schemas.py)

**Key Enums:**

```python
class PolicyEffect(str, Enum):
    ALLOW = "allow"   # Explicitly allow
    DENY = "deny"     # Explicitly deny
    WARN = "warn"     # Allow with warning
    AUDIT = "audit"   # Allow with audit requirement
```

**Core Models:**
- `PolicyRule` - Single rule with conditions, effect, priority
- `Policy` - Collection of rules with default_effect
- `PolicyEvaluationContext` - Input: agent_id, action, resource, environment, params
- `PolicyEvaluationResult` - Output: allowed, effect, matched_rule, reason, warnings

---

## 3. Event Design Summary

### 3.1 Event Types (7 Total)

| Event Type | Source Method | Trigger Condition | Priority |
|------------|--------------|-------------------|----------|
| `policy.evaluated` | `evaluate()` | Every policy evaluation | CRITICAL |
| `policy.denied` | `evaluate()` | When `allowed=false` | CRITICAL |
| `policy.warning_triggered` | `_apply_effect()` | When `effect=WARN` | HIGH |
| `policy.audit_required` | `_apply_effect()` | When `effect=AUDIT` | HIGH |
| `policy.created` | `create_policy()` | New policy created | MEDIUM |
| `policy.updated` | `update_policy()` | Policy modified | MEDIUM |
| `policy.deleted` | `delete_policy()` | Policy removed | MEDIUM |

---

### 3.2 Event Trigger Points (Code Locations)

#### Event 1: `policy.evaluated`
**Location:** `service.py:245` (end of `evaluate()` method)
**Trigger:** Every policy evaluation (success or failure)

```python
# Line 162-245
async def evaluate(self, context: PolicyEvaluationContext) -> PolicyEvaluationResult:
    # ... evaluation logic ...
    result = self._apply_effect(rule.effect, policy, rule, context)

    # 🔥 EVENT TRIGGER POINT
    await self._emit_event_safe(
        EventType.POLICY_EVALUATED,
        policy=policy,
        rule=rule,
        context=context,
        result=result,
    )

    return result
```

**Payload Fields:**
- `agent_id`: context.agent_id
- `action`: context.action
- `resource`: context.resource
- `result.allowed`: bool
- `result.effect`: ALLOW/DENY/WARN/AUDIT
- `result.matched_policy`: policy_id or None
- `result.matched_rule`: rule_id or None
- `result.reason`: string
- `evaluation_time_ms`: float

---

#### Event 2: `policy.denied`
**Location:** `service.py:227` (inside `evaluate()` when `allowed=false`)
**Trigger:** When evaluation returns DENY effect

```python
# Line 210-227
if not result.allowed:
    logger.warning(f"⚠️ Policy denied: agent={context.agent_id}, action={context.action}")

    # 🔥 EVENT TRIGGER POINT (before returning)
    await self._emit_event_safe(
        EventType.POLICY_DENIED,
        policy=policy,
        rule=rule,
        context=context,
        result=result,
    )

    return result
```

**Payload Fields:**
- `agent_id`: context.agent_id
- `action`: context.action
- `resource`: context.resource
- `matched_policy`: policy_id
- `matched_rule`: rule_id
- `reason`: result.reason
- `denied_at`: timestamp

---

#### Event 3: `policy.warning_triggered`
**Location:** `service.py:394` (in `_apply_effect()` when `effect=WARN`)
**Trigger:** When matched rule has WARN effect

```python
# Line 386-394
elif effect == PolicyEffect.WARN:
    result = PolicyEvaluationResult(
        allowed=True,
        effect=effect,
        matched_rule=rule.rule_id,
        matched_policy=policy.policy_id,
        reason=f"Allowed with warning by rule '{rule.name}'",
        warnings=[f"Action '{context.action}' triggered warning rule"],
    )

    # 🔥 EVENT TRIGGER POINT
    await self._emit_event_safe(
        EventType.POLICY_WARNING_TRIGGERED,
        policy=policy,
        rule=rule,
        context=context,
        warnings=result.warnings,
    )

    return result
```

**Payload Fields:**
- `agent_id`: context.agent_id
- `action`: context.action
- `matched_policy`: policy_id
- `matched_rule`: rule_id
- `warnings`: list of warning messages
- `triggered_at`: timestamp

---

#### Event 4: `policy.audit_required`
**Location:** `service.py:404` (in `_apply_effect()` when `effect=AUDIT`)
**Trigger:** When matched rule has AUDIT effect

```python
# Line 396-404
elif effect == PolicyEffect.AUDIT:
    result = PolicyEvaluationResult(
        allowed=True,
        effect=effect,
        matched_rule=rule.rule_id,
        matched_policy=policy.policy_id,
        reason=f"Allowed with audit requirement by rule '{rule.name}'",
        requires_audit=True,
    )

    # 🔥 EVENT TRIGGER POINT
    await self._emit_event_safe(
        EventType.POLICY_AUDIT_REQUIRED,
        policy=policy,
        rule=rule,
        context=context,
        requires_audit=True,
    )

    return result
```

**Payload Fields:**
- `agent_id`: context.agent_id
- `action`: context.action
- `matched_policy`: policy_id
- `matched_rule`: rule_id
- `requires_audit`: true
- `audit_at`: timestamp

---

#### Event 5: `policy.created`
**Location:** `service.py:470` (end of `create_policy()`)
**Trigger:** When new policy is created

```python
# Line 453-470
async def create_policy(self, request: PolicyCreateRequest) -> Policy:
    policy_id = f"policy_{len(self.policies) + 1}"

    policy = Policy(
        policy_id=policy_id,
        name=request.name,
        version=request.version,
        description=request.description,
        rules=request.rules,
        default_effect=request.default_effect,
        enabled=request.enabled,
    )

    self.policies[policy_id] = policy
    logger.info(f"✅ Created policy: {policy_id}")

    # 🔥 EVENT TRIGGER POINT
    await self._emit_event_safe(
        EventType.POLICY_CREATED,
        policy=policy,
    )

    return policy
```

**Payload Fields:**
- `policy_id`: unique ID
- `name`: policy name
- `version`: semver version
- `rules_count`: number of rules
- `enabled`: bool
- `created_at`: timestamp

---

#### Event 6: `policy.updated`
**Location:** `service.py:503` (end of `update_policy()`)
**Trigger:** When policy is modified

```python
# Line 480-503
async def update_policy(self, policy_id: str, request: PolicyUpdateRequest) -> Optional[Policy]:
    policy = self.policies.get(policy_id)
    if not policy:
        return None

    # Track changes for event payload
    changes = {}

    if request.name is not None:
        changes["name"] = {"old": policy.name, "new": request.name}
        policy.name = request.name
    if request.rules is not None:
        changes["rules"] = {"old_count": len(policy.rules), "new_count": len(request.rules)}
        policy.rules = request.rules
    # ... other fields

    policy.updated_at = datetime.utcnow()
    logger.info(f"✅ Updated policy: {policy_id}")

    # 🔥 EVENT TRIGGER POINT
    await self._emit_event_safe(
        EventType.POLICY_UPDATED,
        policy=policy,
        changes=changes,
    )

    return policy
```

**Payload Fields:**
- `policy_id`: unique ID
- `changes`: dict of old vs new values
- `updated_at`: timestamp

---

#### Event 7: `policy.deleted`
**Location:** `service.py:511` (inside `delete_policy()`)
**Trigger:** When policy is removed

```python
# Line 505-511
async def delete_policy(self, policy_id: str) -> bool:
    if policy_id in self.policies:
        policy = self.policies[policy_id]

        # 🔥 EVENT TRIGGER POINT (before deletion)
        await self._emit_event_safe(
            EventType.POLICY_DELETED,
            policy=policy,
        )

        del self.policies[policy_id]
        logger.info(f"✅ Deleted policy: {policy_id}")
        return True
    return False
```

**Payload Fields:**
- `policy_id`: unique ID
- `name`: policy name
- `deleted_at`: timestamp

---

## 4. EventStream Integration Strategy

### 4.1 Dependency Injection

**Current Singleton Pattern:**
```python
# Line 540-545
_policy_engine: Optional[PolicyEngine] = None

def get_policy_engine() -> PolicyEngine:
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
```

**Modified with EventStream:**
```python
# NEW: Accept optional EventStream
def get_policy_engine(event_stream: Optional["EventStream"] = None) -> PolicyEngine:
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine(event_stream=event_stream)
    return _policy_engine
```

**PolicyEngine Constructor:**
```python
# Line 56-73 (MODIFIED)
def __init__(self, event_stream: Optional["EventStream"] = None):
    """Initialize Policy Engine with optional EventStream"""
    self.event_stream = event_stream  # NEW
    self.policies: Dict[str, Policy] = {}
    self.permissions: Dict[str, Permission] = {}
    # ... rest of init
```

---

### 4.2 Non-Blocking Event Helper

**Add new method to PolicyEngine:**
```python
async def _emit_event_safe(
    self,
    event_type: str,  # e.g., "policy.evaluated"
    policy: Optional[Policy] = None,
    rule: Optional[PolicyRule] = None,
    context: Optional[PolicyEvaluationContext] = None,
    result: Optional[PolicyEvaluationResult] = None,
    changes: Optional[Dict] = None,
    warnings: Optional[List[str]] = None,
) -> None:
    """
    Emit policy event with error handling (non-blocking).

    Charter v1.0 Compliance:
    - Event publishing MUST NOT block business logic
    - Failures are logged but NOT raised
    """
    if self.event_stream is None or Event is None:
        logger.debug("[PolicyEngine] EventStream not available, skipping event")
        return

    try:
        # Build payload based on event type
        payload = {}

        if context:
            payload.update({
                "agent_id": context.agent_id,
                "action": context.action,
                "resource": context.resource,
            })

        if policy:
            payload["policy_id"] = policy.policy_id
            payload["policy_name"] = policy.name

        if rule:
            payload["rule_id"] = rule.rule_id
            payload["rule_name"] = rule.name

        if result:
            payload.update({
                "allowed": result.allowed,
                "effect": result.effect.value,
                "reason": result.reason,
            })

        if changes:
            payload["changes"] = changes

        if warnings:
            payload["warnings"] = warnings

        # Create and publish event
        event = Event(
            type=event_type,
            source="policy_engine",
            payload=payload,
        )

        await self.event_stream.publish(event)

        logger.debug(
            "[PolicyEngine] Event published: %s (policy=%s)",
            event_type,
            policy.policy_id if policy else "none",
        )

    except Exception as e:
        logger.error(
            "[PolicyEngine] Event publishing failed: %s (event_type=%s)",
            e,
            event_type,
            exc_info=True,
        )
        # DO NOT raise - business logic must continue
```

---

### 4.3 EventStream Import

**Add to top of service.py:**
```python
# EventStream integration (Sprint 3)
try:
    from backend.mission_control_core.core import EventStream, Event, EventType
except ImportError:
    EventStream = None
    Event = None
    EventType = None
    import warnings
    warnings.warn(
        "[PolicyEngine] EventStream not available (mission_control_core not installed)",
        RuntimeWarning
    )
```

---

## 5. Testing Strategy

### 5.1 Test Coverage Plan

**11 Tests Required:**

1. `test_policy_evaluated_event_on_allow` - ALLOW result triggers event
2. `test_policy_evaluated_event_on_deny` - DENY result triggers event
3. `test_policy_denied_event_published` - policy.denied event on DENY
4. `test_policy_warning_triggered_event` - WARN effect triggers event
5. `test_policy_audit_required_event` - AUDIT effect triggers event
6. `test_policy_created_event` - New policy creation triggers event
7. `test_policy_updated_event` - Policy update triggers event
8. `test_policy_deleted_event` - Policy deletion triggers event
9. `test_event_lifecycle_deny` - Full lifecycle: evaluate → denied
10. `test_policy_engine_works_without_eventstream` - Graceful degradation
11. `test_event_envelope_charter_compliance` - Charter v1.0 structure

**Test File:** `backend/tests/test_policy_events.py`

---

### 5.2 Mock Strategy

**Fixtures:**
```python
@pytest.fixture
def mock_event_stream():
    """Mock EventStream that captures published events"""
    class MockEventStream:
        def __init__(self):
            self.events = []

        async def publish(self, event):
            self.events.append(event)

    return MockEventStream()

@pytest.fixture
def sample_context():
    """Sample policy evaluation context"""
    return PolicyEvaluationContext(
        agent_id="test_agent",
        agent_role="admin",
        action="read_data",
        resource="database",
    )
```

---

## 6. Implementation Checklist

### Phase 2: Producer Implementation
- [ ] Add EventStream import with graceful fallback
- [ ] Update `PolicyEngine.__init__()` to accept event_stream parameter
- [ ] Update `get_policy_engine()` singleton to pass event_stream
- [ ] Implement `_emit_event_safe()` helper method
- [ ] Add event publishing to `evaluate()` (policy.evaluated)
- [ ] Add event publishing to `evaluate()` for DENY (policy.denied)
- [ ] Add event publishing to `_apply_effect()` for WARN
- [ ] Add event publishing to `_apply_effect()` for AUDIT
- [ ] Add event publishing to `create_policy()`
- [ ] Add event publishing to `update_policy()`
- [ ] Add event publishing to `delete_policy()`

### Phase 4: Testing
- [ ] Create `test_policy_events.py`
- [ ] Implement all 11 tests
- [ ] Verify all tests pass
- [ ] Verify payload structure matches Charter v1.0

### Phase 5: Documentation
- [ ] Create `backend/app/modules/policy/EVENTS.md`
- [ ] Update `backend/app/modules/policy/README.md`
- [ ] Document breaking changes (if any)

---

## 7. Risk Assessment

### High Risk Areas
- **Complex evaluation logic** - Many code paths (ALLOW, DENY, WARN, AUDIT)
- **Foundation integration** - Double-check may override result
- **Condition matching** - 7 operators (==, !=, >, <, contains, matches, in)

### Mitigation
- Add event publishing at the END of methods (after logic completes)
- Use non-blocking `_emit_event_safe()` pattern
- Comprehensive testing of all code paths

### Low Risk
- CRUD operations (`create_policy`, `update_policy`, `delete_policy`) are straightforward
- Event pattern proven in Sprint 1 & 2

---

## 8. Estimated Effort Breakdown

| Phase | Task | Estimated Time |
|-------|------|---------------|
| Phase 0 | Analysis | ✅ 45 min (DONE) |
| Phase 1 | Event design + EVENTS.md | 45 min |
| Phase 2 | Producer implementation | 2.5 hours |
| Phase 4 | Testing (11 tests) | 1.5 hours |
| Phase 5 | Documentation | 30 min |
| Phase 6 | Commit & push | 15 min |

**Total:** 5.75 hours (~6 hours with buffer)

---

## 9. Next Steps

1. **Phase 1:** Create detailed event specifications in EVENTS.md
2. **Phase 2:** Implement EventStream integration in service.py
3. **Phase 4:** Create comprehensive test suite
4. **Phase 5:** Document changes

**Ready to proceed to Phase 1: Event Design** ✅
