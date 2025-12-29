# Sprint 3: EventStream Migration Plan

**Sprint Goal:** Integrate EventStream into 3 security-critical modules
**Estimated Effort:** 8-11 hours
**Modules Selected:** policy, threats, immune

---

## 1. Module Selection Rationale

### ✅ Selected Modules

#### 1.1 **policy** (Priority: HIGHEST)
- **Location:** `backend/app/modules/policy/`
- **Size:** 561 lines (service.py)
- **Complexity:** HIGH
- **Event Count:** 6+ events
- **Effort:** 4-5 hours
- **Value:** ⭐⭐⭐⭐⭐ CRITICAL

**Why Migrate:**
- Critical for security audit trail
- Every policy evaluation should be logged
- DENY/WARN/AUDIT effects need event tracking
- Policy CRUD operations need change tracking

**Event Types:**
1. `policy.evaluated` - Every policy evaluation (agent, action, result)
2. `policy.denied` - When action is denied
3. `policy.warning_triggered` - When WARN effect applied
4. `policy.audit_required` - When AUDIT effect applied
5. `policy.created` - When new policy created
6. `policy.updated` - When policy modified
7. `policy.deleted` - When policy removed

**Key Functions to Instrument:**
- `PolicyEngine.evaluate()` - Core evaluation logic
- `PolicyEngine.create_policy()` - CRUD create
- `PolicyEngine.update_policy()` - CRUD update
- `PolicyEngine.delete_policy()` - CRUD delete

---

#### 1.2 **threats** (Priority: HIGH)
- **Location:** `backend/app/modules/threats/`
- **Size:** 173 lines (service.py)
- **Complexity:** MEDIUM
- **Event Count:** 4 events
- **Effort:** 3-4 hours
- **Value:** ⭐⭐⭐⭐ HIGH

**Why Migrate:**
- Critical for security monitoring
- Threat lifecycle needs tracking
- Integration with immune system
- Real-time threat alerting

**Event Types:**
1. `threat.detected` - When threat created
2. `threat.status_changed` - When status updated (OPEN → INVESTIGATING → RESOLVED)
3. `threat.escalated` - When severity increases
4. `threat.mitigated` - When threat resolved/closed

**Key Functions to Instrument:**
- `create_threat()` - Threat creation
- `update_threat_status()` - Status changes
- (Add severity escalation logic if needed)

---

#### 1.3 **immune** (Priority: MEDIUM)
- **Location:** `backend/app/modules/immune/core/`
- **Size:** 44 lines (service.py)
- **Complexity:** LOW
- **Event Count:** 2 events
- **Effort:** 1-2 hours
- **Value:** ⭐⭐⭐ MEDIUM

**Why Migrate:**
- Quick win (simple codebase)
- Complements threats module
- Already has event concept (ImmuneEvent)
- Health monitoring integration

**Event Types:**
1. `immune.event_published` - When immune event recorded
2. `immune.critical_issue_detected` - When critical severity detected

**Key Functions to Instrument:**
- `ImmuneService.publish_event()` - Event recording
- `ImmuneService.health_summary()` - Health checks

---

### ❌ Skipped Modules

#### **supervisor** (Reason: Low Value, Stub Code)
- **Size:** 46 lines (mostly empty)
- **Issue:** No real supervisor logic implemented
- **Current State:** Just queries mission stats
- **Decision:** Skip until supervisor logic is implemented

---

## 2. Migration Phases (Per Module)

### Phase 0: Analysis (30-45 min per module)
- [ ] Read all module files (service, router, schemas)
- [ ] Identify event trigger points
- [ ] Map data flows and state changes
- [ ] Document event types and payloads

### Phase 1: Event Design (30-45 min per module)
- [ ] Create EVENTS.md specification
- [ ] Define event payload schemas
- [ ] Document event lifecycle
- [ ] Identify consumer use cases

### Phase 2: Producer Implementation (2-3 hours per module)
- [ ] Add EventStream import with graceful fallback
- [ ] Inject EventStream via dependency injection
- [ ] Implement `_emit_event_safe()` helper
- [ ] Add event publishing to all trigger points
- [ ] Ensure non-blocking (Charter v1.0)

### Phase 3: Consumer Implementation (Skip for Sprint 3)
- All 3 modules are **producer-only** (no consumers needed)

### Phase 4: Testing (1-2 hours per module)
- [ ] Create comprehensive test file
- [ ] Test all event types individually
- [ ] Test event lifecycle scenarios
- [ ] Test Charter v1.0 compliance (graceful degradation)
- [ ] Test payload structure
- [ ] Ensure all tests pass

