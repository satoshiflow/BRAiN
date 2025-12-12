# BRAiN V2 Deployment Guide

## Quick Start - Replace /opt/brain/

This guide will help you replace the old `/opt/brain/` installation with BRAiN V2.

### Prerequisites
- Server: `root@brain.falklabs.de` (46.224.37.114)
- Docker and Docker Compose installed
- Git repository access

---

## Automated Deployment (Recommended)

We've created an automated deployment script that handles everything:

### On the Server:

```bash
# 1. Connect to server
ssh root@brain.falklabs.de

# 2. Navigate to V2 repository
cd /home/user/BRAiN

# 3. Pull latest changes
git fetch origin
git checkout claude/migrate-v2-launch-01UQ1FuiVg8Rv6UQwwDar1g5
git pull

# 4. Run deployment script
bash deploy-v2.sh
```

The script will:
1. ✅ Stop old /opt/brain/ containers (volumes kept)
2. ✅ Update V2 repository
3. ✅ Create .env.dev with secure passwords
4. ✅ Pull all Docker images
5. ✅ Start all V2 services
6. ✅ **Migrate existing Ollama models** (if found - saves GB of downloads!)
7. ✅ Run comprehensive health checks

**Deployment time:** ~5-10 minutes (depending on image pull speed)

**Smart Migration:** If Ollama models exist in the old installation, they will be automatically migrated to V2 - **no need to re-download GB of models!**

---

## What Gets Deployed

### Services
- **Backend API** (FastAPI) - Port 8001
- **Control Deck** (Next.js) - Port 3001
- **AXE UI** (Next.js) - Port 3002
- **PostgreSQL** (v16) - Port 5433
- **Redis** (v7) - Port 6380
- **Qdrant** (Vector DB) - Port 6334
- **Ollama** (LLM Server) - Port 11434
- **OpenWebUI** (Chat Interface) - Port 8080

### Volumes (Persistent Data)
- `brain_pg_data_dev` - PostgreSQL data
- `brain_qdrant_data_dev` - Qdrant vectors
- `brain_ollama_data_dev` - Ollama models
- `brain_openwebui_data_dev` - OpenWebUI data

---

## After Deployment

### 1. Check/Download Ollama Models

If the deployment script found existing models, they're already migrated! Otherwise, download them:

```bash
# Check if models are already available
docker exec brain-ollama-dev ollama list

# If no models found, download recommended ones:
docker exec brain-ollama-dev ollama pull phi3
docker exec brain-ollama-dev ollama pull llama3.2
docker exec brain-ollama-dev ollama pull llama3.1
```

### 2. Access Services

**Via Browser:**
- Control Deck: http://brain.falklabs.de:3001
- AXE UI: http://brain.falklabs.de:3002
- OpenWebUI: http://brain.falklabs.de:8080
- Backend API: http://brain.falklabs.de:8001/docs

**Via curl:**
```bash
# Health check
curl http://localhost:8001/health

# API docs
curl http://localhost:8001/docs
```

### 3. View Logs

```bash
cd /home/user/BRAiN

# All services
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Specific service
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend

# Last 100 lines
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml logs --tail=100 backend
```

### 4. Restart Services

```bash
cd /home/user/BRAiN

# Restart all
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml restart

# Restart specific service
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml restart backend

# Rebuild and restart
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

---

## Manual Deployment (Alternative)

If you prefer manual steps:

### 1. Stop Old Installation

```bash
cd /opt/brain
docker compose down
```

### 2. Update Repository

```bash
cd /home/user/BRAiN
git fetch origin
git checkout claude/migrate-v2-launch-01UQ1FuiVg8Rv6UQwwDar1g5
git pull
```

### 3. Create .env.dev

```bash
cp .env.example .env.dev
nano .env.dev  # Edit configuration
```

### 4. Start Services

```bash
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### 5. Verify

```bash
# Check containers
docker ps

# Check logs
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

---

## Troubleshooting

### Services Not Starting

```bash
# Check container status
docker ps -a | grep brain

# Check specific container logs
docker logs brain-backend-dev

# Check docker compose status
cd /home/user/BRAiN
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

### Port Conflicts

If ports are already in use:

```bash
# Check what's using the ports
netstat -tulpn | grep -E ":(8001|3001|3002|8080|11434|6334|5433|6380)"

# Stop old containers
docker stop $(docker ps -aq --filter "name=brain")
```

### Database Connection Issues

```bash
# Check PostgreSQL
docker exec brain-postgres-dev pg_isready -U brain

# Check Redis
docker exec brain-redis-dev redis-cli ping

# Connect to PostgreSQL
docker exec -it brain-postgres-dev psql -U brain -d brain_v2_dev
```

### Rebuild Everything

```bash
cd /home/user/BRAiN

# Stop and remove everything
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v

# Rebuild and start fresh
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build --force-recreate
```

---

## Production Deployment

For production deployment on standard ports:

1. Stop dev environment
2. Use `docker-compose.prod.yml`
3. Update nginx configuration
4. Get SSL certificates

See `MIGRATION_PLAN.md` for detailed production deployment instructions.

---

## Rollback to /opt/brain/

If you need to rollback:

```bash
# Stop V2
cd /home/user/BRAiN
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Start old installation
cd /opt/brain
docker compose up -d
```

---

## Support

For issues or questions:
1. Check logs: `docker compose logs -f`
2. Review `MIGRATION_PLAN.md`
3. Check `CLAUDE.md` for architecture details

---

**Last Updated:** 2025-12-12
**Version:** 0.3.0
