# 🧠 BRAIN Server Infrastructure - Complete Datasheet

**Für:** ChatGPT (Projektleiter Odoo/ERP)
**Von:** Claude (Chief Developer BRAIN)
**Datum:** 2025-11-14
**Status:** Production Live

---

## 🏗️ Server-Architektur Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    BRAIN ECOSYSTEM                          │
└─────────────────────────────────────────────────────────────┘

🖥️ BRAIN Server (brain.falklabs.de)
├─ IP: 46.224.37.114 (öffentlich)
├─ Private IP: 10.0.0.4
├─ Provider: Hetzner Cloud
├─ Typ: CPX42
├─ Specs: 8 vCPU, 16 GB RAM, 300 GB SSD
├─ OS: Ubuntu 24.04 LTS
└─ Rolle: KI-Framework (Agents, Missions, KARMA)

🖥️ Odoo Server (ERP)
├─ IP: 10.0.0.x (private network)
├─ Provider: Hetzner Cloud
├─ Rolle: Business-Daten (CRM, Projects, Tasks)
└─ Status: Separate Verwaltung (ChatGPT)

🖥️ App Server (geplant)
├─ IP: 167.x.x.x (öffentlich)
├─ Provider: TBD
├─ Stack: Next.js Frontends
├─ Apps: SatoshiFlow, FeWoHeroes, LandRad
└─ Status: Noch nicht aufgesetzt

🖥️ Coolify Server (optional, später)
├─ Rolle: Zentrales Deployment-Management
└─ Status: Geplant für App Server
```

---

## 🖥️ BRAIN Server - Detaillierte Specs

### Hardware & Provider
```
Provider:       Hetzner Cloud
Server Type:    CPX42
vCPU:           8 Cores
RAM:            16 GB (15.24 GB usable)
Storage:        300 GB SSD
Disk Usage:     ~8.4 GB / 300 GB (2.1%)
Network:        Public + Private Network
Location:       Germany (EU)
```

### Network Configuration
```
Public IP:      46.224.37.114
Private IP:     10.0.0.4
Hostname:       brain
FQDN:           brain.falklabs.de
```

### Network Access
```
Private Network: Connected to Odoo Server
Ports Open:
  - 22   (SSH)
  - 80   (HTTP → redirects to 443)
  - 443  (HTTPS)
  - 10.0.0.0/24 (Private Network Traffic)
```

---

## 🔐 Security Configuration

### SSH Access
```
Method:         SSH Key Authentication (Ed25519)
Password Login: DISABLED
Key Location:   ~/.ssh/brain_ed25519
Key Format:     Ed25519
User:           root

PuTTY Key:      brain_putty.ppk (für Windows)
```

### Firewall (UFW)
```
Status:         Active
Default:        Deny Incoming, Allow Outgoing

Rules:
  22/tcp        ALLOW       Anywhere (SSH)
  80/tcp        ALLOW       Anywhere (HTTP)
  443/tcp       ALLOW       Anywhere (HTTPS)
  10.0.0.0/24   ALLOW       Anywhere (Private Network)
```

### Fail2ban
```
Status:         Active
Protected:      SSH (Port 22)
Ban Time:       10 minutes
Max Retries:    5
```

### SSL/TLS
```
Domain:         brain.falklabs.de
Provider:       Let's Encrypt
Certificate:    /etc/letsencrypt/live/brain.falklabs.de/fullchain.pem
Private Key:    /etc/letsencrypt/live/brain.falklabs.de/privkey.pem
Valid Until:    2026-02-08
Auto-Renewal:   Enabled (Certbot)
```

---

## 🐳 Docker Stack

### Docker Version
```
Docker Engine:  26.1.3
Docker Compose: v2.27.0
```

### Running Services
```yaml
services:
  brain-postgres:
    image: ankane/pgvector:latest
    version: PostgreSQL 15.4
    port: 127.0.0.1:5432 (internal only)
    status: Up 18 hours (healthy)
    
  brain-redis:
    image: redis:7-alpine
    version: Redis 7.4.7
    port: 127.0.0.1:6379 (internal only)
    status: Up 18 hours (healthy)
    
  brain-qdrant:
    image: qdrant/qdrant:latest
    port: 127.0.0.1:6333 (internal only)
    status: Up 18 hours
    collections: 1 (brain_memory)
    
  brain-api:
    image: brain-backend (custom)
    framework: FastAPI
    port: 127.0.0.1:8000 (internal only)
    status: Up 10 hours (healthy)
    
  brain-nginx:
    image: nginx:alpine
    ports: 80, 443 (public)
    status: Up 14 hours
    role: Reverse Proxy + SSL Termination
