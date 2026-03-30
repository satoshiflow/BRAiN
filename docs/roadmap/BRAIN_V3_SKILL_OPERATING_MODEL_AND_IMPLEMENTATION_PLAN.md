# BRAiN v3 Skill Operating Model and Implementation Plan

Status: Proposed canonical implementation package
Date: 2026-03-30
Owner: OpenCode (project lead + senior dev package for implementation handoff)

Decision Update (2026-03-30, superseding earlier draft assumptions):
- Obsidian and external markdown vault workflows are removed from the implementation scope.
- BRAiN now uses a native Knowledge Engine (`backend/app/modules/knowledge_engine/`) as the primary knowledge infrastructure.
- Human-readable knowledge UX is implemented directly in ControlDeck (`/knowledge`).

## 1. Purpose

This document defines the target operating model for skills in BRAiN v3 and turns the current repo state into a concrete execution plan.

It covers:

- the roles of AXE UI, ControlDeck v3, backend runtime, and Neural Core
- the canonical skill taxonomy and lifecycle
- the migration path from the current mixed implementation to a governed BRAiN v3 model
- the value/refinancing model for skills
- the knowledge architecture using PostgreSQL with a native BRAiN Knowledge Engine and human-facing ControlDeck knowledge UX
- a detailed junior-dev execution package

This document intentionally combines architecture, delivery planning, and implementation instructions because the current system already contains most of the primitives, but they are not yet aligned into one coherent product surface.

---

## 2. Executive Summary

BRAiN already contains the core technical ingredients for a strong skill platform:

- governed `SkillRun` runtime in `backend/app/modules/skill_engine/`
- canonical `SkillDefinition` registry in `backend/app/modules/skills_registry/`
- evaluation via `backend/app/modules/skill_evaluator/`
- learning, experience, knowledge, discovery, and economy support modules
- AXE chat bridge defaulting to `skillrun_bridge`
- an initial ControlDeck v3 skill page

However, the system is still fragmented:

- there is still a legacy/direct `skills` module beside the governed registry/runtime path
- ControlDeck v3 skill UI is not aligned with the backend contracts
- there is no unified skill value model for ROI, effort saved, people-equivalent, or pricing
- there is no deep curated human-readable knowledge space for skills and accumulated BRAiN knowledge
- there is no marketplace-ready lifecycle even though major prerequisites exist

The target model in this document is:

1. `SkillRun` remains the only canonical execution truth.
2. `skills_registry` becomes the only canonical definition catalog.
3. AXE becomes the primary intent frontdoor.
4. ControlDeck v3 becomes the governance, catalog, analytics, and economy surface.
5. BRAiN Knowledge Engine becomes the native knowledge plane for skills and all BRAiN knowledge.
6. Value scoring precedes monetization.
7. Marketplace/refinancing is a later layer on top of value, governance, and lifecycle.

---

## 3. Current System Inventory

### 3.1 What already exists in the backend

#### Canonical and strategic surfaces

- `backend/app/modules/skills_registry/`
  - canonical skill definition catalog
  - versioning, activation, deprecation, deterministic resolution
- `backend/app/modules/skill_engine/`
  - canonical governed runtime via `SkillRun`
  - planning, execution, approval, cancel, evaluation handoff
- `backend/app/modules/skill_evaluator/`
  - evaluation results per skill run
- `backend/app/modules/experience_layer/`
  - durable experience capture from runs
- `backend/app/modules/knowledge_layer/`
  - durable knowledge items with provenance back to runs/experience/evaluation
- `backend/app/modules/insight_layer/`
  - derives bounded insight from experience
- `backend/app/modules/discovery_layer/`
  - detects gaps and proposes future skills/capabilities
- `backend/app/modules/economy_layer/`
  - scoring support for prioritization using confidence/frequency/impact/cost
- `backend/app/modules/learning/`
  - strategy/experiment/metric support
- `backend/app/modules/axe_fusion/`
  - AXE frontdoor with `skillrun_bridge` default
- `backend/app/neural/`
  - Brain 3.0 Neural Core with synapses such as `skill_execute` and `skill_list`

#### Legacy or conflicting surfaces

