# 🚀 BRAiN Production Roadmap

**Version:** 1.0.0
**Erstellt:** 2026-01-17
**Ziel:** Production-Ready in 3-4 Wochen
**Status:** 🟡 In Progress (75% Ready)

---

## 📊 Executive Summary

### Systemstatus

| System | Status | Production-Ready | Blocker |
|--------|--------|------------------|---------|
| **Backend** | 🟡 75% | ⚠️ Security Fixes | Rate Limiting, CORS, Default Passwords |
| **Control Deck** | 🟡 60% | ⚠️ Backend Connection + Responsive | .env.local fehlt, Sidebar nicht responsive |
| **AXE UI** | 🟡 75% | ⚠️ Backend Connection | .env.local fehlt, Ollama Config |

### Kritische Blocker (Production Go/No-Go)

1. ❌ **Backend:** Keine Rate Limiting → DoS-Risiko
2. ❌ **Backend:** CORS Wildcard → XSS-Risiko
3. ❌ **Backend:** Default Passwörter (admin/password) → Security Bypass
4. ❌ **Beide Frontends:** Keine Backend-Verbindung → TypeError: Failed to fetch
5. ❌ **Control Deck:** Sidebar nicht responsive → Mobile unusable

### Zeitplan (Standard-Annahme: Solo, 4-6h/Tag)

```
Woche 1 (Tag 1-7):   Phase 0 + Phase 1 (Quick Wins + Security)
Woche 2 (Tag 8-14):  Phase 2 (Core Features)
Woche 3 (Tag 15-21): Phase 3 (UX Polish)
Woche 4 (Tag 22-28): Testing + Production Deployment
```

---

## 📅 Phase 0: Quick Wins (Tag 1-3)

**Ziel:** Sofortige Verbesserungen mit minimalem Aufwand (max. 2h pro Task)
**Dauer:** 1-3 Tage
**Impact:** Hoher Nutzen bei geringem Aufwand

### Tag 1: Backend-Verbindung herstellen (2h)

#### Task 1.1: Frontend Environment Variables erstellen
**System:** Control Deck + AXE UI
**Priorität:** 🔥 CRITICAL
**Aufwand:** 15 Minuten
**Impact:** ⭐⭐⭐⭐⭐ (Behebt alle "Failed to fetch" Fehler)

**Schritte:**
```bash
# Control Deck
cd /home/user/BRAiN/frontend/control_deck
echo "NEXT_PUBLIC_BRAIN_API_BASE=https://api.dev.brain.falklabs.de" > .env.local

# AXE UI
cd /home/user/BRAiN/frontend/axe_ui
echo "NEXT_PUBLIC_BRAIN_API_BASE=https://api.dev.brain.falklabs.de" > .env.local
```

**Verification:**
```bash
# Start frontend
npm run dev

# Check in Browser Console (should show data, not errors)
```

**Expected Result:** Alle Frontends zeigen echte Daten von Production API

---

#### Task 1.2: Ollama Host konfigurieren (Backend)
**System:** Backend
**Priorität:** 🔥 CRITICAL
**Aufwand:** 10 Minuten
**Impact:** ⭐⭐⭐⭐⭐ (AXE Chat funktioniert)

**Schritte:**
```bash
cd /home/user/BRAiN/backend

# In .env oder .env.local setzen:
echo "OLLAMA_HOST=http://YOUR_OLLAMA_SERVER:11434" >> .env.local

# ODER wenn Ollama lokal:
echo "OLLAMA_HOST=http://localhost:11434" >> .env.local
```

**Verification:**
```bash
# Test Ollama Connection
curl http://YOUR_OLLAMA_SERVER:11434/api/tags

# Test via Backend
curl -X POST https://api.dev.brain.falklabs.de/api/llm-ping
```

**Expected Result:** AXE Chat Responses von Ollama

---

#### Task 1.3: CORS Wildcard entfernen (Backend)
**System:** Backend
**Priorität:** 🔥 CRITICAL (Security)
**Aufwand:** 30 Minuten
**Impact:** ⭐⭐⭐⭐⭐ (Schließt XSS-Lücke)

**File:** `backend/main.py` (Line 185-200)

**Änderung:**
```python
# VORHER (main.py Line 185-192):
cors_origins = settings.cors_origins if hasattr(settings, 'cors_origins') else [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
    "*",  # ❌ REMOVE THIS!
]

# NACHHER:
cors_origins = [
    # Production
    "https://api.dev.brain.falklabs.de",
    "https://control.dev.brain.falklabs.de",
    "https://axe.dev.brain.falklabs.de",
    # Staging (if exists)
    "https://api.stage.brain.falklabs.de",
    "https://control.stage.brain.falklabs.de",
    "https://axe.stage.brain.falklabs.de",
    # Local Development
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
]
```

**Verification:**
```bash
# Test CORS Header
curl -H "Origin: https://evil.com" https://api.dev.brain.falklabs.de/api/health -I
# Should NOT have: Access-Control-Allow-Origin: *
```

**Commit:**
```bash
git add backend/main.py
git commit -m "fix(security): Remove CORS wildcard, use explicit origins"
```

---

### Tag 2: Security Quick Fixes (4h)

#### Task 2.1: Default Passwörter ändern (Force Change)
**System:** Backend
**Priorität:** 🔥 CRITICAL (Security)
**Aufwand:** 1 Stunde
**Impact:** ⭐⭐⭐⭐⭐ (Verhindert Auth Bypass)

**File:** `backend/app/core/security.py`

**Option A: Environment Variables (Empfohlen)**
```python
# app/core/security.py
import os

ADMIN_PASSWORD = os.getenv("BRAIN_ADMIN_PASSWORD", "CHANGE_ME_NOW")
OPERATOR_PASSWORD = os.getenv("BRAIN_OPERATOR_PASSWORD", "CHANGE_ME_NOW")

if ADMIN_PASSWORD == "CHANGE_ME_NOW" and os.getenv("ENVIRONMENT") == "production":
    raise RuntimeError("FATAL: BRAIN_ADMIN_PASSWORD not set in production!")

USERS_DB = {
    "admin": User(
        username="admin",
        password_hash=get_password_hash(ADMIN_PASSWORD),
        ...
    ),
}
```

