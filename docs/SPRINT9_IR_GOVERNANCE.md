# Sprint 9 (P0): IR Governance Kernel v1

**Version:** 1.0.0
**Sprint:** Sprint 9 (P0)
**Status:** ✅ Complete
**Author:** BRAiN Development Team

---

## Overview

The **IR Governance Kernel** transforms BRAiN from "LLM-assisted automation" into a **deterministic, policy-enforced operating kernel** by introducing:

1. **Canonical Intermediate Representation (IR)** - Single Source of Truth
2. **Deterministic Validator** - Policy-as-code enforcement (LLM-free)
3. **HITL Approvals Service** - Human-in-the-loop workflow with secure tokens
4. **Diff-Audit Gate** - IR ↔ DAG integrity verification

**Core Principle:** Fail-closed by default. No LLM in the critical path.

---

## Operating Principles

✅ **Conservative approach** - Minimal changes, maximum stability
✅ **Fail-closed by default** - If uncertain → ESCALATE/REJECT, never guess
✅ **No LLM in critical path** - LLMs propose IR, kernel validates deterministically
✅ **Backwards compatible** - Legacy entrypoints continue to work
✅ **No external dependencies** - Pure Python, no Redis required
✅ **No secrets/PII in logs** - Token hashes only, never raw tokens

---

## Architecture

### Execution Flow

```
User Intent
    │
    ▼
┌─────────────────────────────────┐
│ LLM (Optional)                  │
│ Proposes IR from natural language│
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ IR (Canonical SSOT)             │
│ - Strict schema                 │
│ - Fixed vocabularies            │
│ - Idempotency keys              │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Validator (Deterministic)       │
│ - Risk tier calculation         │
│ - Auto-escalation rules         │
│ - Status: PASS|ESCALATE|REJECT  │
└──────────────┬──────────────────┘
               │
               ├─── PASS ──────────┐
               │                   │
               ├─── ESCALATE ──────┤
               │                   │
               ▼                   │
         ┌─────────────┐           │
         │ Approvals   │           │
         │ (HITL)      │           │
         └──────┬──────┘           │
                │                  │
                ▼                  │
         Approval Token            │
                │                  │
                ▼                  │
         Consume Approval          │
                │                  │
                └──────────────────┤
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │ DAG Compile         │
                        │ (from IR)           │
                        └──────────┬──────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │ Diff-Audit Gate     │
                        │ (IR ↔ DAG integrity)│
                        └──────────┬──────────┘
                                   │
                            Success │ Mismatch
                                   │     │
                                   ▼     ▼
                              Execute  BLOCK
```

---

## Components

### A) IR Schema (SSOT)

**File:** `backend/app/modules/ir_governance/schemas.py`

**IR Structure:**
```python
{
  "tenant_id": "tenant_demo",              # Required
  "request_id": "uuid",                    # Auto-generated
  "intent_summary": "Deploy staging...",   # Optional
  "steps": [
    {
      "action": "deploy.website",          # Fixed vocabulary (IRAction)
      "provider": "deploy.provider_v1",    # Fixed vocabulary (IRProvider)
      "resource": "site:staging",
      "params": {...},
      "constraints": {...},
      "idempotency_key": "deploy-001",     # Required, non-empty
      "budget_cents": 5000,                # Integer only (no floats)
      "step_id": "step_0"                  # Optional
    }
  ]
}
```

**Fixed Vocabularies (Fail-Closed):**

| IRAction (20 actions) | IRProvider (12 providers) |
|-----------------------|---------------------------|
| `deploy.website`      | `deploy.provider_v1`      |
| `deploy.api`          | `deploy.docker`           |
| `dns.update_records`  | `dns.hetzner`             |
| `dns.create_zone`     | `dns.cloudflare`          |
| `dns.delete_zone`     | `dns.route53`             |
| `odoo.install_module` | `odoo.v16`                |
| `odoo.uninstall_module`| `odoo.v17`               |
| `webgen.generate_site`| `webgen.v1`               |
| `infra.provision`     | `infra.terraform`         |
| `infra.destroy`       | `infra.ansible`           |
| ... (20 total)        | ... (12 total)            |

**Unknown action/provider → REJECT** (fail-closed)

---

### B) Canonicalization & Hashing

**File:** `backend/app/modules/ir_governance/canonicalization.py`

**Functions:**
- `canonical_json(obj)` - Deterministic JSON serialization
- `sha256_hex(str)` - SHA256 hash
- `ir_hash(ir)` - Hash entire IR
- `step_hash(step)` - Hash individual step
- `compute_dag_hash(nodes)` - Hash DAG for diff-audit

**Rules:**
- Sorted keys (`sort_keys=True`)
- No whitespace (`separators=(',',':')`)
- UTF-8 encoding
- **No floats allowed** (raises TypeError)
- Control characters forbidden

