# BRAiN MASTER ROADMAP - COMPLETE MODULE DETAILS
**All 62 Modules with Full Implementation Strategy**

---

## QUICK REFERENCE TABLE

All modules sorted by priority and risk:

### PHASE 0: BLOCKING ISSUES (MUST FIX FIRST)

| Rank | Module | Score | Files | Main Issue | Fix Type | Est. Time | Status | Dependencies |
|------|--------|-------|-------|------------|----------|-----------|--------|--------------|
| 🔴1 | immune | 3/10 | 3 | Missing enum values (RESOURCE_EXHAUSTION, AGENT_FAILURE, PERFORMANCE_DEGRADATION) | CODE_FIX | **30min** | ⭐ START HERE | None |
| 🔴2 | factory_executor | 5/10 | 7 | Method not async (base.py:409) | CODE_FIX | **1h** | Blocking factory | immune |
| 🔴3 | axe_governance | 3/10 | 1 | Hardcoded DMZ_GATEWAY_SECRET | SECRETS | **1h** | Blocking sovereign | factory_executor |
| 🔴4 | sovereign_mode | 4/10 | 17 | NameError: undefined class/function | CODE_FIX | **2h** | Runtime crash | axe_governance |
| 🔴5 | skills | 2/10 | 12 | subprocess.shell=True RCE + NO auth | RCE_FIX + AUTH | **3-4h** | CRITICAL | sovereign_mode |
| 🔴6 | physical_gateway | 6/10 | 8 | In-memory agents + hardcoded MASTER_KEY | DB_MIGRATION + SECRETS | **2-3h** | Core gateway | skills |
| 🔴7 | dmz_control | 3/10 | 5 | NO endpoints auth | AUTH_ONLY | **1h** | Security | physical_gateway |
| 🔴8 | foundation | 4/10 | 4 | Config endpoints NO auth | AUTH_ONLY | **1h** | Core service | dmz_control |
| 🔴9 | memory | 2/10 | 12 | Complete in-memory, DATA LOSS | DB_MIGRATION | **4-5h** | Data loss risk | foundation |
| 🔴10 | learning | 3/10 | 11 | In-memory strategies, DATA LOSS | DB_MIGRATION | **3-4h** | Data loss risk | memory |

---

### PHASE 1: HIGH PRIORITY (THIS WEEK)

