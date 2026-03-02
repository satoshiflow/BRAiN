# Sprint 9-B: Run Contracts & Deterministic Replay

**Version:** 1.0.0
**Sprint:** Sprint 9-B
**Status:** ✅ Complete
**Author:** BRAiN Development Team

---

## Overview

**Run Contracts** provide immutable, cryptographically verifiable snapshots of every pipeline execution. They enable legal proof, deterministic replay, and audit compliance.

**Core Principle:** Every run becomes legally & technically provable.

---

## Key Features

### 1. Immutable Run Snapshot

Every pipeline run creates a `RunContract` containing:

- **Input**: Business intent (original + resolved)
- **Graph**: Execution DAG specification
- **Policy**: Budget & governance rules applied
- **Result**: Execution outcome (after completion)
- **Hashes**: SHA256 cryptographic verification

### 2. Deterministic Hashing

All hashes are computed deterministically:

```python
input_hash    → SHA256(business_intent_input + resolved_intent)
graph_hash    → SHA256(execution_graph_spec)
policy_hash   → SHA256(execution_policy)
contract_hash → SHA256(contract_id + input_hash + graph_hash + policy_hash)
```

**Determinism Requirements:**
- Sort all JSON keys (`sort_keys=True`)
- Exclude timestamps and generated IDs
- Include only stable, deterministic fields
- Sort lists before hashing (e.g., `sorted(odoo_modules_required)`)

### 3. Deterministic Replay API

Replay any past execution from its contract:

```bash
POST /api/pipeline/replay/{contract_id}
```

**Replay Process:**
1. Load contract from storage
2. Verify contract integrity (recompute hashes)
3. Re-execute graph in **dry-run mode** (no side effects)
4. Compare results with original execution
5. Create new replay contract (linked to original)

**Safety:** Replays are ALWAYS dry-run only.

### 4. Evidence Pack Integration

Evidence packs now include run contracts:

```json
{
  "pack_id": "evidence_pack_xyz",
  "run_contract": { ... },
  "contract_id": "contract_1703001234000_graph_abc",
  "execution_result": { ... },
  "summary": { ... }
}
```

Contracts are also saved separately as `{contract_id}.json` for easier access.

---

## Architecture

### RunContract Schema

```python
class RunContract(BaseModel):
    # Identity
    contract_id: str  # "contract_{timestamp_ms}_{graph_id}"
    created_at: datetime

    # Input snapshot
    business_intent_input: Optional[BusinessIntentInput]
    resolved_intent: Optional[ResolvedBusinessIntent]

    # Graph snapshot
    graph_spec: ExecutionGraphSpec

    # Policy snapshot
    policy: Optional[ExecutionPolicy]

    # Results (filled after execution)
    result: Optional[ExecutionGraphResult]

    # Hashes (deterministic verification)
    input_hash: str    # SHA256 of business intent
    graph_hash: str    # SHA256 of execution graph
    policy_hash: str   # SHA256 of execution policy
    contract_hash: str # SHA256 of entire contract

    # Metadata
    dry_run: bool
    replay_of: Optional[str]  # Contract ID if this is a replay
```

### Contract Lifecycle

```
┌─────────────────────────────┐
│ 1. Create Contract          │
│    (before execution)       │
│    - Generate contract_id   │
│    - Compute input_hash     │
│    - Compute graph_hash     │
│    - Compute policy_hash    │
│    - Compute contract_hash  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 2. Execute Pipeline         │
│    (actual work)            │
│    - Run nodes              │
│    - Collect results        │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 3. Finalize Contract        │
│    (after execution)        │
│    - Add execution result   │
│    - Recompute contract_hash│
│    - Save to storage        │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 4. Contract Stored          │
│    - storage/run_contracts/ │
│    - {contract_id}.json     │
│    - Immutable              │
│    - Verifiable             │
└─────────────────────────────┘
```

---

## API Usage

### Create and Execute with Contract

```python
from backend.app.modules.autonomous_pipeline.run_contract import get_run_contract_service
from backend.app.modules.autonomous_pipeline.execution_graph import create_execution_graph

# Create run contract
run_contract_service = get_run_contract_service()
run_contract = run_contract_service.create_contract(
    graph_spec=graph_spec,
    business_intent_input=intent_input,
    resolved_intent=resolved_intent,
    policy=policy,
    dry_run=False,
)

# Execute graph
graph = create_execution_graph(graph_spec)
result = await graph.execute()

# Finalize contract with result
run_contract = run_contract_service.finalize_contract(run_contract, result)

# Save contract
contract_path = run_contract_service.save_contract(run_contract)

print(f"Contract saved: {contract_path}")
print(f"Contract hash: {run_contract.contract_hash}")
```

### Verify Contract Integrity

```python
# Load contract
contract = run_contract_service.load_contract("contract_1703001234000_graph_abc")

# Verify integrity (recompute all hashes)
is_valid = run_contract_service.verify_contract(contract)

if is_valid:
    print("✅ Contract is valid and untampered")
else:
    print("❌ Contract verification FAILED - possible tampering")
```

### Replay Contract (API)