- `backend/app/modules/skills/`
  - legacy/direct CRUD and direct execution model
  - built-ins and handler path based execution
- `backend/api/routes/skills.py`
  - parallel legacy route implementation

#### Important architectural fact

`backend/main.py` mounts `skills_registry` and `skill_engine`, which means the governed path is already the strategic runtime direction. The legacy `skills` implementation still exists in the repo and still influences mental models and some frontend assumptions.

### 3.2 What already exists in the frontend

#### AXE UI

- AXE UI already acts as the primary execution-oriented user surface.
- It contains AXE run handling and domain-specific skill surfaces such as the Odoo skill page.
- It does not currently expose a general-purpose skill catalog/governance surface.

#### ControlDeck v3

- There is already a dedicated protected page for skills:
  - `frontend/controldeck-v3/src/app/(protected)/skills/page.tsx`
- There is an API client:
  - `frontend/controldeck-v3/src/lib/api/skills.ts`
- But the page and client are not yet aligned to the actual backend contract.

### 3.3 Current mismatch summary

The current gap is not a lack of architecture. It is a lack of integration and alignment.

Main mismatches:

- frontend expects arrays where backend returns paginated wrappers
- frontend trigger flow does not satisfy `SkillRunCreate` contract requirements
- frontend assumes retry/cancel endpoints that do not match backend behavior
- frontend skill object shape does not match registry response shape
- pricing, value, ROI, and marketplace concepts are not yet modeled into the actual skill surfaces
- Obsidian integration does not exist yet

---

## 4. Permanent Architecture Principles

These principles are binding for this initiative.

### 4.1 Skill vs module decision rule

Use this rule permanently:

> Everything that describes behavior, strategy, or work style should be modeled as a skill by default. Everything that provides stability, security, persistence, governance, routing, or observability remains a module/core service.

Examples:

#### Module/Core Service

- auth and identity
- policy engine
- audit
- registry
- memory/knowledge storage
- task queue
- telemetry
- pricing/value computation
- marketplace billing
- Obsidian sync/export

#### Skill

- brainstorming
- feature development
- structured debugging
- TDD implementation
- hardening review
- migration delivery
- incident response
- skill creator

### 4.2 Runtime truth rule

- `SkillRun` remains the only canonical execution truth.
- No skill work may bypass `SkillRun`.
- Neural Core may route or parameterize execution, but not replace `SkillRun` as runtime truth.

### 4.3 Knowledge truth rule

- PostgreSQL remains the canonical runtime and governance source of truth.
- Obsidian becomes the curated deep knowledge layer for human understanding, documentation, pattern extraction, architecture memory, and strategy iteration.
- Obsidian does not replace runtime truth.

### 4.4 Economy rule

- Pricing cannot be based only on token cost.
- Value must include time saved, complexity removed, quality improvement, and risk reduction.
- Marketplace comes after scoring, governance, and lifecycle discipline.

---

## 5. Target Operating Model

### 5.1 AXE UI role

AXE is the operational intent frontdoor.

AXE owns:

- user intent intake
- chat-based execution entry
- URL/problem/feature/bug intake
- guided skill invocation
- live execution feedback
- lightweight task-focused controls

AXE does not own:

- catalog governance
- version lifecycle
- monetization governance
- deep skill analytics
- promotion/deprecation workflows

### 5.2 ControlDeck v3 role

ControlDeck v3 is the governance and control plane for skills.

ControlDeck owns:

- skill catalog and search
- skill definition review and lifecycle transitions
- skill run monitoring and triage
- evaluation, experience, knowledge, discovery, and economy dashboards
- value score and pricing visibility
- promotion/deprecation
- private/public/premium status administration
- Obsidian-linked knowledge browsing

ControlDeck does not own:

- conversational intake
- direct chat-style user interaction as the primary frontdoor

### 5.3 Backend role

The backend provides:

- `skills_registry` as the canonical definition plane
- `skill_engine` as the canonical execution plane
- `skill_evaluator` as evaluation plane
- `experience_layer`, `knowledge_layer`, `insight_layer`, `discovery_layer` as learning plane
- `economy_layer` and future value engine as prioritization/value plane
- future marketplace/billing modules as economy plane
- future Obsidian sync module as knowledge export plane

