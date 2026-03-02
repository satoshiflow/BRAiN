# Credits Add Endpoint - Dokumentation

**Erstellt:** 2026-02-05
**Feature:** Dedicated `/api/credits/add` endpoint für Credits nachladen
**Status:** ✅ Implementiert

---

## 📋 Zusammenfassung

Neuer dedizierter Endpoint zum Hinzufügen von Credits zu bestehenden Agents. Semantisch klarer als die Verwendung von `/refund` für Budget-Aufstockungen.

## 🆕 Was wurde hinzugefügt

### 1. Router Endpoint (`backend/app/modules/credits/router.py`)

```python
@router.post("/add", response_model=Dict)
async def add_credits(request: AddCreditsRequest)
```

**Request Model:**
```python
class AddCreditsRequest(BaseModel):
    agent_id: str        # Agent der Credits erhält
    amount: float        # Anzahl Credits (muss > 0 sein)
    reason: str          # Grund für die Zuteilung
    actor_id: str        # Wer die Credits vergibt (default: "system")
```

### 2. Service Layer (`backend/app/modules/credits/service.py`)

```python
async def add_agent_credits(
    agent_id: str,
    amount: float,
    reason: str,
    actor_id: str = "system"
) -> Dict
```

### 3. Event Sourcing (`backend/app/modules/credits/integration_demo.py`)

```python
async def add_credits(
    self,
    agent_id: str,
    amount: float,
    reason: str,
    actor_id: str = "system"
) -> float
```

**Event Type:** `CREDIT_ALLOCATED`
Nutzt das bestehende Event für semantische Klarheit ("allocated" = "zugeteilt/hinzugefügt")

---

## 🔧 Verwendung

### cURL Beispiel

```bash
curl -X POST http://localhost:8000/api/credits/add \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_001",
    "amount": 100.0,
    "reason": "Monatliches Budget aufgestockt",
    "actor_id": "admin"
  }'
```

**Response:**
```json
{
  "agent_id": "agent_001",
  "amount": 100.0,
  "balance_after": 150.0,
  "reason": "Monatliches Budget aufgestockt"
}
```

### Python Beispiel

```python
from app.modules.credits import service

# Credits hinzufügen
result = await service.add_agent_credits(
    agent_id="agent_001",
    amount=100.0,
    reason="Monthly budget top-up",
    actor_id="admin"
)

print(f"New balance: {result['balance_after']}")
# Output: New balance: 150.0
```

---

## 🧪 Test Script

Ein vollständiges Test-Script ist verfügbar:

```bash
./test_add_credits.sh
```

**Was der Test macht:**
1. Erstellt Test-Agent mit initialen Credits (skill_level=0.5 → 50 Credits)
2. Prüft initiale Balance
3. Fügt 100 Credits hinzu via `/add` Endpoint
4. Prüft Balance nach Addition
5. Fügt weitere 50 Credits hinzu
6. Zeigt finale Balance und Transaction History

**Erwartete Ausgabe:**
- Initial: 50.0 Credits
- Nach +100: 150.0 Credits
- Nach +50: 200.0 Credits

---

## 🆚 Vergleich: `/add` vs. `/refund`

| Aspekt | `/add` | `/refund` |
|--------|--------|-----------|
| **Semantik** | Credits hinzufügen | Credits zurückerstatten |
| **Use Case** | Budget-Aufstockung, Bonus | Mission fehlgeschlagen |
| **Event Type** | `CREDIT_ALLOCATED` | `CREDIT_REFUNDED` |
| **mission_id** | Nicht erforderlich | Optional |
| **Klarheit** | ✅ Klar | 🟡 Missverständlich für Budget-Tops |

**Empfehlung:** Nutze `/add` für alle Budget-Aufstockungen und `/refund` nur für tatsächliche Rückerstattungen.

---

## 📊 Use Cases

### 1. Monatliches Budget
```bash
curl -X POST http://localhost:8000/api/credits/add \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_001",
    "amount": 1000.0,
    "reason": "Monatliches Budget Februar 2026",
    "actor_id": "billing_system"
  }'
```