```bash
POST /api/pipeline/replay/contract_1703001234000_graph_abc

# Response:
{
  "replay_result": { ... },           # New execution result
  "original_result": { ... },         # Original execution result
  "contract_verified": true,
  "hashes_match": true,
  "replay_contract_id": "contract_1703001235000_replay_graph_abc",
  "original_contract_id": "contract_1703001234000_graph_abc",
  "replay_path": "/path/to/replay_contract.json",
  "message": "Replay successful. Graph hashes match."
}
```

---

## Deterministic Hashing Implementation

### Why Determinism Matters

For legal and audit purposes, contract hashes must be **reproducible**:

- Same input → Same hash (always)
- Different input → Different hash (guaranteed)
- Tampering detection (any change breaks hash)

### How We Achieve It

1. **Sort JSON keys** when serializing:
   ```python
   json.dumps(hash_content, sort_keys=True)
   ```

2. **Exclude non-deterministic fields**:
   ```python
   # ✅ GOOD: Only hash deterministic fields
   hash_content = {
       "business_type": resolved_dict.get("business_type"),
       "monetization_type": resolved_dict.get("monetization_type"),
       "odoo_modules_required": sorted(resolved_dict.get("odoo_modules_required", [])),
   }

   # ❌ BAD: Including timestamps breaks determinism
   hash_content = {
       "created_at": datetime.utcnow(),  # Changes every time!
       ...
   }
   ```

3. **Sort lists** before hashing:
   ```python
   "odoo_modules_required": sorted(odoo_modules_required)
   ```

4. **Use SHA256** for cryptographic strength:
   ```python
   hashlib.sha256(hash_json.encode("utf-8")).hexdigest()
   ```

---

## Testing

### Test: Deterministic Hashing

```python
def test_contract_deterministic_hashing():
    service = RunContractService()

    graph_spec = ExecutionGraphSpec(
        graph_id="test_graph",
        business_intent_id="test_intent",
        nodes=[],
        dry_run=True,
    )

    # Create two contracts with same spec
    contract1 = service.create_contract(graph_spec=graph_spec, dry_run=True)
    contract2 = service.create_contract(graph_spec=graph_spec, dry_run=True)

    # Graph hashes should match (deterministic)
    assert contract1.graph_hash == contract2.graph_hash
    assert contract1.policy_hash == contract2.policy_hash
```

### Test: Contract Verification

```python
def test_contract_verification():
    service = RunContractService()

    contract = service.create_contract(graph_spec=graph_spec, dry_run=True)

    # Verify contract
    is_valid = service.verify_contract(contract)
    assert is_valid is True
```

### Test: Tampering Detection

```python
def test_contract_tampering_detection():
    service = RunContractService()

    contract = service.create_contract(graph_spec=graph_spec, dry_run=True)

    # Tamper with contract
    contract.dry_run = False  # Change field

    # Verification should fail
    is_valid = service.verify_contract(contract)
    assert is_valid is False
```

---

## Storage

Contracts are stored in:

```
storage/
└── run_contracts/
    ├── contract_1703001234000_graph_abc.json
    ├── contract_1703001235000_graph_def.json
    └── contract_1703001236000_replay_graph_abc.json (replay)
```

Each contract is a complete, self-contained JSON file with all information needed for verification and replay.

---

## Use Cases

### 1. Legal Proof

**Scenario:** Customer disputes that a deployment occurred.

**Solution:**
1. Load run contract: `contract_1703001234000_deploy_prod`
2. Verify integrity: `verify_contract(contract)`
3. Show cryptographic hash: `contract.contract_hash`
4. Provide evidence pack with contract

**Result:** Immutable proof of what was executed, when, and with what result.

### 2. Bug Reproduction

**Scenario:** Pipeline failed mysteriously in production.

**Solution:**
1. Find failed contract: `contract_1703001234000_graph_failed`
2. Replay in dry-run: `POST /api/pipeline/replay/{contract_id}`
3. Analyze replay results
4. Compare with original execution

**Result:** Exact reproduction of failure for debugging.

### 3. Compliance Audit

**Scenario:** Auditor needs proof of governance compliance.

**Solution:**
1. Provide evidence pack
2. Show run contract with policy applied
3. Verify contract integrity
4. Prove no tampering (hash verification)

**Result:** Auditor-ready evidence with cryptographic guarantees.

---

## Files

| File | Description |
|------|-------------|
| `run_contract.py` | RunContract schema and service |
| `router.py` | Replay API endpoint |
| `evidence_generator.py` | Integration with evidence packs |

---

## Key Takeaways

✅ **Every run has a contract** – No execution without audit trail
✅ **Deterministic hashing** – Same input → Same hash (reproducible)
✅ **Cryptographically verifiable** – SHA256 hashes detect tampering
✅ **Deterministic replay** – Reproduce any past execution (dry-run only)
✅ **Legal proof** – Immutable evidence for compliance and disputes
✅ **Integrated with evidence packs** – Contract saved alongside evidence

---

**Previous:** [Sprint 9-A: Governance](./SPRINT9_GOVERNANCE.md)
**Next:** [Sprint 9-C: Multi-Tenancy](./SPRINT9_MULTI_TENANCY.md)
