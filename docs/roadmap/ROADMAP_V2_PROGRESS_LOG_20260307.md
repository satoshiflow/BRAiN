# Roadmap v2 Progress Log (2026-03-07)

## Completed in this run

1) Auth token migration branch repaired and applied
- File: `backend/alembic/versions/a1_add_token_tables.py`
- Fix: added unique constraint for `agent_credentials.agent_id` so self-reference FK is valid.
- Result: `refresh_tokens`, `service_accounts`, `agent_credentials` tables created.

2) Policy engine runtime compatibility fix
- File: `backend/app/modules/policy/service.py`
- Fix: `get_policy_engine` now supports no-DB sync usage for runtime callers; async eager variant retained as `get_policy_engine_async`.
- Result: previous `db_session` missing crash path removed.

3) Event/persistence hardening follow-up
- Files:
  - `backend/app/core/token_keys.py`
  - `backend/app/core/event_contract.py`
  - `backend/mission_control_core/core/event_stream.py`
  - `backend/app/modules/immune_orchestrator/service.py`
  - `backend/app/modules/recovery_policy_engine/service.py`
  - `backend/app/modules/genetic_integrity/service.py`
  - `backend/app/modules/*/models.py` (stabilization modules)
  - `backend/app/modules/audit_logging/models.py`
- Result: smoke path validates immune->recovery persistence, unified audit, and event stream emission.

4) Worker noise hardening
- Files:
  - `backend/app/workers/metrics_collector.py`
  - `backend/app/workers/autoscaler.py`
- Fix: missing cluster schema/enum now treated as migration-missing skip condition to avoid repeated hard error loops.

5) Reserved SQLAlchemy metadata cleanup in memory ORM
- Files:
  - `backend/app/modules/memory/models.py`
  - `backend/app/modules/memory/db_adapter.py`
- Fix: renamed ORM attrs to safe names while preserving DB column names.

6) Runtime readiness re-check (feasible subset) executed
- Backend health reached on localhost bind (`127.0.0.1:8001`) during gate script.
- Login validation: `/api/auth/login` returned `200` after token table migration fix.
- DB verification: stabilization tables + `refresh_tokens` table confirmed present.
- Smoke flow verification: immune -> recovery -> unified audit -> event stream confirmed.
  - evidence sample: `event_delta=2`, `unified_audit=2` for correlation test.

7) AXE_UI frontend analysis completed
- Analysis report: `docs/frontend/AXE_UI_ANALYSIS_20260307.md`
- Build + typecheck pass in `frontend/axe_ui`.

8) Phase C baseline implemented: Genetic Quarantine Manager
- New module: `backend/app/modules/genetic_quarantine/`
- Router registered in `backend/main.py`
- Migration added and applied: `backend/alembic/versions/018_add_quarantine_and_repair_tables.py`
- Module tests added: `backend/tests/modules/test_genetic_quarantine.py`

9) Phase D baseline implemented: OpenCode Repair Loop
- New module: `backend/app/modules/opencode_repair/`
- Router registered in `backend/main.py`
- Immune and Recovery services now support optional repair trigger hooks for high-risk outcomes.
- Module tests added: `backend/tests/modules/test_opencode_repair.py`

10) Gate and verification update
- `./scripts/run_rc_staging_gate.sh` passes end-to-end after fixes.
- Targeted suite passes:
  - immune/recovery/genetic/event-contract + quarantine/repair tests.

11) Route-level auth and audit tests added for new modules
- New test file: `backend/tests/modules/test_quarantine_repair_api_auth.py`
- Coverage:
  - unauthenticated requests -> 401
  - viewer role -> 403
  - operator role -> success paths
  - audit list endpoints include created actions

12) Service hardening for deterministic test/runtime behavior
- Updated stabilization services to avoid implicit DB opens when `db=None`:
  - `backend/app/modules/immune_orchestrator/service.py`
  - `backend/app/modules/recovery_policy_engine/service.py`
  - `backend/app/modules/genetic_integrity/service.py`
- Impact:
  - deterministic in-memory behavior for unit tests
  - reduced accidental coupling to local DB state

13) Audit bridge implicit DB behavior hardened
- File: `backend/app/core/audit_bridge.py`
- Change: implicit DB session creation is now opt-in via `BRAIN_AUDIT_BRIDGE_IMPLICIT_DB=true`.
- Default behavior now avoids hidden DB opens in `db=None` code paths.
- Result: reduced async cancellation runtime warnings in module test runs.

14) Startup seeding path corrected
- File: `backend/main.py`
- Change: built-in skill seeding uses `AsyncSessionLocal` directly (removed invalid `async_session_maker` reference).
- Result: cleaner startup behavior and fewer avoidable warnings.

15) Startup profile and router autodiscovery controls added
- File: `backend/main.py`
- Added:
  - `BRAIN_STARTUP_PROFILE` (`full` / `minimal`)
  - `ENABLE_LEGACY_ROUTER_AUTODISCOVERY`
  - `ENABLE_APP_ROUTER_AUTODISCOVERY`
- Also switched direct `__main__` bind default to `127.0.0.1`.