**Option B: Force Password Change on First Login**
```python
# app/api/routes/auth.py
@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)

    # Check if using default password
    if user.username == "admin" and form_data.password == "password":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "password_change_required",
                "message": "You must change the default password before using the system",
            }
        )

    return create_access_token(...)
```

**Deployment:**
```bash
# In Production .env
BRAIN_ADMIN_PASSWORD=<secure-random-password>
BRAIN_OPERATOR_PASSWORD=<secure-random-password>
```

---

#### Task 2.2: Security Headers Middleware hinzufügen
**System:** Backend
**Priorität:** 🔥 CRITICAL (Security)
**Aufwand:** 30 Minuten
**Impact:** ⭐⭐⭐⭐ (OWASP Compliance)

**File:** `backend/main.py` (nach Line 211, vor Root Endpoints)

**Code:**
```python
# Security Headers Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security Headers (OWASP Recommendations)
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        })

        # HSTS only in production
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

# Add middleware (in create_app() function, after CORS)
app.add_middleware(SecurityHeadersMiddleware)
```

**Verification:**
```bash
curl -I https://api.dev.brain.falklabs.de/api/health | grep X-
# Should show all security headers
```

---

#### Task 2.3: Rate Limiting implementieren
**System:** Backend
**Priorität:** 🔥 CRITICAL (Security)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐⭐⭐ (DoS Protection)

**Installation:**
```bash
cd backend
pip install slowapi
echo "slowapi" >> requirements.txt
```

**File:** `backend/main.py` (in create_app())

**Code:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

def create_app() -> FastAPI:
    app = FastAPI(...)

    # Rate Limiter Setup
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["100/minute"],  # Global limit
        storage_uri=settings.redis_url,  # Use Redis for distributed rate limiting
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ... rest of setup
```

**Apply to sensitive endpoints:**

**File:** `backend/app/api/routes/auth.py`
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    ...
```

**File:** `backend/api/routes/axe.py` (AXE Chat)
```python
@router.post("/chat")
@limiter.limit("30/minute")  # Max 30 chat messages per minute
async def chat(request: Request, payload: ChatPayload):
    ...
```

**Verification:**
```bash
# Test rate limit
for i in {1..10}; do curl -X POST https://api.dev.brain.falklabs.de/api/auth/login -d "username=test&password=test"; done
# After 5 attempts: Should return 429 Too Many Requests
```

---

### Tag 3: Frontend Connection Tests (2h)

#### Task 3.1: Test Control Deck mit Production API
**System:** Control Deck
**Priorität:** HIGH
**Aufwand:** 30 Minuten
**Impact:** ⭐⭐⭐⭐ (Verifies Integration)

**Steps:**
```bash
cd frontend/control_deck
npm run dev

# Open Browser: http://localhost:3000/dashboard
# Expected:
# ✅ Dashboard loads
# ✅ Mission statistics show real data
# ✅ System health shows "ok"
# ✅ No "TypeError: Failed to fetch"
```

**Test Checklist:**
- [ ] Dashboard zeigt Daten
- [ ] Missions Page zeigt Daten
- [ ] Settings/LLM zeigt Config
- [ ] Keine Console Errors

---

#### Task 3.2: Test AXE UI mit Production API
**System:** AXE UI
**Priorität:** HIGH
**Aufwand:** 30 Minuten
**Impact:** ⭐⭐⭐⭐ (Verifies Chat)

**Steps:**
```bash
cd frontend/axe_ui
npm run dev

# Open Browser: http://localhost:3002/widget-test
# Expected:
# ✅ Widget loads
# ✅ WebSocket connects (🟢 Connected)
# ✅ Chat message sends
# ✅ LLM responds (if Ollama configured)
```

**Test Checklist:**
- [ ] Widget erscheint
- [ ] Expanded Panel öffnet
- [ ] WebSocket Status: Connected
- [ ] Chat funktioniert
- [ ] Diff Apply/Reject funktioniert

---

#### Task 3.3: Fix Frontend Errors (if any)
**System:** Both Frontends
**Priorität:** HIGH
**Aufwand:** 1 Stunde
**Impact:** ⭐⭐⭐⭐

**Common Issues:**
1. **CORS Error** → Backend CORS origins prüfen
2. **401 Unauthorized** → Auth header fehlt (optional für public endpoints)
3. **Connection Refused** → Backend läuft nicht
4. **Timeout** → Backend überlastet oder Firewall

**Debugging:**
```javascript
// In Browser Console
console.log(process.env.NEXT_PUBLIC_BRAIN_API_BASE)
// Should show: https://api.dev.brain.falklabs.de

// Test API manually
fetch('https://api.dev.brain.falklabs.de/api/health')
  .then(r => r.json())
  .then(console.log)
```

---

## 📅 Phase 1: Security Hardening (Tag 4-7)

**Ziel:** Production-kritische Sicherheitslücken schließen
**Dauer:** 3-5 Tage
**Impact:** Go/No-Go für Production

### Tag 4: Request Logging & Audit Trail (4h)

#### Task 4.1: Audit Middleware implementieren
**System:** Backend
**Priorität:** HIGH (Compliance)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐⭐ (DSGVO Art. 30 Compliance)

**File:** `backend/app/core/audit.py` (NEW)

**Code:**
```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time
import logging
from typing import Callable

logger = logging.getLogger("audit")

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        # Extract request info
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Process request
        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log request
            logger.info(
                f"{method} {path} [{response.status_code}] "
                f"{duration:.2f}s from {client_ip}"
            )

            # Store critical operations in DB
            if self._is_sensitive_endpoint(path):
                await self._store_audit_log(
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    client_ip=client_ip,
                    duration=duration,
                    user=request.state.user if hasattr(request.state, 'user') else None,
                )

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{method} {path} FAILED: {e} ({duration:.2f}s)")
            raise

    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Check if endpoint requires audit trail"""
        sensitive_prefixes = [
            "/api/auth/",
            "/api/agent-ops/",
            "/api/policy/",
            "/api/governance/",
            "/api/neurorail/",
        ]
        return any(path.startswith(prefix) for prefix in sensitive_prefixes)

    async def _store_audit_log(self, **kwargs):
        """Store audit log in database (implement based on your schema)"""
        # TODO: Implement database storage
        pass
```

