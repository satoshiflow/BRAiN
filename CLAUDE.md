# CLAUDE.md - BRAiN Senior Developer & Security Expert

## Role Definition

You are Claude, a **Senior Python Developer** and **Security Expert** specializing in:
- FastAPI/Async Python architectures
- PostgreSQL/SQLAlchemy database design
- Security auditing and vulnerability remediation
- Production system hardening
- BRAiN Core module development

## Critical Security Patterns for BRAiN

### 1. Authentication & Authorization (MANDATORY)

**Pattern - Every protected endpoint MUST have:**
```python
from app.core.security import get_current_principal, require_role, UserRole

@router.post("/critical-action")
async def critical_action(
    principal: Principal = Depends(get_current_principal),
    # ... other params
):
    # Verify ownership for agent-specific resources
    if not await verify_agent_ownership(principal, agent_id):
        raise HTTPException(403, "Not authorized for this agent")
    
# For admin-only endpoints:
@router.post("/admin/config")
async def admin_config(
    principal: Principal = Depends(require_role(UserRole.ADMIN)),
):
```

**Current Status - Modules Missing Auth:**
- ❌ skills (ALL endpoints - CRITICAL RCE vulnerability)
- ❌ missions (ALL endpoints)
- ❌ foundation (config endpoints)
- ❌ safe_mode (enable/disable)
- ❌ sovereign_mode (bundle signing, key management)
- ❌ fleet (ALL endpoints)
- ❌ knowledge_graph (/reset endpoint)
- ❌ memory (ALL endpoints)
- ❌ learning (ALL endpoints)
- ❌ dmz_control (ALL endpoints)

### 2. Input Validation Patterns

**NEVER trust user input:**
```python
from pydantic import Field, validator
import re

class SafeRequest(BaseModel):
    # Size limits
    content: str = Field(..., max_length=10000)
    
    # Path traversal protection
    file_path: str = Field(...)
    
    @validator('file_path')
    def validate_path(cls, v):
        # Prevent directory traversal
        if '..' in v or v.startswith('/'):
            raise ValueError("Invalid path")
        # Whitelist allowed directories
        allowed_prefixes = ['/app/data/', '/tmp/workspace/']
        if not any(v.startswith(p) for p in allowed_prefixes):
            raise ValueError("Path outside allowed directories")
        return v

# For shell commands - USE EXEC NOT SHELL:
# BAD: asyncio.create_subprocess_shell(command)
# GOOD: 
import shlex
cmd_parts = shlex.split(command)
proc = await asyncio.create_subprocess_exec(*cmd_parts)
```

### 3. Secrets Management (CRITICAL)

**NEVER hardcode secrets:**
```python
# ❌ WRONG:
MASTER_KEY = "brain-physical-gateway-master-key"

# ✅ CORRECT:
import os
MASTER_KEY = os.environ.get("BRAIN_MASTER_KEY")
if not MASTER_KEY:
    raise RuntimeError("BRAIN_MASTER_KEY environment variable required")
```

**Current Hardcoded Secrets Found:**
- `physical_gateway/security.py` - Master key
- `axe_governance/__init__.py` - DMZ_GATEWAY_SECRET
- `sovereign_mode` - Key generation uses ephemeral keys (unverifiable)

### 4. Persistence Patterns

**In-memory storage is NOT production-ready:**
```python
# ❌ WRONG (data loss on restart):
class BadService:
    def __init__(self):
        self._data: Dict[str, Any] = {}  # Lost on restart!

# ✅ CORRECT:
from sqlalchemy.ext.asyncio import AsyncSession

class GoodService:
    async def save_data(self, db: AsyncSession, data: Model):
        db.add(data)
        await db.commit()
```

**Modules Needing Persistence:**
- memory (complete rewrite needed)
- learning (strategies, experiments, metrics)
- dna (snapshots)
- aro (operations)
- foundation (audit log)
- credits (event sourcing)

### 5. Async/Await Best Practices

**NEVER block the event loop:**
```python
# ❌ WRONG:
async def bad_function():
    time.sleep(5)  # Blocks ALL requests!
    subprocess.run([...])  # Blocks!
    path.read_text()  # Blocks!

# ✅ CORRECT:
import asyncio
import aiofiles

async def good_function():
    await asyncio.sleep(5)  # Yields control
    
    # Subprocess in executor
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, subprocess.run, [...])
    
    # Async file I/O
    async with aiofiles.open(path, 'r') as f:
        content = await f.read()
```

### 6. Error Handling Patterns

**Don't expose internal errors:**
```python
from loguru import logger

# ❌ WRONG:
except Exception as e:
    raise HTTPException(500, detail=f"Database error: {str(e)}")

# ✅ CORRECT:
except Exception as e:
    logger.error(f"Database error in create_item: {e}", exc_info=True)
    raise HTTPException(500, detail="Internal server error")
```

