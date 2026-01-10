# 🧪 AXE WebSocket E2E Test Guide

**Status:** ✅ Beide Server laufen
**Backend:** http://localhost:8000 (Minimal Test Server)
**Frontend:** http://localhost:3002 (Next.js Dev Server)

---

## 📊 Server Status

### Backend (Minimal Test Server)
```
✅ Running on port 8000
✅ WebSocket endpoint: ws://localhost:8000/api/axe/ws/{session_id}
✅ Health: http://localhost:8000/api/health
✅ Info: http://localhost:8000/api/axe/info
✅ Config: http://localhost:8000/api/axe/config/widget-test
```

**Test Server Features:**
- Echo chat responses
- Mock diff generation (when "code" or "function" in message)
- Full WebSocket protocol support
- Console logging for debugging

### Frontend (Next.js)
```
✅ Running on port 3002
✅ Test Page: http://localhost:3002/widget-test
✅ API Base: http://localhost:8000 (env var set)
```

---

## 🎯 Quick Start

### 1. Open Browser

```bash
# Option A: If you have a desktop environment
xdg-open http://localhost:3002/widget-test

# Option B: Copy URL and open in your browser
http://localhost:3002/widget-test
```

### 2. Expected Initial State

**You should see:**
- ✅ Widget test page with instructions
- ✅ Floating AXE button in bottom-right corner (60x60px)
- ✅ Button shows "A" avatar with pulsing animation

**Browser Console should show:**
```
[AXE WebSocket] Connecting to: ws://localhost:8000/api/axe/ws/session-xxx
[AXE WebSocket] Connected
[AXE WebSocket] Received: pong {...}
```

---

## 📋 E2E Test Scenarios

### Test 1: Widget State Transitions ⭐

**Objective:** Verify widget state changes (minimized → expanded → canvas)

**Steps:**
1. **Initial State:** Widget is minimized (60x60px button, bottom-right)
2. **Click widget** → Should expand to 320x480px chat panel
3. **In expanded panel:** Look for:
   - Header: "AXE Test Mode"
   - Connection status: 🟢 Wifi icon + "Connected" (green)
   - Empty messages area with welcome message
   - Text input at bottom
4. **Click Maximize (⛶ icon)** → Should open full-screen CANVAS
5. **In CANVAS:** Look for:
   - Header with "AXE Builder Mode"
   - Connection status badge: "Connected" (green)
   - Split screen: 40% Chat (left) / 60% Code Editor (right)
   - File tabs: "untitled.tsx"
6. **Click Minimize** → Should collapse back to expanded panel
7. **Click Close (X)** → Should minimize to button

**Expected Result:** ✅ All state transitions work smoothly

---

### Test 2: WebSocket Connection Status ⭐

**Objective:** Verify connection indicators work

**Steps:**
1. **Expand widget** → Connection status should show 🟢 "Connected"
2. **Open CANVAS** → Connection badge should be green
3. **Open Browser DevTools** → Console tab
4. **Look for logs:**
   ```
   [AXE WebSocket] Connected
   [AXE WebSocket] Received: pong
   ```
5. **Every 30 seconds:** Should see ping/pong logs

**Expected Result:** ✅ Connection status always accurate

---

### Test 3: Chat Message Flow ⭐⭐

**Objective:** Verify chat works end-to-end

**Steps:**
1. **Expand widget** (or open CANVAS)
2. **Type:** "Hello, this is a test"
3. **Press Enter**
4. **User message appears:**
   - Right side
   - Blue background
   - Content: "Hello, this is a test"
5. **Wait ~1-2 seconds**
6. **Assistant message appears:**
   - Left side
   - Gray background
   - Content: "Echo: Hello, this is a test" (from test server)

**Browser Console:**
```
[AXE WebSocket] Received: chat_response {payload: {...}}
```

**Expected Result:** ✅ Messages flow correctly

---

### Test 4: Code Diff Generation ⭐⭐⭐

**Objective:** Verify diff generation and display

**Steps:**
1. **Open CANVAS mode** (full screen with code editor)
2. **Type:** "Write a function to calculate fibonacci"
3. **Press Enter**
4. **Chat response appears** (left side)
5. **After response, diff overlay should appear:**
   - Semi-transparent overlay covering code editor
   - Header: "AXE Code Suggestion"
   - File name: "example.tsx"
   - Description: "Mock code suggestion"
   - Monaco DiffEditor showing side-by-side comparison
   - Buttons: "✓ Apply Changes" and "✗ Reject"

**Expected Result:** ✅ Diff overlay displays correctly

