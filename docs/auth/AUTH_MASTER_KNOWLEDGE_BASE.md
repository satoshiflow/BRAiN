# BRAiN Authentication & Identity - Master Knowledge Base

**Version:** 1.0  
**Status:** Implementation Ready  
**Last Updated:** 2026-02-12  
**Owner:** Fred (OpenClaw Orchestrator)

---

## Executive Summary

BRAiN verwendet ein **OIDC-basiertes Enterprise-Grade Authentication System** mit folgenden Kernmerkmalen:

- **Phase 1:** Authentik (aktuell)
- **Phase 2:** Keycloak (zukünftig, migrations-fähig)
- **Pattern:** Backend For Frontend (BFF) mit Auth.js
- **Token-Model:** Human Sessions (Cookies) + Agent Tokens (Client Credentials)

---

## Identity Layers (V1-V4 Roadmap)

### V1 - Authentication (AKTUELL)
**Ziel:** Login & API Security  
**Komponenten:**
- OIDC Provider (Authentik)
- Next.js + Auth.js Frontend
- JWT Validation im Backend

### V2 - Enterprise Identity (Q2 2026)
**Ziel:** RBAC + Multi-Tenant  
**Erweiterungen:**
- Rollenbasierte Zugriffskontrolle
- Tenant-Isolation
- Service Identity (mTLS)

### V3 - Agent Civilization (Q3 2026)
**Ziel:** Reputation + Economy  
**Erweiterungen:**
- Karma/Reputation Scores
- Wallet Binding
- Capability-based Access

### V4 - Sovereign AI (Q4 2026+)
**Ziel:** Legal Personhood  
**Vision:**
- Autonome ökonomische Akteure
- Vertragsfähige Agents
- Governance Participation

---

## Current Architecture (V1)

### 1. Identity Provider Layer
```yaml
Phase 1: Authentik
  - OIDC Discovery: /.well-known/openid-configuration
  - JWKS Endpoint: /jwks
  - Token Endpoint: /token
  - Userinfo Endpoint: /userinfo

Phase 2: Keycloak (Migration-Ready)
  - Compatible OIDC
  - Same claim structure
  - Config-switchable
```

**Migration Requirement:** IdP-Wechsel nur via Config, keine Code-Änderungen.

### 2. Frontend Auth Layer (Next.js + Auth.js)
```typescript
// Pattern: Backend For Frontend (BFF)
// Session Cookie Rules:
- httpOnly: true
- Secure: true (HTTPS only)
- SameSite: "Lax" oder "Strict"
- Short TTL + Refresh Rotation

// VERBOTEN:
- localStorage für Tokens
- SessionStorage für Tokens
- client-side Token Storage
```

### 3. API Security Layer (FastAPI + Node)
```python
# JWT Validation Muss:
1. Signature validieren (JWKS)
2. Issuer validieren
3. Audience validieren
4. Expiration prüfen
5. Scope prüfen
6. Optional: Roles/Permissions

# JWKS muss dynamisch fetched werden
# Keine hardcoded Keys!
```

---

## Token Model

### Human Tokens
```yaml
Use Case: Dashboard, Admin UI, Human Workflows
Transport: httpOnly Cookie
Flow: Authorization Code + PKCE
Storage: Server-side Session
Features:
  - Refresh Token Rotation
  - Session Revocation
  - Short-lived Access Tokens
```

### Agent Tokens
```yaml
Use Case: Agent-to-API Communication
Transport: Bearer Token (Header)
Flow: OAuth2 Client Credentials
Identity: Ein Agent = Eindeutige Identity
REGEL: Nie Human-Tokens für Agents verwenden!
```

### Service Tokens
```yaml
Use Case: Service-to-Service
Transport: mTLS oder Signed JWT
Identity: Machine Identity
Features:
  - Kurze Lebensdauer
  - Keine Refresh Tokens
```

---

## BRAiN Claim Standard

### Required Claims (Alle Token)
```json
{
  "sub": "user-123",
  "iss": "https://auth.falklabs.io",
  "aud": "brain-api",
  "exp": 1735689600,
  "iat": 1735686000,
  "scope": "read:missions write:missions"
}
```