### 5.4 Neural Core role

Neural Core remains:

- parameter/state manager
- synapse routing layer
- dynamic execution weighting layer

Neural Core must not become a second skill runtime.

---

## 6. Skill Taxonomy

### 6.1 Capabilities

Atomic abilities provided by modules/adapters.

Examples:

- file read
- file write
- diff analyze
- run tests
- fetch URL
- query backend health
- restart container
- execute SQL safely

### 6.2 Atomic Skills

Small reusable behavioral blocks built on capabilities.

Examples:

- `repo_analysis_skill`
- `test_authoring_skill`
- `api_contract_check_skill`
- `log_diagnosis_skill`

### 6.3 Composite Skills

Reusable multi-step workflows.

Examples:

- `tdd_implementation_skill`
- `structured_debugging_skill`
- `hardening_review_skill`
- `benchmark_evaluation_skill`

### 6.4 Mission Skills

End-to-end delivery workflows.

Examples:

- `feature_dev_skill`
- `migration_delivery_skill`
- `incident_recovery_skill`
- `integration_rollout_skill`

### 6.5 Meta Skills

Skills that select, compose, generate, or improve other skills.

Examples:

- `intent_to_skill`
- `skill_creator_skill`
- `skill_optimizer_skill`
- `skill_packaging_skill`

### 6.6 Skill origin taxonomy

Every skill must carry an origin.

- `native`
- `brain_generated`
- `user_defined`
- `external_imported`
- `premium`

---

## 7. Canonical Skill Lifecycle

### 7.1 Lifecycle states

Skill definition lifecycle:

- `draft`
- `review`
- `approved`
- `active`
- `deprecated`
- `retired`
- `rejected`

Skill commercialization lifecycle extension:

- `trusted`
- `verified`
- `premium_candidate`
- `premium_active`
- `premium_suspended`

These commercialization states should be added as governance/economy metadata first, not as a replacement for the canonical definition status machine.

### 7.2 Operational lifecycle flow

```text
Create -> Register -> Execute -> Evaluate -> Learn -> Promote -> Monetize
```

### 7.3 Lifecycle meaning

- `Create`
  - seed, import, user creation, auto-generation from intent
- `Register`
  - persist definition in registry with versioned contract
- `Execute`
  - one or more `SkillRun`s
- `Evaluate`
  - quality, robustness, cost, policy compliance, outcome
- `Learn`
  - experience, insight, patterns, knowledge
- `Promote`
  - trust and marketplace readiness decisions
- `Monetize`
  - value-aware pricing and optional external distribution

---

## 8. Canonical Data Model Extensions

### 8.1 Existing strong foundations

Already present:

- `SkillDefinitionModel`
- `SkillRunModel`
- `EvaluationResultModel`
- `ExperienceRecordModel`
- `KnowledgeItemModel`
- `SkillProposalModel`
- `EconomyAssessmentModel`

### 8.2 Missing skill business metadata

We need a new extension model, recommended as a separate table rather than bloating `skill_definitions` immediately.

Recommended new table: `skill_value_profiles`

Suggested fields:

- `id`
- `skill_definition_id`
- `tenant_id`
- `origin`
- `category_family`
- `value_status` (`draft`, `measured`, `trusted`, `verified`, `premium_candidate`, `premium_active`)
- `time_saved_hours_estimate`
- `people_equivalent_estimate`
- `quality_improvement_score`
- `risk_reduction_score`
- `complexity_reduction_score`
- `reuse_rate`
- `run_count`
- `success_rate`
- `avg_execution_cost`
- `value_score`
- `roi_score`
- `price_floor_credits`
- `price_recommended_credits`
- `price_ceiling_credits`
- `market_visibility` (`private`, `tenant`, `internal_catalog`, `marketplace`)
- `pricing_model` (`free`, `credits_per_run`, `subscription_pack`, `premium_fixed`, `revenue_share`)
- `pricing_notes`
- `evidence_refs`
- `created_at`
- `updated_at`

### 8.3 Missing skill knowledge model

