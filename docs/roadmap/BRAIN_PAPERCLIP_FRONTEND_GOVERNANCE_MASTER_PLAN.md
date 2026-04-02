# BRAiN + Paperclip Frontend / Governance Master Plan

Status: Active implementation  
Owner: BRAiN Core  
Date: 2026-04-01

## Current Slice Status

Implemented locally in this repo:

- backend Paperclip handoff endpoints with runtime-policy enforcement
- canonical read-only execution context endpoint for Paperclip MissionCenter
- governed Paperclip action-request endpoint for approval/retry/escalation intents
- ControlDeck inbox and operator decision flow for Paperclip action requests
- approved retry requests now materialize a fresh governed SkillRun + TaskLease dispatch
- approved escalation requests now materialize a supervisor domain escalation handoff
- dedicated ControlDeck Supervisor inbox and escalation detail pages with deep-links from External Operations
- OpenClaw now follows the same governed handoff, action-request and bounded MissionCenter pattern as Paperclip
- External Operations triage is now executor-aware across Paperclip and OpenClaw
- audit/control-plane events for create/open/failure
- replay protection for handoff exchange
- CD3 `External Operations` surface with `Open in Paperclip`
- bounded Paperclip MissionCenter handoff UI served by `paperclip_worker`

Remaining higher-order work:

- richer Paperclip-native operational mappings for company/project/issue entities
- richer supervisor triage workflows and domain-specific handling after escalation intake
- production deployment topology and auth hardening for external app sessions

## 1. Ziel

Paperclip soll nicht nur als externer Executor verfuegbar sein, sondern als sichtbare, kontrollierte Operations-Oberflaeche in das BRAiN-System eingebunden werden, ohne eine zweite Runtime-Autoritaet oder eine zweite Governance-Ebene zu schaffen.

Der Plan verbindet vier Ebenen klar und dauerhaft:

- `BRAiN Core` = Denken, Routing, Governance, Audit, Lernen
- `AXE` = Human Intent, Chat, Ad-hoc Override, Incident-Eingriff
- `ControlDeck v3 (CD3)` = Governance-Konsole, Runtime-Control, Policies, Freigaben, Systemzustand
- `Paperclip UI / MissionCenter` = operative Business-/Agentenverwaltung und Sicht auf laufende Agentenarbeit

## 2. Architekturentscheidung (fest)

## 2.1 Source of Truth

Unveraenderliche Regel:

- `SkillRun` bleibt kanonischer Execution Record.
- `TaskLease` bleibt kanonischer bounded dispatch path fuer externe Executor.
- `BRAiN Runtime-Control + Policy + Audit` bleiben alleinige Governance-Autoritaet.

Paperclip darf anzeigen, organisieren und bounded ausfuehren, aber nicht die Runtime-Wahrheit definieren.

## 2.2 Rolle der Oberflaechen

### AXE

Funktion:

- Chat-/Intent-Eingang
- Human Override
- schnelle Interaktion mit dem System
- Incident-/Approval-Aktionen bei laufenden Missionen

Nicht seine Rolle:

- tiefe Governance-Verwaltung
- umfassende Business-Operations-Uebersicht

### ControlDeck v3

Funktion:

- Governance-Cockpit fuer BRAiN selbst
- Runtime-Control, Policies, Registry, Overrides, Audit, Explainability
- God-Mode / Systemaufsicht

Nicht seine Rolle:

- operative Verwaltung des taeglichen Agenten-Business-Flows
- Ersatz fuer ERP oder Agent-Org-Management

### Paperclip UI / MissionCenter

Funktion:

- operative Agenten-/Team-/Task-Verwaltung
- Sicht auf Ziele, Issues, Heartbeats, Org-Struktur, Ausfuehrungsfortschritt
- menschlicher Beobachtungs- und Eingriffspunkt in das operative Unternehmen

Nicht seine Rolle:

- Governance-Source-of-Truth
- Policy-/Approval-Bypass
- unkontrollierter Zugriff auf externe Systeme

### Odoo

Funktion:

- ERP/System of Record fuer kaufmaennische und operative Geschaeftsdaten

## 2.3 Endgueltige Metapher

- `BRAiN` ist das Gehirn.
- `CD3` ist das Diagnostik- und Governance-Cockpit.
- `AXE` ist die menschliche Sprach- und Eingriffsschnittstelle.
- `Paperclip` ist das sichtbare Operations-/Verwaltungszentrum fuer die Agentenfirma.
- `Odoo` ist das Rueckgrat fuer Geschaeftsprozesse.

## 3. Empfehlung zur UI-Integration

## 3.1 Nicht sofort voll verschmelzen

Die empfohlene Strategie ist **nicht**:

- Paperclip-Frontend komplett in CD3 nachbauen
- CD3 durch Paperclip ersetzen
- beide UIs unkontrolliert parallel als gleichwertige Steuerebenen betreiben

Das wuerde zu doppelten Konzepten, Drift und Governance-Verwirrung fuehren.

