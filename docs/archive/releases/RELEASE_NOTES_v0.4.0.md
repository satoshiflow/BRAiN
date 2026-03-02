# BRAiN v0.4.0 - Fred Bridge & AXE Widget Release

## 🎯 Übersicht
Dieser Release fügt das **Fred Bridge** (Development Intelligence Interface) und **AXE Widget** (Floating Chat) zu BRAiN hinzu.

## ✨ Neue Features

### Fred Bridge
- Ticket Management (Incident/Feature/Refactor/Security)
- Patch Artifact System
- Mock Fred für Testing
- Governor Approval Workflow
- API: `/api/fred-bridge/*`

### AXE Widget
- Embeddable Floating Chat
- Session Management
- Widget Admin UI
- API: `/widget/*`

### Weitere Module
- Mission Worker System
- Skills Registry
- LLM Router Integration

## 🐛 Bugfixes
- OpenAPI Generation stabilisiert
- Redis-Handling verbessert
- Port-Konflikte gelöst (3001/3002/8001)

## 📝 API Endpoints

### Fred Bridge
- `POST /api/fred-bridge/tickets` - Ticket erstellen
- `GET /api/fred-bridge/tickets` - Tickets listen
- `POST /api/fred-bridge/patches` - Patch einreichen
- `GET /api/fred-bridge/health` - Status

### AXE Widget
- `GET /widget/js` - Embeddable Script
- `POST /widget/init` - Session initialisieren

## 🚀 Deployment

### Voraussetzungen
- Redis (Port 6380)
- PostgreSQL (Port 5432)
- OpenWebUI (optional, Port 8080)

### Umgebungsvariablen
```env
REDIS_URL=redis://localhost:6380
DATABASE_URL=postgresql://user:pass@localhost:5432/brain
ENABLE_MISSION_WORKER=true
BRAIN_EVENTSTREAM_MODE=required
```

### Ports
- Backend API: 8001
- Control Deck: 3001
- AXE_UI: 3002

## 👥 Credits
- Implementation: OpenClaw/Fred
- Architecture: FalkLabs

## 📄 Lizenz
Proprietär - FalkLabs 2026
