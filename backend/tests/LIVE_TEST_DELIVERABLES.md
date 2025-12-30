# 🎯 BRAiN Credit System — Live Test Deliverables

**Status:** ✅ **COMPLETE** — Ready for Execution
**Datum:** 2024-12-30
**Branch:** `claude/event-sourcing-foundation-GmJza`
**Verantwortlich:** Claude (Lead Engineer & Reliability Owner)

---

## 📦 Was wurde geliefert?

### 1. Docker Setup Analyse ✅

**Datei:** `DOCKER_SETUP_ANALYSIS.md`

**Inhalt:**
- Vollständige Analyse des Docker Compose Setups
- Bewertung aller 8 Services (backend, postgres, redis, qdrant, ollama, etc.)
- **Kernaussage:** Credit System ist **infrastrukturell autark** (file-based, in-memory)
- **Postgres/Redis:** Dormant (nicht genutzt für Event Sourcing)
- **Für Live-Tests erforderlich:** Nur `backend` Service

**Key Finding:**
```
Event Journal: File-based JSONL (storage/events/credits.jsonl)
Projections: In-Memory (Balance, Ledger, Approval, Synergie)
→ KEINE DB/Redis-Dependencies!
```

---

### 2. Live Test Playbook ✅

**Datei:** `live_credit_system_playbook.md`

**Inhalt:**
- Schritt-für-Schritt Anleitung für Live-Tests
- 6 Pflicht-Szenarien (Credit Storm, Synergy, Approval Race, KARMA Blackout, ML Chaos, Crash/Replay)
- 5 Hard Gates (Event Integrity, Projection Integrity, Human Gate Safety, Failure Safety, Load Reality)
- Testparameter (Concurrency, Duration, Seeds)
- Erwartete Ergebnisse & Failure-Symptome
- Go/No-Go Kriterien

**Verwendung:**
```bash
# Playbook lesen
cat backend/tests/live_credit_system_playbook.md

# Tests vorbereiten
docker compose up -d backend
```

---

### 3. Test Harness ✅

**Datei:** `run_live_credit_tests.py` (900+ Zeilen)

**Features:**
- ✅ 6 vollständig implementierte Szenarien
- ✅ Concurrency-Simulation (50/100/300 parallel)
- ✅ Retry & Duplicate Injection (Idempotency-Tests)
- ✅ Deterministische Seeds (reproduzierbare Tests)
- ✅ Metrics-Sammlung (Throughput, Latency, Memory)
- ✅ JSON-Report-Generation
- ✅ CLI-Interface mit argparse

**Szenarien:**
1. **Credit Storm / Reuse Cascade** — Massive parallele Consumption (Invarianten-Check)
2. **Synergy Anti-Gaming Loop** — Reward-Caps (Anti-Gaming-Mechanismus)
3. **Approval Race / Concurrency** — OCC-Serialisierung (Human Gate Safety)
4. **KARMA Blackout** — LLM-Ausfall-Fallback (Resilience)
5. **ML Chaos Injection** — Anomalie-Detection ohne Overreaction
6. **Crash / Replay** — Deterministische Replay-Konsistenz

**CLI-Beispiele:**
```bash
# Alle 6 Szenarien + Gates
docker compose exec backend python backend/tests/run_live_credit_tests.py --full

# Einzelnes Szenario
docker compose exec backend python backend/tests/run_live_credit_tests.py --scenario credit_storm

# Mit JSON-Report
docker compose exec backend python backend/tests/run_live_credit_tests.py --full --report-json reports/live_test_report.json

# Custom Concurrency
docker compose exec backend python backend/tests/run_live_credit_tests.py --concurrency 300 --seed 42
```

---

### 4. Invarianten-Checker ✅

**Datei:** `live_invariants.py` (400+ Zeilen)

**Hard Invariants:**
1. ✅ **Ledger Integrity:** `balance(agent) == sum(event_deltas)`
2. ✅ **No NaN/Inf:** Alle Balances sind finite floats
3. ✅ **No Negative Credits:** Keine negativen Balances (Business Rule)
4. ✅ **Idempotency:** Keine Duplikate (unique idempotency_keys)
5. ✅ **Projection Consistency:** Event Count ↔ Projection Count synchron

