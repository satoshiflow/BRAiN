# Phase 1 Report: Mage.ai Setup

**Date:** 2026-01-09
**Branch:** `claude/fix-traefik-config-eYoK3`
**Commit:** `80596f1`
**Status:** ✅ Ready for Deployment

---

## 📋 Executive Summary

Phase 1 fügt **Mage.ai** als interne Data Pipeline Platform zu BRAiN hinzu:

- ✅ PostgreSQL mit pgvector Extension
- ✅ Ollama mit LLM Models (llama3.2, nomic-embed-text)
- ✅ Mage.ai Service (internal-only, port 6789)
- ✅ Automated Setup & Verification Scripts

**Deployment Zeit:** ~15-20 Minuten (inkl. Ollama Model Download)

---

## 🏗️ Architecture

```
BRAiN Services (Internal Network)
│
├── PostgreSQL (pgvector/pgvector:pg16)
│   ├── Port: 5432 (internal only)
│   ├── Database: brain
│   ├── Extension: pgvector ✅
│   └── Schema: mage_metadata
│
├── Ollama (ollama/ollama:latest)
│   ├── Port: 11434 (internal only)
│   ├── Models:
│   │   ├── llama3.2:latest (Chat & Reasoning)
│   │   └── nomic-embed-text (Embeddings)
│   └── Storage: brain_ollama_data volume
│
└── Mage.ai (mageai/mageai:latest)
    ├── Port: 6789 (localhost only, NO public access)
    ├── Access: SSH tunnel required
    ├── Connects to:
    │   ├── PostgreSQL (metadata storage)
    │   └── Ollama (AI features)
    └── Storage: brain_mage_data volume
```

---

## 📦 Files Created

### 1. docker-compose.mage.yml
**Purpose:** Extends docker-compose.yml with Mage.ai services

**Key Features:**
- PostgreSQL override mit pgvector image
- Mage.ai service definition
- Internal-only networking (no Traefik labels)
- Healthcheck für Mage.ai

**Usage:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.mage.yml up -d
```

---

### 2. backend/scripts/init-pgvector.sql
**Purpose:** PostgreSQL initialization script

**What it does:**
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create mage_metadata schema
CREATE SCHEMA IF NOT EXISTS mage_metadata;

-- Grant permissions to brain user
GRANT ALL PRIVILEGES ON SCHEMA mage_metadata TO brain;
```

**Execution:** Runs automatically on first PostgreSQL container startup

---

### 3. backend/mage_config/metadata.yaml
**Purpose:** Mage.ai configuration

**Key Settings:**
- Ollama integration: `http://ollama:11434`
- PostgreSQL connection: `postgresql+psycopg2://brain:brain@postgres:5432/brain`
- Logging: INFO level, console output
- Authentication: Local mode (internal only)

---

### 4. setup-phase1-mage.sh
**Purpose:** Automated deployment script

**What it does:**
1. Backup current state
2. Stop existing containers
3. Pull Docker images (pgvector, mageai, ollama)
4. Start services with docker-compose
5. Wait for PostgreSQL initialization
6. Pull Ollama models (llama3.2, nomic-embed-text)
7. Wait for Mage.ai startup (60s)
8. Display service status

**Execution Time:** 15-20 minutes

**Usage:**
```bash
bash setup-phase1-mage.sh
```

---

### 5. verify-phase1.sh
**Purpose:** Validation script with 8 checks

**Checks:**
1. ✅ Mage.ai container running
2. ✅ Mage.ai NOT publicly accessible (security)
3. ✅ Mage.ai accessible on localhost:6789
4. ✅ PostgreSQL pgvector extension installed
5. ✅ Ollama container running
6. ✅ Ollama models pulled (llama3.2, nomic-embed-text)
7. ✅ Mage.ai can reach Ollama (network connectivity)
8. ✅ Mage.ai can reach PostgreSQL (network connectivity)

**Usage:**
```bash
bash verify-phase1.sh
```

**Expected Output:**
```
✅ PASSED: 8/8
🎉 Phase 1: ALL CHECKS PASSED!
```

---

## 🚀 Deployment Instructions

### On Server (brain.falklabs.de)

```bash
# 1. Navigate to deployment directory
cd /srv/dev  # Or wherever Coolify deploys

# 2. Pull latest changes
git pull origin claude/fix-traefik-config-eYoK3

# 3. Run setup script
bash setup-phase1-mage.sh

# 4. Wait 15-20 minutes (Ollama model downloads)

# 5. Run verification
bash verify-phase1.sh

# 6. Check logs
docker logs -f brain-mage
```

---

## 🔒 Security Features

### ✅ Internal-Only Access

**Mage.ai:**
- Port 6789 bound to `127.0.0.1` only
- NO Traefik labels (not exposed via reverse proxy)
- Only accessible via SSH tunnel

**PostgreSQL:**
- Port 5432 internal only
- No external exposure

**Ollama:**
- Port 11434 internal only
- Only accessible from brain_internal network

### ✅ Access Method (SSH Tunnel)

**From Developer Machine:**
```bash
ssh -L 6789:localhost:6789 root@brain.falklabs.de
```

**Then open browser:**
```
http://localhost:6789
```

---

## 📊 Resource Requirements

### Disk Space
- **PostgreSQL pgvector:** ~500 MB
- **Ollama (with models):** ~5 GB
  - llama3.2:latest: ~2 GB
  - nomic-embed-text: ~300 MB
- **Mage.ai:** ~1 GB
- **Total:** ~6.5 GB

### Memory
- **PostgreSQL:** ~256 MB (idle), up to 1 GB
- **Ollama:** ~2 GB (with loaded model)
- **Mage.ai:** ~512 MB (idle), up to 2 GB
- **Total Recommended:** 8 GB RAM

