# BRAiN Governance Engine V1 — Spezifikation (FINAL / In-Stein-Gemeißelt)

**Status:** FINAL — Autoritatives Referenzdokument
**Version:** 1.0.0
**Datum:** 2026-02-25
**Erstellt durch:** Claude Code (Security Review + Fixes)
**Gültig für:** User (ControlDeck/AXE) + Agents (Workers/OpenClaw/PicoClaw)
**Prinzip:** *Deny-by-default · audit-everything · approvals for high-risk*

> ⚠️ Dieses Dokument enthält 6 sicherheitskritische Korrekturen gegenüber dem ursprünglichen Template.
> Abweichungen von dieser Spec → Security Review erforderlich.

---

## 1) Überblick

### 1.1 Problem
BRAiN hat gefährliche Aktionen (Reset, Delete, Exec, Deploy, etc.).
Ohne zentrale Governance verteilt sich die Logik über Controller → inkonsistent, unsicher, nicht auditierbar.

### 1.2 Lösung
Ein eigenständiges Modul **Governance Engine V1**, das jede Aktion entscheidet:

- `ALLOW`
- `DENY`
- `REQUIRE_APPROVAL`

und dabei:

- Policies versionierbar aus `policies/governance.yml` lädt
- `decision_id` + `request_id` durchgängig führt
- Approvals verwaltet (2-step, Token-basiert, zeitlich begrenzt)
- Audit schreibt (entscheidungsbasiert, unveränderlich)

---

## 2) Kernprinzipien (VERBINDLICH)

1. **Deny-by-default:** ohne Policy-Eintrag → `DENY`, kein ALLOW ohne explizite Regel
2. **Einheitlicher Subject-Standard:** `user:<id>` oder `agent:<id>`
3. **Risk Levels:** `low | medium | high | critical`
4. **Risk kommt AUSSCHLIESSLICH aus der Policy** — niemals aus dem Request des Callers
5. **Approvals für high/critical:** policy-gesteuert, Token-basiert, TTL=5min
6. **Audit immer:** jede Entscheidung wird persistiert, niemals gelöscht
7. **No trust without boundary:** Browser kann Governance nicht umgehen; Proxy/Agent Auth ist Trust-Boundary
8. **Token-Sicherheit:** Approval Tokens werden genau einmal zurückgegeben, in DB nur als SHA-256-Hash gespeichert

---

## 3) Modulstruktur

```
backend/app/modules/governance/
├── __init__.py
├── engine.py          # decide() — Kernentscheidungslogik
├── policy_store.py    # YAML loader + In-memory Cache + Versionsprüfung
├── approval.py        # request/confirm approval flow, Token-Lifecycle
├── audit.py           # persist decisions + audit events
├── models.py          # SQLAlchemy DB models
├── types.py           # Enums + Request/Response Pydantic models
├── router.py          # FastAPI endpoints
└── policies/
    └── governance.yml # Versionierte Policy-Datei (Git-controlled)
```

---

## 4) Datenmodelle

### 4.1 `governance_decisions`

| Feld         | Typ         | Beschreibung                              |
|--------------|-------------|-------------------------------------------|
| `id`         | `uuid`      | decision_id (PK)                          |
| `request_id` | `uuid`      | Tracing (aus X-Request-Id Header)         |
| `subject`    | `text`      | `user:<id>` oder `agent:<id>`             |
| `role`       | `text`      | `admin / operator / user / agent`         |
| `action`     | `text`      | z.B. `knowledge.reset`                    |
| `risk`       | `text`      | `low / medium / high / critical` (aus Policy) |
| `result`     | `text`      | `ALLOW / DENY / REQUIRE_APPROVAL`         |
| `reason`     | `text`      | Kurze Begründung (nicht intern-detail)    |
| `policy_version` | `int`   | Version der geladenen Policy              |
| `created_at` | `timestamptz` | Zeitpunkt                               |
| `meta`       | `jsonb`     | Optionaler Context (path, ip, ...)        |