### Optional Claims (Context-Dependent)
```json
{
  "email": "user@falklabs.io",
  "tenant_id": "tenant-456",
  "roles": ["admin", "ops"],
  "permissions": ["mission:execute", "agent:create"],
  "agent_id": "agent-789",
  "service_id": "service-abc"
}
```

---

## BRAiN Role Model

### Rollen-Hierarchie
```
superadmin    # Gott-Modus, Infrastructure Access
admin         # Tenant-Admin, User Management
ops           # Operations, Mission Control
partner       # Externe Partner (eingeschränkt)
customer      # End-User, eigene Ressourcen
agent         # AI Agent Identity
service       # Service Account
```

### Autorisierungs-Regel
**Frontend = UI Only**  
**API Layer = Authorization**  

Alle Auth-Checks müssen im Backend passieren, nie nur im Frontend vertrauen.

---

## Security Baseline (MANDATORY)

### Hard Requirements
- [ ] HTTPS Only (kein HTTP in Production)
- [ ] Secure Cookies (httpOnly, Secure, SameSite)
- [ ] Refresh Token Rotation
- [ ] Login Rate Limiting (5 Versuche / 15 Min)
- [ ] Brute Force Protection
- [ ] Session Revocation Support
- [ ] Audit Log Hooks
- [ ] CSRF Protection

### Token Security
- [ ] Keine Tokens in localStorage
- [ ] Keine Tokens in URLs
- [ ] Kurze Access Token TTL (5-15 Min)
- [ ] Refresh Token Rotation
- [ ] Token Binding (optional)

---

## Access Patterns

### Pattern 1: BFF (Backend For Frontend)
```
Browser → Next.js (Auth.js) → BRAiN APIs
         ↑______BFF Layer______↑
         Session Cookie (httpOnly)
```

**Use Case:** Dashboard, Admin UI  
**Vorteil:** Tokens nie im Browser sichtbar

### Pattern 2: Direct API
```
External Client → API Gateway → BRAiN APIs
                  Bearer Token
```

**Use Case:** External Integrations, Scripts  
**Vorteil:** Direkter API-Zugriff

---

## Agent Identity Model

### Agent Authentication
```yaml
Flow: OAuth2 Client Credentials
Client ID: agent-{agent_id}
Client Secret: Rotierend, sicher gespeichert
Scope: "agent:execute agent:read"
Token TTL: 1 Stunde
```

### Agent Token Claims
```json
{
  "sub": "agent-abc-123",
  "type": "agent",
  "agent_id": "agent-abc-123",
  "capabilities": ["web_search", "file_read"],
  "mission_scope": "mission-xyz",
  "tenant_id": "tenant-456"
}
```

### Agent vs Human Unterscheidung
```python
# In API Layer
def check_agent_permission(token: JWT):
    if token.get("type") == "agent":
        # Agent-spezifische Logik
        verify_agent_scope(token)
    else:
        # Human-spezifische Logik
        verify_user_permissions(token)
```

---

## Implementation Phases

### Phase 1: Auth Foundation (Woche 1-2)
**Kimi:**
- [ ] Auth.js OIDC Integration
- [ ] Login/Logout Flow
- [ ] Session Refresh
- [ ] Cookie Hardening

**Claude:**
- [ ] Session Security Review
- [ ] CSRF Analysis
- [ ] Session Fixation Analysis

### Phase 2: API Security (Woche 3-4)
**Kimi:**
- [ ] FastAPI JWT Middleware
- [ ] Node.js JWT Middleware
- [ ] API Gateway Integration

**Claude:**
- [ ] Signature Validation Review
- [ ] Algorithm Attack Review
- [ ] Claim Validation Review

### Phase 3: Agent Identity (Woche 5-6)
**Kimi:**
- [ ] Client Credentials Flow
- [ ] Agent Token Validation
- [ ] Agent Identity Schema

**Claude:**
- [ ] Privilege Escalation Analysis
- [ ] Scope Abuse Analysis
- [ ] Service Isolation Review

### Phase 4: RBAC & Multi-Tenant (Woche 7-8)
**Features:**
- [ ] Rollenbasierte Zugriffskontrolle
- [ ] Tenant-Isolation
- [ ] Permission Matrix

### Phase 5: Advanced Security (Woche 9-10)
**Features:**
- [ ] Hardware Key Support
- [ ] Passkey Integration
- [ ] Advanced Audit Logging

