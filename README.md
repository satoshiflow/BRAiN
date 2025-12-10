# 🧠 BRAiN Core Architecture v1.0 – Starter Kit

Dieses Repository ist ein produktionsreifes Skeleton für BRAiN Core v1.0:
- FastAPI Backend mit Modul-Architektur
- ControlDeck (Next.js 14, App Router)
- AXE UI (Next.js 14, App Router)
- Docker Compose Setup mit Postgres & Redis

## Services

- Backend API: http://localhost:8000
- ControlDeck: http://localhost:3000
- AXE UI: http://localhost:3001

## Quickstart

```bash
# Backend lokal
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# ControlDeck
cd frontend/control_deck
npm install
npm run dev

# AXE UI
cd frontend/axe_ui
npm install
npm run dev
```

Für Docker siehe `docker-compose.yml`.
