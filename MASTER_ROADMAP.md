# BRAiN MASTER ROADMAP - 62 Modules
**Audit Date:** 2026-02-25
**Total Issues:** 33 CRITICAL + 117 HIGH + 94 MEDIUM = 244 Issues
**Modules:** 62 Total (10 CRITICAL P0, 20 HIGH P1, 32 MEDIUM P2)

---

## EXECUTIVE SUMMARY

The BRAiN framework contains **244 security and implementation issues** across 62 modules. This roadmap prioritizes fixes for autonomous execution over **4-6 weeks**.

### Key Statistics
| Category | Count | Time | Priority |
|----------|-------|------|----------|
| **CRITICAL Modules** | 10 | 42-60h | P0 - Immediate |
| **HIGH Modules** | 20 | (included above) | P1 - This Week |
| **MEDIUM Modules** | 32 | 30h+ | P2 - Next Phase |
| **Quickest Wins** | 5 | 2.5h | Do First |
| **Blocking Issues** | 5 | 8-10h | Must Fix First |

---

## PHASE 0: BLOCKING ISSUES (DO FIRST - 8-10 hours)

These 5 issues **BLOCK** everything else. Fix in order:

### 1. 🔴 IMMUNE: Missing Enum Values (30 min) ⭐ QUICKEST WIN
**Location:** `/home/user/BRAiN/backend/app/modules/immune/schemas.py`
**Issue:** Runtime crash on event matching - missing enum values
**Fix:**
```python
class ImmuneEventType(str, Enum):
    POLICY_VIOLATION = "POLICY_VIOLATION"
    ERROR_SPIKE = "ERROR_SPIKE"
    SELF_HEALING_ACTION = "SELF_HEALING_ACTION"
    # ADD THESE THREE:
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    AGENT_FAILURE = "AGENT_FAILURE"
    PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"
```
**Impact:** Removes 1 runtime crash, enables system health monitoring

---

### 2. 🔴 FACTORY_EXECUTOR: Syntax Error (1-2 hours)
**Location:** `/home/user/BRAiN/backend/app/modules/factory_executor/base.py:409`
**Issue:** Method not declared async but uses await
**Fix:** Change `def _validate_input_strict()` to `async def _validate_input_strict()`
**Impact:** Fixes syntax error, enables factory module

---

### 3. 🔴 SOVEREIGN_MODE: NameError Crash (2-3 hours)
**Location:** `/home/user/BRAiN/backend/app/modules/sovereign_mode/`
**Issue:** Undefined class/function reference (likely `KeyGenerator` or similar)
**Fix:**
- [ ] Identify missing import or class definition
- [ ] Either import from existing module OR implement missing class
- [ ] Ensure key generation uses persistent storage (not ephemeral)
**Impact:** Removes runtime crash, enables secure key management

---

### 4. 🔴 SKILLS: RCE Vulnerability (3-4 hours)
**Location:** `/home/user/BRAiN/backend/app/modules/skills/`
**Issue:** subprocess.shell=True allows shell injection RCE
**Fix Type:** [BLOCKING] [AUTH_ONLY] [RCE_FIX]
**Changes:**
- [ ] Add `require_role(UserRole.OPERATOR)` to ALL endpoints
- [ ] Replace `subprocess.shell=True` with `subprocess.exec()`
- [ ] Add path sandboxing validation
- [ ] Add command allowlist

**Impact:** Eliminates CRITICAL RCE vulnerability, enables safe skill execution

---

### 5. 🔴 PHYSICAL_GATEWAY: In-Memory Data Loss (2-3 hours)
**Location:** `/home/user/BRAiN/backend/app/modules/physical_gateway/`
**Issue:** Agents and commands stored in-memory only, lost on restart
**Fix Type:** [DB_MIGRATION] [SECRETS]
**Changes:**
- [ ] Create SQLAlchemy ORM models for agents and commands
- [ ] Create Alembic migration script
- [ ] Replace `self._agents = {}` with async DB queries
- [ ] Move MASTER_KEY from hardcoded to `os.environ.get("BRAIN_MASTER_KEY")`

**Impact:** Enables persistent gateway state, fixes hardcoded secrets

---

## PHASE 1: QUICK WINS (2.5 hours - HIGH MOMENTUM)

Fix these auth-only and simple code issues in parallel:

