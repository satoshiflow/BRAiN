# 🔧 Development Setup für BRAiN

Dieses Dokument beschreibt die Entwicklungsumgebung für BRAiN Core v2.0.

## 📋 Voraussetzungen

### Für Docker (empfohlen)
- Docker Engine 24.0+
- Docker Compose 2.20+

### Für lokale Entwicklung (ohne Docker)
- Python 3.11+
- Node.js 18+
- PostgreSQL 16
- Redis 7

## 🐳 Setup mit Docker (Empfohlen)

Docker gewährleistet konsistente Umgebungen zwischen Entwicklung und Produktion.

### Schnellstart

```bash
# Repository klonen
git clone https://github.com/satoshiflow/BRAiN.git
cd BRAiN-V1

# Konfiguration vorbereiten
cp backend/.env.example backend/.env

# Alle Services starten
docker-compose up --build
```

Die Services sind dann verfügbar unter:
- Backend API: http://localhost:8000
- ControlDeck UI: http://localhost:3000
- AXE UI: http://localhost:3001
- API Docs: http://localhost:8000/docs

### Nützliche Docker-Befehle

```bash
# Services im Hintergrund starten
docker-compose up -d

# Logs anschauen
docker-compose logs -f backend        # Backend logs
docker-compose logs -f control_deck   # ControlDeck logs
docker-compose logs control_deck -n 50 # Letzte 50 Zeilen

# Spezifischen Service restarten
docker-compose restart backend

# Alles herunterfahren
docker-compose down

# Volumes löschen (Datenbankdaten!)
docker-compose down -v

# In Container gehen
docker exec -it brain-backend bash
docker exec -it brain-postgres psql -U brain -d brain
```

### Backend-Service

```bash
# Container bauen
docker-compose build backend

# Container starten
docker-compose up backend postgres redis

# In Backend-Container gehen
docker exec -it brain-backend bash
pip list              # Installierte Pakete
uvicorn --version    # Check Uvicorn
```

### Frontend-Services

```bash
# ControlDeck bauen und starten
docker-compose build control_deck
docker-compose up control_deck

# AXE UI bauen und starten
docker-compose build axe_ui
docker-compose up axe_ui
```

## 💻 Lokale Entwicklung (ohne Docker)

Nur für Entwicklung ohne Docker-Isolation.

### Backend Setup

```bash
# In Backend-Verzeichnis gehen
cd backend

# Dependencies installieren (pip, nicht venv!)
pip install -r requirements.txt

# Lokale Umgebungsvariablen setzen
cp .env.example .env
# Bearbeite .env und setze DATABASE_URL auf lokale PostgreSQL
# DATABASE_URL=postgresql://brain:brain@localhost:5432/brain

# Server starten
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### ControlDeck Setup

```bash
# In ControlDeck-Verzeichnis gehen
cd frontend/control_deck

# Dependencies installieren
npm install

# Development Server starten
npm run dev
# Verfügbar unter http://localhost:3000
```

### AXE UI Setup

```bash
# In AXE UI-Verzeichnis gehen
cd frontend/axe_ui

# Dependencies installieren
npm install

# Development Server starten
npm run dev
# Verfügbar unter http://localhost:3001
```

### PostgreSQL & Redis lokal starten

**macOS/Linux:**
```bash
# PostgreSQL
brew install postgresql@16
brew services start postgresql@16

# Redis
brew install redis
brew services start redis

# oder mit Docker
docker run -d -p 5432:5432 -e POSTGRES_USER=brain -e POSTGRES_PASSWORD=brain -e POSTGRES_DB=brain postgres:16
docker run -d -p 6379:6379 redis:7-alpine
```

**Windows:**
```bash
# Mit Chocolatey oder direkter Installation
choco install postgresql redis

# oder mit Docker Desktop
docker run -d -p 5432:5432 -e POSTGRES_USER=brain -e POSTGRES_PASSWORD=brain -e POSTGRES_DB=brain postgres:16
docker run -d -p 6379:6379 redis:7-alpine
```

## 🚫 Warum keine virtuellen Umgebungen (.venv)?

- **Docker ist Quelle der Wahrheit**: Konsistente Python-Version und Dependencies über alle Maschinen
- **Kein `node_modules` in Git**: Frontend-Dependencies sind auch nicht versioniert
- **CI/CD-freundlich**: Automatische Tests und Deployments nutzen Docker
- **.venv sollte nie in Git sein**: Zu große Dateien, plattformabhängig

## 📦 Abhängigkeiten verwalten

### Backend

```bash
# Neue Dependency hinzufügen
cd backend
pip install new-package
pip freeze > requirements.txt

# Docker rebuilden
docker-compose build --no-cache backend
```

### Frontend

```bash
# ControlDeck
cd frontend/control_deck
npm install new-package
npm run build

# AXE UI
cd frontend/axe_ui
npm install new-package
npm run build

# Docker rebuilden
docker-compose build --no-cache control_deck axe_ui
```

## 🧪 Testing

```bash
# Backend Tests im Docker-Container
docker exec brain-backend pytest

# oder lokal
cd backend
pip install pytest pytest-asyncio
pytest
```

## 📝 Umgebungsvariablen

Die Datei `backend/.env` wird von Docker automatisch geladen. Kopiere `.env.example` und bearbeite die Werte:

```bash
cp backend/.env.example backend/.env
# Dann editieren
```

**Wichtig:** Committed `.env` niemals in Git!

## 🐛 Häufige Probleme

### "Docker Container können sich nicht miteinander verbinden"
→ Stelle sicher, dass alle Services im gleichen `docker-compose.yml` definiert sind. Die Container kommunizieren über Service-Namen (z.B. `backend`, `postgres`).

### "Port 8000 ist bereits belegt"
```bash
docker-compose down  # Alte Container herunterfahren
docker ps -a          # Alle Container anschauen
docker rm <container-id>  # Spezifischen Container löschen
```

### "PostgreSQL Verbindung fehlgeschlagen"
```bash
# Container neu starten
docker-compose restart postgres

# oder Volumen neu initialisieren
docker-compose down -v
docker-compose up -d
```

## 📚 Weitere Ressourcen

- [BRAiN Architecture](docs/ARCHITECTURE.md)
- [Copilot Instructions](/.github/copilot-instructions.md)
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