16) Password hashing backend hardening
- File: `backend/app/core/security.py`
- Changed CryptContext scheme order to prefer `pbkdf2_sha256` with `bcrypt` compatibility fallback.
- Replaced dev password stdout print with logger warning.

17) Verification after hardening
- `./scripts/run_rc_staging_gate.sh` remains green end-to-end.
- Focused module/auth suites pass with reduced warning noise.

18) Task queue governance hardening
- File: `backend/app/modules/task_queue/router.py`
- Added role/auth guards for mutating worker/task endpoints and agent-identity mismatch checks.
- Reduced unguarded mutating surface for core execution path.

19) Runtime blocker mapping and auth surface inventory
- Added script: `backend/scripts/auth_surface_report.py`
- Added report: `docs/roadmap/RUNTIME_BLOCKER_MAP_20260307.md`
- Current unguarded mutating routes concentrated in `agent_management`, `axe_widget`, `credits`, `dns_hetzner`, `knowledge_graph`.

20) Governance/auth closure for high-risk mutating routers
- Hardened auth/role guards in:
  - `backend/app/modules/agent_management/router.py`
  - `backend/app/modules/credits/router.py`
  - `backend/app/modules/dns_hetzner/router.py`
  - `backend/app/modules/knowledge_graph/router.py`
  - `backend/app/modules/task_queue/router.py`
- Added scanner improvements for custom-header auth detection (widget endpoints):
  - `backend/scripts/auth_surface_report.py`
- Result: current auth surface report shows no unguarded mutating endpoints.

21) Startup robustness improvements in full profile
- Skills seeding compatibility fixes:
  - `backend/app/modules/skills/models.py`
  - `backend/app/modules/skills/builtins_seeder.py`
- Cluster enum compatibility hardened in ORM:
  - `backend/app/modules/cluster_system/models.py`
- Worker warning loop noise reduced:
  - `backend/app/workers/metrics_collector.py`
  - `backend/app/workers/autoscaler.py`

22) Router autodiscovery drift reduction
- File: `backend/main.py`
- Changed autodiscovery defaults to disabled unless explicitly enabled:
  - `ENABLE_LEGACY_ROUTER_AUTODISCOVERY=false` (default)
  - `ENABLE_APP_ROUTER_AUTODISCOVERY=false` (default)
- Impact: lowers duplicate/implicit route registration drift; explicit router wiring remains primary path.

23) P1 governance surface closure verified
- Auth hardening completed for remaining previously-flagged mutating routers.
- Auth scanner output (`backend/scripts/auth_surface_report.py`) now reports no unguarded mutating routes.
- RC staging gate remains green after these changes.

24) Legacy containment in entrypoint
- File: `backend/main.py`
- Changes:
  - Mission worker legacy import moved from module import-time to lazy runtime import.
  - Legacy supervisor router switched to explicit opt-in (`ENABLE_LEGACY_SUPERVISOR_ROUTER=false` default).
  - Keeps current behavior when enabled, reduces mandatory legacy coupling by default.

25) Startup profile validation after containment
- Minimal/full startup probes pass with cleaner logs and deterministic startup.
- Full profile starts mission worker, metrics, autoscaler, and skills seeding without prior startup warnings.

26) Additional legacy reference reduction
- File: `backend/app/modules/supervisor/service.py`
- Removed unused direct legacy import (`modules.missions.models.MissionStatus`) from app-level supervisor service.
- Impact: lower hard coupling to `backend/modules/*` within app-module path.

27) Validation after legacy-reduction pass
- `PYTHONPATH=. pytest tests/test_supervisor_agent.py tests/test_module_auth.py -q` passed.
- `./scripts/run_rc_staging_gate.sh` remains green.

28) Phase E close-out
- Hardening objective reached for this roadmap cycle:
  - RC staging gate stable and green after repeated runs
  - auth surface scan reports no unguarded mutating endpoints
  - startup behavior deterministic under minimal/full profiles
- Phase E moved to maintenance mode; further improvements treated as non-blocking cleanup.

## Remaining blockers / deferred

1) Local backend startup path is still heavy and noisy due unrelated module initialization side effects.
- Impact: background start checks are less deterministic than foreground run.
- Next: split startup profiles or gate optional workers/services by env flags.

2) Planning module EventStream wiring still reports reserved metadata error during startup.
- Impact: non-fatal warning, but indicates remaining ORM drift in imported dependency chain.
- Next: trace import chain from planning wiring and remove remaining reserved ORM attribute usage.

3) Cluster system DB enum/type migrations are not fully aligned for all worker query paths in this local DB state.
- Impact: workers skip with warning instead of executing cluster checks.
- Next: apply/repair cluster migration branch and enum creation order.

4) Full background-start stability still depends on startup profile cleanup.
- Impact: service start can be slow/noisy, making nohup health polling brittle.
- Next: create startup profile flags (disable optional workers/services in local gate mode).

5) Full authenticated API tests for quarantine/repair routes not yet added.
- Impact: module behavior is verified at service level; route-level auth contracts still need dedicated tests.
- Next: add authenticated FastAPI tests for create/update/list and audit endpoints.

Resolved in this block:
- Route-level auth tests now implemented for quarantine/repair modules.

