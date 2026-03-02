# BRAiN Infrastructure Setup - Complete Guide

**Everything you need to set up production-ready infrastructure**

---

## 📚 Quick Navigation

| Document | Purpose |
|----------|---------|
| **This file** | Master overview & setup order |
| `DEPLOYMENT_GUIDE.md` | Complete deployment documentation |
| `BRANCH_PROTECTION.md` | GitHub branch protection rules |
| `setup_branches.sh` | Create main/dev/stage branches |
| `server_setup.sh` | Initialize remote server (as root) |
| `deploy.sh` | Deploy to environments |
| `.github/workflows/` | CI/CD automation |

---

## 🎯 What This Setup Provides

### Branch Strategy
- ✅ **`main`** - Production (stable releases only)
- ✅ **`stage`** - Testing (pre-production validation)
- ✅ **`dev`** - Development (active work)

### Server Environments
- ✅ `/srv/dev/` → dev.brain.falklabs.de
- ✅ `/srv/stage/` → stage.brain.falklabs.de
- ✅ `/srv/prod/` → brain.falklabs.de

### Automation
- ✅ GitHub Actions CI/CD
- ✅ Auto-deploy on branch push
- ✅ Health checks
- ✅ Database backups
- ✅ Rollback capabilities

---

## 🚀 Setup Order (Step-by-Step)

### Phase 1: GitHub Branch Setup (15 min)

**On your local machine:**

```bash
cd /home/user/BRAiN

# 1. Run branch creation script
chmod +x setup_branches.sh
./setup_branches.sh

# 2. Configure branch protection
# See BRANCH_PROTECTION.md for instructions
# Or use GitHub Web UI:
# https://github.com/satoshiflow/BRAiN/settings/branches

# 3. Set default branch to 'dev'
# https://github.com/satoshiflow/BRAiN/settings
```

**Result:** ✅ Three-tier branch strategy ready

---

### Phase 2: Remote Server Setup (20 min)

**On brain.falklabs.de:**

```bash
# 1. Upload setup script
scp server_setup.sh root@brain.falklabs.de:/root/

# 2. SSH as root
ssh root@brain.falklabs.de

# 3. Run setup script
chmod +x /root/server_setup.sh
/root/server_setup.sh

# 4. SAVE THE SSH PUBLIC KEY DISPLAYED!
# You'll need it for GitHub deploy key
```

**What it creates:**
- ✅ Claude user with sudo access
- ✅ Deployment directories (/srv/dev, /srv/stage, /srv/prod)
- ✅ SSH key pair
- ✅ Docker, Git, Nginx installed
- ✅ Proper permissions

**Result:** ✅ Server ready for deployments

---

### Phase 3: GitHub Configuration (10 min)

**Configure GitHub access:**

```bash
# 1. Add deploy key
# Go to: https://github.com/satoshiflow/BRAiN/settings/keys
# Click "Add deploy key"
# Title: "Claude Deploy Key - brain.falklabs.de"
# Paste the public key from server_setup.sh output
# ✅ Check "Allow write access"

# 2. Add deployment secret
# Go to: https://github.com/satoshiflow/BRAiN/settings/secrets/actions
# Click "New repository secret"
# Name: DEPLOY_SSH_KEY
# Value: Private key from server

# Get private key:
ssh root@brain.falklabs.de "cat /home/claude/.ssh/id_ed25519"
# Copy entire output including -----BEGIN/END-----
```

**Result:** ✅ GitHub can deploy to server

---

### Phase 4: First Deployment (15 min)

**Deploy to development:**

```bash
# 1. SSH as claude user
ssh claude@brain.falklabs.de

# 2. Clone repository to dev
cd /srv/dev
git clone -b dev git@github.com:satoshiflow/BRAiN.git .

# 3. Configure environment
cp .env.example .env
nano .env  # Edit configuration

# 4. Deploy
chmod +x deploy.sh
./deploy.sh dev

# 5. Verify
curl http://localhost:8001/api/health
```

**Result:** ✅ Development environment running

---

### Phase 5: CI/CD Verification (5 min)

**Test automatic deployment:**

```bash
# Make a change on dev branch
git checkout dev
echo "# Test" >> README.md
git add README.md
git commit -m "test: CI/CD verification"
git push origin dev

# Watch GitHub Actions
gh run watch

# Check deployment
curl https://dev.brain.falklabs.de/api/health
```

**Result:** ✅ CI/CD pipeline working

---

## 📋 Configuration Checklist

### GitHub Settings

- [ ] Branches created (main, dev, stage)
- [ ] Branch protection rules configured
- [ ] Default branch set to `dev`
- [ ] Deploy key added
- [ ] `DEPLOY_SSH_KEY` secret added
- [ ] GitHub Actions enabled

### Server Setup

- [ ] Claude user created
- [ ] SSH keys generated
- [ ] Deployment directories created (/srv/dev, /srv/stage, /srv/prod)
- [ ] Docker installed
- [ ] Git configured
- [ ] Nginx installed (optional for now)

### Deployments

- [ ] Development deployed (/srv/dev/)
- [ ] Environment files configured (.env)
- [ ] Health checks passing
- [ ] Staging deployed (/srv/stage/) - optional
- [ ] Production deployed (/srv/prod/) - when ready

