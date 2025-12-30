# 🧪 BRAiN Credit System — Live Test Playbook

**Scope:** Event Sourcing Foundation (Phasen 7–10) — Stabilität & Governance
**Testtyp:** Live System Validation (File-based, Single-Instance)
**Branch:** `claude/event-sourcing-foundation-GmJza`
**Verantwortlich:** Lead Engineer & Reliability Owner

---

## 📋 Inhaltsverzeichnis

1. [Voraussetzungen](#voraussetzungen)
2. [Testumgebung Setup](#testumgebung-setup)
3. [Testparameter](#testparameter)
4. [Testszenarien](#testszenarien)
5. [Hard Gates](#hard-gates)
6. [Ausführung](#ausführung)
7. [Erwartete Ergebnisse](#erwartete-ergebnisse)
8. [Failure Symptome](#failure-symptome)
9. [Cleanup & Wiederholung](#cleanup--wiederholung)

---

## 1️⃣ Voraussetzungen

### Infrastruktur

| Komponente | Version | Status | Erforderlich? |
|------------|---------|--------|---------------|
| Docker | ≥ 20.10 | ✅ Installiert | ✅ JA |
| Docker Compose | ≥ 2.0 | ✅ Installiert | ✅ JA |
| Python | ≥ 3.11 | ✅ Container | ✅ JA (im Backend) |
| PostgreSQL | 16 | ⚠️ Dormant | ❌ NEIN |
| Redis | 7 | ⚠️ Dormant | ❌ NEIN |

**Wichtig:** Postgres und Redis sind im Compose definiert, werden aber **logisch nicht genutzt**.

### Repository Status

```bash
# Branch checken
git branch --show-current
# → claude/event-sourcing-foundation-GmJza

# Letzter Commit
git log -1 --oneline
# → 3e25513 feat: Event Sourcing Next Steps - Integration & Extensions
```

### Verzeichnisstruktur

```bash
backend/
├── app/modules/credits/
│   ├── event_sourcing/          # Core Event Sourcing
│   │   ├── events.py
│   │   ├── event_journal.py     # File-based JSONL
│   │   ├── event_bus.py
│   │   ├── projections.py       # In-Memory
│   │   └── replay.py
│   ├── integration_demo.py      # CreditSystemDemo
│   ├── service.py               # Service Layer
│   ├── router.py                # REST API
│   ├── analytics.py             # Advanced Analytics
│   ├── mission_integration.py   # Mission Hooks
│   └── resource_pools.py        # Shared Pools
└── tests/
    ├── run_live_credit_tests.py     # ← Test Harness (zu erstellen)
    ├── live_invariants.py           # ← Invarianten-Checker (zu erstellen)
    └── live_credit_system_playbook.md  # ← Dieses Dokument
```

---

## 2️⃣ Testumgebung Setup

### Schritt 1: Services starten

```bash
# Ins Projekt-Root wechseln
cd /home/user/BRAiN

# NUR Backend starten (ausreichend!)
docker compose up -d backend

# Verifizieren
docker compose ps
# → backend: Up (8000->8000)
```

**Warum nur Backend?**
- Event Sourcing ist **file-based** (JSONL)
- Projections sind **In-Memory**
- Keine DB-Dependencies

### Schritt 2: Healthcheck

```bash
# API erreichbar?
curl http://localhost:8000/api/health
# → {"status": "healthy"}

# Credits Module erreichbar?
curl http://localhost:8000/api/credits/health
# → {"status": "healthy", "event_sourcing": true}
```

### Schritt 3: Event Journal initialisieren

```bash
# Automatisch beim ersten Event angelegt
# Pfad: storage/events/credits.jsonl

# Manuell anlegen (optional)
docker compose exec backend mkdir -p /app/storage/events
```

### Schritt 4: Test-Abhängigkeiten (im Container)

```bash
# Im Backend-Container
docker compose exec backend pip list | grep -E "pytest|httpx|loguru"
# → Sollte bereits installiert sein
```

---

## 3️⃣ Testparameter

### Konfigurierbare Parameter

| Parameter | Wert (Default) | Beschreibung |
|-----------|----------------|--------------|
| `CONCURRENCY` | 50, 100, 300 | Parallele Anfragen |
| `TEST_DURATION` | 30 Minuten | Dauerlauf-Dauer |
| `RETRY_INJECTION` | True | Duplicate Requests |
| `SEED` | 42 | Deterministischer Seed |
| `KARMA_ENABLED` | False | LLM-Verfügbarkeit simulieren |
| `ML_ANOMALY_INJECTION` | True | Anomalie-Injection |

### Umgebungsvariablen (optional)

```bash
# Überschreiben via ENV
export LIVE_TEST_CONCURRENCY=100
export LIVE_TEST_DURATION=1800  # 30 Minuten in Sekunden
export LIVE_TEST_SEED=42
```

---

## 4️⃣ Testszenarien

### Szenario 1: Credit Storm / Reuse Cascade

**Ziel:** Prüfen, ob massive parallele Credit-Konsumierung Balances korrekt hält

**Setup:**
- 10 Agents mit je 1000 Credits
- 50 parallele Threads
- Jeder Thread: 20 Consume-Operationen (zufällige Beträge)

**Erwartung:**
- ✅ Alle Balances >= 0
- ✅ Keine Idempotency-Violations
- ✅ `balance == sum(event_deltas)`

**Failure-Symptome:**
- ❌ Negative Balances
- ❌ NaN / Inf in Balances
- ❌ Drift zwischen Events und Projections

---

### Szenario 2: Synergy Anti-Gaming Loop

**Ziel:** Prüfen, ob Synergie-Rewards begrenzt sind (Anti-Gaming)

**Setup:**
- 5 Agents in Team "Alpha"
- 100 Synergie-Events (simuliert)
- Reward-Deckel: 500 Credits

**Erwartung:**
- ✅ Kein Agent > 500 Credits aus Synergie
- ✅ Audit-Log zeigt "reward_capped" Events

**Failure-Symptome:**
- ❌ Unbegrenzte Rewards
- ❌ Missing Audit Events

---

### Szenario 3: Approval Race / Concurrency

**Ziel:** Prüfen, ob parallele Approval-Requests serialisiert werden (OCC)

**Setup:**
- 1 Agent wartet auf Approval für 500 Credits
- 10 parallele Approve/Deny Requests

**Erwartung:**
- ✅ Nur 1 Approval wirksam
- ✅ Restliche Requests: "already_decided" Error
- ✅ Audit-Log vollständig

**Failure-Symptome:**
- ❌ Mehrfache Approvals
- ❌ Inkonsistenter Approval-State
- ❌ Fehlende Audit-Einträge

---

### Szenario 4: KARMA Blackout

**Ziel:** Prüfen, ob System ohne KARMA-LLM stabil bleibt

**Setup:**
- KARMA-Service simuliert "unavailable"
- 50 Credit-Operationen
- Fallback-Modus aktiv

**Erwartung:**
- ✅ System läuft weiter (degraded mode)
- ✅ Keine Crashes
- ✅ Fallback-Logik greift (z. B. Default CI = 0.5)

**Failure-Symptome:**
- ❌ System-Crash bei KARMA-Ausfall
- ❌ Keine Fallback-Logik

---

### Szenario 5: ML Chaos Injection

**Ziel:** Prüfen, ob ML-Anomalie-Erkennung nicht zu Overreaction führt

**Setup:**
- Injiziere absichtlich anomale Transaktionen (z. B. 10× Durchschnitt)
- Edge-of-Chaos Metriken tracken

**Erwartung:**
- ✅ Anomalien werden **markiert**, nicht blockiert
- ✅ CI-Score bleibt im Safe-Range (0.3–0.7)
- ✅ Keine Throttle-Spirale

**Failure-Symptome:**
- ❌ System blockiert bei jeder Anomalie
- ❌ CI-Score kippt in Extreme (< 0.1 oder > 0.9)

---

### Szenario 6: Crash / Replay

**Ziel:** Prüfen, ob Crash-Recovery via Replay deterministisch ist

**Setup:**
- 100 Events schreiben
- State in Projections merken (Snapshot)
- Projections löschen (simulierter Crash)
- Replay ausführen

**Erwartung:**
- ✅ Nach Replay: identischer State
- ✅ Alle Invarianten erfüllt
- ✅ Keine Idempotency-Violations beim Replay

**Failure-Symptome:**
- ❌ State-Drift nach Replay
- ❌ Invarianten verletzt

---

## 5️⃣ Hard Gates

### Gate A — Event Integrity

**Prüfung:**
```python
# Idempotency Key wirksam?
assert len(duplicate_events) == 0

# Schema-Version gesetzt?
for event in events:
    assert event.schema_version > 0

# Correlation/Causation IDs korrekt?
for event in events:
    assert event.correlation_id is not None
    if event.causation_id:
        assert causation_event_exists(event.causation_id)
```

**Go/No-Go:**
- ✅ GO: Alle Events valide, keine Duplikate
- ❌ NO-GO: Idempotency-Violations > 0

---

### Gate B — Projection Integrity

**Prüfung:**
```python
# Balance == Sum(Event-Deltas)?
for agent_id, balance in balances.items():
    deltas = sum_deltas_for_agent(agent_id)
    assert abs(balance - deltas) < 0.01  # Floating-Point-Toleranz

# Keine NaN / Inf?
for balance in balances.values():
    assert not math.isnan(balance)
    assert not math.isinf(balance)

# Kein Drift nach Replay?
original_state = snapshot_projections()
replay_all()
replayed_state = snapshot_projections()
assert original_state == replayed_state
```

**Go/No-Go:**
- ✅ GO: Balance-Invarianten erfüllt, Replay deterministisch
- ❌ NO-GO: Drift > 0

---

### Gate C — Human Gate Safety

**Prüfung:**
```python
# Approval serialisiert (OCC)?
approvals = get_approval_events()
assert len(approvals) <= 1  # Nur 1 Final Decision

# Audit-Log vollständig?
for approval in approvals:
    assert audit_log_contains(approval.event_id)
```

**Go/No-Go:**
- ✅ GO: OCC wirksam, Audit vollständig
- ❌ NO-GO: Race Conditions in Approvals

---

### Gate D — Failure Safety

**Prüfung:**
```python
# KARMA-Ausfall ohne Crash?
with simulate_karma_down():
    result = consume_credits(agent_id, 50)
    assert result.success  # Fallback greift

# ML-Anomalie markiert, nicht blockiert?
inject_anomaly(agent_id, amount=10000)
result = consume_credits(agent_id, 10000)
assert result.success
assert "anomaly_detected" in result.metadata
```

**Go/No-Go:**
- ✅ GO: Graceful Degradation funktioniert
- ❌ NO-GO: Crashes bei Service-Ausfall

---

### Gate E — Load Reality

**Prüfung:**
```python
# ≥ 30 Minuten Dauerlauf?
runtime = measure_test_duration()
assert runtime >= 1800  # 30 Minuten

# P95 Latenz < Grenzwert?
latencies = collect_latencies()
p95 = percentile(latencies, 95)
assert p95 < 500  # ms

# Memory-Leak-Trend?
memory_samples = collect_memory_usage()
trend = linear_regression_slope(memory_samples)
assert trend < 0.1  # MB/Minute
```

**Go/No-Go:**
- ✅ GO: System stabil über 30 Min, Latenz akzeptabel
- ❌ NO-GO: Memory-Leak oder Performance-Degradation

---

## 6️⃣ Ausführung

### Manueller Start

```bash
# Im Projekt-Root
cd /home/user/BRAiN

# Test-Harness ausführen
docker compose exec backend python backend/tests/run_live_credit_tests.py

# Oder direkt mit pytest
docker compose exec backend pytest backend/tests/run_live_credit_tests.py -v
```

### Mit Parametern

```bash
# Concurrency überschreiben
docker compose exec backend python backend/tests/run_live_credit_tests.py --concurrency 300

# Seed setzen
docker compose exec backend python backend/tests/run_live_credit_tests.py --seed 1337

# Alle Szenarien einzeln
docker compose exec backend python backend/tests/run_live_credit_tests.py --scenario credit_storm
docker compose exec backend python backend/tests/run_live_credit_tests.py --scenario approval_race
```

### Vollständiger Durchlauf

```bash
# Alle 6 Szenarien + 5 Gates
docker compose exec backend python backend/tests/run_live_credit_tests.py --full

# Mit JSON-Report
docker compose exec backend python backend/tests/run_live_credit_tests.py --full --report-json reports/live_test_report.json
```

---

## 7️⃣ Erwartete Ergebnisse

### Szenario-Matrix (Target)

| Szenario | Status | Throughput | P95 Latency | Invarianten |
|----------|--------|------------|-------------|-------------|
| Credit Storm | ✅ PASS | > 100 req/s | < 300 ms | ✅ OK |
| Synergy Anti-Gaming | ✅ PASS | — | — | ✅ OK |
| Approval Race | ✅ PASS | — | < 100 ms | ✅ OK |
| KARMA Blackout | ✅ PASS | — | — | ✅ OK |
| ML Chaos | ✅ PASS | — | — | ✅ OK |
| Crash/Replay | ✅ PASS | — | — | ✅ OK |

### Gate-Matrix (Target)

| Gate | Kriterium | Target | Actual |
|------|-----------|--------|--------|
| A — Event Integrity | Idempotency Violations | 0 | — |
| B — Projection Integrity | Balance Drift | 0.0 | — |
| C — Human Gate Safety | Approval Races | 0 | — |
| D — Failure Safety | Crashes | 0 | — |
| E — Load Reality | Runtime | ≥ 30 Min | — |

---

## 8️⃣ Failure Symptome

### Kritische Failures (NO-GO)

| Symptom | Gate | Root Cause | Fix Required |
|---------|------|------------|--------------|
| Negative Balance | B | Race Condition in consume() | ✅ Kritisch |
| Idempotency-Violations > 0 | A | Duplicate-Key-Check broken | ✅ Kritisch |
| Approval Race (>1 Final) | C | OCC not implemented | ✅ Kritisch |
| Crash bei KARMA-Ausfall | D | Missing Fallback | ✅ Kritisch |
| Memory Leak (Trend > 0.5 MB/min) | E | Projection Memory not GC'ed | ✅ Kritisch |

### Warnungen (CONDITIONAL)

| Symptom | Gate | Impact | Action |
|---------|------|--------|--------|
| P95 > 500 ms | E | Performance | ⚠️ Optimieren |
| Anomaly Overreaction | D | UX | ⚠️ Threshold tunen |
| Missing Audit Entries | C | Compliance | ⚠️ Fix Logging |

---

## 9️⃣ Cleanup & Wiederholung

### Event Journal löschen

```bash
# Kompletter Reset
docker compose exec backend rm -f /app/storage/events/credits.jsonl

# Container neu starten
docker compose restart backend
```

### Projections neu aufbauen

```python
# Im Test-Harness
await replay_engine.replay_all()
```

### Report-Archivierung

```bash
# Timestamped Report
mv reports/live_test_report.json reports/live_test_report_$(date +%Y%m%d_%H%M%S).json

# Git committen
git add reports/live_test_report_*.json
git commit -m "test: Live Test Report $(date +%Y-%m-%d)"
```

---

## 🎯 Erfolgs-Kriterien (Go/No-Go)

### ✅ GO — Nächste Phase (5a: Postgres Event Store)

**Bedingungen:**
- ✅ Alle 6 Szenarien: PASS
- ✅ Alle 5 Gates: PASS
- ✅ Keine kritischen Failures
- ✅ P95 < 500 ms
- ✅ 30-Min-Dauerlauf ohne Drift

**Empfehlung:**
> "System stabil. Event Sourcing Foundation production-ready. **Freigabe für Phase 5a (Postgres Event Store)**."

---

### ⚠️ CONDITIONAL — Weiter testen

**Bedingungen:**
- ⚠️ 1–2 Szenarien: FAIL (nicht-kritisch)
- ⚠️ Gates A/B: PASS, aber C/D/E: Warnungen
- ⚠️ P95 > 500 ms, aber < 1000 ms

**Empfehlung:**
> "System grundsätzlich stabil, aber Performance/Governance-Optimierung nötig. **Weiter testen für X Tage, dann Re-Evaluation**."

---

### ❌ NO-GO — Evolution blockiert

**Bedingungen:**
- ❌ ≥ 3 Szenarien: FAIL
- ❌ Gate A oder B: FAIL (Invarianten verletzt)
- ❌ Kritische Failures (Crash, Race, Negative Balance)

**Empfehlung:**
> "Kritische Risiken identifiziert. **Evolution blockiert bis Fixes implementiert**. Phase 5–8 weiterhin gesperrt."

---

## 📊 Report-Template

Siehe: `/home/user/BRAiN/backend/tests/LIVE_TEST_REPORT_TEMPLATE.md`

---

## 📝 Änderungshistorie

| Datum | Version | Autor | Änderung |
|-------|---------|-------|----------|
| 2024-12-30 | 1.0 | Claude | Initial Playbook (Event Sourcing MVP) |

---

**Status:** ✅ Bereit für Ausführung
**Nächster Schritt:** Test Harness implementieren (`run_live_credit_tests.py`)
