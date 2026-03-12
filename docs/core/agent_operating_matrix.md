# BRAiN Agent Operating Matrix

Version: 1.0
Status: Active Working Standard
Purpose: Define the sub-agent operating model, role assignment, model preference, and parallelization strategy for BRAiN delivery.

---

## 1 Purpose

BRAiN delivery should run with a stable orchestration model:

- one orchestrator controls scope and integration
- specialist agents work in parallel
- high-risk decisions receive stronger models and stricter review
- cheap or free models handle low-risk exploration and synthesis work

This matrix is the working standard for autonomous execution.

---

## 2 Core Principle

Use the strongest model where wrong decisions are expensive.

Recommended priority:

- `Claude` for architecture, logic, security, migration risk, and critical review
- `ChatGPT` for implementation, test design, refactors, structured docs, and iterative code work
- `Free/lightweight models` for repo search, file mapping, low-risk summarization, and documentation prep
- `Kimi` optional only when quota is available; do not rely on it for core flow

---

## 3 Operating Roles

### 3.1 Orchestrator

Purpose:
- own plan, sequence, integration, final decisions, and merge quality

Responsibilities:
- split work into parallel tracks
- assign roles and expected outputs
- compare competing proposals
- choose implementation direction
- enforce BRAiN standards and documentation cadence

Preferred model:
- `ChatGPT` as active execution orchestrator
- `Claude` as escalation/review partner for critical decisions

Write authority:
- yes

---

### 3.2 Architecture Lead

Purpose:
- evaluate system shape, boundaries, target state, ADR-level tradeoffs

Best for:
- runtime ownership
- module boundaries
- migration sequencing
- event/audit/control-plane decisions

Preferred model:
- `Claude`

Write authority:
- no by default

---

### 3.2a Domain Orchestrator

Purpose:
- shape work inside one business or technical domain without taking over global governance or execution ownership

Best for:
- domain decomposition
- specialist selection
- domain review gates
- budget and spawn discipline inside a domain

Preferred model:
- `ChatGPT` or `Claude` depending on domain risk and ambiguity

Write authority:
- controlled; usually through orchestrator or runtime engineer

Notes:
- this operating role maps to the technical `Domain Agent` layer and the "Cardinal" metaphor
- it must not become a second supervisor or direct execution runtime

---

### 3.3 Schema and Contract Designer

Purpose:
- design object contracts, lifecycle rules, API shape, event types, error codes

Best for:
- specs
- state machines
- data contracts
- versioning rules

Preferred model:
- `Claude` primary
- `ChatGPT` secondary for fast drafting

Write authority:
- controlled, usually via orchestrator only

---

### 3.4 Runtime Engineer

Purpose:
- implement backend modules, service wiring, routers, tests, migrations, adapters

Best for:
- iterative coding
- controlled refactors
- test-driven implementation

Preferred model:
- `ChatGPT`

Write authority:
- yes, under orchestrator control

---

### 3.5 Migration Engineer

Purpose:
- own legacy containment, compatibility adapters, cutover rules, deprecation safety

Best for:
- route ownership changes
- old/new coexistence rules
- decommission plans

Preferred model:
- `Claude`

Write authority:
- controlled, high review requirement

---

### 3.6 Security and Governance Reviewer

Purpose:
- verify auth, tenant isolation, audit durability, policy fit, breakglass safety, event ordering

Best for:
- Constitution Gate
- registry mutation rules
- infra-affecting flows
- approval semantics

Preferred model:
- `Claude`

Write authority:
- no; review and block/approve role

---

### 3.7 Verification Engineer

Purpose:
- design and validate tests, acceptance criteria, regression coverage, gates

Best for:
- API tests
- state transition tests
- migration tests
- RC gate prep

Preferred model:
- `ChatGPT`

Write authority:
- yes for tests

---

### 3.8 Repo Scout

Purpose:
- rapidly explore file locations, imports, collisions, impact surface, config paths

Best for:
- repo search
- dependency mapping
- “what will this touch?” questions

Preferred model:
- `free/lightweight model`

Write authority:
- no

---

### 3.9 Docs and ADR Scribe

Purpose:
- keep `docs/specs`, `docs/roadmap`, `docs/core`, `AGENTS.md` synchronized with actual decisions

Best for:
- ADRs
- progress logs
- migration notes
- implementation checklists

Preferred model:
- `ChatGPT` or `free/lightweight model`

