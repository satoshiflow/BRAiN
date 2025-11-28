# Changelog – BRAiN

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.
Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
und Semantic Versioning (MAJOR.MINOR.PATCH).

---

## [0.3.0] – 2025-11-28

### Added
- **Supervisor Deck** (`/supervisor`):
  - Übersicht über Supervisor-Status (Health, Version, Message).
  - Missionssystem-Kachel mit Queue-Status (In Queue, Running, Waiting).
  - Tabellen für:
    - Supervisor Agents (ID, Rolle, Status, Last Heartbeat).
    - Missions Agents (Name/ID, Typ, Status, Meta-Keys).
- **Lifecycle Deck** (`/lifecycle`):
  - Read-only Überblick über Agents-System (Name, Status, Version).
  - Lifecycle-Tabelle mit Agent-ID, Status, Heartbeat, Generation & Meta.
  - Vorbereitung für Register / Heartbeat / Deregister Mutationen.
- **Agent Hooks**:
  - `useAgentsInfo()` – Infos aus `/api/agents/info`.
  - `useSupervisorAgents()` / `useAgentList()` – Supervisor-Agentliste (normalisiert).
  - Lifecycle-Mutations:
    - `useAgentRegister()` → POST `/api/agents/register`.
    - `useAgentHeartbeat()` → POST `/api/agents/heartbeat`.
    - `useAgentDeregister()` → POST `/api/agents/deregister`.
- **Missions Hooks**:
  - `useMissionsInfo()` → `/api/missions/info`.
  - `useMissionsHealth()` / `useMissionHealth()` → `/api/missions/health`.
  - `useMissionsQueuePreview()` / `useMissionQueue()` → `/api/missions/queue`.
  - `useMissionsAgentsInfo()` → `/api/missions/agents/info`.
  - `useMissionEnqueue()` → `/api/missions/enqueue`.

### Changed
- **Dashboard Overview** (`/`):
  - Robustere Normalisierung von Backend-Responses:
    - Missionsqueue wird als Array behandelt, egal ob die API `[...]` oder `{ queue: [...] }` liefert.
    - Supervisor-Agents werden aus `data`, `data.agents` oder Fallback-Arrays extrahiert.
  - Aggregation von Agent-Zuständen über eine `classifyState`-Funktion
    (`online`, `degraded`, `error`, `unknown`).
  - Klare Kacheln für Systemstatus, Agents, Missions und Cluster Health.
- **Sidebar Navigation**:
  - Einträge für:
    - `Overview` (`/`)
    - `Agents` (`/agents`)
    - `Missions` (`/missions`)
    - `LLM Config` (`/settings/llm`)
    - `Agent Config` (`/settings/agents`)
    - `Lifecycle` (`/lifecycle`)
    - `Supervisor` (`/supervisor`)
  - Einheitliches, shadcn-inspiriertes Layout (Sidebar + Header + Content).

### Fixed
- Diverse **Runtime-Fehler** im Frontend:
  - `useMissionQueue is not a function`.
  - `missions.filter is not a function`.
  - `missionAgents.map is not a function`.
  - Import-Probleme von `@/lib/api` & `@/hooks/useMissions`.
- **LLM Settings Page**:
  - Stabiler Zugriff auf LLM-Konfiguration via `useLLMConfig`.
  - API-Wrapper konsolidiert (`src/lib/api.ts` + `brainApi`).

---

## [0.2.0] – 2025-11-27

### Added
- **Control Deck / Overview** (`/`):
  - Erste Version des Dashboards mit Kacheln für Systemstatus, Agenten, Missions
    und Cluster Health.
- **LLM Settings** (`/settings/llm`):
  - Basis-UI für LLM-Konfiguration (Provider, Model, Temperature etc.).
  - React Query Integration für Laden & Aktualisieren der LLM-Config.
- **Agents Settings** (`/settings/agents`):
  - Anzeige grundlegender Agent-Systeminformationen.

---

## [0.1.0] – 2025-11-26

### Added
- Initiales Setup:
  - Next.js + Tailwind + shadcn/ui.
  - Grundlegendes Layout (Sidebar, Header, Content).
  - Integration mit FastAPI-Backend über `brainApi.ts`.
