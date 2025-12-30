# Sprint 1 - Phase 0 Analysis: ir_governance

**Module:** `backend/app/modules/ir_governance`
**Analyzed:** 2025-12-28
**Analyst:** Claude (Sprint 1 Migration)

---

## 📋 Module Purpose

**ir_governance** provides deterministic policy enforcement for autonomous business pipelines:

- **IR Validation**: Policy-as-code enforcement (no LLM, fail-closed)
- **HITL Approvals**: Human-In-The-Loop approval workflow for high-risk operations
- **Diff-Audit Gate**: IR ↔ DAG integrity verification
- **Risk Tiering**: Automatic risk assessment (Tier 0-3)
- **Single-Use Tokens**: Secure, time-limited approval tokens

**Current Status:** Sprint 9 (P0) + Sprint 11 (Redis backend)

---

## 🔍 Key Business State Changes

### 1. Approval Lifecycle

| Operation | Method | State Change |
|-----------|--------|--------------|
| Create Approval | `create_approval()` | Approval request created with secure token |
| Consume Approval | `consume_approval()` | Token validated and marked consumed (single-use) |
| Expire Approval | `consume_approval()` (check) | Approval marked expired if TTL exceeded |
| Invalid Token | `consume_approval()` (check) | Token validation failed |

### 2. IR Validation

| Operation | Method | State Change |
|-----------|--------|--------------|
| Validate IR | `validate_ir()` | IR validated → PASS, ESCALATE, or REJECT |

### 3. Diff-Audit

| Operation | Method | State Change |
|-----------|--------|--------------|
| Audit IR-DAG Mapping | `audit_ir_dag_mapping()` | IR ↔ DAG integrity verified (success/fail) |

---

## 📡 Event Design (Phase 0 → Phase 1)

### Events to Publish (Producer Role)

| Event Type | When Published | Critical? | Consumers |
|------------|----------------|-----------|-----------|
| `ir.approval_created` | Approval request created | Yes | Audit, Compliance |
| `ir.approval_consumed` | Approval token consumed | **CRITICAL** | Audit, Compliance, Execution Engine |
| `ir.approval_expired` | Token expired (TTL exceeded) | Yes | Audit, Monitoring |
| `ir.approval_invalid` | Token validation failed | Yes | Audit, Security Monitoring |
| `ir.validated_pass` | IR validation passed | Yes | Execution Engine, Audit |
| `ir.validated_escalate` | IR requires approval (Tier 2+) | **CRITICAL** | Approval Service, Audit |
| `ir.validated_reject` | IR validation failed | **CRITICAL** | Audit, Monitoring |
| `ir.dag_diff_ok` | IR ↔ DAG integrity verified | Yes | Execution Engine, Audit |
| `ir.dag_diff_failed` | IR ↔ DAG mismatch detected | **CRITICAL** | Execution Engine (BLOCK), Security |

**Total Events (Producer):** 8

### Events to Consume (Consumer Role)

**Status:** ❌ **NONE**

This module is **producer-only**. It does not consume events from other modules.

---

## 🏗️ Module Architecture

```
ir_governance/
├── schemas.py                  # Pydantic models (IR, IRStep, Approvals, etc.)
├── canonicalization.py         # Deterministic hashing (SHA256)
├── validator.py                # Policy-as-code enforcement
├── approvals.py                # HITL approval workflow
├── diff_audit.py               # IR ↔ DAG integrity gate
├── redis_approval_store.py     # Redis backend for approvals (Sprint 11)
├── approval_cleanup_worker.py  # Background cleanup for expired approvals
├── router.py                   # FastAPI endpoints (validation, approvals)
├── hitl_router.py              # Human-in-the-loop UI endpoints
└── __init__.py                 # Module exports
```

**Storage:**
- In-memory (default) or Redis (configurable via `APPROVAL_STORE` env var)
- No PostgreSQL yet

**Dependencies:** No cross-module imports (clean!)

---

## 🚨 Legacy Code Patterns

### ❌ Cross-Module Synchronous Calls

**Status:** ✅ **NONE FOUND**

No direct imports from `course_factory`, `course_distribution`, or `missions` detected.

### ⚠️ TODO Integration Points