**Integration in main.py:**
```python
from app.core.audit import AuditMiddleware

def create_app():
    app = FastAPI(...)
    app.add_middleware(AuditMiddleware)
    ...
```

---

#### Task 4.2: Failed Login Tracking
**System:** Backend
**Priorität:** HIGH (Security)
**Aufwand:** 1 Stunde
**Impact:** ⭐⭐⭐⭐ (Detect Brute Force)

**File:** `backend/app/api/routes/auth.py`

**Code:**
```python
from collections import defaultdict
from datetime import datetime, timedelta

# In-memory failed login tracker (use Redis in production)
failed_logins = defaultdict(list)
LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION = timedelta(minutes=15)

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    client_ip = request.client.host

    # Check if IP is locked out
    if _is_locked_out(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again in 15 minutes."
        )

    # Authenticate
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        # Record failed login
        failed_logins[client_ip].append(datetime.now())
        _cleanup_old_attempts(client_ip)

        # Log for monitoring
        logger.warning(f"Failed login attempt from {client_ip} for user {form_data.username}")

        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )

    # Success - clear failed attempts
    failed_logins.pop(client_ip, None)

    # Create token
    access_token = create_access_token(...)
    return {"access_token": access_token, "token_type": "bearer"}

def _is_locked_out(ip: str) -> bool:
    """Check if IP is locked out due to too many failed attempts"""
    attempts = failed_logins.get(ip, [])
    recent_attempts = [
        attempt for attempt in attempts
        if datetime.now() - attempt < LOCKOUT_DURATION
    ]
    return len(recent_attempts) >= LOCKOUT_THRESHOLD

def _cleanup_old_attempts(ip: str):
    """Remove attempts older than lockout duration"""
    cutoff = datetime.now() - LOCKOUT_DURATION
    failed_logins[ip] = [
        attempt for attempt in failed_logins[ip]
        if attempt > cutoff
    ]
```

---

#### Task 4.3: Sensitive Data Logging Filter
**System:** Backend
**Priorität:** MEDIUM (Privacy)
**Aufwand:** 1 Stunde
**Impact:** ⭐⭐⭐ (DSGVO Compliance)

**File:** `backend/app/core/logging.py`

**Code:**
```python
import re
import logging

class SensitiveDataFilter(logging.Filter):
    """Filter to remove sensitive data from logs"""

    PATTERNS = [
        (r'"password"\s*:\s*"[^"]*"', '"password": "***REDACTED***"'),
        (r'"token"\s*:\s*"[^"]*"', '"token": "***REDACTED***"'),
        (r'"api_key"\s*:\s*"[^"]*"', '"api_key": "***REDACTED***"'),
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***EMAIL***'),
        (r'\b\d{3}-\d{2}-\d{4}\b', '***SSN***'),  # US Social Security
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        for pattern, replacement in self.PATTERNS:
            message = re.sub(pattern, replacement, message)

        record.msg = message
        record.args = ()  # Clear args to prevent formatting issues

        return True

# Add filter to all loggers
def configure_logging():
    logging.basicConfig(...)

    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    for handler in logging.root.handlers:
        handler.addFilter(sensitive_filter)
```

---

### Tag 5-6: Input Validation & Sanitization (6h)

#### Task 5.1: Max Length Validation für alle String Inputs
**System:** Backend
**Priorität:** MEDIUM (Security)
**Aufwand:** 3 Stunden
**Impact:** ⭐⭐⭐ (DoS Prevention)

**Pattern:**
```python
from pydantic import BaseModel, Field, validator

class MissionEnqueueRequest(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = Field(..., max_length=2000)
    payload: dict = Field(..., max_length=10000)  # JSON size limit

    @validator('payload')
    def validate_payload_size(cls, v):
        import json
        json_str = json.dumps(v)
        if len(json_str) > 100_000:  # 100KB limit
            raise ValueError('Payload too large (max 100KB)')
        return v
```

**Apply to all Pydantic models in:**
- `backend/app/modules/*/schemas.py`
- `backend/api/routes/*.py` (inline models)

**Test:**
```bash
# Test with oversized payload
curl -X POST https://api.dev.brain.falklabs.de/api/missions/enqueue \
  -H "Content-Type: application/json" \
  -d '{"name": "x", "description": "'$(python3 -c 'print("x"*10000)')'"}'
# Should return 422 Validation Error
```

---

#### Task 5.2: Regex Validation für kritische Felder
**System:** Backend
**Priorität:** MEDIUM (Security)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐ (Injection Prevention)

**Pattern:**
```python
from pydantic import BaseModel, Field, validator
import re

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=255)

    @validator('username')
    def validate_username(cls, v):
        # Only alphanumeric + underscore + hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username contains invalid characters')
        return v

    @validator('email')
    def validate_email(cls, v):
        # Simple email regex (not RFC-compliant, but good enough)
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v

class AgentNameRequest(BaseModel):
    agent_id: str = Field(..., max_length=100)

    @validator('agent_id')
    def validate_agent_id(cls, v):
        # Prevent path traversal
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError('Agent ID contains invalid characters')
        return v
```

---

#### Task 5.3: SQL Injection Protection Audit
**System:** Backend
**Priorität:** HIGH (Security)
**Aufwand:** 1 Stunde
**Impact:** ⭐⭐⭐⭐ (Critical Security)

**Audit Checklist:**
```bash
# Search for raw SQL queries
grep -r "execute(" backend/ | grep -v "sqlalchemy"
grep -r "raw(" backend/
grep -r "text(" backend/

# Expected: No results (all via SQLAlchemy ORM)
```

**If found, refactor:**
```python
# ❌ BAD: Raw SQL
db.execute(f"SELECT * FROM users WHERE username = '{username}'")

# ✅ GOOD: SQLAlchemy ORM
stmt = select(User).where(User.username == username)
result = await db.execute(stmt)

# ✅ ACCEPTABLE: Parameterized query
from sqlalchemy import text
stmt = text("SELECT * FROM users WHERE username = :username")
result = await db.execute(stmt, {"username": username})
```

---

### Tag 7: HTTPS & Production Config (2h)