Recommended new table: `skill_knowledge_links`

Purpose:

- link skill definitions and value profiles to curated Obsidian knowledge artifacts
- keep knowledge refs stable while markdown files evolve

Suggested fields:

- `id`
- `skill_definition_id`
- `tenant_id`
- `knowledge_type` (`spec`, `runbook`, `pattern`, `lessons_learned`, `business_case`, `pricing_case`, `architecture_note`)
- `obsidian_path`
- `vault_namespace`
- `frontmatter_snapshot`
- `linked_knowledge_item_id`
- `linked_experience_record_id`
- `linked_evaluation_result_id`
- `created_at`
- `updated_at`

### 8.4 Missing intent-entry model

Recommended new table later: `intent_requests`

Purpose:

- store URL/text/problem inputs that later become skill generation or skill orchestration jobs

This is phase-later and not phase-one critical.

---

## 9. Value System and Refinancing Model

### 9.1 Why token-cost-only is insufficient

Token cost measures compute spend, not delivered value.

Two skills can cost the same but create radically different value.

Examples:

- one skill saves 10 minutes
- another skill prevents a production outage or saves five developer-days

Therefore BRAiN needs a dual model:

- `execution_cost`
- `delivered_value`

### 9.2 Core value dimensions

Every important skill should be assessed along these dimensions:

- `time_saved_hours`
- `people_equivalent`
- `quality_gain`
- `risk_reduction`
- `complexity_reduction`
- `reuse_rate`
- `success_rate`
- `execution_cost`

### 9.3 Proposed first value score formula

Start simple and transparent.

```text
value_score =
  (time_saved_hours_normalized * 0.30)
  + (people_equivalent_normalized * 0.20)
  + (quality_gain * 0.15)
  + (risk_reduction * 0.15)
  + (complexity_reduction * 0.10)
  + (reuse_rate * 0.05)
  + (success_rate * 0.05)
```

Then derive:

```text
roi_score = value_score / max(execution_cost_normalized, 0.05)
```

The exact normalization constants should be configurable in a value-engine config table.

### 9.4 First commercial interpretation

Examples:

- saves 5 days of work
- replaces 3 repeated specialist actions
- reduces failure probability in a high-risk area
- turns a 2-hour diagnosis into a 5-minute diagnosis

These should be visible in ControlDeck as plain-language business statements, not just raw numbers.

### 9.5 Monetization model sequence

#### Phase A - internal value visibility

- no external marketplace yet
- expose cost, value score, ROI score, and effort saved

#### Phase B - credit pricing

- internal credits per run
- recommended credit price based on value score and execution cost

#### Phase C - premium catalog

- selected trusted/verified skills become premium-capable
- tenant-local or platform-global listing

#### Phase D - marketplace

- revenue split
- publisher profile
- private/public listing
- premium packs

---

## 10. Obsidian Knowledge Architecture

### 10.1 Purpose of Obsidian in BRAiN

Obsidian is introduced as the curated human-readable knowledge environment for BRAiN.

It will store not just skills, but the whole curated knowledge layer around BRAiN:

- skill specifications
- architecture decisions
- business cases
- lessons learned
- runbooks
- reports
- patterns
- domain knowledge
- problem/solution catalogs
- visual maps using Excalidraw

### 10.2 Truth boundary

- PostgreSQL = canonical runtime truth
- Obsidian = curated knowledge truth for humans and agentic recall/reconstruction

Obsidian is not the runtime registry and does not replace policy/audit/runtime records.

### 10.3 Recommended initial vault structure

This must stay expandable and support subfolders.

```text
obsidian-vault/
  00 Kontext/
    Architektur/
    ADR/
    Leitprinzipien/
    Systeme/

  01 Inbox/
    Rohideen/
    Importe/
    Zu_pruefen/

  02 Projekte/
    Skills/
    Frontend/
    Backend/
    Integrationen/
    Marketplace/

  03 Berichte/
    Weekly/
    Monthly/
    RC_Gates/
    Reviews/
    Retro/

  04 Ressourcen/
    Referenzen/
    Links/
    Frameworks/
    APIs/

  05 Daily Notes/

  06 Archiv/

  07 Anhaenge/
    Bilder/
    PDFs/
    Exporte/

  08 Excalidraw/
    Architektur/
    Flows/
    SkillMaps/

  10 Wissen/
    Branche/
    Problem/
    Loesung/
    Situation/
    Pattern/
    Failure/
    Opportunity/
    Skill_Katalog/
    Skill_Runs/
    Skill_Lifecycle/
    Value_und_Pricing/
```