| Rank | Module | Score | Files | Main Issue | Fix Type | Est. Time | Dependencies |
|------|--------|-------|-------|------------|----------|-----------|--------------|
| 🟠11 | missions | 4/10 | 5 | NO endpoints auth | AUTH_ONLY | 1h | foundation |
| 🟠12 | knowledge_graph | 4/10 | 5 | /reset endpoint NO auth + no validation | AUTH_ONLY + VALIDATION | 1h | missions |
| 🟠13 | fleet | 4/10 | 4 | All endpoints NO auth | AUTH_ONLY | 1h | knowledge_graph |
| 🟠14 | threats | 4/10 | 3 | NO auth + in-memory threat storage | AUTH_ONLY + DB_MIGRATION | 1-2h | fleet |
| 🟠15 | safe_mode | 4/10 | 3 | Enable/disable endpoints NO auth | AUTH_ONLY | 30min | threats |
| 🟠16 | runtime_auditor | 4/10 | 4 | NO persistence (in-memory audit logs) | DB_MIGRATION | 1-2h | safe_mode |
| 🟠17 | ir_governance | 4/10 | 10 | NO audit logging + missing endpoint auth | AUTH_ONLY + LOGGING | 1-2h | runtime_auditor |
| 🟠18 | tool_system | 5/10 | 11 | Arbitrary code execution (loader) + auth token leak + timeout race | SANDBOX + SECURITY | 3-4h | ir_governance |
| 🟠19 | connectors | 6/10 | 26 | Webhook input validation missing + timing side-channel + history growth + no rate limit | VALIDATION + RATE_LIMIT | 3-4h | tool_system |
| 🟠20 | llm_router | 5/10 | 4 | No prompt injection sanitization + model string injection + missing timeout | VALIDATION + PROMPT_INJECTION | 2h | connectors |
| 🟠21 | integrations | 5/10 | 11 | OAuth token leak in errors + no timeout + circuit breaker race + password not cleared | SECURITY + ASYNC_FIX | 2-3h | llm_router |
| 🟠22 | aro | 4/10 | 8 | In-memory operations (DATA LOSS) | DB_MIGRATION | 2-3h | integrations |
| 🟠23 | credits | 4/10 | 22 | Event sourcing missing, in-memory | DB_MIGRATION + EVENT_SOURCING | 3-4h | aro |
| 🟠24 | karma | 4/10 | 3 | In-memory scoring (DATA LOSS) | DB_MIGRATION | 1-2h | credits |
| 🟠25 | planning | 4/10 | 10 | Plans not persisted, in-memory state (DATA LOSS) | DB_MIGRATION | 2-3h | karma |
| 🟠26 | governance | 5/10 | 10 | Policy storage in-memory + missing audit trail | DB_MIGRATION + LOGGING | 2-3h | planning |
| 🟠27 | supervisor | 4/10 | 4 | In-memory state + NO control validation | AUTH_ONLY + DB_MIGRATION | 1-2h | governance |
| 🟠28 | autonomous_pipeline | 5/10 | 25 | State in-memory + missing validation + error handling (DATA LOSS) | DB_MIGRATION + VALIDATION | 4-5h | supervisor |
| 🟠29 | cluster_system | 5/10 | 15 | Cluster state in-memory (DATA LOSS) + race conditions | DB_MIGRATION + CONCURRENCY | 4-5h | autonomous_pipeline |
| 🟠30 | dna | 4/10 | 4 | In-memory snapshots (DATA LOSS) | DB_MIGRATION | 2-3h | cluster_system |

---

### PHASE 2: MEDIUM PRIORITY (NEXT PHASE)

