# 🐳 Docker Setup Analysis — Credit System Event Sourcing

**Zweck:** Dokumentation der tatsächlich genutzten Services für Live-Tests
**Datum:** 2024-12-30
**Branch:** `claude/event-sourcing-foundation-GmJza`

---

## 📋 Executive Summary

**Kernaussage:**
Das Credit System Event Sourcing (Phasen 7–10) ist **infrastrukturell autark** und benötigt **keine** externen Datenbank- oder Cache-Services.

**Für Live-Tests erforderlich:**
- ✅ `backend` Service (Container)
- ❌ `postgres` — Definiert, aber **logisch nicht genutzt**
- ❌ `redis` — Definiert, aber **logisch nicht genutzt**
- ❌ `qdrant`, `ollama`, `openwebui` — Optional, nicht relevant

---

## 🔍 Docker Compose Struktur

### Haupt-Compose-Datei
**Pfad:** `/home/user/BRAiN/docker-compose.yml`

### Definierte Services (8)

| Service | Container Name | Status | Logisch Genutzt? |
|---------|---------------|--------|------------------|
| **backend** | `brain-backend` | ✅ Aktiv | ✅ **JA** (Core Runtime) |
| **control_deck** | `brain-control-deck` | ✅ Aktiv | ⚠️ Optional (Frontend) |
| **axe_ui** | `brain-axe-ui` | ✅ Aktiv | ⚠️ Optional (Frontend) |
| **postgres** | `brain-postgres` | ✅ Defined | ❌ **NEIN** (Phase 5+) |
| **redis** | `brain-redis` | ✅ Defined | ❌ **NEIN** (Phase 5+) |
| **qdrant** | `brain-qdrant` | ✅ Defined | ❌ NEIN (Vector DB) |
| **ollama** | `brain-ollama` | ✅ Defined | ❌ NEIN (LLM) |
| **openwebui** | `brain-openwebui` | ✅ Defined | ❌ NEIN (UI) |

---

## 🎯 Event Sourcing Implementation Details

### Aktueller Stand (CQRS-Light)

**Phase:** 7–10 (Resource Pools, Synergie, Human Gates, KARMA, ML)
**Architektur:** Append-Only Event-Journal + In-Memory Projections
**Persistenz:** File-based JSONL

### Storage Layer

```python
# backend/app/modules/credits/event_sourcing/event_journal.py
class EventJournal:
    def __init__(
        self,
        file_path: str | Path = "storage/events/credits.jsonl",  # ← FILE-BASED!
        enable_fsync: bool = True,
    ):
        self.file_path = Path(file_path)
        self.enable_fsync = enable_fsync
        self._seen_idempotency_keys: Set[str] = set()  # ← IN-MEMORY!
```

**Eigenschaften:**
- ✅ Zero external dependencies
- ✅ Pure Python file I/O mit fsync
- ✅ In-Memory Idempotency tracking
- ✅ Graceful corruption recovery

### Projections (Read Models)

Alle Projections sind **In-Memory**:

| Projection | Zweck | Storage |
|------------|-------|---------|
| `BalanceProjection` | Agent-Balances | In-Memory Dict |
| `LedgerProjection` | Transaction History | In-Memory List |
| `ApprovalProjection` | Human Approval State | In-Memory Dict |
| `SynergieProjection` | Team Rewards | In-Memory Dict |

**Keine Redis/Postgres-Nutzung!**

---

## 🚀 Live-Test Requirements

### Minimale Service-Konfiguration

```bash
# NUR Backend starten (ausreichend für Event Sourcing Tests)
docker compose up -d backend

# Verifizieren
docker compose ps
docker compose logs -f backend
```

### Optionale Services (für Integrationstests)

```bash
# Mit Frontends (falls UI-Tests gewünscht)
docker compose up -d backend control_deck axe_ui

# Voller Stack (inkl. dormanter Services)
docker compose up -d  # Startet alle 8 Services
```

---

## 📊 Dependency Matrix

### Backend Service Dependencies (docker-compose.yml)

```yaml
backend:
  depends_on:
    - postgres  # ← Compose-Dependency, aber LOGISCH NICHT GENUTZT
    - redis     # ← Compose-Dependency, aber LOGISCH NICHT GENUTZT
```

**Analyse:**
- `depends_on` ist **Startorder-Constraint**, kein Nutzungsnachweis
- Backend startet nach Postgres/Redis, **nutzt sie aber nicht**
- Event Sourcing läuft komplett datenbankfrei

### Beweis: Code-Analyse

