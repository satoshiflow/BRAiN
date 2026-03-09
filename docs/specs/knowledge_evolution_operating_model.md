# Knowledge and Evolution Operating Model

Version: 1.0  
Status: Active modeling draft (post Epic 12 hardening)

---

## 1 What we have today

Current runtime foundation is strong and mostly aligned:

- `SkillRun` is the canonical execution truth.
- `memory` stores contextual and episodic traces (`skill_run_id` is now anchored).
- `learning` stores metrics/strategy outcomes (`skill_run_id` ingest path exists).
- `knowledge_layer` stores curated durable knowledge with provenance.
- `module_lifecycle` can block writes for deprecated/retired modules.
- builder flows (`course_factory`, `webgenesis`) are wrapped around canonical skill execution.

This is already enough to run a governed execution platform with traceability.

---

## 2 Architecture idea we are following

We are not building "one memory".

We are building a staged learning pipeline:

`Execution -> Experience -> Insight -> Knowledge -> Skill Evolution`

Why this matters:

- execution data is noisy and local
- knowledge must be curated and stable
- evolution must be stricter than learning

So each stage has a different job and different governance strictness.

---

## 3 Problem this model solves

Without staged layers, systems usually fail in one of two ways:

- they stay reactive and forgetful (only logs, no durable learning)
- or they overfit noise into permanent behavior (unsafe auto-evolution)

BRAiN should avoid both by separating:

- **Experience** (what happened)
- **Insight** (what it might mean)
- **Knowledge** (what is validated enough to keep)
- **Evolution** (what is strong enough to change future skills)

---

## 4 How the system should work (simple flow)

1. `SkillRun` finishes (success/failure, cost, policy, telemetry).
2. One canonical `ExperienceRecord` is created.
3. Insight extraction creates `InsightCandidate` entries from experiences.
4. Repeated insights become `PatternCandidate` entries.
5. Only promoted patterns create `EvolutionProposal` items.
6. Evolution proposals run validation and can update `skills_registry` versioning.

Design constraint:

- no stage may bypass the previous stage
- no direct jump from raw run output to automatic skill mutation

---

## 5 Use-case thought tests

### Use case A: repeated deployment drift

- Situation: deploy runs still succeed but cost drifts upward.
- Expected flow: `SkillRun` -> `ExperienceRecord` -> cost insight -> cost pattern -> evolution proposal to tighten strategy.
- Resilience test: if learning module is deprecated, execution continues; evolution is paused safely.

### Use case B: incident delegation under pressure

- Situation: agent delegates recovery repeatedly.
- Expected flow: delegation run outcomes form experiences, recurring failure mode becomes pattern, pattern drives supervised fallback strategy update.
- Resilience test: if knowledge write path is blocked, no partial promotion occurs.

### Use case C: noisy one-off failures

- Situation: single connector outage causes two failed runs.
- Expected flow: experiences exist, low-confidence insight exists, but no pattern promotion.
- Resilience test: system does not overreact into permanent skill mutation.

### Use case D: high-confidence best practice

- Situation: one mitigation repeatedly improves success and cost.
- Expected flow: pattern reaches promotion threshold, creates evolution proposal, validates against guardrails, then promotes to new skill version.
- Resilience test: rollback remains possible if validation drift appears later.

---

## 6 Is it resilient enough today?

Partly yes:

- runtime and governance are increasingly stable (`SkillRun`, lifecycle write-blocking, RC gate discipline)
- tracing and ingest surfaces exist

Not yet fully:

- `ExperienceRecord`, `InsightCandidate`, `PatternCandidate`, `EvolutionProposal` are not yet first-class runtime modules
- ingestion is still mostly endpoint-driven, not one canonical post-run consolidation pipeline
- mission/knowledge/evolution semantics are documented but only partially materialized in durable contracts

---

## 7 What is missing right now

Minimal missing module set:

- `experience_layer` (durable post-run bridge)
- `insight_layer` (candidate derivation + validation state)
- `pattern_layer` (repeatability and support counts)
- `evolution_control` (proposal, validation run, promotion/rollback)

Minimal missing process:

- one deterministic post-run consolidation worker:
  - input: `skill_run_id`
  - output: experience + optional insight/pattern updates

---

## 8 Is it too complicated?

It can become too complicated if we model every layer at once.

Rule: genius stays simple.

Keep only one new durable object per step:

Step 1: add `ExperienceRecord` only  
Step 2: add `InsightCandidate` only  
Step 3: add `PatternCandidate` only  
Step 4: add `EvolutionProposal` only

Each step must be independently testable and reversible.

---

## 9 Next implementation slice (recommended)

### Slice E1 - Experience first

- new module: `backend/app/modules/experience_layer/`
- table: `experience_records`
- API:
  - `POST /api/experience/skill-runs/{run_id}/ingest`
  - `GET /api/experience/{experience_id}`
  - `GET /api/experience/skill-runs/{run_id}`
- write guard integrated with `module_lifecycle`
- tests: ingestion success, idempotency, tenant isolation, lifecycle blocking

Done when:

- every relevant completed `SkillRun` can produce exactly one durable experience record
- no direct pattern/evolution logic exists yet

This keeps the architecture simple while opening the path for deeper learning and evolution.
