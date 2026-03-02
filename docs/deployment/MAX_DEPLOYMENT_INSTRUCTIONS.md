# Max - BRAiN Deployment Instructions

**Datum:** 2024-02-17
**Verantwortlich:** Max (Junior Developer mit OpenClaw + Kimi 2.5)
**Geschätzte Zeit:** 45 Minuten
**Priorität:** CRITICAL - Production System fehlen Services!

---

## 📖 CONTEXT (Hintergrund)

### Ist-Zustand
- **BRAiN Backend** läuft auf Production Server (Coolify)
- **PostgreSQL** läuft als Coolify Resource
- **Redis** läuft als Coolify Resource
- **Ollama** ❌ FEHLT (wurde beim Deployment nicht angelegt)
- **Qdrant** ❌ FEHLT (wurde beim Deployment nicht angelegt)

### Problem
Ohne Ollama und Qdrant:
- ❌ LLM-Funktionen funktionieren nicht (AXE Chat, Missions mit AI)
- ❌ Knowledge Graph kann keine Embeddings speichern
- ❌ Memory System kann keine semantische Suche machen
- ❌ RAG (Retrieval Augmented Generation) nicht möglich

### Was ist Qdrant?
**Qdrant** = Vector Database für Machine Learning
- Speichert Embeddings (numerische Vektoren von Text/Bildern)
- Ermöglicht semantische Suche (Ähnlichkeitssuche)
- Wird genutzt von:
  - Knowledge Graph (Wissens-Embeddings)
  - Memory System (Agent-Gedächtnis)
  - Document Search (Dokument-Ähnlichkeit)
  - RAG-System (Context-Retrieval für LLM)

### Architektur
```
BRAiN Production Stack
├── PostgreSQL      ✅ (Relational DB - Agents, Missions, Users)
├── Redis           ✅ (Event Stream, Cache, Queue)
├── Qdrant          ❌ (Vector DB - Embeddings, Semantic Search)
├── Ollama          ❌ (Local LLM - qwen2.5:0.5b)
├── BRAiN Backend   ✅ (FastAPI)
├── Control Deck    ✅ (Next.js Frontend)
└── AXE UI          ✅ (Next.js Widget)
```

---

## 🎯 ZIEL

1. **Ollama als Coolify Resource** anlegen
2. **Qdrant als Coolify Resource** anlegen
3. **Qwen 2.5 0.5B Modell** in Ollama pullen
4. **BRAiN Backend Config** updaten (Environment Variables)
5. **Verbindung testen** (Health Checks)
6. **Dokumentation** erstellen

---

## 🚀 KONKRETE ANWEISUNGEN (Ausführ-Prompt)

### **Task 1: Ollama Service in Coolify anlegen** ⏱️ 10 Min

#### 1.1 Coolify UI öffnen
```
1. Öffne Coolify Dashboard: https://coolify.falklabs.de (oder deine URL)
2. Login mit Admin-Account
3. Navigiere zu Projekt: "BRAiN"
```

#### 1.2 Neue Resource erstellen
```
Schritte:
1. Klicke auf "+ Add Resource" oder "New Resource"
2. Wähle "Service" → "Docker Image"
3. Name: ollama
4. Docker Image: ollama/ollama:latest
5. Netzwerk: brain-network (WICHTIG: gleiches Netzwerk wie Backend!)
```

#### 1.3 Konfiguration
```yaml
# General Settings
Name: ollama
Description: Local LLM Provider (Qwen 0.5B für BRAiN)

# Docker Settings
Image: ollama/ollama:latest
Tag: latest
Pull Policy: Always

# Network
Network: brain-network
Internal Only: YES  # ⚠️ WICHTIG: Nicht öffentlich!
Ports: NONE  # Kein Public Port!

# Volumes (Persistent Storage)
Volume Mounts:
  - Source: ollama_data (create new named volume)
  - Destination: /root/.ollama
  - Read-Write: true

# Health Check
Type: Command
Command: ollama list
Interval: 30s
Timeout: 10s
Retries: 3
Start Period: 30s

# Resource Limits
CPU Limit: 2.0 cores
Memory Limit: 4 GB
CPU Reservation: 1.0 cores
Memory Reservation: 2 GB

# Environment Variables
NONE (Ollama braucht keine Env Vars)
```

