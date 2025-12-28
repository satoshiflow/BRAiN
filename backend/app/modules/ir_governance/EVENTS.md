# IR Governance - Event Specifications

**Module:** `backend/app/modules/ir_governance`
**Version:** 1.0.0 (EventStream Migration - Sprint 1)
**Last Updated:** 2025-12-28
**Charter Compliance:** v1.0 ✅

---

## 📋 Overview

IR Governance publishes **8 event types** for governance lifecycle, validation, and diff-audit. This module is **producer-only** and does not consume events from other modules.

**Role:** PRODUCER-ONLY

---

## 📤 Producer Events (8 Total)

### 1. `ir.approval_created`

**When Published:** HITL approval request created

**Criticality:** High (audit trail, compliance)

**Payload:**
```json
{
  "approval_id": "appr_a1b2c3d4",
  "tenant_id": "tenant_123",
  "ir_hash": "sha256:abcd1234...",
  "ttl_seconds": 3600,
  "expires_at": "2025-12-28T11:30:00Z",
  "created_by": "admin_user",
  "created_at": "2025-12-28T10:30:00Z"
}
```

**Envelope (Charter v1.0):**
```json
{
  "id": "evt_uuid_v4",
  "type": "ir.approval_created",
  "source": "ir_governance",
  "target": null,
  "timestamp": "2025-12-28T10:30:00.123456Z",
  "payload": { /* above */ },
  "meta": {
    "schema_version": "1.0",
    "producer": "ir_governance",
    "source_module": "ir_governance",
    "tenant_id": "tenant_123",
    "correlation_id": "req_123"
  }
}
```

**Consumers:**
- Audit Log (compliance tracking)
- Security Monitoring (approval requests)
- Analytics (governance metrics)

---

### 2. `ir.approval_consumed` ⚠️ CRITICAL

**When Published:** Approval token successfully consumed

**Criticality:** **CRITICAL** (execution authorization, audit trail)

**Payload:**
```json
{
  "approval_id": "appr_a1b2c3d4",
  "tenant_id": "tenant_123",
  "ir_hash": "sha256:abcd1234...",
  "consumed_by": "admin_user",
  "consumed_at": "2025-12-28T10:45:00Z",
  "time_to_consume_seconds": 900,
  "was_expired": false
}
```

**Consumers:**
- **Execution Engine** (green light to execute IR)
- Audit Log (approval consumed event)
- Compliance (governance trail)
- Analytics (approval latency metrics)

---

### 3. `ir.approval_expired`

**When Published:** Approval token expired (TTL exceeded)

**Criticality:** High (security, audit)

**Payload:**
```json
{
  "approval_id": "appr_a1b2c3d4",
  "tenant_id": "tenant_123",
  "ir_hash": "sha256:abcd1234...",
  "expired_at": "2025-12-28T11:30:00Z",
  "created_at": "2025-12-28T10:30:00Z",
  "ttl_seconds": 3600,
  "was_consumed": false
}
```

**Consumers:**
- Audit Log (expiration tracking)
- Security Monitoring (unused approvals)
- Analytics (approval abandonment rate)

---

### 4. `ir.approval_invalid`

**When Published:** Approval token validation failed

**Criticality:** High (security incident, potential attack)

**Payload:**
```json
{
  "tenant_id": "tenant_123",
  "ir_hash": "sha256:abcd1234...",
  "reason": "token_not_found | tenant_mismatch | ir_hash_mismatch | already_consumed",
  "attempted_by": "unknown_user",
  "attempted_at": "2025-12-28T10:50:00Z",
  "approval_id": null
}
```

**Consumers:**
- **Security Monitoring** (potential attack detection)
- Audit Log (failed authorization attempts)
- Incident Response (alert on high frequency)

---

### 5. `ir.validated_pass`

**When Published:** IR validation passed (no policy violations)

**Criticality:** High (execution clearance)

**Payload:**
```json
{
  "tenant_id": "tenant_123",
  "request_id": "req_123",
  "ir_hash": "sha256:abcd1234...",
  "risk_tier": 0,
  "requires_approval": false,
  "violations": [],
  "validated_at": "2025-12-28T10:30:00Z",
  "step_count": 5
}
```

**Consumers:**
- Execution Engine (proceed with execution)
- Audit Log (validation success)
- Analytics (validation metrics)

