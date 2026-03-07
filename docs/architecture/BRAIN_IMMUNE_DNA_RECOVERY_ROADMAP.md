# BRAIN Immune DNA Recovery Roadmap

## Zweck

Dieses Dokument definiert die priorisierte Umsetzungsroadmap für den Ausbau von:

- Immune Orchestrator
- Genetic Integrity Service
- Genetic Quarantine Manager
- Unified Recovery Policy Engine
- OpenCode Dev/Repair Integration (nachgelagert)

Ziel ist eine belastbare, production-orientierte Reifung von BRAiN von verteilten Einzelmechanismen hin zu zentral orchestrierten Schutz-, Integritäts- und Recovery-Fähigkeiten.

---

## Ausgangslage (aus BRAIN_SYSTEM_ANALYSIS)

### Bereits vorhanden

- Immune Event-Klassifikation und Schutzreflexe (`backend/app/modules/immune`)
- Runtime Auditor + System Health Aggregation (`runtime_auditor`, `system_health`)
- Mehrere Recovery-Primitiven (retry/backoff/circuit-breaker/rollback/detox) in verschiedenen Modulen
- DNA/Genesis Grundstrukturen (Snapshots, Traits, Blueprint, Mutation) vorhanden
- EventStream-Zielpfad etabliert, Legacy EventBus per Guard blockiert

### Hauptlücken

- Kein zentraler Immune Orchestrator als Entscheidungsinstanz
- Keine zentrale Recovery Policy Engine über Modulgrenzen hinweg
- DNA-Service noch nicht vollständig persistent/integritätsgesichert
- Keine Genetic Quarantine Lane für riskante/mutierte Varianten
- Keine harte Governance-Kette für high-risk genetische Änderungen

---

## Leitprinzipien

1. Production-Zielbild vor lokaler Bequemlichkeit.
2. `backend/app/modules/*` ist Zielpfad, Legacy wird migriert oder eingefroren.
3. EventStream ist verbindlicher Eventpfad.
4. Immune muss orchestrieren, nicht nur protokollieren.
5. DNA muss persistent, auditierbar, governance-fähig und integritätsgesichert sein.
6. Recovery muss policy-basiert, zentral priorisiert und reproduzierbar werden.
7. OpenCode ist internes Dev/Repair-System, aber keine Hoheitsinstanz.

---

## Priorisierte Phasen

## Phase 0 - Architektur-Freeze und Baseline-Schutz (kurz, sofort)

### Ziel
Verhindern, dass neue Drift entsteht, waehrend Kernmodule konsolidiert werden.

### Deliverables
- Modulklassifikation als Arbeitsstandard aktiv verwenden (`BRAIN_MODULE_CLASSIFICATION.md`)
- EventStream-only Regel bei neuen Runtime-Modulen durchsetzen
- Legacy-Pfade markieren: "migrate" oder "freeze"

### Exit-Kriterien
- Neue Runtime-Aenderungen nur im Zielpfad `backend/app/modules/*`
- Keine neuen Legacy EventBus-Imports
- Dokumentierter Migrationsplan fuer `backend/modules/missions/*`

---

## Phase 1 - Immune Orchestrator (Priorität 1)

### Ziel
Verteilte Schutzsignale zu einer zentralen Entscheidungsschicht zusammenfuehren.

### Scope
- Neues Modul: `backend/app/modules/immune_orchestrator` (Zielname)
- Intake fuer Signale aus:
  - `immune`
  - `runtime_auditor`
  - `system_health`
  - `agent_management`
  - `neurorail`
- Priorisierung nach Severity, Blast Radius, Confidence, Recurrence
- Aktionstypen:
  - observe
  - warn
  - mitigate
  - isolate
  - escalate (Governance/HITL)

### Wichtige Schnittstellen
- EventStream Events in standardisiertem Schema (type, severity, source, entity, context, correlation)
- Policy Hook fuer erlaubte Gegenmaßnahmen
- Audit Hook fuer alle Entscheidungen

### Exit-Kriterien
- Immune-Entscheidungen laufen über einen zentralen Orchestrator-Pfad
- Entscheidung + Aktion + Ergebnis sind auditierbar verknüpft
- Basis-Playbooks fuer mindestens 3 Incident-Typen aktiv

---

## Phase 2 - Unified Recovery Policy Engine (Priorität 2)

### Ziel
Recovery-Logik von verstreuten Implementierungen in ein konsistentes policy-faehiges System ueberfuehren.

### Scope
- Neues Modul: `backend/app/modules/recovery_policy_engine`
- Vereinheitlichung der Strategien:
  - retry
  - circuit-break
  - backpressure
  - rollback
  - detox
  - isolate
  - escalate
- Policy-Regeln fuer:
  - wann welche Strategie erlaubt ist
  - maximale Wiederholungen
  - Eskalationsgrenzen
  - Cooldown/Quarantine-Trigger

### Integration
- Adapter fuer bestehende Recovery-Pfade:
  - `planning/failure_recovery`
  - `neurorail/enforcement`
  - `task_queue` retry-Mechanismen
  - ggf. mission worker retry im Legacy-Pfad

### Exit-Kriterien
- Recovery-Entscheidungen laufen policy-basiert über zentrale Engine
- Bestehende Recovery-Implementierungen nutzen Engine oder klaren Adapter
- Incident -> Recovery -> Outcome Kette ist durchgängig nachvollziehbar

---

## Phase 3 - Genetic Integrity Service (Priorität 3)

### Ziel
DNA von teils in-memory orientierter Verwaltung in persistente, verifizierbare Integrität überführen.

