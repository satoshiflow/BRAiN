# BRAiN Auth & Governance Engine – Komplettes Konzept

**Datum:** 2026-02-25
**Status:** Zur Implementierung freigegeben
**Branch:** `claude/auth-governance-engine-vZR1n`
**Für:** Max (Implementierung)

---

## Kontext

Das BRAiN-Projekt hat eine fragmentierte Auth-Architektur:
- Drei koexistierende Implementierungen (Legacy in-memory, Enhanced JWKS, Database-backed)
- ~80% der 65 Modul-Router ohne Auth-Guards
- Keine zentrale Governance-Engine die Policy-Entscheidungen mit Auth-Identität verbindet
- Kein vollständiger Token-Lebenszyklus (keine Refresh-Tokens, keine Revocation)

**Ziel:** Eine einheitliche, produktionsreife Auth/Governance-Architektur.

---

## Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                    IDENTITY LAYER                                │
│  Human (email/pwd)  │  Agent (JWT)  │  Service (M2M)  │  Anon  │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Credentials
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  TOKEN ISSUANCE (AuthService)                    │
│  Access Token (RS256, 15min)  │  Refresh Token (DB, 7d)         │
│  Agent Token (RS256, 24h)     │  Service Token (M2M, konf.)     │
│  JWKS Endpoint /.well-known/jwks.json                           │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Bearer Token
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│               JWT MIDDLEWARE (jwt_middleware.py)                  │
│  Signature Verify → Decode → TokenPayload → request.state        │
└────────────────────────────────┬────────────────────────────────┘
                                 │ TokenPayload
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│          GOVERNANCE ENGINE (NEU: authorization_engine.py)        │
│  Principal resolving → RBAC check → Scope check → Policy eval   │
│  → AXE Trust Tier → HITL Approval (wenn nötig) → ALLOW/DENY     │
│  → Audit Log (alle Entscheidungen persistent in DB)              │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Principal (authorized)
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              MODULE ROUTERS (65 Stück)                           │
│  Depends(require_role / require_scope / require_auth)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Token-Architektur konsolidieren

### 1.1 RSA-Keypair für Token-Signierung

**Datei:** `/backend/app/core/token_keys.py` (NEU)

```python
# Lädt RSA private key aus ENV: BRAIN_JWT_PRIVATE_KEY (PEM)
# Publisht public key via JWKS-Endpoint
# Key-ID (kid) = SHA256(public_key_der)[:16]
```

Ergänzungen in `/backend/app/core/config.py`:
```python
jwt_private_key_pem: str = ""  # aus ENV BRAIN_JWT_PRIVATE_KEY
jwt_algorithm: str = "RS256"   # statt HS256
access_token_expire_minutes: int = 15   # NEU: kürzer als bisher
refresh_token_expire_days: int = 7      # NEU
agent_token_expire_hours: int = 24      # NEU
```

### 1.2 Token-Datenbank-Modelle

**Datei:** `/backend/app/models/token.py` (NEU)

```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: UUID
    user_id: UUID          # FK → users.id
    token_hash: str        # SHA256 des Tokens (nie Plaintext!)
    principal_type: str    # "human" | "agent" | "service"
    scopes: JSON           # gewährte Scopes
    issued_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime]
    revoked_reason: Optional[str]
    last_used_at: Optional[datetime]
    device_info: Optional[JSON]   # User-Agent, IP

class ServiceAccount(Base):
    __tablename__ = "service_accounts"
    id: UUID
    name: str
    description: Optional[str]
    client_id: str          # unique, public
    client_secret_hash: str # BCrypt
    scopes: JSON            # erlaubte Scopes
    roles: JSON             # zugewiesene Rollen
    is_active: bool
    created_by: UUID
    expires_at: Optional[datetime]

class AgentCredential(Base):
    __tablename__ = "agent_credentials"
    id: UUID
    agent_id: str           # BRAiN agent identifier
    public_key_pem: str     # Ed25519 public key (für Agent-JWT-Signing)
    issued_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime]
    parent_agent_id: Optional[str]
```

Neue Alembic Migration: `/backend/alembic/versions/xxx_add_token_tables.py`

### 1.3 Token-Service erweitern

**Datei:** `/backend/app/services/auth_service.py` (ERWEITERN)