**Soft Invariants (Warnings):**
- Audit-Log-Completeness (correlation_id vorhanden)
- Approval Safety (max 1 final decision pro request)

**Verwendung:**
```python
from live_invariants import InvariantsChecker

checker = InvariantsChecker(credit_system)
all_ok = await checker.check_all(fail_fast=True)

if not all_ok:
    summary = checker.get_summary()
    print(f"Violations: {summary['violations']}")
```

**Standalone CLI:**
```bash
# Direkt ausführen
docker compose exec backend python backend/tests/live_invariants.py
```

---

### 5. Report Template ✅

**Datei:** `LIVE_TEST_REPORT_TEMPLATE.md`

**Struktur:**
1. Executive Summary (GO / CONDITIONAL / NO-GO)
2. Testumgebung (Docker, Services, Startkommandos)
3. Testparameter (Concurrency, Duration, Seeds)
4. Getestete Szenarien (Matrix: Szenario → Pass/Fail → Metriken)
5. Hard Gates Evaluation (A–E mit Checklisten)
6. Key Metrics (Throughput, Latency, Memory, EoC Score)
7. Findings & Risiken (Kritisch vs. Beobachtungen)
8. Entscheidungsbewertung (Phase-Freigabe)
9. Empfehlung (Nächste Schritte)
10. Sign-Off (Tester, Reviewer, Supervisor)

**Verwendung:**
```bash
# Template kopieren
cp backend/tests/LIVE_TEST_REPORT_TEMPLATE.md reports/live_test_report_$(date +%Y%m%d).md

# Befüllen mit Test-Ergebnissen
# (Automatisch via --report-json)
```

---

## 🚀 Wie ausführen?

### Schritt 1: Docker Setup

```bash
cd /home/user/BRAiN

# Backend starten (OHNE Postgres/Redis — nicht genutzt!)
docker compose up -d backend

# Verifizieren
docker compose ps
curl http://localhost:8000/api/health
curl http://localhost:8000/api/credits/health
```

---

### Schritt 2: Vollständiger Test-Durchlauf

```bash
# Alle 6 Szenarien + 5 Gates
docker compose exec backend python backend/tests/run_live_credit_tests.py --full --report-json reports/live_test_report.json

# Logs anschauen
docker compose logs -f backend

# Report lesen
cat reports/live_test_report.json | jq .
```

---

### Schritt 3: Einzelne Szenarien (Debug)

```bash
# Credit Storm (Concurrency-Test)
docker compose exec backend python backend/tests/run_live_credit_tests.py --scenario credit_storm --concurrency 100

# Crash/Replay (Wichtigster Test!)
docker compose exec backend python backend/tests/run_live_credit_tests.py --scenario crash_replay

# KARMA Blackout (Resilience)
docker compose exec backend python backend/tests/run_live_credit_tests.py --scenario karma_blackout
```

---

### Schritt 4: Invarianten manuell prüfen

```bash
# Standalone Invarianten-Check
docker compose exec backend python backend/tests/live_invariants.py

# Erwartete Ausgabe:
# ✅ Ledger invariants OK (N agents)
# ✅ No NaN/Inf (N agents)
# ✅ No negative credits (N agents)
# ✅ Idempotency OK (N unique events)
# ✅ Projection consistency OK
# ✅ All invariants PASS
```

---

## 📊 Erwartete Ergebnisse (Baseline)

### Szenarien-Matrix (Target)

| Szenario | Status | Throughput | P95 Latency | Invarianten |
|----------|--------|------------|-------------|-------------|
| Credit Storm | ✅ PASS | > 100 req/s | < 300 ms | ✅ OK |
| Synergy Anti-Gaming | ✅ PASS | — | — | ✅ OK |
| Approval Race | ✅ PASS | — | < 100 ms | ✅ OK |
| KARMA Blackout | ✅ PASS | — | — | ✅ OK |
| ML Chaos | ✅ PASS | — | — | ✅ OK |
| Crash/Replay | ✅ PASS | — | — | ✅ OK |

---

### Gates-Matrix (Target)

