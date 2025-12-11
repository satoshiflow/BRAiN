# 🧠 BRAiN Core Architecture v2.0 – Starter Kit

Dieses Repository ist ein produktionsreifes Skeleton für BRAiN Core v1.0:
- FastAPI Backend mit Modul-Architektur
- ControlDeck (Next.js 14, App Router)
- AXE UI (Next.js 14, App Router)
- Docker Compose Setup mit Postgres & Redis

## Services

- Backend API: http://localhost:8000
- ControlDeck: http://localhost:3000
- AXE UI: http://localhost:3001

## Quickstart mit Docker (empfohlen)

```bash
# Alle Services starten (Backend, Datenbanken, Frontends)
docker-compose up --build

# Im Hintergrund laufen lassen
docker-compose up -d --build

# Logs ansehen
docker-compose logs -f backend
docker-compose logs -f control_deck

# Herunterfahren
docker-compose down
```

## Lokale Entwicklung (ohne Docker)

**Voraussetzung:** PostgreSQL 16 und Redis 7 müssen lokal laufen.

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# ControlDeck (neues Terminal)
cd frontend/control_deck
npm install
npm run dev

# AXE UI (neues Terminal)
cd frontend/axe_ui
npm install
npm run dev
```

## Entwicklungsumgebung

Das Projekt verwendet **ausschließlich Docker und Docker Compose** für konsistente Umgebungen. Virtuelle Umgebungen (`.venv`) werden nicht in das Repository eingecheckt und sollten nicht lokal gepflegt werden.