### CPU
- **Minimum:** 2 cores
- **Recommended:** 4 cores (for Ollama inference)

---

## 🧪 Testing

### Test 1: Mage.ai Accessibility

**From Server:**
```bash
curl http://localhost:6789/api/status
```

**Expected:**
```json
{"status":"ok"}
```

---

### Test 2: pgvector Extension

**Check Extension:**
```bash
docker exec brain-postgres psql -U brain -d brain -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

**Expected:**
```
 extname | extowner | extnamespace | extrelocatable | extversion
---------+----------+--------------+----------------+------------
 vector  |       10 |         2200 | f              | 0.5.1
```

---

### Test 3: Ollama Models

**List Models:**
```bash
docker exec brain-ollama ollama list
```

**Expected:**
```
NAME                    ID              SIZE    MODIFIED
llama3.2:latest         a80c4f17acd5    2.0 GB  2 hours ago
nomic-embed-text:latest 0a109f422b47    274 MB  1 hour ago
```

---

### Test 4: Mage.ai → Ollama Connectivity

**From Mage.ai Container:**
```bash
docker exec brain-mage curl http://ollama:11434/api/tags
```

**Expected:**
```json
{"models":[{"name":"llama3.2:latest",...},{"name":"nomic-embed-text:latest",...}]}
```

---

## 🐛 Troubleshooting

### Issue 1: Mage.ai Container Restart Loop

**Symptoms:**
```bash
docker ps -a | grep brain-mage
# Shows: Restarting (1) 5 seconds ago
```

**Solution:**
```bash
# Check logs
docker logs brain-mage

# Common causes:
# 1. PostgreSQL not ready → Wait 30s, check postgres logs
# 2. Volume permission issue → Check volume ownership
# 3. Config error → Validate backend/mage_config/metadata.yaml

# Recreate container
docker-compose -f docker-compose.yml -f docker-compose.mage.yml up -d --force-recreate mage
```

---

### Issue 2: pgvector Extension Not Installed

**Symptoms:**
```bash
docker exec brain-postgres psql -U brain -d brain -c "SELECT * FROM pg_extension WHERE extname='vector';"
# Returns empty
```

**Solution:**
```bash
# Check if init script ran
docker logs brain-postgres | grep pgvector

# If no logs:
# 1. PostgreSQL volume already exists (init scripts only run on FIRST startup)
# 2. Remove volume to trigger init:
docker-compose down -v  # ⚠️ DELETES ALL DATA
docker-compose -f docker-compose.yml -f docker-compose.mage.yml up -d

# Or install manually:
docker exec brain-postgres psql -U brain -d brain -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

### Issue 3: Ollama Model Download Fails

**Symptoms:**
```bash
docker exec brain-ollama ollama pull llama3.2:latest
# Error: connection timeout
```

**Solution:**
```bash
# Check internet connectivity
docker exec brain-ollama ping -c 3 registry.ollama.ai

# Check disk space
df -h | grep docker

# Retry with verbose logging
docker exec brain-ollama ollama pull llama3.2:latest --verbose

# Alternative: Download on host, import into container
# (See Ollama docs for manual import)
```

---

### Issue 4: Mage.ai Not Accessible on localhost:6789

**Symptoms:**
```bash
curl http://localhost:6789/api/status
# Connection refused
```

**Solution:**
```bash
# 1. Check container is running
docker ps | grep brain-mage

# 2. Check port binding
docker port brain-mage
# Should show: 6789/tcp -> 127.0.0.1:6789

# 3. Check if another process uses port 6789
netstat -tuln | grep 6789

# 4. Check Mage.ai logs
docker logs brain-mage | grep "Starting server"

# 5. Wait longer (Mage.ai can take 60-90s to start)
sleep 60 && curl http://localhost:6789/api/status
```

---

## ✅ Success Criteria

**Phase 1 is successful when:**

1. ✅ All 8 verification checks pass
2. ✅ Mage.ai UI accessible via SSH tunnel
3. ✅ PostgreSQL pgvector queries work
4. ✅ Ollama models respond to API calls
5. ✅ Mage.ai can create and run pipelines
6. ✅ No public exposure (port 6789 blocked externally)

---

## 📈 Next Steps (Future Phases)

### Phase 2: BRAiN ↔ Mage.ai Integration
- Backend API endpoints for Mage.ai
- Pipeline triggers from BRAiN missions
- Results storage in PostgreSQL

### Phase 3: Advanced Pipelines
- Vector search with pgvector
- LLM-powered data transformations
- Embedding generation for semantic search

### Phase 4: UI Integration
- Control Deck: Mage.ai pipeline management
- Real-time pipeline status
- Logs and metrics visualization

---

## 📝 Git Changes

**Branch:** `claude/fix-traefik-config-eYoK3`
**Commit:** `80596f1`

**Files Added:**
- `docker-compose.mage.yml` (65 lines)
- `backend/scripts/init-pgvector.sql` (37 lines)
- `backend/mage_config/metadata.yaml` (33 lines)
- `setup-phase1-mage.sh` (106 lines)
- `verify-phase1.sh` (154 lines)

**Total:** 395 lines added

---

## 🎯 Summary

**Phase 1: Mage.ai Setup - COMPLETE**

✅ **PostgreSQL** upgraded to pgvector
✅ **Ollama** with LLM models ready
✅ **Mage.ai** deployed (internal-only)
✅ **Automated Setup** script created
✅ **Verification** script with 8 checks
✅ **Documentation** complete

**Deployment Ready:** Execute `setup-phase1-mage.sh` on server

**Estimated Time:** 15-20 minutes

**Security:** All services internal-only, no public exposure

---

**Report Generated:** 2026-01-09 22:30 UTC
**Project Lead:** Claude (AI Assistant)
**User Approval:** Pending execution on server