This structure must be implemented as a seeded, extensible baseline only. It must not assume final taxonomy completeness.

### 10.4 Obsidian note types

Recommended note families:

- `Skill Spec`
- `Skill Case`
- `Run Review`
- `Pattern`
- `Failure Pattern`
- `Decision Record`
- `Value Case`
- `Pricing Note`
- `Market Note`
- `Architecture Map`

### 10.5 Obsidian frontmatter recommendation

Each note should support structured frontmatter like:

```yaml
type: skill_spec
skill_key: feature_dev_skill
version: 1
origin: native
status: active
value_status: measured
tags:
  - engineering
  - feature-dev
knowledge_refs: []
run_refs: []
evaluation_refs: []
experience_refs: []
economy_refs: []
updated_at: 2026-03-30
```

### 10.6 Obsidian tooling notes

The following inspirations are useful but must remain optional and non-canonical:

- Excalidraw for visual system maps
- BRAT for loading experimental community plugins in a controlled vault
- `github.com/YishTu/claudian`
  - worth evaluating as a possible AXE/Obsidian writing bridge, but not part of phase-one delivery
- `github.com/kepano/obsidian-skills`
  - useful as inspiration for note templates and vault ergonomics, not as canonical BRAiN runtime model

### 10.7 Required Obsidian integration approach

Recommended backend module to add later:

- `backend/app/modules/knowledge_sync/`

Responsibilities:

- export curated skill and knowledge artifacts to markdown
- maintain stable vault paths
- optionally import approved curated notes back into structured metadata
- never mutate runtime truth directly from raw notes without governance

---

## 11. Final Target Product Model

### 11.1 User-facing experience

#### AXE UI

User gives:

- a URL
- a problem statement
- a feature request
- a bug report
- a domain-specific task

BRAiN responds by:

- choosing an existing skill
- or composing a plan from skills
- or later generating a draft skill definition

#### ControlDeck v3

Operators can:

- browse all skills
- filter by category/origin/value/risk
- inspect skill definitions and versions
- inspect skill runs
- inspect evaluation and experience
- inspect knowledge and patterns
- inspect value score and pricing
- promote/deprecate/publish skills
- inspect Obsidian-linked deep docs

### 11.2 Business-facing experience

The system can express value in human language:

- saves 5 developer-days per run
- reduces triage from 4 hours to 15 minutes
- automates work previously handled by 3 specialists
- reduces release risk in critical auth flows

This is the bridge from technical runtime to refinancing and marketplace.

---

## 12. Phased Implementation Plan

### Phase 0 - Alignment and hardening

Goal:

- lock the architecture before new UI or monetization work diverges further

Tasks:

1. declare `skills_registry + skill_engine + SkillRun` as canonical skill path
2. document legacy `app/modules/skills` as compatibility surface only
3. fix ControlDeck v3 skill frontend/backend contract mismatches
4. ensure routes and docs reflect the governed path, not the legacy direct path

Done criteria:

- CD3 skill page reads real backend data
- CD3 can create and observe real `SkillRun`s
- route and object shape mismatches are removed

### Phase 1 - Canonical skill catalog and runtime alignment

Goal:

- make skill registry and skill engine visible and usable end-to-end

Tasks:

1. add CD3 adapters for `SkillDefinitionResponse` and `SkillRunResponse`
2. add missing backend list/read endpoints if needed for active versions and lightweight catalog search
3. implement explicit `create run -> execute run` flow in CD3
4. remove assumptions about retry/delete routes that do not exist
5. show definition lifecycle status and risk tier in CD3

Done criteria:

- skill catalog works
- run monitor works
- run execution works
- lifecycle status is visible

### Phase 2 - Evaluation and experience visibility

