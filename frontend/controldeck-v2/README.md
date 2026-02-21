# ControlDeck v2

**Enterprise Futuristic Control System for BRAiN**

Modernes React/Next.js Frontend mit strict Design System - basierend auf BRAiN OS Theme Spec v2.

---

## 🚀 Quick Start

### Lokale Entwicklung

```bash
cd frontend/controldeck-v2
npm install
npm run dev
```

Öffne http://localhost:3000

### Mit Docker (empfohlen)

```bash
# Entwicklung
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up controldeck_v2

# Oder alles zusammen
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Öffne http://localhost:3003

---

## 📁 Struktur

```
frontend/controldeck-v2/
├── packages/ui-core/          # Design System (Tokens + Components)
│   ├── src/
│   │   ├── tokens/            # Farben, Spacing, Typography
│   │   ├── components/        # Reusable UI Components
│   │   └── utils/             # Helper Functions
├── src/
│   ├── app/                   # Next.js App Router
│   │   ├── page.tsx           # Dashboard
│   │   ├── missions/page.tsx  # Mission Control
│   │   ├── events/page.tsx    # Event Stream
│   │   ├── agents/page.tsx    # Agent Fleet
│   │   ├── health/page.tsx    # Health Monitoring
│   │   └── settings/page.tsx  # Einstellungen
│   └── components/shell/      # Layout (Sidebar, Topbar)
├── Dockerfile
└── package.json
```

---

## 🎨 Design System

### Farben

| Token | Wert | Verwendung |
|-------|------|------------|
| `bg-main` | `#0F172A` | Hintergrund |
| `bg-card` | `#1E293B` | Cards |
| `accent-primary` | `#C9A227` | Gold Akzent |
| `border-muted` | `#334155` | Borders |

### Regeln (Hard Limits)

- Max 4 KPI Cards pro Row
- Max 2 Charts pro Page
- Desktop-first Responsive (Mobile = functional)
- Keine Hardcoded Farben
- Focus-visible niemals entfernen

---

## 🔗 API Integration

Standardmäßig verbindet sich ControlDeck v2 mit:

```
NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8001
```

### Verfügbare Endpoints (Backend)

| Endpoint | Beschreibung |
|----------|-------------|
| `GET /api/missions/queue` | Mission Queue |
| `GET /api/missions/health` | Mission Health |
| `GET /api/events` | System Events |
| `GET /api/system_stream/*` | SSE Events |

---

## 🛠️ Tech Stack

- **Framework:** Next.js 15 + React 19
- **Styling:** Tailwind CSS 3.4
- **State:** TanStack Query
- **UI:** Radix UI Primitives
- **Icons:** Lucide React
- **Charts:** Recharts

---

## 📋 MVP Features

✅ Dashboard mit KPIs und Event Feed  
✅ Mission List mit Filter & Status  
✅ Event Stream mit Severity  
✅ Agent Fleet Übersicht  
✅ Health Check Monitoring  
✅ Einstellungen (Theme, API)  

---

## 🔮 Roadmap

- [ ] Echte API Integration (statt Mock Data)
- [ ] WebSocket Events (Echtzeit)
- [ ] Mission Detail Drawer
- [ ] Create Mission Form
- [ ] Dashboard Widgets API
- [ ] Dark/Light Mode Toggle
- [ ] Mobile Optimierung

---

## 📝 Notizen

- **Backend Changes:** Keine erforderlich - bestehende API vollständig kompatibel
- **Auth:** Noch nicht implementiert (folgt mit Backend Session Management)
- **Tests:** Noch nicht implementiert

---

**Built with ❤️ for BRAiN OS**
