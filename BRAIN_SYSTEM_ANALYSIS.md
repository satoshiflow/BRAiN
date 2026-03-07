# BRAIN_SYSTEM_ANALYSIS

Datum: 2026-03-06
Scope: Gesamt-Repository (Schwerpunkt `backend/` Runtime + relevante Integrations-/Ops-Skripte)
Methodik: statische Codeanalyse (Module, Services, Router, Worker, Modelle, Guards), keine Implementierungsaenderung

## 1. Architekturuebersicht

BRAiN ist aktuell als modulare FastAPI-Plattform mit starkem Module-Ansatz aufgebaut (`backend/app/modules/*`), plus Legacy-Runtime-Teile in `backend/modules/*`.

Wesentliche Architekturbeobachtungen:
- **Zentraler Runtime-Entry**: `backend/main.py` mit Lifespan-Orchestrierung, Router-Integration, Worker-Start/Stop, EventStream-Initialisierung.
- **Dualitaet Alt/Neu**: Einige Kernpfade existieren doppelt oder ueberlappend (z. B. Mission Runtime in `backend/modules/missions/*` vs. Mission Templates in `backend/app/modules/missions/*`).
- **Event-Infrastruktur im Umbau**: `EventStream` (mission_control_core) ist Zielbild; legacy `app/core/event_bus.py` ist nur Stub und wird per Guard blockiert.
- **Sicherheits-/Qualitaetsgates vorhanden**: Policy/Rate-Limits/Auth plus Repo-Guards (`scripts/check_no_legacy_event_bus.py`, `scripts/critic_gate.py`, etc.).

## 2. Vorhandene Module (Systemarchitektur Inventar)

Reifegrad-Legende:
- `mock`: stubhaft / demoartig / starke TODO-Abhaengigkeit
- `teilweise implementiert`: produktiv nutzbare Teile, aber Luecken/Legacy/Umbaupfad
- `produktionsnah`: persistente Daten, klare APIs, operational plausibel

| Modul | Pfad | Zweck | Reifegrad |
|---|---|---|---|
| Supervisor | `backend/app/modules/supervisor/*` | Supervisor-Status/Health API | teilweise implementiert (Statuslogik stubhaft) |
| Mission Engine (Runtime) | `backend/modules/missions/*` | Queue + Worker-Orchestrierung + Retry | teilweise implementiert |
| Mission Templates | `backend/app/modules/missions/*` | Template CRUD/Instantiation | teilweise implementiert |
| Agent Registry/Lifecycle | `backend/app/modules/agent_management/*` | Agent Registrierung, Heartbeat, Offline-Erkennung, Termination | produktionsnah |
| Event Stream (Zielpfad) | `backend/main.py`, `mission_control_core` Integration | Event-Publish fuer Runtime-Module | teilweise implementiert |
| Legacy Event Bus | `backend/app/core/event_bus.py` | Stub pub/sub ohne Persistenz | mock |
| Memory Layer | `backend/app/modules/memory/*` | Persistente Working/Episodic/Semantic Memory via PostgreSQL | produktionsnah |
| Governance HITL | `backend/app/modules/governance/*` | Approval-Workflows, Audit, Token-basierte Freigaben | teilweise implementiert (file-based storage) |
| Governor | `backend/app/modules/governor/*` | Mode-Decision + Shadow-Manifest | teilweise implementiert (Phase-Stub, dry-run Fokus) |
| Policy Engine | `backend/app/modules/policy/*` | Rule Evaluation + Cache + EventStream Hooks | produktionsnah |
| Resource Management (Cluster) | `backend/app/modules/cluster_system/*` | Cluster/Agent-Hierarchie, Blueprints, Scaling | teilweise implementiert |
| Task Queue | `backend/app/modules/task_queue/*` | Priorisierte Task-Lifecycle, Retry/Dependencies | produktionsnah |
| Worker Layer | `backend/app/workers/*` | BaseWorker, Autoscaler, Metrics Collector | teilweise implementiert |
| LLM Integration | `backend/app/modules/llm_router/*`, `services/mock-llm/*` | Provider-Abstraktion + OpenAI-kompatibler Mock | teilweise implementiert |
| Metrics/Monitoring | `backend/app/core/metrics.py`, `backend/app/modules/monitoring/*` | Prometheus-Metriken + Operational Monitoring | produktionsnah |
| Runtime Auditor | `backend/app/modules/runtime_auditor/*` | Anomaly Detection, Edge-of-Chaos, Immune-Integration | teilweise implementiert |
| Immune | `backend/app/modules/immune/*` | Event-Klassifikation + Self-Protection Actions | teilweise implementiert |
| System Health | `backend/app/modules/system_health/*` | Aggregierte Health-Sicht ueber Subsysteme | teilweise implementiert |
| Audit Logging | `backend/app/modules/audit_logging/*` | DB-basierter Audit Trail + Event-Publish | produktionsnah |
| Telemetry (AXE) | `backend/app/modules/telemetry/*` | Event-Telemetrie + Anonymisierung + Stats | produktionsnah |
| NeuroRail (Lifecycle/Enforcement/Audit/Telemetry) | `backend/app/modules/neurorail/*` | State Machines, Budget Enforcements, Reflex-Layer, Audit | teilweise implementiert bis produktionsnah (je Teilmodul) |