### 4.2 `governance_approvals`

| Feld           | Typ           | Beschreibung                                    |
|----------------|---------------|-------------------------------------------------|
| `id`           | `uuid`        | approval_id (PK)                                |
| `decision_id`  | `uuid`        | FK → governance_decisions.id                   |
| `status`       | `text`        | `PENDING / APPROVED / DENIED / EXPIRED`         |
| `token_hash`   | `text`        | SHA-256(raw_token) — niemals Plaintext          |
| `expires_at`   | `timestamptz` | TTL (Standard: +5 Minuten ab created_at)        |
| `requested_by` | `text`        | Subject (`user:<id>`)                           |
| `approved_by`  | `text?`       | Subject nach Confirmation                       |
| `created_at`   | `timestamptz` | Zeitpunkt                                       |
| `meta`         | `jsonb`       | Optionaler Context                              |

> **KRITISCH:** `token_hash` ist immer `SHA-256(raw_token)`.
> Der Plaintext-Token verlässt das System genau einmal: in der Response von `POST /approvals/request`.
> Kein Endpoint gibt den Token ein zweites Mal zurück.

### 4.3 `audit_log`

| Feld           | Typ           | Beschreibung              |
|----------------|---------------|---------------------------|
| `id`           | `uuid`        | audit_id (PK)             |
| `request_id`   | `uuid`        | Tracing                   |
| `decision_id`  | `uuid`        | FK → governance_decisions |
| `subject`      | `text`        | Actor                     |
| `path`         | `text`        | Endpoint                  |
| `method`       | `text`        | GET/POST/...              |
| `status`       | `int`         | HTTP Status               |
| `duration_ms`  | `int`         | Response Time             |
| `ip`           | `inet`        | Client IP                 |
| `user_agent`   | `text`        | UA                        |
| `created_at`   | `timestamptz` | Zeitpunkt                 |
| `meta`         | `jsonb`       | Additional                |

---

## 5) Policy Format (YAML)

### 5.1 Datei `policies/governance.yml`

```yaml
version: 1

defaults:
  deny_by_default: true    # KRITISCH: niemals auf false setzen ohne Security Review

actions:

  knowledge.reset:
    risk: high
    requires_role: admin
    requires_approval: true

  system.exec:
    risk: critical
    requires_role: admin
    requires_approval: true
    allowlist:
      - "ls"
      - "cat"
      - "echo"

  agent.mission.execute:
    risk: medium
    requires_role: operator      # PFLICHT: explicit role, nicht weggelassen
    requires_approval: false
    min_karma: 70

  knowledge.read:
    risk: low
    requires_role: user
    requires_approval: false

  system.config.read:
    risk: low
    requires_role: operator
    requires_approval: false
```

### 5.2 Policy-Auswertungsregeln

1. `deny_by_default: true` und action nicht gelistet → **DENY** (kein Fallback auf ALLOW)
2. `requires_role` muss matchen — RBAC-Hierarchie: `admin > operator > user > agent`
3. `min_karma` gilt für user/agent sofern im Principal vorhanden; fehlender karma-Wert → DENY
4. `requires_approval: true` → **REQUIRE_APPROVAL** (niemals ALLOW direkt)
5. Risk-Level wird **niemals** aus dem Request gelesen — ausschließlich aus dieser Datei

### 5.3 Policy Updates (PFLICHT)

- Policies sind **versioniert in Git** — keine direkten Änderungen auf dem Server
- Jede Änderung → **PR + Review** durch mindestens eine weitere Person
- Breaking rule changes → `version` incrementieren
- Policy-Reload: bei Deployment oder via Admin-Endpoint (kein Hot-Reload ohne Audit)

---

## 6) Public API (FastAPI) — Endpoints

### 6.1 `POST /governance/decide`

**Auth:** OPERATOR minimum
**Zweck:** Liefert Entscheidung für eine action.

