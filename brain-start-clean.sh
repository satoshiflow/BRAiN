#!/bin/bash
# brain-start-clean.sh - Sauberer Start aller Services

set -e

echo "🧠 BRAiN CLEAN START"
echo "====================="
echo ""

# Kill all existing processes
echo "1️⃣  Stoppe alle bestehenden Services..."
pkill -f "uvicorn.*8001" 2>/dev/null || true
pkill -f "next.*3001" 2>/dev/null || true  
pkill -f "next.*3002" 2>/dev/null || true
sleep 3

# Check if ports are free
echo "2️⃣  Prüfe Ports..."
for port in 3001 3002 8001; do
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "   ⚠️  Port $port ist noch belegt, kill Prozesse..."
    kill $(lsof -t -i:$port) 2>/dev/null || true
    sleep 2
  fi
  echo "   ✅ Port $port frei"
done

echo ""
echo "3️⃣  Starte Backend (Port 8001)..."
cd /home/oli/dev/brain-v2/backend
export ENABLE_MISSION_WORKER=true
export BRAIN_EVENTSTREAM_MODE=required
export BRAIN_LOG_LEVEL=warning

nohup uvicorn main:app --host 127.0.0.1 --port 8001 > /tmp/brain.log 2>&1 &
BACKEND_PID=$!
echo "   PID: $BACKEND_PID"

# Wait for backend
echo "   Warte auf Backend..."
for i in {1..40}; do
  if curl -s http://127.0.0.1:8001/api/health 2>/dev/null | grep -q "ok"; then
    echo "   ✅ Backend läuft!"
    break
  fi
  sleep 1
  echo -n "."
done

echo ""
echo "4️⃣  Starte Control Deck (Port 3001)..."
cd /home/oli/dev/brain-v2/frontend/control_deck
rm -rf .next 2>/dev/null || true

PORT=3001 nohup npm run dev > /tmp/control_deck.log 2>&1 &
CONTROL_PID=$!
echo "   PID: $CONTROL_PID"

echo "   Warte auf Control Deck (ca. 45s)..."
for i in {1..50}; do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 2>/dev/null | grep -qE "200|307"; then
    echo ""
    echo "   ✅ Control Deck läuft!"
    break
  fi
  sleep 2
  if [ $((i % 10)) -eq 0 ]; then echo -n "$i"; else echo -n "."; fi
done

echo ""
echo "5️⃣  Starte AXE_UI (Port 3002)..."
cd /home/oli/dev/brain-v2/frontend/axe_ui
rm -rf .next 2>/dev/null || true

PORT=3002 nohup npm run dev > /tmp/axe_ui.log 2>&1 &
AXE_PID=$!
echo "   PID: $AXE_PID"

echo "   Warte auf AXE_UI (ca. 45s)..."
for i in {1..50}; do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:3002 2>/dev/null | grep -qE "200|307"; then
    echo ""
    echo "   ✅ AXE_UI läuft!"
    break
  fi
  sleep 2
  if [ $((i % 10)) -eq 0 ]; then echo -n "$i"; else echo -n "."; fi
done

echo ""
echo "========================================"
echo "🎉 ALLE SERVICES BEREIT!"
echo "========================================"
echo ""
echo "🔗 URLs:"
echo "   Control Deck:  http://localhost:3001"
echo "   Fred Bridge:   http://localhost:3001/fred-bridge"
echo "   AXE_UI:        http://localhost:3002"
echo "   Backend:       http://127.0.0.1:8001"
echo ""
echo "📊 PIDs (für Stoppen):"
echo "   Backend:     $BACKEND_PID"
echo "   Control:     $CONTROL_PID"
echo "   AXE_UI:      $AXE_PID"
echo ""
echo "📋 Logs:"
echo "   tail -f /tmp/brain.log"
echo "   tail -f /tmp/control_deck.log"
echo "   tail -f /tmp/axe_ui.log"
echo ""
echo "🛑 Stoppen:"
echo "   kill $BACKEND_PID $CONTROL_PID $AXE_PID"
echo ""

# Final check
echo "🧪 Final Check:"
curl -s http://127.0.0.1:8001/api/fred-bridge/health 2>/dev/null | head -1
curl -s -o /dev/null -w "Control Deck: %{http_code}\n" http://localhost:3001
curl -s -o /dev/null -w "AXE_UI: %{http_code}\n" http://localhost:3002