```

---

## 📁 Directory Structure

### Main Directory
```
/opt/brain/
├── docker-compose.yml       # Main orchestration
├── .env                     # Environment variables (SECRETS!)
├── nginx.conf               # Nginx configuration
├── certbot/                 # Let's Encrypt webroot
├── data/                    # Persistent data
│   ├── postgres/            # Database files
│   ├── redis/               # Redis persistence
│   └── qdrant/              # Vector DB storage
├── logs/                    # Application logs
└── backend/                 # FastAPI Application
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── main.py
        ├── api/             # API Endpoints
        ├── core/            # Core Logic
        │   ├── agents/
        │   ├── health/
        │   └── database/
        └── models/          # Data Models
```

---

## 🔑 Credentials & Secrets

### Environment Variables (.env)
```bash
# Location: /opt/brain/.env

# PostgreSQL
POSTGRES_DB=brain
POSTGRES_USER=brain
POSTGRES_PASSWORD=changeme123  # ⚠️ PLACEHOLDER - sollte geändert werden

# Redis
REDIS_URL=redis://redis:6379/0

# Qdrant
QDRANT_URL=http://qdrant:6333

# FastAPI Backend
DATABASE_URL=postgresql://brain:changeme123@postgres:5432/brain
LOG_LEVEL=INFO

# Anthropic API (für später)
ANTHROPIC_API_KEY=  # Noch nicht gesetzt

# Optional
# LLM_CLIENT_TYPE=mock
# REDIS_PASSWORD=  # Nicht gesetzt
# QDRANT_API_KEY=  # Nicht gesetzt
```

### Docker Compose Variables
```yaml
# Aus docker-compose.yml:
environment:
  DATABASE_URL: postgresql://brain:${POSTGRES_PASSWORD:-changeme123}@postgres:5432/brain
  REDIS_URL: redis://redis:6379/0
  QDRANT_URL: http://qdrant:6333
  ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
  LOG_LEVEL: INFO
```

---

## 🌐 API Endpoints

### Base URL
```
Production: https://brain.falklabs.de
Internal:   http://localhost:8000
```

### Available Endpoints
```
Health Monitoring:
  GET  /api/health               → Simple health check
  GET  /api/health/detailed      → Detailed with DB status
  GET  /api/health/live          → Liveness probe
  GET  /api/health/ready         → Readiness probe

Agent Management:
  GET  /api/agents               → List all agents
  GET  /api/agents/{id}          → Get specific agent
  POST /api/agents/{id}/execute  → Execute task
  POST /api/agents/{id}/start    → Start agent
  POST /api/agents/{id}/stop     → Stop agent
  GET  /api/agents/type/{type}   → Get by type
  GET  /api/agents/health/check  → Health agent check
  GET  /api/agents/health/alerts → Health alerts

Missions (404 - noch nicht implementiert):
  POST /api/missions/create              → 404
  GET  /api/missions/{id}                → 404
  GET  /api/missions/{id}/status         → 404
  POST /api/missions/{id}/cancel         → 404
  GET  /api/missions/orchestrator/stats  → 404
  GET  /api/missions/queue/stats         → 404
  GET  /api/missions/active/list         → 404

Documentation:
  GET  /api/docs                 → Swagger UI
  GET  /api/openapi.json         → OpenAPI Schema
```

---

## 💾 Database Schemas

### PostgreSQL (brain database)
```sql
-- Haupt-Tabellen (bereits erstellt):
agents              → Agent Registry
agent_health_checks → Health Monitoring
system_metrics      → Performance Tracking

-- Geplant (noch nicht erstellt):
missions            → Mission Queue
mission_results     → Execution Results
karma_scores        → Ethical Ratings
memory_entries      → Knowledge Storage
```

### Redis Keys
```
Keys in Use:
  agent:*              → Agent State
  health:*             → Health Check Data
  session:*            → Session Data

Geplant:
  mission_queue        → Priority Queue (ZSET)
  mission_processing   → Active Missions (SET)
  mission_dlq          → Dead Letter Queue (ZSET)
  mission_queue_stats:* → Statistics
```

### Qdrant Collections
```
Existing:
  brain_memory        → Vector embeddings (1 collection)
  
Planned:
  agent_knowledge     → Agent-specific knowledge
  mission_context     → Mission context vectors
```

---

## 📊 Current System Status

### Resource Usage (Live)
```
CPU:     0-2%      (idle)
Memory:  5.9%      (~940 MB / 16 GB)
Disk:    2.1%      (~8.4 GB / 300 GB)
Network: Minimal
Uptime:  Backend: 10h, Services: 18h
```

### Service Health
```
✅ PostgreSQL:  CONNECTED, Healthy
✅ Redis:       CONNECTED, Healthy
✅ Qdrant:      CONNECTED, 1 collection
✅ FastAPI:     ONLINE, Healthy
✅ Nginx:       ONLINE, SSL Active
```

### Registered Agents
```
1. health-monitor
   Type:   health
   Status: running
   Role:   System monitoring
