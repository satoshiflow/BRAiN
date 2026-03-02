# 🚀 AXE E2E Test Servers - Status & Control

**Created:** 2026-01-10
**Status:** ✅ BOTH SERVERS RUNNING

---

## 📊 Current Status

### Backend (Minimal Test Server)
```
Status:    ✅ RUNNING
Port:      8000
PID:       1356 (check with: ps aux | grep test_axe)
Log File:  /home/user/BRAiN/test_server.log
```

**Endpoints:**
- Health: http://localhost:8000/api/health
- Info: http://localhost:8000/api/axe/info
- Config: http://localhost:8000/api/axe/config/widget-test
- WebSocket: ws://localhost:8000/api/axe/ws/{session_id}

**Quick Check:**
```bash
curl http://localhost:8000/api/health
# Expected: {"status":"healthy","connections":0}
```

---

### Frontend (Next.js Dev Server)
```
Status:    ✅ RUNNING
Port:      3002
Log File:  /home/user/BRAiN/frontend/axe_ui/frontend.log
```

**URLs:**
- Test Page: http://localhost:3002/widget-test
- Home: http://localhost:3002/
- Dashboard: http://localhost:3002/dashboard

**Quick Check:**
```bash
curl -I http://localhost:3002/widget-test
# Expected: HTTP/1.1 200 OK
```

---

## 🎛 Server Control

### Stop Servers

**Backend:**
```bash
pkill -f test_axe_websocket_server
# Or specific PID:
kill 1356
```

**Frontend:**
```bash
pkill -f "next dev"
# Or:
cd /home/user/BRAiN/frontend/axe_ui
npm run dev  # Press Ctrl+C
```

**Both:**
```bash
pkill -f test_axe_websocket_server && pkill -f "next dev"
```

---

### Restart Servers

**Backend:**
```bash
cd /home/user/BRAiN
nohup python3 test_axe_websocket_server.py > test_server.log 2>&1 &

# Check if running:
sleep 2 && curl http://localhost:8000/api/health
```

**Frontend:**
```bash
cd /home/user/BRAiN/frontend/axe_ui
NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8000 nohup npm run dev > frontend.log 2>&1 &

# Check if running:
sleep 10 && curl -I http://localhost:3002/widget-test
```

**Both (one command):**
```bash
cd /home/user/BRAiN && \
nohup python3 test_axe_websocket_server.py > test_server.log 2>&1 & \
cd frontend/axe_ui && \
NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8000 nohup npm run dev > frontend.log 2>&1 &
```

---

## 📋 View Logs

**Backend Logs (Real-time):**
```bash
tail -f /home/user/BRAiN/test_server.log
```

**Frontend Logs (Real-time):**
```bash
tail -f /home/user/BRAiN/frontend/axe_ui/frontend.log
```

**Both (split terminal):**
```bash
# Terminal 1:
tail -f /home/user/BRAiN/test_server.log

# Terminal 2:
tail -f /home/user/BRAiN/frontend/axe_ui/frontend.log
```

---

## 🔍 Check Server Status

**Quick Status Check:**
```bash
#!/bin/bash
# Save as check_status.sh

echo "🔍 Checking AXE E2E Test Servers..."
echo ""

# Backend
echo "📡 Backend Server:"
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "   ✅ RUNNING on port 8000"
    curl -s http://localhost:8000/api/health | python3 -m json.tool
else
    echo "   ❌ NOT RUNNING"
fi

echo ""

# Frontend
echo "🎨 Frontend Server:"
if curl -s -I http://localhost:3002 | grep "200 OK" > /dev/null 2>&1; then
    echo "   ✅ RUNNING on port 3002"
    echo "   URL: http://localhost:3002/widget-test"
else
    echo "   ❌ NOT RUNNING"
fi
```

**Usage:**
```bash
chmod +x check_status.sh
./check_status.sh
```

---

## 🐛 Troubleshooting

### Port Already in Use

**Backend (Port 8000):**
```bash
# Find process using port
lsof -i :8000
# OR
netstat -tuln | grep 8000

# Kill process
kill -9 <PID>

# Restart
python3 test_axe_websocket_server.py &
```

**Frontend (Port 3002):**
```bash
# Find process using port
lsof -i :3002

# Kill process
kill -9 <PID>

# Restart
cd frontend/axe_ui && npm run dev
```

---

### Server Won't Start

**Backend:**
```bash
# Check Python and dependencies
python3 --version  # Should be 3.11+
python3 -c "import fastapi; print('FastAPI OK')"
python3 -c "import uvicorn; print('Uvicorn OK')"

# Run in foreground to see errors
python3 test_axe_websocket_server.py
```

**Frontend:**
```bash
# Check Node and npm
node --version  # Should be 18+
npm --version

# Reinstall dependencies
cd frontend/axe_ui
rm -rf node_modules package-lock.json
npm install

# Run in foreground
npm run dev
```

---

### WebSocket Connection Failed

**Check:**
1. Backend server running? `curl http://localhost:8000/api/health`
2. Firewall blocking WebSocket? Try disabling temporarily
3. Browser console errors?

**Test WebSocket manually:**
```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c ws://localhost:8000/api/axe/ws/test-session

# Send ping
> {"type":"ping","payload":{"timestamp":123}}

# Expected response:
< {"type":"pong","payload":{"timestamp":123}}
```

---

## 📊 Server Metrics

**Backend:**
```bash
# Active connections
curl -s http://localhost:8000/api/health | jq '.connections'

# Server info
curl -s http://localhost:8000/api/axe/info | jq
```

**Frontend:**
```bash
# Next.js build info
cd frontend/axe_ui && npm run build

# Check bundle size
ls -lh .next/static/chunks/
```

---

## 🔧 Environment Variables

**Backend:**
```bash
# No special env vars needed for test server
# (Minimal server has hardcoded defaults)
```

**Frontend:**
```bash
# Set API base URL
export NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8000

# Run dev server
npm run dev
```

---

## 📝 Process IDs

**Find PIDs:**
```bash
# Backend
ps aux | grep test_axe_websocket_server | grep -v grep

# Frontend
ps aux | grep "next dev" | grep -v grep

# All Node processes
ps aux | grep node | grep -v grep
```

---

## ⚡ Quick Commands

**Start Everything:**
```bash
cd /home/user/BRAiN && \
nohup python3 test_axe_websocket_server.py > test_server.log 2>&1 & \
cd frontend/axe_ui && \
NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8000 nohup npm run dev > frontend.log 2>&1 & \
cd ../.. && \
echo "✅ Servers starting..."
sleep 5 && \
curl http://localhost:8000/api/health && \
echo "" && \
echo "✅ Backend: http://localhost:8000" && \
echo "✅ Frontend: http://localhost:3002/widget-test"
```

**Stop Everything:**
```bash
pkill -f test_axe_websocket_server && \
pkill -f "next dev" && \
echo "✅ All servers stopped"
```

**Status Check:**
```bash
echo "Backend:" && curl -s http://localhost:8000/api/health && \
echo "" && echo "Frontend:" && curl -I http://localhost:3002 2>&1 | grep "200 OK"
```

---

## 🎯 Next Steps

**Now that servers are running:**

1. **Open Browser:** http://localhost:3002/widget-test
2. **Follow Test Guide:** `docs/AXE_E2E_TEST_GUIDE.md`
3. **Run all 12 test scenarios**
4. **Document results**

---

**Updated:** 2026-01-10
**Session:** claude/fix-traefik-config-eYoK3