Neue Methoden:
```python
async def create_token_pair(user, scopes, device_info) -> TokenPair
    # → Access Token (RS256, 15min) + Refresh Token (DB-gespeichert)

async def refresh_access_token(refresh_token: str, db) -> TokenPair
    # Prüft DB, revoked?, expired? → neues Token-Pair

async def revoke_token(token_hash: str, reason: str, db)
    # Setzt revoked_at + revoked_reason

async def create_agent_token(agent_id, parent_agent_id, scopes, db) -> str
    # Agent-JWT mit 24h Laufzeit, signiert mit BRAiN RSA key

async def create_service_token(client_id, client_secret, scopes, db) -> str
    # M2M Client-Credentials Flow
```

### 1.4 Neue Auth-Endpoints

**Datei:** `/backend/app/api/routes/auth.py` (ERWEITERN)

```
POST /api/auth/refresh          → Token refresh mit Refresh-Token
POST /api/auth/logout           → Token revocation
POST /api/auth/service-token    → M2M Client Credentials
GET  /.well-known/jwks.json     → JWKS public key distribution
POST /api/auth/agent-token      → Agent credential issuance (OPERATOR+)
```

---

## Phase 2: Governance Engine

### 2.1 Zentrale Authorization Engine

**Datei:** `/backend/app/core/authorization_engine.py` (NEU)

```python
@dataclass
class AuthorizationRequest:
    principal: Principal
    action: str              # z.B. "skills:execute", "sovereign:change_mode"
    resource_id: Optional[str]
    context: Dict[str, Any]  # tenant, agent_id, trust_tier, etc.

@dataclass
class AuthorizationDecision:
    allowed: bool
    reason: str
    requires_approval: bool       # HITL-Workflow nötig?
    approval_request_id: Optional[str]
    policy_matched: Optional[str]
    risk_tier: str                # LOW | MEDIUM | HIGH | CRITICAL

class AuthorizationEngine:
    async def authorize(
        req: AuthorizationRequest,
        db: AsyncSession
    ) -> AuthorizationDecision:
        # 1. Principal valid & active?
        # 2. RBAC: hat Principal die Rolle für diese Action?
        # 3. Scope: hat Token den required Scope?
        # 4. AXE Trust Tier: Local/DMZ/External?
        # 5. Policy Engine: welche Policies greifen?
        # 6. HITL: Risk Tier HIGH/CRITICAL → Approval Request
        # 7. Audit Log persistent in DB schreiben
        # 8. AuthorizationDecision zurückgeben
```

**Entscheidungs-Kaskade:**

```
Identity Valid? ──NO──→ DENY (401)
       │
       YES
       │
RBAC Check ──NO──→ DENY (403)
       │
       YES
       │
Scope Check ──NO──→ DENY (403)
       │
       YES
       │
AXE Trust Tier OK? ──NO──→ DENY (403)
       │
       YES
       │
Policy Match? ──DENY──→ DENY (403)
       │
      ALLOW
       │
Risk Tier HIGH/CRITICAL? ──YES──→ HITL Approval Request → PENDING (202)
       │
       NO
       │
     ALLOW (200)
```

### 2.2 Policy Persistenz

Problem: Aktuell In-Memory Storage in `/backend/app/modules/policy/service.py`.

Neue Datei: `/backend/app/models/policy.py`
```python
class Policy(Base):
    __tablename__ = "policies"
    id: UUID
    name: str
    description: str
    resource_pattern: str    # glob: "skills:*", "sovereign:*"
    action_pattern: str      # "execute", "write", "*"
    effect: str              # "allow" | "deny"
    conditions: JSON         # {min_role: "operator", require_mfa: false, ...}
    priority: int
    is_active: bool
    created_by: UUID
    created_at: datetime
```

### 2.3 Audit Log Persistenz

**Datei:** `/backend/app/models/audit.py` (NEU)

```python
class AuthAuditLog(Base):
    __tablename__ = "auth_audit_log"
    id: UUID
    timestamp: datetime      # index
    principal_id: str
    principal_type: str      # "human" | "agent" | "service"
    action: str
    resource_id: Optional[str]
    decision: str            # "allow" | "deny" | "pending_approval"
    reason: str
    policy_matched: Optional[str]
    risk_tier: str
    ip_address: Optional[str]
    request_id: str
    metadata: JSON
```

### 2.4 HITL-Governance Integration

Die bestehende `GovernanceService` (`/backend/app/modules/governance/governance_service.py`)
wird durch die `AuthorizationEngine` aufgerufen, wenn `risk_tier == CRITICAL`
oder eine Policy `require_approval: true` setzt.