---

## 🔧 Common Tasks

### Deploy to Specific Environment

```bash
# Development
ssh claude@brain.falklabs.de "cd /srv/dev && ./deploy.sh dev"

# Staging
ssh claude@brain.falklabs.de "cd /srv/stage && ./deploy.sh stage"

# Production
ssh claude@brain.falklabs.de "cd /srv/prod && ./deploy.sh prod"
```

### Create Pull Request

```bash
# Promote dev → stage
gh pr create --base stage --head dev \
  --title "chore: Promote to staging" \
  --body "Ready for testing"

# Promote stage → main
gh pr create --base main --head stage \
  --title "release: Production release" \
  --body "Tested and verified"
```

### View Logs

```bash
# Development logs
ssh claude@brain.falklabs.de "cd /srv/dev && docker-compose logs -f"

# Specific service
ssh claude@brain.falklabs.de "cd /srv/dev && docker-compose logs -f backend"
```

### Restart Services

```bash
ssh claude@brain.falklabs.de "cd /srv/dev && docker-compose restart"
```

---

## 🆘 Troubleshooting

### Setup Issues

**Problem:** `setup_branches.sh` fails with 403 error

**Solution:** Use GitHub web UI or `gh` CLI to create branches manually. Protected branches can't be pushed directly.

---

**Problem:** Server setup fails

**Solution:**
```bash
# Check if running as root
whoami  # Should show 'root'

# Check prerequisites
apt-get update
apt-get install -y git docker.io docker-compose
```

---

**Problem:** Deploy key not working

**Solution:**
```bash
# Test SSH to GitHub from server
ssh -T git@github.com

# If fails, check deploy key:
# https://github.com/satoshiflow/BRAiN/settings/keys
# Ensure "Allow write access" is checked
```

---

**Problem:** CI/CD workflow failing

**Solution:**
```bash
# Check GitHub Actions logs
gh run list
gh run view <run-id>

# Common fixes:
# 1. Add DEPLOY_SSH_KEY secret
# 2. Ensure claude user exists on server
# 3. Check disk space: df -h
```

---

### Deployment Issues

**Problem:** Docker build fails

**Solution:**
```bash
cd /srv/dev
docker-compose build --no-cache
docker-compose up -d
```

---

**Problem:** Database migration error

**Solution:**
```bash
cd /srv/dev
docker-compose exec backend alembic upgrade head

# If still fails, check database:
docker-compose exec postgres psql -U brain -d brain
```

---

**Problem:** Port already in use

**Solution:**
```bash
# Find process using port
lsof -i :8001

# Kill process
kill -9 <PID>

# Or change port in docker-compose.dev.yml
```

---

## 📊 Environment Comparison

| Feature | Development | Staging | Production |
|---------|-------------|---------|------------|
| Branch | `dev` | `stage` | `main` |
| Path | `/srv/dev/` | `/srv/stage/` | `/srv/prod/` |
| Backend Port | 8001 | 8002 | 8000 |
| Frontend Port | 3001 | 3003 | 3000 |
| URL | dev.brain.falklabs.de | stage.brain.falklabs.de | brain.falklabs.de |
| Auto-deploy | ✅ On push | ✅ On push | ⚠️ Manual approval |
| Database | Dev DB | Stage DB | Production DB |
| Backups | No | Optional | ✅ Yes |
| SSL | Let's Encrypt | Let's Encrypt | Let's Encrypt |

---

## 🎓 Next Steps

### After Setup Complete:

1. **Configure Nginx** (optional, for SSL/domain routing)
   ```bash
   # See nginx/README.md for configuration
   ```

2. **Set up monitoring** (optional)
   ```bash
   # Add monitoring tools (Prometheus, Grafana, etc.)
   ```

3. **Configure backups** (recommended for production)
   ```bash
   # Automated database backups
   # See DEPLOYMENT_GUIDE.md
   ```

4. **Continue development!**
   ```bash
   git checkout dev
   # Start coding...
   ```

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `DEPLOYMENT_GUIDE.md` | Complete deployment documentation |
| `BRANCH_PROTECTION.md` | GitHub branch protection rules |
| `INFRASTRUCTURE_SETUP.md` | This file - master setup guide |
| `setup_branches.sh` | Creates main/dev/stage branches |
| `server_setup.sh` | Initializes remote server |
| `deploy.sh` | Deployment automation script |
| `.github/workflows/deploy-dev.yml` | Development CI/CD |
| `.github/workflows/deploy-stage.yml` | Staging CI/CD |
| `.github/workflows/deploy-prod.yml` | Production CI/CD |

---

## ✅ Infrastructure Complete!

Once you complete all phases above, you'll have:

- ✅ Three-tier branch strategy (main/stage/dev)
- ✅ Three isolated environments on server
- ✅ Automated CI/CD pipeline
- ✅ Health checks and monitoring
- ✅ Rollback capabilities
- ✅ Database migrations
- ✅ Production-ready infrastructure

**Ready to develop on a solid foundation!** 🚀

---

**Questions?** Check the detailed guides:
- Full deployment: `DEPLOYMENT_GUIDE.md`
- Branch protection: `BRANCH_PROTECTION.md`
- Troubleshooting: See sections above
