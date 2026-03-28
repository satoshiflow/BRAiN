# Canonical Identity Contract (v1)

Status: Draft (Phase 1 Sprint 1.1)

## Purpose

Define the durable, machine-readable identity and operating intent for BRAiN so
that purpose/routing/governance decisions resolve against one canonical source.

## Contract Fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `version` | string | yes | Contract version, e.g. `1.0` |
| `identity_statement` | string | yes | Canonical identity text |
| `operational_purpose` | string | yes | Mission-operational intent |
| `autonomy_mode_default` | enum | yes | `brain_first` |
| `human_control_policy` | enum | yes | `optional_by_policy` |
| `non_negotiable_constraints` | string[] | yes | Hard invariants |
| `source_precedence` | string[] | yes | Ordered source list |
| `updated_by` | string | yes | Principal/actor id |
| `updated_at` | timestamptz | yes | UTC |

### Enum Notes

- `autonomy_mode_default`: `brain_first`
- `human_control_policy`: `optional_by_policy`, `required_for_sensitive_or_promotion`

## Validation Rules

- `autonomy_mode_default` must be `brain_first` unless explicit governance
  migration is approved.
- `non_negotiable_constraints` must include:
  - `skillrun_is_canonical_execution_record`
  - `governance_precedes_sensitive_execution`
  - `opencode_is_bounded_execution_plane`
  - `sandbox_first_for_self_improvement`
  - `axe_is_human_brain_interface`
- `source_precedence` must include `AGENTS.md` and `DESIGN.md` at the top.

## Lifecycle

`draft -> approved -> active -> superseded`

Rules:
- exactly one active canonical identity contract at a time
- activation requires governance review record and audit event

## Error Codes

- `CI-001 INVALID_MODE`
- `CI-002 MISSING_REQUIRED_CONSTRAINT`
- `CI-003 INVALID_SOURCE_PRECEDENCE`
- `CI-004 ILLEGAL_STATE_TRANSITION`
- `CI-005 GOVERNANCE_APPROVAL_REQUIRED`

## Minimal API Structure

- `GET /api/v1/governance/canonical-identity/active`
- `POST /api/v1/governance/canonical-identity` (create draft)
- `POST /api/v1/governance/canonical-identity/{version}/approve`
- `POST /api/v1/governance/canonical-identity/{version}/activate`

Mutating endpoints require auth + governance role + audit.

## Event Types

- `identity.contract.created.v1`
- `identity.contract.approved.v1`
- `identity.contract.activated.v1`
- `identity.contract.superseded.v1`

## Storage

- PostgreSQL: canonical contract versions and activation history
- Redis: optional read cache only
- EventStream: lifecycle and governance events
