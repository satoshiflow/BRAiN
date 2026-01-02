# Server Deployment Commands - Execute on brain.falklabs.de

**Current Status:**
- ✅ Logged in as: claude
- ✅ Location: /srv/dev/
- ✅ Branch: v2
- ✅ deploy.sh: present and executable
- ⚠️ Missing: docker-compose.dev.yml (created in new commit)
- ⚠️ Needs: .env configuration with secure passwords

---

## STEP 1: Create docker-compose.dev.yml

The docker-compose.dev.yml file is required but missing on v2 branch. Create it manually:

```bash
cd /srv/dev

cat > docker-compose.dev.yml << 'EOF'
# Docker Compose overrides for DEVELOPMENT environment
# Used with: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

services:
  backend:
    container_name: dev-backend
    ports:
      - "8001:8000"  # Dev backend on port 8001
    environment:
      - APP_ENV=development
      - LOG_LEVEL=DEBUG

  control_deck:
    container_name: dev-control-deck
    ports:
      - "3001:3000"  # Dev frontend on port 3001
    environment:
      - NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8001

  axe_ui:
    container_name: dev-axe-ui
    ports:
      - "3002:3000"  # Dev AXE UI on port 3002
    environment:
      - NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8001

  postgres:
    container_name: dev-postgres
    environment:
      POSTGRES_DB: brain_dev

  redis:
    container_name: dev-redis

  qdrant:
    container_name: dev-qdrant

  ollama:
    container_name: dev-ollama

  openwebui:
    container_name: dev-openwebui
EOF

# Verify file was created
ls -la docker-compose.dev.yml
cat docker-compose.dev.yml
```

---

## STEP 2: Generate Secure Passwords

```bash
# Generate PostgreSQL password
POSTGRES_PASS=$(openssl rand -base64 32)
echo "PostgreSQL Password: $POSTGRES_PASS"

# Generate JWT secret
JWT_SECRET=$(openssl rand -base64 64)
echo "JWT Secret: $JWT_SECRET"

# IMPORTANT: Copy these values! You'll need them in the next step.
```

---

## STEP 3: Configure .env File

```bash
# Backup existing .env
cp .env .env.backup

# Edit .env
nano .env
```

**Update these lines in .env:**

Find and replace:
```bash
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
```
With:
```bash
POSTGRES_PASSWORD=<paste-the-postgres-password-from-step-2>
```

Find and replace:
```bash
DATABASE_URL=postgresql+asyncpg://brain:CHANGE_ME_STRONG_PASSWORD@postgres:5432/brain
```
With:
```bash
DATABASE_URL=postgresql+asyncpg://brain:<paste-same-postgres-password>@postgres:5432/brain
```

Find and replace:
```bash
JWT_SECRET_KEY=CHANGE_ME_RANDOM_SECRET_KEY
```
With:
```bash
JWT_SECRET_KEY=<paste-the-jwt-secret-from-step-2>
```

**Also verify/update these settings:**
```bash
APP_ENV=development
BRAiN_MODE=development
API_PORT=8000
ENABLE_MISSION_WORKER=true
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=DEBUG
LOG_ENABLE_CONSOLE=true
```

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

---

## STEP 4: Verify Configuration

```bash
# Check that passwords are set (should NOT show CHANGE_ME)
grep -E "POSTGRES_PASSWORD|JWT_SECRET_KEY|DATABASE_URL" .env

# Verify no placeholders remain
grep "CHANGE_ME" .env
# Expected: No output

# Verify docker-compose.dev.yml exists
ls -la docker-compose.dev.yml
```

---

## STEP 5: Execute Deployment

```bash
# Make deploy.sh executable (if not already)
chmod +x deploy.sh

# Run deployment for dev environment
./deploy.sh dev
```

**What to expect:**
- Script will take 5-10 minutes (first build is slower)
- You'll see 8 steps:
  1. Preparing deployment directory
  2. Cloning/updating repository
  3. Setting up environment files
  4. Checking environment configuration
  5. Building Docker images ⏱️ (longest step, ~5-8 minutes)
  6. Running database migrations
  7. Starting services
  8. Post-deployment verification

**Watch for:**
- ✅ Green checkmarks = success
- ⚠️ Yellow warnings = non-critical (continue)
- ❌ Red errors = deployment failed (see troubleshooting below)

---

## STEP 6: Monitor Deployment

The script runs automatically. Watch the output for any errors.

**If deployment completes successfully, you'll see:**
```
========================================
Deployment Complete!
========================================

Environment: dev
Branch: v2 (<commit-hash>)
Path: /srv/dev

Services:
  Backend: http://localhost:8001
  Frontend: http://localhost:3001
  Domain: https://dev.brain.falklabs.de
```

---

## STEP 7: Verify Services

```bash
# Check all containers are running
docker ps

# Expected containers:
# - dev-backend
# - dev-control-deck
# - dev-postgres
# - dev-redis
# - dev-qdrant

# Test backend health
curl http://localhost:8001/api/health
# Expected: {"status":"healthy",...}

# Test frontend (should return HTML)
curl -I http://localhost:3001
# Expected: HTTP/1.1 200 OK
```

---

## STEP 8: View Logs (if needed)

```bash
# View all logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs

# View backend logs only
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs backend

# Follow logs in real-time
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

---

## TROUBLESHOOTING

### Error: "Missing environment variables"
```bash
# The script will tell you which variables are missing
# Edit .env and add them:
nano .env
# Then re-run: ./deploy.sh dev
```

### Error: "Port already in use"
```bash
# Find what's using the port
sudo netstat -tlnp | grep -E ":(8001|3001)"

# If old containers, stop them
docker ps -a
docker stop <container-id>
docker rm <container-id>

# Re-run deployment
./deploy.sh dev
```

### Error: Docker build fails
```bash
# Check Docker is installed
docker --version

# If not installed, install it:
sudo apt update
sudo apt install -y docker.io docker-compose

# Restart Docker
sudo systemctl restart docker

# Re-run deployment
./deploy.sh dev
```

### Error: Permission denied
```bash
# Add claude user to docker group
sudo usermod -aG docker claude

# Log out and log back in for group membership to take effect
exit
# Then SSH back in and try again
```

### Error: Backend health check fails
```bash
# Check backend logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs backend

# Common issues:
# - Database connection failed → verify POSTGRES_PASSWORD in .env
# - Redis connection failed → check redis container is running
# - Port conflict → check if port 8001 is already in use
```

### Error: Frontend build fails
```bash
# Check frontend logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs control_deck

# If TypeScript errors, rebuild with no cache
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache control_deck
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d control_deck
```

---

## QUICK COMMANDS REFERENCE

```bash
# Check service status
docker ps

# View logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Restart services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart

# Stop services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Check backend health
curl http://localhost:8001/api/health

# Check frontend
curl -I http://localhost:3001
```

---

## AFTER SUCCESSFUL DEPLOYMENT

Once deployment succeeds, these services will be accessible:

**From server (localhost):**
- Backend API: http://localhost:8001/api/health
- API Docs: http://localhost:8001/docs
- Frontend: http://localhost:3001
- AXE UI: http://localhost:3002

**From external (after nginx setup):**
- Frontend: https://dev.brain.falklabs.de
- Backend: https://dev.brain.falklabs.de/api/

**Next steps:**
1. Configure nginx for dev.brain.falklabs.de
2. Set up SSL with Let's Encrypt
3. Test external access

---

## READY TO START!

Execute the commands starting from STEP 1.

If you encounter any errors, refer to the TROUBLESHOOTING section above.

Good luck! 🚀