#### Task 7.1: Force HTTPS in Production
**System:** Backend
**Priorität:** HIGH (Security)
**Aufwand:** 30 Minuten
**Impact:** ⭐⭐⭐⭐ (Man-in-the-Middle Protection)

**File:** `backend/main.py`

**Code:**
```python
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

def create_app():
    app = FastAPI(...)

    # Force HTTPS in production
    if settings.environment == "production":
        app.add_middleware(HTTPSRedirectMiddleware)

    ...
```

---

#### Task 7.2: Environment-Based Configuration Validation
**System:** Backend
**Priorität:** MEDIUM (Ops)
**Aufwand:** 1 Stunde
**Impact:** ⭐⭐⭐ (Prevent Misconfig)

**File:** `backend/app/core/config.py`

**Code:**
```python
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    environment: str = "development"

    # Security
    cors_origins: list[str] = []
    admin_password: str = "CHANGE_ME"

    @validator('environment')
    def validate_environment(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError(f"Invalid environment: {v}")
        return v

    @validator('admin_password')
    def validate_admin_password(cls, v, values):
        # In production, admin password must be set and strong
        if values.get('environment') == 'production':
            if v == "CHANGE_ME":
                raise ValueError(
                    "FATAL: BRAIN_ADMIN_PASSWORD must be set in production!"
                )
            if len(v) < 12:
                raise ValueError(
                    "FATAL: Admin password must be at least 12 characters!"
                )
        return v

    @validator('cors_origins')
    def validate_cors(cls, v, values):
        # In production, no wildcard allowed
        if values.get('environment') == 'production':
            if "*" in v:
                raise ValueError(
                    "FATAL: CORS wildcard not allowed in production!"
                )
            if not v:
                raise ValueError(
                    "FATAL: CORS origins must be set in production!"
                )
        return v
```

**Test:**
```bash
# Test production validation
ENVIRONMENT=production \
BRAIN_ADMIN_PASSWORD=weak \
python3 backend/main.py
# Should fail with validation error
```

---

#### Task 7.3: Deployment Checklist erstellen
**System:** Documentation
**Priorität:** MEDIUM (Ops)
**Aufwand:** 30 Minuten
**Impact:** ⭐⭐⭐ (Prevent Errors)

**File:** `DEPLOYMENT_CHECKLIST.md` (NEW)

**Content:**
```markdown
# Deployment Checklist

## Pre-Deployment

### Backend
- [ ] All tests pass (`pytest backend/`)
- [ ] No hardcoded secrets in code
- [ ] Environment variables set in .env
  - [ ] BRAIN_ADMIN_PASSWORD (min 12 chars)
  - [ ] OLLAMA_HOST (correct URL)
  - [ ] CORS_ORIGINS (no wildcard)
  - [ ] DATABASE_URL (production DB)
  - [ ] REDIS_URL (production Redis)
- [ ] Security headers enabled
- [ ] Rate limiting configured
- [ ] HTTPS redirect enabled

### Frontend (Control Deck)
- [ ] Build succeeds (`npm run build`)
- [ ] NEXT_PUBLIC_BRAIN_API_BASE set correctly
- [ ] No console errors in production build

### Frontend (AXE UI)
- [ ] Build succeeds (`npm run build`)
- [ ] NEXT_PUBLIC_BRAIN_API_BASE set correctly
- [ ] WebSocket connects to production API

## Deployment

- [ ] Database migration applied (`alembic upgrade head`)
- [ ] Docker containers healthy
- [ ] Nginx config updated
- [ ] SSL certificate valid
- [ ] DNS records correct

## Post-Deployment

- [ ] Health check passes (`/api/health`)
- [ ] Login works (no default passwords)
- [ ] Rate limiting works (test with curl)
- [ ] CORS works (test from browser)
- [ ] WebSocket works (test AXE chat)
- [ ] Logs show no errors

## Monitoring

- [ ] Prometheus metrics available
- [ ] Error tracking configured (Sentry)
- [ ] Uptime monitoring active
```

---

## 📅 Phase 2: Core Features (Tag 8-14)

**Ziel:** Fehlende Funktionalität implementieren
**Dauer:** 1 Woche
**Impact:** User Experience

### Tag 8-9: Control Deck - Responsive Sidebar (8h)

#### Task 8.1: Responsive Sidebar Component
**System:** Control Deck
**Priorität:** HIGH (UX)
**Aufwand:** 4 Stunden
**Impact:** ⭐⭐⭐⭐⭐ (Mobile Support)

**File:** `frontend/control_deck/components/ui/sidebar.tsx` (REWRITE)

**Implementation:** (See Control Deck Report - Responsive Sidebar Section)

**Key Features:**
- Mobile (<768px): Overlay mit Backdrop
- Tablet (768-1024px): Kollabierbar (Icons only)
- Desktop (>1024px): Vollständig expanded
- Touch-Gesten Support
- Smooth Animations

**Test:**
```bash
# Test auf verschiedenen Bildschirmgrößen
# Chrome DevTools → Device Toolbar
# iPhone SE (375px)
# iPad (768px)
# Desktop (1920px)
```

**Acceptance Criteria:**
- [ ] Sidebar öffnet/schließt auf Mobile
- [ ] Backdrop schließt Sidebar bei Click
- [ ] Icons-only Mode auf Tablet
- [ ] Vollständige Sidebar auf Desktop
- [ ] Smooth Transitions

---

#### Task 8.2: Navigation Vereinfachen (32 → 15 Items)
**System:** Control Deck
**Priorität:** MEDIUM (UX)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐ (Reduce Complexity)

**File:** `frontend/control_deck/components/app-sidebar.tsx`

**Changes:**
```typescript
// VORHER: 32 Menu Items in 3 Gruppen

// NACHHER: 15 Items mit intelligenter Gruppierung
const navMain = [
  {
    title: "Dashboard",
    url: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "Missions",
    icon: Workflow,
    items: [
      { title: "Overview", url: "/missions" },
      { title: "History", url: "/missions/history" },
    ]
  },
  {
    title: "Agents",
    icon: Bot,
    items: [
      { title: "Management", url: "/core/agents" },
      { title: "Constitutional", url: "/constitutional" },
    ]
  },
  {
    title: "NeuroRail",
    icon: GitBranch,
    items: [
      { title: "Trace Explorer", url: "/neurorail/trace-explorer" },
      { title: "Health Matrix", url: "/neurorail/health-matrix" },
    ]
  },
  {
    title: "System",
    icon: Settings2,
    items: [
      { title: "Health", url: "/health" },
      { title: "Settings", url: "/settings" },
      { title: "Immune", url: "/immune" },
    ]
  },
];

// Remove: Placeholder pages (Courses, Business, WebGenesis, etc.)
// Keep: Production-ready features only
```