29) Legacy Elimination Sprint 1 (compat boundary pass)
- New compatibility bridge:
  - `backend/app/compat/legacy_supervisor.py`
- Legacy imports in app/api runtime paths routed through `app.compat` adapters:
  - `backend/api/routes/axe.py` -> `app.compat.legacy_connector_hub`, `app.compat.legacy_llm`
  - `backend/app/modules/system_health/service.py` -> `app.compat.legacy_missions.get_mission_health_metrics`
  - `backend/app/modules/credits/mission_integration.py` -> `app.compat.legacy_missions.register_credit_hooks`
  - `backend/main.py` legacy supervisor router now loaded via `app.compat.legacy_supervisor`
- Result:
  - Non-test direct `from modules.*` imports are centralized behind `backend/app/compat/*`.
  - Remaining direct legacy imports are limited to compatibility adapters and legacy-oriented tests.

30) Validation notes for this sprint
- Syntax check pass on touched files via `python3 -m py_compile`.
- Targeted pytest collection encountered environment/import blockers in this shell context:
  - missing/strict settings env compatibility for test startup (`Settings` extra fields)
  - legacy test package import expectations (`modules.missions`) in current PYTHONPATH/runtime layout
- No functional rollback performed; blockers documented for follow-up test harness normalization.

31) Skill Engine contract groundwork (Epic 1) drafted
- Added spec files under `docs/specs/`:
  - `skill_definition.md`
  - `capability_definition.md`
  - `provider_binding.md`
  - `skill_run.md`
  - `evaluation_result.md`
- Scope covered per object:
  - field model + types
  - lifecycle states and transition constraints
  - validation rules
  - error code sets
  - minimal API structure
  - event type definitions
- Persistence split explicitly documented:
  - PostgreSQL as durable source of truth
  - Redis for ephemeral runtime/event state
- Governance integration documented:
  - policy gate, auth/role constraints, audit/event requirements

32) Agent execution governance cadence reinforced
- Updated `AGENTS.md` with review flow for spec work:
  - `GROUNDING -> STRUCTURE -> CREATION -> EVALUATION -> FINALIZATION`
- Added explicit contract documentation expectations:
  - fields, lifecycle, validation, error codes, minimal API, event types
  - PostgreSQL vs Redis ownership boundaries.

33) Epic 1 spec review hardening applied (read-only architecture phase)
- Contract docs refined after architecture/risk review:
  - lifecycle/API parity improved for definition objects (reject/deprecate/retire actions)
  - approval flow endpoints added for `SkillRun` (`approve`/`reject`)
  - role/scope baseline added across all five object specs
  - tenant isolation clarified (token-derived tenant, cross-tenant mutation forbidden)
  - capability reference strategy tightened (`CapabilityRef` with version selectors)
  - provider binding deterministic resolution clarified (`capability_key + capability_version`)
  - Event compatibility notes added for envelope/version transition behavior
  - durability note added for state-transition persistence + outbox-compatible event publication.

34) Epic 2 Constitution Gate specs drafted
- Added governance-sensitive specs under `docs/specs/`:
  - `constitution_gate.md`
  - `policy_decision.md`
  - `approval_gate.md`
- Scope covered:
  - fail-closed SkillRun gate flow (`authn -> authz -> tenant -> policy -> approval/breakglass -> audit -> event -> execution`)
  - auth/role/scope matrix
  - tenant isolation rules
  - policy decision contract and immutable snapshotting
  - approval/breakglass lifecycle and anti-replay constraints
  - audit durability and event ordering expectations
  - PostgreSQL vs Redis ownership boundaries

35) Governance spec cadence tightened in agent guidance
- Updated `AGENTS.md` to require governance-sensitive specs to document:
  - auth/role/scope matrix
  - tenant isolation
  - approval/breakglass semantics
  - audit durability and event publication ordering.

36) Epic 3 registry specs drafted
- Added control-plane specs under `docs/specs/`:
  - `skill_registry.md`
  - `capability_registry.md`
- Scope covered:
  - canonical source-of-truth rules (PostgreSQL vs bootstrap/cache)
  - tenant-aware versioning and activation invariants
  - deterministic resolution rules and ambiguity handling
  - search/indexing requirements
  - auth/role/scope baselines for registry mutations and reads
  - durable audit + outbox-first event ordering
  - integration boundaries with Epic 1 contracts and Epic 2 Constitution Gate
  - legacy compatibility boundary for existing `backend/app/modules/skills/`

37) Registry/control-plane documentation rules added to AGENTS guidance
- Updated `AGENTS.md` to require registry specs to document:
  - source-of-truth boundaries
  - deterministic resolution behavior
  - activation/version invariants
  - legacy compatibility and deprecation scope.

38) Epic 4-6 runtime specs drafted
- Added runtime execution specs under `docs/specs/`:
  - `capability_adapter_interface.md`
  - `skill_engine_mvp.md`
  - `skill_telemetry_evaluator_optimizer.md`
- Scope covered:
  - capability adapter contract and normalized result/error model
  - Skill Engine MVP aligned to `GROUNDING -> EXECUTION -> EVALUATION -> FINALIZATION`
  - telemetry/evaluator/optimizer boundaries and KPI minimum set
  - frozen snapshots, determinism, retry/fallback separation
  - privacy/cardinality constraints