### Phase 5: Documentation (30 min per module)
- [ ] Create/update EVENTS.md
- [ ] Update README.md with EventStream integration
- [ ] Create Sprint 3 migration summary
- [ ] Document any breaking changes

### Phase 6: Commit & Push (15 min per module)
- [ ] Commit implementation + tests
- [ ] Commit documentation
- [ ] Push to branch

---

## 3. Detailed Event Specifications

### 3.1 Policy Events

#### Event: `policy.evaluated`
**Source:** `backend.app.modules.policy.service.PolicyEngine`
**Trigger:** Every policy evaluation in `evaluate()`

**Payload:**
```json
{
  "agent_id": "ops_agent",
  "action": "deploy_application",
  "resource": null,
  "result": {
    "allowed": false,
    "effect": "deny",
    "matched_policy": "admin_full_access",
    "matched_rule": "admin_allow_all",
    "reason": "Denied by rule 'Guest Write Deny'"
  },
  "evaluation_time_ms": 1.23,
  "evaluated_at": 1735424567.89
}
```

#### Event: `policy.denied`
**Source:** `backend.app.modules.policy.service.PolicyEngine`
**Trigger:** When `evaluate()` returns `allowed=false`

**Payload:**
```json
{
  "agent_id": "guest_user",
  "action": "delete_database",
  "matched_policy": "guest_read_only",
  "matched_rule": "guest_write_deny",
  "reason": "Denied by rule 'Guest Write Deny'",
  "denied_at": 1735424567.89
}
```

#### Event: `policy.warning_triggered`
**Source:** `backend.app.modules.policy.service.PolicyEngine`
**Trigger:** When effect is `WARN`

**Payload:**
```json
{
  "agent_id": "ops_agent",
  "action": "deploy_to_production",
  "matched_policy": "production_safety",
  "matched_rule": "prod_deploy_warning",
  "warnings": ["Deploying to production without manual approval"],
  "triggered_at": 1735424567.89
}
```

#### Event: `policy.audit_required`
**Source:** `backend.app.modules.policy.service.PolicyEngine`
**Trigger:** When effect is `AUDIT`

**Payload:**
```json
{
  "agent_id": "admin_user",
  "action": "delete_all_data",
  "matched_policy": "critical_actions",
  "matched_rule": "delete_audit",
  "requires_audit": true,
  "audit_at": 1735424567.89
}
```

#### Event: `policy.created`
**Source:** `backend.app.modules.policy.service.PolicyEngine`
**Trigger:** `create_policy()`

**Payload:**
```json
{
  "policy_id": "policy_3",
  "name": "Production Safety Policy",
  "version": "1.0.0",
  "rules_count": 3,
  "enabled": true,
  "created_at": 1735424567.89
}
```

#### Event: `policy.updated`
**Source:** `backend.app.modules.policy.service.PolicyEngine`
**Trigger:** `update_policy()`

**Payload:**
```json
{
  "policy_id": "policy_3",
  "changes": {
    "enabled": {"old": true, "new": false},
    "rules": {"old_count": 3, "new_count": 4}
  },
  "updated_at": 1735424567.89
}
```

#### Event: `policy.deleted`
**Source:** `backend.app.modules.policy.service.PolicyEngine`
**Trigger:** `delete_policy()`

**Payload:**
```json
{
  "policy_id": "policy_3",
  "name": "Production Safety Policy",
  "deleted_at": 1735424567.89
}
```

---

### 3.2 Threats Events

#### Event: `threat.detected`
**Source:** `backend.app.modules.threats.service`
**Trigger:** `create_threat()`

**Payload:**
```json
{
  "threat_id": "uuid-1234",
  "type": "sql_injection",
  "source": "api_gateway",
  "severity": "HIGH",
  "status": "OPEN",
  "description": "Detected SQL injection attempt in /api/users endpoint",
  "metadata": {
    "ip": "192.168.1.100",
    "endpoint": "/api/users"
  },
  "detected_at": 1735424567.89
}
```

#### Event: `threat.status_changed`
**Source:** `backend.app.modules.threats.service`
**Trigger:** `update_threat_status()`

**Payload:**
```json
{
  "threat_id": "uuid-1234",
  "old_status": "OPEN",
  "new_status": "INVESTIGATING",
  "severity": "HIGH",
  "changed_at": 1735424567.89
}
```

#### Event: `threat.escalated`
**Source:** `backend.app.modules.threats.service`
**Trigger:** Severity increase (if implemented)

**Payload:**
```json
{
  "threat_id": "uuid-1234",
  "old_severity": "MEDIUM",
  "new_severity": "HIGH",
  "reason": "Repeated attempts detected",
  "escalated_at": 1735424567.89
}
```

#### Event: `threat.mitigated`
**Source:** `backend.app.modules.threats.service`
**Trigger:** `update_threat_status()` when status → RESOLVED/CLOSED

