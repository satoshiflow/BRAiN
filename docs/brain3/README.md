# BRAIN 3.0 - Neural State Architecture

## Übersicht

BRAIN 3.0 ist die nächste Generation der BRAiN-Architektur. 
Das Konzept basiert auf der Idee, dass das **Gehirn nicht speichert, sondern verarbeitet**.

### Kernkonzepte

| Konzept | Beschreibung |
|---------|--------------|
| **Synapse** | Eine Verbindung zwischen Input und Output |
| **Parameter** | Die "Gewichte" die bestimmen wie Synapsen funktionieren |
| **State** | Der aktuelle Zustand des Systems |
| **Execution** | Der Forward-Pass durch das neuronale Netz |

### Unterschied zu BRAIN 2.0

| Aspekt | BRAIN 2.0 | BRAIN 3.0 |
|--------|-----------|-----------|
| Logik | In jedem Service fix codiert | In Datenbank-Tabellen |
| Konfiguration | ENV-Variablen | JSON-Parameter (Runtime änderbar) |
| Verknüpfungen | Import-Statements zur Compile-Zeit | SQL-Queries zur Laufzeit |
| Änderung | Code ändern → neu deployen | UPDATE auf Datenbank → sofort aktiv |

---

## Schnellstart

### 1. Datenbank-Tabellen erstellen

```bash
docker exec brain-postgres psql -U brain -d brain -f /app/app/neural/db/migrations/001_neural_core.sql
```

### 2. Neural Core nutzen

```python
from app.neural import get_neural_core, ExecutionRequest

# Mit Database Session
core = get_neural_core(db)

# Parameter holen
creativity = await core.get_parameter("creativity", default=0.7)
print(f"Creativity: {creativity}")

# Execution durchführen
result = await core.execute(ExecutionRequest(
    action="skill_execute",
    payload={"skill_key": "http_request"}
))
print(result)
```

---

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    API ENDPOINT                              │
│                  (nur Executor)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              BRAIN STATE MANAGER                           │
│         (NeuralCore - liest Parameter aus DB)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ Synapse 1│ │Synapse 2 │ │Synapse N │
    │(skill_   │ │(memory) │ │(plan-    │
    │ engine)  │ │          │ │ ning)    │
    └──────────┘ └──────────┘ └──────────┘
          │            │            │
          └────────────┼────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              POSTGRESQL                                     │
│         (Das eigentliche Gehirn)                            │
│    → neural_synapses, brain_states, brain_parameters        │
└─────────────────────────────────────────────────────────────┘
```

---

## Verzeichnis-Struktur

```
backend/app/neural/
├── __init__.py              # Exporte
├── core.py                  # NeuralCore Service
└── db/
    └── migrations/
        └── 001_neural_core.sql  # DB-Tabellen
```

---

## Verfügbare Parameter

| Parameter | Typ | Bereich | Beschreibung |
|-----------|-----|---------|---------------|
| creativity | float | 0.0 - 1.0 | Kreativitäts-Level |
| caution | float | 0.0 - 1.0 | Vorsicht-Level |
| speed | float | 0.0 - 1.0 | Geschwindigkeits-Faktor |
| learning_rate | float | 0.0 - 1.0 | Lern-Rate |
| execution_timeout | int | 1 - 300 | Timeout in Sekunden |
| max_retries | int | 0 - 10 | Maximale Wiederholungen |

---

## Verfügbare States

| State | Parameter | Beschreibung |
|-------|-----------|---------------|
| default | creativity: 0.7, caution: 0.5, speed: 0.8 | Standard-Modus |
| creative | creativity: 0.95, caution: 0.2, speed: 0.6 | Kreativ-Modus |
| fast | creativity: 0.4, caution: 0.7, speed: 0.95 | Schnell-Modus |
| safe | creativity: 0.3, caution: 0.95, speed: 0.5 | Sicherheits-Modus |

---

## Verfügbare Synapsen

| Synapse | Target | Capability | Beschreibung |
|---------|--------|------------|---------------|
| skill_execute | skill_engine | execute | Führt einen Skill aus |
| skill_list | skill_engine | list | Listet Skills auf |
| memory_store | memory | store | Speichert Memory |
| memory_recall | memory | recall | Erinnert Memory |
| planning_decompose | planning | decompose | Plant Task |
| policy_evaluate | policy | evaluate | Evaluiert Policy |

---

## API

### Execution

```python
# Request
ExecutionRequest(
    action="skill_execute",  # Die Aktion
    payload={"skill_key": "http_request"},  # Input-Daten
    context={}  # Optionaler Kontext
)

# Response
ExecutionResponse(
    success=True,
    result={"skill_executed": True},
    synapse_id="skill_execute",
    execution_time_ms=45.2,
    parameters_used={"creativity": 0.7}
)
```

### Parameter ändern

```python
await core.set_parameter("creativity", 0.9)
```

### State wechseln

```python
await core.set_state("creative", {"creativity": 0.95})
```

---

## Monitoring

### Statistiken abrufen

```sql
-- Synapsen-Statistiken
SELECT 
    synapse_id,
    COUNT(*) as executions,
    AVG(execution_time_ms) as avg_time_ms,
    SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) * 100 as success_rate
FROM synapse_executions
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY synapse_id;

-- Parameter-Nutzung
SELECT parameter_key, COUNT(*) as reads
FROM brain_parameters
GROUP BY parameter_key;
```

---

## Fehlerbehandlung

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| No synapse found | Keine Synapse für Action | Synapse in DB erstellen |
| Parameter not mutable | Parameter ist readonly | is_mutable prüfen |
| Execution timeout | Synapse dauert zu lange | execution_timeout erhöhen |
| SQL Error | DB-Verbindungsproblem | DB-Logs prüfen |

---

## Weiterentwicklung

1. **Learning Loop** - Automatische Parameter-Anpassung basierend auf Erfolg
2. **Mehr Synapsen** - Weitere Brain 2.0 Module wrappen
3. **Caching** - Redis für noch schnellere Zugriffe
4. **Monitoring** - Dashboard für Parameter und States

---

## Links

- [DATABASE.md](DATABASE.md) - Detaillierte DB-Dokumentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architektur-Details
- [MIGRATION.md](MIGRATION.md) - Migrations-Guide