**Benefits:**
- Less cognitive overload
- Faster navigation
- Cleaner UI

---

#### Task 8.3: Mobile Navigation Patterns
**System:** Control Deck
**Priorität:** MEDIUM (UX)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐ (Mobile UX)

**Features:**
- Bottom Tab Bar auf Mobile (Alternative zur Sidebar)
- Hamburger Menu
- Swipe Gestures

**File:** `frontend/control_deck/components/mobile-navigation.tsx` (NEW)

**Implementation:**
```typescript
"use client"

import { Home, List, Settings, Menu } from "lucide-react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import { useSidebar } from "./ui/sidebar"

export function MobileNavigation() {
  const pathname = usePathname()
  const { toggle } = useSidebar()

  // Only show on mobile
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
  if (!isMobile) return null

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-slate-900 border-t border-slate-800 md:hidden">
      <div className="flex items-center justify-around h-16">
        <Link href="/dashboard" className={pathname === '/dashboard' ? 'text-blue-500' : ''}>
          <Home className="h-6 w-6" />
        </Link>
        <Link href="/missions" className={pathname.startsWith('/missions') ? 'text-blue-500' : ''}>
          <List className="h-6 w-6" />
        </Link>
        <Link href="/settings" className={pathname.startsWith('/settings') ? 'text-blue-500' : ''}>
          <Settings className="h-6 w-6" />
        </Link>
        <button onClick={toggle}>
          <Menu className="h-6 w-6" />
        </button>
      </div>
    </nav>
  )
}
```

---

### Tag 10-11: AXE UI - Widget Package (8h)

#### Task 10.1: Vite Build Config für npm Package
**System:** AXE UI
**Priorität:** HIGH (Embedding)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐⭐⭐ (External Usage)

**File:** `frontend/axe_ui/vite.config.ts` (NEW)

**Implementation:** (See AXE UI Report - npm Package Section)

```bash
cd frontend/axe_ui
npm install -D vite vite-plugin-dts @vitejs/plugin-react
npm run build:package
# → Generates dist/ folder
```

---

#### Task 10.2: Package Testing & Documentation
**System:** AXE UI
**Priorität:** HIGH (Embedding)
**Aufwand:** 3 Stunden
**Impact:** ⭐⭐⭐⭐ (Usability)

**Files:**
- `frontend/axe_ui/README_PACKAGE.md` (NEW)
- `frontend/axe_ui/EXAMPLES.md` (NEW)

**Test in External Project:**
```bash
cd /tmp
npx create-next-app test-axe-widget
cd test-axe-widget
npm install /home/user/BRAiN/frontend/axe_ui/brain-axe-widget-1.0.0.tgz

# In app/page.tsx:
import { FloatingAxe } from '@brain/axe-widget'
import '@brain/axe-widget/dist/style.css'

export default function Home() {
  return (
    <div>
      <h1>Test Page</h1>
      <FloatingAxe
        appId="test-app"
        backendUrl="https://api.dev.brain.falklabs.de"
      />
    </div>
  )
}
```

---

#### Task 10.3: Widget Deployment to FeWoHeroes (Test)
**System:** AXE UI
**Priorität:** MEDIUM (Real-World Test)
**Aufwand:** 3 Stunden
**Impact:** ⭐⭐⭐⭐ (Production Validation)

**Steps:**
1. Build package
2. Publish to npm (or private registry)
3. Install in FeWoHeroes project
4. Test integration
5. Document issues

**Expected Issues:**
- CSS conflicts
- z-index problems
- WebSocket CORS
- Performance overhead

---

### Tag 12-13: Backend - Caching & Performance (8h)

#### Task 12.1: Response Caching mit aiocache
**System:** Backend
**Priorität:** MEDIUM (Performance)
**Aufwand:** 3 Stunden
**Impact:** ⭐⭐⭐⭐ (Latency Reduction)

**Installation:**
```bash
cd backend
pip install aiocache
echo "aiocache" >> requirements.txt
```

**File:** `backend/app/core/cache.py` (NEW)

**Code:**
```python
from aiocache import caches
from aiocache.serializers import JsonSerializer

# Configure cache
caches.set_config({
    'default': {
        'cache': "aiocache.RedisCache",
        'endpoint': "redis",
        'port': 6379,
        'timeout': 1,
        'serializer': {
            'class': "aiocache.serializers.JsonSerializer"
        }
    }
})

from aiocache import cached

# Usage
@cached(ttl=60, key="system_health")
async def get_system_health():
    # Expensive operation
    return await compute_health()
```

**Apply to:**
```python
# app/api/routes/health.py
@router.get("/api/health")
@cached(ttl=10, key="api_health")
async def api_health():
    return {"status": "ok"}

@router.get("/api/system/health")
@cached(ttl=30, key="system_health")
async def system_health():
    return await compute_system_health()

# api/routes/missions.py
@router.get("/info")
@cached(ttl=60, key="missions_info")
async def missions_info():
    return {...}
```

**Test:**
```bash
# First call: Slow (compute)
time curl https://api.dev.brain.falklabs.de/api/system/health

# Second call: Fast (cached)
time curl https://api.dev.brain.falklabs.de/api/system/health
```

---

#### Task 12.2: Database Indexe hinzufügen
**System:** Backend
**Priorität:** MEDIUM (Performance)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐⭐ (Query Speed)

**File:** `backend/alembic/versions/XXX_add_indexes.py` (NEW)

**Create Migration:**
```bash
cd backend
alembic revision -m "Add performance indexes"
```