**Request Body:**
```json
{
  "request_id": "uuid-v4",
  "subject":    "user:u_123",
  "role":       "admin",
  "action":     "knowledge.reset",
  "context": {
    "path":       "/api/knowledge-graph/reset",
    "ip":         "1.2.3.4",
    "user_agent": "Mozilla/5.0 ...",
    "source":     "control-deck-proxy"
  }
}
```

> ⚠️ `risk` wird NICHT im Request übergeben. Engine lädt es aus der Policy.

**Response 200:**
```json
{
  "decision_id":    "uuid-v4",
  "request_id":     "uuid-v4",
  "result":         "REQUIRE_APPROVAL",
  "reason":         "action requires admin approval (risk=high)",
  "risk":           "high",
  "policy_version": 1,
  "created_at":     "2026-02-25T10:00:00Z"
}
```

**Result Values:**

| result               | HTTP | Bedeutung                        |
|----------------------|------|----------------------------------|
| `ALLOW`              | 200  | Ausführung erlaubt               |
| `DENY`               | 200  | Ausführung verweigert            |
| `REQUIRE_APPROVAL`   | 200  | Approval nötig vor Ausführung    |

> Hinweis: `/decide` gibt immer 200 zurück. Der Caller wertet `result` aus
> und entscheidet dann selbst über den Enforcement-Flow (siehe Section 7.2).

---

### 6.2 `POST /governance/approvals/request`

**Auth:** ADMIN
**Zweck:** Erzeugt Approval Request + gibt Token einmalig zurück.

**Request Body:**
```json
{
  "decision_id":  "uuid-v4",
  "requested_by": "user:u_123",
  "reason":       "Reindex after schema change"
}
```

**Response 201:**
```json
{
  "approval_id":         "uuid-v4",
  "token":               "raw-plaintext-token-only-returned-once",
  "expires_in_seconds":  300,
  "expires_at":          "2026-02-25T10:05:00Z"
}
```

> **SICHERHEITSKRITISCH:**
> - `token` wird genau **einmal** zurückgegeben — in dieser Response.
> - In der DB wird nur `SHA-256(token)` gespeichert.
> - Kein weiterer Endpoint gibt den Token zurück.
> - Empfänger muss Token sicher aufbewahren (Clipboard/Passwort-Manager).

---

### 6.3 `POST /governance/approvals/confirm`

**Auth:** ADMIN
**Zweck:** Bestätigt Approval (2-step confirmation).

**Request Body:**
```json
{
  "approval_id":   "uuid-v4",
  "confirm_token": "raw-plaintext-token",
  "approved":      true
}
```

**Response 200:**
```json
{
  "status":      "APPROVED",
  "decision_id": "uuid-v4",
  "approved_by": "user:admin_456",
  "approved_at": "2026-02-25T10:03:00Z"
}
```

**Fehlercodes:**

| HTTP | Bedeutung                                    |
|------|----------------------------------------------|
| 403  | Token ungültig (hash match failed)           |
| 409  | Token bereits konsumiert (Replay Protection) |
| 410  | Token abgelaufen (TTL exceeded)              |
| 404  | approval_id nicht gefunden                   |

---

### 6.4 `GET /governance/decisions/{decision_id}`

**Auth:** ADMIN
**Zweck:** Decision Details inkl. Approval-Status.

**Response 200:**
```json
{
  "decision_id":    "uuid-v4",
  "request_id":     "uuid-v4",
  "subject":        "user:u_123",
  "role":           "admin",
  "action":         "knowledge.reset",
  "risk":           "high",
  "result":         "REQUIRE_APPROVAL",
  "reason":         "action requires admin approval (risk=high)",
  "policy_version": 1,
  "created_at":     "2026-02-25T10:00:00Z",
  "meta":           { "path": "/api/knowledge-graph/reset" },
  "approval": {
    "approval_id":  "uuid-v4",
    "status":       "APPROVED",
    "approved_by":  "user:admin_456",
    "expires_at":   "2026-02-25T10:05:00Z",
    "approved_at":  "2026-02-25T10:03:00Z"
  }
}
```

