# Plugin and Module Lifecycle Specification (v1)

Status: Baseline implemented and stabilized (2026-03-08)  
Scope: Establishes official lifecycle, activation prerequisites, compatibility, and decommission rules for modules/plugins.

## Purpose

This spec makes module and plugin lifecycle explicit so BRAiN can evolve without architecture drift.

## Dual Axes

Architecture classification and lifecycle are separate.

### Architecture classification
- `CORE`
- `CONSOLIDATE`
- `MIGRATE`
- `FREEZE`
- `REPLACE`
- `NEW`

### Operational lifecycle
- `experimental`
- `stable`
- `deprecated`
- `retired`

## Canonical Lifecycle Metadata

Every module/plugin record must track:
- `module_id`
- `owner_scope`
- `classification`
- `lifecycle_status`
- `canonical_path`
- `active_routes`
- `data_owner`
- `auth_surface`
- `event_contract_status`
- `audit_policy`
- `migration_adapter`
- `kill_switch`
- `replacement_target`
- `sunset_phase`

Canonical source-of-truth rule:
- plugin/module lifecycle state must be persisted in a control-plane record, not inferred from autodiscovery, importability, or incidental router registration.

## Activation Prerequisites

Before a module/plugin is `stable`:
- canonical path is defined
- auth surface is documented
- audit policy is defined
- event contract is defined
- registry/control-plane ownership is clear
- compatibility and decommission plan exists if replacing legacy behavior

## Deprecation Rules

- deprecated modules may remain readable or adapter-backed
- new write paths must not target deprecated modules
- sunset phase and replacement target must be documented

Route ownership rule:
- for any runtime object, exactly one module/plugin may be canonical write owner at a time
- competing legacy/app/autodiscovered write routes must be disabled, adapter-backed, or made read-only

## Decommission Matrix

Every retiring module/plugin needs:
- successor or explicit retirement reason
- migration boundary
- kill switch strategy
- remaining active routes inventory
- data ownership confirmation

## API Surface

- `GET /api/v1/module-lifecycle`
- `GET /api/v1/module-lifecycle/{module_id}`
- `POST /api/v1/module-lifecycle/{module_id}/deprecate`
- `POST /api/v1/module-lifecycle/{module_id}/retire`

## Audit and Event Requirements

- `module.lifecycle.deprecated.v1`
- `module.lifecycle.retired.v1`
- `module.lifecycle.kill_switch.enabled.v1`
- `module.lifecycle.adapter.bound.v1`

Durable audit required for all lifecycle transitions.

## PostgreSQL vs Redis vs EventStream

### PostgreSQL
- canonical lifecycle records
- decommission matrix records

### Redis
- transient kill switch cache

### EventStream
- lifecycle transition notifications

## Legacy Compatibility

- Legacy modules remain behind compatibility boundaries only.
- `backend/modules/*` must not expand.
- Existing standby/autodiscovery ambiguity must be replaced by explicit lifecycle state.

Event compatibility rule:
- legacy unversioned lifecycle events may be mirrored during migration, but the target state uses versioned `.v1` contracts.

## Done Criteria

- architecture classification and lifecycle are separated
- activation prerequisites are explicit
- decommission matrix is required
- legacy and replacement boundaries are documented

## Implementation Status

- `backend/app/modules/module_lifecycle/` now provides the lifecycle control-plane baseline
- `course_factory` and `webgenesis` write paths consult lifecycle state and block deprecated/retired write ownership in normal runtime paths
- lifecycle state is now explicit persisted control-plane data instead of implicit autodiscovery/import state
- builder and RC-gate verification passed after lifecycle integration
- lifecycle transitions are now validated so invalid backward moves are rejected and `replacement_target` is enforced for deprecated/retired state
- decommission-matrix readout is exposed through the module lifecycle API for control-plane review
- targeted lifecycle tests now cover transition rules, filtered listing, decommission matrix reads, and builder write-blocking behavior
