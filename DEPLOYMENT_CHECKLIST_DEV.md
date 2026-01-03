# Development Environment Deployment Checklist

**Server:** brain.falklabs.de
**User:** claude
**Path:** /srv/dev/
**Branch:** v2
**Environment:** development

---

## Pre-Deployment Verification

Execute these commands on the server via PuTTY:

```bash
# Verify you're in the correct directory
pwd
# Expected: /srv/dev

# Verify you're on the correct branch
git branch
# Expected: * v2

# Verify deploy.sh is executable
ls -la deploy.sh
# Expected: -rwxrwxr-x ... deploy.sh
```

---

## Step 1: Configure Environment Variables

The .env file needs secure passwords and proper configuration.

### Generate Secure Passwords

```bash
# Generate PostgreSQL password (copy the output)
openssl rand -base64 32

# Generate JWT secret key (copy the output)
openssl rand -base64 64
```

### Edit .env File

```bash
nano .env
```

**Update these critical variables:**

```bash
# Replace with your generated PostgreSQL password
POSTGRES_PASSWORD=<paste-postgres-password-here>

# Update database URL with same password
DATABASE_URL=postgresql+asyncpg://brain:<paste-postgres-password-here>@postgres:5432/brain

# Replace with your generated JWT secret
JWT_SECRET_KEY=<paste-jwt-secret-here>

# Ensure these are set correctly for development
APP_ENV=development
BRAiN_MODE=development
API_PORT=8000
NEXT_PUBLIC_API_BASE=http://localhost:8000

# Enable mission worker
ENABLE_MISSION_WORKER=true

# Redis (should be correct by default)
REDIS_URL=redis://redis:6379/0

# Logging for development
LOG_LEVEL=DEBUG
LOG_ENABLE_CONSOLE=true
```

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

### Verify .env Configuration

```bash
# Check that critical variables are set (should NOT show CHANGE_ME)
grep -E "POSTGRES_PASSWORD|JWT_SECRET_KEY|DATABASE_URL" .env

# Verify no placeholder passwords remain
grep -E "CHANGE_ME" .env
# Expected: No output (if output appears, you need to replace those values)
```

---

## Step 2: Execute Deployment

```bash
# Run the deployment script for dev environment
./deploy.sh dev
```

**What this script does:**
1. ✅ Verifies environment is 'dev'
2. ✅ Updates repository from v2 branch
3. ✅ Checks environment configuration
4. ✅ Builds Docker images (5-10 minutes)
5. ✅ Runs database migrations
6. ✅ Starts all services (backend, frontend, postgres, redis, qdrant)
7. ✅ Runs health checks
8. ✅ Displays service URLs

**Expected duration:** 5-10 minutes (first build takes longer)

---

## Step 3: Monitor Deployment Progress

The script will show progress for each step. Watch for:

- ✅ Green checkmarks = success
- ⚠️ Yellow warnings = non-critical issues
- ❌ Red errors = deployment failed

If deployment fails, check the error message and see Troubleshooting section below.

---

## Step 4: Verify Services

After deployment completes, verify all services are running:

```bash
# Check running containers
docker ps

# Expected output should show these containers:
# - brain-backend (or dev-backend)
# - brain-control-deck (or dev-control_deck)
# - brain-postgres
# - brain-redis
# - brain-qdrant
```

### Test Backend Health

```bash
# Test backend API
curl http://localhost:8001/api/health

# Expected response:
# {"status":"healthy","timestamp":...}
```

### Test Frontend

```bash
# Test frontend (should return HTML)
curl -I http://localhost:3001

# Expected: HTTP/1.1 200 OK
```

---

## Step 5: Check Logs (if needed)

If services aren't responding, check logs:

```bash
# View all logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs

# View backend logs only
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs backend

# View frontend logs only
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs control_deck

# Follow logs in real-time
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

---

## Step 6: Access Services

Once deployment is successful:

### Local Access (from server)
- **Backend API:** http://localhost:8001/api/health
- **Frontend:** http://localhost:3001
- **API Docs:** http://localhost:8001/docs

### External Access (after nginx configuration)
- **Frontend:** https://dev.brain.falklabs.de
- **Backend API:** https://dev.brain.falklabs.de/api/

---

## Troubleshooting

### Issue: "Missing environment variables"

**Solution:**
```bash
nano .env
# Add the missing variables shown in the error message
# Save and re-run: ./deploy.sh dev
```

### Issue: "Port already in use"

**Solution:**
```bash
# Check what's using the port
sudo netstat -tlnp | grep -E ":(8001|3001)"

# Stop old containers
docker ps -a
docker stop <container-id>
docker rm <container-id>

# Re-run deployment
./deploy.sh dev
```

### Issue: Docker build fails

**Solution:**
```bash
# Clean up Docker cache
docker system prune -a

# Rebuild with no cache
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache

# Restart deployment
./deploy.sh dev
```

### Issue: Database connection failed

**Solution:**
```bash
# Check if PostgreSQL container is running
docker ps | grep postgres

# Check PostgreSQL logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs postgres

# Verify POSTGRES_PASSWORD matches in .env
grep POSTGRES_PASSWORD .env
```

### Issue: Frontend build errors

**Solution:**
```bash
# Check frontend logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs control_deck

# If TypeScript errors, rebuild frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache control_deck
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d control_deck
```

---

## Restart Services

If you need to restart services after deployment:

```bash
# Restart all services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart

# Restart specific service
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart control_deck
```

---

## Stop Services

To stop all services:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# To also remove volumes (⚠️ deletes database data!)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

---

## Next Steps After Successful Deployment

1. ✅ Configure nginx for dev.brain.falklabs.de (see INFRASTRUCTURE_SETUP.md)
2. ✅ Set up SSL certificate with Let's Encrypt
3. ✅ Configure GitHub Actions secrets (DEPLOY_SSH_KEY)
4. ✅ Create main and dev branches from v2
5. ✅ Set up branch protection rules

---

## Quick Reference

```bash
# Deploy
./deploy.sh dev

# Check status
docker ps

# View logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Restart
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart

# Stop
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Health check
curl http://localhost:8001/api/health
```

---

## Environment Ports

| Service | Port | URL |
|---------|------|-----|
| Backend | 8001 | http://localhost:8001 |
| Frontend | 3001 | http://localhost:3001 |
| PostgreSQL | 5432 | postgres://localhost:5432 |
| Redis | 6379 | redis://localhost:6379 |
| Qdrant | 6333 | http://localhost:6333 |

---

**Ready to deploy!** Start with Step 1 above.
