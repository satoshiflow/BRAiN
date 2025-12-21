# Credit System v2.0

## Phase 2: Multi-Agent Credit & Selection System

**Version:** 2.0.0
**Status:** Production Ready
**Specification:** `docs/specs/brain_credit_selection_spec.v1.yaml`

---

## Overview

The BRAIN Credit System implements a deterministic, auditable resource allocation framework treating computational resources as "energy" rather than currency. It provides:

- **Append-Only Ledger**: Immutable transaction history with cryptographic signatures
- **Deterministic Calculator**: Pure function credit calculations
- **Entity Lifecycle Management**: Agent creation, existence tax, auto-suspension
- **Complete Auditability**: Every transaction and state change is logged

---

## Core Philosophy

### Credits as Energy

Credits represent the right to consume system resources:
- **CC** (Compute Credits): CPU and memory
- **LC** (LLM Credits): Language model tokens
- **SC** (Storage Credits): Persistent storage
- **NC** (Network Credits): Network I/O and external APIs

### Security Principles

1. **No Manual Minting**: Credits can only be created by system-defined rules
2. **Append-Only**: Transactions cannot be modified or deleted
3. **Fail-Closed**: Ambiguous states result in denial, never approval
4. **Complete Audit**: Every action is traceable and signed

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Credits Service                         │
│  (High-level orchestration)                                 │
└──────────────┬────────────────┬─────────────────┬───────────┘
               │                │                 │
       ┌───────▼──────┐  ┌─────▼──────┐  ┌──────▼────────┐
       │   Ledger     │  │ Calculator │  │  Lifecycle    │
       │  Service     │  │            │  │   Manager     │
       └──────┬───────┘  └────────────┘  └───────────────┘
              │
       ┌──────▼─────────────────────────────────────────────┐
       │          PostgreSQL Database                        │
       │  - credit_ledger (append-only)                     │
       │  - agent_registry (lifecycle tracking)             │
       │  - audit_trail (comprehensive logging)             │
       └─────────────────────────────────────────────────────┘
```

---

## Components

### 1. Credit Ledger (`ledger.py`)

**Purpose:** Append-only transaction log

**Key Features:**
- Cryptographic signatures (HMAC-SHA256)
- Monotonic sequence numbers
- Prevents negative balances
- Automatic audit trail creation

**API:**
```python
ledger = CreditLedgerService(session, signing_key)

# Mint credits (system only)
tx = await ledger.mint_credits(
    entity_id="agent_001",
    entity_type=EntityType.AGENT,
    credit_type=CreditType.COMPUTE_CREDITS,
    amount=Decimal("1000.0"),
    reason="Agent creation",
)

# Burn credits (spend)
tx = await ledger.burn_credits(
    entity_id="agent_001",
    entity_type=EntityType.AGENT,
    credit_type=CreditType.COMPUTE_CREDITS,
    amount=Decimal("50.0"),
    reason="LLM API call",
)

# Get balance
balance = await ledger.get_balance("agent_001", CreditType.COMPUTE_CREDITS)
```

### 2. Credit Calculator (`calculator.py`)

**Purpose:** Deterministic credit calculations

**Key Features:**
- Pure functions (no side effects)
- Deterministic (same inputs → same outputs)
- Configurable rules
- Comprehensive error handling

**Rules Implemented:**
- `AGENT_CREATION_MINT`: 1000 CC on creation
- `AGENT_EXISTENCE_TAX`: 5 CC per hour active
- `LLM_CALL_COST`: 0.001 LC per token
- `STORAGE_USAGE_TAX`: 0.1 SC per MB per day
- `MISSION_COMPLETION_REWARD`: 50 CC × priority multiplier

**API:**
```python
calculator = CreditCalculator()

context = CalculationContext(
    entity_id="agent_001",
    entity_type=EntityType.AGENT,
    timestamp=datetime.now(timezone.utc),
    agent_status=AgentStatus.ACTIVE,
    hours_active=Decimal("2.5"),
)

result = calculator.calculate_existence_tax(context)
# result.amount = 12.5 CC (5 CC/hour × 2.5 hours)
```

### 3. Entity Lifecycle Manager (`lifecycle.py`)

**Purpose:** Manage agent lifecycle with credit integration

**Key Features:**
- Agent creation with initial credits
- State transitions (ACTIVE → SUSPENDED → TERMINATED)
- Existence tax collection
- Auto-suspension on low credits
- Auto-termination after prolonged suspension

**Lifecycle States:**
```
CREATED → ACTIVE → SUSPENDED → TERMINATED
          ↑          ↓
          └──────────┘
```

**API:**
```python
lifecycle = EntityLifecycleManager(session, ledger, calculator)

# Create agent
agent = await lifecycle.create_agent(
    agent_name="coder_001",
    agent_type="CODER",
)