---

## Migration Strategy

### Von Authentik zu Keycloak
```yaml
Anforderungen:
  - Dynamic Issuer URL
  - Dynamic JWKS URL
  - Config-based Client IDs
  - Config-based Audience

Migration:
  1. Keycloak parallel aufsetzen
  2. Gleiche Clients/Scopes konfigurieren
  3. JWKS URLs austauschen
  4. Smoke Tests
  5. DNS Switch
  6. Authentik abschalten
```

**Kein Vendor Lock-in:** Alles konfigurierbar.

---

## Test Cases (MUST PASS)

### Token Validation Tests
```
✅ Valid Token → Access Granted
✅ Expired Token → 401 Unauthorized
✅ Wrong Issuer → 401 Unauthorized
✅ Wrong Audience → 401 Unauthorized
✅ Missing Scope → 403 Forbidden
✅ Revoked Session → 401 Unauthorized
```

### Agent Token Tests
```
✅ Valid Agent Token → Access Granted
✅ Agent Token for Human Endpoint → 403
✅ Human Token for Agent Endpoint → 403
✅ Wrong Agent Scope → 403
```

### Security Tests
```
✅ Token in localStorage → Rejected
✅ HTTP (non-HTTPS) → Redirect/Block
✅ CSRF Token Missing → 403
✅ Rate Limit Exceeded → 429
```

---

## Failure Conditions (REJECT)

Ein Implementation wird **abgelehnt** wenn:
- ❌ Tokens in localStorage
- ❌ Hardcoded IdP URLs
- ❌ Keine JWKS Validation
- ❌ Keine Issuer Validation
- ❌ Keine Role Separation
- ❌ Kein Agent Identity Support
- ❌ Tokens über HTTP
- ❌ Session Cookies ohne httpOnly

---

## Configuration Template

### Authentik (Current)
```yaml
# brain-auth-config.yaml
oidc:
  issuer: "https://auth.falklabs.io/application/o/brain/"
  client_id: "brain-frontend"
  client_secret: "${AUTH_CLIENT_SECRET}"
  redirect_uri: "https://brain.falklabs.io/api/auth/callback"
  scopes: ["openid", "email", "profile", "brain:access"]
  
jwks:
  url: "https://auth.falklabs.io/application/o/brain/jwks/"
  refresh_interval: 3600
  
session:
  cookie_name: "brain_session"
  max_age: 86400  # 24h
  secure: true
  http_only: true
  same_site: "lax"
```

### Keycloak (Future)
```yaml
oidc:
  issuer: "https://keycloak.falklabs.io/realms/brain"
  # Rest identical structure
```

---

## Definition of Done

### ✅ Phase 1 Complete
- [ ] Dashboard requires login
- [ ] Login flow funktioniert
- [ ] Logout funktioniert
- [ ] Session refresh funktioniert
- [ ] Cookies sind secure

### ✅ Phase 2 Complete
- [ ] APIs reject invalid tokens
- [ ] JWT validation korrekt
- [ ] JWKS dynamic fetch
- [ ] Error handling korrekt

### ✅ Phase 3 Complete
- [ ] Agents authenticate independently
- [ ] Client Credentials Flow funktioniert
- [ ] Agent Scope validation
- [ ] Keine Token-Reuse

### ✅ Production Ready
- [ ] Alle Test Cases pass
- [ ] Security Review complete
- [ ] IdP switch tested
- [ ] Audit logging aktiv
- [ ] Rate limiting aktiv

---

## Emergency Contacts

**Security Incidents:** security@falklabs.io  
**Auth Issues:** devops@falklabs.io  
**IdP Problems:** Authentik Admin / Keycloak Admin

---

## Future Extensions (V2-V4)

### V2 - Enterprise
- Wallet Identity Binding
- Lightning Identity Link
- Karma Reputation Claims
- Hardware Identity

### V3 - Agent Civilization
- Autonomous Economic Entities
- Trust Negotiation
- Capability Leasing
- Cross-Network Identity

### V4 - Sovereign AI
- Legal Personhood
- Contract Execution
- Treasury Management
- Governance Rights

---

**Last Review:** 2026-02-12  
**Next Review:** Bei IdP-Wechsel oder Security Incident  
**Owner:** Fred (OpenClaw Orchestrator)