```python
# In authorization_engine.py:
if risk_tier in ["HIGH", "CRITICAL"]:
    approval = await governance_service.request_approval(
        action=req.action,
        principal=req.principal,
        context=req.context,
        approval_type=ApprovalType.HIGH_RISK_ACTION
    )
    return AuthorizationDecision(
        allowed=False,
        requires_approval=True,
        approval_request_id=approval.id,
        risk_tier=risk_tier
    )
```

---

## Phase 3: Module Auth Coverage (65 Router)

### 3.1 Prioritäts-Matrix

**[P0] KRITISCH – sofort absichern:**

| Modul | Router | Guard |
|-------|--------|-------|
| `sovereign_mode` | `router.py` | `require_admin` – Key Management! |
| `dmz_control` | `router.py` | `require_admin` |
| `safe_mode` | `router.py` | `require_operator` |
| `fleet` | `router.py` | `require_operator` |

**[P1] HOCH:**

| Modul | Endpoint | Guard |
|-------|----------|-------|
| `memory` | alle | `require_auth` |
| `learning` | alle | `require_auth` |
| `foundation` | config-Endpoints | `require_admin` |
| `knowledge_graph` | `/reset` | `require_admin` |
| `skills` | `/execute` | `require_operator` + Scope `skills:execute` |

**[P2] MITTEL – alle verbleibenden ~45 Router:**

Standard-Pattern (Read/Write/Admin):
```python
from app.core.auth_deps import require_auth, require_operator, require_admin

@router.get("/items", dependencies=[Depends(require_auth)])
async def list_items(...): ...

@router.post("/items", dependencies=[Depends(require_operator)])
async def create_item(...): ...

@router.delete("/items/{id}", dependencies=[Depends(require_admin)])
async def delete_item(...): ...
```

### 3.2 Hilfsfunktion für Bulk-Absicherung

**Datei:** `/backend/app/core/auth_deps.py` (ERWEITERN)

```python
def module_auth_guard(
    read_role: str = "viewer",
    write_role: str = "operator",
    admin_role: str = "admin"
) -> Dict[str, Depends]:
    """Standard-Guards für CRUD-Operationen eines Moduls."""
    return {
        "read": Depends(require_role(read_role)),
        "write": Depends(require_role(write_role)),
        "admin": Depends(require_role(admin_role))
    }
```

---

## Phase 4: Frontend Token-Lifecycle

### 4.1 NextAuth Token Refresh

**Datei:** `/frontend/control_deck/auth.ts` (ERWEITERN)