#### 1.4 Deployment
```
1. Klicke "Save" oder "Deploy"
2. Warte bis Status "Running" zeigt (~30 Sekunden)
3. Prüfe Logs: Sollte "Ollama is running" zeigen
```

#### 1.5 Modell Qwen 0.5B pullen
```bash
# In Coolify: Gehe zu Ollama Resource → Terminal/Exec
# Führe aus:
ollama pull qwen2.5:0.5b

# Warte ca. 2-3 Minuten (Download ~400 MB)

# Verifiziere:
ollama list

# Expected Output:
# NAME            SIZE      MODIFIED
# qwen2.5:0.5b    397 MB    2 minutes ago
```

#### 1.6 Optional: Backup-Modell pullen
```bash
# Fallback wenn Qwen nicht gut funktioniert:
ollama pull llama3.2:1b

# Verifiziere:
ollama list

# Jetzt sollten beide Modelle da sein
```

---

### **Task 2: Qdrant Service in Coolify anlegen** ⏱️ 10 Min

#### 2.1 Neue Resource erstellen
```
Schritte:
1. Noch im BRAiN Projekt: "+ Add Resource"
2. Wähle "Service" → "Docker Image"
3. Name: qdrant
4. Docker Image: qdrant/qdrant:latest
```

#### 2.2 Konfiguration
```yaml
# General Settings
Name: qdrant
Description: Vector Database für Embeddings & Semantic Search

# Docker Settings
Image: qdrant/qdrant:latest
Tag: latest
Pull Policy: Always

# Network
Network: brain-network  # Gleiches Netzwerk!
Internal Only: YES  # Nicht öffentlich
Ports: NONE  # Kein Public Port (nur intern Port 6333)

# Volumes (Persistent Storage)
Volume Mounts:
  - Source: qdrant_data (create new named volume)
  - Destination: /qdrant/storage
  - Read-Write: true

# Health Check
Type: HTTP
Path: /
Port: 6333
Interval: 30s
Timeout: 10s
Retries: 3

# Resource Limits
CPU Limit: 1.0 cores
Memory Limit: 2 GB
CPU Reservation: 0.5 cores
Memory Reservation: 1 GB

# Environment Variables
QDRANT__SERVICE__HTTP_PORT=6333
QDRANT__SERVICE__GRPC_PORT=6334
```

#### 2.3 Deployment
```
1. Klicke "Save" oder "Deploy"
2. Warte bis Status "Running"
3. Prüfe Logs: Sollte "Qdrant HTTP listening on 6333" zeigen
```

---

### **Task 3: BRAiN Backend Environment Variables updaten** ⏱️ 5 Min

#### 3.1 Coolify UI: BRAiN Backend Resource
```
1. Navigiere zu "brain-backend" Resource
2. Gehe zu "Environment Variables" Tab
```

#### 3.2 Ollama Config hinzufügen/updaten
```bash
# Falls nicht vorhanden, hinzufügen:
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=qwen2.5:0.5b

# ⚠️ WICHTIG: Nicht localhost, sondern Docker service name "ollama"!
```

#### 3.3 Qdrant Config hinzufügen/updaten
```bash
# Falls nicht vorhanden, hinzufügen:
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=  # Leer lassen (optional, nur bei Public)
QDRANT_COLLECTION_NAME=brain_embeddings
```

#### 3.4 Optional: LLM Router Settings
```bash
# Falls noch nicht gesetzt:
LLM_DEFAULT_PROVIDER=ollama
LLM_ENABLE_FALLBACK=true
LLM_CACHE_ENABLED=true
LLM_CACHE_TTL=3600
```

#### 3.5 Backend neu deployen
```
1. Scrolle runter zu "Deployment" Section
2. Klicke "Redeploy" oder "Restart"
3. Warte ca. 30-60 Sekunden
4. Status sollte wieder "Running" zeigen
```

---

### **Task 4: Verbindung testen** ⏱️ 10 Min

#### 4.1 Test: Backend → Ollama Verbindung
```bash
# In Coolify: brain-backend Resource → Terminal/Exec
# Führe aus:
curl http://ollama:11434/api/tags

# Expected Output: JSON mit models array
# {
#   "models": [
#     {"name": "qwen2.5:0.5b", "size": 397000000, ...}
#   ]
# }

# Falls "Connection refused":
# → Prüfe ob beide Services im gleichen Netzwerk sind
# → Prüfe Ollama Logs
```