**Found 1 critical TODO:**

**File:** `validator.py:429`
```python
# TODO: Integrate with existing audit event system
```

**Migration Strategy:**
- This TODO will be resolved via EventStream integration
- Replace logger.info() calls with event publishing
- All 8 audit events will be properly emitted

---

## 🎯 Migration Role Determination

**Role:** **PRODUCER-ONLY**

**Producer:**
- Publishes 8 event types for governance state changes

**Consumer:**
- NO consumer role (does not listen to other module events)

---

## 📦 Phase 1 Requirements

### EventTypes to Add (event_stream.py)

```python
# IR Governance Events (Sprint 1)
IR_APPROVAL_CREATED = "ir.approval_created"
IR_APPROVAL_CONSUMED = "ir.approval_consumed"
IR_APPROVAL_EXPIRED = "ir.approval_expired"
IR_APPROVAL_INVALID = "ir.approval_invalid"
IR_VALIDATED_PASS = "ir.validated_pass"
IR_VALIDATED_ESCALATE = "ir.validated_escalate"
IR_VALIDATED_REJECT = "ir.validated_reject"
IR_DAG_DIFF_OK = "ir.dag_diff_ok"
IR_DAG_DIFF_FAILED = "ir.dag_diff_failed"
```

### Files to Create

1. **`EVENTS.md`** - Complete event specification (8 producer events)
2. **`README.md`** - Module documentation (doesn't exist yet!)

### Files to Modify

1. **`approvals.py`** - Add EventStream injection, 4 publisher methods
2. **`validator.py`** - Add EventStream injection, 3 publisher methods
3. **`diff_audit.py`** - Add EventStream injection, 2 publisher methods
4. **`router.py`** - Update dependency injection (if needed)
5. **`event_stream.py`** - Add 8 new EventTypes

---

## 🧪 Test Requirements (Phase 4)

**Mandatory Tests (4):**

1. ✅ Event wird publiziert (Test 8 producers: approvals, validation, diff-audit)
2. ✅ Consumer verarbeitet Event (N/A - producer-only)
3. ✅ Replay derselben Message → keine Doppelwirkung (N/A - producer-only)
4. ✅ Fehlerfall korrekt behandelt (Event publish failures don't break business logic)

**Additional Tests:**
- Approval lifecycle events (created, consumed, expired, invalid)
- Validation events (pass, escalate, reject)
- Diff-audit events (ok, failed)
- Event publish error handling (non-blocking)

**Test File:** `backend/tests/test_ir_governance_events.py`

---

## 📊 Complexity Assessment

**Phase 2 (Producer):** Low-Medium
- 8 events to publish
- 3 service files to instrument (approvals, validator, diff_audit)
- Standard `_publish_event_safe()` pattern
- NO consumer implementation needed

**Phase 3 (Consumer):** N/A
- Module is producer-only
- Skip Phase 3 entirely

**Phase 4 (Tests):** Low-Medium
- Producer tests: Standard (similar to course_factory)
- Consumer tests: N/A
- Total: ~8-10 tests

**Phase 5 (Cleanup & Docs):** Low
- No legacy code to remove
- README.md creation
- Update validator.py TODO (line 429)

**Overall Complexity:** **LOW-MEDIUM** (simpler than course_distribution due to no consumer)

---

## ✅ Phase 0 Completion Checklist

- [x] Module purpose documented
- [x] All business state changes identified (8 producer events)
- [x] Consumer role assessed (none - producer-only)
- [x] Legacy code patterns checked (none found)
- [x] Event list finalized (8 producer events)
- [x] Architecture documented
- [x] Test requirements outlined
- [x] Complexity assessed
- [x] TODO comments catalogued (validator.py:429)

---

## 🚀 Next Steps

**Phase 1:** Event Design
- Create `EVENTS.md` with 8 event specifications
- Add 8 EventTypes to `event_stream.py`
- Design payload structures for each event

**Critical Decision Point:**
- Module is producer-only (no consumer)
- Can skip Phase 3 (Consumer Implementation)
- Faster migration path than course_distribution

---

**Analysis Status:** ✅ **COMPLETE**
**Proceed to Phase 1:** YES