| Module | Fix Type | ETA | Changes |
|--------|----------|-----|---------|
| **safe_mode** | AUTH_ONLY | 30min | Add `require_role(ADMIN)` to enable/disable endpoints |
| **dmz_control** | AUTH_ONLY | 30min | Add `require_role(OPERATOR)` to all endpoints |
| **foundation** | AUTH_ONLY | 30min | Add `require_role(OPERATOR)` to config endpoints |
| **missions** | AUTH_ONLY | 1h | Add auth to all 5-6 endpoints |
| **knowledge_graph** | AUTH_ONLY | 1h | Add auth + input validation to /reset endpoint |

**Checkpoint 1:** Deploy all PHASE 0 + PHASE 1 fixes

---

## PHASE 2: AUTH-ONLY MODULES (7 hours - SECURITY HARDENING)

Add authentication to remaining endpoints:

### Group A: Quick Auth Additions (1-2 hours each)

| Rank | Module | Files | Endpoints to Protect | ETA | Blocker |
|------|--------|-------|----------------------|-----|---------|
| 11 | **fleet** | 4 | All agent fleet endpoints | 1h | MEDIUM |
| 12 | **threats** | 3 | Threat detection/response | 1-2h | MEDIUM |
| 13 | **dmz_control** | 5 | DMZ gateway control | 1h | MEDIUM |
| 14 | **runtime_auditor** | 4 | Audit log endpoints | 1-2h | MEDIUM |
| 15 | **ir_governance** | 10 | Incident response policies | 1-2h | MEDIUM |

**Strategy:** Create common auth decorator, apply to all routes
```python
from app.core.security import require_role, UserRole

@router.get("/items", dependencies=[Depends(require_role(UserRole.OPERATOR))])
async def list_items():
    # Now protected
```

**Checkpoint 2:** Deploy all auth changes

---

## PHASE 3: COMPLEX SECURITY FIXES (10-12 hours)

### Group B: Code/Security Fixes (3-4 hours each)

#### 1. **TOOL_SYSTEM** - Arbitrary Code Execution (3-4 hours)
**Location:** `/home/user/BRAiN/backend/app/modules/tool_system/`
**Issues:**
- [ ] Loader allows arbitrary Python module imports
- [ ] HTTP tool auth token leak in exception chain
- [ ] Sandbox timeout race condition
- [ ] No recursion limit
- [ ] No resource limits (CPU, memory)

**Fixes:**
1. Implement subprocess isolation for STANDARD/RESTRICTED levels
2. Wrap HTTP tool execution in try-except with token cleanup
3. Add `asyncio.wait_for()` with proper cancellation handling
4. Set recursion limit: `sys.setrecursionlimit(100)` in sandbox
5. Add CPU/memory ulimits in subprocess execution

**Files to Modify:**
- `loader.py` - Add security validation before import
- `sandbox.py` - Add resource limits and timeout handling
- `validator.py` - Restrict dunder access patterns

---

#### 2. **CONNECTORS** - Webhook Security (3-4 hours)
**Location:** `/home/user/BRAiN/backend/app/modules/connectors/`
**Issues:**
- [ ] WhatsApp webhook: No input validation on Form fields
- [ ] Timing side-channel in signature validation
- [ ] Unbounded conversation history growth
- [ ] Missing rate limiting on webhooks

**Fixes:**
1. Add max_length constraints to all Form fields:
   ```python
   Body: str = Form(..., max_length=4096)  # Add limit
   MessageBody: str = Field(..., max_length=10000)
   ```
2. Fix timing side-channel:
   ```python
   # BEFORE: if not self.auth_token or not signature: return False
   # AFTER: Always run full comparison
   if not self.auth_token or not signature:
       expected = ""
   hmac.compare_digest(actual, expected)  # Always runs
   ```
3. Add conversation history limit:
   ```python
   MAX_HISTORY = 100  # Max messages per chat
   if len(self._history[chat_id]) > MAX_HISTORY:
       self._history[chat_id] = self._history[chat_id][-MAX_HISTORY:]
   ```