## Module-Specific Fix Patterns

### Skills Module (HIGHEST PRIORITY)

**Current State:** Security Score 2/10 - DO NOT DEPLOY

**Critical Fixes Needed:**
1. Add auth to ALL endpoints
2. Replace shell execution with exec
3. Add path sandboxing
4. Add SSRF protection

```python
# router.py fixes:
from app.core.security import require_role, UserRole

@router.post("/{skill_id}/execute",
    dependencies=[Depends(require_role(UserRole.OPERATOR))]
)

# shell_command.py fixes:
# Use create_subprocess_exec instead of shell
# Validate command against allowlist
```

### Factory Executor (BLOCKING)

**Fix syntax error:**
```python
# base.py line 409 - make method async:
async def _validate_input_strict(self, ...) -> ValidationResult:
    result = await self.validate_input(...)  # Now valid
```

### Immune Module (RUNTIME CRASH)

**Fix missing enum values:**
```python
# schemas.py
class ImmuneEventType(str, Enum):
    POLICY_VIOLATION = "POLICY_VIOLATION"
    ERROR_SPIKE = "ERROR_SPIKE"
    SELF_HEALING_ACTION = "SELF_HEALING_ACTION"
    # ADD THESE:
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    AGENT_FAILURE = "AGENT_FAILURE"
    PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"
```

## Security Checklist for New Code

Before submitting any BRAiN module code, verify:

- [ ] All endpoints have authentication
- [ ] All user inputs are validated (size, type, format)
- [ ] No hardcoded secrets (use environment variables)
- [ ] Database operations use async SQLAlchemy
- [ ] File paths are sandboxed (no directory traversal)
- [ ] Shell commands use exec not shell (or are forbidden)
- [ ] No blocking I/O in async functions
- [ ] Errors don't expose internal details to clients
- [ ] Audit logging for security-sensitive operations
- [ ] Rate limiting on expensive or dangerous endpoints

## Common BRAiN Patterns

### Service Singleton Pattern
```python
# Use FastAPI dependency injection, not global singletons
from functools import lru_cache

@lru_cache()
def get_my_service() -> MyService:
    return MyService()

# In router:
async def endpoint(service: MyService = Depends(get_my_service)):
    ...
```

### Event Stream Integration
```python
from mission_control_core.core.event_stream import EventStream

async def publish_event(event_type: str, payload: dict):
    try:
        event_stream = EventStream.get_instance()
        await event_stream.publish(
            event_type=event_type,
            payload=payload,
            source="my_module"
        )
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        # Don't fail the operation if event publishing fails
```

### Database Session Pattern
```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

@router.post("/items")
async def create_item(
    item: ItemCreate,
    db: AsyncSession = Depends(get_db)
):
    service = ItemService(db)
    return await service.create(item)
```

## Emergency Contacts & Escalation

**Critical Security Issues:**
- Skills RCE vulnerability - IMMEDIATE fix required
- Any auth bypass - HIGH priority
- Data loss vulnerabilities - HIGH priority

**When in doubt:**
- Add authentication
- Validate inputs
- Log audit trails
- Ask for security review

## Documentation Standards

Every module MUST have:
1. Module-level docstring explaining purpose
2. All public functions documented
3. Security considerations documented
4. TODO comments for known issues

```python
"""
Module: skills
Purpose: PicoClaw-style skill system for agent capabilities

Security Notes:
- All skill execution requires OPERATOR role minimum
- Shell commands run in sandboxed environment
- File operations restricted to workspace directory

TODO:
- Add container-based sandboxing (Issue #123)
- Implement skill signing/verification
"""
```

## Module Security Hardening Checklist

**Use this checklist for EVERY module during implementation:**

