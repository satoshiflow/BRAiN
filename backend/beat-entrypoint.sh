#!/bin/bash
#
# Celery Beat Entrypoint Script
#
# Starts Celery Beat scheduler for periodic tasks.
#
# Created: 2025-12-20
# Phase: 5 - Developer Experience & Advanced Features

set -e

# Default values
LOG_LEVEL=${CELERY_LOG_LEVEL:-"INFO"}
SCHEDULE_FILE=${CELERY_SCHEDULE_FILE:-"/tmp/celerybeat-schedule"}

echo "========================================="
echo "BRAiN Celery Beat Scheduler"
echo "========================================="
echo "Log Level: $LOG_LEVEL"
echo "Schedule File: $SCHEDULE_FILE"
echo "========================================="

# Wait for Redis to be ready
echo "Waiting for Redis..."
timeout=30
counter=0

while ! nc -z redis 6379; do
  counter=$((counter + 1))
  if [ $counter -ge $timeout ]; then
    echo "Error: Redis not available after ${timeout}s"
    exit 1
  fi
  echo "Redis not ready, waiting... ($counter/$timeout)"
  sleep 1
done

echo "Redis is ready!"

# Remove old schedule file if exists
rm -f "$SCHEDULE_FILE"

# Start Celery Beat
exec celery -A backend.app.core.celery_app beat \
  --loglevel=$LOG_LEVEL \
  --schedule="$SCHEDULE_FILE"