---

## 7) Integration Standard (Backend)

### 7.1 `extract_subject()` — Dependency (VERBINDLICH)

```python
from app.core.security import get_current_principal

async def extract_subject(
    principal: Principal = Depends(get_current_principal)
) -> GovernanceSubject:
    """
    Ermittelt Subject + Role aus validiertem Principal.

    Trust-Quellen (in Priorität):
    1. JWT-validierter Principal aus get_current_principal() → user:<id>
    2. Agent-Bearer-Token (HMAC-signiert) → agent:<id>

    NIEMALS vertrauen:
    - X-Subject Header vom Client (Header-Spoofing-Risiko)
    - Query-Parameter
    - Unvalidierte Request-Bodies
    """
    if principal.is_agent:
        return GovernanceSubject(
            subject=f"agent:{principal.agent_id}",
            role="agent",
            karma=principal.karma
        )
    return GovernanceSubject(
        subject=f"user:{principal.user_id}",
        role=principal.role.value,
        karma=principal.karma
    )
```

### 7.2 Enforcement Pattern (MUSS in jedem geschützten Endpoint)

```python
from app.modules.governance.engine import GovernanceEngine
from app.modules.governance.types import DecisionResult

@router.post("/knowledge-graph/reset")
async def reset_knowledge_graph(
    subject: GovernanceSubject = Depends(extract_subject),
    db: AsyncSession = Depends(get_db)
):
    # SCHRITT 1: Governance-Entscheidung einholen
    decision = await GovernanceEngine.decide(
        db=db,
        subject=subject.subject,
        role=subject.role,
        action="knowledge.reset",
        context={"path": "/knowledge-graph/reset"}
    )

    # SCHRITT 2: DENY → 403
    if decision.result == DecisionResult.DENY:
        raise HTTPException(
            status_code=403,
            detail={"message": "Action not permitted", "decision_id": str(decision.decision_id)}
        )

    # SCHRITT 3: REQUIRE_APPROVAL → 202 (nicht 409, nicht 423!)
    if decision.result == DecisionResult.REQUIRE_APPROVAL:
        raise HTTPException(
            status_code=202,
            detail={
                "message":     "Approval required before execution",
                "decision_id": str(decision.decision_id),
                "hint":        "POST /governance/approvals/request mit dieser decision_id"
            }
        )

    # SCHRITT 4: ALLOW → execute
    result = await knowledge_service.reset(db)
    return result
```

> **HTTP 202 für REQUIRE_APPROVAL** — nicht 409 (Conflict) oder 423 (Locked).
> 202 = "Accepted but not yet executed" — semantisch korrekt.

### 7.3 Pflicht-Enforcement (V1 Minimum)

Mindestens diese **zwei** Endpoints müssen V1-Governance nutzen:

1. **`POST /knowledge-graph/reset`** — action: `knowledge.reset`, risk: `high`
2. **`POST /missions/{id}/execute`** oder **`POST /agents/{id}/run`** — action: `agent.mission.execute`, risk: `medium`

---

## 8) Integration Standard (ControlDeck Proxy)

### 8.1 UI → Proxy

UI ruft ausschließlich `/api/proxy/*` auf. Optional kann die UI setzen:
- `x-governance-action` — Hint für den Proxy
- `x-governance-risk` — **NUR als Hint**, wird vom Proxy ignoriert (Policy ist autoritativ)

### 8.2 Proxy → Backend

Proxy setzt folgende Headers (vertrauenswürdig, da Proxy-interne Logik):

| Header               | Wert                                   | Pflicht |
|----------------------|----------------------------------------|---------|
| `x-request-id`       | UUID v4 (frisch generiert)             | ✅      |
| `x-subject`          | `user:<id>` aus validierter Session    | ✅      |
| `x-subject-role`     | `admin / operator / user`              | ✅      |
| `x-decision-id`      | UUID wenn Proxy Governance aufruft     | optional |

