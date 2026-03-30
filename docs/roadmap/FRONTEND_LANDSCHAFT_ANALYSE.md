# BRAiN Frontend Landschaft Analyse

**Datum:** 29.03.2026
**Status:** Analyse abgeschlossen

---

## 1. Überblick: Drei Frontends

| Name | Verzeichnis | Zweck | Status |
|------|-------------|-------|--------|
| **AXE UI** | `frontend/axe_ui/` | Chat-Interface für AXE Agent | ✅ Aktiv in docker-compose |
| **ControlDeck v2** | `frontend/controldeck-v2/` | Enterprise Dashboard für Mission Control | ❌ Nicht integriert |
| **ControlDeck (alt)** | `frontend/control_deck/` | Legacy Frontend | ❌ Veraltet |

---

## 2. AXE UI - Aktuelles Produktives Frontend

### Verzeichnisstruktur
```
frontend/axe_ui/
├── app/
│   ├── chat/           # AXE Chat Interface
│   ├── dashboard/      # Dashboard
│   ├── settings/       # Settings (Provider, Odoo)
│   ├── neural/         # Neural Core Dashboard
│   └── page.tsx       # Landing
├── components/
│   └── auth/          # Login/Auth Komponenten
├── lib/
│   ├── api.ts         # API Client
│   ├── auth.ts       # Auth Funktionen
│   └── config.ts      # Config
└── docker-compose.yml # Docker Config
```

### Features
- ✅ AXE Chat mit Multi-Provider (OpenAI, Groq, Ollama, Mock)
- ✅ Neural Core Dashboard (Parameter, States, Synapsen)
- ✅ Odoo Settings Integration
- ✅ Provider Runtime Switching
- ✅ JWT Authentication

### Ports
- Development: `localhost:3002` (AXE UI)
- Docker: `localhost:3002`

---

## 3. ControlDeck v2 - Geplantes Enterprise Frontend

### Verzeichnisstruktur
```
frontend/controldeck-v2/
├── src/app/
│   ├── dashboard/      # KPIs + Event Feed
│   ├── missions/      # Mission Control
│   ├── events/        # Event Stream
│   ├── agents/        # Agent Fleet
│   ├── health/        # Health Monitoring
│   ├── settings/      # Settings
│   ├── audit/         # Audit Logs
│   ├── security/      # Security Panel
│   ├── tasks/         # Task Management
│   └── intelligence/  # Intelligence
├── packages/ui-core/  # Design System
├── docs/              # Spezifikationen
└── docker-compose.yml
```

### Features (Geplant)
- ✅ Dashboard mit KPIs
- ✅ Mission List mit Filter
- ✅ Event Stream
- ✅ Agent Fleet Overview
- ✅ Health Monitoring
- ❌ Echte API Integration (noch nicht)
- ❌ WebSocket Events (noch nicht)

### Ports
- Development: `localhost:3000`
- Docker: `localhost:3001`

---

## 4. Vergleich: AXE UI vs ControlDeck

| Feature | AXE UI | ControlDeck v2 |
|---------|--------|----------------|
| Chat Interface | ✅ | ❌ |
| Dashboard | ✅ Basis | ✅ Enterprise KPIs |
| Mission Control | ❌ | ✅ |
| Event Stream | ❌ | ✅ |
| Agent Fleet | ❌ | ✅ |
| Health Monitoring | ❌ | ✅ |
| Neural Dashboard | ✅ | ❌ |
| Provider Settings | ✅ | ❌ |
| Odoo Settings | ✅ | ❌ |
| Auth | ✅ JWT | ❌ (geplant) |

---

## 5. Probleme und Empfehlungen

### Problem 1: Zwei getrennte Systeme
- AXE UI für Chat und Neuronale Steuerung
- ControlDeck v2 für Operations

### Problem 2: Doppelte Funktionalität
- Beide haben "Settings" Seiten
- Beide haben "Dashboard" (unterschiedlich)

### Problem 3: ControlDeck nicht integriert
- Läuft nicht in docker-compose.local.yml
- Keine einheitliche Entwicklungsumgebung

### Empfehlung 1: Integration
ControlDeck v2 als zweiten Service in docker-compose.local.yml hinzufügen

### Empfehlung 2: Klare Trennung
- AXE UI = Chat + Skill Execution + Neural Control
- ControlDeck = Operations + Monitoring + Administration

### Empfehlung 3: Konsolidierung
- Ein gemeinsames UI-Core Package nutzen
- Geteilte Auth-Lösung

---

## 6. Nächste Schritte

1. **Sofort**: ControlDeck v2 in Docker Compose integrieren
2. **Kurzfristig**: Auth in ControlDeck nachrüsten
3. **Mittelfristig**: Klare API-Integration definieren
4. **Langfristig**: UI-Core Konsolidierung

---

## 7. API Endpoints Übersicht

### AXE UI nutzt:
- `GET /api/axe/chat` - Chat
- `GET /api/axe/sessions` - Sessions
- `GET /api/neural/*` - Neural Core
- `GET /api/auth/*` - Authentication

### ControlDeck v2 erwartet:
- `GET /api/missions/queue` - Mission Queue
- `GET /api/missions/health` - Mission Health
- `GET /api/events` - System Events
- `GET /api/system_stream/*` - SSE Events

---

## 8. Fazit

Das System hat zwei komplementäre Frontends mit unterschiedlichen Fokus:
- **AXE UI**: Agent-Chat Interface (produktiv)
- **ControlDeck v2**: Operations Dashboard (in Entwicklung)

Eine Integration in die lokale Entwicklungsumgebung ist notwendig.
