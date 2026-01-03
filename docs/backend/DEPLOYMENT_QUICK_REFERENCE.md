# Phase 2 Deployment - Quick Reference Card

**Server:** brain.falklabs.de | **Environment:** Development | **Backend Port:** 8001

---

## Quick Access Commands

### SSH to Server
```bash
ssh root@brain.falklabs.de
```

### Navigate to Project
```bash
cd /srv/dev
```

### Check Service Status
```bash
docker compose ps
docker compose logs -f backend
```

### Run Smoke Test
```bash
cd /srv/dev/backend/tests
./test_system_events_curl.sh http://localhost:8001
```

---

## API Endpoints (Local)

### Health Checks
```bash
curl http://localhost:8001/health
curl http://localhost:8001/api/health/database
```

### Events Statistics
```bash
curl http://localhost:8001/api/events/stats
```

### Create Event
```bash
curl -X POST http://localhost:8001/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "test",
    "severity": "info",
    "message": "Test event",
    "source": "cli",
    "details": {}
  }'
```

### List Events
```bash
curl "http://localhost:8001/api/events?limit=10"
```

### Get Event by ID
```bash
curl http://localhost:8001/api/events/1
```

### Update Event
```bash
curl -X PUT http://localhost:8001/api/events/1 \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Updated message",
    "severity": "warning"
  }'
```

### Delete Event
```bash
curl -X DELETE http://localhost:8001/api/events/1
```

---

## API Endpoints (HTTPS)

Replace `http://localhost:8001` with `https://dev.brain.falklabs.de`

```bash
curl https://dev.brain.falklabs.de/health
curl https://dev.brain.falklabs.de/api/events/stats
```

---

## Database Access

### Connect to PostgreSQL
```bash
docker exec -it dev-postgres psql -U postgres -d brain_dev
```

### View Events Table
```sql
SELECT * FROM system_events ORDER BY created_at DESC LIMIT 10;
SELECT COUNT(*) FROM system_events;
SELECT severity, COUNT(*) FROM system_events GROUP BY severity;
```

### Check Migration Status
```sql
SELECT * FROM alembic_version;
```

---

## Docker Management

### Restart Backend
```bash
docker compose restart backend
```

### View Logs
```bash
docker compose logs -f backend
docker compose logs backend --tail 50
```

### Rebuild Container
```bash
docker compose build backend
docker compose up -d backend
```

### Stop All Services
```bash
docker compose down
```

### Start All Services
```bash
docker compose up -d
```

---

## Git Operations

### Check Current Branch
```bash
git branch
git status
```

### Pull Latest Changes
```bash
git pull origin claude/infrastructure-setup-complete-h1NXi
```

### View Recent Commits
```bash
git log --oneline -10
```

---

## Troubleshooting Commands

### Reset Database
```bash
docker exec dev-postgres psql -U postgres -d brain_dev \
  -c "DROP TABLE IF EXISTS system_events CASCADE;"
docker exec dev-postgres psql -U postgres -d brain_dev \
  -c "DROP TABLE IF EXISTS alembic_version CASCADE;"
docker compose restart backend
```

### Check Container Health
```bash
docker inspect dev-backend | grep -A 10 Health
```

### View Container Resource Usage
```bash
docker stats dev-backend --no-stream
```

### Clear Redis Cache
```bash
docker exec -it dev-redis redis-cli FLUSHALL
```

---

## File Locations

| Component | Path |
|-----------|------|
| Backend Code | `/srv/dev/backend/` |
| API Routes | `/srv/dev/backend/api/routes/` |
| Main App | `/srv/dev/backend/main.py` |
| Events Service | `/srv/dev/backend/app/services/events_service.py` |
| Migrations | `/srv/dev/backend/alembic/versions/` |
| Tests | `/srv/dev/backend/tests/` |
| Environment | `/srv/dev/.env.dev` |
| Docker Compose | `/srv/dev/docker-compose.yml` |
| Nginx Config | `/etc/nginx/conf.d/dev.brain.conf` |

---

## URLs

| Service | URL |
|---------|-----|
| Backend API | https://dev.brain.falklabs.de |
| API Docs | https://dev.brain.falklabs.de/docs |
| Health Check | https://dev.brain.falklabs.de/health |
| Frontend | https://dev.brain.falklabs.de (port 3001) |

---

## Common Issues & Quick Fixes

### Import Errors
```bash
# Fix: Remove backend. prefix from imports
find /srv/dev/backend/api/ -name "*.py" -exec sed -i 's/from backend\./from /g' {} \;
docker compose restart backend
```

### Migration Conflicts
```bash
# Fix: Reset migrations
cd /srv/dev/backend
rm -f alembic/versions/00{2,3,4,5}_*.py
docker compose restart backend
```

### Container Won't Start
```bash
# Fix: Check logs and rebuild
docker compose logs backend --tail 100
docker compose build --no-cache backend
docker compose up -d backend
```

---

## Monitoring

### Real-time Logs
```bash
# Backend only
docker compose logs -f backend

# All services
docker compose logs -f

# Filter for errors
docker compose logs backend | grep -i error
```

### Database Activity
```bash
docker exec dev-postgres psql -U postgres -d brain_dev \
  -c "SELECT * FROM pg_stat_activity WHERE datname='brain_dev';"
```

### Redis Stats
```bash
docker exec dev-redis redis-cli INFO stats
docker exec dev-redis redis-cli DBSIZE
```

---

## Emergency Procedures

### Full System Restart
```bash
cd /srv/dev
docker compose down
docker compose up -d
docker compose logs -f
```

### Rollback Deployment
```bash
cd /srv/dev
git log --oneline -5  # Find previous commit
git checkout <previous-commit-hash>
docker compose build backend
docker compose up -d backend
```

### Backup Database
```bash
docker exec dev-postgres pg_dump -U postgres brain_dev > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Database
```bash
docker exec -i dev-postgres psql -U postgres brain_dev < backup_YYYYMMDD_HHMMSS.sql
```

---

**Last Updated:** 2026-01-03
**Status:** ✅ Deployment Complete