---

### Test 5: Apply Diff Workflow ⭐⭐⭐

**Objective:** Verify Apply button works

**Steps:**
1. **Generate a diff** (Test 4)
2. **Click "✓ Apply Changes"**
3. **Overlay should close**
4. **File content updates** in code editor
5. **Browser Console:**
   ```
   Diff applied: diff-xxx in session session-xxx
   [AXE WebSocket] Received: diff_applied_confirmed {...}
   ```

**Expected Result:** ✅ Code updates, overlay closes

---

### Test 6: Reject Diff Workflow ⭐⭐⭐

**Objective:** Verify Reject button works

**Steps:**
1. **Generate a new diff** (type "write another function")
2. **Click "✗ Reject"**
3. **Overlay should close**
4. **File content UNCHANGED**
5. **Browser Console:**
   ```
   Diff rejected: diff-xxx in session session-xxx
   [AXE WebSocket] Received: diff_rejected_confirmed {...}
   ```

**Expected Result:** ✅ Overlay closes, no code change

---

### Test 7: File Management ⭐⭐

**Objective:** Verify multi-file support

**Steps:**
1. **In CANVAS mode**
2. **Click "+ Add File" button** (top header)
3. **New file tab appears:** "untitled-2.tsx"
4. **Click new file tab** → Editor switches to new file
5. **Type some code** in new file
6. **Click first file tab** → Editor switches back
7. **Click X on file tab** to close
8. **File tab disappears**

**Expected Result:** ✅ File management works

---

### Test 8: Auto-Reconnect ⭐⭐⭐

**Objective:** Verify auto-reconnect on disconnect

**Steps:**
1. **Widget expanded with chat visible**
2. **Stop backend server:**
   ```bash
   pkill -f test_axe_websocket_server
   ```
3. **Connection status changes:**
   - Icon: 🔴 WifiOff
   - Text: "Offline" (red)
   - Input warning: "⚠ Reconnecting to server..."
   - Send button: Disabled
4. **Restart backend:**
   ```bash
   python3 test_axe_websocket_server.py &
   ```
5. **After 3 seconds:** Connection status → "Connected" (green)
6. **Send button:** Enabled again
7. **Browser Console:**
   ```
   [AXE WebSocket] Disconnected
   [AXE WebSocket] Attempting reconnect...
   [AXE WebSocket] Connected
   ```

**Expected Result:** ✅ Auto-reconnect works

---

### Test 9: Keep-Alive Ping/Pong ⭐

**Objective:** Verify ping/pong mechanism

**Steps:**
1. **Widget expanded**
2. **Open Browser DevTools → Network → WS tab**
3. **Click on WebSocket connection**
4. **Watch Messages tab**
5. **Every 30 seconds, you should see:**
   - ⬆️ Outgoing: `{"type":"ping","payload":{"timestamp":xxx}}`
   - ⬇️ Incoming: `{"type":"pong","payload":{"timestamp":xxx}}`

**Expected Result:** ✅ Ping/pong every 30 seconds

---

### Test 10: Diff Toggle View ⭐

**Objective:** Verify diff view toggle

**Steps:**
1. **Generate a diff**
2. **In diff overlay:**
3. **Click "Hide Diff" button**
   - Monaco DiffEditor disappears
   - Shows only new code in `<pre><code>` block
4. **Click "Show Diff" button**
   - Monaco DiffEditor reappears
   - Shows side-by-side comparison

**Expected Result:** ✅ View toggles correctly

---

### Test 11: Multiple Messages ⭐

**Objective:** Verify chat history works

**Steps:**
1. **Send 5 messages:**
   - "Message 1"
   - "Message 2"
   - "Message 3"
   - "Message 4"
   - "Message 5"
2. **Each message:**
   - Appears on right (user)
   - Gets echo response on left (assistant)
3. **Scroll up** in chat area
4. **All 10 messages visible** (5 user + 5 assistant)

**Expected Result:** ✅ Chat history persists

---

### Test 12: Keyboard Shortcuts ⭐

**Objective:** Verify keyboard shortcuts

**Steps:**
1. **In chat input:**
2. **Type:** "First line"
3. **Press Shift+Enter** → New line appears
4. **Type:** "Second line"
5. **Press Enter** → Message sends (both lines)
6. **In code editor:**
7. **Press Cmd/Ctrl+S** → Console log: "Save file" (placeholder)

**Expected Result:** ✅ Shortcuts work

---

## 🐛 Troubleshooting

### Issue: Widget doesn't appear

