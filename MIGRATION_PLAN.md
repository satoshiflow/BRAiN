# Migration Plan: /opt/brain/ → V2

## Ziel
V2-System auf dem Server `brain.falklabs.de` zum Laufen bringen, parallel zu `/opt/brain/`

## Status
- ✅ Git Repository (branch `v2`) vorhanden
- ✅ Docker Compose Konfiguration vorhanden
- ❌ Environment-Dateien fehlen
- ❌ System nicht deployed

---

## Schritt 1: Environment-Dateien erstellen

### `.env.dev` (Development)
```bash
# B R A I N v2.0 – Development Environment
APP_ENV=development
APP_NAME=BRAIN-v2-Dev
APP_VERSION=0.3.0
ENVIRONMENT=dev

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=brain_v2_dev
POSTGRES_USER=brain
POSTGRES_PASSWORD=<NEUES_SICHERES_PASSWORT>
DATABASE_URL=postgresql+asyncpg://brain:<PASSWORD>@postgres:5432/brain_v2_dev

# Redis
REDIS_URL=redis://redis:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000

# Mission Worker
ENABLE_MISSION_WORKER=true
MISSION_WORKER_POLL_INTERVAL=2.0

# LLM (falls Ollama lokal läuft)
LLM_PROVIDER=ollama
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=phi3
LLM_MAX_TOKENS=1024
LLM_TEMPERATURE=0.5

# Logging
LOG_LEVEL=DEBUG
LOG_ENABLE_CONSOLE=true

# Security
JWT_SECRET_KEY=<GENERIERTER_SECRET_KEY>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=300

# CORS (für Frontend-Zugriff)
CORS_ORIGINS=["http://localhost:3001","http://localhost:3002","https://dev.brain.falklabs.de"]
```

---

## Schritt 2: Docker Compose starten

### Development Environment
```bash
cd /home/user/BRAiN

# Erstelle .env.dev mit obiger Konfiguration
nano .env.dev

# Starte Services
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Logs überwachen
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend
```

---

## Schritt 3: Health Checks

### Backend API
```bash
curl http://localhost:8001/health
curl http://localhost:8001/api/health
```

### Frontend Control Deck
```bash
curl http://localhost:3001
```

### Frontend AXE UI
```bash
curl http://localhost:3002
```

### Datenbanken
```bash
# PostgreSQL
docker exec brain-postgres-dev psql -U brain -d brain_v2_dev -c "SELECT 1"

# Redis
docker exec brain-redis-dev redis-cli PING
```

---

## Schritt 4: Vergleich mit /opt/brain/

### Was V2 NICHT hat (aber /opt/brain/ schon):
1. **Qdrant** - Vector Database
2. **Ollama** - Lokaler LLM Server
3. **OpenWebUI** - Chat Interface
4. **Nginx** - Reverse Proxy

### Entscheidungen:
- [ ] Qdrant zu V2 hinzufügen?
- [ ] Ollama wird über `host.docker.internal` genutzt (falls auf Host läuft)
- [ ] OpenWebUI kann separat bleiben
- [ ] Nginx wird für Production benötigt

---

## Schritt 5: Migration von /opt/brain/ Daten (Optional)

Falls Daten von `/opt/brain/` übernommen werden sollen:

### PostgreSQL Daten exportieren
```bash
docker exec brain-postgres pg_dump -U brain -d brain > /tmp/brain_old_backup.sql
```

### In V2 importieren
```bash
docker exec -i brain-postgres-dev psql -U brain -d brain_v2_dev < /tmp/brain_old_backup.sql
```

### Redis Daten exportieren (falls nötig)
```bash
docker exec brain-redis redis-cli SAVE
docker cp brain-redis:/data/dump.rdb /tmp/redis_backup.rdb
docker cp /tmp/redis_backup.rdb brain-redis-dev:/data/dump.rdb
docker restart brain-redis-dev
```

---

## Schritt 6: Nginx für V2 konfigurieren (Production)

Wenn V2 öffentlich erreichbar sein soll:

### Nginx Config für V2
```nginx
# /etc/nginx/sites-available/brain-v2.conf

upstream brain_v2_backend {
    server localhost:8001;
}

upstream brain_v2_control_deck {
    server localhost:3001;
}

upstream brain_v2_axe_ui {
    server localhost:3002;
}

server {
    listen 443 ssl http2;
    server_name v2.brain.falklabs.de;

    ssl_certificate /etc/letsencrypt/live/v2.brain.falklabs.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/v2.brain.falklabs.de/privkey.pem;

    # Backend API
    location /api/ {
        proxy_pass http://brain_v2_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Control Deck (/)
    location / {
        proxy_pass http://brain_v2_control_deck;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # AXE UI (/axe)
    location /axe/ {
        proxy_pass http://brain_v2_axe_ui/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name v2.brain.falklabs.de;
    return 301 https://$server_name$request_uri;
}
```

---

## Schritt 7: Production Deployment

Wenn alles funktioniert, Production deployen:

```bash
# Production Environment File erstellen
cp .env.dev .env.prod

# Anpassen:
# - ENVIRONMENT=prod
# - POSTGRES_DB=brain_v2_prod
# - LOG_LEVEL=INFO
# - Starke Passwörter setzen
# - CORS_ORIGINS auf Production-Domain anpassen

# Starten
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## Entscheidungspunkte (WICHTIG!)

### 1. Soll V2 /opt/brain/ ersetzen oder parallel laufen?
- **Parallel**: V2 läuft auf anderen Ports (8001, 3001, 3002)
- **Ersetzen**: Alte Installation stoppen, V2 auf Standard-Ports (8000, 3000)

### 2. Welche Services aus /opt/brain/ werden benötigt?
- [ ] Qdrant (Vector DB)
- [ ] Ollama (LLM Server)
- [ ] OpenWebUI (Chat Interface)

### 3. Deployment-Strategie?
- **Option A**: V2 in `/srv/dev/` deployen (wie in CLAUDE.md beschrieben)
- **Option B**: V2 in `/opt/brain-v2/` deployen (neben alter Installation)
- **Option C**: `/opt/brain/` stoppen und durch V2 ersetzen

---

## Nächste Schritte

1. **Entscheidung treffen**: Parallel oder Ersatz?
2. **Environment-Datei erstellen**: `.env.dev` mit sicheren Passwörtern
3. **Docker Compose starten**: Development Environment hochfahren
4. **Testen**: Health Checks durchführen
5. **Optional**: Nginx konfigurieren für öffentlichen Zugang

---

## Ressourcen

- **Alte Installation**: `/opt/brain/`
- **V2 Repository**: `/home/user/BRAiN` (branch: `claude/migrate-v2-launch-01UQ1FuiVg8Rv6UQwwDar1g5`)
- **CLAUDE.md**: Detaillierte Dokumentation in `/home/user/BRAiN/CLAUDE.md`

---

*Status: Bereit für Deployment*
*Erstellt: 2025-12-12*