---

### 6. `ir.validated_escalate` ⚠️ CRITICAL

**When Published:** IR requires approval (Tier 2+ risk detected)

**Criticality:** **CRITICAL** (blocks execution pending approval)

**Payload:**
```json
{
  "tenant_id": "tenant_123",
  "request_id": "req_123",
  "ir_hash": "sha256:abcd1234...",
  "risk_tier": 2,
  "requires_approval": true,
  "violations": [],
  "high_risk_steps": [
    {
      "step_index": 2,
      "action": "odoo.update",
      "provider": "odoo",
      "risk_tier": 2,
      "reason": "Critical Odoo model: account.move"
    }
  ],
  "validated_at": "2025-12-28T10:30:00Z",
  "step_count": 5
}
```

**Consumers:**
- **Approval Service** (trigger HITL approval workflow)
- Execution Engine (BLOCK until approval)
- Audit Log (escalation event)
- Security Monitoring (high-risk operation tracking)

---

### 7. `ir.validated_reject` ⚠️ CRITICAL

**When Published:** IR validation failed (policy violations detected)

**Criticality:** **CRITICAL** (execution blocked permanently)

**Payload:**
```json
{
  "tenant_id": "tenant_123",
  "request_id": "req_123",
  "ir_hash": "sha256:abcd1234...",
  "risk_tier": 3,
  "requires_approval": false,
  "violations": [
    {
      "step_index": 1,
      "code": "UNKNOWN_ACTION",
      "message": "Unknown action: custom.delete. Must be from IRAction enum.",
      "severity": "ERROR"
    }
  ],
  "validated_at": "2025-12-28T10:30:00Z",
  "step_count": 5
}
```

**Consumers:**
- Execution Engine (BLOCK execution permanently)
- Audit Log (rejection event)
- Security Monitoring (policy violation tracking)
- Analytics (rejection rate, violation patterns)

---

### 8. `ir.dag_diff_ok`

**When Published:** IR ↔ DAG integrity verified (hashes match)

**Criticality:** High (execution clearance)

**Payload:**
```json
{
  "tenant_id": "tenant_123",
  "request_id": "req_123",
  "ir_hash": "sha256:abcd1234...",
  "dag_hash": "sha256:abcd1234...",
  "step_count": 5,
  "dag_node_count": 5,
  "all_hashes_match": true,
  "verified_at": "2025-12-28T10:30:00Z"
}
```

**Consumers:**
- Execution Engine (proceed with execution)
- Audit Log (integrity verification)
- Analytics (diff-audit success rate)

---

### 9. `ir.dag_diff_failed` ⚠️ CRITICAL

**When Published:** IR ↔ DAG mismatch detected

**Criticality:** **CRITICAL** (BLOCKS execution, security incident)

**Payload:**
```json
{
  "tenant_id": "tenant_123",
  "request_id": "req_123",
  "ir_hash": "sha256:abcd1234...",
  "dag_hash": "sha256:different...",
  "step_count": 5,
  "dag_node_count": 6,
  "all_hashes_match": false,
  "mismatch_details": {
    "missing_ir_steps": [],
    "extra_dag_nodes": [3],
    "hash_mismatches": [
      {
        "step_index": 1,
        "ir_step_hash": "sha256:aaa...",
        "dag_node_hash": "sha256:bbb..."
      }
    ]
  },
  "verified_at": "2025-12-28T10:30:00Z"
}
```

**Consumers:**
- **Execution Engine** (BLOCK execution immediately)
- **Security Monitoring** (critical security incident - potential tampering)
- Incident Response (alert immediately)
- Audit Log (integrity failure)

---

## 🔧 Implementation Guide

### Producer Integration

**File:** `approvals.py`, `validator.py`, `diff_audit.py`