## 3. Vorhandene Health-/Diagnostics-Mechanismen

### 3.1 Healthchecks
- `backend/main.py`: global `/api/health` plus Lifespan-Initialisierung und Redis/EventStream Startchecks.
- `backend/app/modules/health_monitor/*`: registrierte Services, Statusklassifikation (healthy/degraded/unhealthy), History in DB (`health_checks`, `health_check_history`).
- `backend/app/modules/system_health/*`: aggregierte Gesamtgesundheit inkl. Bottleneck-/Recommendation-Logik.

### 3.2 Heartbeat
- `backend/app/modules/agent_management/service.py`: Heartbeat-Verarbeitung pro Agent, Statusuebergaenge (registered->active, offline->active), Missed-Heartbeat-Offline-Markierung.
- `backend/app/workers/base_worker.py`: Redis-Heartbeat pro Worker (`brain:worker:<id>:heartbeat` mit TTL).

### 3.3 Diagnostics / Runtime Audit
- `backend/app/modules/runtime_auditor/service.py`: kontinuierliche Metrik-Samples, Anomaly Detection, Edge-of-Chaos-Metriken.
- `backend/app/modules/system_health/service.py`: konsolidierte Diagnosesicht (immune/threats/mission/agent/audit).

### 3.4 Retry / Recovery / Watchdog-Naehe
- `backend/app/modules/planning/failure_recovery.py`: Recovery-Strategien (`retry`, `rollback`, `skip`, `alternative`, `detox`, `escalate`) mit Backoff/Cooldown.
- `backend/app/modules/task_queue/service.py`: Task-Retry-Workflow mit Zeitsteuerung.
- `backend/modules/missions/worker.py`: mission-level Retry per Re-enqueue.
- `backend/app/modules/neurorail/enforcement/retry.py`: Budget-konformes Retry mit Exponential Backoff + Retriability-Klassifikation.
- **Watchdog im engeren Sinne**: kein dedizierter zentraler Runtime-Watchdog im Backend-Core gefunden; verteilte Schutz-/Recovery-Mechanik existiert in Immune/RuntimeAuditor/NeuroRail.

### 3.5 Error Handling
- Breite Verwendung von fail-safe Event-Publish (`try/except`, non-blocking) in mehreren Services (Immune, DNA, Policy, Missions Worker, Audit etc.).
- Sanitized HTTP Errors in vielen Routern; heterogenes Niveau zwischen Modulen bleibt.

## 4. Logging / Ledger / Observability

### 4.1 Logging
- Zentrales JSON Logging: `backend/app/core/logging.py` (python-json-logger, stdout).
- Modul-Logs via `loguru`/`logging` gemischt.

### 4.2 Audit / Ledger / Event Sourcing
- Audit Logging Modul: `backend/app/modules/audit_logging/*`, DB-Tabelle `audit_events`.
- NeuroRail Audit: append-only Orientierung in `backend/app/modules/neurorail/audit/service.py` mit PostgreSQL + EventStream publish.
- Credits Event Sourcing Demo: `backend/app/modules/credits/integration_demo.py` + Credits Service Integration (teilweise demo-getrieben).