```bash
# Redis-Nutzung im Credit System?
grep -r "redis\|Redis\|REDIS" backend/app/modules/credits/
# → Keine Treffer!

# Postgres-Nutzung im Credit System?
grep -r "postgres\|PostgreSQL\|DATABASE_URL" backend/app/modules/credits/
# → Keine Treffer!
```

**Ergebnis:** ❌ Keine DB-Nutzung im Event Sourcing Credit System

---

## 🧪 Test Environment Setup

### Empfohlene Konfiguration

**Für Live-Tests:**
```bash
# 1. Backend starten
docker compose up -d backend

# 2. Gesundheitscheck
curl http://localhost:8000/api/health
curl http://localhost:8000/api/credits/health

# 3. Event Journal initialisieren (automatisch beim Start)
# → storage/events/credits.jsonl wird erstellt

# 4. Tests ausführen
docker compose exec backend pytest backend/tests/run_live_credit_tests.py
```

**Cleanup:**
```bash
# Event Journal löschen (für Neustart)
rm storage/events/credits.jsonl

# Container neu starten
docker compose restart backend
```

---

## ⚠️ Wichtige Einschränkungen

### Was NICHT getestet werden kann

1. **Postgres Event Store** (Phase 5)
   - Nicht implementiert
   - Service dormant

2. **Redis Event Bus** (Phase 7)
   - Nicht implementiert
   - Service dormant

3. **Distributed CQRS** (Phase 8)
   - Nicht implementiert
   - Multi-Instance Replay nicht möglich

### Was getestet werden KANN

✅ Event Integrity (Idempotency, Ordering, Schema)
✅ Projection Integrity (Balance == Sum(Deltas), No NaN/Inf)
✅ Crash Recovery (File-Replay mit corruption handling)
✅ Concurrency Safety (In-Memory Locks, OCC)
✅ Human Gate Workflow (Approval State Machine)
✅ KARMA Integration (wenn LLM verfügbar)
✅ ML Anomaly Detection (wenn Anomalie-Thresholds gesetzt)
✅ Load Testing (Throughput, Latency, Memory)

---

## 📈 Phasen-Roadmap

| Phase | Feature | DB/Redis? | Status |
|-------|---------|-----------|--------|
| 1–5 | Event Sourcing MVP | ❌ File | ✅ Aktiv |
| 6–9 | Integration & REST | ❌ File | ✅ Aktiv |
| 10 | MVP Testing | ❌ File | ✅ Aktiv |
| 11–14 | Extensions | ❌ File | ✅ Aktiv |
| **5a** | Postgres Event Store | ✅ Postgres | 🔒 Blockiert (nach Live-Test) |
| **6a** | Event Snapshots | ✅ Postgres | 🔒 Blockiert |
| **7a** | Redis Event Bus | ✅ Redis | 🔒 Blockiert |
| **8a** | CQRS-Full | ✅ Beide | 🔒 Blockiert |

---

## 🎯 Live-Test Scope

**Testziel:** Stabilität & Governance-Sicherheit der **file-based** Event Sourcing Implementation
**Out-of-Scope:** DB-Integration, Distributed Systems, Multi-Instance

**Hard Gates:**
- ✅ Gate A — Event Integrity (Idempotency, Ordering)
- ✅ Gate B — Projection Integrity (Balance Invariants)
- ✅ Gate C — Human Gate Safety (Approval Workflow)
- ✅ Gate D — Failure Safety (KARMA Blackout, ML Chaos)
- ✅ Gate E — Load Reality (30min Dauerlauf, P95 Latency)

---

## ✅ Empfehlung für Live-Tests

**Startkommando:**
```bash
docker compose up -d backend
```

**Begründung:**
1. Backend ist **autark** (keine DB-Dependencies)
2. Postgres/Redis sind **dormant** (nicht genutzt)
3. Tests sind **deterministisch** (file-based, single-instance)
4. Volle Kontrolle über Event Journal (reset via `rm`)

**Nicht starten:**
- ❌ `postgres`, `redis` — Nicht genutzt, erzeugen nur Noise
- ❌ `qdrant`, `ollama` — Irrelevant für Credit System
- ⚠️ `control_deck`, `axe_ui` — Optional für manuelle UI-Validierung

---

## 📝 Sign-Off

**Analyst:** Claude (Lead Engineer)
**Datum:** 2024-12-30
**Status:** ✅ APPROVED für Live-Tests (Backend-Only)
**Nächster Schritt:** Live-Test Playbook erstellen
