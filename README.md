# 🧠 BRAIN - Lokale Entwicklungsumgebung

**Version:** 1.0.0-MVP
**Stand:** 2025-11-14
**Status:** Production-Ready Base

---

## 📁 Verzeichnisstruktur

Diese ZIP enthält die komplette BRAIN-Struktur für lokale Entwicklung mit VS Code.

```
brain/
├── backend/              # FastAPI Backend
│   ├── app/
│   │   ├── main.py      # Entry Point
│   │   ├── api/         # API Endpoints
│   │   ├── core/        # Core Logic
│   │   │   ├── agents/  # Agent System
│   │   │   ├── health/  # Health Monitoring
│   │   │   ├── llm/     # LLM Abstraction (NEU)
│   │   │   └── missions/# Mission System (NEU)
│   │   └── models/      # Data Models
│   ├── Dockerfile
│   └── requirements.txt
│
├── docs/                 # Dokumentation
│   ├── BRAIN_SERVER_DATASHEET_FOR_CHATGPT.md
│   ├── brain_framework.md
│   ├── BRAIN_ImmuneSystem_and_External_Defense.md
│   └── DEV_LINE_LAST_UPDATE.txt
│
├── mission_system_v1/    # Mission System Components
│   ├── llm_client.py
│   ├── mission_models.py
│   ├── mission_queue.py
│   └── README.md
│
├── docker-compose.yml    # Service Orchestration
├── .env.example          # Environment Template
├── nginx.conf            # Reverse Proxy Config
└── README.md             # Diese Datei
```

---

## 🚀 Setup auf lokalem PC

### 1. Voraussetzungen
```bash
# Installiere:
- Docker Desktop
- VS Code
- Git (optional)
- Python 3.11+ (für lokale Tests)
```

### 2. Projekt öffnen
```bash
# Entpacke ZIP
unzip brain_complete_backup.zip

# Öffne in VS Code
cd brain
code .
```

### 3. Environment Setup
```bash
# Kopiere .env Template
cp .env.example .env

# Editiere .env mit deinen Werten
# (Lokal kannst du die Defaults behalten)
```

### 4. Docker starten (lokal)
```bash
# Starte alle Services
docker compose up -d

# Check Status
docker compose ps

# Logs anschauen
docker compose logs -f backend
```

### 5. API testen
```bash
# Health Check
curl http://localhost:8000/api/health

# Swagger Docs
open http://localhost:8000/api/docs
```

---

## 🔧 VS Code Extensions (empfohlen)

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-azuretools.vscode-docker",
    "ms-vscode.makefile-tools",
    "redhat.vscode-yaml",
    "tamasfe.even-better-toml"
  ]
}
```

---

## 📝 Entwicklungs-Workflow

### Code-Änderungen testen
```bash
# 1. Ändere Code in backend/app/

# 2. Rebuild Container
docker compose build backend

# 3. Restart
docker compose restart backend

# 4. Test
curl http://localhost:8000/api/health
```

### Neue Dependencies hinzufügen
```bash
# 1. Editiere backend/requirements.txt

# 2. Rebuild
docker compose build backend

# 3. Restart
docker compose up -d
```

---

## 🔄 Sync mit Production

### Von Server holen
```bash
# Via WinSCP:
# Download /opt/brain/* → lokales brain/

# Via SSH:
ssh root@brain.falklabs.de
cd /opt/brain
tar -czf brain_backup.tar.gz backend/ docker-compose.yml .env
# Download via WinSCP
```

### Zum Server pushen
```bash
# Via WinSCP:
# Upload lokales brain/* → /opt/brain/

# Dann auf Server:
ssh root@brain.falklabs.de
cd /opt/brain
docker compose down
docker compose up -d --build
```

---

## 🧪 Testing

### Unit Tests (wenn vorhanden)
```bash
docker compose exec backend pytest
```

### Manual API Tests
```bash
# Nutze backend/tests/*.http Files
# Öffne in VS Code mit REST Client Extension
```

---

## 📚 Dokumentation

- **Server Specs:** `docs/BRAIN_SERVER_DATASHEET_FOR_CHATGPT.md`
- **Framework:** `docs/brain_framework.md`
- **Mission System:** `mission_system_v1/README.md`
- **Dev Updates:** `docs/DEV_LINE_LAST_UPDATE.txt`

---

## 🚨 Wichtig

### Lokale Entwicklung
- Ports: 8000 (API), 5432 (Postgres), 6379 (Redis)
- Data bleibt in Docker Volumes (nicht in ZIP)
- .env nie committen!

### Production Deployment
- Nur getestete Änderungen deployen
- Snapshot vor großen Updates
- Logs checken nach Deployment

---

**Happy Coding! 🚀**