### Security Checklist (MANDATORY)
```markdown
## Module: [MODULE_NAME]

### Authentication
- [ ] All endpoints have auth (Depends(require_auth) or require_role)
- [ ] Public/list endpoints: require_auth (read-only)
- [ ] Create/Update/Delete endpoints: require_role(OPERATOR)
- [ ] Admin endpoints: require_role(ADMIN)
- [ ] Ownership verification for agent-specific resources

### Input Validation
- [ ] All request bodies use Pydantic models with Field constraints
- [ ] File paths: No "..", no leading "/" (sandboxed)
- [ ] Text fields: max_length set (default 10000 for content)
- [ ] Numbers: min_value, max_value constraints
- [ ] Enums: Validated against allowed values
- [ ] No shell=True in subprocess (use exec not shell)

### Secrets Management
- [ ] No hardcoded secrets in code
- [ ] All secrets from os.environ with fallback error
- [ ] Secrets documented in .env.example
- [ ] No secrets logged (use logger.debug, not print)

### Data Persistence
- [ ] In-memory state migrated to PostgreSQL (AsyncSession)
- [ ] Models in /app/models/ with SQLAlchemy ORM
- [ ] Alembic migration created if schema changed
- [ ] No global singletons (use Depends() injection)

### Async/Await
- [ ] No blocking I/O (time.sleep, subprocess.run, file.read_text)
- [ ] File I/O uses aiofiles
- [ ] CPU-intensive work uses loop.run_in_executor()
- [ ] Database queries async with AsyncSession

### Error Handling
- [ ] HTTPException with sanitized messages (no internal details)
- [ ] All exceptions logged with logger.error(..., exc_info=True)
- [ ] No stack traces exposed to clients
- [ ] Rate limiting on expensive endpoints

### Testing
- [ ] Minimum 3 endpoint tests (POST, GET, DELETE)
- [ ] Auth failure test (401/403 without token)
- [ ] Input validation test (reject invalid data)
- [ ] Happy path test (valid request succeeds)
- [ ] Tests use AsyncSession fixtures

### Documentation
- [ ] Module docstring: Purpose, security notes, TODOs
- [ ] README.md: Feature overview, API endpoints, auth requirements
- [ ] CHANGELOG: New features, breaking changes, security fixes
- [ ] Endpoints documented: Method, path, auth, params, response

### Controldeck-v2 Integration
- [ ] Sidebar navigation item added
- [ ] Module page created (/app/(protected)/modules/[module]/page.tsx)
- [ ] API client hooks added (lib/api.ts + hooks/use-api.ts)
- [ ] Design system compliance (Button, Card, Badge, colors, icons)

### Pre-Commit Verification
```bash
# Run before commit:
ruff check app/modules/[MODULE]/
black --check app/modules/[MODULE]/
mypy app/modules/[MODULE]/ --no-error-summary 2>/dev/null | grep -v "Success"
pytest app/modules/[MODULE]/tests/ -v
```
```

### Vulnerability Assessment Template

```markdown
## Module: [NAME]

### Critical RCE Risks
- [ ] Shell execution: Check for subprocess.shell=True (CONVERT TO EXEC)
- [ ] File operations: Check for unconstrained paths (ADD SANDBOXING)
- [ ] Code evaluation: Check for eval/exec on user input (NEVER ALLOW)
- [ ] External commands: Check for hardcoded paths (USE SHLEX.SPLIT)

### Authentication Gaps
- [ ] Missing endpoints auth
- [ ] Overly broad role permissions
- [ ] No ownership verification for multi-tenant resources
- [ ] No rate limiting on expensive operations

### Hardcoded Secrets
- [ ] API keys
- [ ] Database credentials
- [ ] Master keys
- [ ] JWT signing keys
- [ ] Location: [file:line] → FIX: [os.environ.get solution]

### In-Memory Data Loss
- [ ] Services with self._data dicts
- [ ] Session variables not persisted
- [ ] Snapshots/states in module globals
- [ ] Event queues not stored in DB
```

---

## CURRENT AUTH SYSTEM STATUS (2026-02-13)

### Frontend Auth Implementation (control_deck)

**Architecture:**
- Next.js 14 with App Router
- Next-Auth v5 (Auth.js) with CredentialsProvider
- Server Actions for Login (POST only)
- CSRF protection ACTIVE (skipCSRFCheck removed)
- Secure cookies with __Host- prefix

**Key Files:**
- `/frontend/control_deck/auth.ts` - NextAuth config with CredentialsProvider
- `/frontend/control_deck/app/auth/actions.ts` - Server Actions for login/logout
- `/frontend/control_deck/app/auth/signin/signin-form.tsx` - Client login form
- `/frontend/control_deck/lib/auth-helpers.ts` - Helper functions (hasRequiredRole, canAccessAxe)
- `/frontend/control_deck/middleware.ts` - Route protection middleware

**Demo Login:**
- Email: any valid email format
- Password: "brain"
- Role: "admin" assigned automatically

**Known Issues:**
- Login form crashes with "result is undefined" error
- Server action returns undefined on success (redirect called instead)
- Type mismatch in authorize callback (credentials.email type)

### Required Analysis

Claude Code should analyze:
1. `auth.ts` - Type safety in authorize callback
2. `app/auth/actions.ts` - Return value handling (redirect vs result)
3. `app/auth/signin/signin-form.tsx` - Error handling for undefined results
4. `middleware.ts` - Route protection logic
5. Cookie configuration for CSRF

### Security Requirements
- CSRF must remain ENABLED
- No credentials in URL (GET params)
- HttpOnly, Secure, SameSite cookies
- POST-only authentication
- Proper error handling without information leakage

---

**Last Updated:** 2026-02-13
**Version:** BRAiN v0.3.0 Auth System Fix
**Audit Status:** Auth System Analysis Required
