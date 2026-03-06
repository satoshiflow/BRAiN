# Roadmap Sprint Status (0-12)

Date: 2026-03-06
Owner: OpenCode

## Sprint 0 - Guardrails

- Done:
  - legacy auth import gate (pipeline)
  - legacy EventBus import gate (`scripts/check_no_legacy_event_bus.py`)
  - auth utcnow deprecation gate (`scripts/check_no_utcnow_auth.py`)

## Sprint 1 - Backend auth convergence

- Done:
  - router auth-dependency migration across core modules
  - auth regression suite stable (`tests/test_auth_flow.py`, `tests/test_module_auth.py`)

## Sprint 2 - Frontend auth single-path

- Done:
  - fixed sign-in server action result contract (`frontend/control_deck/app/auth/actions.ts`)
  - fixed client sign-in undefined result crash (`frontend/control_deck/app/auth/signin/signin-form.tsx`)
  - aligned backend login contract handling + `/me` profile fetch (`frontend/control_deck/auth.ts`)

## Sprint 3 - Event backbone convergence

- Done:
  - removed runtime legacy EventBus usage in PayCore path
  - planning router EventStream hooks added (non-blocking publish)
  - EventStream injection wiring in app startup (`backend/main.py`)

## Sprint 4 - Rate-limit unification

- Done:
  - consolidated limiter usage and Redis-aware backend policy
  - explicit PayCore route limits

## Sprint 5 - Mission execution state stepping

- Done:
  - deterministic one-step executor in planning service (`execute_next_node`)
  - API endpoint `/api/planning/plans/{plan_id}/execute-next`

## Sprint 6 - Planning to execution bridge

- Done:
  - plan lifecycle endpoint can execute a ready node per tick
  - completion feedback hooks to memory + learning from planning execution

## Sprint 7 - Memory/Learning loop closure

- Done:
  - execution feedback persisted into episodic memory and learning latency metric
  - non-blocking best-effort semantics to avoid control-plane interruption

## Sprint 8 - Frontend operationalization step

- Done:
  - auth flow stabilization to support operations deck login reliability

## Sprint 9 - AXE vs ControlDeck boundaries

- Done:
  - middleware role gates retained/enforced (admin/operator split)
  - critic review log baseline added

## Sprint 10 - Specialist agent profiles

- Done:
  - `configs/agent_profiles.json` introduced as shared profile contract

## Sprint 11 - Model routing by cost/capability

- Done:
  - `configs/model_routing_policy.json` introduced with risk-path rules

## Sprint 12 - Critic gate before merge/deploy

- Done:
  - `scripts/critic_gate.py` introduced
  - integrated into `scripts/pipeline_plan.example.json`
  - report output to `reports/critic/critic_gate_report.json`

## Verification snapshot

- `PYTHONPATH=. pytest tests/test_auth_flow.py tests/test_module_auth.py tests/test_paycore_ownership.py -q` -> PASS
- `PYTHONPATH=. pytest app/modules/planning/tests/test_planning.py -q` -> PASS
- `python3 scripts/check_no_legacy_event_bus.py` -> PASS
- `python3 scripts/check_no_utcnow_auth.py` -> PASS
- `python3 scripts/check_no_utcnow_planning.py` -> PASS
- `python3 scripts/resilient_pipeline_runner.py --plan scripts/pipeline_plan.example.json --always-zero` -> PASS

## Stabilization closure

- Planning datetime deprecation cleanup completed (`schemas.py`, `service.py`, `failure_recovery.py`).
- Control Deck admin users API hardened for production behavior (`force-dynamic`, pagination bounds, mock-source safety gate).
- Remaining warning is dependency-level (`passlib/crypt`), tracked as follow-up dependency upgrade.