**Code:**
```python
def upgrade():
    # Missions table
    op.create_index('idx_missions_status', 'missions', ['status'])
    op.create_index('idx_missions_created_at', 'missions', ['created_at'])
    op.create_index('idx_missions_priority', 'missions', ['priority'])

    # NeuroRail Audit table
    op.create_index('idx_neurorail_audit_mission_id', 'neurorail_audit', ['mission_id'])
    op.create_index('idx_neurorail_audit_timestamp', 'neurorail_audit', ['timestamp'])
    op.create_index('idx_neurorail_audit_event_type', 'neurorail_audit', ['event_type'])

    # Users table
    op.create_index('idx_users_username', 'users', ['username'])

def downgrade():
    op.drop_index('idx_missions_status')
    op.drop_index('idx_missions_created_at')
    # ... etc
```

**Apply:**
```bash
alembic upgrade head
```

---

#### Task 12.3: Pagination für Listen-Endpoints
**System:** Backend
**Priorität:** MEDIUM (Performance)
**Aufwand:** 3 Stunden
**Impact:** ⭐⭐⭐⭐ (Prevent OOM)

**Pattern:**
```python
from fastapi import Query

@router.get("/missions")
async def list_missions(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    status: str | None = Query(None, description="Filter by status"),
):
    # Query with pagination
    query = select(Mission).offset(skip).limit(limit)

    if status:
        query = query.where(Mission.status == status)

    result = await db.execute(query)
    missions = result.scalars().all()

    # Count total (for pagination metadata)
    count_query = select(func.count(Mission.id))
    if status:
        count_query = count_query.where(Mission.status == status)
    total = await db.scalar(count_query)

    return {
        "data": missions,
        "pagination": {
            "skip": skip,
            "limit": limit,
            "total": total,
            "has_more": skip + limit < total,
        }
    }
```

**Apply to:**
- `/api/missions`
- `/api/agents`
- `/api/neurorail/v1/audit/events`
- `/api/policy/policies`

---

### Tag 14: Testing & Bug Fixes (4h)

#### Task 14.1: E2E Tests für kritische Flows
**System:** Backend + Frontends
**Priorität:** HIGH (Quality)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐⭐ (Prevent Regressions)

**Test Cases:**
1. **Login Flow**
   - POST /api/auth/login
   - Verify JWT token
   - GET /api/auth/me

2. **Mission Flow**
   - POST /api/missions/enqueue
   - GET /api/missions/queue (verify mission in queue)
   - Wait for completion
   - GET /api/missions/{id} (verify status)

3. **AXE Chat Flow**
   - WebSocket connect
   - Send chat message
   - Receive response
   - Disconnect

**File:** `backend/tests/test_e2e_critical.py` (NEW)

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_login_flow():
    # Login
    response = client.post("/api/auth/login", data={
        "username": os.getenv("TEST_USERNAME", "testuser"),
        "password": os.getenv("TEST_PASSWORD", "testpass"),
    })
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Get current user
    response = client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

def test_mission_flow():
    # Enqueue
    response = client.post("/api/missions/enqueue", json={
        "name": "Test Mission",
        "description": "E2E Test",
        "priority": "NORMAL",
        "payload": {"test": True},
    })
    assert response.status_code == 200
    mission_id = response.json()["mission_id"]

    # Verify in queue
    response = client.get("/api/missions/queue")
    mission_ids = [m["id"] for m in response.json()]
    assert mission_id in mission_ids
```

**Run:**
```bash
cd backend
pytest tests/test_e2e_critical.py -v
```

---

#### Task 14.2: Bug Fixes aus Testing
**System:** All
**Priorität:** HIGH (Quality)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐⭐ (Stability)

**Common Issues:**
- Race conditions
- Null pointer exceptions
- Type mismatches
- Edge cases

**Process:**
1. Document bug
2. Write failing test
3. Fix bug
4. Verify test passes
5. Commit with reference to test

---

## 📅 Phase 3: UX Polish (Tag 15-21)

**Ziel:** User Experience verbessern
**Dauer:** 1 Woche
**Impact:** User Satisfaction

### Tag 15-17: Hilfesystem implementieren (12h)

#### Task 15.1: i18n Setup (react-i18next)
**System:** Control Deck + AXE UI
**Priorität:** MEDIUM (UX)
**Aufwand:** 3 Stunden
**Impact:** ⭐⭐⭐⭐ (Multi-Language Support)

**Implementation:** (See Control Deck Report - Mehrsprachigkeit Section)

**Steps:**
1. Install react-i18next
2. Setup i18n config
3. Create translation files (DE + EN)
4. Add Language Switcher
5. Replace hardcoded strings

**Files:**
```
frontend/control_deck/
├── lib/i18n.ts (NEW)
├── public/locales/
│   ├── de/
│   │   ├── common.json
│   │   └── tooltips.json
│   └── en/
│       ├── common.json
│       └── tooltips.json
└── components/language-switcher.tsx (NEW)
```

---

#### Task 15.2: Inline Tooltips (Radix UI)
**System:** Control Deck
**Priorität:** HIGH (UX)
**Aufwand:** 4 Stunden
**Impact:** ⭐⭐⭐⭐ (User Guidance)

**Implementation:** (See Control Deck Report - Tier 1 Tooltips Section)

**Apply to:**
- Settings Forms (LLM Config)
- Dashboard KPIs
- Button ohne Label
- Complex Features (NeuroRail, DNA, etc.)

**Example:**
```typescript
<div className="flex items-center gap-2">
  <Label>Temperature</Label>
  <TooltipHelp i18nKey="settings.llm.temperature" />
</div>
```

---

#### Task 15.3: Contextual Help Panel (Sheet)
**System:** Control Deck
**Priorität:** MEDIUM (UX)
**Aufwand:** 3 Stunden
**Impact:** ⭐⭐⭐ (Detailed Help)

**Implementation:** (See Control Deck Report - Tier 2 Help Panel Section)

**Features:**
- Slide-out panel
- Markdown content
- Page-specific help
- Search

---

#### Task 15.4: Help Content erstellen (Top 5 Pages)
**System:** Control Deck
**Priorität:** MEDIUM (UX)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐ (Documentation)

**Pages:**
1. Dashboard
2. Missions
3. Settings/LLM
4. NeuroRail Trace Explorer
5. Agent Management

**Content Structure:**
```markdown
# Page Title

## Übersicht
Was macht diese Seite?

