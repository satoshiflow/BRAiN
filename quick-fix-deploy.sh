#!/bin/bash
# Quick Fix Deployment - Switch to fix branch and rebuild

cd /srv/dev

echo "=== Schritt 1: Fetch latest branches ==="
git fetch origin

echo "=== Schritt 2: Switch to fix branch ==="
git checkout claude/check-project-status-y4koZ

echo "=== Schritt 3: Verify fixes are present ==="
echo "Checking __init__.py files:"
ls -la backend/app/__init__.py backend/brain/__init__.py

echo "Checking import fixes:"
echo "Old imports (should be 0): $(grep -c 'from backend.brain' backend/brain/governor/governor.py)"

echo "=== Schritt 4: Stop containers ==="
docker compose down

echo "=== Schritt 5: Clean rebuild ==="
docker compose build backend --no-cache

echo "=== Schritt 6: Start backend ==="
docker compose up -d backend

echo "=== Schritt 7: Wait for startup ==="
sleep 15

echo "=== Schritt 8: Check logs ==="
docker compose logs backend --tail=50

echo "=== Schritt 9: Health check ==="
curl http://localhost:8000/api/health

echo "=== Schritt 10: Verify no import errors ==="
docker compose logs backend 2>&1 | grep -i "Could not import" && echo "❌ Still has errors" || echo "✅ No import errors"