**Example:**
```python
from backend.app.modules.ir_governance import ir_hash

ir = IR(tenant_id="demo", steps=[...])
hash_value = ir_hash(ir)  # Same IR → same hash (always)
```

---

### C) Deterministic Validator

**File:** `backend.app/modules/ir_governance/validator.py`

**Risk Tiers:**

| Tier | Description | Auto-Escalation Rules | Requires Approval |
|------|-------------|----------------------|-------------------|
| **Tier 0** | Read-only, no side effects | - | ❌ |
| **Tier 1** | Low risk, dev/staging only | - | ❌ |
| **Tier 2** | Medium risk | Production DNS changes, Odoo module install | ✅ |
| **Tier 3** | High risk | Destructive ops, module uninstall, accounting actions, bulk ops | ✅ |

**Auto-Escalation Rules:**
- Destructive keywords (`delete`, `destroy`, `uninstall`) → **Tier 3**
- DNS zone deletion → **Tier 3**
- Infrastructure destroy → **Tier 3**
- DNS updates → **Tier 2**
- Production environment → **Tier 2+**
- Odoo accounting/payments → **Tier 3**
- Bulk/batch operations → **Tier 3**

**Validation Status:**
- `PASS` - Safe to execute (Tier 0-1, no violations)
- `ESCALATE` - Requires approval (Tier 2+)
- `REJECT` - Cannot execute (violations detected)

**Example:**
```python
from backend.app.modules.ir_governance import get_validator

validator = get_validator()
result = validator.validate_ir(ir)

if result.status == IRValidationStatus.REJECT:
    raise Exception(f"Validation failed: {result.violations}")
elif result.status == IRValidationStatus.ESCALATE:
    # Create approval request
    ...
else:
    # Execute
    ...
```

---

### D) HITL Approvals Service

**File:** `backend/app/modules/ir_governance/approvals.py`

**Security Features:**
- **Single-use tokens** (cannot replay)
- **TTL** (default: 1 hour, configurable)
- **Token hashing** (never store raw tokens)
- **Tenant-bound** (validates tenant_id match)
- **IR hash matching** (validates ir_hash match)

**Lifecycle:**

1. **Create Approval**
   ```python
   service = get_approvals_service()
   approval, token = service.create_approval(
       tenant_id="tenant_demo",
       ir_hash="abc123...",
       ttl_seconds=3600,
   )
   # Save token - it will not be shown again!
   ```

2. **Consume Approval**
   ```python
   result = service.consume_approval(
       ApprovalConsumeRequest(
           tenant_id="tenant_demo",
           ir_hash="abc123...",
           token=saved_token,
       )
   )
   # result.success == True if valid
   ```

**Validation Checks:**
- ✅ Token exists
- ✅ Not expired
- ✅ Not already consumed
- ✅ Tenant ID matches
- ✅ IR hash matches

---

### E) Diff-Audit Gate

**File:** `backend/app/modules/ir_governance/diff_audit.py`

**Purpose:** Ensure strict mapping between IR steps and DAG nodes.

**Checks:**
- ❌ No extra DAG nodes (not in IR)
- ❌ No missing DAG nodes (IR step not in DAG)
- ❌ All hashes match exactly

**DAG Node Requirements:**
Each DAG node MUST contain:
- `ir_step_id` - Stable reference (step index or UUID)
- `ir_step_hash` - Canonical step hash

**Example:**
```python
from backend.app.modules.ir_governance import get_diff_audit_gate

gate = get_diff_audit_gate()
result = gate.audit_ir_dag_mapping(ir, dag_nodes)

if not result.success:
    # Violations detected
    logger.error(f"Missing IR steps: {result.missing_ir_steps}")
    logger.error(f"Extra DAG nodes: {result.extra_dag_nodes}")
    logger.error(f"Hash mismatches: {result.hash_mismatches}")
    raise Exception("Diff-audit failed: IR ↔ DAG mismatch")
```

---

## API Reference

### Endpoints

**Base Path:** `/api/ir`

#### 1. GET /api/ir/info

Get system information.

**Response:**
```json
{
  "name": "BRAiN IR Governance Kernel",
  "version": "1.0.0",
  "sprint": "Sprint 9 (P0)",
  "features": [...],
  "endpoints": [...]
}
```

#### 2. POST /api/ir/validate

Validate IR against policy rules.

**Request:**
```json
{
  "tenant_id": "tenant_demo",
  "intent_summary": "Deploy staging website",
  "steps": [
    {
      "action": "deploy.website",
      "provider": "deploy.provider_v1",
      "resource": "site:staging",
      "params": {...},
      "idempotency_key": "deploy-staging-001"
    }
  ]
}
```

**Response:**
```json
{
  "status": "PASS",
  "violations": [],
  "risk_tier": 1,
  "requires_approval": false,
  "ir_hash": "abc123...",
  "tenant_id": "tenant_demo",
  "request_id": "uuid"
}
```