### 8.3 P1-Empfehlung: Proxy HMAC Signature

Um Header-Spoofing zu verhindern (falls Backend von außen erreichbar):

```
x-proxy-signature: HMAC-SHA256(payload, PROXY_SECRET)
```

Payload: `{request_id}:{subject}:{timestamp}` — Backend verifiziert vor Vertrauen.

---

## 9) Tests (V1 Minimum — ALLE müssen grün sein)

### 9.1 Unit Tests

```python
# tests/modules/governance/test_engine.py

async def test_policy_allow():
    """Operator darf knowledge.read ausführen (risk=low, no approval)."""
    decision = await engine.decide(subject="user:u1", role="operator", action="knowledge.read")
    assert decision.result == DecisionResult.ALLOW

async def test_policy_deny_role_mismatch():
    """User darf knowledge.reset nicht (requires_role=admin)."""
    decision = await engine.decide(subject="user:u1", role="user", action="knowledge.reset")
    assert decision.result == DecisionResult.DENY
    assert "role" in decision.reason

async def test_policy_deny_unknown_action():
    """Unbekannte Action → DENY (deny_by_default)."""
    decision = await engine.decide(subject="user:u1", role="admin", action="unknown.action")
    assert decision.result == DecisionResult.DENY

async def test_policy_require_approval():
    """Admin + knowledge.reset → REQUIRE_APPROVAL."""
    decision = await engine.decide(subject="user:admin", role="admin", action="knowledge.reset")
    assert decision.result == DecisionResult.REQUIRE_APPROVAL

async def test_risk_not_from_caller():
    """Risk in Entscheidung entspricht Policy, nicht Request."""
    decision = await engine.decide(subject="user:admin", role="admin", action="knowledge.reset")
    assert decision.risk == "high"  # aus Policy, nicht aus Request
```

### 9.2 Integration Tests

```python
# tests/modules/governance/test_integration.py

async def test_destructive_endpoint_blocked_without_approval(client, admin_token):
    """knowledge.reset schlägt mit 202 fehl wenn kein Approval vorhanden."""
    response = await client.post(
        "/knowledge-graph/reset",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 202
    assert "decision_id" in response.json()["detail"]

async def test_approval_flow_enables_action(client, admin_token, db):
    """Vollständiger Approval-Flow: request → confirm → execute."""
    # 1. Trigger decision
    resp = await client.post("/knowledge-graph/reset", headers=auth(admin_token))
    decision_id = resp.json()["detail"]["decision_id"]

    # 2. Request approval
    resp = await client.post("/governance/approvals/request",
        json={"decision_id": decision_id, "requested_by": "user:admin", "reason": "Test"},
        headers=auth(admin_token)
    )
    assert resp.status_code == 201
    token = resp.json()["token"]
    approval_id = resp.json()["approval_id"]

    # 3. Confirm approval
    resp = await client.post("/governance/approvals/confirm",
        json={"approval_id": approval_id, "confirm_token": token, "approved": True},
        headers=auth(admin_token)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

async def test_audit_decision_stored(db, admin_token):
    """Jede Entscheidung wird in governance_decisions persistiert."""
    await engine.decide(subject="user:admin", role="admin", action="knowledge.reset")
    decisions = await db.execute(select(GovernanceDecision).order_by(GovernanceDecision.created_at.desc()))
    latest = decisions.scalars().first()
    assert latest is not None
    assert latest.action == "knowledge.reset"

async def test_token_replay_rejected(client, admin_token):
    """Approval Token kann nicht zweimal verwendet werden."""
    # ... setup approval ...
    resp1 = await client.post("/governance/approvals/confirm",
        json={"approval_id": approval_id, "confirm_token": token, "approved": True},
        headers=auth(admin_token)
    )
    assert resp1.status_code == 200

    resp2 = await client.post("/governance/approvals/confirm",
        json={"approval_id": approval_id, "confirm_token": token, "approved": True},
        headers=auth(admin_token)
    )
    assert resp2.status_code == 409  # Token bereits konsumiert
```