#### 4.2 Test: Backend → Qdrant Verbindung
```bash
# Im Backend Container:
curl http://qdrant:6333/

# Expected Output: JSON mit "title": "qdrant - vector search engine"
# {
#   "title": "qdrant - vector search engine",
#   "version": "1.x.x"
# }

# Falls Fehler:
# → Prüfe Qdrant Logs
# → Prüfe Network Config
```

#### 4.3 Test: BRAiN API Health Checks
```bash
# Von außen (dein Laptop/Browser):
curl https://api.brain.falklabs.de/api/health

# Expected Response:
# {
#   "status": "healthy",
#   "services": {
#     "database": "connected",
#     "redis": "connected",
#     "ollama": "connected",      # ← NEU
#     "qdrant": "connected"        # ← NEU
#   }
# }

# Falls ollama/qdrant "disconnected":
# → Prüfe OLLAMA_HOST und QDRANT_URL Env Vars
# → Prüfe ob Services laufen
```

#### 4.4 Test: LLM Chat funktioniert
```bash
# Von außen:
curl -X POST https://api.brain.falklabs.de/api/llm-router/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hallo! Sage mir die aktuelle Uhrzeit."}
    ],
    "model": "qwen2.5:0.5b",
    "max_tokens": 50
  }'

# Expected: JSON response mit "content" field
# Antwort sollte in <2 Sekunden kommen

# Performance Benchmark:
# - Response Time: < 1 Sekunde (Qwen 0.5B ist sehr schnell)
# - Falls > 3 Sekunden: Modell zu groß oder CPU-Limit zu niedrig
```

#### 4.5 Test: Qdrant Collection erstellen
```bash
# Im Backend Container:
curl -X PUT http://qdrant:6333/collections/brain_embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }'

# Expected: {"result": true, "status": "ok"}

# Verifiziere:
curl http://qdrant:6333/collections/brain_embeddings

# Expected: JSON mit collection info
```

---

### **Task 5: Dokumentation erstellen** ⏱️ 10 Min

#### 5.1 Service Inventory updaten
```markdown
# Erstelle/Update: /home/oli/dev/brain-v2/docs/PRODUCTION_SERVICES.md

# BRAiN Production Services

## Coolify Resources (BRAiN Projekt)

### 1. PostgreSQL
- **Type:** Managed Database Service
- **Version:** 17-alpine
- **Port:** 5432 (internal only)
- **Volume:** postgres_data
- **Purpose:** Primary database (Agents, Missions, Users, etc.)

### 2. Redis
- **Type:** Docker Service
- **Image:** redis:7-alpine
- **Port:** 6379 (internal only)
- **Volume:** redis_data
- **Purpose:** Event Stream, Cache, Task Queue

### 3. Qdrant
- **Type:** Docker Service
- **Image:** qdrant/qdrant:latest
- **Port:** 6333 (internal only)
- **Volume:** qdrant_data
- **Purpose:** Vector Database (Embeddings, Semantic Search)
- **Collections:**
  - brain_embeddings (384-dim, Cosine)

### 4. Ollama
- **Type:** Docker Service
- **Image:** ollama/ollama:latest
- **Port:** 11434 (internal only)
- **Volume:** ollama_data
- **Purpose:** Local LLM Provider
- **Models:**
  - qwen2.5:0.5b (397 MB) - Primary
  - llama3.2:1b (1.3 GB) - Backup

### 5. BRAiN Backend
- **Type:** Application (Build from Dockerfile)
- **Port:** 8000 (public via Traefik)
- **Public URL:** https://api.brain.falklabs.de
- **Purpose:** FastAPI Backend

### 6. Control Deck
- **Type:** Application (Next.js)
- **Port:** 3000 (public via Traefik)
- **Public URL:** https://control.brain.falklabs.de
- **Purpose:** Admin Dashboard

### 7. AXE UI
- **Type:** Application (Next.js)
- **Port:** 3002 (public via Traefik)
- **Public URL:** https://axe.brain.falklabs.de
- **Purpose:** Embeddable AI Widget

---

## Network Architecture

```
┌──────────────────────────────────────────────────┐
│         Internet (Public)                        │
└──────────────┬───────────────────────────────────┘
               │
     ┌─────────▼─────────┐
     │  Traefik Proxy    │
     └─────────┬─────────┘
               │
    ┌──────────┴──────────┐
    │  brain-network      │  (Internal Docker Network)
    │                     │
    │  ┌──────────────┐   │
    │  │ Backend      │───┼──→ PostgreSQL (5432)
    │  │ (Public)     │───┼──→ Redis (6379)
    │  └──────┬───────┘   │
    │         │           │
    │         ├───────────┼──→ Ollama (11434)
    │         │           │
    │         └───────────┼──→ Qdrant (6333)
    │                     │
    │  ┌──────────────┐   │
    │  │ Control Deck │   │
    │  │ (Public)     │   │
    │  └──────────────┘   │
    │                     │
    │  ┌──────────────┐   │
    │  │ AXE UI       │   │
    │  │ (Public)     │   │
    │  └──────────────┘   │
    └─────────────────────┘
