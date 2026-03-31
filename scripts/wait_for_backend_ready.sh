#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
ATTEMPTS="${ATTEMPTS:-30}"
SLEEP_SECONDS="${SLEEP_SECONDS:-2}"

echo "[wait-backend] Waiting for ${BACKEND_URL}/api/health"

for ((i=1; i<=ATTEMPTS; i++)); do
  if curl -fsS --max-time 5 "${BACKEND_URL}/api/health" >/dev/null 2>&1; then
    echo "[wait-backend] Backend is ready"
    exit 0
  fi
  echo "[wait-backend] Attempt ${i}/${ATTEMPTS} not ready yet"
  sleep "$SLEEP_SECONDS"
done

echo "[wait-backend] Backend did not become ready in time"
exit 1