| Rank | Module | Score | Files | Main Issue | Fix Type | Est. Time | Priority |
|------|--------|-------|-------|------------|----------|-----------|----------|
| 🟡31 | neurorail | 6/10 | 44 | Distributed state in-memory (DATA LOSS) | DB_MIGRATION + CONCURRENCY | 5-6h | P2_LARGE |
| 🟡32 | axe_widget | 5/10 | 4 | Widget state in-memory | DB_MIGRATION | 1-2h | P2_LOW |
| 🟡33 | course_factory | 5/10 | 19 | Course state in-memory | DB_MIGRATION | 3-4h | P2_MEDIUM |
| 🟡34 | paycore | 5/10 | 10 | Payment state in-memory + missing transaction logging (FINANCIAL!) | DB_MIGRATION + LOGGING | 3-4h | P2_HIGH |
| 🟡35 | course_distribution | 5/10 | 7 | Distribution state in-memory + no audit trail | DB_MIGRATION + LOGGING | 2-3h | P2_MEDIUM |
| 🟡36 | governor | 5/10 | 13 | Governor state in-memory | DB_MIGRATION | 2-3h | P2_MEDIUM |
| 🟡37 | genesis | 6/10 | 21 | Generation state in-memory + distributed state issues | DB_MIGRATION + CONCURRENCY | 3-4h | P2_LARGE |
| 🟡38 | webgenesis | 5/10 | 8 | Web generation state in-memory | DB_MIGRATION | 2-3h | P2_LOW |
| 🟡39 | business_factory | 4/10 | 4 | Factory state in-memory + incomplete structure | RESTRUCTURE + DB_MIGRATION | 2-3h | P2_LOW |
| 🟡40 | factory | 4/10 | 2 | Minimal implementation | DEVELOPMENT | 2-3h | P2_LOW |
| 🟡41 | coordination | 5/10 | 10 | Coordination state in-memory + race conditions | DB_MIGRATION + CONCURRENCY | 2-3h | P2_MEDIUM |
| 🟡42 | config_management | 5/10 | 5 | Config cache in-memory + no hot-reload | DB_MIGRATION + CACHING | 1-2h | P2_LOW |
| 🟡43 | health_monitor | 5/10 | 5 | Health metrics in-memory (no historical data) | DB_MIGRATION | 1-2h | P2_LOW |
| 🟡44 | monitoring | 5/10 | 3 | Monitoring data in-memory (no aggregation) | DB_MIGRATION | 1-2h | P2_LOW |
| 🟡45 | agent_management | 5/10 | 5 | Agent state in-memory | DB_MIGRATION | 1-2h | P2_MEDIUM |
| 🟡46 | audit_logging | 5/10 | 5 | Audit log in-memory (but has DB model) | DB_MIGRATION | 1-2h | P2_LOW |
| 🟡47 | axe_identity | 5/10 | 5 | Identity state in-memory | DB_MIGRATION | 1-2h | P2_LOW |
| 🟡48 | axe_knowledge | 5/10 | 5 | Knowledge state in-memory | DB_MIGRATION | 1-2h | P2_LOW |
| 🟡49 | axe_fusion | 5/10 | 4 | Fusion state in-memory | DB_MIGRATION | 1-2h | P2_LOW |
| 🟡50 | dns_hetzner | 5/10 | 5 | DNS state in-memory + missing auth | DB_MIGRATION + AUTH | 1-2h | P2_LOW |
| 🟡51 | fred_bridge | 5/10 | 5 | Bridge state in-memory | DB_MIGRATION | 1-2h | P2_LOW |
| 🟡52 | system_health | 5/10 | 4 | Health state in-memory (no historical tracking) | DB_MIGRATION | 1-2h | P2_LOW |
| 🟡53 | task_queue | 5/10 | 5 | Queue state in-memory | DB_MIGRATION | 1-2h | P2_MEDIUM |
| 🟡54 | telemetry | 5/10 | 5 | Telemetry data in-memory (no aggregation) | DB_MIGRATION | 1-2h | P2_LOW |
| 🟡55 | policy | 4/10 | 5 | Policy state in-memory (no enforcement) | DB_MIGRATION | 1-2h | P2_LOW |
| 🟡56 | template_registry | 4/10 | 4 | Templates in-memory | DB_MIGRATION | 1-2h | P2_LOW |
| 🟡57 | ros2_bridge | 4/10 | 4 | ROS2 state in-memory + no integration test | DB_MIGRATION + TESTING | 1-2h | P2_LOW |
| 🟡58 | vision | 4/10 | 2 | Vision processing not implemented | DEVELOPMENT | 3-4h | P2_LOW |
| 🟡59 | hardware | 4/10 | 3 | Hardware control stub (missing device integration) | DEVELOPMENT | 2-3h | P2_LOW |
| 🟡60 | slam | 4/10 | 2 | SLAM not implemented | DEVELOPMENT | 4-5h | P2_LOW |
| 🟡61 | deployment | 5/10 | 3 | Orchestration incomplete (missing validation) | DEVELOPMENT | 2-3h | P2_LOW |
| 🟡62 | metrics | 4/10 | 1 | Not implemented (empty stub) | DEVELOPMENT | 1-2h | P2_LOW |

---

## DETAILED MODULE BREAKDOWN

### 🔴 CRITICAL: immune (Rank #1 - START HERE!)

**Location:** `/home/user/BRAiN/backend/app/modules/immune/`
**Impact:** Runtime crash on event type matching
**Fix Time:** 30 minutes ⭐

**File to fix:** `schemas.py`

**Current state:**
```python
class ImmuneEventType(str, Enum):
    POLICY_VIOLATION = "POLICY_VIOLATION"
    ERROR_SPIKE = "ERROR_SPIKE"
    SELF_HEALING_ACTION = "SELF_HEALING_ACTION"
    # MISSING: RESOURCE_EXHAUSTION, AGENT_FAILURE, PERFORMANCE_DEGRADATION
```

**Fixed state:**
```python
class ImmuneEventType(str, Enum):
    POLICY_VIOLATION = "POLICY_VIOLATION"
    ERROR_SPIKE = "ERROR_SPIKE"
    SELF_HEALING_ACTION = "SELF_HEALING_ACTION"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"  # ADD
    AGENT_FAILURE = "AGENT_FAILURE"              # ADD
    PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"  # ADD
```