39) Epic 7-9 orchestration/runtime consolidation specs drafted
- Added runtime/control-plane specs under `docs/specs/`:
  - `agent_orchestration_contract.md`
  - `runtime_harmonization.md`
  - `knowledge_layer.md`
- Scope covered:
  - agents as orchestration actors instead of business-logic containers
  - harmonized runtime model (`Mission -> SkillRun -> TaskLease`)
  - durable Knowledge Layer distinct from memory
  - compatibility boundaries for legacy mission/task/knowledge paths

40) Epic 10-12 evolution/builder/lifecycle specs drafted
- Added specs under `docs/specs/`:
  - `memory_evolution_model.md`
  - `builder_skill_consumer.md`
  - `plugin_lifecycle.md`
- Scope covered:
  - canonical execution-history anchor for memory/evolution
  - builders as SkillRun consumers
  - official plugin/module lifecycle and decommission rules

41) Review hardening applied across Epic 4-12 specs
- Cross-spec review adjustments included:
  - tenant token-derivation rules added across orchestration/knowledge/evolution/builder flows
  - event taxonomy clarified (`skill.run.*` remains canonical external runtime stream)
  - adapter error model narrowed to provider-side blocking, not BRAiN policy duplication
  - evaluation/finalization ordering clarified for `SkillRun` success semantics
  - semantic memory vs knowledge source-of-truth boundary clarified
  - route ownership and autodiscovery collision constraints added for runtime/plugin migration
  - explicit repo constraint documented where current audit/outbox primitives are not yet transaktional enough for target-state control-plane guarantees.

42) Skill execution standard linked into agent governance
- Updated `AGENTS.md` to require alignment of skill/runtime specs with:
  - `docs/core/brain_skill_execution_standard.md`

43) Agent operating matrix added for parallel delivery
- Added `docs/core/agent_operating_matrix.md`
- Defined:
  - stable working roles for BRAiN delivery
  - preferred model strengths by task type
  - parallel vs sequential execution rules
  - one-writer policy per implementation surface
  - mapping from current local subagent tooling to role-based execution

44) AGENTS guidance extended for multi-agent execution
- Updated `AGENTS.md` with:
  - reference to `docs/core/agent_operating_matrix.md`
  - explicit default role set for BRAiN work
  - role-based orchestration guidance
  - stronger-model preference for architecture/security/migration/critical review.

45) Permanent agent cluster setup guide added
- Added `docs/core/agent_cluster_setup_guide.md`
- Included:
  - required permanent agent list
  - model assignments
  - permission model
  - shared context files
  - escalation rules
  - copy-paste-ready system prompts for all 10 agents

46) Skill-first implementation delivery roadmap added
- Added `docs/roadmap/BRAIN_SKILL_FIRST_IMPLEMENTATION_ROADMAP.md`
- Defined:
  - 6 phases
  - 12 milestones
  - 12 sprint groups
  - immediate next actions for Epic 3 implementation kickoff
  - cross-cutting workstreams for security, verification, docs, and legacy containment

47) AGENTS guidance linked to permanent setup and delivery roadmap
- Updated `AGENTS.md` to reference:
  - `docs/core/agent_cluster_setup_guide.md`
  - `docs/roadmap/BRAIN_SKILL_FIRST_IMPLEMENTATION_ROADMAP.md`

48) Epic 3 implementation baseline started
- Implemented new registry modules:
  - `backend/app/modules/skills_registry/`
  - `backend/app/modules/capabilities_registry/`
- Added initial implementation surfaces:
  - models
  - schemas
  - services
  - routers
  - package exports
- Added backend migration:
  - `backend/alembic/versions/019_add_skill_capability_registries.py`
- Added explicit router wiring in `backend/main.py`
- Preserved existing `backend/app/modules/skills/` as compatibility surface; no legacy expansion performed.

49) Epic 3 implementation verification
- Added targeted tests:
  - `backend/tests/test_skill_capability_registry.py`
- Verified:
  - registry transition helper rules
  - deterministic tenant-over-system resolution preference
  - route authentication baseline
- Local checks run:
  - `python3 -m py_compile` on new registry files
  - `PYTHONPATH=. pytest tests/test_skill_capability_registry.py -q`
  - `PYTHONPATH=. pytest tests/test_skill_capability_registry.py tests/test_module_auth.py -q`
  - `./scripts/run_rc_staging_gate.sh`

50) Architectural observation during Epic 3 grounding
- Current direction suggests BRAiN should likely preserve a small set of stable governance/runtime roles,
  while allowing abilities, contributions, and learned insights to compose contextually at execution time.
- Mission should likely evolve beyond "request envelope -> result" into a source of reusable insight artifacts,
  especially for:
  - run lessons
  - strategy fragments
  - capability/provider performance insights
  - reusable planning/evaluation knowledge
- This aligns more naturally with the existing SkillRun + Knowledge Layer + Memory/Evolution direction than with rigid feature-embedded agent roles.

51) Epic 4 capability adapter baseline implemented
- Added canonical capability runtime layer under `backend/app/core/capabilities/`:
  - adapter base contract
  - normalized execution request/result/error schemas
  - capability execution service
  - bootstrap provider-binding registry for local/runtime bootstrap