### 4.3 Metrics & Telemetry
- Prometheus-Metriken global: `backend/app/core/metrics.py`.
- Monitoring-Modul: `backend/app/modules/monitoring/*` (`/metrics`, `/metrics/summary`, `/metrics/health`).
- AXE Telemetry: `backend/app/modules/telemetry/*` mit Anonymisierung und DB-Queries (`axe_events`).
- NeuroRail Telemetry: `backend/app/modules/neurorail/telemetry/*` (Redis realtime snapshots + PostgreSQL snapshots).

### 4.4 Event Streams
- Zielpfad: EventStream aus `mission_control_core` in `backend/main.py` (required/degraded mode).
- Legacy EventBus: `backend/app/core/event_bus.py` ist Stub ohne Persistenz.
- Guard aktiv gegen Re-Introduction legacy Bus: `scripts/check_no_legacy_event_bus.py`.

### 4.5 Datenquellen und Speicherorte
- PostgreSQL: Agenten, Tasks, Health, Audit, Mission Templates, Telemetry, Cluster u. a.
- Redis: Queue/Heartbeat/Realtimesnapshots/Hot State.
- Dateibasiert: Governance Storage (`storage/governance/*.json*`) fuer Approval/Audit in diesem Modul.
- EventStream-Backend: Redis-basiert (via mission_control_core).

## 5. Agent Lifecycle Analyse

### 5.1 Definition
- Agent-Schemata: `backend/app/modules/agent_management/schemas.py` (`AgentRegister`, `AgentHeartbeat`, `AgentResponse`).
- Cluster-Agentenmodell: `backend/app/modules/cluster_system/models.py` (`ClusterAgent`, Rollen/Hierarchie).
- Genesis-Agentenkontext: `backend/app/modules/genesis/*` (Blueprint+Trait-basiert).

### 5.2 Registrierung
- `backend/app/modules/agent_management/router.py` -> `/api/agents/register`.
- `backend/app/modules/agent_management/service.py` persistiert Agenten in DB, re-registert bestehende IDs.

### 5.3 Start / Aktivierung
- Aktivierungsuebergang bei erstem Heartbeat (`REGISTERED -> ACTIVE`) in `AgentService.process_heartbeat`.
- Mission Worker lifecycle in `backend/modules/missions/worker.py` (`start_mission_worker`, `stop_mission_worker`).

### 5.4 Stop / Termination
- API-gestuetzte Graceful Termination: `/api/agents/{agent_id}/terminate`.
- Hard Delete vorhanden (`DELETE /api/agents/{agent_id}`) mit Admin-Rolle.

### 5.5 Fehler-/Degradation-Meldung
- Agentstatus kann auf `DEGRADED`/`OFFLINE` gesetzt werden (Heartbeat- und Offline-Check-Logik).
- Event-Emission fuer `agent.degraded`, `agent.offline`, `agent.recovered`.

## 6. Dev / Self-Repair Integration

### 6.1 Vorhandene Mechanismen
- **Systemische Self-Repair (Runtime)**:
  - Immune Self-Protection (backpressure/circuit-breaker/GC/restart hooks): `backend/app/modules/immune/core/service.py`.
  - Planning Failure Recovery Strategien: `backend/app/modules/planning/failure_recovery.py`.
  - NeuroRail Reflex + Enforcement: `backend/app/modules/neurorail/reflex/*`, `enforcement/*`.
- **Repo-Operationen mit Governance-Schutz (ARO)**:
  - `backend/app/modules/aro/*` Lifecycle propose->validate->authorize->execute.
  - Aktuelle Execute-Phase noch teilweise placeholder/TODO fuer echte Git-Exekution.

### 6.2 Nicht (oder nur rudimentaer) vorhanden
- Kein belastbarer Runtime-Mechanismus fuer **automatische Codeaenderungen im Produktivlauf** gefunden.
- Keine belastbare, produktionsreife "self-modifying code" Pipeline mit signierter Patch-Autorisierung durchgaengig implementiert.

