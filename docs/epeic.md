Perfekt — hier ist ein konkretes **Read-only Migrations-Backlog** für das aktuelle Repo, in sinnvoller Reihenfolge.

Legende:  
- `[RW]` wiederverwenden  
- `[MV]` verschieben  
- `[MG]` zusammenführen  
- `[NB]` neu bauen  
- `[ST]` stilllegen  

---

### Epic 1 — Verbindliche Ziel-Contracts für Skills/Capabilities festziehen `[NB]`
- **Ziel:** Ein verbindliches Daten-/API-Contract-Fundament schaffen, bevor Migration startet.
- **Betroffene Module/Pfade:** `docs/architecture/brain_target_architecture.md`, `docs/architecture/brain_capability_model.md`, `docs/skills/brain_skill_engine.md`, neu unter `docs/specs/` (Skill/Capability Schemas).
- **Abhängigkeiten:** keine.
- **Risiken:** spätere Rework-Wellen ohne stabile Contracts.
- **Done-Kriterien:** versionierte Spec für `SkillDefinition`, `CapabilityDefinition`, `SkillRun`, `EvaluationResult`, `ProviderBinding` inkl. Felder/States/Fehlercodes.

### Epic 2 — Constitution Gate auf Skill-Run-Ebene definieren `[RW][NB]`
- **Ziel:** Sicherstellen, dass künftige Skill-Ausführung nicht an Auth/Governance vorbei läuft.
- **Betroffene Module/Pfade:** `backend/app/core/auth_deps.py`, `backend/app/core/security.py`, `backend/app/core/event_contract.py`, `backend/app/core/audit_bridge.py`, `backend/app/modules/policy/`, `backend/app/modules/governance/`.
- **Abhängigkeiten:** Epic 1.
- **Risiken:** Shadow-Execution ohne Audit/Policy.
- **Done-Kriterien:** einheitlicher “Skill Run Authorization + Policy Check + Audit Emit” Ablauf spezifiziert und testbar definiert.

### Epic 3 — Registry-Fundament: Skill Registry + Capability Registry `[NB][RW]`
- **Ziel:** Zentralen Registry-Kern schaffen (Definitionen, Versionierung, Aktivierung).
- **Betroffene Module/Pfade:** neu `backend/app/modules/skills_registry/`, neu `backend/app/modules/capabilities_registry/`, `[RW]` Pattern aus `backend/app/modules/agent_management/`, `backend/app/modules/task_queue/`.
- **Abhängigkeiten:** Epic 1, 2.
- **Risiken:** mehrere “Wahrheiten” (YAML/DB/Code) parallel.
- **Done-Kriterien:** CRUD + Versioning + Status (`draft/active/deprecated`) + Auth/Audit + minimale API-Doku.

### Epic 4 — Capability Adapter Interface + Provider Binding Layer `[NB][RW][MG]`
- **Ziel:** Provider-Aufrufe standardisieren und austauschbar machen.
- **Betroffene Module/Pfade:** `[RW]` `backend/app/modules/llm_router/`, `backend/app/modules/connectors/`, `backend/app/modules/integrations/`; neu `backend/app/core/capabilities/`.
- **Abhängigkeiten:** Epic 3.
- **Risiken:** heterogene Providerantworten, inkonsistente Fehlerbehandlung.
- **Done-Kriterien:** standardisiertes Adapter-Interface, einheitliches Result/Error-Schema, mindestens 2 Capability-Domänen angebunden (z. B. `text.generate`, `research.web.search`).

### Epic 5 — Skill Engine MVP (Selector/Planner/Resolver/Executor) `[NB][RW]`
- **Ziel:** Ersten durchgehenden Skill-Lauf implementierbar machen.
- **Betroffene Module/Pfade:** neu `backend/app/modules/skill_engine/`, `[RW]` `backend/app/modules/planning/`, `backend/app/modules/task_queue/`.
- **Abhängigkeiten:** Epic 3, 4.
- **Risiken:** Parallelwelt zu bestehender Mission-Orchestrierung.
- **Done-Kriterien:** end-to-end SkillRun mit Status-Lifecycle, Retry/Fallback-Hooks, Persistenz und Audit/Event-Ausgabe.

### Epic 6 — Telemetry/Evaluation/Optimizer Baseline `[NB][RW][MG]`
- **Ziel:** Skill-Ausführung messbar und optimierbar machen.
- **Betroffene Module/Pfade:** `[RW]` `backend/app/modules/monitoring/`, `backend/app/modules/telemetry/`, `backend/app/core/metrics.py`, `backend/mission_control_core/core/event_stream.py`; neu `backend/app/modules/skill_evaluator/`, `backend/app/modules/skill_optimizer/`.
- **Abhängigkeiten:** Epic 5.
- **Risiken:** hohe Metrik-Cardinality, unklare KPI-Definition.
- **Done-Kriterien:** definierte KPIs (Kosten, Latenz, Qualität, Erfolgsquote), Evaluations-Event-Typen, optimizer input/output contract.

