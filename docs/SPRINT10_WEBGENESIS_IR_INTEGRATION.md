# Sprint 10: WebGenesis IR Governance Integration

**Status:** ✅ Complete
**Sprint:** Sprint 10 (P0)
**Version:** 1.0.0
**Date:** 2025-12-26
**Branch:** `claude/sprint10-webgenesis-ir-xY32y`

---

## Executive Summary

Sprint 10 successfully integrates **IR Governance** (from Sprint 9) into the **WebGenesis autonomous pipeline** with **opt-in, backwards-compatible, dry-run-first** approach.

### Core Achievement
WebGenesis can now enforce deterministic policies on autonomous website generation operations while maintaining 100% backwards compatibility with existing workflows.

### Key Principles Met
- ✅ **Opt-in:** IR is optional (mode=`opt_in`), legacy requests continue to work
- ✅ **Conservative:** Minimal changes, maximum stability, fail-closed
- ✅ **Dry-run first:** Safe by default (`WEBGENESIS_DRY_RUN_DEFAULT=true`)
- ✅ **Zero breaking changes:** All existing code works unchanged
- ✅ **Audit-ready:** Every decision logged with correlation keys

---

## Table of Contents

1. [Architecture](#architecture)
2. [Components](#components)
3. [Configuration](#configuration)
4. [API Reference](#api-reference)
5. [Request/Response Examples](#requestresponse-examples)
6. [Audit Events](#audit-events)
7. [Testing](#testing)
8. [Deployment](#deployment)
9. [Troubleshooting](#troubleshooting)

---

## Architecture

### Execution Flow (IR-enabled)

```
Client Request
    ↓
[1] IR Gateway Validation
    ├─ Mode=off → Allow (skip governance)
    ├─ Mode=opt_in + no IR → Allow (legacy)
    ├─ Mode=opt_in + IR → Validate
    └─ Mode=required + no IR → Reject
    ↓
[2] IR Validation (if IR provided)
    ├─ Status=PASS → Continue
    ├─ Status=ESCALATE → Require approval token
    └─ Status=REJECT → Block
    ↓
[3] IR → Graph Mapping
    └─ Attach ir_step_id + ir_step_hash to DAG nodes
    ↓
[4] Diff-Audit Gate
    ├─ Verify IR ↔ DAG integrity
    ├─ Detect: missing steps, extra nodes, hash mismatches
    └─ Block if any drift detected
    ↓
[5] Execution Mode Selection
    ├─ execute=false → Dry-run
    ├─ execute=true + dry_run_default=true → Dry-run
    └─ execute=true + dry_run_default=false → LIVE
    ↓
[6] ExecutionGraph.execute()
    └─ Instantiate WebGenesisNode → Generate website
    ↓
[7] Evidence Pack Generation
    ├─ Base evidence (Sprint 8)
    └─ IR evidence (Sprint 10) with governance metadata
    ↓
Response to Client
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Client (HTTP POST /api/pipeline/execute-ir)               │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│  IR Router Extension (ir_router_extension.py)              │
│  ├─ PipelineExecuteRequest validation                      │
│  └─ Orchestrates IR governance flow                        │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│  IR Gateway (ir_gateway.py)                                │
│  ├─ Check IR mode (off/opt_in/required)                    │
│  ├─ Validate IR against policy rules                       │
│  ├─ Handle ESCALATE → consume approval token               │
│  └─ Emit audit events                                      │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│  IR Mapper (ir_mapper.py)                                  │
│  ├─ Convert ExecutionGraphSpec → IR steps                  │
│  ├─ Attach IR metadata to DAG nodes                        │
│  └─ Generate deterministic idempotency keys                │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│  Diff-Audit Gate (diff_audit.py, from Sprint 9)           │
│  ├─ Verify IR ↔ DAG node mapping                           │
│  ├─ Detect missing IR steps                                │
│  ├─ Detect extra DAG nodes                                 │
│  └─ Detect hash mismatches                                 │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│  ExecutionGraph (execution_graph.py)                       │
│  ├─ Instantiate WebGenesisNode                             │
│  ├─ Execute nodes in topological order                     │
│  └─ Collect results + audit events                         │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│  WebGenesisNode (webgenesis_node.py)                       │
│  ├─ execute() → Generate website (LIVE)                    │
│  └─ dry_run() → Simulate generation (SAFE)                 │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│  IR Evidence Generator (ir_evidence.py)                    │
│  ├─ Extend base evidence with IR metadata                  │
│  ├─ Include IR hash, validation, diff-audit                │
│  └─ NO SECRETS (no raw approval tokens)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. IR Config (`ir_config.py`)

**Purpose:** Feature flags and configuration management.

**Environment Variables:**
- `WEBGENESIS_IR_MODE`: `off` | `opt_in` | `required` (default: `opt_in`)
- `WEBGENESIS_REQUIRE_APPROVAL_TIER`: Minimum tier requiring approval (default: `2`)
- `WEBGENESIS_MAX_BUDGET`: Maximum budget in cents (optional)
- `WEBGENESIS_DRY_RUN_DEFAULT`: Default dry-run mode (default: `true`)

**Key Methods:**
```python
config = get_ir_config()
config.is_ir_enabled()  # True if opt_in or required
config.is_ir_required()  # True if required
```

**Safe Defaults:**
- `opt_in` mode: Accept both IR and legacy requests
- `dry_run_default=true`: Simulation unless explicitly `execute=true`

---

### 2. IR Gateway (`ir_gateway.py`)

**Purpose:** Validate requests against IR governance rules before execution.

**Key Features:**
- **Mode-aware:** Respects `WEBGENESIS_IR_MODE` setting
- **Fail-closed:** Invalid state → block execution
- **Approval handling:** Consumes single-use tokens for ESCALATE
- **Audit-first:** All decisions logged

**Validation Flow:**
```python
gateway = get_ir_gateway()
result = gateway.validate_request(
    ir=ir,                      # Optional IR
    approval_token=token,       # Optional approval token
    legacy_request=False,       # True if no IR provided
)

if result.allowed:
    # Proceed with execution
else:
    # Block: result.block_reason explains why
```

**IRGatewayResult:**
```python
class IRGatewayResult:
    allowed: bool                          # Can proceed?
    ir: Optional[IR]                       # IR (if provided)
    validation_result: Optional[IRValidationResult]  # Validation details
    approval_result: Optional[ApprovalConsumeResult]  # Approval details
    block_reason: Optional[str]            # Why blocked (if not allowed)
    audit_events: List[Dict]               # All events for this request
```

**Decision Matrix:**

| IR Mode | IR Provided | Approval Token | Result |
|---------|-------------|----------------|--------|
| `off` | Any | Any | ✅ Allow (no governance) |
| `opt_in` | No (legacy) | N/A | ✅ Allow |
| `required` | No (legacy) | N/A | ❌ Block: "IR required" |
| `opt_in` | Yes, PASS | N/A | ✅ Allow |
| `opt_in` | Yes, REJECT | N/A | ❌ Block: "Validation failed" |
| `opt_in` | Yes, ESCALATE | No | ❌ Block: "Approval required" |
| `opt_in` | Yes, ESCALATE | Invalid | ❌ Block: "Approval invalid" |
| `opt_in` | Yes, ESCALATE | Valid | ✅ Allow (approval consumed) |

---

### 3. IR Mapper (`ir_mapper.py`)

**Purpose:** Bidirectional mapping between WebGenesis ExecutionGraphSpec and IR.

**Key Methods:**

**Graph → IR:**
```python
mapper = get_ir_mapper()
ir = mapper.graph_spec_to_ir(
    graph_spec=graph_spec,
    tenant_id="tenant_demo",
)
```

**Attach IR metadata to nodes:**
```python
modified_graph_spec = mapper.attach_ir_metadata_to_nodes(
    graph_spec=graph_spec,
    ir=ir,
)

# Now each node has:
# - executor_params["ir_step_id"]
# - executor_params["ir_step_hash"]
# - executor_params["ir_request_id"]
# - executor_params["ir_tenant_id"]
```

**Node Type → IR Action Mapping:**

| Node Type | IR Action | IR Provider |
|-----------|-----------|-------------|
| `WEBGENESIS` | `webgenesis.site.create` | `webgenesis.v1` |
| `DNS` | `dns.update_records` | `dns.hetzner` |
| `ODOO_MODULE` | `odoo.install_module` | `odoo.v16` |

**Idempotency Key Generation:**
- Format: `{graph_id}:{node_id}`
- Example: `graph_123:webgen_0`
- Deterministic and unique per execution

---

### 4. IR Evidence Pack (`ir_evidence.py`)

**Purpose:** Extend Sprint 8 evidence with IR governance metadata.

**IREvidencePack Structure:**
```python
{
    "base_evidence": {
        # Sprint 8 evidence pack
        "pack_id": "evidence_pack_123",
        "execution_result": {...},
        "artifacts": [...],
        "audit_events": [...]
    },
    "ir_enabled": true,
    "ir": {
        # Canonical IR (if IR was used)
        "tenant_id": "tenant_demo",
        "steps": [...]
    },
    "ir_hash": "abc123def456...",
    "ir_validation": {
        # IR validation result
        "status": "PASS",
        "risk_tier": 1,
        "requires_approval": false
    },
    "approval_used": false,
    "approval_id": null,       # Approval ID (if used), NO RAW TOKEN
    "diff_audit_result": {
        # Diff-audit result
        "success": true,
        "missing_ir_steps": [],
        "extra_dag_nodes": [],
        "hash_mismatches": []
    },
    "ir_summary": {
        "total_steps": 3,
        "risk_tier": 1,
        "approval_required": false,
        "validation_status": "PASS",
        "diff_audit_passed": true
    }
}
```

**Security:** NO RAW APPROVAL TOKENS ever stored in evidence packs.

---

### 5. Router Extension (`ir_router_extension.py`)

**New Endpoint:** `POST /api/pipeline/execute-ir`

**Features:**
- Backwards compatible (accepts both IR and legacy requests)
- Opt-in governance enforcement
- Dry-run-first by default
- Complete evidence pack generation

**Request Schema:**
```python
class PipelineExecuteRequest(BaseModel):
    graph_spec: ExecutionGraphSpec       # Execution graph
    tenant_id: str = "default"           # Tenant ID
    ir: Optional[IR] = None              # Optional IR for governance
    approval_token: Optional[str] = None  # Approval token (if ESCALATE)
    execute: bool = False                # Execute (true) or dry-run (false)
```

---

## Configuration

### Environment Variables

Add to `.env` or `.env.example`:

```bash
#############################################
# WEBGENESIS IR GOVERNANCE (Sprint 10)
#############################################

# IR enforcement mode: off | opt_in | required
# - off: IR disabled, legacy behavior (no governance)
# - opt_in: IR optional, accept both IR and legacy requests (DEFAULT)
# - required: IR mandatory, block legacy requests (fail-closed)
WEBGENESIS_IR_MODE=opt_in

# Minimum risk tier requiring approval (0-3)
# Tier 0: Safe, read-only (no approval)
# Tier 1: Low risk, dev/staging (no approval)
# Tier 2: Medium risk, requires approval (DEFAULT)
# Tier 3: High risk, critical operations (requires approval)
WEBGENESIS_REQUIRE_APPROVAL_TIER=2

# Maximum budget in cents (optional, leave empty for unlimited)
# Example: 500000 = $5000.00
WEBGENESIS_MAX_BUDGET=

# Default dry-run mode (true recommended for safety)
# true: Default to simulation, require explicit execute=true (DEFAULT)
# false: Default to live execution (NOT RECOMMENDED)
WEBGENESIS_DRY_RUN_DEFAULT=true
```

### Deployment Modes

**Development (Permissive):**
```bash
WEBGENESIS_IR_MODE=opt_in
WEBGENESIS_DRY_RUN_DEFAULT=true
WEBGENESIS_REQUIRE_APPROVAL_TIER=3  # Only critical ops need approval
```

**Staging (Testing IR):**
```bash
WEBGENESIS_IR_MODE=opt_in
WEBGENESIS_DRY_RUN_DEFAULT=true
WEBGENESIS_REQUIRE_APPROVAL_TIER=2  # Medium+ needs approval
```

**Production (Strict):**
```bash
WEBGENESIS_IR_MODE=required        # Force IR
WEBGENESIS_DRY_RUN_DEFAULT=true    # Force dry-run by default
WEBGENESIS_REQUIRE_APPROVAL_TIER=1  # Low+ needs approval
WEBGENESIS_MAX_BUDGET=1000000      # $10,000 budget limit
```

---

## API Reference

### GET `/api/pipeline/ir/config`

Get current IR configuration.

**Response:**
```json
{
    "ir_mode": "opt_in",
    "require_approval_tier": 2,
    "max_budget_cents": null,
    "dry_run_default": true,
    "is_ir_enabled": true,
    "is_ir_required": false
}
```

---

### POST `/api/pipeline/execute-ir`

Execute pipeline with IR governance.

**Request (with IR):**
```json
{
    "graph_spec": {
        "graph_id": "graph_123",
        "business_intent_id": "intent_abc",
        "nodes": [
            {
                "node_id": "webgen_0",
                "node_type": "webgenesis",
                "depends_on": [],
                "capabilities": [],
                "executor_class": "WebGenesisNode",
                "executor_params": {
                    "website_template": "nextjs-business",
                    "domain": "example.com",
                    "title": "My Business",
                    "pages": ["home", "about", "contact"]
                }
            }
        ],
        "dry_run": false
    },
    "tenant_id": "tenant_demo",
    "ir": {
        "tenant_id": "tenant_demo",
        "steps": [
            {
                "action": "webgenesis.site.create",
                "provider": "webgenesis.v1",
                "resource": "site:example.com",
                "params": {
                    "website_template": "nextjs-business",
                    "domain": "example.com",
                    "title": "My Business"
                },
                "idempotency_key": "graph_123:webgen_0"
            }
        ]
    },
    "approval_token": null,
    "execute": false
}
```

**Request (legacy, no IR):**
```json
{
    "graph_spec": { ...same as above... },
    "tenant_id": "tenant_demo",
    "execute": false
}
```

**Response:**
```json
{
    "execution_result": {
        "graph_id": "graph_123",
        "status": "completed",
        "success": true,
        "was_dry_run": true,
        "duration_seconds": 1.23,
        "artifacts": ["sim_website_123.html"],
        "audit_events": [...]
    },
    "base_evidence": {
        "pack_id": "evidence_pack_graph_123_1703001234",
        "...": "..."
    },
    "ir_evidence": {
        "ir_enabled": true,
        "ir_hash": "abc123def456...",
        "ir_validation": {
            "status": "PASS",
            "risk_tier": 1
        },
        "diff_audit_result": {
            "success": true
        }
    },
    "gateway_result": {
        "allowed": true,
        "validation_status": "PASS"
    },
    "diff_audit_result": {
        "success": true,
        "missing_ir_steps": [],
        "extra_dag_nodes": [],
        "hash_mismatches": []
    },
    "execution_mode": {
        "is_dry_run": true,
        "execute_requested": false,
        "config_dry_run_default": true
    }
}
```

---

## Request/Response Examples

### Example 1: Dry-run with IR (PASS)

**curl:**
```bash
curl -X POST http://localhost:8000/api/pipeline/execute-ir \
  -H "Content-Type: application/json" \
  -d '{
    "graph_spec": {
        "graph_id": "test_graph",
        "business_intent_id": "intent_001",
        "nodes": [{
            "node_id": "webgen_0",
            "node_type": "webgenesis",
            "depends_on": [],
            "capabilities": [],
            "executor_class": "WebGenesisNode",
            "executor_params": {
                "website_template": "static-landing",
                "domain": "dev.example.com",
                "title": "Dev Site"
            }
        }]
    },
    "tenant_id": "tenant_demo",
    "ir": {
        "tenant_id": "tenant_demo",
        "steps": [{
            "action": "webgenesis.site.create",
            "provider": "webgenesis.v1",
            "resource": "site:dev.example.com",
            "params": {},
            "idempotency_key": "test_graph:webgen_0",
            "constraints": {"env": "dev"}
        }]
    },
    "execute": false
}'
```

**Expected:** Status 200, dry-run executed, IR validation PASS.

---

### Example 2: Execute with approval (ESCALATE)

**Step 1:** Validate IR (will get ESCALATE)
```bash
curl -X POST http://localhost:8000/api/ir/validate \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant_demo",
    "steps": [{
        "action": "webgenesis.site.create",
        "provider": "webgenesis.v1",
        "resource": "site:example.com",
        "params": {},
        "idempotency_key": "test_escalate",
        "constraints": {"env": "production"}
    }]
}'
```

**Response:** `{"status": "ESCALATE", "ir_hash": "abc123...", ...}`

**Step 2:** Create approval
```bash
curl -X POST "http://localhost:8000/api/ir/approvals?tenant_id=tenant_demo&ir_hash=abc123..."
```

**Response:** `{"approval_id": "approval_xxx", "token": "TOKEN_HERE", ...}`

**Step 3:** Execute with token
```bash
curl -X POST http://localhost:8000/api/pipeline/execute-ir \
  -H "Content-Type: application/json" \
  -d '{
    "graph_spec": {...},
    "tenant_id": "tenant_demo",
    "ir": {...},
    "approval_token": "TOKEN_HERE",
    "execute": true
}'
```

**Expected:** Status 200, execution allowed, approval consumed.

---

### Example 3: Legacy request (no IR)

**curl:**
```bash
curl -X POST http://localhost:8000/api/pipeline/execute-ir \
  -H "Content-Type: application/json" \
  -d '{
    "graph_spec": {...},
    "tenant_id": "tenant_demo",
    "execute": false
}'
```

**Expected:** Status 200, legacy request allowed (if `IR_MODE=opt_in`).

---

## Audit Events

### WebGenesis-specific Events

| Event Type | Trigger | Fields |
|------------|---------|--------|
| `webgenesis.ir_disabled` | IR mode=off | message |
| `webgenesis.ir_required_violation` | Legacy request when mode=required | message |
| `webgenesis.ir_legacy_allowed` | Legacy request when mode=opt_in | message |
| `webgenesis.ir_received` | IR received | tenant_id, request_id, ir_hash, step_count |
| `webgenesis.ir_validated_pass` | IR validation PASS | tenant_id, ir_hash, risk_tier |
| `webgenesis.ir_validated_escalate` | IR validation ESCALATE | tenant_id, ir_hash, risk_tier |
| `webgenesis.ir_validated_reject` | IR validation REJECT | tenant_id, ir_hash, violations |
| `webgenesis.ir_approval_required` | ESCALATE without token | tenant_id, ir_hash |
| `webgenesis.ir_approval_consumed` | Approval token consumed | tenant_id, ir_hash, approval_id |
| `webgenesis.ir_approval_invalid` | Invalid approval token | tenant_id, ir_hash, status, message |
| `webgenesis.dag_compiled` | DAG compiled from graph spec | graph_id, node_count |
| `webgenesis.diff_audit_pass` | Diff-audit successful | tenant_id, ir_hash, dag_hash |
| `webgenesis.diff_audit_fail` | Diff-audit failed | tenant_id, ir_hash, missing_steps, extra_nodes |
| `webgenesis.dry_run_completed` | Dry-run completed | graph_id, node_count |
| `webgenesis.execute_blocked` | Execution blocked by governance | tenant_id, ir_hash, reason |
| `webgenesis.execute_started` | LIVE execution started | graph_id, tenant_id |
| `webgenesis.execute_completed` | Execution completed | graph_id, success, duration |

**Example Audit Event:**
```json
{
    "event_type": "webgenesis.ir_validated_pass",
    "timestamp": "2025-12-26T12:00:00Z",
    "tenant_id": "tenant_demo",
    "request_id": "uuid",
    "ir_hash": "abc123def456...",
    "risk_tier": 1
}
```

---

## Testing

### Run All Tests

```bash
pytest backend/tests/test_sprint10_webgenesis_ir.py -v
```

### Test Coverage (13 tests)

1. ✅ opt-in mode allows legacy requests
2. ✅ required mode blocks legacy requests
3. ✅ IR PASS allows execution
4. ✅ IR REJECT blocks execution
5. ✅ IR ESCALATE without approval blocks
6. ✅ IR ESCALATE with valid approval allows
7. ✅ Diff-audit rejects extra DAG node
8. ✅ Evidence pack contains required fields (no secrets)
9. ✅ execute=false → dry-run (no side effects)
10. ✅ execute=true → execution path called
11. ✅ Graph spec to IR mapping works
12. ✅ IR metadata attached to DAG nodes
13. ✅ Config dry_run_default enforced

**Expected Result:** All tests PASS.

---

## Deployment

### Migration Path

**Phase 1: Deploy Sprint 10 (Opt-In)**
```bash
# .env
WEBGENESIS_IR_MODE=opt_in
WEBGENESIS_DRY_RUN_DEFAULT=true

# Deploy
docker compose build backend
docker compose up -d backend

# Test
curl http://localhost:8000/api/pipeline/ir/config
```

**Phase 2: Monitor Audit Events (1-2 weeks)**
```bash
# Check audit events
docker compose logs -f backend | grep "webgenesis.ir"
```

**Phase 3: Enable Required Mode (After confidence)**
```bash
# .env
WEBGENESIS_IR_MODE=required  # Force IR for all new requests

# Redeploy
docker compose restart backend
```

---

## Troubleshooting

### Issue 1: Legacy request blocked unexpectedly

**Symptom:** Legacy request returns 403 "IR required".

**Solution:** Check `WEBGENESIS_IR_MODE`:
```bash
curl http://localhost:8000/api/pipeline/ir/config
# Should show: "ir_mode": "opt_in" (not "required")
```

**Fix:**
```bash
# In .env
WEBGENESIS_IR_MODE=opt_in

# Restart
docker compose restart backend
```

---

### Issue 2: Approval token rejected

**Symptom:** 403 "Approval failed: Tenant ID mismatch".

**Solution:** Ensure IR `tenant_id` matches approval creation:
```bash
# IR tenant_id must match
ir.tenant_id == approval.tenant_id
```

---

### Issue 3: Diff-audit fails with hash mismatch

**Symptom:** 400 "Diff-audit failed: hash mismatch".

**Root Cause:** IR was modified after mapping to DAG.

**Solution:** Ensure IR is frozen (not modified) after initial mapping:
```python
# ❌ BAD
ir = mapper.graph_spec_to_ir(graph_spec)
ir.steps[0].params["new_field"] = "value"  # Modifies IR → hash changes!

# ✅ GOOD
ir = mapper.graph_spec_to_ir(graph_spec)
# Don't modify IR after mapping
```

---

### Issue 4: Dry-run forced even with execute=true

**Symptom:** `execute=true` but result shows `was_dry_run=true`.

**Root Cause:** `WEBGENESIS_DRY_RUN_DEFAULT=true` overrides `execute` flag.

**Solution (if intentional):** This is the safe default. To allow live execution:
```bash
# In .env (NOT RECOMMENDED for production)
WEBGENESIS_DRY_RUN_DEFAULT=false

# Restart
docker compose restart backend
```

---

## Backwards Compatibility Statement

**Sprint 10 is 100% backwards compatible with all existing BRAiN code:**

✅ **Legacy endpoints work unchanged:**
- `/api/pipeline/execute` continues to work (no IR)
- `/api/pipeline/dry-run` continues to work (no IR)
- All Sprint 8 functionality preserved

✅ **Opt-in by default:**
- `WEBGENESIS_IR_MODE=opt_in` accepts both IR and legacy requests
- Legacy requests bypass IR governance entirely

✅ **No schema changes:**
- Existing `ExecutionGraphSpec` models unchanged
- IR fields are optional additions

✅ **Fail-safe defaults:**
- `dry_run_default=true`: Safe by default
- `opt_in` mode: Permissive by default
- All guard rails are opt-in, not forced

**Migration is zero-risk:** Deploy Sprint 10 with no code changes required in existing systems.

---

## Key Takeaways

1. **IR Governance is opt-in:** Legacy workflows continue unchanged
2. **Dry-run first:** Safe by default (`WEBGENESIS_DRY_RUN_DEFAULT=true`)
3. **Fail-closed when enabled:** Invalid IR → block execution
4. **Approval workflow:** ESCALATE requires single-use token
5. **Diff-audit enforced:** IR ↔ DAG integrity verified
6. **Evidence packs:** Complete audit trail (no secrets)
7. **13 comprehensive tests:** Exceed 10+ requirement
8. **Zero breaking changes:** 100% backwards compatible

---

**Sprint 10 Status:** ✅ **COMPLETE**

**Next Steps:**
1. Deploy to staging
2. Monitor audit events for 24-48 hours
3. Consider enabling `required` mode after confidence
4. Sprint 11: HITL Approvals UI + Redis backend

---

**END OF TECHNICAL DOCUMENTATION**