```

---

## 🔗 Integration Points

### BRAIN → Odoo (geplant)
```
Connection:  Private Network (10.0.0.4 → 10.0.0.x)
Protocol:    XML-RPC (Odoo Standard)
Direction:   Bidirectional

Odoo → BRAIN:
  - Trigger missions from Odoo events
  - Push business data (contacts, projects, tasks)
  - Real-time notifications

BRAIN → Odoo:
  - Write analysis results
  - Update records
  - Create automated tasks
```

### BRAIN → App Server (geplant)
```
Connection:  Public Internet (HTTPS)
Protocol:    REST API
Direction:   Bidirectional

Apps (SatoshiFlow, FeWoHeroes, LandRad):
  - Request AI analysis
  - Get recommendations
  - Real-time agent responses
```

---

## 🚀 Deployment Workflow

### Current (Manual)
```bash
# 1. SSH Connect
ssh root@brain.falklabs.de

# 2. Navigate
cd /opt/brain

# 3. Pull changes (wenn Git)
git pull

# 4. Rebuild & Restart
docker compose down
docker compose up -d --build

# 5. Check logs
docker compose logs -f backend

# 6. Verify
curl https://brain.falklabs.de/api/health
```

### Planned (via Coolify - später)
```
Git Push → Coolify → Auto-Deploy → Health Check
```

---

## 📝 Important Files & Locations

### Configuration Files
```
/opt/brain/docker-compose.yml    → Service Orchestration
/opt/brain/.env                  → Secrets (WICHTIG!)
/opt/brain/nginx.conf            → Reverse Proxy Config
/etc/letsencrypt/                → SSL Certificates
```

### Application Code
```
/opt/brain/backend/              → FastAPI App Root
/opt/brain/backend/app/main.py   → Entry Point
/opt/brain/backend/Dockerfile    → Container Build
```

### Logs
```
/opt/brain/logs/                 → App Logs
/var/log/nginx/                  → Nginx Logs
docker compose logs backend      → Container Logs
```

---

## 🔧 Useful Commands

### Service Management
```bash
# Status
docker compose ps
docker compose logs -f [service]

# Restart
docker compose restart [service]
docker compose down && docker compose up -d

# Rebuild
docker compose build [service]
docker compose up -d --build [service]
```

### Database Access
```bash
# PostgreSQL
docker compose exec postgres psql -U brain -d brain

# Redis
docker compose exec redis redis-cli

# Qdrant API
curl http://localhost:6333/collections
```

### Monitoring
```bash
# System Resources
htop
docker stats

# Disk Usage
df -h
du -sh /opt/brain/data/*

# Network
netstat -tulpn
```

---

## 🎯 Next Steps (Planned)

### Phase 1 (diese Woche):
- ✅ Mission System V1 (Core fertig)
- [ ] Mission System V1 (API Endpoints)
- [ ] Mission System V1 (Deploy)

### Phase 2:
- [ ] Memory Layer (pgvector integration)
- [ ] KARMA Agent (Ethical Governor)
- [ ] Credit System

### Phase 3:
- [ ] Odoo Connector (ChatGPT baut)
- [ ] Agent-Genesis Mechanism
- [ ] Frontend Dashboard

---

## 📞 Access für ChatGPT

### SSH Access (wenn benötigt)
```
Host:     brain.falklabs.de
Port:     22
User:     root
Auth:     SSH Key (Ed25519)

⚠️ Key muss von Oli freigegeben werden!
```

### API Access (jetzt)
```
Base URL: https://brain.falklabs.de
Auth:     Keine (noch nicht implementiert)
Rate Limit: Keine

Test:
curl https://brain.falklabs.de/api/health
```

---

## 🚨 Critical Information

### Was ChatGPT NICHT tun sollte:
- ❌ KEINE Änderungen an BRAIN Server
- ❌ KEINE Docker Services restart
- ❌ KEINE Firewall-Änderungen
- ❌ KEINE .env File Änderungen

### Was ChatGPT tun kann:
- ✅ Odoo-Server separat verwalten
- ✅ Odoo-Daten für BRAIN vorbereiten
- ✅ API-Endpoints von BRAIN nutzen
- ✅ Integration Specs entwickeln
- ✅ Mock-Daten erstellen

---

## 📋 Zusammenfassung für ChatGPT

**Du (ChatGPT) managst:**
- Odoo Server (10.0.0.x)
- Odoo Configuration
- Odoo Data Models
- Odoo → BRAIN Integration (XML-RPC)

**Ich (Claude) manage:**
- BRAIN Server (brain.falklabs.de)
- Docker Stack
- FastAPI Backend
- Agent System
- Mission System

**Zusammenarbeit:**
- Private Network Connection
- API Integration
- Data Exchange Specs
- Common Data Models

---

**Status:** Ready for Integration
**Contact:** Via Oli (Owner)

---

**Built by Claude (Chief Developer)**
**FalkLabs / Vinatic AG - 2025**
