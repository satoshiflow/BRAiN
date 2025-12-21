#!/bin/bash
#
# Celery Worker Entrypoint Script
#
# Starts Celery worker with configured queues and concurrency.
#
# Created: 2025-12-20
# Phase: 5 - Developer Experience & Advanced Features

set -e

# Default values
QUEUE_NAME=${CELERY_QUEUE:-"default"}
CONCURRENCY=${CELERY_CONCURRENCY:-"4"}
LOG_LEVEL=${CELERY_LOG_LEVEL:-"INFO"}

echo "========================================="
echo "BRAiN Celery Worker"
echo "========================================="
echo "Queue: $QUEUE_NAME"
echo "Concurrency: $CONCURRENCY"
echo "Log Level: $LOG_LEVEL"
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

# Start Celery worker
exec celery -A backend.app.core.celery_app worker \
  --loglevel=$LOG_LEVEL \
  --concurrency=$CONCURRENCY \
  --queues=$QUEUE_NAME \
  --max-tasks-per-child=1000 \
  --time-limit=600 \
  --soft-time-limit=300
