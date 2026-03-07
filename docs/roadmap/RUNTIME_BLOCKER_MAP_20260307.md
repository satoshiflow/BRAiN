# Runtime Blocker Map (2026-03-07)

## Snapshot

Based on startup probes and auth surface scan after Phase A-E baseline work.

## 1) Startup warnings

- **Cluster schema warning loop (reduced):** worker logs now degrade to one warning + debug repeats when cluster schema is missing.
  - files: `backend/app/workers/metrics_collector.py`, `backend/app/workers/autoscaler.py`
- **Dev password generation warning:** emitted in development when no env password is set.
  - file: `backend/app/core/security.py`
- **Optional dependency notices (now debug-level by default):** system_health/runtime_auditor optional imports.
  - files: `backend/app/modules/system_health/service.py`, `backend/app/modules/runtime_auditor/service.py`

## 2) Architecture drift

- Auto-discovery defaults now disabled; explicit router wiring is primary path.
  - file: `backend/main.py`
- Legacy supervisor router now opt-in (`ENABLE_LEGACY_SUPERVISOR_ROUTER=false` default).
- Legacy-vs-target code paths still coexist (`backend/modules/*` and `backend/app/modules/*`) but entrypoint coupling reduced.
- Additional containment: removed one unused app-level legacy import in supervisor service.

## 3) Dependency issues

- Passlib/bcrypt environment warning may still appear in some environments (non-blocking).
- Cluster model/migration mismatch previously caused enum issues; corrected via non-native enums in ORM.
  - file: `backend/app/modules/cluster_system/models.py`

## 4) Governance risk

Auth surface scan (`backend/scripts/auth_surface_report.py`) now reports no unguarded mutating endpoints.

Latest interpretation:
- `axe_widget` mutating public endpoints are treated as protected via custom header auth (`X-API-Key`, `X-Session-Token`) in the auth-surface scanner.
- Previously unguarded module routes (`agent_management`, `credits`, `dns_hetzner`, `knowledge_graph`, `task_queue`) were hardened with explicit role/auth dependencies.

## Priority Order (stability-first)

1. **P1 - Governance/Auth Closure for unguarded mutating routes**
   - Highest risk (security + control boundary).
   - Status: Completed for currently detected surface.
2. **P2 - Startup determinism cleanup in full profile**
   - Reduce residual warning noise and startup side effects.
3. **P3 - Router/autodiscovery drift control**
   - Lower surprise/duplication risk in deployments.
4. **P4 - Dependency hygiene cleanup**
   - Minimize environment-specific warnings and brittle behavior.

## Immediate actions already applied in this block

- Task queue mutating endpoints hardened with role/auth checks and agent identity check.
  - file: `backend/app/modules/task_queue/router.py`
- Startup warning profile reduced:
  - skills builtins seeding fixed (`backend/app/modules/skills/builtins_seeder.py`, `backend/app/modules/skills/models.py`)
  - optional dependency warnings downgraded in non-strict mode
  - cluster enum mismatch addressed in ORM (`native_enum=False`)
