# BRAiN Phase 4 Demo Guide

**Version:** Phase 4 Complete
**Date:** 2024-12-20
**Features:** Robot Simulator, 2D Path Visualization, WebSocket Live Updates, Full Dashboard Suite, Landing Page

---

## Quick Start

### 1. Start Backend

```bash
cd /home/user/BRAiN

# Start FastAPI server with auto-reload
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Verify Backend:**
```bash
curl http://localhost:8000/api/health
# Expected: {"status": "healthy", "version": "..."}
```

### 2. Start Robot Simulator

In a **new terminal**:

```bash
# Start the simulator
curl -X POST http://localhost:8000/api/simulator/start

# Expected response:
# {
#   "status": "started",
#   "robots": ["robot_01", "robot_02", "robot_03", "robot_04", "robot_05"],
#   "message": "Simulator running. Robots will send health metrics every 5 seconds."
# }
```

**Check simulator status:**
```bash
curl http://localhost:8000/api/simulator/status
```

### 3. Start Control Deck (Frontend)

In a **new terminal**:

```bash
cd /home/user/BRAiN/frontend/control_deck

# Install dependencies (if not already installed)
npm install

# Start dev server
npm run dev
```

**Expected Output:**
```
- ready started server on 0.0.0.0:3000, url: http://localhost:3000
- event compiled client and server successfully
```

**Access Control Deck:** http://localhost:3000

### 4. Start Landing Page (Optional)

In a **new terminal**:

```bash
cd /home/user/BRAiN/frontend/landing_page

# Install dependencies (if not already installed)
npm install

