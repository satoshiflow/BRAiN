# ControlDeck v2 - Future Components Plan

**Datum:** 2026-02-21  
**Basierend auf:** v0 Templates Inspiration (Futuristic/Cyberpunk) + BRAiN OS Design System  

---

## Inspiration aus Templates

### Gemeinsame Elemente (Futuristic Dashboards)

| Element | Beschreibung | BRAiN OS Anpassung |
|---------|-------------|-------------------|
| **Glow Effects** | Neon-Glow um aktive Elemente | Sehr subtil, nur für Focus/Active |
| **Grid Background** | Subtile Grid-Lines im Hintergrund | ✅ Kann hinzugefügt werden |
| **Progress Rings** | Kreisförmige Progress-Indikatoren | Für Agent Status |
| **Terminal/Console** | Monospace Logs mit Scroll | Für Event Feed |
| **Animated Charts** | Echtzeit-Charts mit Animation | Für Metrics |
| **Card Hover Effects** | Lift + Glow on Hover | Subtil, nicht zu viel |
| **Status Indicators** | Pulsierende Dots, Farb-Transitions | ✅ Bereits implementiert |

### Was wir NICHT machen (zu Cyberpunk/Gaming)

❌ Starke Neon-Farben (Pink, Cyan, Green)  
❌ Glitch Effects  
❌ Animated Backgrounds  
❌ "Hacker" Terminal Look  
❌ Starke Schatten/Glows überall  

---

## Zukünftige Komponenten (Priorisiert)

### Phase 1: API Integration (Jetzt)

| Komponente | Zweck | API Endpoint | Backend Status |
|------------|-------|--------------|----------------|
| `useMissions()` | Mission Daten | `GET /api/missions/queue` | ✅ Verfügbar |
| `useEvents()` | Event Stream | `GET /api/events` | ✅ Verfügbar |
| `useMissionHealth()` | Health Status | `GET /api/missions/health` | ✅ Verfügbar |
| `useAgents()` | Agent Info | `GET /api/missions/agents/info` | ⚠️ Placeholder |
| `useSystemStream()` | SSE Events | `GET /api/system_stream/*` | ✅ Verfügbar |

### Phase 2: Erweiterte UI (Nach API)

| Komponente | Zweck | Inspiration | Komplexität |
|------------|-------|-------------|-------------|
| `ConsoleFeed` | Terminal-ähnlicher Event Stream | Cyberpunk Terminal | Mittel |
| `CircularProgress` | Ring-Progress für Agenten | Futuristic Gauge | Mittel |
| `LineChart` | Echtzeit Metrics Chart | Dashboard Charts | Mittel |
| `HeatmapGrid` | System-Status Heatmap | Server Monitoring | Hoch |
| `Timeline` | Zeitstrahl für Events | Activity Timeline | Mittel |
| `DataTable` | Erweiterte Tabelle mit Sort/Filter | Data Grids | Mittel |

### Phase 3: Advanced Features (Später)

| Komponente | Zweck | API Endpoint | Backend Status |
|------------|-------|--------------|----------------|
| `MissionCreateForm` | Neue Mission erstellen | `POST /api/missions/enqueue` | ✅ Verfügbar |
| `MissionDetailDrawer` | Mission Details | `GET /api/missions/queue/{id}` | ⚠️ Fehlend |
| `AgentDetail` | Agent Details | `GET /api/agents/{id}` | ❌ Nicht vorhanden |
| `WorkflowEditor` | Workflow Visual Editor | `GET/POST /api/business/*` | ✅ Verfügbar |
| `RealtimeMap` | Agent Locations | WebSocket / SSE | ⚠️ Partial |

---

## Backend API Status

### ✅ Vorhanden & Stabil

```
GET  /api/missions/info
GET  /api/missions/health
POST /api/missions/enqueue
GET  /api/missions/queue
GET  /api/missions/events/history
GET  /api/missions/events/stats
GET  /api/missions/worker/status
GET  /api/missions/agents/info        # Placeholder

GET  /api/events                      # CRUD
GET  /api/events/stats

GET  /api/system_stream/*             # SSE

GET  /api/business/*                  # Workflows
```

### ⚠️ Erweiterung Nötig

```
GET  /api/missions/queue/{id}         # Detail für Mission
GET  /api/agents                      # Liste aller Agenten
GET  /api/agents/{id}                 # Agent Detail
GET  /api/agents/{id}/metrics         # Agent Metrics
GET  /api/dashboard/stats             # Aggregierte Stats
GET  /api/dashboard/widgets           # Widget Config
```

### ❌ Nicht Vorhanden (Neue Module)

```
GET  /api/fleet/*                     # Fleet Management
GET  /api/neurorail/*                 # Budget/Tracing
GET  /api/webgenesis/*                # Site Management
GET  /api/health/checks               # Health Check Details
```

---

## Komponenten-Spezifikationen

### 1. ConsoleFeed (Terminal-ähnlich)

```typescript
interface ConsoleFeedProps {
  events: Event[];
  maxLines?: number;
  autoScroll?: boolean;
  showTimestamp?: boolean;
  showSeverity?: boolean;
  filter?: 'all' | 'error' | 'warning' | 'info';
}
```

