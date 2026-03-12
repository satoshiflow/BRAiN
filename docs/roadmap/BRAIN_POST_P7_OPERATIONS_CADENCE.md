# BRAiN Post-P7 Operations and Evolution Cadence

Version: 1.0
Status: Active
Date: 2026-03-09
Purpose: Define the operating cadence after phase P7 so delivery quality, governance,
and evolution safety remain stable in continuous operation.

---

## 1) Scope

This cadence starts after `P0-P7` completion and runs in recurring cycles.

It does not replace the canonical layered roadmap. It operationalizes it.

Dependencies:
- `docs/roadmap/BRAIN_SKILL_FIRST_IMPLEMENTATION_ROADMAP.md`
- `docs/roadmap/IMPLEMENTATION_PROGRESS.md`
- `docs/specs/economy_selection_support_mvp.md`

---

## 2) Operating Objectives (O1-O3)

### O1 - Monthly Governance Review Cadence

Goal:
- run one monthly review package covering contracts, migration posture, and governance evidence.

Required package:
1. contract delta report (API/schema/event/error changes).
2. tenant isolation review (cross-tenant denials + boundary checks).
3. lifecycle/decommission ledger review.
4. RC gate trend report and unresolved failures.
5. reviewer sign-off notes (security, migration, verification, docs).

Exit criteria (monthly):
- package published under `docs/roadmap/monthly/`.
- unresolved Sev1 governance item count = `0`.

### O2 - Economy Hardening (Anti-Gaming + Explainability)

Goal:
- keep economy scoring transparent, bounded, and non-manipulable.

Controls:
1. preserve dimension-level score breakdown (`confidence`, `frequency`, `impact`, `cost`).
2. enforce bounded values and deterministic weighting.
3. require evidence references for rank-affecting inputs.
4. add anomaly review criteria for sudden ranking spikes.
5. keep economy as prioritization-only signal (never direct apply).

Exit criteria:
- explainability payload present for every economy assessment.
- anti-gaming checks documented and test-backed.

### O3 - Production Quality Gates as SLOs

Goal:
- track safety invariants as steady-state reliability objectives.

SLO set:
1. tenant isolation: `0` confirmed cross-tenant data exposure incidents.
2. audit ordering: all sensitive flows maintain durable state -> durable audit -> event publish.
3. RC gate drift: no sustained red state longer than one release window.

Measurement:
- monthly SLO snapshot attached to governance package.
- incident/corrective action notes linked from `IMPLEMENTATION_PROGRESS` updates.

---

## 3) Recurring Execution Loop

Per month:
1. collect verification evidence.
2. run RC gate and targeted economy/discovery/evolution suites.
3. publish monthly package.
4. record deltas and follow-up actions.
5. schedule next cycle owners.

Suggested command baseline:
- `cd backend && PYTHONPATH=. pytest tests/test_discovery_layer.py tests/test_discovery_layer_service.py tests/test_economy_layer.py tests/test_economy_layer_service.py tests/test_evolution_control.py tests/test_evolution_control_service.py -q`
- `./scripts/run_rc_staging_gate.sh`

---

## 4) Ownership

- `brain-orchestrator`: cadence owner and gate decisions.
- `brain-security-reviewer`: tenant and governance posture.
- `brain-verification-engineer`: RC/test evidence bundle.
- `brain-docs-scribe`: monthly package and roadmap/spec sync.

---

## 5) Initial Backlog (Next 30 Days)

1. create `docs/roadmap/monthly/2026-04-governance-package.md` template.
2. add explicit anti-gaming test cases for economy ranking outliers.
3. add SLO snapshot section to `IMPLEMENTATION_PROGRESS` monthly entries.