# Start dev server
npm run dev
```

**Access Landing Page:** http://localhost:3005

---

## Demo Walkthrough

### Phase 1: Landing Page

**URL:** http://localhost:3005

**What to Test:**
1. **Language Toggle:** Click DE/EN toggle in top-right
2. **Pricing Section:** Verify pricing displays correctly:
   - Grundpreis: 499 € / Monat
   - Variable Nutzung: + 3,60 € / Stunde
   - Early Adopter: 250 € Reservierung
3. **Responsive Design:** Resize browser to test mobile layout
4. **Waitlist Form:** Enter email and click "Zur Warteliste"

**Expected Behavior:**
- Language switches between German and English
- All sections scroll smoothly
- Pricing calculations update correctly
- Form displays success message

---

### Phase 2: Control Deck Dashboard

**URL:** http://localhost:3000

**Dashboard Overview:**
- **Sidebar Navigation:** All Phase 4 modules accessible
- **Dark Theme:** Full dark mode throughout
- **Real-time Updates:** WebSocket status indicators

---

### Phase 3: Predictive Maintenance Dashboard

**Path:** `/maintenance`

**Features to Test:**

#### 1. Fleet Health Summary
- **Fleet Health:** Average health percentage across all robots
- **Active Anomalies:** Count of unacknowledged anomalies
- **Critical Components:** Components with health < 50%
- **Scheduled Tasks:** Upcoming maintenance tasks

**Verify:**
- Cards update in real-time (every 5 seconds via simulator)
- Health percentages decrease over time
- Anomaly count increases when temp > 80°C or vibration > 10

#### 2. WebSocket Live Updates Indicator

**Top-right corner of page:**
- 🟢 **Connected:** Green pulsing dot + "connected"
- 🟡 **Connecting:** Yellow pulsing dot + "connecting"
- ⚫ **Disconnected:** Gray dot + "disconnected"

**Test:**
1. Watch indicator turn green when WebSocket connects
2. Stop backend (`CTRL+C`) → Indicator turns gray
3. Restart backend → Indicator auto-reconnects

#### 3. Component Health Grid

**Grid shows:**
- Component ID (e.g., "motor_fl_robot_01")
- Component Type (motor, battery, sensor)
- Health Score (0-100%)
- Status Badge (Healthy/Warning/Critical)

**Health Thresholds:**
- **Healthy:** Green, health > 70%
- **Warning:** Yellow, health 50-70%
- **Critical:** Red, health < 50%

**Verify:**
- Grid populates with ~20 components (4 per robot × 5 robots)
- Health scores decrease over time
- Status badges change colors based on health

#### 4. Active Anomalies Feed

**Displays anomalies detected by the system:**
- **Temperature Spike:** temp > 80°C
- **Vibration:** vibration > 10
- **Degradation:** health < 40%

**Each anomaly shows:**
- Anomaly Type
- Severity (low, medium, high, critical)
- Component ID
- Timestamp
- Acknowledge button

**Test:**
1. Wait for simulator to generate anomalies (health < 60% triggers temp spikes)
2. Click "Acknowledge" → Anomaly disappears from list
3. Verify new anomalies appear in real-time (WebSocket updates)

#### 5. Failure Predictions

**Shows predictions for components likely to fail:**
- Component ID
- Predicted Failure Time (hours from now)
- Probability (0-100%)
- Recommended Actions

**Verify:**
- Predictions appear when health < 75%
- Probability increases as health decreases
- Recommended actions suggest maintenance or replacement

#### 6. Maintenance Schedule

**Upcoming maintenance tasks:**
- Task type (inspection, repair, replacement)
- Component ID
- Scheduled time
- Status (scheduled, in_progress, completed)

**Verify:**
- Schedule displays properly formatted dates
- Status badges show correct colors

---

### Phase 4: Advanced Navigation Dashboard

**Path:** `/navigation`

**Features to Test:**

#### 1. Navigation Statistics Cards
- **Active Goals:** Number of active navigation goals
- **Planned Paths:** Number of planned paths
- **Tracked Robots:** Robots currently navigating
- **Total Obstacles:** Detected obstacles

#### 2. Real-Time 2D Path Visualization

**Canvas Features:**
- **Grid:** 1-meter grid lines with origin marker
- **Robots:** Colored circles with orientation arrows
  - 🔵 Blue: Idle
  - 🟢 Green: Moving
  - 🟡 Amber: Charging
  - 🔴 Red: Error
- **Obstacles:**
  - Gray: Static obstacles
  - Pink: Humans (dynamic)
- **Planned Paths:** Purple dashed lines showing future trajectory
- **Formations:** Teal circles grouping robots
- **Velocity Vectors:** Arrows showing robot direction and speed
- **Battery Indicators:** Color-coded battery bars above robots

**Interactive Controls:**
- **Pause/Resume:** Freeze/unfreeze simulation
- **Settings Panel:** Toggle grid, IDs, velocities, paths, formations

**Test:**
1. **Watch robots move:** Robots navigate autonomously
2. **Pause simulation:** Click "⏸ Pause" → Movement stops
3. **Resume:** Click "▶ Resume" → Movement continues
4. **Toggle settings:** Click "⚙ Settings" → Check/uncheck options
5. **Verify legend:** Match colors to robots and obstacles
6. **Battery drain:** Watch battery bars decrease over time

**Expected Behavior:**
- Robots move smoothly across canvas
- Paths update dynamically
- Obstacles move (humans have velocity)
- Robots wrap around world bounds (-20 to +20 meters)
- Formation appears occasionally (3 robots in line)

#### 3. Social Navigation Parameters

**Editable parameters:**
- **Personal Space Zones:** Intimate, Personal, Social (meters)
- **Behavior Weights:** Efficiency, Safety, Comfort (0-1)
- **Crowd Handling:** Max density, avoidance margin
- **Approach Behavior:** Angle (degrees), passing side preference

**Test:**
1. Click "Edit Parameters"
2. Adjust sliders
3. Click "Save" → Parameters update
4. Click "Cancel" → Reverts to previous values

---

### Phase 5: Multi-Robot Collaboration Dashboard

**Path:** `/collaboration`

**Features to Test:**

#### 1. Collaboration Statistics
- **Active Tasks:** Number of collaborative tasks
- **Active Formations:** Current formations
- **Connected Robots:** Robots in collaboration network
- **Shared Models:** Number of shared world models

#### 2. Formation Types
- **Line:** Robots in single file
- **Column:** Robots in vertical column
- **Wedge:** V-formation
- **Circle:** Circular formation
- **Grid:** Grid pattern

**Test:**
1. View formation type badges
2. Verify all formation types listed

#### 3. Task Allocation
- View task allocation strategy (auction-based)
- See allocated tasks list

---

### Phase 6: Learning from Demonstration Dashboard

**Path:** `/learning`

**Features to Test:**

#### 1. Learning Statistics
- **Recorded Demos:** Number of demonstrations
- **Trained Policies:** Number of policies
- **Total Trajectories:** Sum of all trajectories
- **Active Learners:** Robots currently learning

#### 2. Recording Methods
- **Teleoperation:** Manual control
- **Kinesthetic:** Physical guidance
- **Vision-Based:** Camera-based recording

#### 3. Learning Algorithms
- **BC:** Behavioral Cloning
- **DAgger:** Dataset Aggregation
- **GAIL:** Generative Adversarial Imitation Learning
- **IRL:** Inverse Reinforcement Learning

**Verify:**
- All methods and algorithms listed
- Descriptions accurate

---

### Phase 7: WebSocket Functionality Test

**Test Real-Time Updates:**

1. **Open Maintenance Dashboard** (`/maintenance`)
2. **Open Browser DevTools** (F12)
3. **Go to Console tab**
4. **Look for WebSocket messages:**
   ```
   [WebSocket] Connecting to ws://localhost:8000/api/ws/maintenance...
   [WebSocket] Connected to maintenance
   ```

5. **Watch for live updates:**
   - Every 5 seconds, simulator broadcasts health metrics
   - Anomalies appear instantly when detected
   - Analytics cards update automatically

6. **Test disconnect/reconnect:**
   - Stop backend (CTRL+C in uvicorn terminal)
   - Observe console: `[WebSocket] Disconnected from maintenance`
   - Observe status indicator: turns gray
   - Restart backend
   - Observe console: `[WebSocket] Reconnecting to maintenance...`
   - Observe status indicator: turns green

---

## API Endpoints Reference

### Simulator Endpoints

```bash
# Start simulator
POST /api/simulator/start

