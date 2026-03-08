# Mission Deliberation and Insight Evolution

Version: 1.0
Status: Active Architecture Strand
Purpose: Define the minimal extension path from execution-only orchestration toward mission-centered deliberation, insight consolidation, and governed capability evolution.

---

## 1 Problem Statement

Modern agent systems are usually optimized for execution, not for durable insight formation.

They can:
- plan
- call tools
- execute skills
- store logs or vectors

But they usually lack an explicit transformation path from:

`experience -> insight -> pattern -> knowledge -> skill evolution`

BRAiN should solve this as a first-class architecture concern.

---

## 2 Target Layering

BRAiN should evolve around four connected layers.

### Layer A - Execution

Canonical execution artifacts:
- `Capability`
- `Skill`
- `SkillRun`

This layer answers:
- what can BRAiN do?
- what exactly ran?

### Layer B - Mission Deliberation

Mission is more than a request container.

Long-term mission artifacts:
- `MissionHypothesis`
- `MissionPerspective`
- `MissionTension`
- `DecisionRecord`
- `DeliberationSummary`

This layer answers:
- what competing explanations or strategies existed?
- what risks and tensions shaped the decision?
- what remained unresolved?

### Layer C - Knowledge Consolidation

This layer converts runtime and deliberation into durable, curated learning artifacts.

Core artifacts:
- `ExperienceRecord`
- `InsightCandidate`
- `PatternCandidate`
- `KnowledgePromotionRecord`

This layer answers:
- what was learned?
- what recurs often enough to matter?
- what is validated enough to promote?

### Layer D - Meta-Cognition and Evolution

This layer decides whether learning should change future behavior.

Core artifacts:
- `EvolutionProposal`
- `ValidationRun`
- `PromotionDecision`
- `RollbackDecision`

This layer answers:
- should this insight affect future skills?
- should a pattern be promoted or rejected?
- is the system improving or drifting?

---

## 3 Core Transform Path

The long-term BRAiN learning path should be:

`Tension -> Deliberation -> Decision -> Distillation -> Validation -> Knowledge`

And later, in controlled cases:

`Knowledge -> PatternCandidate -> EvolutionProposal -> Skill Evolution`

Notes:
- not every execution generates durable knowledge
- not every insight becomes a pattern
- not every pattern causes evolution
- all promotions must be governed and auditable

---

## 4 Architectural Principles

### 4.1 Execution stays canonical

`SkillRun` remains the canonical execution record.

Mission deliberation and insight extraction must not create a parallel runtime.

### 4.2 Tensions are first-class

Competing hypotheses, unresolved contradictions, and risk-vs-goal conflicts should remain visible.

Do not prematurely collapse all tension into one answer.

### 4.3 Compression must be structured

Do not persist raw chain-of-thought as durable truth.

Persist only bounded, structured summaries with provenance and governance.

### 4.4 Knowledge is curated

Knowledge must be:
- versioned
- provenance-backed
- validated
- supersedable

### 4.5 Evolution is stricter than learning

Learning may create insight candidates.

Evolution requires:
- evidence
- validation
- governance
- rollback path

---

## 5 Minimal Viable Extension

The smallest useful architecture addition is not a full deliberation graph.

It is a thin consolidation layer with three new durable objects.

### 5.1 ExperienceRecord

Purpose:
- canonical bridge from execution and mission context into later insight formation

Minimal fields:
- `experience_id`
- `tenant_id`
- `mission_id`
- `task_id`
- `skill_run_id`
- `correlation_id`
- `agent_id`
- `status`
- `outcome_summary`
- `artifact_refs`
- `memory_refs`
- `evaluation_refs`
- `audit_refs`
- `created_at`

### 5.2 InsightCandidate

Purpose:
- one derived lesson, observation, or decision-relevant insight from one or more experiences

Minimal fields:
- `insight_id`
- `tenant_id`
- `experience_refs`
- `statement`
- `confidence`
- `scope`
- `evidence_refs`
- `validation_state`
- `created_at`

### 5.3 PatternCandidate

Purpose:
- repeated, aggregated insight with reuse potential

Minimal fields:
- `pattern_id`
- `tenant_id`
- `insight_refs`
- `pattern_statement`
- `support_count`
- `failure_modes`
- `confidence`
- `promotion_state`
- `created_at`

---

## 6 Future Deliberation Objects

These do not need to be implemented immediately, but the architecture should leave room for them.

### MissionHypothesis
- candidate explanation or strategy

### MissionPerspective
- bounded viewpoint from one agent, reviewer, policy frame, or evidence source

### MissionTension
- unresolved contradiction, tradeoff, or conflict between hypotheses, risks, or goals

### DecisionRecord
- reasoned reduction from many alternatives to one chosen path, preserving rejected alternatives and remaining uncertainty

### DeliberationSummary
- bounded structured summary of the mission thinking state suitable for later compression and audit

---

## 7 Selection and Promotion Mechanisms

Long-term, BRAiN will need explicit selection to decide what becomes durable.

Possible selection signals:
- evaluation quality
- repeatability
- success rate
- policy safety
- cost efficiency
- human review
- credit cost
- karma/reputation
- tenant/domain fit

Important:
- no single signal should decide promotion alone
- credits may contribute, but must not become the only gate
- reputation/karma without provenance is insufficient

---

## 8 Relationship to Credits, Karma, and Governance

### Credits
- useful as resource/cost signal
- not sufficient alone for promotion decisions

### Karma / Reputation
- useful as quality/trust signal
- must become durable, explainable, and anti-gaming-aware before acting as a strong promotion input

### Governance
- required for:
  - promotion to stable knowledge
  - promotion to active skill evolution
  - risky or cross-tenant learning effects

---

## 9 Minimal Build Path

### Stage 1
- complete `SkillRun` runtime spine
- anchor execution history cleanly

### Stage 2
- add `ExperienceRecord`
- wire from `SkillRun`, mission bridge, task queue, evaluation, and memory

### Stage 3
- add `InsightCandidate`
- create bounded distillation flow from experience to insight

### Stage 4
- add `PatternCandidate`
- aggregate recurring insight candidates

### Stage 5
- connect validated pattern promotion into Knowledge Layer

### Stage 6
- introduce governed `EvolutionProposal` for skill evolution

---

## 10 Expected Outcome

If BRAiN follows this strand, it will not only orchestrate actions.

It will be able to:
- preserve productive tensions
- distill decisions into insights
- turn repeated insights into reusable patterns
- promote validated patterns into knowledge
- eventually improve skills from knowledge under governance

This is the bridge from execution competence to genuine system learning.