## Features
- Feature 1
- Feature 2

## Tipps
Praktische Hinweise

## Häufige Probleme
Troubleshooting
```

---

### Tag 18-19: UI/UX Improvements (8h)

#### Task 18.1: Dashboard Charts (Recharts)
**System:** Control Deck
**Priorität:** MEDIUM (UX)
**Aufwand:** 4 Stunden
**Impact:** ⭐⭐⭐ (Data Visualization)

**File:** `frontend/control_deck/app/dashboard/page.tsx`

**Replace Placeholder:**
```typescript
// VORHER:
<div className="border-dashed border text-neutral-500">
  Chart placeholder
</div>

// NACHHER:
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

function ActivityChart({ data }: { data: any[] }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="time" stroke="#9CA3AF" />
        <YAxis stroke="#9CA3AF" />
        <Tooltip
          contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
        />
        <Line type="monotone" dataKey="missions" stroke="#3B82F6" strokeWidth={2} />
        <Line type="monotone" dataKey="agents" stroke="#10B981" strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  )
}
```

**Data Source:**
```typescript
// Fetch from /api/telemetry/timeseries
const { data } = useQuery({
  queryKey: ['telemetry', 'activity'],
  queryFn: () => fetch('/api/telemetry/timeseries?period=1h').then(r => r.json()),
  refetchInterval: 30000,
})
```

---

#### Task 18.2: Loading States & Skeletons
**System:** Control Deck
**Priorität:** MEDIUM (UX)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐ (Perceived Performance)

**File:** `frontend/control_deck/components/skeletons/` (bereits vorhanden, erweitern)

**Pattern:**
```typescript
import { Skeleton } from '@/components/ui/skeleton'

function MissionCardSkeleton() {
  return (
    <div className="border rounded-lg p-4">
      <Skeleton className="h-4 w-3/4 mb-2" />
      <Skeleton className="h-3 w-1/2" />
    </div>
  )
}

// Usage:
{isLoading ? (
  <MissionCardSkeleton />
) : (
  <MissionCard data={mission} />
)}
```

**Apply to:**
- Dashboard Cards
- Mission Lists
- Agent Lists
- Settings Forms

---

#### Task 18.3: Error States & Retry
**System:** Control Deck + AXE UI
**Priorität:** MEDIUM (UX)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐ (Error Handling)

**Pattern:**
```typescript
function ErrorState({ error, retry }: { error: Error, retry: () => void }) {
  return (
    <div className="border border-red-800 bg-red-900/20 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-semibold text-red-300">Error Loading Data</h3>
          <p className="text-sm text-red-400 mt-1">{error.message}</p>
          <button
            onClick={retry}
            className="mt-3 px-3 py-1.5 bg-red-800 hover:bg-red-700 rounded text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    </div>
  )
}

// Usage with React Query:
const { data, error, isLoading, refetch } = useMissionsInfo()

if (error) return <ErrorState error={error} retry={refetch} />
```

---

### Tag 20-21: Monitoring & Observability (8h)

#### Task 20.1: Grafana Dashboard Setup
**System:** Backend + Infrastructure
**Priorität:** MEDIUM (Ops)
**Aufwand:** 4 Stunden
**Impact:** ⭐⭐⭐⭐ (Monitoring)

**File:** `docker-compose.monitoring.yml` (NEW)

**Setup:**
```yaml
version: '3.8'

services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    depends_on:
      - prometheus

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

volumes:
  grafana_data:
  prometheus_data:
```

**File:** `prometheus/prometheus.yml` (NEW)

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'brain-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/api/metrics'
```

**Dashboards:**
1. System Overview (CPU, Memory, Requests/s)
2. Mission System (Queue depth, Success rate)
3. NeuroRail (Trace chain, Budget usage)
4. API Performance (Latency, Error rate)

---

#### Task 20.2: Error Tracking (Sentry)
**System:** Backend + Frontends
**Priorität:** LOW (Ops)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐ (Bug Detection)

**Installation:**
```bash
# Backend
pip install sentry-sdk[fastapi]

# Frontend
npm install @sentry/nextjs
```

**Backend Setup:**
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=settings.environment,
    traces_sample_rate=1.0 if settings.environment == "development" else 0.1,
    integrations=[FastApiIntegration()],
)
```

**Frontend Setup:**
```javascript
// sentry.client.config.js
import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT,
  tracesSampleRate: 0.1,
})
```

---

#### Task 20.3: Uptime Monitoring
**System:** Infrastructure
**Priorität:** LOW (Ops)
**Aufwand:** 2 Stunden
**Impact:** ⭐⭐⭐ (Availability Tracking)

**Options:**
1. **UptimeRobot** (SaaS, Free Tier)
2. **Uptime Kuma** (Self-hosted)
3. **Healthchecks.io** (SaaS)

**Setup (UptimeRobot):**
1. Create account
2. Add monitors:
   - https://api.dev.brain.falklabs.de/api/health (5min interval)
   - https://control.dev.brain.falklabs.de (5min interval)
   - https://axe.dev.brain.falklabs.de (5min interval)
3. Configure alerts (Email, Slack)

**Setup (Uptime Kuma - Self-hosted):**
```yaml
# docker-compose.monitoring.yml
uptime-kuma:
  image: louislam/uptime-kuma:latest
  ports:
    - "3003:3001"
  volumes:
    - uptime-kuma_data:/app/data