| Gate | Kriterium | Target | Actual |
|------|-----------|--------|--------|
| A — Event Integrity | Idempotency Violations | 0 | — |
| B — Projection Integrity | Balance Drift | 0.0 | — |
| C — Human Gate Safety | Approval Races | 0 | — |
| D — Failure Safety | Crashes | 0 | — |
| E — Load Reality | Runtime | ≥ 30 Min | — |

---

## ⚠️ Bekannte Einschränkungen

### Was NICHT getestet werden kann (aktuell)

1. **Postgres Event Store** (Phase 5a)
   - Nicht implementiert
   - Tests verwenden file-based Journal

2. **Redis Event Bus** (Phase 7a)
   - Nicht implementiert
   - Tests verwenden In-Memory EventBus

3. **Distributed CQRS** (Phase 8a)
   - Nicht implementiert
   - Multi-Instance Replay nicht möglich

4. **Docker in dieser Umgebung**
   - Docker CLI nicht verfügbar in Claude Code Umgebung
   - **User muss Tests selbst auf lokalem System ausführen**

---

## 🎯 Go/No-Go Kriterien

### ✅ GO — Phase 5a freigegeben

**Bedingungen:**
- ✅ Alle 6 Szenarien: PASS
- ✅ Alle 5 Gates: PASS
- ✅ Keine kritischen Failures (Negative Balance, Race Conditions, Crashes)
- ✅ P95 Latency < 500 ms
- ✅ 30-Min-Dauerlauf ohne Drift
- ✅ Memory-Leak-Trend < 0.1 MB/min

**Empfehlung:**
> "System stabil. Event Sourcing Foundation production-ready. **Freigabe für Phase 5a (Postgres Event Store)**."

---

### ⚠️ CONDITIONAL — Weiter testen

**Bedingungen:**
- ⚠️ 1–2 Szenarien: FAIL (nicht-kritisch)
- ⚠️ Gates A/B: PASS, aber C/D/E: Warnungen
- ⚠️ P95 > 500 ms, aber < 1000 ms
- ⚠️ Memory-Leak-Trend < 0.5 MB/min

**Empfehlung:**
> "System grundsätzlich stabil, aber Performance/Governance-Optimierung nötig. **Weiter testen für 3–7 Tage, dann Re-Evaluation**."

---

### ❌ NO-GO — Evolution blockiert

**Bedingungen:**
- ❌ ≥ 3 Szenarien: FAIL
- ❌ Gate A oder B: FAIL (Invarianten verletzt)
- ❌ Kritische Failures:
  - Negative Balances
  - Idempotency-Violations > 0
  - Approval Races (>1 Final Decision)
  - System-Crash bei Service-Ausfall
  - Memory-Leak-Trend > 1.0 MB/min

**Empfehlung:**
> "Kritische Risiken identifiziert. **Evolution blockiert bis Fixes implementiert**. Phase 5–8 weiterhin gesperrt."

---

## 📝 Nächste Schritte für User

### 1. Tests ausführen (lokal mit Docker)

```bash
# Terminal 1: Backend starten
docker compose up -d backend

# Terminal 2: Tests ausführen
docker compose exec backend python backend/tests/run_live_credit_tests.py --full --report-json reports/live_test_report.json

# Report analysieren
cat reports/live_test_report.json | jq '.overall_status'
cat reports/live_test_report.json | jq '.recommendation'
```

---

### 2. Report befüllen

```bash
# Template kopieren
cp backend/tests/LIVE_TEST_REPORT_TEMPLATE.md reports/live_test_report_20241230.md

# Mit JSON-Daten befüllen
# (Manuell oder via jq)

# Git committen
git add reports/live_test_report_20241230.md
git commit -m "test: Live Test Report 2024-12-30"
```

---

### 3. Entscheidung treffen

Basierend auf `overall_status` im JSON-Report:

**GO:**
- Phase 5a starten: Postgres Event Store implementieren
- ADR erstellen: "Event Store Migration von File zu Postgres"
- Snapshot-Strategie planen (Phase 6a)

**CONDITIONAL:**
- 3–7 Tage weitertesten (gleiche Parameter)
- Performance-Optimierungen identifizieren
- Re-Evaluation mit neuem Report

**NO-GO:**
- Kritische Fixes implementieren (siehe Violations)
- Weitere Evolution blockiert
- Regression-Tests nach Fixes

---

## 🔍 Troubleshooting

