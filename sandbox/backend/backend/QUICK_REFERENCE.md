# Backend v3 Quick Reference

Quick commands for deploying and testing the System Events API.

## 🚀 Deployment (One Command)

```bash
cd /srv/dev/backend && bash DEPLOY_V3.sh
```

## 🧪 Testing

### Smoke Test (Recommended)
```bash
cd /srv/dev/backend/tests
./test_system_events_curl.sh http://localhost:8001
./test_system_events_curl.sh https://dev.brain.falklabs.de
```

### pytest (Full Suite)
```bash
cd /srv/dev/backend
pytest tests/test_system_events_api.py -v
```

## 📡 Health Checks

```bash
# Basic health
curl http://localhost:8001/api/health

# Database health
curl http://localhost:8001/api/db/health

# Events stats
curl http://localhost:8001/api/events/stats | jq .
```

## 📝 Create Test Event

```bash
curl -X POST http://localhost:8001/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "test",
    "severity": "info",
    "message": "Test event from command line"
  }' | jq .
```

## 📊 Query Events

```bash
# List recent events
curl http://localhost:8001/api/events?limit=10 | jq .

# Filter by type
curl http://localhost:8001/api/events?event_type=health_check | jq .

# Filter by severity
curl http://localhost:8001/api/events?severity=error | jq .

# Get statistics
curl http://localhost:8001/api/events/stats | jq .
```

## 🔍 Monitoring

```bash
# Follow logs
docker logs -f dev_backend_minimal

# Check database
docker exec dev-postgres psql -U postgres -d brain_dev -c \
  "SELECT COUNT(*) FROM system_events;"

# Check Redis cache
docker exec dev-redis redis-cli KEYS "events:*"
```

## 🛠️ Troubleshooting

```bash
# Container status
docker ps | grep dev_backend_minimal

# Recent logs
docker logs --tail 50 dev_backend_minimal

# Migration status
docker exec dev_backend_minimal alembic current

# Database connection test
docker exec dev-postgres psql -U postgres -d brain_dev -c "SELECT 1;"

# Redis connection test
docker exec dev-redis redis-cli ping
```

## 🔄 Restart Backend

```bash
docker restart dev_backend_minimal
docker logs -f dev_backend_minimal
```

## 🧹 Cleanup (CAUTION!)

```bash
# Remove container
docker stop dev_backend_minimal && docker rm dev_backend_minimal

# Clear events (database)
docker exec dev-postgres psql -U postgres -d brain_dev -c \
  "DELETE FROM system_events;"

# Clear cache (Redis)
docker exec dev-redis redis-cli FLUSHDB
```

## 📚 Documentation

- **Full Deployment Guide:** `backend/DEPLOY_GUIDE.md`
- **Phase 2 Summary:** `backend/PHASE2_COMPLETE.md`
- **Implementation Plan:** `backend/PHASE2_PLAN.md`
- **API Docs:** http://localhost:8001/docs

## 🌐 Production URLs

- **API Base:** https://dev.brain.falklabs.de/api
- **Health:** https://dev.brain.falklabs.de/api/health
- **Events:** https://dev.brain.falklabs.de/api/events
- **Stats:** https://dev.brain.falklabs.de/api/events/stats
- **Docs:** https://dev.brain.falklabs.de/docs