```

---

## Service Discovery

**Internal DNS (Docker):**
- Backend erreicht Ollama via: `http://ollama:11434`
- Backend erreicht Qdrant via: `http://qdrant:6333`
- Backend erreicht PostgreSQL via: `postgres:5432`
- Backend erreicht Redis via: `redis:6379`

**External Access:**
- Only via BRAiN Backend API
- No direct access to internal services
- All requests logged and authenticated

---

## Deployment Checklist

- [x] PostgreSQL deployed and initialized
- [x] Redis deployed and running
- [x] Qdrant deployed with collections created
- [x] Ollama deployed with models pulled
- [x] Backend deployed with correct env vars
- [x] Control Deck deployed
- [x] AXE UI deployed
- [x] All services in same network
- [x] Health checks passing
- [x] Public URLs accessible
- [x] SSL certificates valid
```

#### 5.2 Environment Variables Dokumentation
```markdown
# Erstelle: /home/oli/dev/brain-v2/docs/ENVIRONMENT_VARIABLES.md

# BRAiN Environment Variables

## Backend (.env)

### Database
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/brain
```

### Redis
```bash
REDIS_URL=redis://redis:6379/0
```

### Qdrant (Vector Database)
```bash
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=  # Empty for internal use
QDRANT_COLLECTION_NAME=brain_embeddings
```

### Ollama (Local LLM)
```bash
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=qwen2.5:0.5b
```

### LLM Router
```bash
LLM_DEFAULT_PROVIDER=ollama
LLM_ENABLE_FALLBACK=true
LLM_CACHE_ENABLED=true
LLM_CACHE_TTL=3600
```

### Optional: External LLM Providers
```bash
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Security
```bash
AUTH_SECRET=your-secret-key-min-32-chars
BRAIN_DMZ_GATEWAY_SECRET=your-gateway-secret
```

### CORS
```bash
CORS_ORIGINS=https://axe.brain.falklabs.de,https://control.brain.falklabs.de
```
```

---

## ✅ ACCEPTANCE CRITERIA (Erfolgs-Check)

### Services Running
- [ ] `ollama` Resource in Coolify: Status "Running", Health "Healthy"
- [ ] `qdrant` Resource in Coolify: Status "Running", Health "Healthy"
- [ ] `brain-backend` Resource: Status "Running", Health "Healthy"

### Models & Collections
- [ ] `ollama list` zeigt `qwen2.5:0.5b` (397 MB)
- [ ] Qdrant Collection `brain_embeddings` existiert

### Connectivity
- [ ] Backend kann Ollama erreichen: `curl http://ollama:11434/api/tags`
- [ ] Backend kann Qdrant erreichen: `curl http://qdrant:6333/`
- [ ] Public API Health Check: `GET /api/health` → alle Services "connected"

### Performance
- [ ] LLM Chat Response Time: < 2 Sekunden
- [ ] Qdrant Query Response: < 100ms
- [ ] Keine Timeout-Fehler in Logs

### Documentation
- [ ] `PRODUCTION_SERVICES.md` erstellt/updated
- [ ] `ENVIRONMENT_VARIABLES.md` erstellt
- [ ] Deployment-Datum dokumentiert