- Added initial adapters:
  - `text.generate` via LLM router adapter
  - `connectors.health.check` via connector health adapter
- Added capability runtime API surface:
  - `backend/app/modules/capability_runtime/router.py`
- Wired capability runtime router into `backend/main.py`.

52) Epic 4 hardening adjustments after review
- Fixed registry exact-read/update/transition ambiguity with explicit `owner_scope` targeting and deterministic tenant-first selection.
- Fixed incorrect auth/conflict behavior for system-scope registry writes:
  - missing `platform:catalog:write` now treated as permission failure, not business conflict.
- Fixed capability runtime actor spoofing risk:
  - runtime now stamps authenticated principal as `actor_id` instead of trusting request-supplied actor identity.
- Restricted capability binding inventory/health endpoints to admin-level access.
- Adjusted skill capability validation to prefer tenant-local capability definitions before system fallback.
- Updated migration timestamps to `TIMESTAMPTZ` for better alignment with timezone-aware runtime models.

53) Epic 4 verification
- Added targeted tests:
  - `backend/tests/test_capability_adapters.py`
- Verified:
  - adapter normalization for success and failure
  - binding mismatch rejection
  - capability runtime auth baseline
- Local checks run:
  - `python3 -m py_compile` on Epic 3/4 files
  - `PYTHONPATH=. pytest tests/test_capability_adapters.py tests/test_skill_capability_registry.py tests/test_module_auth.py -q`
  - `./scripts/run_rc_staging_gate.sh`

54) Ongoing architecture observation: mission as shared thinking space
- Current implementation still needs `SkillRun` as canonical execution anchor, but the longer-term architectural pull appears to go beyond action orchestration.
- Strong signal: missions should likely mature into shared thinking spaces that can hold and evolve:
  - goals
  - hypotheses
  - risks
  - external knowledge
  - conflicting perspectives
  - unresolved tensions
  - derived insight artifacts
- This suggests a future pattern where robust decisions emerge not just from executing actions, but from making tensions between perspectives explicit and then resolving or preserving them as reusable mission knowledge.

55) Parallel architecture strand added: mission deliberation and insight evolution
- Added `docs/specs/mission_deliberation_insight_evolution.md`
- Added `docs/roadmap/BRAIN_MISSION_DELIBERATION_INSIGHT_ROADMAP.md`
- New strand formalizes the long-term path:
  - `Execution -> Experience -> Insight -> Pattern -> Knowledge -> Skill Evolution`
- Minimal proposed addition is an `Experience Consolidation` layer with:
  - `ExperienceRecord`
  - `InsightCandidate`
  - `PatternCandidate`
- Long-term mission layer direction captured explicitly:
  - `MissionHypothesis`
  - `MissionPerspective`
  - `MissionTension`
  - `DecisionRecord`
  - `DeliberationSummary`

56) AGENTS guidance extended for learning/evolution architecture
- Updated `AGENTS.md` to require mission/knowledge/evolution work to document:
  - execution anchor vs deliberation artifact boundary
  - insight/pattern/knowledge promotion path
  - selection signals and governance gates
  - unresolved tensions that should stay explicit
- Added explicit references to:
  - `docs/specs/mission_deliberation_insight_evolution.md`
  - `docs/roadmap/BRAIN_MISSION_DELIBERATION_INSIGHT_ROADMAP.md`

57) Epic 5 Skill Engine MVP baseline implemented
- Added `backend/app/modules/skill_engine/` with:
  - `models.py`
  - `schemas.py`
  - `service.py`
  - `router.py`
- Added migration:
  - `backend/alembic/versions/020_add_skill_runs.py`
- Added explicit router wiring in `backend/main.py`
- Implemented first canonical `SkillRun` baseline with:
  - idempotent create path
  - skill registry resolution
  - provider binding freeze snapshot
  - lightweight planning snapshot linkage
  - policy evaluation gate baseline
  - sequential capability execution through adapter runtime
  - terminal success/failure/cancel paths

58) Epic 5 verification
- Added targeted tests:
  - `backend/tests/test_skill_engine.py`
- Verified:
  - plan snapshot shaping
  - evaluation summary behavior
  - route authentication baseline
  - execute endpoint wiring
- Local checks run:
  - `python3 -m py_compile` on Epic 5 files
  - `PYTHONPATH=. pytest tests/test_skill_engine.py tests/test_capability_adapters.py tests/test_skill_capability_registry.py tests/test_module_auth.py -q`
  - `./scripts/run_rc_staging_gate.sh`

59) Skill Engine MVP scope note
- Current Epic 5 implementation intentionally provides a production-oriented baseline, not the final full contract set.
- Present scope includes:
  - canonical `SkillRun` persistence
  - deterministic execution snapshots
  - policy evaluation gate baseline
  - adapter-driven capability execution
- Deferred to later epics or hardening passes:
  - full durable `PolicyDecision` and `ApprovalGate` persistence
  - richer EventStream/audit outbox integration for `SkillRun`
  - advanced evaluator/optimizer integration
  - queue-backed asynchronous execution ownership