**Test:** Can create ImmuneEvent with all event types, no error on enum matching

---

### 🔴 CRITICAL: factory_executor (Rank #2)

**Location:** `/home/user/BRAiN/backend/app/modules/factory_executor/`
**Impact:** Syntax error blocks factory module
**Fix Time:** 1-2 hours

**File to fix:** `base.py:409`

**Current code:**
```python
def _validate_input_strict(self, input_data: dict) -> ValidationResult:
    # Uses await but method is not async!
    result = await self.validate_input(input_data)
```

**Fixed code:**
```python
async def _validate_input_strict(self, input_data: dict) -> ValidationResult:
    # Now properly async
    result = await self.validate_input(input_data)
```

**Test:** Module imports without syntax error, method can be awaited

---

### 🔴 CRITICAL: axe_governance (Rank #3)

**Location:** `/home/user/BRAiN/backend/app/modules/axe_governance/`
**Impact:** Hardcoded secret exposed, security risk
**Fix Time:** 1-2 hours

**File to fix:** `__init__.py` or main service file

**Current code:**
```python
DMZ_GATEWAY_SECRET = "hardcoded-secret-here"  # NEVER DO THIS!
```

**Fixed code:**
```python
import os

DMZ_GATEWAY_SECRET = os.environ.get("AXE_DMZ_GATEWAY_SECRET")
if not DMZ_GATEWAY_SECRET:
    raise RuntimeError("AXE_DMZ_GATEWAY_SECRET environment variable required")
```

**Setup:** Add to `.env.example`:
```
AXE_DMZ_GATEWAY_SECRET=your-secure-secret-here-change-in-prod
```

**Test:** Module loads with env var set, fails with clear error if unset

---

### 🔴 CRITICAL: sovereign_mode (Rank #4)

**Location:** `/home/user/BRAiN/backend/app/modules/sovereign_mode/`
**Impact:** Runtime NameError crash on import
**Fix Time:** 2-3 hours

**Diagnosis needed:**
1. Run: `python -c "from backend.app.modules.sovereign_mode import *"` to see exact error
2. Likely issue: Missing import or undefined class (e.g., `KeyGenerator`)

**Common solutions:**
- [ ] If `KeyGenerator` is missing: Import from `app.crypto` or implement it
- [ ] If `KeyManager` is missing: Check if should import from `physical_gateway`
- [ ] If method reference is broken: Check method existence in parent class

**Fix strategy:**
```python
# Option 1: Import from existing module
from app.modules.crypto import KeyGenerator

# Option 2: Implement missing class
class KeyGenerator:
    async def generate_key(self, **kwargs):
        ...

# Option 3: Fix method/attribute reference
# Was: self.undefined_method()
# Now: self.defined_method()
```

**Test:** Module imports without NameError, KeyGenerator available for use

---

### 🔴 CRITICAL: skills (Rank #5 - HIGHEST SECURITY RISK)

**Location:** `/home/user/BRAiN/backend/app/modules/skills/`
**Impact:** RCE vulnerability + NO authentication = CRITICAL
**Fix Time:** 3-4 hours

**Issues:**
1. subprocess.shell=True allows injection
2. All endpoints unprotected
3. Path traversal possible

**Files to modify:**
- `router.py` - Add auth to all endpoints
- `shell_command.py` (or equivalent) - Fix execution method

**Step 1: Add Authentication**
```python
# router.py
from app.core.security import require_role, UserRole

@router.post("/{skill_id}/execute",
    dependencies=[Depends(require_role(UserRole.OPERATOR))]
)
async def execute_skill(skill_id: str, ...):
    # Now protected
```

**Step 2: Fix Shell Execution**
```python
# BEFORE (VULNERABLE):
import subprocess
cmd = f"python {skill_file} {args}"
subprocess.run(cmd, shell=True)  # NEVER DO THIS!

# AFTER (SECURE):
import subprocess
import shlex
cmd_parts = shlex.split(f"python {skill_file} {args}")
proc = subprocess.run(cmd_parts, shell=False)  # shell=False prevents injection
```