```python
from backend.mission_control_core.core.event_stream import EventStream, Event, EventType
from datetime import datetime
import uuid
from typing import Optional

class ApprovalsService:
    def __init__(self, store: Optional[ApprovalStore] = None, event_stream: Optional[EventStream] = None):
        self.store = store or InMemoryApprovalStore()
        self.event_stream = event_stream

    async def _publish_event_safe(self, event: Event) -> None:
        """Publish event with error handling (non-blocking)."""
        if self.event_stream is None:
            logger.debug("[IRGovernance] EventStream not available, skipping")
            return

        try:
            await self.event_stream.publish_event(event)
            logger.info(f"[IRGovernance] Event published: {event.type.value}")
        except Exception as e:
            logger.error(f"[IRGovernance] Event publishing failed", exc_info=True)
            # DO NOT raise - business logic must continue

    def create_approval(
        self,
        tenant_id: str,
        ir_hash: str,
        ttl_seconds: Optional[int] = None,
        created_by: Optional[str] = None,
    ) -> tuple[ApprovalRequest, str]:
        # ... business logic ...

        # Emit event
        await self._publish_event_safe(
            Event(
                id=str(uuid.uuid4()),
                type=EventType.IR_APPROVAL_CREATED,
                source="ir_governance",
                target=None,
                timestamp=datetime.utcnow(),
                payload={
                    "approval_id": approval.approval_id,
                    "tenant_id": tenant_id,
                    "ir_hash": ir_hash,
                    "ttl_seconds": ttl,
                    "expires_at": approval.expires_at.isoformat() + "Z",
                    "created_by": created_by,
                    "created_at": datetime.utcnow().isoformat() + "Z",
                },
                meta={
                    "schema_version": "1.0",
                    "producer": "ir_governance",
                    "source_module": "ir_governance",
                    "tenant_id": tenant_id,
                },
            )
        )

        return approval, raw_token
```

### Dependency Injection

**File:** `router.py`

```python
from fastapi import Request
from typing import Optional

def get_approvals_service_with_events(request: Request) -> ApprovalsService:
    """Get ApprovalsService with EventStream injection."""
    event_stream: Optional[EventStream] = getattr(request.app.state, "event_stream", None)

    # Get existing store
    store_type = os.getenv("APPROVAL_STORE", "memory").lower()
    store = InMemoryApprovalStore()  # or RedisApprovalStore

    return ApprovalsService(store=store, event_stream=event_stream)
```

---

## 🧪 Testing Requirements

### Producer Tests (8 events)

1. ✅ `ir.approval_created` published on create_approval()
2. ✅ `ir.approval_consumed` published on successful consume_approval()
3. ✅ `ir.approval_expired` published on expired token
4. ✅ `ir.approval_invalid` published on invalid token
5. ✅ `ir.validated_pass` published on IR validation success
6. ✅ `ir.validated_escalate` published on Tier 2+ detection
7. ✅ `ir.validated_reject` published on policy violation
8. ✅ `ir.dag_diff_ok` published on integrity verification success
9. ✅ `ir.dag_diff_failed` published on mismatch detection

### Error Handling Tests

1. ✅ Event publish failure doesn't break approval creation
2. ✅ Event publish failure doesn't break validation
3. ✅ Event publish failure doesn't break diff-audit

### Total Tests: ~10-12

---

## 📊 Event Flow Diagram

```
IR Submission                EventStream                   Consumers
┌─────────────┐             ┌──────────┐                  ┌──────────────┐
│ Submit IR   │             │          │                  │              │
│             │───────────> │ Publish  │                  │              │
│             │  Validation │          │                  │              │
│             │             │          │─────────────────>│ Validation   │
│             │             │          │ ir.validated_*   │ Consumer     │
└─────────────┘             │          │                  │              │
                            │          │                  └──────────────┘
┌─────────────┐             │          │                  ┌──────────────┐
│ Request     │             │          │                  │              │
│ Approval    │───────────> │ Publish  │                  │              │
│             │             │          │─────────────────>│ Approval     │
│             │             │          │ ir.approval_*    │ Consumer     │
└─────────────┘             │          │                  │              │
                            │          │                  └──────────────┘
┌─────────────┐             │          │                  ┌──────────────┐
│ Diff Audit  │             │          │                  │              │
│             │───────────> │ Publish  │                  │              │
│             │             │          │─────────────────>│ Execution    │
│             │             │          │ ir.dag_diff_*    │ Engine       │
└─────────────┘             └──────────┘                  └──────────────┘
```

---

## ✅ Phase 1 Checklist

- [x] 8 EventTypes specified
- [x] All producer event payloads defined
- [x] Event flow documented
- [x] Implementation examples provided
- [x] Testing requirements outlined
- [x] Dependency injection strategy defined

---

**Status:** ✅ **COMPLETE**
**Next Phase:** Phase 2 (Producer Implementation)
