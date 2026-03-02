# Constitutional Agents Framework - Deployment Guide

Complete guide for deploying the Constitutional Agents Framework to production.

**Version:** 1.0.0
**Last Updated:** 2023-12-20

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Step-by-Step Deployment](#step-by-step-deployment)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Services

| Service | Version | Purpose |
|---------|---------|---------|
| PostgreSQL | 15+ | Database with pgvector extension |
| Redis | 7+ | Mission queue and caching |
| Ollama | Latest | LLM service (or compatible) |
| Node.js | 18+ | Frontend build |
| Python | 3.11+ | Backend runtime |

### System Requirements

- **CPU:** 4+ cores recommended
- **RAM:** 8GB minimum, 16GB recommended
- **Disk:** 50GB minimum (for models and logs)
- **Network:** Stable internet for LLM model downloads

---

## Quick Start

For a complete automated deployment:

```bash
# Clone repository
git clone <repository-url>
cd BRAiN

# Run automated deployment
./deploy_production.sh production

# Start services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Step-by-Step Deployment

### Step 1: Database Setup

#### 1.1 Install PostgreSQL with pgvector

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql-15 postgresql-15-pgvector

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### 1.2 Create Database and User

```sql
-- As postgres user
sudo -u postgres psql

CREATE DATABASE brain_prod;
CREATE USER brain WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE brain_prod TO brain;

-- Enable pgvector extension
\c brain_prod
CREATE EXTENSION IF NOT EXISTS vector;

-- Exit
\q
```

#### 1.3 Run Alembic Migrations

```bash
cd backend

# Update DATABASE_URL in .env.prod
echo "DATABASE_URL=postgresql://brain:your_secure_password@localhost:5432/brain_prod" >> .env.prod

# Run migrations
alembic upgrade head

# Verify
alembic current
# Should show: 002_audit_trail_schema (head)
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Running upgrade 001_initial_schema -> 002_audit_trail_schema
INFO  [alembic.runtime.migration] Running upgrade 002_audit_trail_schema -> head
```

**Verify Tables Created:**
```sql
psql -U brain -d brain_prod -c "\dt"

# Should show:
# supervision_audit
# human_oversight_approvals
# agent_actions_log
# policy_evaluation_log
# compliance_reports
```

---

### Step 2: Load Example Policies

Load pre-configured DSGVO and EU AI Act compliance policies:

```bash
# Load all policies
python3 scripts/load_example_policies.py

# Or load specific category
python3 scripts/load_example_policies.py --category privacy

# Or load compliance framework
python3 scripts/load_example_policies.py --compliance DSGVO
```

**Expected Output:**
```
======================================================================
Loading Example Policies into Policy Engine
======================================================================

Loading all example policies

✓ Loaded: [300] Social Scoring - Prohibited Practice (deny)
✓ Loaded: [300] Subliminal Manipulation - Prohibited (deny)
✓ Loaded: [250] Personal Data Processing - Consent Required (deny)
...

======================================================================
✓ Successfully loaded 12 policies
======================================================================

Policies by category:
  privacy: 3
  prohibited_practice: 2
  deployment: 2
  security: 2
  ...

Total policies in system: 12
```

**Verify Policies Loaded:**
```python
from backend.app.modules.policy.service import PolicyService

service = PolicyService()
policies = service.get_all_policies()
print(f"Loaded {len(policies)} policies")
```

---

### Step 3: LLM Configuration

#### 3.1 Install and Start Ollama

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Start service
systemctl start ollama
systemctl enable ollama

# Verify
systemctl status ollama
```

#### 3.2 Pull Required Models

```bash
# Pull Llama 3.2 (recommended)
ollama pull llama3.2:latest

# Or alternative models
ollama pull mistral:latest
ollama pull codellama:latest

# Verify
ollama list
```

**Expected Output:**
```
NAME                ID              SIZE    MODIFIED
llama3.2:latest     a1b2c3d4e5f6    4.9 GB  2 hours ago
```

#### 3.3 Configure Backend

```bash
# Update .env.prod
cat >> .env.prod <<EOF
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
EOF
```

#### 3.4 Test LLM Connection

```bash
curl http://localhost:11434/api/tags

# Should return JSON with available models
```

---

### Step 4: Start Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Start with Uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Or with Gunicorn (production)
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Verify Backend Running:**
```bash
curl http://localhost:8000/api/health

# Expected response:
# {"status": "ok", "version": "0.5.0"}
```

---

### Step 5: Start Frontend

```bash
cd frontend/brain_control_ui

# Install dependencies
npm install --legacy-peer-deps

# Build for production
npm run build

# Start production server
npm run start
```

**Verify Frontend Running:**
```bash
curl http://localhost:3000

# Should return HTML
```

---

### Step 6: Verify Deployment

Run the comprehensive verification script:

```bash
./scripts/verify_deployment.sh
```

**Manual Verification Checklist:**

#### Backend Health Checks

```bash
# 1. General health
curl http://localhost:8000/api/health

# 2. Agent ops info
curl http://localhost:8000/api/agent-ops/info

# 3. Supervisor metrics
curl http://localhost:8000/api/agent-ops/supervisor/metrics

# 4. Test supervision request
curl -X POST http://localhost:8000/api/agent-ops/supervisor/supervise \
  -H "Content-Type: application/json" \
  -d '{
    "requesting_agent": "TestAgent",
    "action": "test_action",
    "context": {},
    "risk_level": "low"
  }'
```

#### Database Verification

```sql
-- Check audit trail is working
SELECT COUNT(*) FROM supervision_audit;

-- Check policies loaded
SELECT COUNT(*) FROM policy_evaluation_log;

-- Verify most recent supervision
SELECT audit_id, requesting_agent, action, approved, timestamp
FROM supervision_audit
ORDER BY timestamp DESC
LIMIT 5;
```

#### Frontend Verification

1. Navigate to http://localhost:3000
2. Navigate to http://localhost:3000/constitutional
3. Test SupervisorDashboard - Submit test request
4. Verify metrics update
5. Check all 5 agent tabs load correctly

---

## Configuration

### Environment Variables

#### Backend (.env.prod)

```bash
# Application
ENVIRONMENT=production
VERSION=0.5.0
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000
UVICORN_WORKERS=4

# Database
DATABASE_URL=postgresql://brain:PASSWORD@localhost:5432/brain_prod
REDIS_URL=redis://localhost:6379/0

# LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Supervisor
SUPERVISOR_HEARTBEAT_INTERVAL=10
SUPERVISOR_AGENT_TIMEOUT=30

# Mission System
MISSION_WORKER_POLL_INTERVAL=2.0
MISSION_DEFAULT_MAX_RETRIES=3

# Security
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
CORS_ORIGINS=["https://brain.yourdomain.com"]

# Constitutional Agents
ENABLE_HITL=true
HITL_TIMEOUT=3600  # 1 hour
AUDIT_RETENTION_DAYS=365
```

#### Frontend (.env.production)

```bash
NEXT_PUBLIC_BRAIN_API_BASE=https://api.brain.yourdomain.com
NEXT_PUBLIC_ENVIRONMENT=production
NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

### Policy Configuration

Edit policies in `backend/app/modules/policy/example_policies.py` or create custom policies:

```python
from backend.app.modules.policy.schemas import PolicyRule, PolicyEffect

CUSTOM_POLICY = PolicyRule(
    id="custom-policy-1",
    name="My Custom Policy",
    description="Custom business rule",
    effect=PolicyEffect.DENY,
    priority=200,
    conditions={
        "action": {"==": "custom_action"},
        "context.environment": {"==": "production"}
    },
    enabled=True
)
```

---

## Monitoring

### Step 1: Access Audit Trail Dashboard

Navigate to: http://localhost:3000/audit

**Features:**
- Real-time supervision audit trail
- Policy violations tracking
- Human-in-the-Loop queue
- Analytics and metrics

### Step 2: Database Monitoring Queries

```sql
-- Supervision requests per hour
SELECT
  date_trunc('hour', timestamp) AS hour,
  COUNT(*) AS requests,
  SUM(CASE WHEN approved THEN 1 ELSE 0 END) AS approved,
  SUM(CASE WHEN human_oversight_required THEN 1 ELSE 0 END) AS hitl_required
FROM supervision_audit
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;

-- Policy violations summary
SELECT
  matched_rule_id,
  COUNT(*) AS violation_count,
  MAX(timestamp) AS last_seen
FROM policy_evaluation_log
WHERE effect = 'deny'
GROUP BY matched_rule_id
ORDER BY violation_count DESC
LIMIT 10;

-- Pending HITL approvals
SELECT
  token,
  requesting_agent,
  action,
  created_at,
  expires_at
FROM human_oversight_approvals
WHERE status = 'pending'
AND expires_at > NOW()
ORDER BY created_at;
```

### Step 3: Grafana Integration (Optional)

See `docs/GRAFANA_SETUP.md` for comprehensive Grafana dashboard configuration.

### Step 4: Alerting

Configure alerts for:
- Pending HITL > 10 requests
- Policy violations spike
- Low approval rate (<80%)
- High processing time (>5s)

---

## Troubleshooting

### Issue: Alembic Migration Fails

**Error:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution:**
```bash
# Check PostgreSQL is running
systemctl status postgresql

# Verify DATABASE_URL
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### Issue: LLM Not Responding

**Error:**
```
httpx.ConnectError: All connection attempts failed
```

**Solution:**
```bash
# Check Ollama is running
systemctl status ollama

# Test Ollama API
curl http://localhost:11434/api/tags

# Check model is pulled
ollama list

# Restart Ollama
systemctl restart ollama
```

### Issue: Frontend Build Fails

**Error:**
```
Module not found: Can't resolve '@/components/ui/...'
```

**Solution:**
```bash
cd frontend/brain_control_ui

# Clear cache
rm -rf .next node_modules

# Reinstall with legacy peer deps
npm install --legacy-peer-deps

# Rebuild
npm run build
```

### Issue: Supervision Requests Fail

**Error:**
```
{"detail": "Policy Engine not available"}
```

**Solution:**
```bash
# Verify policies are loaded
python3 scripts/load_example_policies.py

# Check policy service
python3 -c "from backend.app.modules.policy.service import PolicyService; print(len(PolicyService().get_all_policies()))"

# Should output: 12 (or number of loaded policies)
```

---

## Rollback Procedure

If deployment fails, rollback using:

```bash
# 1. Rollback database migration
cd backend
alembic downgrade -1

# 2. Stop services
docker-compose down

# 3. Restore from backup
psql -U brain brain_prod < backup.sql

# 4. Restart previous version
git checkout <previous-commit>
docker-compose up -d
```

---

## Next Steps

After successful deployment:

1. **Run Integration Tests:** `./scripts/run_integration_tests.sh --coverage`
2. **Configure Monitoring:** Set up Grafana dashboards
3. **Set Up Backups:** Configure automated database backups
4. **Security Hardening:** Review security checklist
5. **Load Testing:** Run performance tests under load

---

## Support

For issues or questions:
- **Documentation:** `docs/CONSTITUTIONAL_AGENTS.md`
- **Integration Tests:** `backend/tests/integration/README.md`
- **API Reference:** `CLAUDE.md` - Constitutional Agents API section

---

**Deployment Complete!** 🎉

The Constitutional Agents Framework is now running in production with:
- ✅ DSGVO compliance
- ✅ EU AI Act compliance
- ✅ Risk-based supervision
- ✅ Human-in-the-loop workflows
- ✅ Comprehensive audit trail
