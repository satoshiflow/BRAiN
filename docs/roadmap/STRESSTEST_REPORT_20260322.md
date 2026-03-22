# Stress Test Report - AXE/SkillRun Pipeline (2026-03-22)

## Scope

- AXE frontdoor chat path and legacy compatibility path
- SkillRun bridge behavior and fallback handling
- Governance and evolution apply guards
- Memory/knowledge durable chain regressions

## Configuration baseline

- AXE bridge default: `AXE_CHAT_EXECUTION_PATH=skillrun_bridge`
- AXE canonical chat skill default: `AXE_CHAT_SKILL_KEY=axe.chat.bridge`
- Skill/capability contract auto-seed enabled: `ENABLE_AXE_CHAT_SKILL_SEED=true`
- Direct capability execute block default: `BRAIN_BLOCK_DIRECT_CAPABILITY_EXECUTE=true`

## Executed suites

1. `PYTHONPATH=. pytest tests/test_axe_fusion_routes.py tests/test_skill_engine.py tests/test_evolution_control.py tests/test_evolution_control_service.py tests/test_experience_layer.py tests/test_knowledge_layer_service.py -q`
   - Result: `40 passed`

2. `PYTHONPATH=. pytest tests/test_axe_chat_skill_seeder.py -q`
   - Result: verifies canonical chat skill seeding path and active transitions

3. `./scripts/local_ci_gate.sh backend-fast`
   - Result: PASS (evidence in `docs/roadmap/local_ci/`)

## Scenario matrix

| Scenario | Expected behavior | Result |
|---|---|---|
| AXE chat (normal DMZ) | request accepted, controlled response path | PASS |
| AXE chat prefers SkillRun bridge | response marks `execution_path=skillrun_bridge` | PASS |
| SkillRun waiting approval | request returns controlled `409` approval signal | PASS |
| AXE stress burst (20 requests) | stable 2xx bridge responses, no crash | PASS |
| External trust denied | controlled 403 | PASS |
| Evolution apply without governance evidence | fail-closed | PASS |
| Evolution apply with governance + rollback metadata | transition allowed | PASS |
| Adaptive freeze / safe mode guards | apply blocked when frozen or safe mode active | PASS |
| Durable memory chain regressions | SkillRun->Eval->Experience->Knowledge invariants preserved | PASS |

## Error handling and debugging checks

- AXE route now re-raises `HTTPException` from bridge path (no accidental 500 wrapping).
- Legacy `/api/axe/message` no longer executes direct provider fallback when bridge is unavailable; returns controlled guidance error.
- Evolution apply guard remains test-compatible when DB fixtures are minimal/mocked.
- Control-plane learning/evolution events remain available for operational timeline inspection.

## Outcome

- Stress and failure routines are covered at route/service/test level.
- Core pipeline remains stable under repeated request bursts and guard-rail scenarios.
- Remaining operational validation is browser/live runtime check with real env and active provider endpoints.
