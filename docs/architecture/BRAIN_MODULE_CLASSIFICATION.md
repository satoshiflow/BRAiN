# BRAIN Module Classification

## Zweck

Dieses Dokument klassifiziert alle aktuell vorhandenen BRAiN-Module in klare Kategorien, um:

- Architektur-Drift zu reduzieren
- Legacy-Pfade zu identifizieren
- Zielmodule zu definieren
- Konsolidierungsentscheidungen vorzubereiten
- zukünftige Entwicklungsprioritäten festzulegen

Es dient als Arbeitsgrundlage für:

- Runtime-Konsolidierung
- Immune-System-Aufbau
- DNA/Genesis-Härtung
- Event-Infrastruktur-Vereinheitlichung
- OpenCode Dev-Layer Integration

---

# Klassifikationskategorien

Module werden in folgende Klassen eingeteilt:

### CORE
Stabil, produktionsnah, zentral für BRAiN.

Diese Module bilden das Fundament der Runtime.

### CONSOLIDATE
Wichtige Module, aber Architektur, API oder Struktur müssen vereinheitlicht werden.

### MIGRATE
Legacy-Pfade oder ältere Implementierungen, die in neue Zielpfade überführt werden sollen.

### FREEZE
Module bleiben vorerst unverändert bestehen, werden aber nicht weiterentwickelt.

### REPLACE
Module mit falscher Architektur oder redundanter Funktion, die durch neue ersetzt werden sollen.

### NEW
Noch nicht existierende, aber laut Zielarchitektur notwendige Module.

---

# Core Runtime Module

Diese Module sind stabil genug und bleiben Teil der Zielarchitektur.

| Modul | Pfad | Status | Bemerkung |
|-----|-----|-----|-----|
Agent Management | `backend/app/modules/agent_management` | CORE | Agent Lifecycle, Heartbeats, Registration |
Memory | `backend/app/modules/memory` | CORE | Working/Episodic/Semantic Memory |
Policy Engine | `backend/app/modules/policy` | CORE | Regelprüfung und Event Integration |
Task Queue | `backend/app/modules/task_queue` | CORE | Priorisierte Taskverarbeitung |
Audit Logging | `backend/app/modules/audit_logging` | CORE | Persistenter Audit Trail |
Monitoring | `backend/app/modules/monitoring` | CORE | Prometheus Metrics |
Telemetry | `backend/app/modules/telemetry` | CORE | AXE Telemetry |
Metrics Core | `backend/app/core/metrics.py` | CORE | globale Prometheus Integration |

Diese bilden das aktuelle **Runtime-Fundament von BRAiN**.

---

# Runtime Modules (Consolidate)

Diese Module sind wichtig, aber noch nicht vollständig vereinheitlicht.

| Modul | Pfad | Status | Bemerkung |
|-----|-----|-----|-----|
Supervisor | `backend/app/modules/supervisor` | CONSOLIDATE | Supervisor Status und Control |
Missions Templates | `backend/app/modules/missions` | CONSOLIDATE | Template-basierte Mission Instantiation |
Cluster System | `backend/app/modules/cluster_system` | CONSOLIDATE | Agent Cluster Management |
System Health | `backend/app/modules/system_health` | CONSOLIDATE | Aggregierte Health-Sicht |
Runtime Auditor | `backend/app/modules/runtime_auditor` | CONSOLIDATE | Anomaly Detection |
NeuroRail | `backend/app/modules/neurorail` | CONSOLIDATE | Lifecycle Enforcement / Reflex / Telemetry |
LLM Router | `backend/app/modules/llm_router` | CONSOLIDATE | Provider-Abstraktion |

Diese Module benötigen:

- API-Konsolidierung
- EventStream-Harmonisierung
- klarere Rollenabgrenzung

---

# Legacy Runtime (Migrate)

Diese Module existieren im älteren Pfad:

`backend/modules/*`

| Modul | Pfad | Status | Bemerkung |
|-----|-----|-----|-----|
Mission Runtime | `backend/modules/missions` | MIGRATE | Worker Runtime, Retry Logic |

### Ziel

Mission Runtime soll langfristig vollständig unter:

`backend/app/modules/missions`

konsolidiert werden.

---

# Immune / Recovery Layer

Teilweise implementierte Schutzmechanismen.

