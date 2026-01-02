# Backend v3 Deployment Guide

Quick guide for deploying the BRAiN backend v3 with Events CRUD system.

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL container running
- Redis container running
- Network: `dev_brain_internal` (or update DEPLOY_V3.sh)

## Quick Deployment (Automated)

### Option 1: Local Development

```bash
# Pull latest code
cd /srv/dev  # or your deployment directory
git pull origin claude/infrastructure-setup-complete-h1NXi

# Run deployment script
cd backend
bash DEPLOY_V3.sh
```

The script will:
1. Stop old backend container
2. Build new Docker image (v3)
3. Run database migrations
4. Start backend container
5. Run comprehensive tests
6. Display test results

### Option 2: Manual Deployment

```bash
# 1. Navigate to backend directory
cd /srv/dev/backend

# 2. Build Docker image
docker build -f Dockerfile.minimal.v3 -t dev_backend_minimal:v3 .

# 3. Run migrations (before starting app!)
docker run --rm \
  --network dev_brain_internal \
  -e DATABASE_URL="postgresql://brain:brain@dev-postgres:5432/brain_dev" \
  dev_backend_minimal:v3 \
  alembic upgrade head

# 4. Start backend container
docker run -d \
  --name dev_backend_minimal \
  --network dev_brain_internal \
  -p 8001:8000 \
  -e DATABASE_URL="postgresql://brain:brain@dev-postgres:5432/brain_dev" \
  -e REDIS_URL="redis://dev-redis:6379/0" \
  dev_backend_minimal:v3

# 5. Check logs
docker logs -f dev_backend_minimal
```

## Verification

### Check Backend Health

```bash
# Basic health check
curl http://localhost:8001/api/health

# Database health check
curl http://localhost:8001/api/db/health

# Events stats (should work even if empty)
curl http://localhost:8001/api/events/stats
```

### Run Test Suite

**pytest (requires Python environment):**
```bash
cd backend
pytest tests/test_system_events_api.py -v
```

**Curl smoke test (works anywhere):**
```bash
cd backend/tests
./test_system_events_curl.sh http://localhost:8001
```

**External HTTPS test (if nginx configured):**
```bash
./test_system_events_curl.sh https://dev.brain.falklabs.de
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs dev_backend_minimal

# Common issues:
# 1. Import errors - ensure no 'backend.' prefix in imports
# 2. Database connection - check PostgreSQL is running
# 3. Redis connection - check Redis is running
# 4. Port conflict - check if port 8001 is already in use
```

### Migration errors

```bash
# Check current migration version
docker exec dev_backend_minimal alembic current

# View migration history
docker exec dev_backend_minimal alembic history

# If needed, reset migrations (CAUTION: drops data!)
docker exec dev-postgres psql -U postgres -d brain_dev -c "DROP TABLE IF EXISTS alembic_version;"
docker exec dev-postgres psql -U postgres -d brain_dev -c "DROP TABLE IF EXISTS system_events;"

# Then run migrations again
docker run --rm \
  --network dev_brain_internal \
  -e DATABASE_URL="postgresql://brain:brain@dev-postgres:5432/brain_dev" \
  dev_backend_minimal:v3 \
  alembic upgrade head
```

### Database connection issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test database connection
docker exec dev-postgres psql -U postgres -d brain_dev -c "SELECT 1;"

# Check backend can reach database
docker exec dev_backend_minimal pg_isready -h dev-postgres -p 5432
```

### Redis connection issues

```bash
# Check Redis is running
docker ps | grep redis

# Test Redis connection
docker exec dev-redis redis-cli ping

# Check backend can reach Redis
docker exec dev_backend_minimal sh -c "echo 'PING' | nc dev-redis 6379"
```

## Environment Variables

Required environment variables (adjust for your setup):

```bash
# Database
DATABASE_URL="postgresql://brain:brain@dev-postgres:5432/brain_dev"

# Redis
REDIS_URL="redis://dev-redis:6379/0"

# Optional
LOG_LEVEL="INFO"
ENVIRONMENT="development"
```

## API Endpoints

Once deployed, these endpoints are available:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Basic health check |
| GET | `/api/db/health` | Database health check |
| POST | `/api/events` | Create event |
| GET | `/api/events` | List events (with filters) |
| GET | `/api/events/{id}` | Get event by ID |
| PUT | `/api/events/{id}` | Update event |
| DELETE | `/api/events/{id}` | Delete event |
| GET | `/api/events/stats` | Event statistics |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc UI |

## Docker Network Setup

If you need to create the network:

```bash
# Create network
docker network create dev_brain_internal

# Connect PostgreSQL
docker network connect dev_brain_internal dev-postgres

# Connect Redis
docker network connect dev_brain_internal dev-redis
```

## Nginx Configuration (Optional)

If using nginx reverse proxy:

```nginx
# /etc/nginx/conf.d/dev.brain.conf
upstream dev_backend {
    server localhost:8001;
}

server {
    listen 80;
    server_name dev.brain.falklabs.de;

    location /api/ {
        proxy_pass http://dev_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://dev_backend;
    }

    location /redoc {
        proxy_pass http://dev_backend;
    }
}
```

Then:
```bash
nginx -t
systemctl reload nginx
```

## Monitoring

### View logs

```bash
# Follow logs
docker logs -f dev_backend_minimal

# Last 100 lines
docker logs --tail 100 dev_backend_minimal

# With timestamps
docker logs -f --timestamps dev_backend_minimal
```

### Check database

```bash
# Connect to database
docker exec -it dev-postgres psql -U postgres -d brain_dev

# Count events
docker exec dev-postgres psql -U postgres -d brain_dev -c "SELECT COUNT(*) FROM system_events;"

# View recent events
docker exec dev-postgres psql -U postgres -d brain_dev -c "SELECT id, event_type, severity, message, timestamp FROM system_events ORDER BY timestamp DESC LIMIT 10;"
```

### Check Redis cache

```bash
# Connect to Redis
docker exec -it dev-redis redis-cli

# List all keys
KEYS *

# View cached event
GET events:id:1

# View cached stats
GET events:stats
```

## Performance Notes

- Events are cached for 5 minutes
- Stats are cached for 30 seconds
- Database uses connection pooling (2-10 connections)
- JSONB indexing for fast queries
- Indexes on event_type, severity, timestamp

## Cleanup

### Remove old containers

```bash
# Stop and remove backend
docker stop dev_backend_minimal
docker rm dev_backend_minimal

# Remove old images
docker images | grep dev_backend_minimal
docker rmi dev_backend_minimal:v2
```

### Clean database (CAUTION!)

```bash
# Drop events table
docker exec dev-postgres psql -U postgres -d brain_dev -c "DROP TABLE IF EXISTS system_events CASCADE;"

# Clear Redis cache
docker exec dev-redis redis-cli FLUSHDB
```

## Support

For issues or questions:
1. Check logs: `docker logs dev_backend_minimal`
2. Review PHASE2_COMPLETE.md for troubleshooting
3. Run smoke test: `./tests/test_system_events_curl.sh`
4. Check GitHub issues

## Version Info

- **Backend:** v3 (minimal with Events CRUD)
- **Migration:** 001_create_system_events
- **Python:** 3.11
- **FastAPI:** Latest
- **PostgreSQL:** 15+ (with JSONB support)
- **Redis:** 7+
