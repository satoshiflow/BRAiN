# BRAiN Module Inventory (2026-03-07)

This inventory is a machine-assisted snapshot of backend architecture status before further development.

Scope:
- `backend/app/modules/*`
- `backend/modules/*` (legacy)
- runtime wiring in `backend/main.py`

Method (heuristic):
- `status=active` if module router is explicitly included in `backend/main.py`
- `status=standby` if module has `router.py` but is not explicitly included
- `status=library` if no router exists
- `auth_surface` inferred from common auth dependency markers in router code
- `persistence` inferred from presence of `models.py`

## Snapshot Summary

- Total components inventoried: 72
- App modules: 67
- Legacy modules: 5
- Explicitly active app modules in `main.py`: 31
- Standby app modules (router exists, not explicitly wired): 28
- Library app modules (no router): 8
- Legacy overlap names (app + legacy): `missions`, `supervisor`

## Key Findings

- Legacy containment is in progress; direct runtime imports are increasingly routed through `backend/app/compat/*`.
- There is still architectural duality across API/module surfaces (`backend/api/routes`, `backend/app/api/routes`, `backend/app/modules/*/router.py`).
- Some modules are likely dormant in default startup because autodiscovery is disabled by default.
- `backend/app/core/event_bus.py` remains a documented stub and should not be treated as production event backbone.

## Output Data

Detailed machine-readable inventory:
- `docs/architecture/module_inventory_20260307.csv`

Suggested immediate usage:
1. Use `migration_priority=high` as Sprint-1 cleanup candidates.
2. Assign explicit owners for all `owner=unassigned` rows.
3. Confirm whether `standby` modules are intentional or should be wired/removed.
