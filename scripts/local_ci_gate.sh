#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-all}"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_DIR="$ROOT_DIR/docs/roadmap/local_ci"
LOG_FILE="$LOG_DIR/${TIMESTAMP}_${MODE}.md"
AXE_CI_API_BASE="${BRAIN_LOCAL_CI_AXE_API_BASE:-https://api.brain.falklabs.de}"

mkdir -p "$LOG_DIR"

cat >"$LOG_FILE" <<EOF
# Local CI Evidence

- Timestamp (UTC): $TIMESTAMP
- Mode: $MODE
- Repo: BRAiN

## Results

EOF

run_cmd() {
  local label="$1"
  local command="$2"
  local workdir="$3"

  echo "==> $label"
  {
    echo "### $label"
    echo
    echo "- Command: \`$command\`"
    echo "- Workdir: \`$workdir\`"
    echo "- Started (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo '```text'
  } >>"$LOG_FILE"

  if (cd "$workdir" && eval "$command") >>"$LOG_FILE" 2>&1; then
    {
      echo '```'
      echo "- Status: PASS"
      echo "- Finished (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
      echo
    } >>"$LOG_FILE"
  else
    {
      echo '```'
      echo "- Status: FAIL"
      echo "- Finished (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
      echo
    } >>"$LOG_FILE"
    echo "Command failed: $command"
    echo "Evidence written to: $LOG_FILE"
    exit 1
  fi
}

case "$MODE" in
  backend)
    run_cmd "Backend RC gate" "./scripts/run_rc_staging_gate.sh" "$ROOT_DIR"
    ;;
  backend-fast)
    run_cmd "Backend targeted pytest" "PYTHONPATH=. pytest tests/test_module_auth.py -q" "$ROOT_DIR/backend"
    ;;
  axe)
    run_cmd "AXE lint" "NEXT_PUBLIC_BRAIN_API_BASE=$AXE_CI_API_BASE npm run lint" "$ROOT_DIR/frontend/axe_ui"
    run_cmd "AXE typecheck" "NEXT_PUBLIC_BRAIN_API_BASE=$AXE_CI_API_BASE npm run typecheck" "$ROOT_DIR/frontend/axe_ui"
    run_cmd "AXE build" "NEXT_PUBLIC_BRAIN_API_BASE=$AXE_CI_API_BASE npm run build" "$ROOT_DIR/frontend/axe_ui"
    run_cmd "AXE e2e" "npm run test:e2e" "$ROOT_DIR/frontend/axe_ui"
    ;;
  axe-fast)
    run_cmd "AXE lint" "NEXT_PUBLIC_BRAIN_API_BASE=$AXE_CI_API_BASE npm run lint" "$ROOT_DIR/frontend/axe_ui"
    run_cmd "AXE typecheck" "NEXT_PUBLIC_BRAIN_API_BASE=$AXE_CI_API_BASE npm run typecheck" "$ROOT_DIR/frontend/axe_ui"
    run_cmd "AXE build" "NEXT_PUBLIC_BRAIN_API_BASE=$AXE_CI_API_BASE npm run build" "$ROOT_DIR/frontend/axe_ui"
    ;;
  all)
    run_cmd "Backend RC gate" "./scripts/run_rc_staging_gate.sh" "$ROOT_DIR"
    run_cmd "AXE lint" "NEXT_PUBLIC_BRAIN_API_BASE=$AXE_CI_API_BASE npm run lint" "$ROOT_DIR/frontend/axe_ui"
    run_cmd "AXE typecheck" "NEXT_PUBLIC_BRAIN_API_BASE=$AXE_CI_API_BASE npm run typecheck" "$ROOT_DIR/frontend/axe_ui"
    run_cmd "AXE build" "NEXT_PUBLIC_BRAIN_API_BASE=$AXE_CI_API_BASE npm run build" "$ROOT_DIR/frontend/axe_ui"
    run_cmd "AXE e2e" "npm run test:e2e" "$ROOT_DIR/frontend/axe_ui"
    ;;
  *)
    echo "Unknown mode: $MODE"
    echo "Usage: ./scripts/local_ci_gate.sh <backend|backend-fast|axe|axe-fast|all>"
    exit 2
    ;;
esac

echo "Local CI completed successfully."
echo "Evidence written to: $LOG_FILE"