**Step 3: Add Path Validation**
```python
from pathlib import Path

def validate_skill_path(skill_id: str, base_path: str = "/app/skills/"):
    requested = Path(base_path) / skill_id
    resolved = requested.resolve()
    base_resolved = Path(base_path).resolve()

    # Prevent directory traversal
    if not str(resolved).startswith(str(base_resolved)):
        raise ValueError("Path traversal detected")

    if not resolved.exists():
        raise ValueError("Skill not found")

    return resolved
```

**Test:**
- [ ] Unauthenticated request returns 401
- [ ] Command injection payloads fail (no shell execution)
- [ ] Path traversal blocked (../ rejected)

---

### 🔴 CRITICAL: physical_gateway (Rank #6)

**Location:** `/home/user/BRAiN/backend/app/modules/physical_gateway/`
**Impact:** Agent state LOST on restart + hardcoded secrets
**Fix Time:** 2-3 hours

**Two issues:**

**Issue 1: In-Memory Agents**
```python
# CURRENT (DATA LOSS):
class PhysicalGatewayService:
    def __init__(self):
        self._agents = {}  # Lost on restart!

# FIXED (PERSISTENT):
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

class PhysicalGatewayService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_agents(self):
        stmt = select(AgentModel)
        result = await self.db.execute(stmt)
        return result.scalars().all()
```

**Issue 2: Hardcoded Master Key**
```python
# BEFORE:
MASTER_KEY = "brain-physical-gateway-master-key"  # EXPOSED!

# AFTER:
import os
MASTER_KEY = os.environ.get("BRAIN_MASTER_KEY")
if not MASTER_KEY:
    raise RuntimeError("BRAIN_MASTER_KEY environment variable required")
```

**Database Schema (Alembic migration):**
```python
# alembic/versions/026_physical_gateway_agents.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'gateway_agents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(256)),
        sa.Column('config', sa.JSON()),
        sa.Column('status', sa.String(50)),  # active, inactive, error
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), onupdate=datetime.utcnow),
    )
    op.create_index('idx_gateway_agents_status', 'gateway_agents', ['status'])

def downgrade():
    op.drop_table('gateway_agents')
```

**Test:**
- [ ] Create agent via API
- [ ] Stop service
- [ ] Start service
- [ ] Agent still exists (not lost)
- [ ] BRAIN_MASTER_KEY env var required for startup

---

### 🟠 HIGH: dmz_control (Rank #7)

**Location:** `/home/user/BRAiN/backend/app/modules/dmz_control/`
**Impact:** NO authentication on critical DMZ endpoints
**Fix Time:** 1 hour

**Quick fix:** Add auth decorator to all endpoints

```python
# router.py
from app.core.security import require_role, UserRole

@router.post("/gateway/configure",
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)
async def configure_gateway(config: GatewayConfig):
    # Now protected
```

**Identify all endpoints:** Run grep to find them:
```bash
grep -n "@router\." /home/user/BRAiN/backend/app/modules/dmz_control/router.py
```

Add `dependencies=[Depends(require_role(UserRole.ADMIN))]` to each

**Test:** All endpoints return 401 without auth token

---

### 🟠 HIGH: foundation (Rank #8)

**Location:** `/home/user/BRAiN/backend/app/modules/foundation/`
**Impact:** Config endpoints unprotected + NO audit logging
**Fix Time:** 1-1.5 hours

**Changes:**
1. Add auth to config endpoints
2. Add audit logging for changes

```python
# router.py
from app.core.security import require_role, UserRole
from mission_control_core.core.event_stream import EventStream

@router.post("/config",
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)
async def update_config(
    config: ConfigUpdate,
    principal: Principal = Depends(get_current_principal),
):
    # Update config
    ...

    # Log change
    event_stream = EventStream.get_instance()
    await event_stream.publish(
        event_type="foundation.config_changed",
        payload={"principal": principal.id, "config": config},
        source="foundation"
    )
```

