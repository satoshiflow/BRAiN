#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/oli/dev/brain-v2"
BACKEND="$ROOT/backend"

cd "$BACKEND"

echo "[gate] auth + agent lifecycle"
PYTHONPATH=. pytest tests/test_auth_flow.py tests/test_module_auth.py tests/test_supervisor_agent.py -q -x --disable-warnings

echo "[gate] immune decision + event contract"
PYTHONPATH=. pytest tests/modules/test_immune_orchestrator.py tests/modules/test_arch_event_contracts.py -q -x --disable-warnings

echo "[gate] recovery action flow"
PYTHONPATH=. pytest tests/modules/test_recovery_policy_engine.py tests/test_enforcement_retry.py tests/test_reflex_actions.py -q -x --disable-warnings

echo "[gate] DNA integrity + audit"
PYTHONPATH=. pytest tests/test_dna_events.py tests/modules/test_genetic_integrity.py -q -x --disable-warnings

echo "[gate] discovery + evolution + economy"
PYTHONPATH=. pytest \
  tests/test_discovery_layer.py \
  tests/test_discovery_layer_service.py \
  tests/test_evolution_control.py \
  tests/test_evolution_control_service.py \
  tests/test_economy_layer.py \
  tests/test_economy_layer_service.py \
  -q -x --disable-warnings

echo "[gate] health system (Sprint B)"
PYTHONPATH=. pytest tests/test_health_system.py -q -x --disable-warnings

echo "[gate] diagnostics suite (Sprint C)"
PYTHONPATH=. pytest tests/test_diagnostics.py -q -x --disable-warnings

echo "[gate] immune system (Sprint D)"
PYTHONPATH=. pytest tests/test_immune_system.py -q -x --disable-warnings

cd "$ROOT"
echo "[gate] guardrails"
python3 scripts/check_no_changes_deprecated_modules.py
python3 scripts/check_no_legacy_event_bus.py
python3 scripts/check_no_utcnow_auth.py
python3 scripts/check_no_utcnow_planning.py
python3 scripts/critic_gate.py

echo "[gate] runtime preflight"
python3 scripts/preflight_runtime.py

echo "[gate] RC staging verification complete"