**Check:**
1. Frontend server running? `curl http://localhost:3002`
2. Browser console for errors
3. Refresh page (Cmd/Ctrl+R)

### Issue: "Offline" status (red)

**Check:**
1. Backend server running? `curl http://localhost:8000/api/health`
2. Browser console for WebSocket errors
3. Network tab → WS connection failed?

**Fix:**
```bash
# Restart backend
python3 test_axe_websocket_server.py &

# Check logs
tail -f test_server.log
```

### Issue: No chat responses

**Check:**
1. Backend logs: `tail -f test_server.log`
2. Look for: `💬 Chat: <your message>`
3. Browser console for WebSocket messages

### Issue: Diff doesn't appear

**Check:**
1. Message contains "code" or "function"? (trigger word)
2. Backend logs show: `📝 Sent diff: xxx`?
3. Browser console: `[AXE WebSocket] Received: diff`?

---

## 📊 Test Results Template

Copy this and fill out as you test:

```markdown
## E2E Test Results - AXE WebSocket

**Date:** 2026-01-10
**Tester:** [Your Name]
**Environment:** Local Development

| # | Test Scenario | Status | Notes |
|---|---------------|--------|-------|
| 1 | Widget State Transitions | ⬜ PASS / ❌ FAIL | |
| 2 | WebSocket Connection Status | ⬜ PASS / ❌ FAIL | |
| 3 | Chat Message Flow | ⬜ PASS / ❌ FAIL | |
| 4 | Code Diff Generation | ⬜ PASS / ❌ FAIL | |
| 5 | Apply Diff Workflow | ⬜ PASS / ❌ FAIL | |
| 6 | Reject Diff Workflow | ⬜ PASS / ❌ FAIL | |
| 7 | File Management | ⬜ PASS / ❌ FAIL | |
| 8 | Auto-Reconnect | ⬜ PASS / ❌ FAIL | |
| 9 | Keep-Alive Ping/Pong | ⬜ PASS / ❌ FAIL | |
| 10 | Diff Toggle View | ⬜ PASS / ❌ FAIL | |
| 11 | Multiple Messages | ⬜ PASS / ❌ FAIL | |
| 12 | Keyboard Shortcuts | ⬜ PASS / ❌ FAIL | |

**Overall:** ___/12 PASS

**Issues Found:**
1.
2.
3.

**Notes:**
-
```

---

## 🔍 Debugging Tips

### View WebSocket Traffic

**Chrome/Edge:**
1. F12 → Network tab
2. Filter: WS (WebSocket)
3. Click connection
4. Messages tab → See all messages

**Firefox:**
1. F12 → Network tab
2. WS filter
3. Click connection → Response tab

### View Console Logs

**Frontend:**
```
[AxeCanvas] WebSocket connected
[AxeExpanded] WebSocket connected
[AXE WebSocket] Received: chat_response
```

**Backend (test_server.log):**
```bash
tail -f test_server.log
```

Output:
```
✅ WebSocket connected: session=xxx
💬 Chat: Hello
📝 Sent diff: xxx
✅ Diff applied: xxx
❌ Diff rejected: xxx
🏓 Pong sent
```

---

## 🎬 Video Recording (Optional)

If you want to record a demo:

```bash
# Install screen recorder
sudo apt install kazam  # Linux
# OR use OBS Studio

# Start recording
# Run all 12 test scenarios
# Save video as "axe-websocket-e2e-test.mp4"
```

---

## ✅ Completion Checklist

After testing, verify:

- [ ] All 12 test scenarios completed
- [ ] Test results documented
- [ ] Screenshots/video captured (optional)
- [ ] Issues logged (if any)
- [ ] Test results shared in docs/

---

## 🚀 Next Steps After Testing

### If All Tests Pass ✅

Proceed to **Phase 3: Event Telemetry**
- POST /api/axe/events endpoint
- PostgreSQL schema
- Anonymization middleware

### If Tests Fail ❌

1. Document failures in detail
2. Create bug reports
3. Fix issues
4. Re-test

---

## 📞 Help

**Stuck? Check:**
1. Server logs (backend + frontend)
2. Browser console
3. Network tab (XHR + WS)
4. Test server documentation

**Still stuck? Debug with:**
```bash
# Backend health
curl http://localhost:8000/api/health

# Frontend health
curl http://localhost:3002

# WebSocket test (manual)
npm install -g wscat
wscat -c ws://localhost:8000/api/axe/ws/test-session
> {"type":"ping","payload":{"timestamp":123}}
```

---

**Happy Testing! 🎉**