#### 3. POST /api/ir/approvals

Create approval request.

**Query Parameters:**
- `tenant_id` (required)
- `ir_hash` (required)
- `ttl_seconds` (default: 3600)
- `created_by` (optional)

**Response:**
```json
{
  "approval_id": "uuid",
  "token": "single-use-token",  // Save this!
  "expires_at": "2025-01-01T13:00:00Z",
  "message": "Save the token - it will not be shown again."
}
```

#### 4. POST /api/ir/approvals/consume

Consume approval token.

**Request:**
```json
{
  "tenant_id": "tenant_demo",
  "ir_hash": "abc123...",
  "token": "single-use-token"
}
```

**Response:**
```json
{
  "success": true,
  "status": "consumed",
  "message": "Approval consumed successfully",
  "approval_id": "uuid"
}
```

#### 5. GET /api/ir/approvals/{approval_id}/status

Get approval status.

**Response:**
```json
{
  "approval_id": "uuid",
  "status": "pending",
  "tenant_id": "tenant_demo",
  "ir_hash": "abc123...",
  "created_at": "2025-01-01T12:00:00Z",
  "expires_at": "2025-01-01T13:00:00Z"
}
```

---

## Testing

**File:** `backend/tests/test_ir_governance.py`

**18 Comprehensive Tests:**

1. Canonicalization stable hash
2. Canonicalization different hash on change
3. Schema forbids extra fields
4. Reject missing idempotency_key
5. Reject whitespace-only idempotency_key
6. Reject unknown action
7. Reject unknown provider
8. PASS for safe Tier 0/1 IR
9. ESCALATE for Tier 2 IR
10. ESCALATE for destructive action
11. Approval token single-use
12. Approval token TTL
13. Approval tenant_id validation
14. Approval ir_hash validation
15. Diff-audit rejects extra DAG node
16. Diff-audit rejects hash mismatch
17. Diff-audit success
18. Edge case coverage

**Run Tests:**
```bash
pytest backend/tests/test_ir_governance.py -v
```

---

## Audit Events

All events logged with correlation keys (tenant_id, request_id, ir_hash).

**Validation Events:**
- `ir.validated_pass`
- `ir.validated_escalate`
- `ir.validated_reject`

**Approval Events:**
- `ir.approval_created`
- `ir.approval_consumed`
- `ir.approval_expired`
- `ir.approval_invalid`

**Diff-Audit Events:**
- `ir.dag_diff_ok`
- `ir.dag_diff_failed`

**Execution Events:**
- `ir.execution_blocked` (when gate blocks execution)

---

## Security Notes

### Fail-Closed Design
- Unknown action/provider → **REJECT**
- Invalid state → **ERROR**, not degraded behavior
- Missing fields → **REJECT**

### Token Security
- **Never log raw tokens** (only hashes)
- **Single-use** (token replay fails)
- **TTL enforcement** (expired tokens rejected)
- **Tenant-bound** (validates tenant_id)
- **IR hash matching** (validates ir_hash)

### No PII in Logs
- Token hashes only (SHA256)
- IR hashes truncated in logs (first 16 chars)
- No sensitive params logged

---

## Backwards Compatibility

**All Sprint 8 code continues to work.**

- IR governance is **opt-in** for new pipeline entrypoints
- Legacy entrypoints can continue without IR
- Feature flag: `IR_REQUIRED` (default: false for compatibility)

**Migration Path:**
1. Start with `IR_REQUIRED=false` (permissive)
2. Gradually add IR to new workflows
3. Monitor audit events
4. When confident, set `IR_REQUIRED=true` (enforce)

---

## Files Added

| File | Lines | Description |
|------|-------|-------------|
| `schemas.py` | 267 | IR, IRStep, validation models |
| `canonicalization.py` | 240 | Deterministic hashing |
| `validator.py` | 389 | Policy enforcement |
| `approvals.py` | 370 | HITL approval workflow |
| `diff_audit.py` | 157 | IR ↔ DAG integrity |
| `router.py` | 279 | FastAPI endpoints |
| `__init__.py` | 73 | Module exports |
| `test_ir_governance.py` | 540 | 18 comprehensive tests |
| **Total** | **2315** | **LOC** |

---

## Key Takeaways

✅ **Canonical IR as SSOT** - Single source of truth for all executions
✅ **Deterministic validation** - LLM-free, policy-as-code
✅ **Fail-closed everywhere** - Invalid state → error
✅ **HITL approvals** - Secure, single-use, TTL-enforced
✅ **Diff-audit gate** - IR ↔ DAG integrity guaranteed
✅ **No external dependencies** - Pure Python, no Redis required
✅ **Backwards compatible** - Sprint 8 unchanged
✅ **Auditor-ready** - Full audit trail with correlation

---

**Next:** [Implementation Report](./SPRINT9_IMPLEMENTATION_REPORT.md)