```typescript
// JWT callback:
async jwt({ token, user }) {
  // Erstes Login: access_token + refresh_token speichern
  if (user) {
    token.accessToken = user.accessToken
    token.refreshToken = user.refreshToken          // NEU
    token.accessTokenExpires = Date.now() + 15 * 60 * 1000
  }

  // Token noch gültig?
  if (Date.now() < (token.accessTokenExpires as number)) return token

  // Token abgelaufen → refresh:
  return await refreshAccessToken(token)
}

async function refreshAccessToken(token: JWT): Promise<JWT> {
  const response = await fetch(`${process.env.NEXT_PUBLIC_BRAIN_API_BASE}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: token.refreshToken })
  })
  if (!response.ok) {
    // Refresh fehlgeschlagen → Session invalidieren
    return { ...token, error: "RefreshAccessTokenError" }
  }
  const data = await response.json()
  return {
    ...token,
    accessToken: data.access_token,
    accessTokenExpires: Date.now() + 15 * 60 * 1000,
    refreshToken: data.refresh_token ?? token.refreshToken
  }
}
```

**Datei:** `/frontend/control_deck/app/auth/actions.ts` (ERWEITERN)

```typescript
export async function logoutAction() {
  const session = await auth()
  // Backend-seitige Token-Revocation
  if (session?.user?.accessToken) {
    await fetch(`${process.env.NEXT_PUBLIC_BRAIN_API_BASE}/api/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${session.user.accessToken}` }
    }).catch(() => {})  // Nicht-kritisch: logout trotzdem durchführen
  }
  await signOut({ redirectTo: "/" })
}
```

---

## Dateiübersicht

### Neu zu erstellen:

| Datei | Zweck |
|-------|-------|
| `/backend/app/core/authorization_engine.py` | Zentrale Governance Engine |
| `/backend/app/core/token_keys.py` | RSA keypair management + JWKS |
| `/backend/app/models/token.py` | RefreshToken, ServiceAccount, AgentCredential |
| `/backend/app/models/audit.py` | AuthAuditLog |
| `/backend/app/models/policy.py` | Policy DB-Modell |
| `/backend/alembic/versions/xxx_auth_governance.py` | DB-Migration |

### Zu modifizieren:

| Datei | Änderung |
|-------|----------|
| `/backend/app/core/security.py` | Legacy → thin wrapper um auth_deps.py |
| `/backend/app/core/auth_deps.py` | authorization_engine + module_auth_guard |
| `/backend/app/core/jwt_middleware.py` | RS256 Standard, token_keys nutzen |
| `/backend/app/core/config.py` | Neue Token-Settings (RS256, TTLs) |
| `/backend/app/services/auth_service.py` | Token-Pair, Revocation, M2M, Agent |
| `/backend/app/api/routes/auth.py` | Refresh, Logout, JWKS, Agent-Token |
| `/backend/app/modules/sovereign_mode/router.py` | `require_admin` |
| `/backend/app/modules/safe_mode/router.py` | `require_operator` |
| `/backend/app/modules/fleet/router.py` | `require_operator` |
| `/backend/app/modules/dmz_control/router.py` | `require_admin` |
| `/backend/app/modules/memory/router.py` | `require_auth` |
| `/backend/app/modules/learning/router.py` | `require_auth` |
| `/backend/app/modules/skills/router.py` | `require_operator` + Scope |
| `/backend/app/modules/policy/service.py` | In-Memory → DB |
| `/backend/app/modules/governance/governance_service.py` | authorization_engine koppeln |
| `/frontend/control_deck/auth.ts` | Token refresh, refreshToken speichern |
| `/frontend/control_deck/app/auth/actions.ts` | Logout mit Revocation |

---

## Implementierungs-Reihenfolge

| Priorität | Task | Dateien |
|-----------|------|---------|
| **P0** | RSA-Keys + JWKS | `token_keys.py`, `config.py`, auth routes |
| **P0** | Token DB-Modelle + Migration | `models/token.py`, alembic |
| **P0** | auth_service Token-Pair | `auth_service.py` |
| **P0** | Sovereign Mode absichern | `sovereign_mode/router.py` |
| **P1** | Governance Engine | `authorization_engine.py`, `models/audit.py` |
| **P1** | Policy DB-Persistenz | `models/policy.py`, `policy/service.py` |
| **P1** | Kritische Module | dmz_control, safe_mode, fleet, skills |
| **P2** | Frontend Token Refresh | `auth.ts`, `actions.ts` |
| **P2** | Service Accounts (M2M) | `models/token.py`, auth routes |
| **P2** | Agent Credentials | `models/token.py`, auth routes |
| **P3** | Alle ~45 restlichen Router | Standard-Guards |
| **P3** | MFA/TOTP | Eigene Phase, optional |

---

## Verifikation

```bash
# 1. Unit Tests für Authorization Engine
pytest backend/tests/test_authorization_engine.py -v

# 2. Integration: Login → Refresh → Revoke Flow
pytest backend/tests/test_auth_flow.py -v

# 3. Sovereign Mode unauthenticated → muss 401 zurückgeben
curl -X POST http://localhost:8000/api/sovereign-mode/mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"offline"}'
# Expected: {"detail": "Not authenticated"}

# 4. JWKS Endpoint erreichbar
curl http://localhost:8000/.well-known/jwks.json
# Expected: {"keys": [{"kty": "RSA", "use": "sig", "kid": "...", ...}]}

# 5. Audit Log nach Auth-Events
SELECT action, decision, risk_tier, timestamp
FROM auth_audit_log
ORDER BY timestamp DESC LIMIT 10;

# 6. Alle Module-Router haben Auth-Guards
grep -rL "require_role\|require_auth\|require_admin\|require_operator" \
  backend/app/modules/*/router.py
# Expected: Leere Ausgabe (alle abgedeckt)
```

---

## ENV-Variablen (neu benötigt)

```bash
# RSA Private Key (PEM-Format, base64-encoded für ENV)
BRAIN_JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."

# Bestehende (müssen gesetzt bleiben)
JWT_SECRET_KEY=<32-byte-random>        # Fallback HS256 (deprecated)
BRAIN_ADMIN_PASSWORD=<strong>
BRAIN_DMZ_GATEWAY_SECRET=<32-byte>
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
```

Generierung:
```bash
openssl genrsa -out brain_jwt.pem 2048
BRAIN_JWT_PRIVATE_KEY=$(cat brain_jwt.pem)
```
