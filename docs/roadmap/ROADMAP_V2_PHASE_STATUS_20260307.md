# Roadmap v2 Phase Status (2026-03-07)

## Phase A - Hardening and Baseline Freeze

Status: Completed (with residual warnings)

Completed:
- SQLAlchemy reserved-name blockers fixed (`policy`, `audit`, `widget`, `memory` models)
- import-path compatibility blockers fixed for supervisor path
- neurorail syntax and constructor mismatches fixed
- auth key-loading resilience for local runtime
- policy engine runtime compatibility for worker callers

Residual:
- startup still logs non-blocking warnings in optional modules
- passlib/bcrypt version warning in environment

## Phase B - Runtime Operational Readiness Gate 2.0

Status: Completed

Completed:
- dev stack startup and service checks executed
- migrations and stabilization tables verified
- immune -> recovery -> unified audit -> event stream smoke flow validated
- RC staging gate script passes end-to-end

## Phase C - Genetic Quarantine Manager

Status: Implemented baseline

Delivered:
- module: `backend/app/modules/genetic_quarantine/`
- state model: `candidate/quarantined/probation/approved/rejected`
- DB persistence + migration revision `018_add_quarantine_and_repair_tables`
- API routes with auth and operator/admin guard
- event + unified audit emission

## Phase D - OpenCode Repair Loop

Status: Implemented baseline

Delivered:
- module: `backend/app/modules/opencode_repair/`
- ticket lifecycle model (`open -> ... -> closed`)
- auto-trigger endpoint and service path
- integration trigger hooks from immune/recovery high-risk decisions
- persistence + audit + event emission

## Phase E - Post-integration hardening

Status: Completed (stability target met, maintenance mode)

Completed in this iteration:
- optional startup controls strengthened (`ENABLE_BUILTIN_SKILL_SEED` support)
- worker migration-missing safeguards expanded for cluster enum/table drift
- docs and runtime reference artifacts consolidated

Maintenance backlog (non-blocking):
- further reduce environment-level warnings (`passlib`/`crypt` stack and pydantic deprecation noise)
- continue gradual legacy-path retirement under `backend/modules/*`
- optional additional e2e/API coverage beyond current gate scope

Update after next block:
- authenticated API coverage for quarantine/repair routes has been added.
- RC staging gate re-run remains green after these additions.

Update after current hardening pass:
- startup profile controls and router autodiscovery toggles added.
- direct run bind defaults to localhost (`127.0.0.1`).
- warning footprint reduced further; gate remains green.

Update after governance closure sprint:
- previously unguarded mutating endpoints were hardened with explicit auth/role controls.
- auth surface report currently shows no unguarded mutating routes.
- autodiscovery defaults set to disabled to reduce architecture drift.

Update after legacy containment sprint:
- legacy supervisor router moved to opt-in startup flag.
- mission worker legacy import changed to lazy runtime import in lifespan.
- startup probes (minimal/full) remain stable with cleaner logs.
