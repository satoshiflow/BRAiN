# MAX EXECUTION PROMPT — Governance Engine V1

**Datum:** 2026-02-25
**Auftraggeber:** BRAiN Core Team
**Ausführer:** Max (Multi-Agent Orchestrator)
**Priorität:** HIGH
**Branch:** `claude/fix-404-error-IK8D1`
**Referenz-Spec:** `docs/GOVERNANCE_V1_SPEC.md` (autoritatives Dokument — LESEN BEVOR START)

---

## MISSION BRIEFING

Implementiere das **BRAiN Governance Engine V1 Modul** vollständig nach Spec.

Die Spec ist **FINAL** und enthält 6 sicherheitskritische Korrekturen gegenüber dem ursprünglichen Template.
**Keine Abweichungen von der Spec ohne explizites Security Review.**

---

## FEHLERANALYSE (Claude Code Security Review — 2026-02-25)

Der ursprüngliche Template-Entwurf hatte folgende Fehler.
Diese sind in der Spec bereits korrigiert. Hier zur Klarheit nochmal dokumentiert:

### F1 — KRITISCH: Risk war client-supplied

**Problem:** Original-Template hatte `risk` im Request Body von `/governance/decide`:
```json
{ "action": "knowledge.reset", "risk": "high" }
```
Ein Attacker kann `"risk": "low"` setzen und die Policy umgehen.

**Fix in Spec:** `risk` wird **ausschließlich aus `policies/governance.yml`** geladen.
Nie aus dem Request. Engine ignoriert jedes risk-Feld im Request.

---

### F2 — KRITISCH: Token fehlte in `/approvals/request` Response

**Problem:** Original-Template gab nur zurück:
```json
{ "approval_id": "uuid", "expires_in_seconds": 300 }
```
Kein Token. `/approvals/confirm` braucht aber einen `confirm_token`. Unlösbare Lücke.

**Fix in Spec:**
```json
{
  "approval_id":         "uuid",
  "token":               "raw-plaintext-einmalig",
  "expires_in_seconds":  300,
  "expires_at":          "..."
}
```
Token wird **genau einmal** zurückgegeben. In DB nur als `SHA-256(token)`.
Kein Endpoint gibt Token ein zweites Mal zurück → Replay-Protection.

---

### F3 — KRITISCH: Falscher HTTP-Code für REQUIRE_APPROVAL

**Problem:** Original-Template: `→ 409 (oder 423) mit Approval hint`
- `409 Conflict` = semantisch falsch (kein Konflikt)
- `423 Locked` = Resource-Lock, nicht Approval-Flow

**Fix in Spec:** **HTTP `202 Accepted`**
```python
raise HTTPException(
    status_code=202,
    detail={"message": "Approval required", "decision_id": "..."}
)
```

---

### F4 — MEDIUM: `confirm_delete: true` zu spezifisch

**Problem:** `/approvals/confirm` hatte `"confirm_delete": true` im Body.
Governance ist action-agnostisch — `confirm_delete` ist sinnlos für `system.exec` oder `agent.mission.execute`.

**Fix in Spec:** `"approved": true` (generisch, action-unabhängig)

---

### F5 — MEDIUM: `agent.mission.execute` ohne `requires_role`

**Problem:** Policy-YAML hatte:
```yaml
agent.mission.execute:
  risk: medium
  min_karma: 70
  # requires_role FEHLTE
```
Ohne `requires_role` greift `deny_by_default: true` → jeder Call wird DENY.
Oder noch schlimmer: wenn deny_by_default deaktiviert wird → jeder kann ausführen.

**Fix in Spec:**
```yaml
agent.mission.execute:
  risk: medium
  requires_role: operator
  requires_approval: false
  min_karma: 70
```

---

### F6 — LOW: `extract_subject()` ohne Trust-Spezifikation

**Problem:** Section 7.1 beschrieb die Funktion aber nicht, welchen Headers vertraut wird.
Risiko: X-Subject Header vom Client direkt vertrauen → Header-Spoofing.

**Fix in Spec:** Explizite Priorisierung:
1. JWT-validierter Principal aus `get_current_principal()` → `user:<id>`
2. Agent-Bearer-Token (HMAC-signiert) → `agent:<id>`
3. **NIEMALS:** Client-Headers (`X-Subject`, etc.) direkt vertrauen

---

## IMPLEMENTIERUNGSAUFTRAG

### Schritt 1: Spec lesen
```
docs/GOVERNANCE_V1_SPEC.md
```
Vollständig lesen. Alle 13 Sections. Dann starten.

---

### Schritt 2: Modulstruktur anlegen

```
backend/app/modules/governance/
├── __init__.py
├── engine.py
├── policy_store.py
├── approval.py
├── audit.py
├── models.py
├── types.py
├── router.py
└── policies/
    └── governance.yml
```

---

### Schritt 3: DB-Migrationen

Erstelle Alembic-Migration für:
- `governance_decisions`
- `governance_approvals`
- `audit_log`

Schema exakt nach Spec Section 4.

---

### Schritt 4: Core implementieren

**Reihenfolge:**
1. `types.py` — Enums + Pydantic Models
2. `models.py` — SQLAlchemy Models
3. `policy_store.py` — YAML Loader + Cache
4. `engine.py` — `decide()` Funktion
5. `approval.py` — Token-Lifecycle
6. `audit.py` — Persistenz
7. `router.py` — FastAPI Endpoints

**Kritische Implementierungsdetails:**