# Stop simulator
POST /api/simulator/stop

# Get simulator status
GET /api/simulator/status
# Response: { "running": true/false, "robot_count": 5, "robots": [...] }

# Get simulator info
GET /api/simulator/info
```

### Maintenance Endpoints

```bash
# Get maintenance info
GET /api/maintenance/info

# Get analytics
GET /api/maintenance/analytics

# Get anomalies
GET /api/maintenance/anomalies?acknowledged=false

# Get predictions
GET /api/maintenance/predictions?min_probability=0.5

# Record health metrics (called by simulator)
POST /api/maintenance/metrics
```

### WebSocket Endpoints

```bash
# Maintenance updates
ws://localhost:8000/api/ws/maintenance

# Simulator updates
ws://localhost:8000/api/ws/simulator

# Collaboration updates
ws://localhost:8000/api/ws/collaboration

# Navigation updates
ws://localhost:8000/api/ws/navigation

# WebSocket status
GET /api/ws/status
# Response: { "active_channels": [...], "connections": {...}, "total_connections": N }
```

---

## Expected Demo Flow

### Minute 0-1: System Startup
1. Start backend → Healthy
2. Start simulator → 5 robots initialized
3. Start frontend → Dashboard loads

### Minute 1-2: Initial Data Load
1. Open Maintenance dashboard
2. WebSocket connects (green indicator)
3. Fleet health shows ~85-95% (initial robot health)
4. Component grid populates with 20 components

### Minute 2-5: Health Degradation
1. Watch health scores decrease (degradation rate: 0.01-0.05 per update)
2. First anomalies appear (temp spikes, vibration)
3. Active Anomalies counter increases
4. Failure predictions generated for components with health < 75%

### Minute 5-10: Real-Time Updates
1. Analytics cards update every 5 seconds
2. New anomalies appear in feed
3. Health grid shows color changes (green → yellow → red)
4. WebSocket messages visible in DevTools console

### Minute 10+: Advanced Features
1. Navigate to `/navigation`
2. Watch 2D path visualization with robots moving
3. Pause/Resume simulation
4. Toggle settings (grid, IDs, velocities)
5. Navigate to other dashboards (`/collaboration`, `/learning`)

---

## Troubleshooting

### Backend Issues

**Problem:** Backend won't start
```bash
# Check port 8000 is not in use
lsof -i :8000
# Kill process if needed
kill -9 <PID>
```

**Problem:** Simulator not generating data
```bash
# Check simulator status
curl http://localhost:8000/api/simulator/status