**Test:** Config endpoints require ADMIN role, changes logged

---

### 🟠 HIGH: memory (Rank #9 - MAJOR DATA LOSS)

**Location:** `/home/user/BRAiN/backend/app/modules/memory/`
**Impact:** Complete in-memory storage, ALL MEMORIES LOST on restart
**Fix Time:** 4-5 hours (includes DB schema, migration, service rewrite)

**Current problem:**
```python
class MemoryService:
    def __init__(self):
        self._memories: Dict[str, Memory] = {}  # Lost!
        self._embeddings: Dict[str, List[float]] = {}  # Lost!
```

**Solution: PostgreSQL + SQLAlchemy**

**Step 1: Create ORM models** (`models.py`)
```python
from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class MemoryModel(Base):
    __tablename__ = "memories"

    id = Column(String(36), primary_key=True)
    agent_id = Column(String(36), index=True)
    content = Column(Text())
    embedding = Column(JSON())  # Store vector as JSON
    memory_type = Column(String(50))  # short_term, long_term, procedural
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # For TTL

class MemoryAccessLog(Base):
    __tablename__ = "memory_access_logs"

    id = Column(String(36), primary_key=True)
    memory_id = Column(String(36), index=True)
    agent_id = Column(String(36), index=True)
    accessed_at = Column(DateTime, default=datetime.utcnow)
```

**Step 2: Create Alembic migration**
```bash
alembic revision --autogenerate -m "Add memory persistence"
```

**Step 3: Rewrite MemoryService**
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_memory(self, agent_id: str, content: str, embedding: List[float]):
        memory = MemoryModel(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            content=content,
            embedding=embedding,
            memory_type="short_term",
        )
        self.db.add(memory)
        await self.db.commit()

        # Log access
        log = MemoryAccessLog(
            id=str(uuid.uuid4()),
            memory_id=memory.id,
            agent_id=agent_id,
        )
        self.db.add(log)
        await self.db.commit()

    async def list_memories(self, agent_id: str, limit: int = 100):
        stmt = select(MemoryModel).where(
            MemoryModel.agent_id == agent_id
        ).order_by(
            MemoryModel.created_at.desc()
        ).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
```

**Test:**
- [ ] Save memory via API
- [ ] Stop service, restart
- [ ] Memory still exists
- [ ] Access logs recorded
- [ ] Can query memories by agent_id

---

### 🟠 HIGH: learning (Rank #10 - MAJOR DATA LOSS)

**Location:** `/home/user/BRAiN/backend/app/modules/learning/`
**Impact:** Strategies, experiments, metrics all lost on restart
**Fix Time:** 3-4 hours

**Similar to memory module, but for learning strategies:**

**ORM Models needed:**
```python
class LearningStrategy(Base):
    __tablename__ = "learning_strategies"
    id = Column(String(36), primary_key=True)
    agent_id = Column(String(36), index=True)
    strategy_type = Column(String(100))  # reinforcement, supervised, etc.
    config = Column(JSON())
    performance_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class LearningExperiment(Base):
    __tablename__ = "learning_experiments"
    id = Column(String(36), primary_key=True)
    strategy_id = Column(String(36), ForeignKey("learning_strategies.id"))
    agent_id = Column(String(36), index=True)
    status = Column(String(50))  # running, completed, failed
    results = Column(JSON())
    created_at = Column(DateTime, default=datetime.utcnow)

class LearningMetric(Base):
    __tablename__ = "learning_metrics"
    id = Column(String(36), primary_key=True)
    strategy_id = Column(String(36), ForeignKey("learning_strategies.id"))
    metric_name = Column(String(100))
    value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
```

**Apply same pattern as memory module:** Create migration, rewrite service with AsyncSession

---

## DATABASE MIGRATION CHECKLIST

For each in-memory module being migrated:

```
Module: ___________________

Phase 1: Planning (0.5h)
- [ ] List all in-memory data structures
- [ ] Design SQL schema
- [ ] Identify relationships (foreign keys)
- [ ] Plan indexes for query performance