---

## 10) Operational Standard

### 10.1 Policy Updates

- Policies **ausschließlich via Git** — kein direktes Bearbeiten auf dem Server
- PR + Review durch mindestens eine weitere Person
- Policy version bei breaking changes incrementieren
- Nach Deployment: Governance-Engine neu starten (kein Hot-Reload ohne Audit-Trail)

### 10.2 Logs & Audit

- Jeder Request **muss** `request_id` (UUID) haben
- Jede Entscheidung **muss** `decision_id` (UUID) haben
- Audit-Log ist **append-only** — keine Updates, keine Deletes
- Audit exportierbar (CSV/JSON) — Admin-Endpoint in V1.1

### 10.3 Monitoring

- Alert wenn DENY-Rate > 10% in 5 Minuten (mögliche Attacke)
- Alert wenn REQUIRE_APPROVAL Tokens ohne Confirmation ablaufen (Prozess-Lücke)
- Alert wenn Policy-Version ≠ erwartete Version (Deployment-Fehler)

---

## 11) Definition of Done (V1)

- [x] Standalone Modul vorhanden (nicht verteilt über Controller)
- [x] `deny_by_default: true` aktiv in Policy
- [x] Policy YAML geladen + gecacht + versioniert
- [x] `POST /governance/decide` vorhanden — **Risk kommt aus Policy, nicht Request**
- [x] `POST /governance/approvals/request` — Token einmalig zurückgegeben, Hash in DB
- [x] `POST /governance/approvals/confirm` — Token-Verifikation + Replay-Protection
- [x] `GET /governance/decisions/{id}` — Decision Details
- [x] Decisions persistiert in `governance_decisions`
- [x] 2 Endpoints enforced (`knowledge.reset`, `agent.mission.execute`)
- [x] Unit Tests vorhanden und grün
- [x] Integration Tests vorhanden und grün
- [x] `extract_subject()` nutzt JWT/Agent-Auth — kein Header-Spoofing
- [x] HTTP 202 für REQUIRE_APPROVAL (nicht 409/423)
- [x] Dokumentation vollständig (dieses Dokument)

---

## 12) Claude Code Gate Checklist

Vor jedem Merge/Deploy prüfen:

- [ ] Standalone module existiert (nicht scattered logic)
- [ ] `deny_by_default` ist `true`
- [ ] Risk-Level kommt aus Policy, **NICHT aus dem Request**
- [ ] Approval tokens werden **genau einmal** zurückgegeben
- [ ] Token in DB als **SHA-256-Hash** gespeichert (nie Plaintext)
- [ ] HTTP **202** für REQUIRE_APPROVAL (nicht 409, nicht 423)
- [ ] `extract_subject()` vertraut keinen Client-Headers direkt
- [ ] Mindestens **2 Endpoints** tatsächlich enforced
- [ ] Tests pass (unit + integration)
- [ ] Kein Bypass-Pfad identifiziert

---

## 13) Bekannte Sicherheitskorrekturen (vs. ursprüngliches Template)

| # | Fehler | Schwere | Fix |
|---|--------|---------|-----|
| F1 | `risk` war client-supplied im Request Body | KRITISCH | Risk ausschließlich aus Policy geladen |
| F2 | Token fehlte in `/approvals/request` Response | KRITISCH | Token einmalig in Response, Hash in DB |
| F3 | HTTP 409/423 für REQUIRE_APPROVAL | KRITISCH | HTTP 202 Accepted |
| F4 | `confirm_delete: true` (zu spezifisch) | MEDIUM | `approved: true` (generisch) |
| F5 | `agent.mission.execute` ohne `requires_role` | MEDIUM | `requires_role: operator` explizit |
| F6 | `extract_subject()` ohne Header-Trust-Spezifikation | LOW | JWT-first, niemals Client-Header direkt |

---

*Letzte Änderung: 2026-02-25 — Claude Code Security Review*
*Nächste Review: vor V1.1 Deployment*