### Problem: "Docker Compose not found"

```bash
# Docker installieren
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Oder Docker Desktop (Windows/Mac)
# https://www.docker.com/products/docker-desktop/
```

---

### Problem: "Backend startet nicht"

```bash
# Logs prüfen
docker compose logs backend

# Container neu bauen
docker compose build backend
docker compose up -d backend

# Ports prüfen
netstat -tuln | grep 8000
```

---

### Problem: "Event Journal Permission Denied"

```bash
# Verzeichnis erstellen
mkdir -p storage/events

# Permissions setzen
chmod 755 storage/events

# Im Container
docker compose exec backend mkdir -p /app/storage/events
docker compose exec backend chmod 755 /app/storage/events
```

---

### Problem: "Import Errors in Tests"

```bash
# Python Path prüfen
docker compose exec backend python -c "import sys; print(sys.path)"

# Module installieren (falls fehlend)
docker compose exec backend pip install loguru pydantic

# Container neu bauen
docker compose build backend
```

---

## 📚 Referenz-Dokumentation

### Erstellte Dateien

```
backend/tests/
├── DOCKER_SETUP_ANALYSIS.md              # Docker Setup Analyse
├── live_credit_system_playbook.md        # Test Playbook
├── run_live_credit_tests.py              # Test Harness (900+ Zeilen)
├── live_invariants.py                    # Invarianten-Checker (400+ Zeilen)
├── LIVE_TEST_REPORT_TEMPLATE.md          # Report Template
└── LIVE_TEST_DELIVERABLES.md             # Dieses Dokument
```

---

### Code-Statistik

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `run_live_credit_tests.py` | 900+ | Test Harness mit 6 Szenarien |
| `live_invariants.py` | 400+ | Invarianten-Checker (5 Hard Checks) |
| `DOCKER_SETUP_ANALYSIS.md` | ~350 | Docker Setup Dokumentation |
| `live_credit_system_playbook.md` | ~700 | Test Playbook & Ablaufplan |
| `LIVE_TEST_REPORT_TEMPLATE.md` | ~300 | Report Template |
| **TOTAL** | **~2,650 Zeilen** | **Komplette Live-Test-Suite** |

---

## ✅ Deliverables Checklist

- [x] **Schritt 0:** Docker Setup analysiert & dokumentiert
- [x] **Playbook:** Live Test Ablaufplan erstellt
- [x] **Test Harness:** 6 Szenarien vollständig implementiert
- [x] **Invarianten-Checker:** 5 Hard Gates implementiert
- [x] **Report Template:** Professionelles Template erstellt
- [x] **Go/No-Go Kriterien:** Klar definiert
- [x] **Troubleshooting:** Häufige Probleme dokumentiert
- [x] **CLI-Interface:** Vollständig mit argparse
- [x] **JSON-Report:** Automatische Report-Generierung

---

## 🎉 Zusammenfassung

**Was wurde erreicht:**

✅ **Vollständige Live-Test-Suite** für BRAiN Credit System Event Sourcing
✅ **Charter-strict** — Keine neuen Features, nur Stabilität & Auditierbarkeit
✅ **Repo-konkret** — Passt exakt zum bestehenden Docker & Code-Setup
✅ **Deterministisch** — Seeds, Replay, reproduzierbare Ergebnisse
✅ **Production-Ready** — Hard Gates, Invarianten, Go/No-Go Kriterien

**Was User tun muss:**

1. Docker starten: `docker compose up -d backend`
2. Tests ausführen: `docker compose exec backend python backend/tests/run_live_credit_tests.py --full`
3. Report analysieren: `cat reports/live_test_report.json | jq .`
4. Entscheidung treffen: GO / CONDITIONAL / NO-GO

**Empfohlene Baseline:**

Wenn alle Tests PASS:
- ✅ **GO** — Phase 5a (Postgres Event Store) freigeben
- ✅ System ist **production-ready** für file-based Event Sourcing
- ✅ Keine Blocker für weitere Evolution

---

**Status:** ✅ **DELIVERABLES COMPLETE**
**Nächster Schritt:** User führt Live-Tests aus und erstellt Report
**Sign-Off:** Claude (Lead Engineer & Reliability Owner) — 2024-12-30