Phase 2: Implementation (1-2h per module)
- [ ] Create SQLAlchemy ORM models
- [ ] Create Alembic migration
- [ ] Update service to use AsyncSession + db
- [ ] Update router to pass db dependency

Phase 3: Testing (0.5h)
- [ ] Unit tests for service methods
- [ ] Integration tests (actual DB)
- [ ] Data loss test (restart service)

Phase 4: Deployment (0.5h)
- [ ] Run migration in staging
- [ ] Verify data persists
- [ ] Deploy with dual-write (keep old code)
- [ ] Monitor for issues
```

---

## PARALLEL EXECUTION PLAN

### Team Assignment Suggestion

**Developer A (Security focus):** 15-20 hours
- Week 1: immune, factory_executor, axe_governance (2h)
- Week 1: sovereign_mode, skills RCE (5h)
- Week 2: physical_gateway (2h)
- Week 2: tool_system, connectors (7h)
- Week 2: llm_router (2h)

**Developer B (Auth focus):** 12-15 hours
- Week 1: dmz_control, foundation, safe_mode (2.5h)
- Week 1-2: missions, knowledge_graph, fleet, threats (4h)
- Week 2: runtime_auditor, ir_governance (2.5h)
- Week 2: integrations (2.5h)
- Week 3: supervisor (1.5h)

**Developer A+B (DB Migrations):** 20-25 hours together
- Week 3-4: Design schema together (2-3h)
- Week 3-4: Implement migrations in parallel (20-22h)
  - A: memory, learning, autonomous_pipeline
  - B: dna, aro, credits, karma, planning, governance, cluster_system

---

## DEPLOYMENT GATES

### Before deploying Phase 1:
- [ ] All PHASE 0 blocking issues resolved
- [ ] immune: No runtime errors
- [ ] factory_executor: Syntax valid
- [ ] sovereign_mode: No NameError
- [ ] Full test suite passing

### Before deploying Phase 2:
- [ ] All PHASE 1 auth modules tested
- [ ] 401/403 responses validated
- [ ] Client compatibility verified
- [ ] No data loss in temp restarts

### Before deploying Phase 3:
- [ ] Security audit of tool_system, connectors, llm_router
- [ ] Penetration testing of webhook endpoints
- [ ] RCE vectors eliminated

### Before deploying Phase 4 (DB Migrations):
- [ ] Alembic migrations tested in staging
- [ ] Rollback plan documented
- [ ] Zero-downtime strategy validated
- [ ] Data consistency verified

---

## ESTIMATED BURN DOWN

```
Week 1:
  Day 1: immune (0.5h) ✓
  Day 1: factory_executor (1h) ✓
  Day 1: safe_mode, foundation (1h) ✓
  Day 2: sovereign_mode (2h) ✓
  Day 2: skills RCE (3h) ✓
  Day 3: physical_gateway (2h) ✓
  Day 3: dmz_control (1h) ✓
  Subtotal: ~10.5h

Week 2:
  Day 1-2: missions, knowledge_graph, fleet, threats (4h)
  Day 2-3: tool_system (3-4h)
  Day 3-4: connectors (3-4h)
  Day 4: llm_router (2h)
  Subtotal: ~12-14h

Week 3:
  Day 1: integrations (2-3h)
  Day 1-2: runtime_auditor, ir_governance (2-3h)
  Day 2-3: DB schema design (2-3h)
  Day 3-4: Start migrations (memory, learning) (6-8h)
  Subtotal: ~12-17h

Week 4+:
  Continue DB migrations (20-25h)
  Subtotal: 20-25h

TOTAL: ~55-70 hours (1.5-2 person-months solo, 2-3 weeks with 2 people)
```

---

## SUCCESS CRITERIA

All modules must pass:
- [ ] Import without errors
- [ ] All endpoints authenticated (401 without token)
- [ ] All inputs validated (reject invalid data)
- [ ] No hardcoded secrets (use environment variables)
- [ ] No data loss on restart
- [ ] Audit logging for sensitive operations
- [ ] Test coverage 70%+

---

**Document Version:** 1.0
**Created:** 2026-02-25
**Status:** Ready for execution