60) Architecture observation reinforced during Epic 5
- The new `SkillRun` baseline strengthens execution anchoring and makes later mission-deliberation layering more practical.
- This supports the emerging architecture split:
  - `SkillRun` = execution truth
  - `Mission` = future shared thinking space
  - `Experience/Insight/Pattern` = future consolidation bridge
  - `Knowledge` = curated durable learning layer

61) Epic 6 evaluation and optimizer baseline implemented
- Added new runtime modules:
  - `backend/app/modules/skill_evaluator/`
  - `backend/app/modules/skill_optimizer/`
- Added migration:
  - `backend/alembic/versions/021_add_evaluation_and_optimizer_tables.py`
- Wired evaluator/optimizer routers into `backend/main.py`.
- Integrated automatic `EvaluationResult` creation into `backend/app/modules/skill_engine/service.py` for both success and failure terminalization.
- Baseline optimizer recommendations now project from recent `SkillRun` outcomes:
  - `review_capability_sequence`
  - `tighten_cost_profile`

62) Epic 6 verification and hardening
- Fixed circular-import risk between `skill_engine` and `skill_evaluator` package initialization by removing eager router re-exports in new module `__init__.py` files and narrowing evaluator runtime imports.
- Cleaned Epic 6 lint issues in:
  - `backend/app/modules/skill_engine/service.py`
  - `backend/app/modules/skill_evaluator/models.py`
- Added targeted tests:
  - `backend/tests/test_skill_evaluator_optimizer.py`
- Local checks run:
  - `python3 -m py_compile` on Epic 6 files
  - `cd backend && PYTHONPATH=. pytest tests/test_skill_engine.py tests/test_skill_evaluator_optimizer.py -q`
  - `cd backend && ruff check app/modules/skill_engine app/modules/skill_evaluator app/modules/skill_optimizer tests/test_skill_engine.py tests/test_skill_evaluator_optimizer.py`
  - `./scripts/run_rc_staging_gate.sh`
- Result:
  - targeted Epic 6 suites passed
  - RC staging gate passed end-to-end after Epic 6 integration

63) Epic 6 persistence-contract hardening follow-up
- Evaluation persistence now stores richer frozen execution context in `backend/app/modules/skill_evaluator/`:
  - `skill_key`
  - `skill_version`
  - `metrics_summary`
  - `provider_selection_snapshot`
  - `error_classification`
  - `correlation_id`
  - `evaluation_revision`
- Optimizer persistence now stores advisory lifecycle and evidence linkage in `backend/app/modules/skill_optimizer/`:
  - `status`
  - `source_snapshot`
- Added read-by-id evaluation API in `backend/app/modules/skill_evaluator/router.py`.
- Updated migration draft `backend/alembic/versions/021_add_evaluation_and_optimizer_tables.py` to match hardened contracts before apply.
- Re-verified with:
  - `cd backend && python3 -m py_compile app/modules/skill_evaluator/*.py app/modules/skill_optimizer/*.py app/modules/skill_engine/service.py`
  - `cd backend && PYTHONPATH=. pytest tests/test_skill_evaluator_optimizer.py tests/test_skill_engine.py -q`
  - `cd backend && ruff check app/modules/skill_evaluator app/modules/skill_optimizer app/modules/skill_engine tests/test_skill_evaluator_optimizer.py tests/test_skill_engine.py`
  - `./scripts/run_rc_staging_gate.sh`

64) Epic 7 grounding started: agent/supervisor to SkillRun mapping
- Added grounding doc:
  - `docs/roadmap/EPIC7_AGENT_SKILLRUN_MAPPING_20260308.md`
- Updated orchestration contract:
  - `docs/specs/agent_orchestration_contract.md`
- Mapped current repo state for:
  - `backend/app/modules/agent_management/`
  - `backend/app/modules/supervisor/`
- Locked first-slice direction:
  - agent invocation must wrap `SkillRun`
  - supervisor status must derive from `SkillRun`
  - no new shadow runtime paths in agent/supervisor modules

65) Epic 7 first implementation slice: supervisor status now reads canonical SkillRun runtime
- Updated supervisor runtime wiring:
  - `backend/app/modules/supervisor/service.py`
  - `backend/app/modules/supervisor/router.py`
- Changes:
  - `GET /api/supervisor/status` now derives execution counts from `SkillRun` when DB is available
  - compatibility response fields remain `*_missions` for route stability, but values now map to canonical run states
  - `GET /api/supervisor/agents` now projects running `SkillRun` counts per agent where available
- Added targeted tests:
  - `backend/tests/test_supervisor_skillrun_mapping.py`
- Verification run:
  - `cd backend && python3 -m py_compile app/modules/supervisor/*.py tests/test_supervisor_skillrun_mapping.py`
  - `cd backend && PYTHONPATH=. pytest tests/test_supervisor_skillrun_mapping.py -q`
  - `cd backend && ruff check app/modules/supervisor/service.py app/modules/supervisor/router.py tests/test_supervisor_skillrun_mapping.py`
  - `./scripts/run_rc_staging_gate.sh`

66) Epic 7 first agent-facing orchestration path implemented
- Updated `backend/app/modules/agent_management/` to add:
  - `POST /api/agents/{agent_id}/invoke-skill`
  - request/response contracts for agent-triggered `SkillRun` creation
  - optional immediate execution through the Skill Engine