# If running: false, restart it
curl -X POST http://localhost:8000/api/simulator/start
```

### Frontend Issues

**Problem:** Frontend won't start
```bash
# Clear Next.js cache
rm -rf .next
npm run dev
```

**Problem:** WebSocket not connecting
- Verify backend is running on port 8000
- Check DevTools console for errors
- Ensure WebSocket URL is correct (ws://localhost:8000/api/ws/...)

**Problem:** 2D Visualization not rendering
- Check browser console for errors
- Verify Canvas element is created
- Check if useEffect is running (add console.log)

### Data Issues

**Problem:** No anomalies appearing
- Wait longer (health needs to drop below 60% for temp spikes)
- Check simulator is running: `curl http://localhost:8000/api/simulator/status`
- Verify health degradation is happening (refresh analytics)

**Problem:** Components not updating
- Check WebSocket connection status (should be green)
- Verify simulator is sending updates (DevTools Network tab → WS)
- Refresh page to force data reload

---

## Performance Metrics

**Expected Load:**
- **Backend:** < 5% CPU usage (idle)
- **Frontend:** < 100 MB memory
- **WebSocket:** ~20 messages/second (during simulator run)
- **Canvas FPS:** 10 FPS (100ms update interval)

**Data Volume:**
- **5 robots** × **4 components** = **20 components**
- **20 components** × **1 update/5s** = **4 updates/second**
- **WebSocket messages:** ~240 messages/minute

---

## Key Features Demonstrated

### ✅ Backend Features
- [x] FastAPI async architecture
- [x] Auto-discovery router registration
- [x] WebSocket real-time broadcasting
- [x] Robot simulator with health degradation
- [x] Anomaly detection (threshold + statistical)
- [x] Failure prediction (trend analysis)
- [x] Multi-module system (4 Phase 4 modules)

### ✅ Frontend Features
- [x] Next.js 14 App Router
- [x] TypeScript type safety
- [x] Tailwind CSS styling
- [x] Real-time WebSocket hooks
- [x] 2D Canvas visualization
- [x] Responsive design
- [x] Dark mode theme
- [x] Bilingual landing page (DE/EN)

### ✅ Integration Features
- [x] Backend → Frontend API communication
- [x] WebSocket live updates
- [x] Simulator → Maintenance integration
- [x] Real-time dashboard synchronization
- [x] Auto-reconnect on disconnect

---

## Next Steps

### Immediate (Phase 5)
- [ ] Hardware deployment (excluded from current scope)
- [ ] Connect to real ROS2 robots
- [ ] SLAM integration testing
- [ ] Vision pipeline deployment

### Future Enhancements
- [ ] Database persistence (PostgreSQL)
- [ ] User authentication
- [ ] API rate limiting
- [ ] Advanced ML models (replace mocks)
- [ ] Multi-user WebSocket rooms
- [ ] Historical data visualization
- [ ] Export/import functionality
- [ ] Mobile app (React Native)

---

## Support

**Documentation:**
- Main README: `/home/user/BRAiN/README.md`
- CLAUDE.md: `/home/user/BRAiN/CLAUDE.md`
- CHANGELOG: `/home/user/BRAiN/CHANGELOG.md`

**Logs:**
```bash
# Backend logs (uvicorn terminal)
# WebSocket logs in browser DevTools console
# Next.js logs in npm run dev terminal
```

**Contact:**
For issues or questions, please refer to project documentation.

---

**Demo Guide Version:** 1.0.0
**Last Updated:** 2024-12-20
**Status:** ✅ Complete and Ready for Demo
