# Discovery Layer MVP Contract

Status: Active
Date: 2026-03-09

## Scope

Discovery remains proposal-only. It does not mutate active skills, policies, or runtime state.

## Contracts

- `SkillGap`
  - Fields: `id`, `tenant_id`, `skill_run_id`, `pattern_id`, `gap_type`, `summary`, `severity`, `confidence`, `evidence`, `created_at`
- `CapabilityGap`
  - Fields: `id`, `tenant_id`, `skill_run_id`, `pattern_id`, `capability_key`, `summary`, `severity`, `confidence`, `evidence`, `created_at`
- `SkillProposal`
  - Fields: `id`, `tenant_id`, `skill_run_id`, `pattern_id`, `skill_gap_id`, `capability_gap_id`, `target_skill_key`, `status`, `proposal_summary`, `proposal_evidence`, `dedup_key`, `evidence_score`, `priority_score`, `created_at`, `updated_at`
- `ProposalEvidence`
  - Fields: `evidence_sources`, `observer_signal_count`, `knowledge_item_count`, `thresholds`, `evidence_score`

## Threshold Rules

- `min_pattern_confidence >= 0.55`
- `min_recurrence_support >= 0.45`
- `min_observer_signals >= 1`
- `min_knowledge_items >= 1`

If thresholds are not met, discovery analyze returns `422`.

## APIs

- `POST /api/discovery/skill-runs/{skill_run_id}/analyze`
- `GET /api/discovery/proposals`
- `GET /api/discovery/proposals/{proposal_id}`
- `POST /api/discovery/proposals/{proposal_id}/queue-review`

## Auth / Role / Scope Matrix

- Analyze: `operator | admin | SYSTEM_ADMIN`
- List/Get: authenticated principal with tenant context
- Queue review: `admin | SYSTEM_ADMIN`

## Safety and Governance

- Tenant context mandatory for all endpoints (`403` on missing tenant)
- Lifecycle write guard for mutating paths (`409` on `deprecated|retired`)
- Review handoff blocked if `evolution_control` is not writable (`409`)
- Dedup contract: unique `(tenant_id, dedup_key)` and `(tenant_id, skill_run_id)`

## Storage Ownership

- PostgreSQL: `skill_gaps`, `capability_gaps`, `discovery_skill_proposals`
- Redis/EventStream: no direct mutation publishing in MVP (proposal-only path)
