# BRAiN MASTER ROADMAP - QUICK START GUIDE
**Start here! 5-minute guide to getting started**

---

## 🎯 THE CHALLENGE

**62 modules, 244 issues:**
- 33 CRITICAL (data loss, RCE, crashes)
- 117 HIGH (auth bypass, security gaps)
- 94 MEDIUM (in-memory state, performance)

**Timeline:** 4-6 weeks to fix all P0+P1 issues

---

## ⚡ START HERE (TODAY - 30 SECONDS)

```bash
# 1. Read this file (you're doing it!)

# 2. Open the MASTER_ROADMAP.md
less /home/user/BRAiN/MASTER_ROADMAP.md

# 3. Start with immune module (30 min, highest momentum!)
cd /home/user/BRAiN/backend/app/modules/immune/

# 4. Add 3 missing enum values to schemas.py
vim schemas.py
# Add:
#   RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
#   AGENT_FAILURE = "AGENT_FAILURE"
#   PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"

# 5. Test
python -c "from app.modules.immune.schemas import ImmuneEventType; print(ImmuneEventType.RESOURCE_EXHAUSTION)"

# 6. Commit & Deploy ✓
```

---

## 📋 THE PLAN (4 WEEKS)

### Week 1: Blocking Issues (10h)
- Day 1-2: immune, factory_executor, axe_governance (2h)
- Day 2-3: sovereign_mode, skills RCE fix (5h)
- Day 3: physical_gateway DB migration (2h)
- Day 3: dmz_control, foundation auth (1h)

**Checkpoint 1:** All blocking issues fixed ✓

### Week 2: Auth + Security (20h)
- Days 1-2: 7 auth-only modules (missions, fleet, threats, etc.) (4h)
- Days 2-3: tool_system sandbox hardening (3-4h)
- Days 3-4: connectors webhook security (3-4h)
- Day 4-5: llm_router prompt injection, integrations OAuth (4-5h)

**Checkpoint 2:** All critical security gaps closed ✓

### Weeks 3-4: DB Migrations (25h)
- Days 1: Schema design with team (2-3h)
- Days 1-4: Implement migrations (memory, learning, dna, etc.) (20-25h)
- Deploy with zero-downtime dual-write strategy

**Checkpoint 3:** All state persisted, zero data loss ✓

---

## 🔴 CRITICAL PATH (5 MUST-FIX MODULES)

Do these in order, back-to-back:

| Rank | Module | Time | Why |
|------|--------|------|-----|
| 1 | **immune** | 30min | Quickest win, removes 1 crash |
| 2 | **factory_executor** | 1h | Fixes syntax error |
| 3 | **sovereign_mode** | 2h | Removes NameError crash |
| 4 | **skills** | 3-4h | Fixes CRITICAL RCE |
| 5 | **physical_gateway** | 2-3h | Prevents data loss |

**Total:** 8-10 hours (or 1-2 days)

After these 5, everything else can be parallelized!

---

## 📁 DOCUMENTATION FILES

**Start with these, in order:**

1. **QUICK_START.md** (this file) - 5 min read
2. **MASTER_ROADMAP.md** - Full strategy & details (15 min)
3. **MASTER_ROADMAP_DETAILS.md** - All 62 modules breakdown (reference)
4. **MASTER_ROADMAP.json** - Machine-readable format (for automation)
5. **CLAUDE.md** - Security patterns & requirements (reference)

---

## 🚀 HOW TO EXECUTE

### Option A: Solo Developer (Me!)
- Week 1: Critical path (immune → sovereign_mode → skills → physical_gateway)
- Week 2: Auth modules in parallel
- Week 3-4: DB migrations

### Option B: 2 Developers
- Dev A: Security focus (skills, tool_system, connectors, llm_router)
- Dev B: Auth & Persistence (auth modules, DB migrations)
- **Calendar time: 2-3 weeks instead of 4-6**

### Option C: 3 Developers (Accelerated)
- Dev A: Auth (7 modules, 1 week)
- Dev B: Complex fixes (tool_system, connectors, 1 week)
- Dev C: DB migrations (in parallel, 2 weeks)
- **Calendar time: 10-15 days**

---

## ✅ QUICK CHECKLIST FOR EACH MODULE

When fixing a module, verify:

```markdown
## Module: [NAME]

- [ ] All endpoints authenticated (401 without token)
- [ ] All user inputs validated (reject invalid data)
- [ ] No hardcoded secrets (use environment variables)
- [ ] No in-memory state (use PostgreSQL)
- [ ] No blocking I/O (use async/await)
- [ ] Error messages don't leak internals
- [ ] Audit logging for sensitive operations
- [ ] Tests pass (70%+ coverage)
- [ ] No runtime crashes (syntax valid, imports work)
```

---

## 🔧 COMMON FIX PATTERNS

### Pattern 1: Add Authentication (5 min)
```python
# router.py
from app.core.security import require_role, UserRole

@router.post("/action",
    dependencies=[Depends(require_role(UserRole.OPERATOR))]
)
async def my_action():
    pass
```

### Pattern 2: Move Secret to Environment (5 min)
```python
# BEFORE:
SECRET = "hardcoded-secret"

# AFTER:
import os
SECRET = os.environ.get("MY_SECRET")
if not SECRET:
    raise RuntimeError("MY_SECRET environment variable required")
```

