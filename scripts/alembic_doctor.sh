#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-check}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-brain-backend}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-brain-postgres}"
DB_USER="${DB_USER:-brain}"
DB_NAME="${DB_NAME:-brain}"

if [[ "$MODE" != "check" && "$MODE" != "reconcile" ]]; then
  echo "Usage: ./scripts/alembic_doctor.sh [check|reconcile]"
  exit 2
fi

echo "[alembic-doctor] mode=$MODE backend=$BACKEND_CONTAINER db=$DB_NAME"

heads_raw=$(docker exec "$BACKEND_CONTAINER" sh -lc "cd /app && alembic heads")
heads=$(printf "%s\n" "$heads_raw" | sed -n 's/^\([a-zA-Z0-9_]*\) (head).*/\1/p')
versions=$(docker exec "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -A -c "SELECT version_num FROM alembic_version ORDER BY version_num;")

missing=0
while IFS= read -r head; do
  [[ -z "$head" ]] && continue
  if ! printf "%s\n" "$versions" | grep -qx "$head"; then
    echo "[alembic-doctor] missing head in alembic_version: $head"
    missing=1
  fi
done <<< "$heads"

if [[ "$MODE" == "reconcile" ]]; then
  echo "[alembic-doctor] stamping heads + schema reconcile"
  docker exec "$BACKEND_CONTAINER" sh -lc "cd /app && alembic stamp heads"
  ./scripts/reconcile_local_db_schema.sh
  versions=$(docker exec "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -A -c "SELECT version_num FROM alembic_version ORDER BY version_num;")
  missing=0
  while IFS= read -r head; do
    [[ -z "$head" ]] && continue
    if ! printf "%s\n" "$versions" | grep -qx "$head"; then
      echo "[alembic-doctor] still missing after reconcile: $head"
      missing=1
    fi
  done <<< "$heads"
fi

echo "[alembic-doctor] heads="
printf "%s\n" "$heads"
echo "[alembic-doctor] alembic_version rows="
printf "%s\n" "$versions"

if [[ "$missing" -ne 0 ]]; then
  echo "[alembic-doctor] FAILED"
  exit 1
fi

echo "[alembic-doctor] OK"