# Collect existence tax
stats = await lifecycle.collect_existence_tax_batch()
# stats = {
#     "total_agents": 10,
#     "collected": 8,
#     "suspended": 2,
#     "total_cc": "50.0",
# }
```

### 4. Credits Service (`service.py`)

**Purpose:** High-level business logic layer

**API:**
```python
service = CreditsService(session, signing_key)

# Get balance
balance = await service.get_balance("agent_001")

# Create agent
agent = await service.create_agent("coder_001", "CODER")

# Spend credits
tx = await service.spend_credits(
    entity_id="agent_001",
    entity_type=EntityType.AGENT,
    credit_type=CreditType.LLM_CREDITS,
    amount=Decimal("5.0"),
    reason="LLM API call (5000 tokens)",
)

# Transfer credits
burn_tx, mint_tx = await service.transfer_credits(
    from_entity_id="agent_001",
    from_entity_type=EntityType.AGENT,
    to_entity_id="agent_002",
    to_entity_type=EntityType.AGENT,
    credit_type=CreditType.COMPUTE_CREDITS,
    amount=Decimal("100.0"),
    reason="Resource sharing",
)
```

---

## REST API

**Base Path:** `/api/credits/v2`

### System Endpoints

```http
GET /health
GET /info
```

### Balance & Ledger

```http
GET /balance/{entity_id}
GET /ledger/{entity_id}?credit_type=CC&limit=100&offset=0
```

### Agent Management

```http
POST /agents
{
  "entity_id": "coder_001",
  "entity_type": "AGENT",
  "allocation_reason": "Create new agent",
  "metadata": {
    "agent_name": "coder_001",
    "agent_type": "CODER"
  }
}
```

### Credit Transactions

```http
POST /spend
{
  "entity_id": "agent_001",
  "credit_type": "LC",
  "amount": "5.0",
  "reason": "LLM API call",
  "metadata": {"tokens": 5000}
}

POST /transfer
{
  "from_entity_id": "agent_001",
  "to_entity_id": "agent_002",
  "credit_type": "CC",
  "amount": "100.0",
  "reason": "Resource sharing",
  "metadata": {}
}
```

### Tax & Lifecycle (Admin)

```http
POST /tax/collect
POST /tax/auto-terminate
```

---

## Database Schema

### credit_ledger

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| sequence_number | BIGSERIAL | Monotonic sequence |
| timestamp | TIMESTAMPTZ | Transaction time |
| entity_id | VARCHAR(255) | Entity ID |
| entity_type | VARCHAR(50) | AGENT, MISSION, SYSTEM |
| credit_type | VARCHAR(50) | CC, LC, SC, NC |
| amount | NUMERIC(20,6) | Transaction amount |
| balance_after | NUMERIC(20,6) | Balance after transaction |
| transaction_type | VARCHAR(50) | MINT, BURN, TRANSFER, TAX |
| reason | TEXT | Human-readable reason |
| metadata | JSONB | Additional context |
| signature | VARCHAR(255) | Cryptographic signature |

**Constraints:**
- Append-only (no UPDATE or DELETE)
- CHECK constraints on enums
- Unique sequence_number

### agent_registry

| Column | Type | Description |
|--------|------|-------------|
| agent_id | UUID | Primary key |
| agent_name | VARCHAR(255) | Unique agent name |
| agent_type | VARCHAR(100) | Agent type |
| status | VARCHAR(50) | ACTIVE, SUSPENDED, TERMINATED |
| created_at | TIMESTAMPTZ | Creation time |
| activated_at | TIMESTAMPTZ | Activation time |
| suspended_at | TIMESTAMPTZ | Suspension time |
| terminated_at | TIMESTAMPTZ | Termination time |
| last_activity_at | TIMESTAMPTZ | Last activity |
| credit_balance_cc | NUMERIC(20,6) | Cached CC balance |
| credit_balance_lc | NUMERIC(20,6) | Cached LC balance |
| credit_balance_sc | NUMERIC(20,6) | Cached SC balance |
| credit_balance_nc | NUMERIC(20,6) | Cached NC balance |
| total_credits_earned | NUMERIC(20,6) | Lifetime earned |
| total_credits_spent | NUMERIC(20,6) | Lifetime spent |
| metadata | JSONB | Additional metadata |

### audit_trail

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| timestamp | TIMESTAMPTZ | Event time |
| event_type | VARCHAR(100) | Event type |
| entity_id | VARCHAR(255) | Entity ID |
| entity_type | VARCHAR(50) | Entity type |
| actor_id | VARCHAR(255) | Who/what triggered event |
| action | TEXT | Human-readable description |
| result | VARCHAR(50) | SUCCESS, FAILURE, DENIED |
| metadata | JSONB | Additional context |
| signature | VARCHAR(255) | Event signature |

---

## Testing

### Unit Tests

```bash
pytest backend/tests/test_credit_calculator.py -v
```

**Coverage:**
- Deterministic calculations
- Edge cases (negative values, zero amounts)
- Rule enforcement

### Integration Tests

```bash
pytest backend/tests/test_credit_system_integration.py -v
```

**Coverage:**
- End-to-end workflows
- Multi-component interactions
- Database transactions
- Error handling

### Running All Tests

```bash
pytest backend/tests/test_credit*.py -v --cov=backend/app/modules/credits
```

---

## Deployment

### 1. Apply Migrations

```bash
cd backend
alembic upgrade head
```

This creates:
- `credit_ledger` table
- `agent_registry` table
- `audit_trail` table
- All indexes and constraints

### 2. Configure Signing Key

**Production:** Set environment variable
```bash
export CREDIT_SIGNING_KEY="your-secure-random-key-here"
```

**Development:** Uses default (insecure) key

### 3. Start Services

The credit system is automatically available via FastAPI auto-discovery.

### 4. Verify Deployment

```bash
curl http://localhost:8000/api/credits/v2/info
```

Expected response:
```json
{
  "name": "brain.credits.v2",
  "version": "2.0.0",
  "config": {
    "features": [
      "append_only_ledger",
      "deterministic_calculator",
      "existence_tax",
      "auto_suspension",
      "audit_trail"
    ],
    "spec_version": "1.0.0"
  }
}
```

---

## Operational Tasks

### Collect Existence Tax (Hourly Cron)

```bash
curl -X POST http://localhost:8000/api/credits/v2/tax/collect
```

Recommended: Run hourly via cron or systemd timer.

### Check Auto-Termination (Daily Cron)

```bash
curl -X POST http://localhost:8000/api/credits/v2/tax/auto-terminate
```

Recommended: Run daily via cron or systemd timer.

### Verify Ledger Integrity

```python
from backend.app.modules.credits.ledger import CreditLedgerService

