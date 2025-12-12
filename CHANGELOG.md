# Changelog - BRAiN

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.0] - 2025-12-12

### Added
- **Comprehensive Documentation Overhaul**:
  - Complete rewrite of `README.md` with badges, features, and examples
  - Expanded `README.dev.md` with detailed developer setup and workflows
  - New `docs/ARCHITECTURE.md` with system architecture and design decisions
  - Updated `CLAUDE.md` to version 0.4.0 with latest information

### Changed
- **Documentation Language**: All documentation now in English for broader accessibility
- **Version Synchronization**: All documentation files now at version 0.4.0
- **Improved Structure**: Better organization of documentation with clear navigation

### Fixed
- Documentation consistency across all files
- Outdated references and broken links

---

## [0.3.0] - 2025-11-28

### Added
- **Supervisor Deck** (`/supervisor`):
  - Supervisor status overview (Health, Version, Message)
  - Mission system tile with queue status (In Queue, Running, Waiting)
  - Tables for:
    - Supervisor Agents (ID, Role, Status, Last Heartbeat)
    - Mission Agents (Name/ID, Type, Status, Meta-Keys)
- **Lifecycle Deck** (`/lifecycle`):
  - Read-only overview of Agents system (Name, Status, Version)
  - Lifecycle table with Agent-ID, Status, Heartbeat, Generation & Meta
  - Preparation for Register / Heartbeat / Deregister mutations
- **Agent Hooks**:
  - `useAgentsInfo()` - Info from `/api/agents/info`
  - `useSupervisorAgents()` / `useAgentList()` - Supervisor agent list (normalized)
  - Lifecycle mutations:
    - `useAgentRegister()` → POST `/api/agents/register`
    - `useAgentHeartbeat()` → POST `/api/agents/heartbeat`
    - `useAgentDeregister()` → POST `/api/agents/deregister`
- **Mission Hooks**:
  - `useMissionsInfo()` → `/api/missions/info`
  - `useMissionsHealth()` / `useMissionHealth()` → `/api/missions/health`
  - `useMissionsQueuePreview()` / `useMissionQueue()` → `/api/missions/queue`
  - `useMissionsAgentsInfo()` → `/api/missions/agents/info`
  - `useMissionEnqueue()` → `/api/missions/enqueue`

### Changed
- **Dashboard Overview** (`/`):
  - More robust normalization of backend responses:
    - Mission queue handled as array, whether API returns `[...]` or `{ queue: [...] }`
    - Supervisor agents extracted from `data`, `data.agents`, or fallback arrays
  - Aggregation of agent states via `classifyState` function
    (`online`, `degraded`, `error`, `unknown`)
  - Clear tiles for System Status, Agents, Missions, and Cluster Health
- **Sidebar Navigation**:
  - Entries for:
    - `Overview` (`/`)
    - `Agents` (`/agents`)
    - `Missions` (`/missions`)
    - `LLM Config` (`/settings/llm`)
    - `Agent Config` (`/settings/agents`)
    - `Lifecycle` (`/lifecycle`)
    - `Supervisor` (`/supervisor`)
  - Unified, shadcn-inspired layout (Sidebar + Header + Content)

### Fixed
- Various **runtime errors** in frontend:
  - `useMissionQueue is not a function`
  - `missions.filter is not a function`
  - `missionAgents.map is not a function`
  - Import problems from `@/lib/api` & `@/hooks/useMissions`
- **LLM Settings Page**:
  - Stable access to LLM configuration via `useLLMConfig`
  - Consolidated API wrapper (`src/lib/api.ts` + `brainApi`)

---

## [0.2.0] - 2025-11-27

### Added
- **Control Deck / Overview** (`/`):
  - First version of dashboard with tiles for System Status, Agents, Missions, and Cluster Health
- **LLM Settings** (`/settings/llm`):
  - Basic UI for LLM configuration (Provider, Model, Temperature, etc.)
  - React Query integration for loading & updating LLM config
- **Agents Settings** (`/settings/agents`):
  - Display of basic agent system information

---

## [0.1.0] - 2025-11-26

### Added
- **Initial Setup**:
  - Next.js + Tailwind + shadcn/ui
  - Basic layout (Sidebar, Header, Content)
  - Integration with FastAPI backend via `brainApi.ts`

---

## Version History

### Semantic Versioning

- **MAJOR** version when making incompatible API changes
- **MINOR** version when adding functionality in a backwards compatible manner
- **PATCH** version when making backwards compatible bug fixes

### Release Notes

For detailed release notes and migration guides, see [GitHub Releases](https://github.com/satoshiflow/BRAiN/releases).

---

**Maintained by:** BRAiN Development Team
**Last Updated:** 2025-12-12