| Modul | Pfad | Status | Bemerkung |
|-----|-----|-----|-----|
Immune | `backend/app/modules/immune` | CONSOLIDATE | Event Klassifikation und Schutzaktionen |
Failure Recovery | `backend/app/modules/planning/failure_recovery` | CONSOLIDATE | Retry / Rollback / Detox |
NeuroRail Enforcement | `backend/app/modules/neurorail/enforcement` | CONSOLIDATE | Runtime Enforcement |

Diese Module bilden bereits einen Teil des zukünftigen Immune Systems, benötigen jedoch eine zentrale Koordination.

---

# DNA / Genesis Layer

Teilweise implementierte Evolutionsstruktur.

| Modul | Pfad | Status | Bemerkung |
|-----|-----|-----|-----|
DNA | `backend/app/modules/dna` | CONSOLIDATE | Snapshot + Mutation API |
Genesis | `backend/app/modules/genesis` | CONSOLIDATE | Blueprint + Trait System |
Traits | `backend/app/modules/genesis/traits` | CONSOLIDATE | Trait Mutation + Inheritance |
Blueprint Library | `backend/app/modules/genesis/blueprints` | CONSOLIDATE | Archetyp Registry |

### Wichtig

DNA-Service ist aktuell teilweise **in-memory orientiert** und muss langfristig vollständig persistiert werden.

---

# Governance Layer

| Modul | Pfad | Status | Bemerkung |
|-----|-----|-----|-----|
Governance | `backend/app/modules/governance` | CONSOLIDATE | HITL Approvals |
Governor | `backend/app/modules/governor` | CONSOLIDATE | Mode Decision |

### Verbesserungspotential

- persistenter Storage
- Governance Gate für DNA Mutationen
- Integration mit Immune System

---

# Event Infrastructure

| Modul | Pfad | Status | Bemerkung |
|-----|-----|-----|-----|
EventStream | `mission_control_core` Integration | CONSOLIDATE | Zielarchitektur |
Legacy EventBus | `backend/app/core/event_bus.py` | FREEZE | Stub / Guard geschützt |

### Ziel

EventStream wird **einziger offizieller Eventpfad**.

---

# Development / Evolution Layer

Derzeit noch nicht vollständig implementiert.

| Modul | Status | Bemerkung |
|-----|-----|-----|
OpenCode Dev Layer | NEW | internes Entwicklungs- und Reparatursystem |
Repair Workflows | NEW | Self-Healing Pipeline |
Patch Engine | NEW | strukturierte Code-Reparaturen |

---

# Neue Zielmodule

Diese Module existieren laut Analyse noch nicht oder nur fragmentiert.

| Modul | Zweck |
|-----|-----|
Immune Orchestrator | zentrale Koordination aller Health-/Threat-Signale |
Genetic Integrity Service | Hashing / Signatur / Integrität für DNA |
Genetic Quarantine Manager | isolierte Laufzeit für mutierte Agenten |
Unified Recovery Policy Engine | zentralisierte Recovery Playbooks |
OpenCode Dev Layer | internes Dev-/Repair-System |
Horizon Agent Framework | duplizierbare Beobachtungsagenten |

---

# Horizon Framework (Duplizierbar)

Horizon ist kein einzelner Agent, sondern eine **Agentenfamilie**.

### Beispiele zukünftiger Horizon Instanzen

- Horizon-KI
- Horizon-Robotik
- Horizon-Open-Source
- Horizon-Wirtschaft
- Horizon-Branchen
- Horizon-Politik
- Horizon-Wissenschaft
- Horizon-Sicherheit
- Horizon-Nutzerbedarf

Alle Horizon-Instanzen liefern strukturierte Impulse für:

- AXE
- GOTT
- BRAiN Supervisor
- Governance

---

# Konsolidierungsstrategie

## Phase 1
Architekturordnung:

- Zielmodule definieren
- Legacy isolieren
- EventStream vereinheitlichen

## Phase 2
Immune-System Aufbau:

- Immune Orchestrator
- Unified Recovery Engine

## Phase 3
DNA-Härtung:

- Genetic Integrity Service
- Mutation Governance
- Quarantine Lane

## Phase 4
Dev-Layer Integration:

- OpenCode Dev Layer
- Repair Pipelines

## Phase 5
Evolution:

- Horizon Framework
- modulare Erweiterungen

---

# Langfristiges Ziel

BRAiN entwickelt sich von:

- modularer Agentenplattform

zu einem:

- stabilen
- gesundheitsorientierten
- genetisch konsistenten
- auditierbaren
- evolutionsfähigen System.

Die hier definierte Klassifikation dient als Grundlage für alle weiteren Architekturentscheidungen.