## 7. Lueckenanalyse fuer ein zukuenftiges Immune System

Bereits vorhanden (Bausteine):
- Event-Klassifikation (ImmuneEventType, Severity).
- Runtime Signals (Health Monitor, Runtime Auditor, Agent Heartbeats).
- Recovery-Primitiven (retry/backoff/circuit-breaker/detox/rollback).
- Observability-Grundlage (Prometheus + Telemetry + Audit).

Hauptluecken:
- Fehlende zentrale "immune orchestrator"-Schicht mit einheitlicher Priorisierung und policy-gesteuerter Gegenmassnahmenkette.
- Uneinheitliche Event-Infrastruktur (EventStream Zielbild, aber Restartefakte/Importpfad-Drift vorhanden).
- Einige Dienste sind singleton/in-memory orientiert statt voll persistenter, verteilbarer Runtime-Patterns.
- Kein einheitlicher Health-Score-Standard ueber alle Module (mehrere Teilmetriken, aber begrenzte Harmonisierung).
- Teilweise Legacy-Pfad-Abhaengigkeiten (z. B. Missions Runtime unter `backend/modules`).

---

## Agent DNA and Genetic Integrity

### 1) Vorhandene DNA-/Blueprint-Strukturen

**DNA Kernmodul**
- `backend/app/modules/dna/router.py`: API fuer Snapshot, Mutation, History.
- `backend/app/modules/dna/schemas.py`: `AgentDNASnapshot`, `DNAMetadata`, `MutateDNARequest`.
- `backend/app/modules/dna/core/service.py`: in-memory DNA-Store pro Agent, Versionierung, Event-Emission (`dna.snapshot_created`, `dna.mutation_applied`, `dna.karma_updated`).
- `backend/app/modules/dna/core/store.py`: ORM fuer `agent_dna_snapshots` vorhanden, aber aktuell nicht an Service gebunden.

**Genetische Ableitung / Archetypen**
- `backend/app/modules/genesis/blueprints/schemas.py`: `AgentBlueprint`, Capabilities, Trait-Profiles, Versionsfeld.
- `backend/app/modules/genesis/blueprints/library.py`: Blueprint-Registry (builtin + custom in-memory).
- `backend/app/modules/genesis/core/service.py`: Spawn/Evolve/Reproduce auf DNA+Traits.
- `backend/app/modules/genesis/traits/*`: TraitDefinitionen, Mutation, Inheritance, Crossover.

**Verwandte Template-/Blueprint-Systeme (nicht DNA-kernig, aber genetisch relevant)**
- Cluster Blueprints: `backend/app/modules/cluster_system/*` (inkl. Blueprint Version + Validator).
- Template Registry: `backend/app/modules/template_registry/*` (Template discovery/rendering).

Reifegrad DNA/Genesis:
- DNA Core: `teilweise implementiert` (API + Logik da, Persistenzpfad nicht final integriert).
- Genesis Blueprints/Traits: `teilweise implementiert` mit fortgeschrittener Modellierung.

### 2) Vererbungslogik

Vorhanden:
- Parent-Referenz auf DNA-Snapshot-Ebene: `DNAMetadata.parent_snapshot_id`.
- Reproduktion Parent1/Parent2 -> Child in `GenesisService.reproduce_agents`.
- Trait-Inheritance und Crossover in `TraitService.inherit_traits` / `crossover_traits`.
- Dokumentversionierung mit Parent-Referenz in AXE-Knowledge (`parent_id`, `version`) als verwandtes Muster.

Teilweise/fehlend:
- Keine durchgaengige Vererbung von Rollen/Policies fuer Agenten als hartes, globales DNA-Regelwerk.
- Blueprint-Versionen existieren, aber kein universeller Vererbungs-/Migrationsmechanismus fuer laufende Agentenflotten.

### 3) Mutation / Versionierung

Vorhanden:
- DNA-Versionierung per Snapshot-Liste (`version` inkrementell).
- Mutationen ueber `MutateDNARequest` und Trait-Deltas.
- Cluster Blueprint und andere Module mit Versionsfeldern.
- Mehrere Module mit History-/Rollback-Mustern (Planning, Webgenesis, ARO Lifecycle, NeuroRail State History).