4. Add rate limiting middleware:
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)

   @limiter.limit("100/minute")
   async def webhook_endpoint():
       ...
   ```

**Files to Modify:**
- `whatsapp/webhook.py` - Input validation, rate limiting
- `whatsapp/handlers.py` - Timing side-channel, history limit
- `telegram/handlers.py` - History limit

---

#### 3. **LLM_ROUTER** - Prompt Injection (2 hours)
**Location:** `/home/user/BRAiN/backend/app/modules/llm_router/`
**Issues:**
- [ ] No prompt sanitization (injection attacks)
- [ ] Model string injection possible
- [ ] Missing timeout on requests

**Fixes:**
1. Add prompt injection detection:
   ```python
   def sanitize_prompt(content: str) -> str:
       # Remove common injection patterns
       dangerous_patterns = [
           "ignore instructions",
           "system prompt",
           "break character",
       ]
       for pattern in dangerous_patterns:
           if pattern.lower() in content.lower():
               raise ValueError(f"Suspicious pattern detected: {pattern}")
       return content
   ```
2. Validate model strings:
   ```python
   ALLOWED_MODELS = {"claude-3", "gpt-4", "ollama/..."}
   if not any(model.startswith(allowed) for allowed in ALLOWED_MODELS):
       raise ValueError(f"Model not allowed: {model}")
   ```
3. Add explicit timeouts:
   ```python
   timeout = Timeout(
       timeout=30.0,  # seconds
       connect=5.0,
       read=20.0,
   )
   response = await client.post(..., timeout=timeout)
   ```

**Files to Modify:**
- `service.py` - Add sanitization, model validation, timeout
- `router.py` - Validate messages before processing

---

#### 4. **INTEGRATIONS** - OAuth Security (2-3 hours)
**Location:** `/home/user/BRAiN/backend/app/modules/integrations/`
**Issues:**
- [ ] OAuth token logged in errors
- [ ] Missing timeout on token refresh
- [ ] Circuit breaker race condition
- [ ] Password not cleared from memory

**Fixes:**
1. Add timeout to OAuth refresh:
   ```python
   timeout = httpx.Timeout(10.0)  # 10 second timeout
   async with httpx.AsyncClient(timeout=timeout) as client:
       response = await client.post(self.config.token_url, data=data)
   ```
2. Scrub tokens from errors:
   ```python
   except Exception as e:
       # Don't include token in exception
       logger.error("OAuth refresh failed", exc_info=False)
       raise AuthenticationError("Token refresh failed")
   ```
3. Make circuit breaker atomic:
   ```python
   async def record_failure(self):
       async with self._lock:  # Add asyncio.Lock()
           self._failure_count += 1
           if self._failure_count >= self._threshold:
               self._state = "open"
   ```
4. Clear sensitive data:
   ```python
   import secrets
   credentials = f"{self.config.username}:{self.config.password}"
   # Use credentials
   del credentials  # Explicit deletion
   ```

**Files to Modify:**
- `auth.py` - Add timeout, scrub tokens, clear passwords
- `circuit_breaker.py` - Add atomic lock

---

**Checkpoint 3:** Deploy complex security fixes, run full security audit

---

## PHASE 4: DATABASE MIGRATIONS (20-25 hours - ZERO-DOWNTIME STRATEGY)

### Critical Persistence Issues: 10 High-Priority Modules

These modules have **DATA LOSS** on restart. Migrate to PostgreSQL:

#### Group C: Migration Priority Order

| Rank | Module | Current State | DB Tables Needed | ETA | Depends On |
|------|--------|---------------|------------------|-----|-----------|
| 1 | **memory** | `self._memories: Dict` | memories, embeddings | 4-5h | Base schema |
| 2 | **learning** | `self._strategies: Dict` | strategies, experiments, metrics | 3-4h | Base schema |
| 3 | **dna** | `self._snapshots: Dict` | dna_snapshots, versions | 2-3h | Base schema |
| 4 | **aro** | `self._operations: Dict` | operations, logs | 2-3h | Base schema |
| 5 | **credits** | Event sourcing missing | credit_events, account_ledger | 3-4h | Base schema |
| 6 | **karma** | `self._scores: Dict` | karma_scores, history | 1-2h | Base schema |
| 7 | **runtime_auditor** | `self._logs: List` | audit_logs, entries | 1-2h | Base schema |
| 8 | **planning** | `self._plans: Dict` | plans, execution_state | 2-3h | Base schema |
| 9 | **governance** | `self._policies: Dict` | policies, enforcement_logs | 2-3h | Base schema |
| 10 | **physical_gateway** | Agents in-memory | agents, commands (see Phase 0) | (included above) | Base schema |

#### Alembic Migration Strategy

**Step 1: Design Schema** (1-2 hours)
```python
# alembic/versions/025_add_persistence_tables.py