**Payload:**
```json
{
  "threat_id": "uuid-1234",
  "type": "sql_injection",
  "severity": "HIGH",
  "resolution": "Blocked IP address and patched vulnerability",
  "duration_seconds": 3600,
  "mitigated_at": 1735424567.89
}
```

---

### 3.3 Immune Events

#### Event: `immune.event_published`
**Source:** `backend.app.modules.immune.core.service.ImmuneService`
**Trigger:** `publish_event()`

**Payload:**
```json
{
  "event_id": 42,
  "severity": "CRITICAL",
  "category": "security",
  "message": "Multiple failed login attempts",
  "metadata": {
    "user": "admin",
    "attempts": 5
  },
  "published_at": 1735424567.89
}
```

#### Event: `immune.critical_issue_detected`
**Source:** `backend.app.modules.immune.core.service.ImmuneService`
**Trigger:** `publish_event()` when severity is CRITICAL

**Payload:**
```json
{
  "event_id": 42,
  "category": "security",
  "message": "System compromise detected",
  "metadata": {
    "threat_level": "red",
    "affected_systems": ["database", "api"]
  },
  "detected_at": 1735424567.89
}
```

---

## 4. Implementation Order

### Day 1: policy (4-5 hours)
1. **Phase 0:** Analysis (45 min)
2. **Phase 1:** Event design + EVENTS.md (45 min)
3. **Phase 2:** Producer implementation (2.5 hours)
4. **Phase 4:** Testing (1.5 hours)
5. **Phase 5:** Documentation (30 min)
6. **Phase 6:** Commit & push (15 min)

### Day 2: threats (3-4 hours)
1. **Phase 0:** Analysis (30 min)
2. **Phase 1:** Event design + EVENTS.md (30 min)
3. **Phase 2:** Producer implementation (1.5 hours)
4. **Phase 4:** Testing (1 hour)
5. **Phase 5:** Documentation (30 min)
6. **Phase 6:** Commit & push (15 min)

### Day 3: immune (1-2 hours)
1. **Phase 0:** Analysis (20 min)
2. **Phase 1:** Event design + EVENTS.md (20 min)
3. **Phase 2:** Producer implementation (30 min)
4. **Phase 4:** Testing (30 min)
5. **Phase 5:** Documentation (15 min)
6. **Phase 6:** Commit & push (10 min)

---

## 5. Success Criteria

### Per-Module Checklist
- [ ] All event types implemented and tested
- [ ] `_emit_event_safe()` pattern used (non-blocking)
- [ ] EventStream injection via dependency injection
- [ ] Graceful degradation (works without EventStream)
- [ ] All tests passing (10+ tests per module)
- [ ] EVENTS.md documentation complete
- [ ] README.md updated with EventStream integration
- [ ] Charter v1.0 compliance verified
- [ ] Code committed and pushed

### Sprint 3 Complete When:
- [ ] All 3 modules migrated (policy, threats, immune)
- [ ] All tests passing (30+ total tests)
- [ ] All documentation complete
- [ ] Sprint summary created
- [ ] All commits pushed to branch

---

## 6. Risk Assessment

### Low Risk Items
- **immune module:** Tiny codebase (44 lines), simple logic
- **Event pattern:** Proven in Sprint 1 & 2 (course_factory, ir_governance, missions)

### Medium Risk Items
- **policy module:** Complex rule evaluation logic (561 lines)
- **threats module:** Redis integration needs careful testing

### Mitigation Strategies
- Use proven `_emit_event_safe()` pattern from Sprint 2
- Comprehensive testing (individual + lifecycle + Charter compliance)
- Start with policy (most complex) to identify issues early
- Document any gotchas in EVENTS.md

---

## 7. Timeline

**Sprint 3 Start:** Now
**Estimated Duration:** 8-11 hours (1-2 days of work)
**Expected Completion:** Within 2 days

**Module Breakdown:**
- policy: 4-5 hours (Day 1)
- threats: 3-4 hours (Day 2)
- immune: 1-2 hours (Day 3)

---

## 8. Next Steps After Sprint 3

### Sprint 4 Candidates
- **supervisor:** Once real supervisor logic is implemented
- **credits:** Resource management events
- **telemetry:** System monitoring events
- **fleet:** Robot coordination events (RYR integration)

### Future Enhancements
- **Audit Log Consumer:** Create centralized consumer for all security events
- **Real-time Alerts:** WebSocket consumer for critical events
- **Metrics Dashboard:** Aggregate event statistics
- **Event Replay:** Debugging and analysis tool

---

**Status:** READY TO START 🚀
**First Task:** Migrate policy module (Phase 0: Analysis)