Teilweise/fehlend:
- Keine zentrale "mutation registry" fuer DNA mit diff-basiertem globalem Auditstandard.
- DNA Rollback auf Snapshot-Ebene nicht als eigener Endpunkt/Workflow sichtbar.

### 4) Schutz- und Reparaturlogik fuer DNA

Vorhanden:
- Foundation Layer validiert Agent-Creation und Mutation gegen Ethikregeln (`genesis/foundation/service.py`).
- Ethics-critical Traits und Block-Regeln (z. B. safety/harm/risk bounds).
- Integration zur Immune-Ereignisprotokollierung bei Verstossen.

Teilweise/fehlend:
- Keine explizite DNA-Quarantaene fuer experimentelle Agenten als first-class Workflow.
- Keine sichtbare DNA-Hash/Signature-Pipeline fuer kryptografische Integritaetspruefung.
- Keine explizite "Ligase"-artige automatische DNA-Reparaturpipeline mit Version-Heal/Auto-Revert.
- Governance-Freigaben fuer DNA-Mutationen sind nicht als harter globaler Gate-Standard durchgaengig erkennbar.

### 5) Risiken bei DNA-Aenderungen

- In-memory DNAService kann bei Prozess-Neustart Historie verlieren, wenn nicht persistenter Pfad genutzt wird.
- Genetische Aenderungen in Blueprint-/Trait-Grundlagen koennen mehrere Agententypen gleichzeitig beeinflussen.
- Uneinheitliche Event-/Importpfade in angrenzenden Modulen erhoehen Drift-Risiko fuer genetische Workflows.
- Fehlende kryptografische Integritaet macht unautorisierte oder inkonsistente DNA-Aenderungen schwerer erkennbar.

### 6) Empfehlung fuer Genetic Immunity in BRAiN

1. **DNA Persistence first**
- DNAService auf echte DB-Backed Snapshot-Pipeline umstellen (statt rein in-memory Default).

2. **Genetic Audit Chain**
- Jede Mutation als append-only Event mit Snapshot-ID, Parent-ID, diff, actor, reason, policy decision.

3. **Mutation Governance Gate**
- Pflicht-Freigabe fuer high-risk trait/policy mutations (HITL/Governance).

4. **Genetic Quarantine Lane**
- Experimentelle Agentvarianten in isolierter Lane mit begrenzten Permissions/Ressourcen.

5. **Integrity Controls**
- Snapshot Hashing + optional Signatur, plus periodische Integritaetspruefung.

6. **Automated Genetic Recovery**
- Definierte Rollback-/heal-Strategien bei Anomalie oder Ethikverletzung (automatisch + auditierbar).

---

## Klare Gesamtempfehlung

### Welche Teile eines Immune Systems existieren bereits
- Immune Event-Kern + Self-Protection Aktionen.
- Health Monitor + System Health Aggregation.
- Runtime Auditor (Anomaly Detection / Edge-of-Chaos).
- NeuroRail Enforcement/Reflex (retry, timeout, circuit breaker, lifecycle FSM).
- Observability-Fundament (Prometheus, Telemetry, Audit).

### Welche Module erweitert werden sollten
- `immune` (von Eventsammler zu zentralem Orchestrator/Policy-Engine fuer Gegenmassnahmen).
- `system_health` (einheitliches Scoring und konsistente Signalnormalisierung).
- `runtime_auditor` + `neurorail` (engere Kopplung fuer konkrete auto-recovery policies).
- `dna` + `genesis` (persistente Genetic Immunity, Governance-Gates, Integrity).

### Welche Module neu erstellt werden sollten
- **Immune Orchestrator** (zentrales Decisioning ueber alle Health-/Threat-/Runtime-Signale).
- **Genetic Integrity Service** (Hash/Signatur/Verification fuer DNA-Snapshots).
- **Genetic Quarantine Manager** (isolierte Ausfuehrungs-Lane fuer mutierte Agenten).
- **Unified Recovery Policy Engine** (module-uebergreifende Recovery Playbooks mit Priorisierung).