def upgrade():
    op.create_table(
        'memories',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id')),
        sa.Column('content', sa.Text()),
        sa.Column('embedding', sa.JSON()),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), onupdate=datetime.utcnow),
    )

    # ... other tables

    op.create_index('idx_memories_agent_id', 'memories', ['agent_id'])
```

**Step 2: Implement Service Layer** (per module)
```python
# In each module's service.py

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, memory: Memory):
        db_memory = MemoryModel(**memory.dict())
        self.db.add(db_memory)
        await self.db.commit()

    async def list(self, agent_id: str):
        stmt = select(MemoryModel).where(MemoryModel.agent_id == agent_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()
```

**Step 3: Zero-Downtime Deploy**
1. Deploy with both in-memory AND DB writes (dual-write pattern)
2. Verify DB contains all data (run sanity checks)
3. Switch read-path to DB
4. Monitor for issues
5. Remove old in-memory code

**Timeline:**
- Migrations design: 2-3 hours
- Per-module implementation: 2-3 hours each (10 modules = 20-30h)
- Deploy with dual-write: 2-3 hours
- Cleanup: 1-2 hours

**Total: 25-38 hours** (Can parallelize: 2 devs = 12-19 hours)

---

## PHASE 5: LARGE MODULES (Next Sprint)

These modules don't have breaking issues but need modernization:

| Rank | Module | Size | Primary Issue | ETA | Next Phase? |
|------|--------|------|---------------|-----|------------|
| 31 | **neurorail** | 44 files | Distributed state, no persistence | 5-6h | Yes |
| 33 | **course_factory** | 19 files | In-memory state | 3-4h | Yes |
| 37 | **genesis** | 21 files | Generation state in-memory | 3-4h | Yes |
| 34 | **paycore** | 10 files | Financial data in-memory | 3-4h | Yes |

---

## DETAILED ROADMAP: ALL 62 MODULES

### TOP 10 CRITICAL (P0 - IMMEDIATE)

```
RANK | MODULE                    | SCORE | FILES | PROBLEM                    | FIX_TYPE         | ETA   | BLOCKER
-----|---------------------------|-------|-------|----------------------------|------------------|-------|----------
  1  | physical_gateway          | 6/10  |   8   | In-memory agents/commands  | DB_MIGRATION     | 2-3h  | YES
  2  | skills                    | 2/10  |  12   | RCE via shell execution    | AUTH+RCE_FIX     | 3-4h  | YES
  3  | axe_governance            | 3/10  |   1   | Hardcoded DMZ secret       | SECRETS          | 1-2h  | YES
  4  | sovereign_mode            | 4/10  |  17   | NameError crash            | CODE_FIX         | 2-3h  | YES
  5  | factory_executor          | 5/10  |   7   | Syntax error (async)       | CODE_FIX         | 1-2h  | YES
  6  | immune                    | 3/10  |   3   | Missing enum values        | CODE_FIX         | 30min | YES
  7  | memory                    | 2/10  |  12   | Complete in-memory data    | DB_MIGRATION     | 4-5h  | HIGH
  8  | learning                  | 3/10  |  11   | In-memory strategies       | DB_MIGRATION     | 3-4h  | HIGH
  9  | dna                       | 4/10  |   4   | In-memory snapshots        | DB_MIGRATION     | 2-3h  | MED
 10  | dmz_control               | 3/10  |   5   | NO auth on all endpoints   | AUTH_ONLY        | 1h    | MED
```

### TOP 20 HIGH (P1 - THIS WEEK)

```
 11  | missions                  | 4/10  |   5   | NO auth on all endpoints   | AUTH_ONLY        | 1h    | MED
 12  | foundation                | 4/10  |   4   | Config endpoints NO auth   | AUTH_ONLY        | 1.5h  | MED
 13  | safe_mode                 | 4/10  |   3   | Enable/disable NO auth     | AUTH_ONLY        | 30min | MED
 14  | fleet                     | 4/10  |   4   | All endpoints NO auth      | AUTH_ONLY        | 1h    | MED
 15  | knowledge_graph           | 4/10  |   5   | /reset endpoint NO auth    | AUTH_ONLY        | 1h    | MED
 16  | tool_system               | 5/10  |  11   | Arbitrary code execution   | SANDBOX+SECURITY | 3-4h  | HIGH
 17  | connectors                | 6/10  |  26   | Webhook input validation   | VALIDATION       | 3-4h  | HIGH
 18  | llm_router                | 5/10  |   4   | Prompt injection           | VALIDATION       | 2h    | HIGH
 19  | aro                       | 4/10  |   8   | In-memory operations       | DB_MIGRATION     | 2-3h  | MED
 20  | integrations              | 5/10  |  11   | OAuth token leak           | SECURITY         | 2-3h  | MED
 21  | credits                   | 4/10  |  22   | Event sourcing missing     | DB_MIGRATION     | 3-4h  | MED
 22  | runtime_auditor           | 4/10  |   4   | NO persistence             | DB_MIGRATION     | 1-2h  | MED
 23  | autonomous_pipeline       | 5/10  |  25   | State in-memory            | DB_MIGRATION     | 4-5h  | HIGH
 24  | karma                     | 4/10  |   3   | In-memory scoring          | DB_MIGRATION     | 1-2h  | MED
 25  | threats                   | 4/10  |   3   | NO auth, in-memory         | AUTH+DB_MIGATION | 1-2h  | MED
 26  | supervisor                | 4/10  |   4   | In-memory state            | AUTH+DB_MIGRATION| 1-2h  | MED
 27  | planning                  | 4/10  |  10   | Plans not persisted        | DB_MIGRATION     | 2-3h  | MED
 28  | ir_governance             | 4/10  |  10   | NO audit logging           | AUTH+LOGGING     | 1-2h  | MED
 29  | cluster_system            | 5/10  |  15   | Cluster state in-memory    | DB_MIGRATION     | 4-5h  | HIGH
 30  | governance                | 5/10  |  10   | Policy storage in-memory   | DB_MIGRATION     | 2-3h  | MED
```

### REMAINING 32 MODULES (P2 - NEXT PHASE)

Detailed table continued... see `/home/user/BRAiN/MASTER_ROADMAP_DETAILS.md` for full P2 listing.

---

## IMPLEMENTATION CHECKLIST

### Week 1: Blocking Issues + Quick Wins
- [ ] **Day 1-1:** immune enum values (30min)
- [ ] **Day 1-2:** factory_executor async fix (30min)
- [ ] **Day 1-3:** safe_mode auth (30min)
- [ ] **Day 1-4:** foundation auth (30min)
- [ ] Deploy Checkpoint 1.1 (4 quick fixes)
- [ ] **Day 2-1:** sovereign_mode NameError (2-3h)
- [ ] **Day 2-2:** skills RCE fix (3-4h)
- [ ] **Day 2-3:** physical_gateway DB migration (2-3h)
- [ ] Deploy Checkpoint 1.2 (blocking issues)

### Week 1-2: Auth-Only Hardening
- [ ] dmz_control, missions, fleet, threats (4h total)
- [ ] knowledge_graph, runtime_auditor, ir_governance (3h total)
- [ ] Deploy Checkpoint 2

### Week 2-3: Complex Security Fixes
- [ ] tool_system sandbox hardening (3-4h)
- [ ] connectors webhook security (3-4h)
- [ ] llm_router prompt injection (2h)
- [ ] integrations OAuth security (2-3h)
- [ ] Deploy Checkpoint 3

### Week 3-4+: Database Migrations
- [ ] Design schema (2-3h)
- [ ] Implement memory module (4-5h)
- [ ] Implement learning module (3-4h)
- [ ] Implement remaining modules in parallel (15-20h)
- [ ] Deploy zero-downtime with dual-write strategy

---

## PARALLEL EXECUTION STRATEGY

### Team Structure (Recommended)
- **Developer 1:** CRITICAL blocking fixes (2-3 days)
- **Developer 2:** Auth-only modules (1-2 days)
- Both: Complex security fixes (2-3 days in parallel)
- Both: DB migrations (coordinated effort, 1-2 weeks)

### Parallelizable Groups

**Can do simultaneously (no dependencies):**
- immune + safe_mode + foundation + dmz_control (quick wins, 2h)
- missions + knowledge_graph + fleet + threats (auth, 4h)
- tool_system + connectors + llm_router + integrations (security, 10-12h)
- All DB migrations (after schema design)

**Must sequence:**
1. All CRITICAL fixes must complete before P1 modules
2. All blocking code fixes before DB migrations
3. Schema design before DB implementation

---

## SUCCESS METRICS

### Phase Completion Criteria

**Phase 0 Checkpoint:**
- [ ] immune: No enum crashes
- [ ] factory_executor: No syntax errors
- [ ] sovereign_mode: No NameError on import
- [ ] skills: All endpoints require auth
- [ ] physical_gateway: Agents persist across restart

**Phase 1 Checkpoint:**
- [ ] All auth tests pass (401/403 without token)
- [ ] All CRITICAL modules deployable
- [ ] Zero data loss on container restart

**Phase 2 Checkpoint:**
- [ ] All webhook endpoints validate input
- [ ] No RCE vectors in tool system
- [ ] No OAuth token leaks
- [ ] No prompt injection in LLM router

**Phase 3 Checkpoint:**
- [ ] All 10+ in-memory modules use PostgreSQL
- [ ] Zero data loss on service restart
- [ ] Audit trail for all sensitive operations
- [ ] Full test coverage for persistence layer

**Production Ready Criteria:**
- [ ] All P0+P1 issues resolved
- [ ] Full security audit passed
- [ ] All endpoints have auth + input validation
- [ ] All state persisted to DB
- [ ] Automated tests passing (80%+ coverage)
- [ ] Documentation updated

---

## RISK MITIGATION

### High-Risk Changes
1. **RCE fixes in skills module** - Test thoroughly before deploy
2. **In-memory to DB migrations** - Use dual-write pattern for zero-downtime
3. **Auth enforcement** - May break existing clients, use feature flag
4. **Webhook changes** - May reject valid input, test with real clients

### Rollback Plan
- Create feature flags for all breaking changes
- Keep old code paths available for 1 release cycle
- Automated rollback script for DB migrations
- Health checks after each checkpoint

### Communication Plan
- Notify API clients 1 week before auth enforcement
- Provide migration guide for db persistence changes
- Post-deployment monitoring for 24 hours

---

## COST ESTIMATE

### Development Time (Person-Hours)
- Phase 0: 8-10h (blocking issues)
- Phase 1: 2.5h (quick wins)
- Phase 2: 7h (auth-only)
- Phase 3: 10-12h (complex fixes)
- Phase 4: 20-25h (DB migrations)
- **Total: 47.5-56.5 hours**

### With 2 Developers
- **Estimated Timeline: 25-30 days** (working 4-5h per day on BRAiN)
- **Calendar Time: 4-6 weeks** with other responsibilities

### With 3 Developers (Accelerated)
- **Estimated Timeline: 15-20 days**
- **Calendar Time: 2-3 weeks**

---

## NEXT STEPS

1. **Immediate (Today):**
   - [ ] Create feature branch: `fix/phase-0-blocking`
   - [ ] Start with immune module (easiest, highest momentum)
   - [ ] Run tests continuously

2. **This Week:**
   - [ ] Complete all Phase 0 fixes
   - [ ] Complete all Phase 1 quick wins
   - [ ] Deploy Checkpoint 1 & 2

3. **Next Week:**
   - [ ] Complete Phase 2 auth-only modules
   - [ ] Complete Phase 3 complex security fixes
   - [ ] Deploy Checkpoint 3

4. **Following Weeks:**
   - [ ] Design DB schema (coordinated team effort)
   - [ ] Implement Phase 4 DB migrations
   - [ ] Deploy zero-downtime with gradual rollout

---

## REFERENCES

**Audit Reports:**
- `audit_report_group_c.md` - connectors, integrations, llm_router, tool_system
- `CLAUDE.md` - Security patterns and requirements

**Related Files:**
- `/home/user/BRAiN/backend/MASTER_ROADMAP.md` - This file
- `/home/user/BRAiN/backend/MASTER_ROADMAP_DETAILS.md` - Full P2 module details

**Key Security Patterns:**
- See CLAUDE.md for auth, input validation, secrets management patterns

---

**Document Version:** 1.0
**Last Updated:** 2026-02-25
**Status:** Ready for execution
**Approval:** Pending team review