## 3.2 Empfohlene Integrationsstufe

Empfohlen ist ein **federiertes UI-Modell mit klarer Hierarchie**:

### Stufe A: Deep-Link + Kontextuebergabe

CD3 zeigt:

- externer Executor aktiv: `paperclip`
- verknuepfte Mission, SkillRun, TaskLease, decision_id
- Button: `Open in Paperclip`

Paperclip zeigt:

- operative Arbeitseinheit, Team, Issues, Heartbeats, Agentenstatus

Warum empfohlen:

- schnellster Weg
- wenig Risiko
- klare Zustandsgrenzen
- keine iframe-/session-/CSP-Komplexitaet am Anfang

### Stufe B: Embedded Read-Only Surface in CD3

Nach Stabilisierung:

- Paperclip Summary Widget in CD3
- read-only Uebersicht fuer laufende Company/Project/Issue/Agenten-Stats

Warum erst spaeter:

- braucht saubere API-Vertraege
- erhoeht Frontend-Komplexitaet

### Stufe C: Federated Action Surface

Spaeter:

- begrenzte Aktionen aus CD3 in Paperclip-Kontext
- z. B. `pause company workflow`, `request approval`, `reassign executor`, `open incident`

Wichtig:

- write-actions immer write-through ueber BRAiN-Governance

## 4. Umsetzungsphasen

## Phase 0 - Bereits erreicht

- Paperclip als External Executor ueber SkillRun/TaskLease integriert
- Policy-/Permit-/Connector-Grenzen geschaffen
- lokaler Docker- und Smoke-Test laeuft

## Phase 1 - Role Clarity + Read-Only Federation

Ziel:

- Oberflaechen sauber trennen
- Navigation und mentale Modelle stabilisieren

Lieferobjekte:

1. Informationsarchitektur-Entscheidung festschreiben
2. CD3 Bereich `External Operations` definieren
3. Deep-Link-Modell CD3 -> Paperclip festlegen
4. eindeutige Begriffe vereinheitlichen:
   - `Mission`
   - `SkillRun`
   - `TaskLease`
   - `Executor`
   - `Company / Project / Issue`

DoD:

- Jeder Operator weiss, welche Aktion in AXE, CD3 oder Paperclip stattfindet.

## Phase 2 - Operational Visibility in CD3

Ziel:

- CD3 wird zur Kontroll- und Beobachtungsebene ueber externe Executor.

Lieferobjekte:

1. CD3 `External Executor Overview`
2. Auflistung aktiver Executor:
   - OpenClaw
   - Paperclip
3. Metriken pro Executor:
   - status
   - task counts
   - failure rate
   - avg duration
   - permit denials
   - connector denials
4. Detailansicht pro SkillRun mit Deep-Link nach Paperclip

DoD:

- Operator kann in CD3 sehen, was extern laeuft, ohne Paperclip zwangsweise oeffnen zu muessen.

## Phase 3 - Paperclip UI als bounded Operations Console

Ziel:

- Paperclip wird offizieller, aber begrenzter Business-Ops-View.

Lieferobjekte:

1. tenant-/company-sichere Zuordnung BRAiN <-> Paperclip
2. Linkmodell:
   - BRAiN mission -> Paperclip company/project/issue
3. signierte Context Handoff Tokens fuer Deep-Link-Start
4. read-only Governance Banner in Paperclip:
   - `Governed by BRAiN`
   - `Sensitive actions require BRAiN approval`

DoD:

- Paperclip fuehlt sich integriert an, bleibt aber sichtbar unter BRAiN-Kontrolle.

## Phase 4 - Bounded Write-Through Actions

Ziel:

- Mensch kann operativ eingreifen, ohne Governance zu umgehen.

Erlaubte erste write-through Aktionen:

- Pause/Resume einer Paperclip-Ausfuehrung
- Reassign bounded task
- Request approval
- Trigger recovery / retry
- Escalate to AXE / CD3 incident view

Nicht erlaubt in dieser Phase:

- direkte Policy-Aenderung in Paperclip
- direkte Secrets-/Connector-Mutationen in Paperclip
- ungebundene neue Systemintegrationen ohne BRAiN approval

DoD:

- Mensch kann eingreifen, aber jede mutation bleibt in BRAiN auditierbar und policy-gesteuert.

## Phase 5 - Multi-App Business Operating Model

Ziel:

- Paperclip, Odoo, Hetzner/Coolify und weitere Apps werden als BRAiN-gesteuerte Business-App-Landschaft harmonisiert.

Lieferobjekte:

1. einheitlicher `Business App Adapter Contract`
2. gemeinsame App-Klassen:
   - `executor_console`
   - `erp`
   - `deployment_plane`
   - `commerce_app`
3. CD3 App Registry / App Governance View
4. Rollenkonzept fuer direkte App-Kommunikation unter Permit-Regeln

DoD:

- Paperclip ist nicht Sonderfall, sondern erstes Mitglied eines generischen Business-App-Modells.