Write authority:
- yes, under orchestrator control

---

### 3.10 Review Critic

Purpose:
- perform aggressive second-pass review against architecture, contracts, and repo fit

Best for:
- missing fields
- drift detection
- security and migration challenge review

Preferred model:
- `Claude`

Write authority:
- no

---

## 4 Task Matrix

| Work Type | Primary Role | Preferred Model | Secondary Role | Parallel? |
|---|---|---|---|---|
| Architecture decision | Architecture Lead | Claude | Review Critic | yes |
| Contract/spec design | Schema Designer | Claude | Security Reviewer | yes |
| Repo exploration | Repo Scout | Free/lightweight | Architecture Lead | yes |
| Backend implementation | Runtime Engineer | ChatGPT | Verification Engineer | yes |
| Migration/cutover | Migration Engineer | Claude | Runtime Engineer | yes |
| Security review | Security Reviewer | Claude | Review Critic | yes |
| Test design | Verification Engineer | ChatGPT | Runtime Engineer | yes |
| Docs sync | Docs and ADR Scribe | ChatGPT/free | Orchestrator | yes |
| Final integration review | Orchestrator | ChatGPT | Claude review | no |

---

## 5 Parallelization Rules

### Run in parallel

- repo grounding across separate subsystems
- contract draft + independent risk review
- implementation of separate modules with low overlap
- docs preparation while code review is running
- test design while runtime implementation is in progress

### Run sequentially

- final architecture choices before schema lock
- schema lock before migrations or public API implementation
- cutover/deprecation before removing compatibility paths
- final merge/integration after all reviews complete

### One-writer rule

- many agents may analyze in parallel
- only one active writer should own a given implementation surface at a time
- orchestrator decides write ownership for each surface

---

## 6 Recommended Agent Set For BRAiN

The practical working set for this project is:

1. `brain-orchestrator`
2. `brain-architect`
3. `brain-schema-designer`
4. `brain-runtime-engineer`
5. `brain-migration-engineer`
6. `brain-security-reviewer`
7. `brain-verification-engineer`
8. `brain-repo-scout`
9. `brain-docs-scribe`
10. `brain-review-critic`

---

## 7 Mapping To Current Execution Environment

Current locally available subagent/tool pattern:

- `explore` -> best mapped to `brain-repo-scout`
- `general` -> can be used as:
  - `brain-architect`
  - `brain-schema-designer`
  - `brain-security-reviewer`
  - `brain-review-critic`

Operational rule:
- the orchestrator assigns a role label in every subagent prompt
- every subagent must return role-specific output, not generic prose

---

## 8 External Model Usage Policy

When external LLM access is available:

- send architecture, security, migration, and hard review tasks to `Claude`
- send coding, test generation, and implementation detail work to `ChatGPT`
- send low-risk exploration and draft summarization to free models

Do not use weaker/free models for:
- security-critical approval logic
- auth/tenant/audit control-plane decisions
- irreversible migration or decommission decisions

---

## 9 Output Contract Per Agent

Each specialist agent should return:

- `role`
- `goal`
- `assumptions`
- `findings`
- `risks`
- `recommended next action`

For implementation-oriented tasks additionally:

- `affected paths`
- `tests needed`
- `migration impact`

---

## 10 Execution Protocol

Every meaningful unit of work should follow:

`GROUNDING -> STRUCTURE -> CREATION -> EVALUATION -> FINALIZATION`

For BRAiN this becomes:

1. `Repo Scout` grounds context
2. `Architecture Lead` or `Schema Designer` structures the solution
3. `Runtime Engineer` creates the implementation or concrete draft
4. `Security Reviewer` and `Review Critic` evaluate it
5. `Docs Scribe` + `Orchestrator` finalize and sync docs

---

## 11 Efficiency Recommendations

- Use `Claude` sparingly on high-value decisions, not on bulk repo search.
- Use `ChatGPT` as primary implementation engine.
- Keep review independent from implementation.
- Separate architecture review from migration review.
- Use free models for mapping, inventories, summaries, and low-risk doc preparation.
- Preserve one canonical merge/integration owner.

---

## 12 Current Constraint

Within the current local execution environment, named role-agents can be established as an operational protocol and documentation standard.

However:
- they are not automatically provisioned as new native tool types
- they are orchestrated through the available subagent mechanisms and explicit role prompts

This is sufficient for disciplined parallel execution as long as the orchestrator enforces role separation.