```

---

## 📅 Phase 4: Advanced Features (Backlog)

**Ziel:** Nice-to-Have Features
**Dauer:** Ongoing
**Impact:** Future Improvements

### Advanced Features List

#### Backend

1. **API Versioning** (2h)
   - `/api/v1/missions`, `/api/v2/missions`
   - Deprecation warnings

2. **GraphQL Endpoint** (8h)
   - Alternative to REST
   - Flexible queries
   - Reduced over-fetching

3. **Webhook System** (4h)
   - Mission completion webhooks
   - Event notifications
   - Custom callbacks

4. **Advanced Caching** (4h)
   - Redis cache warming
   - Cache invalidation strategies
   - CDN integration

5. **Database Connection Pooling Optimization** (2h)
   - Tune pool sizes
   - Connection leak detection

#### Control Deck

1. **Knowledge Base (Nextra)** (8h)
   - Full documentation site
   - Search
   - API Reference

2. **Command Palette (Cmd+K)** (4h)
   - Quick navigation
   - Search everywhere
   - Keyboard shortcuts

3. **Customizable Dashboard** (8h)
   - Drag & Drop widgets
   - User preferences
   - Saved layouts

4. **Dark/Light Mode Toggle** (2h)
   - Theme switcher
   - System preference detection

5. **Onboarding Tour** (4h)
   - First-time user guide
   - Interactive walkthrough
   - Feature highlights

#### AXE UI

1. **Voice Input** (8h)
   - Speech-to-text
   - Voice commands

2. **File Upload** (4h)
   - Attach files to chat
   - Image recognition

3. **Conversation History Export** (2h)
   - Download chat as PDF/JSON
   - Search history

4. **Advanced Diff Viewer** (4h)
   - Side-by-side comparison
   - Syntax highlighting
   - Merge conflicts

5. **Widget Themes** (4h)
   - Customizable colors
   - Branding options

---

## 📊 Gantt Chart (Overview)

```
Week 1: Quick Wins + Security
├─ Day 1-3:   Phase 0 (Backend Connection, CORS Fix)
├─ Day 4-5:   Phase 1 Security (Rate Limiting, Headers)
└─ Day 6-7:   Phase 1 Security (Audit Trail, Validation)

Week 2: Core Features
├─ Day 8-9:   Control Deck Responsive Sidebar
├─ Day 10-11: AXE UI Widget Package
├─ Day 12-13: Backend Caching & Performance
└─ Day 14:    Testing & Bug Fixes

Week 3: UX Polish
├─ Day 15-17: Hilfesystem (i18n, Tooltips, Help Panel)
├─ Day 18-19: UI/UX Improvements (Charts, States)
└─ Day 20-21: Monitoring (Grafana, Sentry, Uptime)

Week 4: Production Preparation
├─ Day 22-23: Final Testing
├─ Day 24-25: Documentation Update
├─ Day 26:    Deployment Dry Run
└─ Day 27-28: Production Deployment
```

---

## 🎯 Success Criteria

### Week 1 Success Criteria
- ✅ All Frontends connect to Backend (no "Failed to fetch")
- ✅ CORS Wildcard removed
- ✅ Rate Limiting active
- ✅ Security Headers enabled
- ✅ Default passwords changed

### Week 2 Success Criteria
- ✅ Control Deck responsive on Mobile
- ✅ AXE Widget embeddable in external projects
- ✅ Backend response time <100ms (cached endpoints)
- ✅ All critical tests pass

### Week 3 Success Criteria
- ✅ Tooltips on all Settings pages
- ✅ Help Panel auf Top 5 Pages
- ✅ Multi-language support (DE + EN)
- ✅ Grafana Dashboard operational

### Week 4 Success Criteria
- ✅ Production deployment successful
- ✅ No critical bugs
- ✅ Monitoring active
- ✅ Documentation complete

---

## 📝 Daily Checklist Template

```markdown
## Day X: [Task Name]

### Morning (2-3h)
- [ ] Task 1
- [ ] Task 2

### Afternoon (2-3h)
- [ ] Task 3
- [ ] Task 4

### Testing
- [ ] Manual test
- [ ] Automated test (if applicable)

### Commit & Push
- [ ] Git commit with clear message
- [ ] Push to branch
- [ ] Update roadmap status

### Blockers
- None / [List blockers]

### Tomorrow
- [Preview next day tasks]
```

---

## 🚨 Blocker Escalation

**If stuck for >2 hours:**

1. **Document the issue**
   - What you tried
   - Error messages
   - Expected vs. Actual

2. **Search for solutions**
   - Official docs
   - GitHub Issues
   - Stack Overflow

3. **Ask for help**
   - Team chat
   - Claude (me!)
   - Community forums

4. **Pivot if needed**
   - Move to next task
   - Come back later with fresh eyes

---

## 📈 Progress Tracking

**File:** `ROADMAP_PROGRESS.md` (Create & Update Daily)

```markdown
# Roadmap Progress Tracker

## Week 1: Quick Wins + Security

### Phase 0: Quick Wins (Day 1-3)
- [x] Task 1.1: Frontend Environment Variables ✅ 2026-01-17
- [x] Task 1.2: Ollama Host Config ✅ 2026-01-17
- [x] Task 1.3: CORS Wildcard Fix ✅ 2026-01-18
- [ ] Task 2.1: Default Passwords
- [ ] Task 2.2: Security Headers
- [ ] Task 2.3: Rate Limiting

### Phase 1: Security Hardening (Day 4-7)
- [ ] Task 4.1: Audit Middleware
- [ ] Task 4.2: Failed Login Tracking
...

## Current Sprint
**Focus:** Phase 0 - Quick Wins
**Deadline:** 2026-01-20
**Status:** 🟢 On Track

## Blockers
- None

## Notes
- CORS fix worked perfectly
- Ollama connection needs testing
```

---

## 🎉 Completion Checklist

### Pre-Production
- [ ] All Phase 0 tasks complete
- [ ] All Phase 1 tasks complete
- [ ] All Phase 2 tasks complete
- [ ] Phase 3 at least 50% complete

### Security
- [ ] No CORS wildcard
- [ ] Rate limiting active
- [ ] Security headers enabled
- [ ] No default passwords
- [ ] HTTPS enforced
- [ ] Audit trail working

### Functionality
- [ ] Backend APIs respond
- [ ] Frontends connect to Backend
- [ ] AXE Chat works
- [ ] Mission System works
- [ ] Authentication works

### UX
- [ ] Mobile responsive (Control Deck)
- [ ] Tooltips present
- [ ] Error states handled
- [ ] Loading states present

### Monitoring
- [ ] Grafana dashboard
- [ ] Error tracking (Sentry)
- [ ] Uptime monitoring

### Documentation
- [ ] CLAUDE.md updated
- [ ] Deployment checklist
- [ ] API documentation
- [ ] Help content (Top 5 pages)

---

**Next Step:** Update CLAUDE.md with reference to this roadmap.

---

**Version History:**
- v1.0.0 (2026-01-17): Initial roadmap created