### Scope
- Neues Modul: `backend/app/modules/genetic_integrity`
- Persistenz der DNA-Snapshots als führender Pfad
- Integrity-Features:
  - canonical snapshot serialization
  - hash pro Snapshot
  - optional Signaturpfad (spätere Härtung)
  - chain/reference über parent snapshot
- Governance-Hooks für high-risk mutation requests

### Integration
- `dna` Service wird auf persistente Speicherung umgestellt
- `genesis` Mutationen / Reproduktion referenzieren Integrity-Metadaten
- Audit Logging für jede Mutation inkl. actor, reason, policy decision

### Exit-Kriterien
- DNA-Snapshots persistent und konsistent abrufbar
- Mutationen haben Integritätsmetadaten + Audit Trail
- Governance-Gate für definierte riskante Änderungen aktiv

---

## Phase 4 - Genetic Quarantine Manager (Priorität 4)

### Ziel
Riskante oder experimentelle genetische Varianten isolieren, bevor sie den Kern beeinflussen.

### Scope
- Neues Modul: `backend/app/modules/genetic_quarantine`
- Quarantine States:
  - candidate
  - quarantined
  - probation
  - approved
  - rejected
- Isolationsregeln:
  - eingeschränkte Permissions
  - limitierte Ressourcen
  - begrenzter Scope/tenancy
  - verpflichtende Monitoring- und Health-Kriterien

### Integration
- Immune Orchestrator kann Quarantine triggern
- Recovery Engine kann bei Regression automatisch in Quarantine zurücksetzen
- Governance entscheidet über Promotion/Reject

### Exit-Kriterien
- Mutierte Varianten laufen nicht ungefiltert im Kern
- Quarantine -> Approval Workflow ist formalisiert und auditierbar

---

## Phase 5 - OpenCode Dev/Repair Integration (Priorität 5)

### Ziel
OpenCode als internes Dev-/Repair-Organ in kontrollierte Runtime-/Governance-Struktur einbetten.

### Scope
- Dev Layer operativ an Incident- und Repair-Tickets ankoppeln
- Standardisierte Trigger:
  - Immune Incident
  - Healthcare Wartungsbedarf
  - Governance freigegebener Repair-Auftrag
- Ergebnispakete verpflichtend:
  - Diagnose
  - Patch-Set
  - Tests
  - Risiko-/Rollback-Notiz
  - Audit-Referenz

### Nicht-Ziele
- Keine Übernahme von Identitätshoheit
- Keine Umgehung von Governance-Freigaben
- Keine ungesteuerte Produktions-Selbständerung

### Exit-Kriterien
- OpenCode-Aufträge sind in Governance- und Audit-Flow eingebettet
- Self-Repair ist kontrolliert, nachvollziehbar und reversibel

---

## Abhängigkeiten und Reihenfolge

Empfohlene Reihenfolge ist verbindlich:

1. Immune Orchestrator
2. Unified Recovery Policy Engine
3. Genetic Integrity Service
4. Genetic Quarantine Manager
5. OpenCode Dev/Repair Integration

Begründung:
- Ohne Orchestrator/Recovery-Engine fehlen zentrale Schutzentscheidungen.
- Ohne Genetic Integrity/Quarantine fehlt sichere Evolutionsgrundlage.
- OpenCode-Integration in Self-Repair muss auf diesen Schutzebenen aufbauen.

---

## Risiko- und Kontrollpunkte

### Top-Risiken
- Weiterer Architekturdrift durch parallele Legacy-/Neupfade
- Inkonsistente Eventtypen/Severity-Schemata
- Unzureichende Governance bei riskanten Mutationseingriffen
- Übergreifende Recovery-Entscheidungen ohne zentrale Policy

### Gegenmaßnahmen
- harte Zielpfad-Regeln (`backend/app/modules/*`)
- EventSchema-Standard als Pflicht
- Governance Mandatory Gate fuer high-risk DNA/Recovery-Eingriffe
- zentrale Audit-Korrelation über Incident-ID / Correlation-ID

---

## Meilensteinplan (kompakt)

### M1
Immune Orchestrator Minimal Viable Orchestration
- zentrale Signalaggregation
- priorisierte Aktionsempfehlung
- Event + Audit Kopplung

### M2
Unified Recovery Policy Engine live für Kernpfade
- planning + neurorail + task_queue adapters
- policy-gesteuerte Playbook-Wahl

### M3
Genetic Integrity Baseline
- persistente DNA snapshots
- hash chain
- mutation audit trail

### M4
Genetic Quarantine Operational
- quarantine lane
- approval/probation workflow

### M5
OpenCode Repair-Lane integriert
- incident -> diagnose -> patch -> test -> audit -> integration

---

## Definition of Ready fuer Implementierungsphasen

Vor Start jeder Phase müssen definiert sein:
- Modulverantwortung (owner + boundaries)
- Event-/API-Verträge
- Governance-Gate-Regeln
- Mindesttestset (unit + integration + failure path)
- Observability-Signale (metrics/logs/events)

## Definition of Done je Phase

Jede Phase gilt nur als abgeschlossen, wenn:
- funktionale Ziele erreicht
- Integrationstests grün
- Auditierbarkeit nachgewiesen
- Rollback-Strategie dokumentiert
- Architektur-Dokumentation aktualisiert

---

## Abschluss

Diese Roadmap ist der verbindliche Pfad für die Reifung von BRAiN in den Bereichen:

- Schutz (Immune)
- Wiederherstellung (Recovery)
- genetische Integrität (DNA/Genesis)
- kontrollierte technische Evolution (OpenCode Dev/Repair)

Sie priorisiert zuerst zentrale Orchestrierung und Integrität, bevor adaptive Selbstentwicklung erweitert wird.
