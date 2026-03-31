# Cognitive Assessment Service

Status: Proposed -> implementation-aligned v1
Date: 2026-03-31

## Purpose

`cognitive_assessment` adds a bounded decision-preparation service between
normalized input and final routing/execution. It does not replace `SkillRun`,
policy, or governance. It produces advisory signals that improve perception,
association, and evaluation before routing.

## Merge guardrails

- advisory-only is mandatory
- no implicit routing control
- no second routing system
- governor/policy remain the only authoritative decision surface
- `CognitiveAssessmentResult` is the stable, versioned context object for downstream propagation

## Non-goals

- no biological brain simulation
- no second runtime object beside `SkillRun`
- no second policy or governor system
- no free autonomous self-modification
- no mandatory multimodal perception in v1

## Runtime placement

Target path:

`Intent -> DecisionContext -> CognitiveAssessment -> Routing/Intent Resolution -> Policy -> SkillRun`

Learning path:

`SkillRun -> EvaluationResult -> ExperienceRecord -> CognitiveLearningFeedback`

## v1 contracts

### CognitiveAssessmentRequest

- `intent_text`
- `problem_statement`
- `source_url`
- `mission_id`
- `context`
- `min_confidence`

### CognitiveAssessmentResponse

- `assessment_id`
- `normalized_intent`
- `perception`
- `association`
- `evaluation`
- `result`
- `recommended_skill_candidates`
- `governance_hints`

### CognitiveAssessmentResult

- `result_version`
- `confidence`
- `risk`
- `impact`
- `novelty`
- `governance_flags`
- `routing_hint` (reserved, not active in v1)

### LearningFeedbackRecord

- `assessment_id`
- `skill_run_id`
- `evaluation_result_id`
- `experience_record_id`
- `outcome_state`
- `overall_score`
- `success`

## v1 capabilities

1. normalize and score the input (`perception`)
2. retrieve similar experience and knowledge (`association`)
3. derive novelty / impact / risk / confidence (`evaluation`)
4. recommend ranked skill candidates (`handoff`)
5. update bounded learning feedback after execution (`learning_update`)

## Boundaries

- `Skill Engine`: owns execution and `SkillRun`
- `Policy / Governor`: remain binding allow/deny/audit surface
- `Memory / Knowledge`: remain system-of-record for retrieval, not duplicated
- `DNA / Evolution`: consume downstream learning artifacts only
- `Neural Core`: remains runtime parameter/synapse manager, not this service

## Storage

- `cognitive_assessments`
- `cognitive_learning_feedback`

Both tables are durable, auditable, and tenant-bounded.

## Rollout

- feature-flag capable
- advisory-only in v1
- first integrated into `intent_to_skill`
- surfaced in ControlDeck and AXE before broader routing adoption

## Follow-up ticket

Create directly after merge:

- `feat(audit): add full provenance chain for cognitive assessment`

Target chain:

`session_id -> agent_id -> assessment_id -> intent_id -> skill_run_id -> outcome_id -> feedback_event_id`