```python
# engine.py — Risk NIEMALS aus Request lesen
async def decide(self, subject: str, role: str, action: str, context: dict) -> GovernanceDecision:
    policy = await self.policy_store.get_action_policy(action)
    if not policy:
        return self._deny(action, "no policy found (deny_by_default)")

    risk = policy.risk  # ← aus Policy, NICHT aus Parametern
    # ... rest der Logik

# approval.py — Token Handling
import hashlib, secrets

def generate_token() -> tuple[str, str]:
    """Returns (raw_token, token_hash)"""
    raw = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed

# Beim Speichern: nur hashed in DB
# In Response: nur raw zurückgeben, einmalig
```

---

### Schritt 5: Enforcement in 2 bestehenden Endpoints

**Endpoint 1:** `backend/app/modules/knowledge_graph/router.py`
- Route: `POST /knowledge-graph/reset` (oder äquivalent)
- Action: `knowledge.reset`
- Enforcement nach Pattern Section 7.2 der Spec

**Endpoint 2:** `backend/app/modules/missions/router.py` (oder äquivalent)
- Route: `POST /missions/{id}/execute`
- Action: `agent.mission.execute`
- Enforcement nach Pattern Section 7.2 der Spec

---

### Schritt 6: Tests schreiben

Alle Tests aus Spec Section 9 implementieren:

**Unit Tests** (`tests/modules/governance/test_engine.py`):
- `test_policy_allow`
- `test_policy_deny_role_mismatch`
- `test_policy_deny_unknown_action`
- `test_policy_require_approval`
- `test_risk_not_from_caller`

**Integration Tests** (`tests/modules/governance/test_integration.py`):
- `test_destructive_endpoint_blocked_without_approval`
- `test_approval_flow_enables_action` (vollständiger Flow)
- `test_audit_decision_stored`
- `test_token_replay_rejected`

**Alle Tests müssen grün sein vor Commit.**

---

### Schritt 7: Gate Checklist abhaken

Vor dem finalen Commit jede Zeile aus Spec Section 12 prüfen:

- [ ] Standalone module existiert
- [ ] `deny_by_default` ist `true`
- [ ] Risk kommt aus Policy, NICHT aus Request
- [ ] Token einmalig zurückgegeben
- [ ] Token in DB als SHA-256-Hash
- [ ] HTTP 202 für REQUIRE_APPROVAL
- [ ] `extract_subject()` vertraut keinen Client-Headers
- [ ] 2 Endpoints enforced
- [ ] Tests pass
- [ ] Kein Bypass-Pfad

---

## AGENT-EMPFEHLUNG (9 Agenten parallel)

Basierend auf letztem erfolgreichen Run empfohlene Aufteilung:

| Agent | Aufgabe |
|-------|---------|
| A1 | `types.py` + `models.py` |
| A2 | `policy_store.py` + `governance.yml` |
| A3 | `engine.py` (decide-Logik) |
| A4 | `approval.py` (Token-Lifecycle) |
| A5 | `audit.py` + DB-Migration |
| A6 | `router.py` (alle 4 Endpoints) |
| A7 | Enforcement in `knowledge_graph/router.py` |
| A8 | Enforcement in `missions/router.py` |
| A9 | Tests (unit + integration) |

**Synchronisationspunkte:**
- A3 braucht A2 (Policy Store) — A3 startet nach A2
- A6 braucht A3+A4+A5 — A6 startet zuletzt
- A7+A8 brauchen A3 (Engine) — parallel zu A6 möglich
- A9 startet wenn A1-A8 abgeschlossen

---

## ERFOLGSKRITERIEN

```bash
# Diese Commands müssen alle erfolgreich durchlaufen:
pytest tests/modules/governance/ -v       # alle grün
pytest tests/modules/knowledge_graph/ -v  # reset-Tests grün
pytest tests/modules/missions/ -v         # execute-Tests grün

# Smoke Test:
curl -X POST /governance/decide \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"action":"knowledge.reset","subject":"user:admin","role":"admin","context":{}}'
# Expected: {"result": "REQUIRE_APPROVAL", "risk": "high"}

# NICHT expected (Bug F1 würde triggern wenn risk aus Request):
# Wenn result=ALLOW → Spec verletzt, sofort reporten
```

---

## WICHTIGE EINSCHRÄNKUNGEN

1. **KEINE** neuen npm/pip Pakete ohne Absprache
2. **KEINE** Änderungen an bestehender Auth (`get_current_principal`)
3. **KEINE** Policy-Logik in Router oder Controller — ausschließlich in `engine.py`
4. **KEIN** Hot-Reload von Policies ohne Audit-Trail
5. Bei **Unklarheiten zur Spec** → Spec ist autoritativ. Bei echten Widersprüchen: reporten, nicht raten.

---

## OUTPUT (wenn fertig)

Committe auf Branch `claude/fix-404-error-IK8D1`:

```
feat(governance): implement governance engine v1

- Standalone governance module with deny-by-default
- Policy YAML with versioning (governance.yml)
- decide() endpoint: risk from policy only (not caller-supplied)
- approval flow: token returned once, SHA-256 hash in DB
- HTTP 202 for REQUIRE_APPROVAL (not 409/423)
- enforcement in knowledge_graph/reset + missions/execute
- unit + integration tests (all green)

Security fixes: F1-F6 from Claude Code review applied
Ref: docs/GOVERNANCE_V1_SPEC.md
```

---

*Generated by Claude Code — 2026-02-25*
*Security Review: PASSED (with 6 fixes applied)*
