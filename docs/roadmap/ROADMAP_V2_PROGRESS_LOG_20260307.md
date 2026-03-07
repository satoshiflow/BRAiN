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