ledger = CreditLedgerService(session, signing_key)
result = await ledger.verify_ledger_integrity(limit=10000)

if not result["integrity_ok"]:
    print(f"Integrity errors: {result['signature_errors']}")
```

---

## Monitoring

### Key Metrics

- **Credit Balance Distribution**: Monitor agent balances
- **Transaction Volume**: Transactions per hour
- **Tax Collection**: Credits collected per tax cycle
- **Suspension Rate**: Agents suspended due to low credits
- **Ledger Size**: Growth rate of ledger table

### Alerts

1. **Low Balance Alert**: Agent balance < 50 CC
2. **High Suspension Rate**: >10% agents suspended
3. **Ledger Integrity Failure**: Signature verification fails
4. **Tax Collection Failure**: Tax cron job fails

---

## Security Considerations

### Threat Model

1. **Manual Credit Minting**: Prevented by ledger constraints
2. **Negative Balance Exploit**: Prevented by balance checks
3. **Ledger Tampering**: Detected by signature verification
4. **Replay Attacks**: Prevented by sequence numbers

### Best Practices

1. **Signing Key**: Use strong random key in production
2. **Database Permissions**: Restrict UPDATE/DELETE on ledger
3. **API Authentication**: Require auth for all endpoints
4. **Audit Retention**: Keep audit trail for compliance

---

## Troubleshooting

### Agent Suspended Unexpectedly

**Symptoms:** Agent status = SUSPENDED

**Diagnosis:**
```sql
SELECT * FROM credit_ledger
WHERE entity_id = 'agent_id'
ORDER BY sequence_number DESC
LIMIT 10;
```

**Solution:** Top up credits or investigate excessive consumption

### Ledger Integrity Failure

**Symptoms:** Signature verification fails

**Diagnosis:**
```python
result = await ledger.verify_ledger_integrity()
print(result["signature_errors"])
```

**Solution:** Investigate data corruption or key mismatch

### High Tax Collection Errors

**Symptoms:** Tax cron job reports many errors

**Diagnosis:** Check logs for specific error messages

**Solutions:**
- Database connection issues
- Agent registry inconsistencies
- Calculator rule errors

---

## Future Enhancements

### Planned for v2.1

- [ ] Credit staking for long-term commitment
- [ ] Dynamic tax rates based on system load
- [ ] Credit market for agent-to-agent trading
- [ ] Multi-tenant credit isolation

### Planned for v3.0

- [ ] Blockchain integration for federation
- [ ] Zero-knowledge proofs for privacy
- [ ] Smart contract credit rules
- [ ] Cross-cluster credit transfers

---

## References

- **Specification:** `docs/specs/brain_credit_selection_spec.v1.yaml`
- **Migration:** `backend/alembic/versions/002_credit_system_schema.py`
- **Tests:** `backend/tests/test_credit_*.py`
- **API Docs:** http://localhost:8000/docs#/credits-v2

---

**© 2025 FalkLabs / Vinatic AG**
*In Freiheit denken. In Liebe handeln.*