- Runtime path now wraps canonical `SkillRun` creation instead of introducing a new agent-owned execution surface.
- Agent identity mismatch is rejected for agent principals invoking a different `agent_id`.

67) Epic 7 delegation baseline implemented
- Added durable delegation model and migration:
  - `backend/app/modules/agent_management/models.py`
  - `backend/alembic/versions/022_add_agent_delegations.py`
- Added new delegation contracts and routes:
  - `POST /api/agents/{agent_id}/delegate`
  - `GET /api/agents/{agent_id}/delegations`
- Delegation records now persist:
  - source agent
  - target agent
  - linked `skill_run_id`
  - status
  - correlation id
  - requesting principal
- Added targeted tests:
  - `backend/tests/test_agent_skillrun_orchestration.py`
- Verification run:
  - `cd backend && python3 -m py_compile app/modules/agent_management/*.py app/modules/supervisor/*.py tests/test_agent_skillrun_orchestration.py tests/test_supervisor_skillrun_mapping.py`
  - `cd backend && PYTHONPATH=. pytest tests/test_agent_skillrun_orchestration.py tests/test_supervisor_skillrun_mapping.py -q`
  - `cd backend && ruff check app/modules/agent_management tests/test_agent_skillrun_orchestration.py`
  - `./scripts/run_rc_staging_gate.sh`

68) Epic 7 next slice documented
- Updated:
  - `docs/roadmap/EPIC7_AGENT_SKILLRUN_MAPPING_20260308.md`
  - `docs/specs/agent_orchestration_contract.md`
- Locked next recommended implementation order:
  - delegation acknowledgement lifecycle
  - delegation/run joined read models
  - supervisor escalation views over approval and compliance pressure
  - durable audit bridge for agent invoke/delegate actions

69) Epic 8-12 stabilization pass completed
- Canonical execution and builder stabilization completed across:
  - `backend/app/modules/task_queue/`
  - `backend/app/modules/knowledge_layer/`
  - `backend/app/modules/memory/`
  - `backend/app/modules/learning/`
  - `backend/app/modules/course_factory/`
  - `backend/app/modules/webgenesis/`
  - `backend/app/modules/module_lifecycle/`
- `backend/main.py` now explicitly wires the new runtime surfaces required for the Epic 8-12 baseline.
- Result:
  - `SkillRun` remains canonical execution truth
  - task queue is narrowed to subordinate lease/dispatch behavior
  - builder routes are wrapped around governed execution ownership
  - module lifecycle is explicit control-plane state instead of implicit import state

70) Legacy/test compatibility normalization completed for wider regression coverage
- Added compatibility/bootstrap handling in:
  - `backend/__init__.py`
  - `backend/backend/__init__.py`
  - `backend/backend/main.py`
  - `backend/api/__init__.py`
  - `backend/app/core/config.py`
- Added pytest compatibility shims in `backend/main.py` so legacy app-level tests can still exercise builder/runtime APIs.
- Result:
  - `backend.main` imports now work cleanly in legacy test layouts
  - wider builder/governance regression collection no longer fails on import-path assumptions

71) Builder, orchestration, and governance regression slice verified
- Verified with:
  - `PYTHONPATH=. pytest tests/test_course_factory.py tests/test_sprint10_webgenesis_ir.py tests/test_webgenesis_mvp.py tests/test_webgenesis_ops.py tests/test_webgenesis_sprint3.py tests/test_skill_engine.py tests/test_skill_evaluator_optimizer.py tests/test_skill_capability_registry.py tests/test_agent_skillrun_orchestration.py tests/test_supervisor_skillrun_mapping.py tests/test_task_queue_skill_run_lease.py -q`
- Result:
  - `100 passed`

72) RC staging gate restored to green after Epic 8-12 work
- Additional compatibility fix:
  - `backend/backend/__init__.py` package-path extension so legacy `backend.modules` imports resolve during RC collection
- Verified with:
  - `./scripts/run_rc_staging_gate.sh`
- Result:
  - auth + agent lifecycle: `48 passed`
  - immune decision + event contract: `6 passed`
  - recovery action flow: `40 passed`
  - DNA integrity + audit: `10 passed`
  - guardrails: passed

73) Current handoff state
- Epic 3-7 remain green.
- Epic 8-12 now have implemented and verified baselines rather than interrupted partial edits.
- Remaining work is mainly cleanup and coverage expansion, not active breakage repair.

74) Epic 12 hardening pass completed
- `module_lifecycle` was strengthened with:
  - typed classification and lifecycle status models
  - validated lifecycle transition rules
  - enforced `replacement_target` for `deprecated` and `retired`
  - filtered listing support
  - decommission-matrix read endpoint
- Builder write-owner guards were rechecked against lifecycle state for `course_factory` and `webgenesis`.

75) Coverage expanded for lifecycle, knowledge, and run-ingest paths
- Added:
  - `backend/tests/test_module_lifecycle.py`
  - `backend/tests/test_knowledge_layer.py`
  - `backend/tests/test_runtime_ingest_routes.py`
