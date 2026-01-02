# BRAiN Deployment Guide

**Complete Infrastructure Setup & Deployment**

---

## Table of Contents

1. [Overview](#overview)
2. [Branch Strategy](#branch-strategy)
3. [Server Setup](#server-setup)
4. [Local Setup](#local-setup)
5. [Deployment Process](#deployment-process)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Troubleshooting](#troubleshooting)

---

## Overview

### Infrastructure

| Environment | Branch | Server Path | URL | Purpose |
|-------------|--------|-------------|-----|---------|
| **Development** | `dev` | `/srv/dev/` | dev.brain.falklabs.de | Active development |
| **Staging** | `stage` | `/srv/stage/` | stage.brain.falklabs.de | Pre-production testing |
| **Production** | `main` | `/srv/prod/` | brain.falklabs.de | Stable releases |

### Server Details

```
Host: brain.falklabs.de (46.224.37.114)
SSH Port: 22
User: claude (created via setup script)
Auth: SSH key only (no password)
```

---

## Branch Strategy

### Branch Flow

```
dev (development)
  ↓ PR when stable
stage (testing)
  ↓ PR after tests pass
main (production)
```

### Branch Protection

- **main:** Requires 1 approval, no direct pushes
- **stage:** Requires 1 approval, tests must pass
- **dev:** Auto-merge for `claude/*` branches

See `BRANCH_PROTECTION.md` for detailed rules.

---

## Server Setup

### Step 1: Initial Server Setup

Run on brain.falklabs.de as root:

```bash
# Upload setup script
scp server_setup.sh root@brain.falklabs.de:/root/

# SSH into server
ssh root@brain.falklabs.de

# Run setup
chmod +x /root/server_setup.sh
/root/server_setup.sh
```

**This creates:**
- ✅ Claude user with sudo access
- ✅ SSH key pair for Claude
- ✅ Deployment directories (/srv/dev, /srv/stage, /srv/prod)
- ✅ Docker, Git, Nginx installed
- ✅ Sudo permissions for deployment commands

### Step 2: Copy SSH Public Key

After running `server_setup.sh`, you'll see an SSH public key. **Save this!**

```bash
# On server, show public key again:
cat /home/claude/.ssh/id_ed25519.pub
```

### Step 3: Add Deploy Key to GitHub

1. Go to: https://github.com/satoshiflow/BRAiN/settings/keys
2. Click "Add deploy key"
3. Title: "Claude Deploy Key - brain.falklabs.de"
4. Paste the public key
5. ✅ Check "Allow write access"
6. Click "Add key"

### Step 4: Test SSH Access

```bash
# From your local machine
ssh claude@brain.falklabs.de

# Test Git access
ssh -T git@github.com
# Should say: "Hi satoshiflow/BRAiN! You've successfully authenticated..."
```

---

## Local Setup

### Prerequisites

```bash
# Install GitHub CLI
brew install gh  # macOS
sudo apt install gh  # Ubuntu

# Authenticate
gh auth login
```

### Step 1: Create Branches

```bash
cd /home/user/BRAiN

# Make setup script executable
chmod +x setup_branches.sh

# Run branch creation
./setup_branches.sh
```

**This creates:**
- `main` (from v2)
- `dev` (from v2)
- `stage` (from v2)

### Step 2: Configure Branch Protection

See `BRANCH_PROTECTION.md` for detailed instructions.

**Quick setup via GitHub Web UI:**

1. https://github.com/satoshiflow/BRAiN/settings/branches
2. Add protection rules for `main`, `stage`, `dev`
3. Set default branch to `dev`

### Step 3: Set Up GitHub Secrets

Add deployment SSH key to GitHub:

1. Go to: https://github.com/satoshiflow/BRAiN/settings/secrets/actions
2. Click "New repository secret"
3. Name: `DEPLOY_SSH_KEY`
4. Value: Private key from server

```bash
# On server (as claude user)
cat /home/claude/.ssh/id_ed25519
# Copy entire output including -----BEGIN/END-----
```

Paste into GitHub secret.

---

## Deployment Process

### Manual Deployment

**From your local machine:**

```bash
# Deploy development
ssh claude@brain.falklabs.de
cd /srv/dev
./deploy.sh dev

# Deploy staging
./deploy.sh stage

# Deploy production
./deploy.sh prod
```

**Or run remotely:**

```bash
ssh claude@brain.falklabs.de "cd /srv/dev && ./deploy.sh dev"
```

### What `deploy.sh` Does

1. ✅ Clones/updates repository from GitHub
2. ✅ Checks out correct branch (dev/stage/main)
3. ✅ Sets up environment files (.env)
4. ✅ Builds Docker images
5. ✅ Runs database migrations
6. ✅ Starts services
7. ✅ Runs health checks

### First-Time Deployment

```bash
# 1. SSH into server
ssh claude@brain.falklabs.de

# 2. Deploy to dev
cd /srv/dev
git clone -b dev git@github.com:satoshiflow/BRAiN.git .
cp .env.example .env
nano .env  # Configure environment variables

# 3. Run deployment
./deploy.sh dev

# 4. Check logs
docker-compose logs -f backend
```

### Environment Files

Each environment needs its own `.env`:

```bash
/srv/dev/.env        # Development config
/srv/stage/.env      # Staging config
/srv/prod/.env       # Production config
```

**Critical variables:**
```bash
DATABASE_URL=postgresql+asyncpg://brain:PASSWORD@postgres:5432/brain
REDIS_URL=redis://redis:6379/0
POSTGRES_PASSWORD=STRONG_PASSWORD_HERE
JWT_SECRET_KEY=RANDOM_SECRET_KEY_HERE

# WebGenesis (if using DNS features)
HETZNER_DNS_API_TOKEN=your_token_here
```

---

## CI/CD Pipeline

### Automatic Deployment

GitHub Actions automatically deploy on push:

| Branch | Workflow | Environment | Triggers |
|--------|----------|-------------|----------|
| `dev` | deploy-dev.yml | Development | Push to dev |
| `stage` | deploy-stage.yml | Staging | Push to stage |
| `main` | deploy-prod.yml | Production | Push to main + manual approval |

### Workflow Process

**Development:**
```
1. Push to dev branch
2. GitHub Actions triggers
3. Deploys to /srv/dev/
4. Health check
5. ✓ dev.brain.falklabs.de updated
```

**Staging:**
```
1. Create PR: dev → stage
2. Merge PR
3. GitHub Actions triggers
4. Deploys to /srv/stage/
5. Runs integration tests
6. ✓ stage.brain.falklabs.de updated
```

**Production:**
```
1. Create PR: stage → main
2. Require approval
3. Merge PR
4. GitHub Actions triggers
5. Creates database backup
6. Deploys to /srv/prod/
7. Runs migrations
8. Creates release tag
9. ✓ brain.falklabs.de updated
```

### Manual Workflow Trigger

```bash
# Trigger deployment manually
gh workflow run deploy-dev.yml
gh workflow run deploy-stage.yml
gh workflow run deploy-prod.yml
```

---

## Troubleshooting

### Deployment Failed

**Check logs:**
```bash
ssh claude@brain.falklabs.de
cd /srv/dev  # or stage/prod
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Common issues:**

1. **Environment variables missing:**
   ```bash
   nano /srv/dev/.env
   # Add missing variables
   ./deploy.sh dev
   ```

2. **Docker build failure:**
   ```bash
   docker-compose build --no-cache
   ```

3. **Database migration error:**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

4. **Port already in use:**
   ```bash
   docker-compose down
   lsof -i :8001  # Find process
   kill -9 <PID>
   docker-compose up -d
   ```

### SSH Access Issues

**Can't connect to server:**
```bash
# Test SSH connection
ssh -v claude@brain.falklabs.de

# Check SSH key
ssh-add -l

# Add key if needed
ssh-add ~/.ssh/id_ed25519
```

**GitHub deploy key issues:**
```bash
# Test GitHub SSH
ssh -T git@github.com

# If fails, check deploy key at:
# https://github.com/satoshiflow/BRAiN/settings/keys
```

### GitHub Actions Failing

**Check workflow status:**
```bash
gh run list
gh run view <run-id>
```

**Common fixes:**

1. **SSH key missing:** Add `DEPLOY_SSH_KEY` to GitHub secrets
2. **Permissions:** Ensure claude user has sudo rights
3. **Disk space:** Check with `df -h`

### Rollback

**Quick rollback to previous commit:**

```bash
ssh claude@brain.falklabs.de
cd /srv/prod

# See recent commits
git log --oneline -5

# Rollback to previous commit
git checkout <commit-hash>
./deploy.sh prod
```

**Restore database backup:**

```bash
cd /srv/prod
docker-compose exec postgres psql -U brain -d brain < /srv/backups/<timestamp>/brain.sql
```

---

## Monitoring

### Service Status

```bash
# Check running containers
ssh claude@brain.falklabs.de "docker ps"

# Check specific environment
ssh claude@brain.falklabs.de "cd /srv/dev && docker-compose ps"
```

### Health Checks

```bash
# Development
curl https://dev.brain.falklabs.de/api/health

# Staging
curl https://stage.brain.falklabs.de/api/health

# Production
curl https://brain.falklabs.de/api/health
```

### Logs

```bash
# Real-time logs
ssh claude@brain.falklabs.de "cd /srv/dev && docker-compose logs -f"

# Last 100 lines
ssh claude@brain.falklabs.de "cd /srv/dev && docker-compose logs --tail=100"

# Specific service
ssh claude@brain.falklabs.de "cd /srv/dev && docker-compose logs -f backend"
```

---

## Quick Reference

### Deployment Commands

```bash
# Local deployment
ssh claude@brain.falklabs.de "cd /srv/dev && ./deploy.sh dev"
ssh claude@brain.falklabs.de "cd /srv/stage && ./deploy.sh stage"
ssh claude@brain.falklabs.de "cd /srv/prod && ./deploy.sh prod"

# Restart services
ssh claude@brain.falklabs.de "cd /srv/dev && docker-compose restart"

# View logs
ssh claude@brain.falklabs.de "cd /srv/dev && docker-compose logs -f"

# Pull latest code
ssh claude@brain.falklabs.de "cd /srv/dev && git pull origin dev"
```

### GitHub PR Commands

```bash
# Create PR: dev → stage
gh pr create --base stage --head dev \
  --title "chore: Promote to staging" \
  --body "Ready for testing"

# Create PR: stage → main
gh pr create --base main --head stage \
  --title "release: v2.1.0" \
  --body "Production release"

# Merge PR
gh pr merge <pr-number> --squash
```

---

## Next Steps

1. ✅ Run `server_setup.sh` on brain.falklabs.de
2. ✅ Add deploy key to GitHub
3. ✅ Run `setup_branches.sh` to create branches
4. ✅ Configure branch protection rules
5. ✅ Add `DEPLOY_SSH_KEY` to GitHub secrets
6. ✅ Test first deployment to dev
7. ✅ Verify CI/CD pipeline
8. 🚀 Start developing!

---

**Need help? Check the scripts:**
- `server_setup.sh` - Server initialization
- `setup_branches.sh` - Branch creation
- `deploy.sh` - Deployment automation
- `BRANCH_PROTECTION.md` - Protection rules
