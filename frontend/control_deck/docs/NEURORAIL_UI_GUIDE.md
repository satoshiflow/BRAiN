# NeuroRail ControlDeck UI - User Guide

**Version:** 1.0.0
**Sprint:** 5+6 (Phase 3)
**Status:** Production Ready

---

## Overview

The **NeuroRail ControlDeck UI** provides real-time monitoring and observability for the NeuroRail execution governance system with:

- ✅ **5 interactive dashboards** for comprehensive monitoring
- ✅ **Real-time updates** via Server-Sent Events (SSE)
- ✅ **Complete trace chain visualization** (Mission → Plan → Job → Attempt → Resource)
- ✅ **Circuit breaker monitoring** with live status updates
- ✅ **Budget enforcement metrics** with interactive charts
- ✅ **Job lifecycle tracking** with state flow diagrams
- ✅ **Type-safe React components** built with Next.js 14 and TypeScript

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Trace Explorer](#trace-explorer)
4. [Reflex Monitor](#reflex-monitor)
5. [Budget Dashboard](#budget-dashboard)
6. [Lifecycle Monitor](#lifecycle-monitor)
7. [Real-Time Updates](#real-time-updates)
8. [Navigation](#navigation)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Accessing the ControlDeck

**Local Development:**
- URL: http://localhost:3001/neurorail
- Prerequisites: Backend running on port 8000

**Production:**
- URL: https://brain.falklabs.de/neurorail

### Navigation Menu

The NeuroRail section is accessible from the main navigation bar:

```
Home → NeuroRail → [Dashboard | Trace | Reflex | Budget | Lifecycle]
```

### First Time Setup

1. **Verify backend connection:**
   - Check that backend is running: http://localhost:8000/health
   - SSE endpoint should be accessible: http://localhost:8000/api/neurorail/v1/stream/events

2. **Open NeuroRail dashboard:**
   - Navigate to http://localhost:3001/neurorail
   - You should see 4 monitor cards with real-time data

3. **Check SSE connection:**
   - Look for "Connected" status indicator (green dot)
   - If disconnected, check browser console for errors

---

## Dashboard Overview

### Main Dashboard (`/neurorail`)

The main dashboard provides quick access to all monitoring tools:

**Monitor Cards:**

1. **Trace Explorer**
   - Icon: 🔍 Search
   - Description: "Complete trace chain visualization"
   - Link: `/neurorail/trace`

2. **Reflex Monitor**
   - Icon: ⚡ Zap
   - Description: "Real-time reflex system monitoring"
   - Link: `/neurorail/reflex`

3. **Budget Dashboard**
   - Icon: 💰 DollarSign
   - Description: "Budget enforcement metrics and charts"
   - Link: `/neurorail/budget`

4. **Lifecycle Monitor**
   - Icon: 🔄 Activity
   - Description: "Job lifecycle state monitoring"
   - Link: `/neurorail/lifecycle`

**Real-Time Event Stream:**

Below the monitor cards, the dashboard shows:
- **Live event count** (updates in real-time)
- **Recent events table** with:
  - Channel (color-coded badges)
  - Event Type
  - Timestamp (relative: "2 seconds ago", "1 minute ago")
  - Entity ID (if present)

**Filter Controls:**

- **Channel Filter:** Select specific channels (audit, lifecycle, metrics, reflex, governor, enforcement)
- **Event Type Filter:** Filter by event type
- **Clear Events Button:** Clear event history

---

## Trace Explorer

**URL:** `/neurorail/trace`

**Purpose:** Explore complete trace chains from mission to resource with full audit trail

### Features

1. **Search Interface**
   - **Entity Type Selector:** Choose between Mission, Plan, Job, Attempt
   - **Entity ID Input:** Enter the entity ID (e.g., `a_abc123`)
   - **Explore Button:** Fetch trace chain

2. **Trace Chain Visualization**

   Shows hierarchical structure:
   ```
   Mission (m_abc123)
     ↓
   Plan (p_xyz789)
     ↓
   Job (j_qwe456)
     ↓
   Attempt (a_asd123)
     ↓
   Resource (r_fgh789)
   ```

   Each level shows:
   - Entity ID (clickable)
   - Created timestamp
   - Entity-specific metadata (tags, type, parameters)

3. **Audit Events Timeline**

   Displays all audit events for the trace chain:
   - **Event Type** badge (color-coded by severity)
   - **Message** with full details
   - **Timestamp** (ISO 8601 format)
   - **Severity** indicator (info, warning, error)

4. **Lifecycle Transitions**

   Shows state machine transitions:
   - **From State → To State**
   - **Transition Type** (enqueue, start, succeed, fail, timeout)
   - **Timestamp**
   - **Metadata** (expandable)

### Usage Examples

**Example 1: Trace an Attempt**

1. Select "Attempt" from entity type dropdown
2. Enter attempt ID: `a_abc123def456`
3. Click "Explore"
4. View complete chain: Mission → Plan → Job → Attempt

**Example 2: Find Mission for a Job**

1. Select "Job" from entity type dropdown
2. Enter job ID: `j_xyz789uvw012`
3. Click "Explore"
4. View parent chain: Mission → Plan → Job

**Example 3: Review Audit Trail**

1. After exploring an entity, scroll to "Audit Events" section
2. Filter by severity (info, warning, error)
3. Click on event to expand details

---

## Reflex Monitor

**URL:** `/neurorail/reflex`

**Purpose:** Real-time monitoring of circuit breakers, triggers, and reflex actions

### Features

1. **Circuit Breaker Status Cards**

   Each circuit breaker shows:
   - **Circuit ID** (e.g., `circuit_timeout_llm_call`)
   - **Current State** (CLOSED, OPEN, HALF_OPEN)
     - 🟢 CLOSED: Operating normally
     - 🔴 OPEN: Circuit broken, rejecting requests
     - 🟡 HALF_OPEN: Testing recovery
   - **Failure Count** / **Threshold**
   - **Last Failure Timestamp**
   - **State Badge** (color-coded)

2. **Trigger Activations**

   Real-time list of trigger activations:
   - **Trigger ID**
   - **Condition** that triggered
   - **Entity ID** affected
   - **Timestamp**
   - **Status Badge**

3. **Reflex Actions Executed**

   History of automated reflex actions:
   - **Action Type** (suspend, cooldown, probe, auto_resume)
   - **Target Entity**
   - **Reason** for action
   - **Timestamp**
   - **Action Badge** (color-coded)

4. **Live Lifecycle State Stream**

   Real-time state changes:
   - **Entity Type** (mission, job, attempt)
   - **Entity ID**
   - **State Transition** (from → to)
   - **Timestamp**

### State Indicators

**Circuit Breaker States:**
- 🟢 **CLOSED**: Normal operation, requests flowing
- 🔴 **OPEN**: Circuit broken, requests blocked
- 🟡 **HALF_OPEN**: Testing if service recovered

**Action Types:**
- 🔴 **SUSPEND**: Entity suspended due to violations
- 🟡 **COOLDOWN**: Cooldown period activated
- 🔵 **PROBE**: Probing attempt (testing recovery)
- 🟢 **AUTO_RESUME**: Automatic resumption after recovery

### Usage Examples

**Example 1: Monitor Circuit Breaker Health**

1. Navigate to `/neurorail/reflex`
2. Check "Circuit Breaker Status" section
3. Look for OPEN circuits (red badges)
4. Review failure count vs. threshold

**Example 2: Investigate Repeated Failures**

1. Find circuit with high failure count
2. Check "Trigger Activations" for matching trigger ID
3. Review "Reflex Actions" to see automated responses
4. Use "Live Lifecycle Stream" to see real-time state changes

**Example 3: Verify Auto-Recovery**

1. Wait for circuit to enter HALF_OPEN state
2. Monitor "Reflex Actions" for PROBE actions
3. Check if circuit transitions back to CLOSED
4. Verify AUTO_RESUME action logged

---

## Budget Dashboard

**URL:** `/neurorail/budget`

**Purpose:** Budget enforcement metrics with interactive charts and real-time updates

### Features

1. **Summary Cards (4 metrics)**

   **Timeout Violations:**
   - Total count of timeout events
   - 🔴 Red badge with count

   **Budget Exceeded:**
   - Total budget overruns (tokens, cost)
   - 🟡 Orange badge with count

   **Retry Exhausted:**
   - Total max retry failures
   - 🟣 Purple badge with count

   **Active Attempts:**
   - Currently running attempts
   - 🔵 Blue badge with count

2. **Timeout Trend Chart (Line Chart)**

   - **X-axis:** Time (last 100 events)
   - **Y-axis:** Cumulative timeout count
   - **Color:** Blue line
   - **Updates:** Real-time as timeout events occur

3. **Budget Metrics Chart (Bar Chart)**

   - **Bars:**
     - Timeouts (blue)
     - Budget Exceeded (orange)
     - Retries Exhausted (purple)
   - **Y-axis:** Count
   - **Updates:** Real-time

4. **Violation Distribution (Pie Chart)**

   - **Slices:**
     - Timeouts (blue)
     - Budget Exceeded (orange)
     - Retries Exhausted (purple)
   - **Percentages:** Calculated dynamically
   - **Legend:** Interactive (click to filter)

5. **Recent Violations Table**

   Latest enforcement events:
   - **Event Type** (timeout_triggered, budget_exceeded, retry_exhausted)
   - **Entity ID** (attempt or job)
   - **Details** (timeout_ms, tokens_used, cost, retry_count)
   - **Timestamp**

### Chart Interactions

**Line Chart:**
- Hover to see exact values
- Auto-scales as data grows

**Bar Chart:**
- Hover to see exact counts
- Bars animate on updates

**Pie Chart:**
- Hover to see percentage
- Click legend to hide/show slices

### Usage Examples

**Example 1: Monitor Timeout Trends**

1. Navigate to `/neurorail/budget`
2. Check "Timeout Trend" line chart
3. Look for upward trend (increasing timeouts)
4. Investigate spike in "Recent Violations" table

**Example 2: Identify Budget Issues**

1. Check "Budget Exceeded" summary card
2. Review "Budget Metrics" bar chart
3. Compare timeouts vs. budget violations
4. Click violations in table to see details

**Example 3: Retry Analysis**

1. Check "Retry Exhausted" summary card
2. Review "Violation Distribution" pie chart
3. See what percentage are retry failures
4. Investigate patterns in "Recent Violations"

---

## Lifecycle Monitor

**URL:** `/neurorail/lifecycle`

**Purpose:** Real-time job lifecycle state monitoring with state flow visualization

### Features

1. **State Summary Cards (7 states)**

   Each card shows:
   - **State Name** (PENDING, QUEUED, RUNNING, SUCCEEDED, FAILED, TIMEOUT, CANCELLED)
   - **Count** of jobs/attempts in this state
   - **Color Badge**:
     - 🔵 PENDING (blue)
     - 🟡 QUEUED (yellow)
     - 🟢 RUNNING (green)
     - 🟢 SUCCEEDED (green)
     - 🔴 FAILED (red)
     - 🟠 TIMEOUT (orange)
     - ⚫ CANCELLED (gray)

2. **State Flow Diagram**

   Visual representation of allowed transitions:
   ```
   PENDING
     ↓ enqueue
   QUEUED
     ↓ start
   RUNNING
     ↓ succeed / fail / timeout / cancel
   SUCCEEDED / FAILED / TIMEOUT / CANCELLED
   ```

   **Terminal States:**
   - SUCCEEDED
   - FAILED
   - TIMEOUT
   - CANCELLED

3. **Active Jobs List**

   Real-time list of non-terminal jobs:
   - **Job ID**
   - **Current State** (color-coded badge)
   - **Entity Type** (job, attempt)
   - **Last Updated** (relative time)

4. **Recent Transitions Table**

   Last 50 state transitions:
   - **Entity Type** (mission, job, attempt)
   - **Entity ID**
   - **Transition** (from → to)
   - **Transition Type** (enqueue, start, succeed, fail, etc.)
   - **Timestamp**

### State Machine Rules

**Allowed Transitions:**

| From State | To State | Transition Type |
|------------|----------|-----------------|
| PENDING | QUEUED | enqueue |
| PENDING | CANCELLED | cancel |
| QUEUED | RUNNING | start |
| QUEUED | CANCELLED | cancel |
| RUNNING | SUCCEEDED | succeed |
| RUNNING | FAILED | fail |
| RUNNING | TIMEOUT | timeout |
| RUNNING | CANCELLED | cancel |

**Terminal States:**
- SUCCEEDED (✅ success)
- FAILED (❌ error)
- TIMEOUT (⏱️ timeout)
- CANCELLED (🚫 manual cancel)

### Usage Examples

**Example 1: Monitor Active Jobs**

1. Navigate to `/neurorail/lifecycle`
2. Check "Active Jobs" section
3. See current state distribution in summary cards
4. Monitor jobs in RUNNING state

**Example 2: Track Job Progression**

1. Find specific job in "Active Jobs" list
2. Watch state transitions in "Recent Transitions" table
3. Verify transitions follow state flow diagram
4. Check for failures (FAILED, TIMEOUT states)

**Example 3: Identify Stuck Jobs**

1. Check "QUEUED" summary card for high count
2. Review "Active Jobs" list for old QUEUED jobs
3. Check "Recent Transitions" for missing start transitions
4. Investigate why jobs aren't starting

---

## Real-Time Updates

### SSE Connection Status

**Connection Indicator:**
- 🟢 **Connected**: SSE stream active, receiving events
- 🔴 **Disconnected**: Connection lost, will auto-reconnect
- 🟡 **Connecting**: Attempting to establish connection

**Auto-Reconnect:**
- Automatic reconnection after 3 seconds
- Exponential backoff on repeated failures
- Manual reconnect button available

### Event Channels

All dashboards subscribe to relevant SSE channels:

| Dashboard | Channels Subscribed |
|-----------|---------------------|
| Main Dashboard | `all` (all channels) |
| Trace Explorer | `audit`, `lifecycle` |
| Reflex Monitor | `reflex`, `lifecycle` |
| Budget Dashboard | `enforcement` |
| Lifecycle Monitor | `lifecycle` |

### Update Frequency

**Real-time updates:**
- Events appear within **< 100ms** of backend publish
- No polling, push-based architecture
- Efficient: only subscribed events delivered

**Event Buffer:**
- Last **100 events** buffered per channel
- Late subscribers receive buffer replay
- Option to disable replay (show only new events)

---

## Navigation

### Main Navigation Bar

```
Home | Dashboard | NeuroRail ▼
                    ├─ Dashboard
                    ├─ Trace Explorer
                    ├─ Reflex Monitor
                    ├─ Budget Dashboard
                    └─ Lifecycle Monitor
```

### Breadcrumbs

Each page shows breadcrumb navigation:
```
Home > NeuroRail > [Current Page]
```

### Quick Links

From main NeuroRail dashboard:
- Click monitor cards to navigate to specific tools
- Use top navigation for direct access

---

## Troubleshooting

### Issue 1: SSE Connection Failed

**Symptoms:**
- Red "Disconnected" indicator
- No real-time updates

**Solutions:**
1. Check backend is running: http://localhost:8000/health
2. Verify SSE endpoint: http://localhost:8000/api/neurorail/v1/stream/events
3. Check browser console for CORS errors
4. Verify `CORS_ORIGINS` in backend `.env`

### Issue 2: No Events Showing

**Symptoms:**
- Connected but no events in dashboard

**Solutions:**
1. Generate events by triggering backend operations
2. Check channel filters (ensure correct channels selected)
3. Verify event types match filter
4. Try "Clear Events" and wait for new events

### Issue 3: Charts Not Updating

**Symptoms:**
- Real-time events arrive but charts don't update

**Solutions:**
1. Refresh page (Ctrl+R)
2. Check browser console for JavaScript errors
3. Verify React component re-rendering (React DevTools)

### Issue 4: Trace Chain Not Found

**Symptoms:**
- "No trace chain found" message in Trace Explorer

**Solutions:**
1. Verify entity ID format (e.g., `a_abc123def456`)
2. Ensure entity exists in backend
3. Try different entity type
4. Check backend logs for errors

### Issue 5: Slow Performance

**Symptoms:**
- UI laggy, charts update slowly

**Solutions:**
1. Clear event history (click "Clear Events")
2. Reduce number of open dashboards
3. Use specific channel filters (not `all`)
4. Close other browser tabs

### Issue 6: Missing Data in Cards

**Symptoms:**
- Summary cards show 0 or "No data"

**Solutions:**
1. Wait for events to arrive (real-time updates)
2. Check if backend has generated events
3. Verify SSE connection is active
4. Refresh page to replay buffer

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | Refresh page |
| `Esc` | Close modal/dialog |
| `Ctrl+K` | Open command palette (if implemented) |

---

## Browser Support

**Supported Browsers:**
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

**Required Features:**
- EventSource API (SSE)
- ES6 JavaScript
- CSS Grid/Flexbox

---

## Performance Tips

1. **Use Specific Channels:**
   - Subscribe to only needed channels
   - Avoid `all` channel for performance

2. **Clear Event History:**
   - Periodically clear events to reduce memory
   - Use "Clear Events" button

3. **Limit Open Dashboards:**
   - Close unused dashboard tabs
   - Each dashboard has separate SSE connection

4. **Filter Events:**
   - Use event type filters to reduce noise
   - Filter by entity ID for specific traces

---

## API Integration

### Fetching Data Programmatically

All dashboards use the NeuroRail API client:

```typescript
import { neurorailAPI } from '@/lib/neurorail-api';

// Get trace chain
const trace = await neurorailAPI.identity.getTraceChain('attempt', 'a_abc123');

// Get lifecycle state
const state = await neurorailAPI.lifecycle.getState('job', 'j_xyz789');

// Query audit events
const events = await neurorailAPI.audit.getEvents({
  mission_id: 'm_abc123',
  limit: 50
});
```

### SSE Hook Usage

```typescript
import { useSSE } from '@/hooks/use-sse';

function MyComponent() {
  const { events, latestEvent, isConnected } = useSSE({
    channels: ['audit', 'lifecycle'],
    eventTypes: ['execution_start'],
    autoReconnect: true,
    reconnectDelay: 3000
  });

  return (
    <div>
      <p>Connected: {isConnected ? 'Yes' : 'No'}</p>
      <p>Total Events: {events.length}</p>
      {latestEvent && <div>Latest: {latestEvent.event_type}</div>}
    </div>
  );
}
```

---

## Changelog

**1.0.0** (2025-12-31)
- Initial release
- 5 interactive dashboards
- Real-time SSE updates
- Complete trace chain visualization
- Circuit breaker monitoring
- Budget enforcement metrics with Recharts
- Lifecycle state tracking

---

## Support

For issues or questions:
- GitHub: https://github.com/satoshiflow/BRAiN/issues
- Documentation: `/frontend/control_deck/docs/`

---

## Next Steps

**Recommended Learning Path:**

1. **Start with Main Dashboard** (`/neurorail`)
   - Familiarize with layout and navigation
   - Watch real-time event stream

2. **Explore Trace Chain** (`/neurorail/trace`)
   - Search for an attempt ID
   - Review complete trace and audit trail

3. **Monitor Reflex System** (`/neurorail/reflex`)
   - Check circuit breaker states
   - Watch for trigger activations

4. **Analyze Budget Metrics** (`/neurorail/budget`)
   - Review timeout trends
   - Check budget violations

5. **Track Lifecycle** (`/neurorail/lifecycle`)
   - Monitor active jobs
   - Verify state transitions

**Advanced Usage:**
- Combine dashboards for comprehensive monitoring
- Use filters for targeted analysis
- Correlate events across multiple dashboards
