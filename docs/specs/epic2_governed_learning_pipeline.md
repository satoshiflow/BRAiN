# Epic 2 Governed Learning Pipeline

Status: Active
Date: 2026-03-22

## Goal

Create promotion candidates from canonical run outcomes while keeping mutation proposal-only and governance-gated.

## Source of truth

- `SkillRun` (runtime execution anchor)
- `EvaluationResult` (canonical quality/compliance signal)
- `ExperienceRecord` (durable operational lesson)
- `PatternCandidate` (consolidation output)
- `EvolutionProposal` (governed promotion candidate)

## Pipeline

1. Observation captured from `SkillRun`
2. Evaluation checked from latest `EvaluationResult`
3. Validation gate applies:
   - status must be `completed`
   - `passed == true`
   - `policy_compliance == compliant`
4. Pattern derivation through consolidation layer
5. Proposal created in evolution control
6. Promotion decision recorded (proposal-only)

## Blocking rules

- Non-compliant, non-passed, or non-completed evaluation blocks promotion.
- Blocked proposals are stored with:
  - `status = rejected`
  - `validation_state = blocked`
  - `proposal_metadata.block_reason`

## Proposal-only guarantee

- Successful candidates are moved to `review` and `validation_state=validated`.
- No direct apply is performed in this phase.
- Governance evidence is still required before any future `applied` transition.

## Event flow

- `learning.observation.captured.v1`
- `learning.evaluation.checked.v1`
- `learning.validation.completed.v1`
- `learning.promotion.decided.v1`

All events are emitted from persistence-near service paths.