### 2. Performance Bonus
```bash
curl -X POST http://localhost:8000/api/credits/add \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "top_performer_agent",
    "amount": 500.0,
    "reason": "Q1 Performance Bonus",
    "actor_id": "hr_system"
  }'
```

### 3. Admin Credit Grant
```bash
curl -X POST http://localhost:8000/api/credits/add \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "premium_agent",
    "amount": 2000.0,
    "reason": "Premium Subscription aktiviert",
    "actor_id": "admin_user_123"
  }'
```

---

## 🔍 Fehlerbehandlung

### Insufficient Balance (bei consume, nicht bei add)
Credits können unbegrenzt hinzugefügt werden. Es gibt keine maximale Balance.

### Event Sourcing Not Available
```json
{
  "detail": "Event Sourcing not available"
}
```
**Lösung:** Stelle sicher dass Event Sourcing initialisiert ist (sollte beim App-Start passieren).

### Agent Not Found
Das System erlaubt Credits zu nicht-existierenden Agents hinzuzufügen. Eine Warnung wird geloggt.

---

## 🔐 Security & Audit

### Event Sourcing
Jede Credit-Addition wird als immutable Event gespeichert:

```json
{
  "event_id": "evt_abc123",
  "event_type": "credit.allocated",
  "timestamp": "2026-02-05T12:00:00Z",
  "actor_id": "admin",
  "correlation_id": "agent_001",
  "payload": {
    "entity_id": "agent_001",
    "entity_type": "agent",
    "amount": 100.0,
    "reason": "Monthly budget top-up",
    "balance_after": 150.0
  }
}
```

### Audit Trail
Vollständige Transaction History verfügbar:

```bash
curl http://localhost:8000/api/credits/history/agent_001?limit=10
```

---

## 📝 Migration von Refund zu Add

Wenn du bisher `/refund` für Budget-Aufstockungen genutzt hast:

**Alt (verwirrend):**
```bash
curl -X POST /api/credits/refund \
  -d '{"agent_id": "agent_001", "amount": 100.0, "reason": "Budget top-up"}'
```

**Neu (klar):**
```bash
curl -X POST /api/credits/add \
  -d '{"agent_id": "agent_001", "amount": 100.0, "reason": "Monthly budget"}'
```

**Beide Endpoints sind funktional identisch**, aber `/add` ist semantisch korrekter.

---

## 🚀 Future Enhancements

Mögliche zukünftige Erweiterungen:

1. **Bulk Add:** Mehrere Agents gleichzeitig auffüllen
   ```bash
   POST /api/credits/add/bulk
   ```

2. **Scheduled Adds:** Automatische monatliche Budget-Zuteilung
   ```python
   schedule.every().month.at("00:00").do(add_monthly_budget)
   ```

3. **Credit Limits:** Maximale Balance pro Agent
   ```python
   if balance_after > agent.max_balance:
       raise ValueError("Balance would exceed limit")
   ```

4. **Credit Packs:** Vordefinierte Pakete
   ```python
   CREDIT_PACKS = {
       "basic": 100.0,
       "premium": 500.0,
       "enterprise": 2000.0
   }
   ```

---

## 📚 Related Endpoints

- **GET** `/api/credits/balance/{agent_id}` - Balance abfragen
- **GET** `/api/credits/history/{agent_id}` - Transaction History
- **POST** `/api/credits/consume` - Credits verbrauchen
- **POST** `/api/credits/refund` - Credits zurückerstatten
- **POST** `/api/credits/agents` - Neuen Agent mit initialen Credits erstellen

---

## ✅ Checklist für Deployment

- [x] Router Endpoint implementiert
- [x] Service Layer implementiert
- [x] Event Sourcing Integration
- [x] Request/Response Models definiert
- [x] Test Script erstellt
- [x] Dokumentation geschrieben
- [ ] Integration Tests hinzufügen
- [ ] Swagger UI Dokumentation aktualisieren
- [ ] Backend neu deployen

---

**Erstellt von:** Claude Code Assistant
**Datum:** 2026-02-05
**PR:** TBD