---

## 🚨 TROUBLESHOOTING

### Problem: "Connection refused" zu Ollama
```bash
# Check 1: Läuft Ollama?
# In Coolify: Ollama Resource → Logs
# Sollte "Ollama is running" zeigen

# Check 2: Richtiges Netzwerk?
# Beide Services müssen in "brain-network" sein
# In Coolify: Resource → Networks Tab

# Check 3: DNS funktioniert?
# Im Backend Container:
nslookup ollama
# Sollte IP-Adresse zurückgeben

# Fix: Beide Services neu deployen mit korrektem Network
```

### Problem: Modell nicht gefunden
```bash
# Check: Wurde Modell wirklich gepullt?
# In Coolify: Ollama → Terminal
ollama list

# Falls leer:
ollama pull qwen2.5:0.5b

# Warte 2-3 Minuten, dann:
ollama list
```

### Problem: Qdrant Collection fehlt
```bash
# Liste alle Collections:
curl http://qdrant:6333/collections

# Falls brain_embeddings fehlt:
curl -X PUT http://qdrant:6333/collections/brain_embeddings \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 384, "distance": "Cosine"}}'
```

### Problem: Langsame LLM Responses
```bash
# Check CPU/Memory:
# In Coolify: Ollama → Metrics

# Falls CPU/Memory am Limit:
# Erhöhe Resource Limits:
# CPU: 2.0 → 4.0
# Memory: 4GB → 8GB
```

### Problem: Health Check failing
```bash
# Ollama Health:
# In Coolify: Terminal
ollama list
# Falls Fehler: Container restart

# Qdrant Health:
curl http://qdrant:6333/
# Falls Fehler: Prüfe Logs
```

---

## 📝 DELIVERABLES (Was du mir zeigen musst)

### Screenshots
1. Coolify Dashboard: Ollama Resource "Running" + "Healthy"
2. Coolify Dashboard: Qdrant Resource "Running" + "Healthy"
3. Ollama Terminal: `ollama list` Output
4. Backend Terminal: `curl http://ollama:11434/api/tags` Response
5. Backend Terminal: `curl http://qdrant:6333/` Response
6. Browser: `https://api.brain.falklabs.de/api/health` Response

### Files
1. `/home/oli/dev/brain-v2/docs/PRODUCTION_SERVICES.md`
2. `/home/oli/dev/brain-v2/docs/ENVIRONMENT_VARIABLES.md`
3. `/home/oli/dev/brain-v2/CHANGELOG.md` (Update mit Deployment-Info)

### Test Results
```bash
# Erstelle: test-results.md
# Mit Output von allen Tests in Task 4
```

---

## ⏱️ ZEITPLAN

```
00:00 - 00:10  Task 1: Ollama anlegen & deployen
00:10 - 00:20  Task 2: Qdrant anlegen & deployen
00:20 - 00:25  Task 3: Backend Env Vars updaten
00:25 - 00:35  Task 4: Tests durchführen
00:35 - 00:45  Task 5: Dokumentation erstellen
```

**Gesamt: 45 Minuten** (wenn alles glatt läuft)

---

## 🤖 FÜR DEINE SUBAGENTEN

Du kannst diese Tasks parallel an verschiedene Subagenten verteilen:

**Subagent 1: Coolify-Deployer**
- Task 1.1 - 1.4 (Ollama anlegen)
- Task 2.1 - 2.3 (Qdrant anlegen)

**Subagent 2: Model-Manager**
- Task 1.5 - 1.6 (Models pullen)
- Task 4.5 (Qdrant Collection erstellen)

**Subagent 3: Config-Manager**
- Task 3.1 - 3.5 (Backend Env Vars)

**Subagent 4: Tester**
- Task 4.1 - 4.4 (Alle Tests)

**Subagent 5: Dokumentation**
- Task 5.1 - 5.2 (Docs erstellen)

**Koordination:**
- Subagent 3 wartet auf Subagent 1+2 (Services müssen erst laufen)
- Subagent 4 wartet auf Subagent 3 (Env Vars müssen gesetzt sein)
- Subagent 5 kann parallel zu allen laufen

---

**Viel Erfolg, Max! Bei Fragen: Screenshots + Logs + konkrete Fehlermeldung!** 🚀