## 5. Daten- und Zustandsmodell

## 5.1 Kanonische Objektbeziehungen

BRAiN-seitig:

- `Mission`
- `SkillRun`
- `TaskLease`
- `decision_id`
- `approval / override / audit / permit`

Paperclip-seitig:

- `Company`
- `Project`
- `Issue`
- `Agent`
- `Heartbeat / Activity`

Verknuepfung:

- `skill_run_id <-> paperclip issue/execution ref`
- `mission_id <-> paperclip company/project context`
- `decision_id <-> governance trace`

## 5.2 Golden Rule

Wenn Status kollidieren:

- BRAiN gewinnt fuer Governance und terminale Ausfuehrungswahrheit.
- Paperclip gewinnt fuer operative Subtask-/Workflow-Sicht innerhalb seiner bounded execution domain.

## 6. Sicherheits- und Governance-Regeln

## 6.1 Harte Regeln

1. Kein direkter Governance-Bypass ueber Paperclip.
2. Keine Secrets-Verwaltung in Paperclip als Source of Truth.
3. Keine direkten Connector-Schreibzugriffe ausserhalb Permit/Policy.
4. Jede sensible Aktion braucht BRAiN-Approval oder Policy-Freigabe.
5. Alle write-actions muessen correlation_id / decision_id / actor-Kontext tragen.

## 6.2 Policy Management Verantwortung

Policy Management bleibt in BRAiN / CD3.

Paperclip darf:

- Policy-Status sehen
- Approval-Status sehen
- bounded approval requests ausloesen

Paperclip darf nicht:

- Policies direkt definieren
- Runtime-Control direkt ueberschreiben

## 7. Frontend-Umsetzungspakete

## Paket A - Informationsarchitektur

Datei-/Doku-Ziel:

- neues Spec/IA-Dokument fuer Rollen der UIs

Inhalt:

- Welche Jobs loest der Nutzer wo?
- Welche Links fuehren zwischen AXE, CD3 und Paperclip?
- Welche Labels sind identisch?

## Paket B - CD3 External Operations Surface

Ziel:

- erste zentrale Sicht auf OpenClaw/Paperclip in CD3

Elemente:

- Executor cards
- policy status
- last decision
- recent task leases
- deep links

## Paket C - Paperclip Handoff UX

Ziel:

- kontrollierter Kontextwechsel von CD3 nach Paperclip

Elemente:

- signierter Link / SSO- oder short-lived handoff token
- target context: company/project/issue
- banner: `Governed by BRAiN`

## Paket D - Approval / Intervention UX

Ziel:

- menschliche Eingriffe konsistent machen

Elemente:

- in CD3: approve/reject/pause/resume
- in AXE: incident and quick-action commands
- in Paperclip: request approval, escalate, view governance reason

## 8. Rollout-Reihenfolge

Empfohlene Reihenfolge:

1. **Dokumente und Begriffe finalisieren**
2. **CD3 read-only external operations view**
3. **Paperclip deep-link handoff**
4. **Canary mit einem echten Unternehmens-Workflow**
5. **bounded write-through actions**
6. **Business App Registry / Multi-App Governance**

## 9. Erfolgskriterien

Der Integrationsschritt ist erfolgreich, wenn:

1. Nutzer eindeutig wissen, wann sie AXE, CD3 oder Paperclip benutzen.
2. Kein operativer Eingriff Governance- oder Policy-Ketten umgeht.
3. Paperclip-UI Mehrwert liefert, ohne zweite Runtime-Autoritaet zu werden.
4. Incident-/Override-Zeit sinkt.
5. External-Executor-Transparenz steigt.
6. Canary-Business-Workflow stabil und nachvollziehbar durchlaeuft.

## 10. Konkrete Empfehlung fuer die direkte Umsetzung

Der naechste beste Schritt ist **nicht** sofortiges Full-Embedding von Paperclip in CD3.

Der naechste beste Schritt ist:

1. Rollenmodell der drei Human Surfaces festschreiben
2. CD3 `External Operations` read-only aufbauen
3. Paperclip per Deep-Link und Handoff-Context anbinden
4. erst danach begrenzte write-through Eingriffe zulassen

## 11. Erste Umsetzungseinheiten (empfohlen)

Wenn wir direkt nach diesem Plan in die Umsetzung gehen, ist die sinnvollste Reihenfolge:

1. Spec: `AXE vs CD3 vs Paperclip responsibilities`
2. Backend contract: `paperclip handoff token + deep-link context`
3. CD3 UI: `External Operations` read-only
4. Paperclip banner + governance context injection
5. Canary workflow validation

---

Kurzform der Entscheidung:

- **Ja**, Paperclip-Frontend nutzen.
- **Nein**, nicht als Ersatz fuer CD3/AXE.
- **Ja**, als Verwaltungs-/Operationsoberflaeche fuer sichtbare Agentenarbeit.
- **Ja**, aber nur bounded unter BRAiN-Governance.