**Features:**
- Monospace Font (JetBrains Mono)
- Farbige Severity-Prefixes
- Auto-scroll zu neuen Events
- Filter nach Severity
- Copy-to-Clipboard

**Design:**
- Darker Background (#0B1220)
- Border-left Color je Severity
- Compact Line-Height

---

### 2. CircularProgress (Agent Status)

```typescript
interface CircularProgressProps {
  value: number;        // 0-100
  size?: 'sm' | 'md' | 'lg';
  color?: 'primary' | 'success' | 'warning' | 'danger';
  label?: string;
  sublabel?: string;
  showValue?: boolean;
}
```

**Features:**
- SVG Ring mit Progress
- Animation bei Value-Change
- Center Label
- Subtle Glow on 100%

**Design:**
- Stroke Width: 8px
- Rounded Caps
- Background Track: border-muted

---

### 3. LineChart (Echtzeit Metrics)

```typescript
interface LineChartProps {
  data: { timestamp: string; value: number }[];
  title?: string;
  color?: string;
  showArea?: boolean;
  showGrid?: boolean;
  height?: number;
}
```

**Features:**
- Recharts Basis
- Auto-updating
- Tooltip mit Zeit
- Gradient Area Fill

**Design:**
- Line: info color (#3B82F6)
- Area: info/10 opacity
- Grid: border-muted/30
- Keine Gold-Farbe (nur für Primary Actions)

---

### 4. HeatmapGrid (System Status)

```typescript
interface HeatmapGridProps {
  cells: {
    id: string;
    label: string;
    status: 'healthy' | 'warning' | 'critical' | 'offline';
    value?: number;
  }[];
  columns?: number;
}
```

**Features:**
- Grid Layout
- Farbcodierung nach Status
- Hover Details
- Click für Drilldown

**Design:**
- Healthy: success/20
- Warning: warning/20
- Critical: danger/20
- Offline: muted/20

---

### 5. Timeline (Event History)

```typescript
interface TimelineProps {
  events: {
    id: string;
    timestamp: string;
    title: string;
    description?: string;
    severity: 'info' | 'warning' | 'error' | 'success';
    icon?: React.ReactNode;
  }[];
  groupBy?: 'hour' | 'day';
}
```

**Features:**
- Vertikale Linie mit Dots
- Zeit-Gruppierung
- Expandable Details
- Scroll-Loading

**Design:**
- Line: border-muted
- Dots: Severity Color
- Connector Lines

---

## Design-Token Erweiterungen

```typescript
// Neue Tokens für Futuristic Effects
export const effects = {
  glow: {
    primary: '0 0 20px rgba(201, 162, 39, 0.3)',
    success: '0 0 20px rgba(16, 185, 129, 0.3)',
    danger: '0 0 20px rgba(239, 68, 68, 0.3)',
  },
  backdrop: {
    grid: `linear-gradient(to right, #334155 1px, transparent 1px),
           linear-gradient(to bottom, #334155 1px, transparent 1px)`,
    gridSize: '40px',
  },
  transition: {
    fast: '150ms ease',
    normal: '250ms ease',
    slow: '350ms ease',
  },
};
```

---

## Implementierungs-Reihenfolge

### Sprint 1: API Foundation
1. ✅ `useApiClient()` - Axios/Fetch Setup
2. ✅ `useMissions()` - Mission Daten
3. ✅ `useEvents()` - Event Stream
4. ✅ `useMissionHealth()` - Health Status
5. ✅ `useQuery` Integration mit TanStack Query

### Sprint 2: Enhanced Components
1. 🟡 `ConsoleFeed` - Terminal Events
2. 🟡 `CircularProgress` - Agent Rings
3. 🟡 `LineChart` - Metrics Charts
4. 🟡 `Timeline` - Event Timeline

### Sprint 3: Advanced Features
1. 🔮 `MissionCreateForm` - Neue Mission
2. 🔮 `MissionDetailDrawer` - Mission Details
3. 🔮 `AgentDetail` - Agent View
4. 🔮 `HeatmapGrid` - System Status

### Sprint 4: Polish
1. 🔮 Animationen & Transitions
2. 🔮 Grid Background
3. 🔮 Hover Effects
4. 🔮 Responsive Optimizations

---

## Backend Erweiterungen (Für Phase 3+)

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| `/api/missions/{id}` | GET | Mission Detail | Hoch |
| `/api/missions/{id}` | DELETE | Mission Cancel | Mittel |
| `/api/agents` | GET | Agent List | Hoch |
| `/api/agents/{id}` | GET | Agent Detail | Mittel |
| `/api/agents/{id}/metrics` | GET | Agent Metrics | Niedrig |
| `/api/dashboard/stats` | GET | Aggregierte Stats | Mittel |
| `/api/events/stream` | WS | WebSocket Events | Hoch |

---

## Notizen

- **ConsoleFeed:** Soll sich an `journalctl` oder `tail -f` anfühlen
- **Charts:** Max 2 pro Page (Design System Regel)
- **Glow Effects:** Sehr subtil, nie als Default
- **Animations:** `prefers-reduced-motion` respektieren