### Epic 7 — Agenten auf Skill-Orchestrierung umstellen `[RW][MG][MV]`
- **Ziel:** Agents delegieren Skills statt Fachlogik selbst zu tragen.
- **Betroffene Module/Pfade:** `backend/app/modules/agent_management/`, `backend/app/modules/supervisor/`, `backend/brain/agents/` (falls aktiv), `backend/app/modules/autonomous_pipeline/`.
- **Abhängigkeiten:** Epic 5, 6.
- **Risiken:** Regression in bestehenden Agent-APIs.
- **Done-Kriterien:** Agent-Aktionen laufen über Skill-Invocation-Contract; direkte Businesslogik in Agenten deutlich reduziert und dokumentiert.

### Epic 8 — Mission/Task Runtime mit SkillRun harmonisieren `[MG][RW][ST]`
- **Ziel:** Doppelte Ausführungspfade auflösen (Mission vs SkillRun).
- **Betroffene Module/Pfade:** `backend/modules/missions/` (legacy), `backend/app/modules/missions/`, `backend/main.py`, `backend/app/modules/task_queue/`.
- **Abhängigkeiten:** Epic 5, 7.
- **Risiken:** bekannte Legacy/App-Kollisionen; Worker-Entkopplung.
- **Done-Kriterien:** klarer primärer Runtime-Pfad dokumentiert; ein Pfad als “source of truth”, anderer explizit deprecated/flagged.

### Epic 9 — Knowledge Layer als langlebige Wissensschicht etablieren `[NB][RW][MG]`
- **Ziel:** Architektur-/Entscheidungs-/Run-Wissen strukturiert persistieren.
- **Betroffene Module/Pfade:** `[RW]` `backend/app/modules/knowledge_graph/`; neu `backend/app/modules/knowledge_layer/` (oder Ausbau des bestehenden Moduls); Docs unter `docs/knowledge/`.
- **Abhängigkeiten:** Epic 6.
- **Risiken:** Vermischung von “Knowledge” und “Memory”.
- **Done-Kriterien:** Knowledge-Schema (versioniert, owner, validity), ingest/update/query-Flows, Governance/Audit angebunden.

### Epic 10 — Memory & Evolution Datenmodell konsolidieren `[RW][MG][MV]`
- **Ziel:** Lernfähige Historien für Optimierung und Evolution vereinheitlichen.
- **Betroffene Module/Pfade:** `backend/app/modules/memory/`, `backend/app/modules/dna/`, `backend/app/modules/genesis/`, `backend/app/modules/genetic_integrity/`, `backend/app/modules/genetic_quarantine/`.
- **Abhängigkeiten:** Epic 6, 9.
- **Risiken:** in-memory Reste, inkonsistente Historienquellen.
- **Done-Kriterien:** gemeinsames SkillRun-History-Modell (episodic/semantic/procedural Bezug), klarer Datenfluss zu Optimizer und Quarantine.

### Epic 11 — Builders als Skill-Consumer standardisieren `[RW][MG][MV]`
- **Ziel:** Domain-Builder (Web/Course/Workflow) nutzen Skills als primären Ausführungspfad.
- **Betroffene Module/Pfade:** `backend/app/modules/webgenesis/`, `backend/app/modules/course_factory/`, ggf. `backend/app/modules/deployment/`, `backend/app/modules/dns_hetzner/`.
- **Abhängigkeiten:** Epic 5, 7, 9.
- **Risiken:** Builder-spezifische Sonderlogik blockiert Standardisierung.
- **Done-Kriterien:** mindestens zwei Builder-End-to-End-Flows laufen über Skill Engine + Capability Resolver.

### Epic 12 — Plugin/Module Lifecycle + Decommission-Plan `[NB][RW][ST][MV]`
- **Ziel:** Neue Plugin-Struktur operationalisieren und Altpfade geordnet stilllegen.
- **Betroffene Module/Pfade:** `backend/app/modules/*`, `backend/modules/*` (legacy), `backend/main.py`, `docs/architecture/BRAIN_MODULE_CLASSIFICATION.md`, `docs/roadmap/*`.
- **Abhängigkeiten:** Epic 8–11.
- **Risiken:** Breaking Changes durch zu frühes Abschalten.
- **Done-Kriterien:** offizieller Lifecycle (`experimental/stable/deprecated/retired`), Decommission-Matrix je Modul, Migrationsflags + Sunset-Termine + Gate-Checks.

---

**Empfohlene Reihenfolge (kompakt)**  
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12
