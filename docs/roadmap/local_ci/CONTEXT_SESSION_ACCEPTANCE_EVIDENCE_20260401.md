# Context/Session Acceptance Evidence (2026-04-01)

## Executed Checks

- `python3 scripts/run_context_soak_profiles.py`
  - output: `docs/roadmap/local_ci/context_soak_report_20260401_143643Z.json`

- Backend targeted suites:
  - `PYTHONPATH=. pytest tests/test_axe_context_management.py tests/test_axe_fusion_routes.py tests/test_runtime_control_router.py tests/test_runtime_control_change_requests.py tests/test_llm_router_runtime_control.py tests/test_task_queue_runtime_enforcement.py -q --disable-warnings`

- Frontend verification:
  - AXE UI: `npm run lint && npm run test -- app/chat/__tests__/upload-flow.test.tsx`
  - ControlDeck v3: `npm run typecheck && npm run lint && npm run test && npm run build`

- Global gate:
  - `./scripts/run_rc_staging_gate.sh`

## Acceptance Snapshot

- Context token telemetry: implemented and surfaced in API + AXE UI
- Context envelope/tiering: implemented (`governance`, `active`, `short-term`, `retrieval`, `summary`)
- Session compression summaries: enabled in context builder for long sessions
- Relevance retrieval: overlap-based top-k selection enabled
- AXE transparency indicators: context mode/token class/trim hints visible in chat UI
- Soak evidence: synthetic profile report generated and archived