### Pattern 3: Migrate In-Memory to DB (30 min per module)
```python
# BEFORE:
class MyService:
    def __init__(self):
        self._data = {}

# AFTER:
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

class MyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self):
        stmt = select(MyModel)
        result = await self.db.execute(stmt)
        return result.scalars().all()
```

### Pattern 4: Fix Shell Injection (10 min)
```python
# BEFORE (VULNERABLE):
import subprocess
cmd = f"python script.py {user_input}"
subprocess.run(cmd, shell=True)  # NEVER!

# AFTER (SAFE):
import subprocess
import shlex
cmd_parts = shlex.split(f"python script.py {user_input}")
subprocess.run(cmd_parts, shell=False)
```

---

## 📊 DAILY PROGRESS TRACKING

Use this to track your work:

```markdown
# Week 1 Progress

## Day 1
- [ ] immune enum values (30min) → DONE ✓
- [ ] factory_executor async fix (1h) → DONE ✓
- [ ] safe_mode auth (30min) → DONE ✓
- [ ] foundation auth (30min) → DONE ✓
- Total: 2.5h

## Day 2
- [ ] axe_governance secret migration (1h) → IN PROGRESS
- [ ] sovereign_mode NameError fix (2h) → BLOCKED (diagnosing)
- [ ] skills RCE fix (3-4h) → TODO
- Total expected: 6-7h
```

---

## 🎯 SUCCESS CRITERIA

**Each checkpoint must pass:**

### Checkpoint 1 (End of Week 1)
- immune, factory_executor, sovereign_mode, skills, physical_gateway ✓
- All modules import without errors ✓
- No syntax/runtime crashes ✓

### Checkpoint 2 (End of Week 2)
- All auth modules complete ✓
- All protected endpoints return 401 without token ✓
- Complex security fixes passing tests ✓

### Checkpoint 3 (End of Week 3-4)
- All state in PostgreSQL ✓
- Zero data loss on restart test ✓
- Full audit passing ✓

### Production Ready
- All P0+P1 issues resolved ✓
- 70%+ test coverage ✓
- Security audit passed ✓
- Documentation updated ✓

---

## 🆘 IF YOU GET STUCK

1. **Module won't import?**
   - Check syntax: `python -m py_compile module.py`
   - Check imports: Run Python and try importing manually
   - See MASTER_ROADMAP_DETAILS.md for specific module guidance

2. **Not sure how to fix something?**
   - Check CLAUDE.md for security patterns
   - Look at already-fixed modules for examples
   - Reference the common fix patterns above

3. **Tests failing?**
   - Run: `pytest backend/app/modules/[module]/tests/ -v`
   - Check test output for specific assertion failures
   - See MASTER_ROADMAP_DETAILS.md for test guidance

4. **Dependency conflicts?**
   - Check if module depends on another unfixed module
   - See "dependencies" column in roadmap table
   - May need to fix dependencies first

---

## 📞 QUICK REFERENCES

**Repo structure:**
```
/home/user/BRAiN/
├── backend/
│   ├── app/
│   │   ├── modules/          ← ALL MODULES HERE (62 total)
│   │   ├── core/security.py  ← Auth patterns
│   │   └── models/           ← ORM models
│   ├── alembic/              ← Database migrations
│   └── tests/                ← Tests
├── CLAUDE.md                  ← Security requirements
├── MASTER_ROADMAP.md          ← Full strategy (READ THIS!)
├── MASTER_ROADMAP_DETAILS.md  ← All 62 modules
└── MASTER_ROADMAP.json        ← Machine-readable format
```

**Key files to know:**
- `app/core/security.py` - auth decorators & functions
- `alembic/env.py` - database migration setup
- `.env.example` - environment variables template
- `pytest.ini` - test configuration

---

## ⏱️ TIME ESTIMATES (REVISED)

Based on actual complexity:

| Phase | Task | Est. Hours | Reality Check |
|-------|------|------------|---------------|
| P0 | immune | 0.5h | ✓ Easy |
| P0 | factory_executor | 1h | ✓ Easy |
| P0 | sovereign_mode | 2h | Maybe 3h (diagnosis) |
| P0 | skills RCE | 3-4h | Could be 5h (testing) |
| P0 | physical_gateway | 2-3h | ✓ Medium |
| P1 | Auth modules (7) | 4h | ✓ Easy (repetitive) |
| P1 | tool_system | 3-4h | Could be 5h (complex) |
| P1 | connectors | 3-4h | ✓ Medium |
| P1 | llm_router | 2h | ✓ Easy |
| P1 | integrations | 2-3h | ✓ Medium |
| P2 | DB migrations (12 modules) | 25h | Depends on schema |
| **TOTAL P0+P1** | | **~60h** | **1.5-2 weeks** |

---

## 🎬 START NOW!

1. Open `/home/user/BRAiN/MASTER_ROADMAP.md`
2. Read "PHASE 0: BLOCKING ISSUES" section
3. Start with immune module (30 minutes, easy win!)
4. Update your git branch: `git checkout -b fix/phase-0-blocking`
5. Make changes and commit
6. Test: `pytest` should pass
7. Move to next module

**You got this!** 🚀

---

**Last Updated:** 2026-02-25
**Status:** Ready to execute
**Estimated Completion:** 4-6 weeks with current team
**Difficulty:** Medium (mostly pattern application)