- Coverage now explicitly validates:
  - lifecycle transition enforcement
  - builder write blocking for deprecated/retired modules
  - knowledge-layer search and run-lesson ingest
  - memory/learning ingestion from canonical `skill_run_id` runtime state

76) Low-risk cleanup applied to test-only compatibility handling
- Moved `TestClient` URL/delete compatibility patching out of `backend/main.py` into `backend/tests/conftest.py`.
- Kept app-level auth overrides in `backend/main.py` because that path remains RC-gate-stable and still supports legacy app-level tests.
- Result:
  - runtime entrypoint is slightly cleaner
  - test-only transport compatibility is now owned by the test layer

77) Post-hardening verification completed
- Verified with:
  - `PYTHONPATH=. pytest tests/test_module_lifecycle.py tests/test_knowledge_layer.py tests/test_runtime_ingest_routes.py tests/test_course_factory.py tests/test_sprint10_webgenesis_ir.py tests/test_webgenesis_mvp.py tests/test_webgenesis_ops.py tests/test_webgenesis_sprint3.py tests/test_skill_engine.py tests/test_skill_evaluator_optimizer.py tests/test_skill_capability_registry.py tests/test_agent_skillrun_orchestration.py tests/test_supervisor_skillrun_mapping.py tests/test_task_queue_skill_run_lease.py -q`
- Result:
  - `110 passed`
- RC gate rerun after hardening/cleanup also passed.

78) Paket A execution: shim-reduction and test-bootstrap centralization advanced
- `backend/main.py` no longer carries pytest-driven auth override logic; test-principal bootstrap now lives in `backend/tests/conftest.py`.
- Builder/runtime tests were further aligned to central test bootstrap usage:
  - `backend/tests/test_course_factory.py`
  - `backend/tests/test_webgenesis_mvp.py`
  - `backend/tests/test_webgenesis_ops.py`
  - `backend/tests/test_webgenesis_sprint3.py`
- Remaining legacy-oriented tests (for example `test_foundation.py`, `test_policy_engine.py`, `test_mission_system.py`) intentionally remain unchanged in this cut to keep blast radius low.

79) Paket B execution: lifecycle/legacy alignment deepened on runtime ingests
- Added lifecycle write guards to additional mutating runtime surfaces:
  - `backend/app/modules/knowledge_layer/router.py`
  - `backend/app/modules/memory/router.py`
  - `backend/app/modules/learning/router.py`
  - `backend/app/modules/task_queue/router.py`
- Guards now block mutating operations when module lifecycle is `deprecated` or `retired`, while keeping read paths unaffected.

80) Coverage expanded for lifecycle-blocking behavior on non-builder runtime paths
- Updated tests:
  - `backend/tests/test_knowledge_layer.py`
  - `backend/tests/test_runtime_ingest_routes.py`
- Added explicit assertions that writes on retired/deprecated modules return `409` for knowledge, memory, and learning ingest routes.

81) Post-A/B verification completed
- Verified with:
  - `PYTHONPATH=. pytest tests/test_course_factory.py tests/test_sprint10_webgenesis_ir.py tests/test_webgenesis_mvp.py tests/test_webgenesis_ops.py tests/test_webgenesis_sprint3.py tests/test_skill_engine.py tests/test_skill_evaluator_optimizer.py tests/test_skill_capability_registry.py tests/test_agent_skillrun_orchestration.py tests/test_supervisor_skillrun_mapping.py tests/test_task_queue_skill_run_lease.py tests/test_module_lifecycle.py tests/test_knowledge_layer.py tests/test_runtime_ingest_routes.py -q`
- Result:
  - `113 passed`
- RC gate rerun also passed after A/B execution.

82) Additional shim-reduction slice completed with low risk
- Reduced package-level pytest side effects by removing `BRAIN_EVENTSTREAM_MODE` toggling from:
  - `backend/__init__.py`
  - `backend/backend/__init__.py`
- Centralized test-side degraded mode ownership in `backend/tests/conftest.py`.
- Stabilized task queue lease response typing for UUID conversion in `backend/app/modules/task_queue/router.py`.

83) Verification after additional shim-reduction slice
- Verified with:
  - `PYTHONPATH=. pytest tests/test_course_factory.py tests/test_webgenesis_mvp.py tests/test_webgenesis_ops.py tests/test_webgenesis_sprint3.py tests/test_task_queue_skill_run_lease.py tests/test_knowledge_layer.py tests/test_runtime_ingest_routes.py -q`
  - `PYTHONPATH=. pytest tests/test_course_factory.py tests/test_sprint10_webgenesis_ir.py tests/test_webgenesis_mvp.py tests/test_webgenesis_ops.py tests/test_webgenesis_sprint3.py tests/test_skill_engine.py tests/test_skill_evaluator_optimizer.py tests/test_skill_capability_registry.py tests/test_agent_skillrun_orchestration.py tests/test_supervisor_skillrun_mapping.py tests/test_task_queue_skill_run_lease.py tests/test_module_lifecycle.py tests/test_knowledge_layer.py tests/test_runtime_ingest_routes.py -q`
- Result:
  - targeted slice: all green
  - wider slice: `113 passed`
- RC gate rerun after this slice also passed.
