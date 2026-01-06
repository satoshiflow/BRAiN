# 🚀 BRAiN Coolify Deployment Plan

**Version:** 1.0
**Date:** 2026-01-05
**Server:** brain.falklabs.de (46.224.37.114)
**Purpose:** Complete migration to Coolify-based deployment with multi-environment support

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Why Coolify?](#why-coolify)
3. [Architecture](#architecture)
4. [Prerequisites](#prerequisites)
5. [Phase 0: Cleanup & Preparation](#phase-0-cleanup--preparation)
6. [Phase 1: Coolify Installation](#phase-1-coolify-installation)
7. [Phase 2: Environment Configuration](#phase-2-environment-configuration)
8. [Phase 3: GitHub Integration](#phase-3-github-integration)
9. [Phase 4: Migration Strategy](#phase-4-migration-strategy)
10. [Phase 5: New Workflow](#phase-5-new-workflow)
11. [Phase 6: Advanced Features](#phase-6-advanced-features)
12. [Troubleshooting](#troubleshooting)
13. [Rollback Plan](#rollback-plan)

---

## Overview

### Current State
```
Manual Deployment:
├── /srv/dev/     → Branch: v2 (claude/python-path-and-deps-fix-h1NXi)
├── /srv/stage/   → Empty
├── /srv/prod/    → Empty
└── /srv/main/    → Empty

Manual Workflow:
1. Code on Windows PC or /root/BRAiN/
2. Push to GitHub
3. SSH to server
4. cd /srv/dev && git pull
5. docker compose restart
```

### Target State (Coolify)
```
Automated Deployment:
├── /srv/dev/     → Branch: dev   → dev.brain.falklabs.de   (Auto-Deploy)
├── /srv/stage/   → Branch: stage → stage.brain.falklabs.de (Semi-Auto)
└── /srv/prod/    → Branch: main  → brain.falklabs.de       (Manual Approve)

Automated Workflow:
1. Code in VSCode Remote SSH (/srv/dev/)
2. git push origin feature-branch
3. GitHub PR → Merge to dev
4. 🎉 Coolify auto-deploys
5. Monitor in Coolify UI
```

---

## Why Coolify?

### ✅ Advantages

| Feature | Without Coolify | With Coolify | Improvement |
|---------|----------------|--------------|-------------|
| **Deployment** | Manual `git pull && docker compose restart` | Push → Auto-Deploy | ⭐⭐⭐⭐⭐ |
| **Multi-Environment** | Manual copy/paste configs | UI-based per environment | ⭐⭐⭐⭐⭐ |
| **Rollback** | Manual `git checkout && restart` | 1-Click in UI | ⭐⭐⭐⭐⭐ |
| **Zero-Downtime** | Container restart = downtime | Rolling updates | ⭐⭐⭐⭐⭐ |
| **Secrets** | `.env` files (risk in git) | Encrypted in Coolify DB | ⭐⭐⭐⭐ |
| **Monitoring** | `docker logs -f` | Web UI + Health Checks | ⭐⭐⭐⭐ |
| **SSL** | Manual Let's Encrypt | Automatic SSL | ⭐⭐⭐⭐ |
| **Webhooks** | Custom scripts | Built-in GitHub integration | ⭐⭐⭐⭐ |

### ⚠️ Considerations

- **Resource Overhead:** Coolify needs ~500MB RAM (Server has 195GB free ✅)
- **Learning Curve:** 2-3 hours initial setup
- **Additional Component:** One more moving part to maintain

### 🎯 Verdict: **Highly Recommended!**

---

## Architecture

### Coolify Infrastructure

```
┌────────────────────────────────────────────────────────┐
│  Coolify Control Plane (brain.falklabs.de:8000)       │
│  ├── PostgreSQL (Coolify metadata)                    │
│  ├── Redis (Queue & Cache)                            │
│  └── Proxy (Traefik/Caddy)                            │
└────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  DEV ENV     │  │  STAGE ENV   │  │  PROD ENV    │
│  /srv/dev/   │  │  /srv/stage/ │  │  /srv/prod/  │
│              │  │              │  │              │
│  Branch: dev │  │  Branch:stage│  │  Branch: main│
│  Auto-Deploy │  │  Semi-Auto   │  │  Manual Only │
└──────────────┘  └──────────────┘  └──────────────┘
```

### BRAiN Application Stack (per environment)

```
Each Environment runs:
├── backend (FastAPI)         → Port: 8000 (internal)
├── control_deck (Next.js)    → Port: 3000 (internal)
├── axe_ui (Next.js)          → Port: 3000 (internal)
├── postgres (PostgreSQL 16)  → Port: 5432 (internal)
├── redis (Redis 7)           → Port: 6379 (internal)
├── qdrant (Vector DB)        → Port: 6333 (internal)
├── ollama (LLM Server)       → Port: 11434 (internal)
└── openwebui (Web UI)        → Port: 8080 (internal)

Coolify Proxy handles:
- External → Internal port mapping
- SSL termination
- Load balancing (future)
```

---

## Prerequisites

### Server Requirements

**Hardware:**
- ✅ **CPU:** Available (check: `nproc`)
- ✅ **RAM:** 195GB free (Coolify needs ~500MB)
- ✅ **Disk:** 301G total, 94G used, 195G available
- ✅ **OS:** Linux (Ubuntu/Debian)

**Software:**
- ✅ **Docker:** 29.1.2 installed
- ✅ **Docker Compose:** Installed
- ✅ **Git:** Installed
- ⚠️ **Coolify:** Not installed (Phase 1)

### Network & DNS

**Domains Required:**
- ✅ `dev.brain.falklabs.de` → Development
- ✅ `stage.brain.falklabs.de` → Staging
- ✅ `brain.falklabs.de` → Production
- ⚠️ `coolify.brain.falklabs.de` → Coolify UI (optional)

**DNS Provider:** [TO BE CONFIRMED]
- Hetzner DNS?
- Cloudflare?
- Other?

**Ports Required:**

| Service | Port | Status |
|---------|------|--------|
| Coolify UI | 8000 | ⚠️ Currently: dev-backend |
| Coolify Proxy (HTTP) | 80 | ✅ Free |
| Coolify Proxy (HTTPS) | 443 | ✅ Free |
| Coolify SSH | 22 | ✅ Existing |

**Port Conflict Resolution:**
- Current `dev-backend` on 8001 → Move to Coolify-managed
- Coolify UI default: 8000 → Change to 9000 (alternative)

### GitHub

**Repository:**
- ✅ `https://github.com/satoshiflow/BRAiN.git`

**Branches:**
- ✅ `v2` (current, will become `dev`)
- ⚠️ `dev` (to be created/renamed from v2)
- ⚠️ `stage` (to be created)
- ✅ `main` (exists, will be production)

**Access:**
- ✅ User `claude` has SSH key for GitHub
- ✅ HTTPS clone works on server

---

## Phase 0: Cleanup & Preparation

### Step 1: Remove /root/BRAiN/

```bash
# As root
rm -rf /root/BRAiN/
```

**Reason:** Not needed with Coolify. Work directly in `/srv/dev/`.

### Step 2: Push current work from /srv/dev/

```bash
# As user claude
su - claude
cd /srv/dev

# Check current branch
git branch
# Should show: * claude/python-path-and-deps-fix-h1NXi

# Check status
git status

# If there's uncommitted work:
git add -A
git commit -m "chore: Pre-Coolify migration checkpoint"

# Push (if branch exists on GitHub)
git push origin $(git branch --show-current)

# Return to root
exit
```

### Step 3: Backup current /srv/dev/

```bash
# As root
cd /srv
tar -czf /root/backups/srv-dev-pre-coolify-$(date +%Y%m%d_%H%M%S).tar.gz dev/

# Verify backup
ls -lh /root/backups/
```

### Step 4: Document current environment

```bash
# Save current container state
docker ps -a > /root/backups/docker-ps-pre-coolify.txt

# Save current environment variables
cd /srv/dev
cat .env > /root/backups/srv-dev-env-backup.txt 2>/dev/null || echo "No .env file"

# Save docker-compose config
cat docker-compose.yml > /root/backups/docker-compose-backup.yml
cat docker-compose.dev.yml > /root/backups/docker-compose-dev-backup.yml
```

### Step 5: Stop current containers

```bash
cd /srv/dev
docker compose down

# Verify stopped
docker ps
# Should show no brain containers
```

### Step 6: Prepare directories

```bash
# Ensure proper ownership
chown -R claude:claude /srv/dev
chown -R claude:claude /srv/stage 2>/dev/null || mkdir -p /srv/stage && chown -R claude:claude /srv/stage
chown -R claude:claude /srv/prod 2>/dev/null || mkdir -p /srv/prod && chown -R claude:claude /srv/prod

# Verify
ls -la /srv/
```

---

## Phase 1: Coolify Installation

### Step 1: Pre-Installation Check

```bash
# As root
# Check if port 8000 is free
netstat -tuln | grep 8000

# If 8000 is occupied, we'll configure Coolify on port 9000
```

### Step 2: Install Coolify

**Official Installation (recommended):**

```bash
# As root
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

**What it does:**
1. Installs Coolify via Docker Compose
2. Creates PostgreSQL database for Coolify
3. Sets up Traefik/Caddy proxy
4. Starts Coolify on `http://SERVER_IP:8000`

**Alternative Installation (custom port):**

```bash
# If port 8000 is occupied
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash -s -- --port 9000
```

### Step 3: Verify Installation

```bash
# Check Coolify containers
docker ps | grep coolify

# Should show:
# - coolify
# - coolify-db (PostgreSQL)
# - coolify-proxy (Traefik/Caddy)
# - coolify-redis (optional)

# Check Coolify logs
docker logs coolify -f

# Wait for: "Coolify is ready"
```

### Step 4: Access Coolify UI

**Browser:**
```
http://brain.falklabs.de:8000
# or
http://46.224.37.114:8000
```

**First Login:**
1. Create admin account
   - Email: [YOUR_EMAIL]
   - Password: [SECURE_PASSWORD]
2. Set server name: `brain-main`
3. Configure default settings

### Step 5: Register Server

**In Coolify UI:**
1. Go to "Servers"
2. Click "Add Server"
3. Select "Localhost" (Coolify runs on same server)
4. Name: `brain-production-server`
5. IP: `localhost` or `127.0.0.1`
6. Validate connection

---

## Phase 2: Environment Configuration

### Environment 1: Development (/srv/dev/)

#### Step 1: Create Project

**Coolify UI → Projects → New Project:**
- **Name:** `brain-dev`
- **Description:** BRAiN Development Environment

#### Step 2: Add Application

**Project brain-dev → New Resource → Docker Compose:**

**General:**
- **Name:** `brain-dev`
- **Server:** `brain-production-server`

**Source:**
- **Type:** Git Repository
- **Repository URL:** `https://github.com/satoshiflow/BRAiN.git`
- **Branch:** `dev` (or current: `v2`)
- **Auto Deploy:** ✅ Enabled

**Build Configuration:**
- **Build Pack:** Docker Compose
- **Compose File:** `docker-compose.yml`
- **Additional Compose Files:** `docker-compose.dev.yml`
- **Base Directory:** `/` (root of repo)

**Domains:**
- **Primary Domain:** `dev.brain.falklabs.de`
- **SSL:** ✅ Let's Encrypt (auto)

**Environment Variables:**
```bash
ENVIRONMENT=development
POSTGRES_DB=brain_dev
POSTGRES_USER=brain
POSTGRES_PASSWORD=<SECURE_PASSWORD>
DATABASE_URL=postgresql://brain:<PASSWORD>@postgres:5432/brain_dev
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=<SECURE_SECRET>
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2:latest
LOG_LEVEL=DEBUG
```

**Health Check:**
- **Enabled:** ✅
- **Endpoint:** `/health` (backend)
- **Interval:** 30s
- **Timeout:** 10s
- **Retries:** 3

**Deployment:**
- Click "Deploy"
- Monitor logs in real-time
- Wait for "Deployment successful"

#### Step 3: Configure GitHub Webhook

**Coolify UI → brain-dev → Settings → Webhooks:**
- Copy Webhook URL: `https://dev.brain.falklabs.de/webhooks/xxxx`

**GitHub → Repository Settings → Webhooks:**
- **Payload URL:** [Coolify Webhook URL]
- **Content type:** `application/json`
- **Events:** Push events
- **Branches:** `dev`
- **Active:** ✅

**Test:**
```bash
# Make a test commit
cd /srv/dev
echo "# Test" >> README.md
git add README.md
git commit -m "test: Coolify webhook"
git push origin dev

# Check Coolify UI for auto-deployment
```

---

### Environment 2: Staging (/srv/stage/)

#### Step 1: Create Project

**Coolify UI → Projects → New Project:**
- **Name:** `brain-stage`
- **Description:** BRAiN Staging Environment

#### Step 2: Add Application

**Similar to dev, but:**
- **Branch:** `stage`
- **Domain:** `stage.brain.falklabs.de`
- **Auto Deploy:** ⚠️ Optional (manual approval recommended)
- **Environment Variables:** Same as dev, but `ENVIRONMENT=staging`

#### Step 3: Create stage branch on GitHub

```bash
cd /srv/dev
git checkout -b stage dev
git push origin stage
```

---

### Environment 3: Production (/srv/prod/)

#### Step 1: Create Project

**Coolify UI → Projects → New Project:**
- **Name:** `brain-prod`
- **Description:** BRAiN Production Environment

#### Step 2: Add Application

**Similar to dev/stage, but:**
- **Branch:** `main`
- **Domain:** `brain.falklabs.de`
- **Auto Deploy:** ❌ Disabled (manual only!)
- **Environment Variables:** Production values
- **Health Check:** More strict (shorter timeout)

**Advanced:**
- **Blue-Green Deployment:** ✅ Enable
- **Pre-deployment Script:** Optional (database migrations)
- **Post-deployment Script:** Optional (cache warming)

---

## Phase 3: GitHub Integration

### Step 1: Branch Strategy

```bash
# Rename v2 to dev
cd /srv/dev
git checkout v2
git branch -m v2 dev
git push origin dev
git push origin --delete v2

# Create stage from dev
git checkout -b stage dev
git push origin stage

# main branch already exists (empty or old)
# Will be used after first production-ready release
```

### Step 2: Branch Protection Rules

**GitHub → Repository → Settings → Branches → Add rule:**

**Branch: `dev`**
- ✅ Require pull request reviews: NO (direct push allowed)
- ✅ Require status checks: NO
- ✅ Auto-deploy via Coolify

**Branch: `stage`**
- ✅ Require pull request reviews: YES (1 approval)
- ✅ Require status checks: YES (tests must pass)
- ✅ Only allow merge from: `dev`

**Branch: `main`**
- ✅ Require pull request reviews: YES (1 approval)
- ✅ Require status checks: YES (all checks)
- ✅ Only allow merge from: `stage`
- ✅ Require signed commits (optional)
- ✅ Manual deploy only (Coolify UI)

### Step 3: GitHub Actions (Optional)

**For automated tests before deployment:**

`.github/workflows/test-dev.yml`:
```yaml
name: Test Dev Branch

on:
  push:
    branches: [dev]
  pull_request:
    branches: [dev]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          cd backend
          docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm backend pytest
```

---

## Phase 4: Migration Strategy

### Step 1: Verify Coolify is running

```bash
# Check Coolify status
docker ps | grep coolify

# Access UI
curl -I http://localhost:8000
```

### Step 2: Migrate Development Environment

```bash
# Current containers should already be stopped (Phase 0)

# Coolify will:
# 1. Clone git repo to managed directory
# 2. Build docker images
# 3. Start containers
# 4. Configure proxy

# Monitor in Coolify UI
```

**Expected Result:**
- `dev.brain.falklabs.de` → BRAiN Dev running
- SSL certificate auto-generated
- Health checks passing

### Step 3: Migrate Staging

```bash
# Create stage branch (already done in Phase 3)
# Deploy via Coolify UI

# Test:
curl https://stage.brain.falklabs.de/health
```

### Step 4: Prepare Production

```bash
# Don't deploy yet!
# Wait until dev + stage are stable
# Production will be deployed manually when ready
```

### Step 5: DNS Configuration

**Required DNS Records:**

```
Type  | Name  | Value              | TTL
------|-------|--------------------|-----
A     | dev   | 46.224.37.114      | 300
A     | stage | 46.224.37.114      | 300
A     | @     | 46.224.37.114      | 300  (for brain.falklabs.de)
```

**Note:** If DNS is with Hetzner, Cloudflare, or other provider, configure there.

---

## Phase 5: New Workflow

### Daily Development Workflow

#### Option A: VSCode Remote SSH (Recommended)

**Setup:**
```bash
# Windows PC: .ssh/config
Host brain-dev
    HostName brain.falklabs.de
    User claude
    IdentityFile ~/.ssh/claude_brain_key
```

**Daily Work:**
1. VSCode → Remote SSH → brain-dev
2. Open Folder: `/srv/dev` (Coolify-managed)
3. Create feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```
4. Edit code in VSCode
5. Commit & Push:
   ```bash
   git add .
   git commit -m "feat: My feature"
   git push origin feature/my-feature
   ```
6. GitHub → Create PR: `feature/my-feature` → `dev`
7. Review & Merge
8. 🎉 Coolify auto-deploys!
9. Monitor: Coolify UI → brain-dev → Logs

#### Option B: Local Development + Push

**Work on Windows PC:**
1. Clone repo locally
2. Work on feature branch
3. Push to GitHub
4. Create PR → Merge to dev
5. Coolify auto-deploys

**Test on Server:**
- `https://dev.brain.falklabs.de`

### Staging Promotion Workflow

```bash
# After dev is stable, promote to staging:

# Option 1: Via GitHub PR
# Create PR: dev → stage
# Review & Merge
# Coolify deploys to stage

# Option 2: Via CLI
cd /srv/dev
git checkout stage
git merge dev
git push origin stage
# Coolify auto-deploys (if enabled)
```

### Production Release Workflow

```bash
# After staging is tested and approved:

# 1. Create Git Tag
git checkout main
git merge stage
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin main --tags

# 2. Manual Deploy in Coolify UI
# - Go to brain-prod project
# - Click "Deploy"
# - Confirm deployment
# - Monitor logs
# - Verify health checks

# 3. Rollback if needed
# - Coolify UI → Previous Deployment
# - Click "Redeploy"
```

---

## Phase 6: Advanced Features

### 6.1 Secrets Management

**Coolify UI → Project → Environment Variables:**
- All secrets stored encrypted in Coolify DB
- Not in Git!
- Per-environment separation

**Migration:**
```bash
# Old: .env file
POSTGRES_PASSWORD=mypassword

# New: Coolify UI
# Add as environment variable (encrypted)
```

### 6.2 Health Checks

**Backend health endpoint:**
```python
# backend/main.py
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": os.getenv("VERSION", "unknown")
    }
```

**Coolify Configuration:**
- Health Check Path: `/health`
- Expected Status Code: 200
- Interval: 30s
- Timeout: 10s
- Retries: 3

### 6.3 Rollback Strategy

**Automatic Rollback:**
- Coolify monitors health checks
- If new deployment fails → Auto-rollback

**Manual Rollback:**
1. Coolify UI → Project → Deployments
2. Select previous successful deployment
3. Click "Redeploy"
4. Confirm

**Time to Rollback:** ~30 seconds

### 6.4 Notifications

**Coolify → Settings → Notifications:**

**Slack:**
- Webhook URL: [YOUR_SLACK_WEBHOOK]
- Events: Deployment Success, Deployment Failed

**Discord:**
- Webhook URL: [YOUR_DISCORD_WEBHOOK]

**Email:**
- SMTP Server: [YOUR_SMTP]

**Telegram:**
- Bot Token + Chat ID

### 6.5 Monitoring Integration

**Prometheus Metrics:**
- Coolify exposes metrics at `/metrics`
- Scrape with existing Prometheus

**Grafana Dashboard:**
- Import Coolify dashboard
- Monitor all environments in one view

### 6.6 Database Backups

**Automated Backups:**
```bash
# Coolify UI → Services → postgres
# Enable automatic backups
# Schedule: Daily at 2 AM
# Retention: 7 days
```

**Manual Backup:**
```bash
# Via Coolify UI: Backup Now
# Or via CLI:
docker exec brain-dev-postgres pg_dump -U brain brain_dev > backup.sql
```

---

## Troubleshooting

### Issue 1: Deployment Failed

**Symptoms:**
- Coolify shows "Deployment failed"
- Red status in UI

**Solutions:**
1. **Check logs:**
   ```
   Coolify UI → Project → Logs
   ```
2. **Common causes:**
   - Missing environment variables
   - Docker build errors
   - Port conflicts
   - Health check failures

3. **Fix & Retry:**
   - Fix issue in code
   - Push to GitHub
   - Coolify auto-redeploys

### Issue 2: Health Check Failing

**Symptoms:**
- Deployment completes but status is "Unhealthy"

**Solutions:**
1. **Verify health endpoint:**
   ```bash
   docker exec brain-dev-backend curl http://localhost:8000/health
   ```
2. **Check health check config:**
   - Path correct?
   - Timeout sufficient?
3. **Adjust in Coolify UI**

### Issue 3: SSL Certificate Error

**Symptoms:**
- `https://dev.brain.falklabs.de` shows SSL error

**Solutions:**
1. **Verify DNS:**
   ```bash
   nslookup dev.brain.falklabs.de
   ```
2. **Regenerate certificate:**
   ```
   Coolify UI → Project → SSL → Regenerate
   ```
3. **Check Let's Encrypt rate limits**

### Issue 4: GitHub Webhook Not Triggering

**Symptoms:**
- Push to GitHub doesn't trigger deployment

**Solutions:**
1. **Check webhook:**
   ```
   GitHub → Settings → Webhooks → Recent Deliveries
   ```
2. **Verify webhook URL:**
   - Should be: `https://dev.brain.falklabs.de/webhooks/xxxx`
3. **Test manually:**
   ```
   Coolify UI → Project → Deploy Now
   ```

### Issue 5: Port Conflicts

**Symptoms:**
- Coolify can't start on port 8000

**Solutions:**
1. **Stop conflicting service:**
   ```bash
   docker ps | grep 8000
   docker stop <container>
   ```
2. **Or change Coolify port:**
   ```bash
   # Re-install with custom port
   curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash -s -- --port 9000
   ```

---

## Rollback Plan

### Complete Rollback to Manual Deployment

**If Coolify doesn't work out:**

#### Step 1: Stop Coolify

```bash
docker compose -f /data/coolify/docker-compose.yml down
```

#### Step 2: Restore /srv/dev/

```bash
cd /srv
rm -rf dev/
tar -xzf /root/backups/srv-dev-pre-coolify-*.tar.gz
```

#### Step 3: Restore Docker Containers

```bash
cd /srv/dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

#### Step 4: Verify

```bash
docker ps
curl http://localhost:8001/health
```

**Time to Rollback:** ~10 minutes

---

## Checklist

### Pre-Installation
- [ ] Backup /srv/dev/
- [ ] Document current state
- [ ] Stop running containers
- [ ] Verify disk space (>10GB free)
- [ ] Verify port availability

### Installation
- [ ] Install Coolify
- [ ] Access Coolify UI
- [ ] Create admin account
- [ ] Register server

### Configuration
- [ ] Create brain-dev project
- [ ] Configure GitHub integration
- [ ] Set up webhooks
- [ ] Add environment variables
- [ ] Configure health checks

### Migration
- [ ] Deploy to dev
- [ ] Verify dev.brain.falklabs.de works
- [ ] Configure SSL
- [ ] Test auto-deployment
- [ ] Deploy to stage (optional)
- [ ] Prepare prod (don't deploy yet)

### Post-Migration
- [ ] Update CLAUDE.md
- [ ] Document new workflow
- [ ] Train team (if applicable)
- [ ] Monitor for 24h
- [ ] Celebrate! 🎉

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Gather missing info** (DNS provider, etc.)
3. **Schedule maintenance window** (low-traffic time)
4. **Execute Phase 0** (cleanup & backup)
5. **Execute Phase 1** (install Coolify)
6. **Execute Phase 2** (configure environments)
7. **Monitor & Optimize**

---

## Support & Resources

**Coolify Documentation:**
- https://coolify.io/docs

**Community:**
- Discord: https://coollabs.io/discord
- GitHub: https://github.com/coollabs-io/coolify

**BRAiN Internal:**
- CLAUDE.md v0.6.1
- GitHub: https://github.com/satoshiflow/BRAiN

---

**Last Updated:** 2026-01-05
**Author:** Claude (AI Assistant)
**Status:** Draft - Awaiting Approval & Missing Info
