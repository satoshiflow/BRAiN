#!/bin/bash
# brain-starter.sh - Startet BRAiN vollständig

set -e

echo "🧠 BRAiN SYSTEM STARTER"
echo "======================="
echo ""

# Konfiguration
BACKEND_DIR="/home/oli/dev/brain-v2/backend"
CONTROL_DECK_DIR="/home/oli/dev/brain-v2/frontend/control_deck"
AXE_UI_DIR="/home/oli/dev/brain-v2/frontend/axe_ui"
BACKEND_PORT=8001
CONTROL_DECK_PORT=3001
AXE_UI_PORT=3002

# Funktion: Port freigeben
free_port() {
    local port=$1
    local pids=$(lsof -t -i:$port 2>/dev/null || echo "")
    if [ -n "$pids" ]; then
        echo "🛑 Beende Prozess auf Port $port..."
        kill -9 $pids 2>/dev/null || true
        sleep 2
    fi
}

# 1. ALLE SERVER STOPPEN
echo "1️⃣  Bereinige alte Prozesse..."
free_port $BACKEND_PORT
free_port $FRONTEND_PORT
pkill -f "uvicorn.*$BACKEND_PORT" 2>/dev/null || true
pkill -f "next.*$FRONTEND_PORT" 2>/dev/null || true
sleep 3

# 2. BACKEND STARTEN (MIT ALLEN FEATURES)
echo ""
echo "2️⃣  Starte BRAiN Backend (Port $BACKEND_PORT)..."
cd "$BACKEND_DIR"

# Full Mode - alle Features aktiviert
export ENABLE_MISSION_WORKER=true
export BRAIN_EVENTSTREAM_MODE=required
export BRAIN_LOG_LEVEL=info

nohup uvicorn main:app --host 127.0.0.1 --port $BACKEND_PORT > /tmp/brain.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Warte auf Backend
echo "   Warte auf Backend..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:$BACKEND_PORT/api/health 2>/dev/null | grep -q "ok"; then
        echo "   ✅ Backend bereit!"
        break
    fi
    sleep 1
    echo -n "."
done

# 3. CONTROL DECK STARTEN (Port 3001)
echo ""
echo "3️⃣  Starte Control Deck (Port $CONTROL_DECK_PORT)..."
cd "$CONTROL_DECK_DIR"

# Cache löschen für sauberen Start
rm -rf .next .turbo 2>/dev/null || true

PORT=$CONTROL_DECK_PORT nohup npm run dev > /tmp/control_deck.log 2>&1 &
CONTROL_DECK_PID=$!
echo "   Control Deck PID: $CONTROL_DECK_PID"

# Warte auf Control Deck
echo "   Warte auf Control Deck..."
for i in {1..60}; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:$CONTROL_DECK_PORT 2>/dev/null | grep -q "200\|307"; then
        echo ""
        echo "   ✅ Control Deck bereit!"
        break
    fi
    sleep 2
    echo -n "."
done

# 4. AXE_UI STARTEN (Port 3002)
echo ""
echo "4️⃣  Starte AXE_UI (Port $AXE_UI_PORT)..."
cd "$AXE_UI_DIR"

# Cache löschen für sauberen Start
rm -rf .next .turbo 2>/dev/null || true

# AXE_UI hat -p 3002 in package.json, aber wir setzen es explizit
PORT=$AXE_UI_PORT nohup npm run dev > /tmp/axe_ui.log 2>&1 &
AXE_UI_PID=$!
echo "   AXE_UI PID: $AXE_UI_PID"

# Warte auf AXE_UI
echo "   Warte auf AXE_UI..."
for i in {1..60}; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:$AXE_UI_PORT 2>/dev/null | grep -q "200\|307"; then
        echo ""
        echo "   ✅ AXE_UI bereit!"
        break
    fi
    sleep 2
    echo -n "."
done

# 5. STATUS
echo ""
echo ""
echo "🎉 SYSTEM BEREIT!"
echo "=================="
echo ""
echo "🔗 URLs:"
echo "   Control Deck:  http://localhost:$CONTROL_DECK_PORT"
echo "   Fred Bridge:   http://localhost:$CONTROL_DECK_PORT/fred-bridge"
echo "   AXE Widget:    http://localhost:$CONTROL_DECK_PORT/axe-widget"
echo "   LLM Config:    http://localhost:$CONTROL_DECK_PORT/settings/llm"
echo "   AXE_UI:        http://localhost:$AXE_UI_PORT"
echo ""
echo "🔧 Backend API:"
echo "   Health:        http://127.0.0.1:$BACKEND_PORT/api/health"
echo "   Fred Bridge:   http://127.0.0.1:$BACKEND_PORT/api/fred-bridge/health"
echo ""
echo "📊 Logs:"
echo "   Backend:       tail -f /tmp/brain.log"
echo "   Control Deck:  tail -f /tmp/control_deck.log"
echo "   AXE_UI:        tail -f /tmp/axe_ui.log"
echo ""
echo "🛑 Stoppen:"
echo "   kill $BACKEND_PID $CONTROL_DECK_PID $AXE_UI_PID"
echo ""

# Teste Verbindung
echo "🧪 Verbindungstest:"
echo "   Backend:"
curl -s http://127.0.0.1:$BACKEND_PORT/api/fred-bridge/health 2>/dev/null && echo "" || echo "⚠️  Backend antwortet nicht"
echo "   Control Deck:"
curl -s -o /dev/null -w "   HTTP %{http_code}\n" http://localhost:$CONTROL_DECK_PORT 2>/dev/null || echo "   ⚠️  Control Deck antwortet nicht"
echo "   AXE_UI:"
curl -s -o /dev/null -w "   HTTP %{http_code}\n" http://localhost:$AXE_UI_PORT 2>/dev/null || echo "   ⚠️  AXE_UI antwortet nicht"