Goal:

- make skill quality visible and measurable

Tasks:

1. surface evaluation results per run in CD3
2. surface experience summaries per run
3. show pass/fail, dimension scores, findings, recommendations
4. connect knowledge provenance chain in UI

Done criteria:

- every important run can be inspected from run -> evaluation -> experience -> knowledge

### Phase 3 - Value engine MVP

Goal:

- create a human-meaningful skill value model

Tasks:

1. add `skill_value_profiles` persistence
2. compute first value score and ROI score
3. store estimates for time saved and people-equivalent
4. add ControlDeck value cards and business language labels

Done criteria:

- selected skills show cost, value score, ROI, and estimated effort saved

### Phase 4 - Obsidian knowledge sync MVP

Goal:

- establish BRAiN deep knowledge layer

Tasks:

1. seed Obsidian vault structure
2. create markdown export of skill specs and selected reports
3. create a note convention and frontmatter contract
4. add CD3 links from skills to Obsidian paths
5. add Excalidraw-ready architecture and skill maps

Done criteria:

- one working Obsidian vault exists
- selected skills and reports are exported as notes
- knowledge links are visible in CD3

### Phase 5 - Skill creator and intent-to-skill path

Goal:

- allow AXE input to resolve into skill selection or draft skill generation

Tasks:

1. add `intent_to_skill` service contract
2. add `POST /api/intent/execute` or equivalent governed endpoint
3. support URL/text/problem ingestion
4. map inputs to existing skills first, then draft generation later

Done criteria:

- AXE can turn a URL/problem statement into a governed skill execution plan

### Phase 6 - Promotion and premium readiness

Goal:

- prepare safe monetization

Tasks:

1. add trust/value/premium metadata
2. add promotion workflows in CD3
3. add internal credits pricing model
4. keep marketplace externalization disabled by default

Done criteria:

- platform can distinguish free, trusted, and premium-capable skills

---

## 13. Final Delivery Order

Recommended execution order:

1. Fix current CD3 skill integration
2. Align backend/route/docs around canonical path
3. Add evaluation/experience visibility
4. Add value engine MVP
5. Add Obsidian sync MVP
6. Add intent-to-skill path
7. Add premium/credits readiness

Do not start with marketplace UI.

---

## 14. Junior Developer Execution Package

This section is the concrete handoff code for a junior developer.

### 14.1 Mandatory working rules

You are not designing a new skill system from scratch.

You must preserve these invariants:

1. `SkillRun` stays the only execution truth.
2. `skills_registry` stays the definition truth.
3. Do not introduce a second runtime path.
4. Do not revive legacy direct execution as the primary path.
5. Do not put business value logic into frontend only; persist it in backend models.
6. Do not use Obsidian as the canonical runtime DB.

### 14.2 First implementation slice

#### Slice A - ControlDeck v3 skill page contract fix

Goal:

- make the existing `/skills` page work against the real backend contracts

Files to inspect and change:

- `frontend/controldeck-v3/src/lib/api/skills.ts`
- `frontend/controldeck-v3/src/app/(protected)/skills/page.tsx`
- `backend/app/modules/skills_registry/router.py`
- `backend/app/modules/skill_engine/router.py`

Tasks:

1. Replace the frontend skill object shape with a mapper from `SkillDefinitionResponse`.
2. Replace the frontend run object shape with a mapper from `SkillRunResponse`.
3. Update `skillsApi.list()` to use `GET /api/skill-definitions`.
4. Update `skillsApi.getRuns()` to use `GET /api/skill-runs` and unpack `{items,total}`.
5. Update trigger flow:
   - create a run with `POST /api/skill-runs`
   - include required `idempotency_key`
   - then execute via `POST /api/skill-runs/{run_id}/execute`
6. Replace delete/retry assumptions with actual available actions.
7. Expose lifecycle status, risk tier, and quality profile in UI.

Verification:

- `npm run build` in `frontend/controldeck-v3`
- manual browser test on `/skills`
- add/update E2E so catalog + run creation are covered

#### Slice B - Catalog/read model polish

Goal:

- make the skill catalog useful for operators

Tasks:

1. Add filters for:
   - status
   - risk tier
   - skill key search
2. Add tabs or panels for:
   - catalog
   - runs
   - lifecycle status
3. Add detail modal sections for:
   - capabilities
   - constraints
   - evaluation criteria
   - artifact refs

#### Slice C - Evaluation and experience surface

Goal:

- expose run quality and learnings

Files to inspect:

- `backend/app/modules/skill_evaluator/router.py`
- `backend/app/modules/experience_layer/router.py`
- `backend/app/modules/knowledge_layer/router.py`

Tasks:

1. Verify read endpoints exist; add read endpoints only if missing.
2. Extend CD3 run detail modal to show:
   - evaluation score
   - findings
   - recommendations
   - experience summary
3. Add links to downstream knowledge items where available.

#### Slice D - Value engine MVP backend

Goal:

- introduce first persistent skill value profile

New backend module suggestion:

- `backend/app/modules/skill_value/`

Create:

- `models.py`
- `schemas.py`
- `service.py`
- `router.py`

Add migration for `skill_value_profiles`.

Implement:

1. create/update value profile for a skill definition
2. read value profile by skill key/version
3. compute `value_score` and `roi_score`
4. allow manual estimates for:
   - `time_saved_hours_estimate`
   - `people_equivalent_estimate`
5. derive `avg_execution_cost` from historical runs where possible

Do not implement billing yet.

#### Slice E - Obsidian sync MVP

Goal:

- create the first working knowledge vault integration

Recommended new backend module:

- `backend/app/modules/knowledge_sync/`

Create:

- vault config support
- export service
- path builder
- markdown renderer

First export targets:

1. skill spec note
2. skill value note
3. run review note
4. architecture note index

Seed target folder structure under a configurable root, for example:

- `knowledge/obsidian-vault/`

The exporter should create the baseline folders listed in section 10.3 if missing.

Frontmatter must include stable IDs and refs back to backend records.

#### Slice F - Documentation updates

You must update docs while implementing.

At minimum update:

- this roadmap file
- `docs/roadmap/README.md`
- any touched spec if API contracts change

### 14.3 Engineering standards for the junior dev

- keep changes scoped
- prefer adapters/mappers over breaking existing contracts
- do not remove legacy code until the new path is verified
- add tests with every behavior change
- preserve auth and tenant boundaries
- preserve audit/event ordering on mutating endpoints

### 14.4 Suggested implementation sequence for the junior dev

1. fix CD3 skill API shapes
2. make catalog render real data
3. make manual run trigger work end-to-end
4. expose evaluation and experience in run detail
5. add `skill_value` backend module and minimal CD3 value cards
6. add Obsidian vault bootstrap + exporter
7. add CD3 links to exported knowledge notes

---

## 15. Risks and Guardrails

### Main risks

- accidental re-expansion of legacy direct skill path
- frontend inventing its own skill/value schema
- marketplace work starting before scoring/governance is stable
- Obsidian being treated as runtime source of truth
- noisy, uncontrolled skill generation creating catalog chaos

### Required guardrails

- one canonical registry path
- one canonical runtime path
- explicit lifecycle and status transitions
- tenant-safe read/write boundaries
- value scoring must be explainable
- premium/public publication requires governance

---

## 16. Definition of Done

This initiative is done for its first real milestone when:

- ControlDeck v3 skill page works end-to-end against the governed backend path
- AXE remains the intent frontdoor and can hand off to governed skill execution
- skill definitions, runs, evaluations, and experience are visible in one coherent operator flow
- value score and ROI score exist for selected skills
- an Obsidian vault can be bootstrapped and populated with curated skill/knowledge notes
- the system can explain the value of a skill in business terms, not only technical metrics
- marketplace-ready metadata exists, even if marketplace UI/payment is not yet enabled

---

## 17. Final Recommendation

Do not build a marketplace first.

Build this sequence first:

1. canonical skill integration
2. evaluation visibility
3. value scoring
4. Obsidian knowledge layer
5. skill creator / intent-to-skill
6. premium/credit readiness

That path gives BRAiN a governed, explainable, economically meaningful skill system rather than a prompt catalog with billing attached.
