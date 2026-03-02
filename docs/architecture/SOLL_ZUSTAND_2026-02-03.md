# BRAiN v2 - SOLL-Zustand (Target State)
**Datum:** 2026-02-03
**Version:** 2.0 SOLL
**Basis:** IST_ZUSTAND_2026-02-03.md
**Ziel:** Production-Ready Enterprise AI Orchestration Platform

---

## Executive Summary

**Vision:** BRAiN v2 wird zu einer **100% produktionsreifen, enterprise-grade AI Orchestration Platform** mit:
- ✅ **High Availability** (99.99% uptime)
- ✅ **Horizontal Scalability** (10K+ concurrent missions)
- ✅ **Zero Critical Security Gaps** (Secrets Management, WAF, HA)
- ✅ **Full Test Coverage** (Backend + Frontend)
- ✅ **Modular Runtime Profiles** (minimal, standard, full, enterprise)
- ✅ **Phase 2 Enforcement** (Budget, Timeout, Reflex aktiv)
- ✅ **SOC 2 / ISO 27001 Ready** (Compliance Framework)

**Timeline:** 6 Monate (24 Wochen)
- **Phase A:** Stabilization (Wochen 1-4)
- **Phase B:** Automation (Wochen 5-12)
- **Phase C:** Enterprise (Wochen 13-24)

---

## 1. Strategische Entscheidungen

### 1.1 Mini-Brain vs. Modular Profiles

**ENTSCHEIDUNG: Modular Runtime Profiles** ✅

**Begründung:**
- Single Codebase = niedrigere Wartungskosten
- Feature Parity garantiert
- Klarer Upgrade-Pfad (Profil-Switch via .env)
- Markt-Positionierung: "Ein BRAiN, vier Profile"

**Profile:**

| Profil | Module | Governance | Datenbank | Use Case |
|--------|--------|------------|-----------|----------|
| **minimal** | missions, agents, llm_client | ❌ | SQLite | Edge/Dev/CI |
| **standard** | missions, agents, policy, neurorail, metrics | ✅ Phase 1 | PostgreSQL | Production (SMB) |
| **full** | Alle 46 Module | ✅ Phase 2 | PostgreSQL + Replication | Production (Enterprise) |
| **enterprise** | Alle 46 Module | ✅ Phase 2 + Compliance | PostgreSQL Cluster | Enterprise + Multi-Tenant |

**Implementation:**
```python
# .env
BRAIN_RUNTIME_PROFILE=standard  # minimal | standard | full | enterprise

# app/core/profiles.py
class ProfileConfig(BaseModel):
    name: str
    modules: List[str]
    governance_enabled: bool
    neurorail_phase: int  # 0, 1, 2
    database_type: str
    redis_required: bool
    multi_tenancy: bool
```

---

### 1.2 Mission System Konsolidierung

**ENTSCHEIDUNG: Legacy beibehalten, App-Version entfernen** ✅

**Begründung:**
- Legacy ist funktional + EventStream-integriert
- App-Version ist absichtlich deaktiviert (orphaned missions)
- Konsolidierung reduziert Code-Duplikation
- Einfachere Wartung

**Aktion:**
```bash
# Woche 2
rm -rf backend/app/modules/missions/
# Remove disabled router include in main.py
# Update CLAUDE.md to reflect single mission system
```

**Alternative (Future):**
- Wenn App-Version benötigt wird: Worker-Integration hinzufügen
- ADR dokumentieren: Warum App-Version reaktiviert wurde

---

### 1.3 Phase 2 Enforcement Rollout

**ENTSCHEIDUNG: Canary Deployment (10% → 50% → 100%)** ✅

**Begründung:**
- Risiko-Minimierung (Breaking Changes möglich)
- Observability (Metriken vor Vollausbau)
- Rollback-Option bei Problemen

**Rollout-Plan:**

**Woche 9-10: Canary 10%**
```python
# app/core/config.py
NEURORAIL_ENFORCEMENT_ENABLED = True
NEURORAIL_ENFORCEMENT_PERCENTAGE = 10  # 10% of missions

# Phase 2 Features
NEURORAIL_ENABLE_TIMEOUT_ENFORCEMENT = True
NEURORAIL_ENABLE_BUDGET_ENFORCEMENT = False  # Week 11
NEURORAIL_ENABLE_REFLEX_SYSTEM = False  # Week 12
```

**Metriken beobachten:**
- `neurorail_attempts_failed_total{error_code="NR-E001"}` (Timeout)
- `neurorail_budget_violations_total` (Budget)
- `neurorail_reflex_actions_total` (Reflex)

**Woche 11: Canary 50%**
```python
NEURORAIL_ENFORCEMENT_PERCENTAGE = 50
NEURORAIL_ENABLE_BUDGET_ENFORCEMENT = True  # Aktivieren
```

**Woche 12: Full Rollout 100%**
```python
NEURORAIL_ENFORCEMENT_PERCENTAGE = 100
NEURORAIL_ENABLE_REFLEX_SYSTEM = True  # Aktivieren
```

**Rollback-Strategie:**
- Bei >5% Error Rate: Rollback auf vorherige Percentage
- Feature Flags per Environment Variable steuerbar

---

### 1.4 PostgreSQL High Availability

**ENTSCHEIDUNG: Streaming Replication (Master-Slave)** ✅

**Begründung:**
- Einfacher als Multi-Master (Patroni)
- Günstiger als Managed Service (AWS RDS Multi-AZ)
- Ausreichend für 99.99% uptime

**Architektur:**
```
┌─────────────┐     Streaming      ┌─────────────┐
│  Primary    │ ────Replication──> │  Standby    │
│ PostgreSQL  │                     │ PostgreSQL  │
│ (Read/Write)│                     │ (Read-Only) │
└─────────────┘                     └─────────────┘
       │                                   │
       │                                   │
       └────────── Failover (pgpool) ─────┘
```

**Tools:**
- **Repmgr** - Replication Management
- **pgpool-II** - Connection Pooling + Failover
- **Barman** - Backup & Recovery

**Implementation (Woche 1):**
```bash
# Install repmgr
sudo apt install postgresql-15-repmgr

# Configure primary
# /etc/postgresql/15/main/postgresql.conf
wal_level = replica
max_wal_senders = 10
wal_keep_size = 1GB

# Configure standby
# /etc/postgresql/15/main/recovery.conf
primary_conninfo = 'host=primary port=5432 user=replicator'
```

**Acceptance Criteria:**
- ✅ Standby kann read-only queries beantworten
- ✅ Failover < 30 Sekunden (pgpool automatic failover)
- ✅ Backup täglich (Barman PITR)
- ✅ RPO < 1 Stunde, RTO < 15 Minuten

---

### 1.5 Frontend Testing Priority

**ENTSCHEIDUNG: Kritische Pfade + E2E für control_deck** ✅

**Begründung:**
- Volle Coverage zu teuer (4+ Wochen)
- Kritische Pfade decken 80% der User-Flows
- E2E fängt Integration-Bugs

**Scope (Woche 2-3):**

**Unit Tests (jest + testing-library):**
```typescript
// Critical User Flows
- ✅ Mission Enqueue Flow
- ✅ Agent Chat Interface
- ✅ System Health Dashboard
- ✅ LLM Config Update
```

**E2E Tests (Playwright):**
```typescript
// End-to-End Scenarios
- ✅ Login → Dashboard → Enqueue Mission → View Status
- ✅ Agent Management → Create Agent → Execute Task
- ✅ System Settings → Update Config → Verify
```

**Coverage Ziel:** 60-70% (kritische Pfade)

**Not Covered (Acceptable):**
- Admin-only Features (Settings, Module Registry)
- Experimentelle Features (Avatar UI, Emotions)
- Low-Traffic Pages (<1% usage)

---

### 1.6 Documentation Update

**ENTSCHEIDUNG: Auto-Generate aus Codebase + Manual Review** ✅

**Tools:**
- DocumentationAgent (bereits implementiert)
- Auto-discovery für Module + Agenten
- Manual Review für Architektur-Beschreibungen

**Scope:**
```bash
# CLAUDE.md Update (Woche 4)
- Module Count: 17+ → 46
- Agent Count: 5 → 17 (11 + 6 WebDev)
- NeuroRail Status: Phase 1 Skeleton → Phase 1 COMPLETE
- Governor Status: Phase 2 Future → Phase 2b DEPLOYED
- Mission System: Single → Dual (dann Konsolidierung dokumentieren)
- EventStream: Framework → 60+ Event Types
- TODO Markers: 125+ documented
- NotImplementedError: 8+ documented
```

**Automation:**
```bash
# Generate module list
find backend/app/modules/ -name "router.py" | wc -l

# Generate agent list
find backend/brain/agents/ -name "*_agent.py" | grep -v "__" | wc -l

# Count TODOs
grep -r "TODO\|FIXME" backend/ | wc -l
```

---

## 2. Target Architecture (SOLL)

### 2.1 System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Load Balancer (Nginx)                   │
│                  + WAF (ModSecurity/Cloudflare)            │
└────────────────────────┬───────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
┌───────▼────────┐              ┌────────▼────────┐
│  Backend Pod 1 │              │  Backend Pod 2  │
│  (FastAPI)     │              │  (FastAPI)      │
└───────┬────────┘              └────────┬────────┘
        │                                 │
        └────────────────┬────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐ ┌────▼─────┐  ┌──────▼──────┐
│  PostgreSQL    │ │  Redis   │  │   Qdrant    │
│  Primary       │ │  Cluster │  │  (Vector DB)│
│  + Standby     │ │  (3 nodes)│  │             │
└────────────────┘ └──────────┘  └─────────────┘
```

**Key Changes from IST:**
- ✅ Load Balancer (Nginx + Health Checks)
- ✅ WAF (Web Application Firewall)
- ✅ Horizontal Scaling (2+ Backend Pods)
- ✅ PostgreSQL Replication (Primary + Standby)
- ✅ Redis Cluster (3-6 nodes with sharding)
- ✅ Secrets Management (HashiCorp Vault)

---

### 2.2 Module Architecture (Modular Profiles)

**Minimal Profile (Edge/Dev):**
```python
modules = [
    "missions",      # Core mission queue
    "agents",        # Agent system (BaseAgent only)
    "llm_client",    # LLM communication
]
governance = False
database = "sqlite:///brain.db"  # Local SQLite
redis = None  # Optional (in-memory fallback)
```

**Standard Profile (Production SMB):**
```python
modules = [
    "missions", "agents", "llm_client",
    "policy",        # Policy engine
    "neurorail",     # Phase 1 observation
    "supervisor",    # Agent orchestration
    "metrics",       # Prometheus metrics
    "system_health", # Health monitoring
    "immune",        # Security monitoring
]
governance = True  # Governor + Policy Engine
neurorail_phase = 1  # Observe-only
database = "postgresql://..."
redis = "redis://redis:6379/0"
```

**Full Profile (Production Enterprise):**
```python
modules = ["*"]  # All 46 modules
governance = True
neurorail_phase = 2  # Enforcement enabled
database = "postgresql://..." with replication
redis = "redis://redis-cluster:6379/0"  # Cluster mode
```

**Enterprise Profile (Multi-Tenant):**
```python
modules = ["*"]
governance = True
neurorail_phase = 2
multi_tenancy = True  # Tenant isolation
compliance_mode = ["SOC2", "ISO27001", "GDPR"]
database = "postgresql://..." with cluster
redis = "redis://redis-cluster:6379/0"
secrets_backend = "vault"  # HashiCorp Vault
```

**Implementation:**
```python
# app/core/profiles.py
from enum import Enum
from typing import List, Optional

class ProfileType(str, Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"
    ENTERPRISE = "enterprise"

class ProfileConfig(BaseModel):
    name: ProfileType
    modules: List[str]
    governance_enabled: bool
    neurorail_phase: int  # 0, 1, 2
    database_url: str
    redis_url: Optional[str]
    redis_cluster: bool = False
    multi_tenancy: bool = False
    compliance_frameworks: List[str] = []
    secrets_backend: str = "env"  # env, vault, aws_secrets

def get_profile(profile_type: ProfileType) -> ProfileConfig:
    profiles = {
        ProfileType.MINIMAL: ProfileConfig(
            name=ProfileType.MINIMAL,
            modules=["missions", "agents", "llm_client"],
            governance_enabled=False,
            neurorail_phase=0,
            database_url="sqlite:///brain.db",
            redis_url=None,
        ),
        # ... weitere Profile
    }
    return profiles[profile_type]
```

---

### 2.3 Execution Layers (Optimiert)

**IST (4-Tier, 50-200ms):**
```
Request → Security → Governor → NeuroRail → Worker
```

**SOLL (3-Tier, 20-80ms):**
```
Request → Security + Governor (Cached) → NeuroRail (Async) → Worker Pool
```

**Optimierungen:**

1. **Governor Decision Caching (Woche 3):**
```python
# cache_key = f"governor:decision:{agent_id}:{action}:{hash(context)}"
cache_ttl = 300  # 5 Minuten

cached_decision = await redis.get(cache_key)
if cached_decision:
    return DecisionResult.parse_raw(cached_decision)

decision = await governor.evaluate(request)
await redis.setex(cache_key, cache_ttl, decision.json())
```

**Impact:** Governor Latency von ~50ms auf ~5ms (90% Reduktion)

2. **NeuroRail Async Audit (Woche 3):**
```python
# Non-blocking audit writes
asyncio.create_task(audit_service.log(event))
# Continue execution without waiting
```

**Impact:** Audit Latency von ~30ms auf ~2ms

3. **Mission Worker Pool (Woche 2):**
```python
# IST: 1 worker, sequential processing
async def _run_loop(self):
    mission = await queue.pop()
    await execute(mission)  # Blocks für gesamte Mission

# SOLL: N workers, concurrent processing
async def _run_loop(self):
    async with asyncio.TaskGroup() as tg:
        for _ in range(num_workers):
            tg.create_task(self._worker())

async def _worker(self):
    while True:
        mission = await queue.pop()
        await execute(mission)  # Parallel execution
```

**Impact:** Throughput von ~30 missions/min auf ~150 missions/min (5x)

**Target Latency (P95):**
- Minimal Profile: <50ms
- Standard Profile: <100ms
- Full Profile: <150ms

---

## 3. Security Hardening (Phase A, Woche 1)

### 3.1 Secrets Management

**SOLL: HashiCorp Vault Integration** ✅

**Architektur:**
```
┌──────────────┐       Secrets       ┌──────────────┐
│  Backend     │ ────API Request──> │  Vault       │
│  (FastAPI)   │ <───Secret Value─── │  (KV Store)  │
└──────────────┘                     └──────────────┘
```

**Implementation:**
```python
# app/core/secrets.py
import hvac

class SecretsManager:
    def __init__(self):
        self.client = hvac.Client(url=settings.VAULT_URL)
        self.client.token = settings.VAULT_TOKEN

    async def get_secret(self, path: str) -> str:
        """Retrieve secret from Vault."""
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        return response["data"]["data"]["value"]

# Usage
secrets = SecretsManager()
pg_password = await secrets.get_secret("brain/database/password")
redis_password = await secrets.get_secret("brain/redis/password")
```

**Migration:**
```bash
# Woche 1: Install Vault
docker run -d --name vault -p 8200:8200 vault:latest

# Store secrets
vault kv put secret/brain/database password=<secure-password>
vault kv put secret/brain/redis password=<secure-password>
vault kv put secret/brain/moonshot api_key=sk-2kmRRcg464ZFeVPIk9KNHoDhzvKXzrb0CSGOPysRtVc6dNgu

# Update .env
VAULT_URL=http://vault:8200
VAULT_TOKEN=<vault-token>

# Remove plain-text secrets from .env
# DATABASE_PASSWORD=<removed>
# REDIS_PASSWORD=<removed>
```

**Acceptance Criteria:**
- ✅ Keine Secrets in .env files
- ✅ Keine Secrets in git history
- ✅ Vault HA mode (3 nodes)
- ✅ Auto-rotation alle 90 Tage

---

### 3.2 Web Application Firewall (WAF)

**SOLL: ModSecurity mit OWASP CRS** ✅

**Nginx Integration:**
```nginx
# nginx.conf
load_module modules/ngx_http_modsecurity_module.so;

http {
    modsecurity on;
    modsecurity_rules_file /etc/nginx/modsecurity/main.conf;

    server {
        listen 443 ssl;
        server_name brain.falklabs.de;

        # ModSecurity rules
        modsecurity_rules '
            SecRuleEngine On
            SecRule ARGS "@rx <script" "id:1,deny,status:403"
        ';

        location / {
            proxy_pass http://backend:8000;
        }
    }
}
```

**OWASP Core Rule Set (CRS):**
```bash
# Install ModSecurity + CRS
git clone https://github.com/coreruleset/coreruleset.git
cp coreruleset/crs-setup.conf.example /etc/nginx/modsecurity/
cp -r coreruleset/rules/ /etc/nginx/modsecurity/

# Enable rules
echo 'Include /etc/nginx/modsecurity/crs-setup.conf' >> /etc/nginx/modsecurity/main.conf
echo 'Include /etc/nginx/modsecurity/rules/*.conf' >> /etc/nginx/modsecurity/main.conf
```

**Protection Against:**
- ✅ SQL Injection (OWASP CRS Rule 942xxx)
- ✅ XSS (OWASP CRS Rule 941xxx)
- ✅ CSRF
- ✅ Path Traversal
- ✅ Command Injection

**Acceptance Criteria:**
- ✅ OWASP Top 10 Coverage
- ✅ False Positive Rate <1%
- ✅ Latency Impact <10ms P95
- ✅ Alert System (Prometheus + Alertmanager)

---

### 3.3 Rate Limiting Enhancement

**IST:** slowapi + Redis (Task 2.3 implementiert)

**SOLL: Multi-Tier Rate Limiting** ✅

**Tier 1: Global Rate Limit (Nginx):**
```nginx
# nginx.conf
limit_req_zone $binary_remote_addr zone=global:10m rate=100r/s;

server {
    location /api/ {
        limit_req zone=global burst=20 nodelay;
        proxy_pass http://backend;
    }
}
```

**Tier 2: Endpoint-Specific (FastAPI):**
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/missions/enqueue")
@limiter.limit("10/minute")  # 10 missions per minute per IP
async def enqueue_mission(payload: MissionPayload):
    ...
```

**Tier 3: User-Based (Application):**
```python
# Per-user rate limiting (multi-tenancy)
@app.post("/api/missions/enqueue")
async def enqueue_mission(
    payload: MissionPayload,
    user: User = Depends(get_current_user)
):
    rate_limit_key = f"user:{user.id}:enqueue"
    if await redis.incr(rate_limit_key) > user.rate_limit:
        raise HTTPException(429, "Rate limit exceeded")
    await redis.expire(rate_limit_key, 60)
```

**Acceptance Criteria:**
- ✅ Global: 100 req/s per IP
- ✅ Endpoint: 10-50 req/min per endpoint
- ✅ User: Configurable per tenant
- ✅ Prometheus Metrics: `rate_limit_exceeded_total`

---

### 3.4 Security Headers (Enhancement)

**IST:** OWASP Headers implemented

**SOLL: Enhanced Headers + CSP** ✅

```python
# main.py middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Existing
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # NEW: Enhanced CSP
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.moonshot.ai; "
        "font-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    # NEW: Permissions Policy
    response.headers["Permissions-Policy"] = (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=(), "
        "usb=(), "
        "magnetometer=()"
    )

    # NEW: Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response
```

---

## 4. Scalability & Performance (Phase A, Woche 2-4)

### 4.1 PostgreSQL Connection Pool Tuning

**IST:** Default pool (5-10 connections)

**SOLL: Optimized Pool** ✅

```python
# app/core/config.py
class Settings(BaseSettings):
    # IST
    database_url: str = "postgresql+asyncpg://..."

    # SOLL
    database_url: str = "postgresql+asyncpg://..."
    database_pool_size: int = 20        # Min connections
    database_max_overflow: int = 10     # Max burst
    database_pool_timeout: int = 30     # Connection timeout
    database_pool_recycle: int = 3600   # Recycle after 1h
    database_echo: bool = False         # SQL logging (dev only)

# Usage
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_recycle=settings.database_pool_recycle,
    echo=settings.database_echo,
)
```

**Capacity:**
- IST: ~50 concurrent requests (pool exhaustion)
- SOLL: ~150 concurrent requests (20 + 10 overflow)

**Monitoring:**
```python
# Prometheus metrics
pg_pool_size = Gauge("pg_pool_size", "Current pool size")
pg_pool_overflow = Gauge("pg_pool_overflow", "Current overflow connections")
pg_pool_checkedout = Gauge("pg_pool_checkedout", "Checked out connections")
```

---

### 4.2 Redis Cluster (Sharding)

**IST:** Single Redis instance

**SOLL: Redis Cluster (3-6 nodes)** ✅

**Architektur:**
```
┌──────────────┐     Hash Slot     ┌──────────────┐
│  Redis Node 1│ ────Replication─> │  Redis Node 2│
│  (Master)    │                    │  (Replica)   │
│  Slots 0-5460│                    │              │
└──────────────┘                    └──────────────┘

┌──────────────┐                    ┌──────────────┐
│  Redis Node 3│                    │  Redis Node 4│
│  (Master)    │                    │  (Replica)   │
│  Slots 5461- │                    │              │
│  10922       │                    │              │
└──────────────┘                    └──────────────┘

┌──────────────┐                    ┌──────────────┐
│  Redis Node 5│                    │  Redis Node 6│
│  (Master)    │                    │  (Replica)   │
│  Slots 10923-│                    │              │
│  16383       │                    │              │
└──────────────┘                    └──────────────┘
```

**Implementation:**
```bash
# docker-compose.yml
services:
  redis-1:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --port 6379
    ports:
      - "6379:6379"

  redis-2:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --port 6380
    ports:
      - "6380:6380"

  # ... redis-3 to redis-6

# Create cluster
redis-cli --cluster create \
  127.0.0.1:6379 127.0.0.1:6380 127.0.0.1:6381 \
  127.0.0.1:6382 127.0.0.1:6383 127.0.0.1:6384 \
  --cluster-replicas 1
```

**Python Client:**
```python
# app/core/redis_client.py
from redis.asyncio.cluster import RedisCluster

async def get_redis_cluster():
    return await RedisCluster(
        startup_nodes=[
            {"host": "redis-1", "port": 6379},
            {"host": "redis-2", "port": 6380},
            {"host": "redis-3", "port": 6381},
        ],
        decode_responses=True,
        skip_full_coverage_check=True,
    )
```

**Capacity:**
- IST: ~10K concurrent missions
- SOLL: ~50K concurrent missions (5x)

**Acceptance Criteria:**
- ✅ Automatic sharding über 16384 hash slots
- ✅ Replica für jeden Master
- ✅ Automatic failover bei Node-Ausfall
- ✅ Monitoring: `redis_cluster_state`, `redis_cluster_slots_ok`

---

### 4.3 Mission Worker Pool

**IST:** Sequential processing (1 mission at a time)

**SOLL: Worker Pool (N concurrent workers)** ✅

**Implementation:**
```python
# modules/missions/worker.py
class MissionWorker:
    def __init__(
        self,
        queue: MissionQueue,
        num_workers: int = 5,  # NEW: Configurable worker count
        poll_interval: float = 2.0
    ):
        self.queue = queue
        self.num_workers = num_workers
        self.poll_interval = poll_interval
        self.workers: List[asyncio.Task] = []

    async def start(self):
        """Start N concurrent workers."""
        for i in range(self.num_workers):
            worker_task = asyncio.create_task(
                self._worker_loop(worker_id=i)
            )
            self.workers.append(worker_task)

    async def _worker_loop(self, worker_id: int):
        """Individual worker loop."""
        logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                mission = await self.queue.pop_next()
                if mission:
                    logger.info(f"Worker {worker_id} executing mission {mission.id}")
                    await self.execute_mission(mission)
                else:
                    await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

    async def stop(self):
        """Stop all workers gracefully."""
        self.running = False
        await asyncio.gather(*self.workers, return_exceptions=True)
```

**Configuration:**
```python
# .env
MISSION_WORKER_COUNT=5  # Minimal: 1, Standard: 5, Full: 10
```

**Throughput:**
- IST: ~30 missions/min (1 worker)
- SOLL: ~150 missions/min (5 workers, assuming 30s avg execution)

**Monitoring:**
```python
# Prometheus metrics
mission_workers_active = Gauge("mission_workers_active", "Active worker count")
mission_workers_busy = Gauge("mission_workers_busy", "Busy workers")
mission_throughput = Counter("mission_throughput_total", "Total missions processed")
```

---

### 4.4 Horizontal Scaling (Backend Pods)

**IST:** Single backend container

**SOLL: 2+ Backend Pods mit Load Balancer** ✅

**Architektur:**
```
                    ┌────────────────┐
                    │  Nginx LB      │
                    │  (Round Robin) │
                    └────────┬───────┘
                             │
               ┌─────────────┴─────────────┐
               │                           │
       ┌───────▼────────┐          ┌──────▼──────────┐
       │  Backend Pod 1 │          │  Backend Pod 2  │
       │  (Port 8000)   │          │  (Port 8001)    │
       └───────┬────────┘          └──────┬──────────┘
               │                           │
               └───────────┬───────────────┘
                           │
                   ┌───────▼────────┐
                   │  Shared State  │
                   │  (PostgreSQL,  │
                   │   Redis)       │
                   └────────────────┘
```

**Nginx Load Balancer:**
```nginx
# nginx/conf.d/upstream.conf
upstream backend {
    least_conn;  # Route to least busy server
    server backend-1:8000 max_fails=3 fail_timeout=30s;
    server backend-2:8001 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl;
    server_name api.brain.falklabs.de;

    location /api/ {
        proxy_pass http://backend;
        proxy_next_upstream error timeout http_502 http_503;
    }
}
```

**docker-compose.yml:**
```yaml
services:
  backend-1:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - WORKER_ID=1

  backend-2:
    build: ./backend
    ports:
      - "8001:8000"
    environment:
      - WORKER_ID=2

  nginx:
    image: nginx:latest
    ports:
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
    depends_on:
      - backend-1
      - backend-2
```

**Health Checks:**
```python
# main.py
@app.get("/health/live")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe."""
    # Check dependencies
    pg_healthy = await check_postgres()
    redis_healthy = await check_redis()

    if not (pg_healthy and redis_healthy):
        raise HTTPException(503, "Not ready")

    return {"status": "ready", "postgres": pg_healthy, "redis": redis_healthy}
```

**Acceptance Criteria:**
- ✅ 2+ Backend Pods aktiv
- ✅ Load Balancer verteilt Traffic
- ✅ Health Checks funktionieren
- ✅ Graceful Shutdown bei Deployment

---

## 5. Code Quality & Testing (Phase A, Woche 2-3)

### 5.1 Dependency Version Pinning

**IST:** Teilweise gepinnt, viele mit `>=` oder `^`

**SOLL: Alle Dependencies vollständig gepinnt** ✅

**Backend (requirements.txt):**
```bash
# Woche 2: Pin all versions
# Before
fastapi>=0.115.0
pydantic>=2.0
redis.asyncio

# After
fastapi==0.115.0
pydantic==2.10.3
redis==5.2.1
asyncpg==0.30.0
sqlalchemy==2.0.36
alembic==1.14.0
loguru==0.7.3
httpx==0.28.1
slowapi==0.1.9
# ... alle weiteren
```

**Tool: pip-compile**
```bash
# Install pip-tools
pip install pip-tools

# Create requirements.in (high-level deps)
echo "fastapi>=0.115" > requirements.in
echo "pydantic>=2.0" >> requirements.in

# Generate requirements.txt (pinned)
pip-compile requirements.in

# Update dependencies
pip-compile --upgrade requirements.in
```

**Frontend (package.json):**
```bash
# Before
"dependencies": {
  "next": "^14.2.33",
  "react": "^18",
  "@tanstack/react-query": "^5.90.0",
  "lucide-react": "latest"  # ❌ SEHR gefährlich
}

# After
"dependencies": {
  "next": "14.2.33",
  "react": "18.3.1",
  "react-dom": "18.3.1",
  "@tanstack/react-query": "5.90.0",
  "zustand": "4.5.2",
  "lucide-react": "0.460.0",
  "tailwindcss": "3.4.17"
}
```

**Remove --legacy-peer-deps:**
```bash
# Resolve peer dependency conflicts
npm install  # Without --legacy-peer-deps
# Fix conflicts manually by updating incompatible packages
```

**Acceptance Criteria:**
- ✅ Alle Backend Dependencies mit `==`
- ✅ Alle Frontend Dependencies ohne `^` oder `~`
- ✅ Keine `latest` Tags
- ✅ CI/CD verifies pinned versions

---

### 5.2 Frontend Testing Setup

**SOLL: Jest + React Testing Library + Playwright** ✅

**Installation (Woche 2):**
```bash
cd frontend/control_deck

# Jest + React Testing Library
npm install --save-dev jest @testing-library/react @testing-library/jest-dom @testing-library/user-event jest-environment-jsdom

# Playwright (E2E)
npm install --save-dev @playwright/test
npx playwright install
```

**Jest Configuration:**
```javascript
// jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.tsx',
  ],
  coverageThreshold: {
    global: {
      statements: 60,
      branches: 50,
      functions: 60,
      lines: 60,
    },
  },
};
```

**Example Test:**
```typescript
// src/hooks/useMissions.test.tsx
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMissionsInfo } from './useMissions';
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/missions/info', (req, res, ctx) => {
    return res(ctx.json({ name: 'Mission System', version: '1.0' }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('useMissionsInfo returns mission info', async () => {
  const queryClient = new QueryClient();
  const wrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  const { result } = renderHook(() => useMissionsInfo(), { wrapper });

  await waitFor(() => expect(result.current.isSuccess).toBe(true));

  expect(result.current.data).toEqual({
    name: 'Mission System',
    version: '1.0',
  });
});
```

**Playwright E2E:**
```typescript
// e2e/mission-flow.spec.ts
import { test, expect } from '@playwright/test';

test('enqueue mission flow', async ({ page }) => {
  await page.goto('http://localhost:3000');

  // Navigate to missions
  await page.click('text=Missions');

  // Fill mission form
  await page.fill('[name="name"]', 'Test Mission');
  await page.fill('[name="description"]', 'E2E Test');
  await page.selectOption('[name="priority"]', 'HIGH');

  // Submit
  await page.click('button:has-text("Enqueue")');

  // Verify success
  await expect(page.locator('text=Mission enqueued successfully')).toBeVisible();
});
```

**Coverage Target:**
- Unit Tests: 60-70% (kritische Pfade)
- E2E Tests: 5-10 Szenarien (critical user flows)

---

### 5.3 Load Testing Framework

**SOLL: k6 für Performance Testing** ✅

**Installation:**
```bash
# Install k6
curl https://github.com/grafana/k6/releases/download/v0.54.0/k6-v0.54.0-linux-amd64.tar.gz -L | tar xvz
sudo mv k6-v0.54.0-linux-amd64/k6 /usr/local/bin/
```

**Load Test Script:**
```javascript
// tests/load/mission_enqueue.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 10 },   // Ramp-up to 10 users
    { duration: '3m', target: 50 },   // Ramp-up to 50 users
    { duration: '2m', target: 100 },  // Spike to 100 users
    { duration: '2m', target: 50 },   // Scale down
    { duration: '1m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% under 500ms
    http_req_failed: ['rate<0.05'],    // <5% error rate
  },
};

export default function () {
  const payload = JSON.stringify({
    name: 'Load Test Mission',
    description: 'Performance testing',
    priority: 'NORMAL',
    payload: { test: true },
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post('http://localhost:8000/api/missions/enqueue', payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });

  sleep(1);
}
```

**Run Load Test:**
```bash
k6 run tests/load/mission_enqueue.js
```

**Acceptance Criteria:**
- ✅ P95 Latency <500ms bei 100 concurrent users
- ✅ Error Rate <5%
- ✅ Throughput >100 req/s
- ✅ No memory leaks (stable over 10min)

---

### 5.4 TODO/FIXME Resolution

**IST:** 125+ TODO markers

**SOLL: <20 TODO markers (kritisch)** ✅

**Strategy:**

**Week 2: Triage (2 Tage)**
```bash
# Kategorisieren nach Severity
grep -r "TODO\|FIXME" backend/ > todos.txt

# Kategorien:
# 🔴 CRITICAL (Security, Data Loss) → Sofort fixen
# 🟡 HIGH (Performance, User-Facing) → Woche 2-3
# 🟢 MEDIUM (Tech Debt) → Woche 4-8
# ⚪ LOW (Nice-to-have) → Backlog
```

**Week 2-3: Fix Critical (5 Tage)**
```bash
# Fix Security-Critical TODOs
# Example:
# TODO: Add authentication to this endpoint → 🔴 CRITICAL
# TODO: Validate user input → 🔴 CRITICAL
# TODO: Encrypt sensitive data → 🔴 CRITICAL
```

**Week 4: Fix High Priority (3 Tage)**
```bash
# Fix Performance TODOs
# Example:
# TODO: Cache this expensive query → 🟡 HIGH
# TODO: Add index to this table → 🟡 HIGH
```

**Acceptance Criteria:**
- ✅ 0 Critical TODOs
- ✅ <10 High Priority TODOs
- ✅ All remaining TODOs have Jira tickets

---

### 5.5 NotImplementedError Resolution

**IST:** 8+ NotImplementedError stubs

**SOLL: 0 NotImplementedError in production code** ✅

**Locations:**
1. `ir_governance/approvals.py` - 5 stubs
2. `autonomous_pipeline/execution_node.py` - 1 stub
3. Weitere 2+ in anderen Modulen

**Resolution Strategy:**

**Option A: Implementieren (Woche 2-3)**
```python
# ir_governance/approvals.py

# IST
def approve_request(self, request_id: str):
    raise NotImplementedError

# SOLL
async def approve_request(self, request_id: str) -> ApprovalResult:
    """Approve HITL request."""
    request = await self.get_request(request_id)
    if not request:
        raise HTTPException(404, "Request not found")

    # Update status
    request.status = ApprovalStatus.APPROVED
    request.approved_at = datetime.utcnow()
    request.approved_by = "admin"  # TODO: Get from auth context

    await self.db.commit()

    # Emit event
    await event_stream.emit(Event(
        event_type=EventType.APPROVAL_GRANTED,
        data={"request_id": request_id}
    ))

    return ApprovalResult(success=True, request_id=request_id)
```

**Option B: Remove (wenn nicht benötigt)**
```python
# Wenn Feature nicht verwendet wird → Entfernen
# 1. Remove stub function
# 2. Remove from router
# 3. Update docs
```

**Acceptance Criteria:**
- ✅ IR Governance HITL voll funktional (5 stubs implementiert)
- ✅ Autonomous Pipeline Execution funktional (1 stub implementiert)
- ✅ Alle anderen stubs entfernt oder implementiert

---

## 6. Phase 2 Features (Phase B, Woche 5-12)

### 6.1 NeuroRail Phase 2 Enforcement

**Timeline:**
- Woche 9-10: Canary 10% (Timeout)
- Woche 11: Canary 50% (Timeout + Budget)
- Woche 12: Full Rollout 100% (Timeout + Budget + Reflex)

**Feature 1: Timeout Enforcement (Woche 9)**
```python
# app/modules/neurorail/execution/service.py

# IST (Phase 1: No enforcement)
result = await executor(**context.job_parameters)

# SOLL (Phase 2: Timeout enforcement)
try:
    result = await asyncio.wait_for(
        executor(**context.job_parameters),
        timeout=context.timeout_ms / 1000
    )
except asyncio.TimeoutError:
    raise NeuroRailError(
        code=NeuroRailErrorCode.EXEC_TIMEOUT,
        message=f"Execution exceeded {context.timeout_ms}ms"
    )
```

**Feature 2: Budget Enforcement (Woche 11)**
```python
# Budget tracking + enforcement
class BudgetEnforcer:
    def __init__(self, max_llm_tokens: int, max_cost_usd: float):
        self.max_llm_tokens = max_llm_tokens
        self.max_cost_usd = max_cost_usd
        self.used_tokens = 0
        self.used_cost = 0.0

    async def check_budget(self, estimated_tokens: int):
        """Check if budget allows execution."""
        if self.used_tokens + estimated_tokens > self.max_llm_tokens:
            raise NeuroRailError(
                code=NeuroRailErrorCode.EXEC_OVERBUDGET,
                message=f"Token budget exceeded: {self.used_tokens}/{self.max_llm_tokens}"
            )

    async def record_usage(self, tokens: int, cost: float):
        """Record actual usage."""
        self.used_tokens += tokens
        self.used_cost += cost

        # Emit metric
        prometheus.counter("neurorail_tokens_used_total").inc(tokens)
        prometheus.counter("neurorail_cost_usd_total").inc(cost)
```

**Feature 3: Reflex System (Woche 12)**
```python
# app/modules/neurorail/reflex/service.py

class ReflexSystem:
    """Auto-remediation on repeated failures."""

    async def evaluate_trigger(self, attempt: Attempt):
        """Check if reflex should trigger."""
        # Count recent failures
        recent_failures = await self.get_recent_failures(
            job_id=attempt.job_id,
            time_window=300  # 5 minutes
        )

        if len(recent_failures) >= 3:
            # Trigger circuit breaker
            await self.trigger_reflex(
                reflex_type=ReflexType.CIRCUIT_BREAKER,
                entity_id=attempt.job_id,
                cooldown_seconds=300
            )

    async def trigger_reflex(
        self,
        reflex_type: ReflexType,
        entity_id: str,
        cooldown_seconds: int
    ):
        """Activate reflex (suspend, probe, cooldown)."""
        await redis.setex(
            f"reflex:{reflex_type}:{entity_id}",
            cooldown_seconds,
            "active"
        )

        # Emit event
        await event_stream.emit(Event(
            event_type=EventType.REFLEX_TRIGGERED,
            data={
                "reflex_type": reflex_type,
                "entity_id": entity_id,
                "cooldown_seconds": cooldown_seconds
            }
        ))
```

**Acceptance Criteria:**
- ✅ Timeout Enforcement: 0 missions exceed timeout after Phase 2
- ✅ Budget Enforcement: No token budget violations
- ✅ Reflex System: Circuit breaker triggers after 3 failures in 5min
- ✅ Metrics: All 9 NeuroRail metrics collecting data
- ✅ Error Rate: <5% after full rollout

---

### 6.2 Autonomous Pipeline Completion

**SOLL: DAG Execution Engine** ✅

**Implementation:**
```python
# app/modules/autonomous_pipeline/execution_node.py

# IST
async def execute(self):
    raise NotImplementedError

# SOLL
async def execute(self) -> ExecutionResult:
    """Execute pipeline node."""
    logger.info(f"Executing node {self.node_id}")

    # Check dependencies
    for dep_id in self.dependencies:
        dep_status = await self.get_node_status(dep_id)
        if dep_status != NodeStatus.COMPLETED:
            raise PipelineError(f"Dependency {dep_id} not completed")

    # Execute node logic
    try:
        result = await self._execute_node_logic()
        await self.update_status(NodeStatus.COMPLETED)
        return ExecutionResult(success=True, data=result)
    except Exception as e:
        await self.update_status(NodeStatus.FAILED)
        raise PipelineError(f"Node execution failed: {e}")

async def _execute_node_logic(self) -> Any:
    """Node-specific execution logic."""
    if self.node_type == NodeType.MISSION:
        return await self._execute_mission()
    elif self.node_type == NodeType.AGENT:
        return await self._execute_agent()
    elif self.node_type == NodeType.TRANSFORM:
        return await self._execute_transform()
```

**Pipeline Definition (YAML):**
```yaml
# pipelines/ml_training_pipeline.yaml
name: "ML Model Training Pipeline"
version: "1.0"
nodes:
  - id: "data_fetch"
    type: "mission"
    mission_name: "Fetch Training Data"
    dependencies: []

  - id: "data_preprocess"
    type: "transform"
    transform_fn: "preprocess_data"
    dependencies: ["data_fetch"]

  - id: "model_train"
    type: "agent"
    agent_id: "ml_trainer"
    dependencies: ["data_preprocess"]

  - id: "model_evaluate"
    type: "agent"
    agent_id: "ml_evaluator"
    dependencies: ["model_train"]

  - id: "model_deploy"
    type: "mission"
    mission_name: "Deploy Model"
    dependencies: ["model_evaluate"]
    conditions:
      - "model_accuracy > 0.85"
```

**Acceptance Criteria:**
- ✅ DAG Execution Engine functional
- ✅ Pipeline Templates: ETL, ML Training, Deployment
- ✅ Visual Pipeline Editor (Frontend)
- ✅ Pipeline Versioning + Rollback
- ✅ Monitoring: `pipeline_executions_total`, `pipeline_duration_ms`

---

### 6.3 Self-Healing & Adaptation

**SOLL: Learning System Integration** ✅

**Architecture:**
```
Execution → Metrics → Learning System → Optimization → Governor
```

**Implementation:**
```python
# app/modules/learning/service.py

class LearningSystem:
    """Adaptive optimization based on execution history."""

    async def analyze_performance(self, time_window: int = 3600):
        """Analyze recent execution patterns."""
        metrics = await self.get_metrics(time_window)

        # Identify bottlenecks
        bottlenecks = []
        if metrics["avg_latency"] > 500:
            bottlenecks.append("high_latency")
        if metrics["error_rate"] > 0.05:
            bottlenecks.append("high_error_rate")

        # Generate recommendations
        recommendations = await self._generate_recommendations(bottlenecks)

        return PerformanceAnalysis(
            bottlenecks=bottlenecks,
            recommendations=recommendations
        )

    async def _generate_recommendations(
        self,
        bottlenecks: List[str]
    ) -> List[Recommendation]:
        """Generate optimization recommendations."""
        recommendations = []

        if "high_latency" in bottlenecks:
            recommendations.append(Recommendation(
                type="cache_tuning",
                description="Increase governor decision cache TTL",
                action="set_cache_ttl",
                params={"ttl": 600}
            ))

        if "high_error_rate" in bottlenecks:
            recommendations.append(Recommendation(
                type="timeout_adjustment",
                description="Increase mission timeout threshold",
                action="adjust_timeout",
                params={"timeout_ms": 45000}
            ))

        return recommendations

    async def apply_recommendation(self, recommendation: Recommendation):
        """Apply optimization automatically (with approval)."""
        # Request supervisor approval
        approval = await supervisor.request_approval(
            action="apply_optimization",
            context={"recommendation": recommendation.dict()}
        )

        if not approval.approved:
            logger.info(f"Optimization denied: {approval.reason}")
            return

        # Apply optimization
        if recommendation.action == "set_cache_ttl":
            await redis.config_set("cache_ttl", recommendation.params["ttl"])

        # Emit event
        await event_stream.emit(Event(
            event_type=EventType.OPTIMIZATION_APPLIED,
            data=recommendation.dict()
        ))
```

**DNA Module Integration:**
```python
# app/modules/dna/service.py

class DNAOptimizer:
    """Genetic optimization for agent parameters."""

    async def optimize_agent_config(
        self,
        agent_id: str,
        fitness_metric: str = "success_rate"
    ):
        """Optimize agent configuration via genetic algorithm."""
        # Get current config
        current_config = await self.get_agent_config(agent_id)

        # Generate population
        population = self._generate_population(current_config, size=10)

        # Evaluate fitness
        for config in population:
            fitness = await self._evaluate_fitness(agent_id, config, fitness_metric)
            config["fitness"] = fitness

        # Select best
        population.sort(key=lambda x: x["fitness"], reverse=True)
        best_config = population[0]

        # Apply if improvement
        if best_config["fitness"] > current_config["fitness"]:
            await self.update_agent_config(agent_id, best_config)

            logger.info(f"Agent {agent_id} optimized: {best_config['fitness']}")
```

**Acceptance Criteria:**
- ✅ Performance Analysis läuft alle 1h
- ✅ Recommendations generiert automatisch
- ✅ Apply Optimization mit Supervisor Approval
- ✅ DNA Optimizer funktional für Agent Configs
- ✅ Metrics: `optimizations_applied_total`, `fitness_score`

---

### 6.4 Code Generation Capabilities

**SOLL: Enhanced CoderAgent** ✅

**Features:**
- ✅ Full-Stack Code Generation (Backend + Frontend)
- ✅ Automated Testing Generation (Test-Driven Development)
- ✅ Self-Documentation (Auto-update CLAUDE.md)

**Implementation:**
```python
# brain/agents/coder_agent.py (Enhanced)

class CoderAgent(BaseAgent):
    async def generate_full_stack_feature(
        self,
        feature_spec: FeatureSpec
    ) -> FullStackResult:
        """Generate backend + frontend + tests."""

        # 1. Generate Backend
        backend_code = await self._generate_backend(
            endpoint=feature_spec.endpoint,
            schema=feature_spec.schema
        )

        # 2. Generate Frontend
        frontend_code = await self._generate_frontend(
            component=feature_spec.component,
            api_endpoint=feature_spec.endpoint
        )

        # 3. Generate Tests
        tests = await self._generate_tests(
            backend_code=backend_code,
            frontend_code=frontend_code
        )

        # 4. Validate Code
        validation = await self._validate_code(
            backend_code, frontend_code, tests
        )

        if not validation.success:
            raise CodeValidationError(validation.errors)

        return FullStackResult(
            backend=backend_code,
            frontend=frontend_code,
            tests=tests,
            validation=validation
        )

    async def _generate_backend(
        self,
        endpoint: str,
        schema: Dict[str, Any]
    ) -> BackendCode:
        """Generate FastAPI endpoint."""
        prompt = f"""
        Generate a FastAPI endpoint for {endpoint}.

        Schema:
        {json.dumps(schema, indent=2)}

        Requirements:
        - Pydantic models for request/response
        - Proper error handling
        - Type hints
        - Docstrings
        - Security (no SQL injection, XSS)
        """

        code = await self.call_llm(prompt)

        return BackendCode(
            router_code=code["router"],
            schema_code=code["schema"],
            service_code=code["service"]
        )

    async def _generate_tests(
        self,
        backend_code: BackendCode,
        frontend_code: FrontendCode
    ) -> TestCode:
        """Generate pytest + jest tests."""
        # Backend tests
        backend_tests = await self.call_llm(f"""
        Generate pytest tests for:
        {backend_code.router_code}

        Cover:
        - Happy path
        - Error cases
        - Edge cases
        """)

        # Frontend tests
        frontend_tests = await self.call_llm(f"""
        Generate jest + testing-library tests for:
        {frontend_code.component_code}

        Cover:
        - Rendering
        - User interactions
        - API integration
        """)

        return TestCode(
            backend_tests=backend_tests,
            frontend_tests=frontend_tests
        )
```

**Self-Documentation:**
```python
# brain/agents/documentation_agent.py (Enhanced)

class DocumentationAgent(BaseAgent):
    async def update_claude_md(self):
        """Auto-update CLAUDE.md from codebase."""

        # Scan modules
        modules = await self._scan_modules("backend/app/modules/")

        # Scan agents
        agents = await self._scan_agents("backend/brain/agents/")

        # Generate markdown
        md = f"""
# CLAUDE.md - Auto-Generated {datetime.now().isoformat()}

## Module Count: {len(modules)}
{self._format_modules(modules)}

## Agent Count: {len(agents)}
{self._format_agents(agents)}

## Recent Changes
{await self._get_recent_changes()}
"""

        # Write to file
        with open("CLAUDE.md", "w") as f:
            f.write(md)

        logger.info(f"CLAUDE.md updated: {len(modules)} modules, {len(agents)} agents")
```

**Acceptance Criteria:**
- ✅ CoderAgent generiert Full-Stack Features (Backend + Frontend + Tests)
- ✅ Generated Code passes Linting (pylint, eslint)
- ✅ Generated Tests have >80% coverage
- ✅ DocumentationAgent updates CLAUDE.md automatisch
- ✅ Integration mit CI/CD (Auto-PR after generation)

---

## 7. Enterprise Features (Phase C, Woche 13-24)

### 7.1 Multi-Tenancy

**SOLL: Tenant Isolation + Billing** ✅

**Architecture:**
```
┌──────────────┐
│  Request     │
│  (Tenant ID) │
└──────┬───────┘
       │
┌──────▼────────────────────────┐
│  Tenant Middleware            │
│  - Extract tenant_id from JWT │
│  - Set tenant context         │
└──────┬────────────────────────┘
       │
┌──────▼────────────────────────┐
│  Row-Level Security           │
│  (PostgreSQL RLS)             │
│  WHERE tenant_id = current    │
└──────┬────────────────────────┘
       │
┌──────▼────────────────────────┐
│  Tenant-Specific Rate Limit   │
│  (Redis per tenant)           │
└───────────────────────────────┘
```

**Implementation:**

**1. Tenant Middleware:**
```python
# app/api/middleware/tenant.py

class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        # Extract tenant from JWT
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        tenant_id = self._extract_tenant_from_jwt(token)

        # Set tenant context
        request.state.tenant_id = tenant_id

        # Inject into DB session
        # PostgreSQL: SET app.current_tenant = 'tenant_123'
        await db.execute(f"SET app.current_tenant = '{tenant_id}'")

        response = await call_next(request)
        return response
```

**2. Row-Level Security (PostgreSQL):**
```sql
-- Enable RLS on tables
ALTER TABLE missions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE neurorail_audit ENABLE ROW LEVEL SECURITY;

-- Create RLS policy
CREATE POLICY tenant_isolation ON missions
    USING (tenant_id = current_setting('app.current_tenant')::TEXT);

CREATE POLICY tenant_isolation ON agents
    USING (tenant_id = current_setting('app.current_tenant')::TEXT);

CREATE POLICY tenant_isolation ON neurorail_audit
    USING (tenant_id = current_setting('app.current_tenant')::TEXT);
```

**3. Tenant Management:**
```python
# app/modules/tenants/service.py

class TenantService:
    async def create_tenant(self, tenant: TenantCreate) -> Tenant:
        """Create new tenant with isolation."""
        new_tenant = Tenant(
            id=generate_tenant_id(),
            name=tenant.name,
            plan=tenant.plan,  # free, standard, enterprise
            rate_limits={
                "missions_per_hour": 100,
                "api_requests_per_second": 10
            },
            created_at=datetime.utcnow()
        )

        await db.tenants.insert(new_tenant)

        # Create tenant-specific resources
        await self._setup_tenant_resources(new_tenant.id)

        return new_tenant

    async def suspend_tenant(self, tenant_id: str, reason: str):
        """Suspend tenant (e.g., non-payment)."""
        await db.tenants.update(
            {"id": tenant_id},
            {"status": "suspended", "suspended_reason": reason}
        )

        # Block all API requests
        await redis.setex(f"tenant:suspended:{tenant_id}", 86400, "1")
```

**4. Tenant Billing/Metering:**
```python
# app/modules/tenants/billing.py

class BillingService:
    async def record_usage(self, tenant_id: str, usage: Usage):
        """Record billable usage."""
        # Store in time-series database (InfluxDB or PostgreSQL)
        await db.billing_events.insert({
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow(),
            "resource_type": usage.resource_type,  # missions, llm_tokens, storage
            "quantity": usage.quantity,
            "cost_usd": usage.cost_usd
        })

        # Update running totals
        await redis.incrbyfloat(
            f"tenant:usage:{tenant_id}:{usage.resource_type}",
            usage.quantity
        )

    async def generate_invoice(self, tenant_id: str, month: str) -> Invoice:
        """Generate monthly invoice."""
        usage_data = await self._get_monthly_usage(tenant_id, month)

        invoice = Invoice(
            tenant_id=tenant_id,
            month=month,
            line_items=[
                InvoiceLineItem(
                    description="Missions",
                    quantity=usage_data["missions"],
                    unit_price=0.10,
                    total=usage_data["missions"] * 0.10
                ),
                InvoiceLineItem(
                    description="LLM Tokens",
                    quantity=usage_data["llm_tokens"],
                    unit_price=0.002 / 1000,  # per 1K tokens
                    total=usage_data["llm_tokens"] * 0.002 / 1000
                ),
            ],
            total=sum(item.total for item in invoice.line_items)
        )

        return invoice
```

**Acceptance Criteria:**
- ✅ Tenant Isolation (RLS funktioniert)
- ✅ Tenant-Specific Rate Limits
- ✅ Tenant Management UI (Create, Suspend, Delete)
- ✅ Billing/Metering funktional
- ✅ Invoice Generation automatisch (monatlich)
- ✅ Security: Keine Cross-Tenant Data Leakage (Penetration Test)

---

### 7.2 SOC 2 / ISO 27001 Compliance

**SOLL: Compliance Framework + Evidence Collection** ✅

**SOC 2 Requirements:**

| Control | Requirement | Implementation |
|---------|-------------|----------------|
| **CC1.1** | COSO Framework | ✅ Governance Framework (Governor + Policy) |
| **CC2.1** | Communication | ✅ EventStream (60+ Event Types) |
| **CC3.1** | Risk Assessment | ✅ Risk Tier System (SAFE/STANDARD/RESTRICTED) |
| **CC4.1** | Monitoring | ✅ Prometheus Metrics + System Health |
| **CC5.1** | Control Activities | ✅ NeuroRail Enforcement + Reflex System |
| **CC6.1** | Logical Access | ✅ JWT Auth + RBAC |
| **CC6.6** | Encryption | ✅ TLS 1.3 + Data at Rest Encryption |
| **CC7.1** | System Operations | ✅ Health Checks + Auto-Scaling |
| **CC8.1** | Change Management | ✅ Alembic Migrations + Git Versioning |
| **CC9.1** | Risk Mitigation | ✅ Circuit Breaker + Failover |

**Implementation:**

**1. Evidence Collection Automation:**
```python
# app/modules/compliance/soc2.py

class SOC2EvidenceCollector:
    async def collect_evidence(self, control: str, period: str):
        """Collect evidence for SOC 2 control."""
        if control == "CC6.1":  # Logical Access
            evidence = await self._collect_access_logs(period)
        elif control == "CC7.1":  # System Operations
            evidence = await self._collect_uptime_reports(period)
        elif control == "CC8.1":  # Change Management
            evidence = await self._collect_deployment_logs(period)

        return Evidence(
            control=control,
            period=period,
            data=evidence,
            collected_at=datetime.utcnow()
        )

    async def _collect_access_logs(self, period: str):
        """Collect authentication logs."""
        return await db.auth_logs.find({
            "timestamp": {"$gte": period_start, "$lte": period_end}
        })

    async def generate_soc2_report(self, period: str) -> SOC2Report:
        """Generate SOC 2 Type II report."""
        controls = [
            "CC1.1", "CC2.1", "CC3.1", "CC4.1", "CC5.1",
            "CC6.1", "CC6.6", "CC7.1", "CC8.1", "CC9.1"
        ]

        evidence_list = []
        for control in controls:
            evidence = await self.collect_evidence(control, period)
            evidence_list.append(evidence)

        return SOC2Report(
            period=period,
            controls=controls,
            evidence=evidence_list,
            generated_at=datetime.utcnow()
        )
```

**2. ISO 27001 Controls:**
```python
# app/modules/compliance/iso27001.py

class ISO27001Compliance:
    async def assess_control(self, control: str) -> ControlAssessment:
        """Assess ISO 27001 control implementation."""
        assessments = {
            "A.9.1.1": self._assess_access_control_policy,
            "A.9.2.1": self._assess_user_registration,
            "A.12.1.1": self._assess_operational_procedures,
            "A.14.2.1": self._assess_secure_development,
        }

        if control in assessments:
            result = await assessments[control]()
            return result
        else:
            return ControlAssessment(
                control=control,
                status="not_implemented"
            )

    async def _assess_access_control_policy(self):
        """A.9.1.1 - Access Control Policy."""
        # Check if policy exists
        policy_exists = await self._check_policy_exists("access_control")

        # Check if policy is enforced
        policy_enforced = await self._check_policy_enforcement()

        return ControlAssessment(
            control="A.9.1.1",
            status="implemented" if (policy_exists and policy_enforced) else "partial",
            evidence={
                "policy_document": "docs/ACCESS_CONTROL_POLICY.md",
                "enforcement_logs": await self._get_enforcement_logs()
            }
        )
```

**3. Continuous Monitoring:**
```python
# app/modules/compliance/monitoring.py

class ComplianceMonitor:
    async def run_continuous_monitoring(self):
        """Run compliance checks every 24h."""
        while True:
            # Check security controls
            security_score = await self._assess_security_controls()

            # Check access patterns
            access_anomalies = await self._detect_access_anomalies()

            # Check data integrity
            data_integrity = await self._verify_data_integrity()

            # Alert if issues
            if security_score < 0.9 or access_anomalies or not data_integrity:
                await self._send_compliance_alert({
                    "security_score": security_score,
                    "access_anomalies": access_anomalies,
                    "data_integrity": data_integrity
                })

            await asyncio.sleep(86400)  # 24 hours
```

**Acceptance Criteria:**
- ✅ SOC 2 Type II Evidence Collection automatisiert
- ✅ ISO 27001 Compliance Assessment läuft monatlich
- ✅ Continuous Monitoring aktiv (24h Checks)
- ✅ Audit Trail vollständig (alle Security Events)
- ✅ External Audit Ready (Dokumentation komplett)

---

### 7.3 GDPR Compliance Automation

**SOLL: Right to be Forgotten + Consent Management** ✅

**Implementation:**

**1. Data Deletion Automation:**
```python
# app/modules/compliance/gdpr.py

class GDPRDataDeletionService:
    async def delete_user_data(self, user_id: str, reason: str):
        """Delete all user data (Right to be Forgotten - Art. 17)."""

        # 1. Anonymize in audit logs (keep for compliance, but anonymize)
        await db.neurorail_audit.update_many(
            {"actor_id": user_id},
            {"$set": {"actor_id": "anonymized", "anonymized_at": datetime.utcnow()}}
        )

        # 2. Delete personal data
        tables = [
            "users",
            "user_profiles",
            "user_missions",
            "user_sessions"
        ]

        for table in tables:
            await db[table].delete_many({"user_id": user_id})

        # 3. Emit event
        await event_stream.emit(Event(
            event_type=EventType.GDPR_DATA_DELETED,
            data={
                "user_id": user_id,
                "reason": reason,
                "deleted_at": datetime.utcnow().isoformat()
            }
        ))

        # 4. Log deletion request
        await db.gdpr_deletion_log.insert({
            "user_id": user_id,
            "reason": reason,
            "requested_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
            "tables_affected": tables
        })

        logger.info(f"GDPR deletion completed for user {user_id}")

    async def export_user_data(self, user_id: str) -> UserDataExport:
        """Export all user data (Right to Data Portability - Art. 20)."""
        data = {}

        tables = ["users", "user_profiles", "user_missions", "user_sessions"]

        for table in tables:
            data[table] = await db[table].find({"user_id": user_id}).to_list()

        return UserDataExport(
            user_id=user_id,
            exported_at=datetime.utcnow(),
            data=data,
            format="json"
        )
```

**2. Consent Management:**
```python
# app/modules/compliance/consent.py

class ConsentManagementService:
    async def record_consent(
        self,
        user_id: str,
        consent_type: str,  # "marketing", "analytics", "data_processing"
        granted: bool
    ):
        """Record user consent (GDPR Art. 6, 7)."""
        await db.user_consents.insert({
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": granted,
            "granted_at": datetime.utcnow(),
            "ip_address": request.client.host,
            "user_agent": request.headers.get("User-Agent")
        })

    async def check_consent(self, user_id: str, consent_type: str) -> bool:
        """Check if user has granted consent."""
        consent = await db.user_consents.find_one({
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": True
        })
        return consent is not None

    async def withdraw_consent(self, user_id: str, consent_type: str):
        """Withdraw user consent (GDPR Art. 7.3)."""
        await db.user_consents.insert({
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": False,
            "withdrawn_at": datetime.utcnow()
        })

        # Stop data processing based on consent
        if consent_type == "marketing":
            await self._stop_marketing_activities(user_id)
        elif consent_type == "analytics":
            await self._stop_analytics_tracking(user_id)
```

**3. Data Processing Agreement (DPA) Templates:**
```python
# app/modules/compliance/dpa.py

class DPAService:
    async def generate_dpa(self, tenant_id: str) -> DPA:
        """Generate Data Processing Agreement (GDPR Art. 28)."""
        tenant = await db.tenants.find_one({"id": tenant_id})

        dpa = DPA(
            controller=tenant.name,
            processor="BRAiN v2 Platform",
            date=datetime.utcnow(),
            terms=[
                "Process data only on documented instructions",
                "Ensure confidentiality of processing",
                "Implement appropriate technical and organizational measures",
                "Assist with data subject requests",
                "Delete or return data at end of contract",
                "Make available all information for audits"
            ]
        )

        return dpa
```

**Acceptance Criteria:**
- ✅ Data Deletion funktioniert innerhalb 30 Tage (GDPR Art. 17)
- ✅ Data Export funktioniert (GDPR Art. 20)
- ✅ Consent Management UI funktional
- ✅ DPA Templates generiert automatisch
- ✅ Audit Trail für alle GDPR-relevanten Aktionen

---

### 7.4 Sovereign Mode (Air-Gapped Deployment)

**SOLL: Zero-Trust Air-Gapped Deployment** ✅

**Architecture:**
```
┌─────────────────────────────────────┐
│  Air-Gapped Environment             │
│  (No Internet Connection)           │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  BRAiN v2 (Full Profile)    │   │
│  │  - All 46 Modules           │   │
│  │  - Local LLM (Ollama)       │   │
│  │  - PostgreSQL Cluster       │   │
│  │  - Redis Cluster            │   │
│  │  - Qdrant                   │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  HashiCorp Vault            │   │
│  │  (Secrets Management)       │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  Monitoring Stack           │   │
│  │  - Prometheus               │   │
│  │  - Grafana                  │   │
│  │  - Loki                     │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

**Implementation:**

**1. Local LLM Deployment:**
```yaml
# docker-compose.sovereign.yml
services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_models:/root/.ollama
    command: serve
    environment:
      - OLLAMA_HOST=0.0.0.0:11434

  # Pre-download models offline
  ollama-init:
    image: ollama/ollama:latest
    volumes:
      - ollama_models:/root/.ollama
    command: |
      sh -c "
        ollama pull llama3.2:latest
        ollama pull codellama:latest
        ollama pull mistral:latest
      "
    depends_on:
      - ollama
```

**2. Encrypted Data at Rest:**
```python
# app/core/encryption.py

from cryptography.fernet import Fernet

class EncryptionService:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt data."""
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt data."""
        return self.cipher.decrypt(ciphertext.encode()).decode()

# PostgreSQL Encryption
# postgresql.conf
# ssl = on
# ssl_cert_file = '/etc/ssl/certs/server.crt'
# ssl_key_file = '/etc/ssl/private/server.key'

# pgcrypto extension for column-level encryption
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt sensitive columns
ALTER TABLE users ADD COLUMN email_encrypted BYTEA;
UPDATE users SET email_encrypted = pgp_sym_encrypt(email, 'encryption_key');
```

**3. Zero-Trust mTLS:**
```nginx
# nginx.conf (mTLS)
server {
    listen 443 ssl;
    server_name brain.local;

    # Server certificate
    ssl_certificate /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;

    # Client certificate verification
    ssl_client_certificate /etc/nginx/ssl/ca.crt;
    ssl_verify_client on;
    ssl_verify_depth 2;

    location / {
        # Verify client certificate CN
        if ($ssl_client_s_dn_cn != "authorized-client") {
            return 403;
        }

        proxy_pass http://backend:8000;
    }
}
```

**4. Offline Update Mechanism:**
```bash
# Update via USB/Physical Media
# 1. Export on development machine
docker save brain-v2:latest > brain-v2-latest.tar
docker save postgres:15 > postgres-15.tar
docker save redis:7 > redis-7.tar

# 2. Transfer via USB
cp *.tar /media/usb/

# 3. Import on air-gapped machine
docker load < /media/usb/brain-v2-latest.tar
docker load < /media/usb/postgres-15.tar
docker load < /media/usb/redis-7.tar

# 4. Start services
docker-compose -f docker-compose.sovereign.yml up -d
```

**Acceptance Criteria:**
- ✅ Deployment funktioniert ohne Internet
- ✅ Local LLM (Ollama) funktional
- ✅ Encrypted Data at Rest (PostgreSQL pgcrypto)
- ✅ mTLS zwischen allen Services
- ✅ Offline Update Mechanism funktioniert
- ✅ Monitoring Stack läuft lokal (Prometheus + Grafana)

---

### 7.5 High Availability (99.99% Uptime)

**SOLL: Multi-Region Active-Active** ✅

**Architecture:**
```
┌────────────────────────────────────────────────────┐
│  Global Load Balancer (Cloudflare / AWS Route 53) │
└────────┬─────────────────────────────────┬─────────┘
         │                                  │
┌────────▼────────┐                ┌───────▼─────────┐
│  Region 1 (EU)  │                │  Region 2 (US)  │
│                 │                │                 │
│  ┌───────────┐  │                │  ┌───────────┐  │
│  │ Backend   │  │                │  │ Backend   │  │
│  │ (2 Pods)  │  │                │  │ (2 Pods)  │  │
│  └─────┬─────┘  │                │  └─────┬─────┘  │
│        │        │                │        │        │
│  ┌─────▼─────┐  │                │  ┌─────▼─────┐  │
│  │ PostgreSQL│  │  Replication   │  │ PostgreSQL│  │
│  │ Primary   │◄─┼────────────────┼──┤ Standby   │  │
│  └───────────┘  │                │  └───────────┘  │
│                 │                │                 │
│  ┌───────────┐  │                │  ┌───────────┐  │
│  │ Redis     │  │  Sync          │  │ Redis     │  │
│  │ Cluster   │◄─┼────────────────┼──┤ Cluster   │  │
│  └───────────┘  │                │  └───────────┘  │
└─────────────────┘                └─────────────────┘
```

**Implementation:**

**1. Disaster Recovery:**
```bash
# Backup Strategy (Barman)
# /etc/barman.conf
[brain-prod]
description = "BRAiN Production Database"
ssh_command = ssh postgres@pg-primary
conninfo = host=pg-primary user=barman dbname=brain
backup_method = postgres
archiver = on
retention_policy = RECOVERY WINDOW OF 7 DAYS

# Daily backups
0 2 * * * barman backup brain-prod

# PITR (Point-in-Time Recovery)
barman recover brain-prod latest /var/lib/postgresql/15/main --target-time "2026-02-03 14:30:00"
```

**2. Chaos Engineering:**
```python
# tests/chaos/chaos_monkey.py
import random

class ChaosMonkey:
    """Chaos engineering for resilience testing."""

    async def inject_failure(self, service: str):
        """Randomly inject failures."""
        failure_types = [
            "kill_pod",
            "network_latency",
            "disk_full",
            "cpu_spike"
        ]

        failure = random.choice(failure_types)

        if failure == "kill_pod":
            await self._kill_random_pod(service)
        elif failure == "network_latency":
            await self._inject_network_latency(service, latency_ms=500)
        elif failure == "disk_full":
            await self._simulate_disk_full(service)
        elif failure == "cpu_spike":
            await self._inject_cpu_spike(service, duration=60)

    async def _kill_random_pod(self, service: str):
        """Kill random pod to test failover."""
        pods = await self._list_pods(service)
        pod = random.choice(pods)
        await self._delete_pod(pod)
        logger.info(f"Chaos: Killed pod {pod}")

# Run chaos tests daily
0 3 * * * python tests/chaos/chaos_monkey.py --service=backend
```

**3. SLA Monitoring:**
```python
# app/modules/monitoring/sla.py

class SLAMonitor:
    """Monitor 99.99% uptime SLA."""

    async def calculate_uptime(self, time_window: int = 86400):
        """Calculate uptime percentage."""
        # Get total time
        total_time = time_window

        # Get downtime from health checks
        downtime = await self._get_downtime(time_window)

        # Calculate uptime
        uptime = ((total_time - downtime) / total_time) * 100

        return uptime

    async def check_sla_breach(self):
        """Check if SLA is breached."""
        monthly_uptime = await self.calculate_uptime(time_window=30*86400)

        if monthly_uptime < 99.99:
            await self._send_sla_breach_alert({
                "uptime": monthly_uptime,
                "threshold": 99.99,
                "breach_severity": "critical"
            })

# Prometheus alert
groups:
- name: sla
  rules:
  - alert: SLABreach
    expr: (1 - (rate(http_requests_total{status=~"5.."}[30d]) / rate(http_requests_total[30d]))) < 0.9999
    for: 1h
    annotations:
      summary: "SLA breach: Uptime < 99.99%"
```

**Acceptance Criteria:**
- ✅ Multi-Region Deployment (EU + US)
- ✅ Automatic Failover <30 Sekunden
- ✅ Disaster Recovery funktioniert (RPO <1h, RTO <15min)
- ✅ Chaos Engineering läuft täglich
- ✅ 99.99% Uptime SLA erreicht (gemessen über 30 Tage)
- ✅ Incident Response Runbook komplett

---

## 8. Migration & Rollout Plan

### 8.1 Phase A: Stabilization (Wochen 1-4)

**Woche 1: Security Hardening**
- ✅ Tag 1-2: Secrets Management (Vault Installation + Migration)
- ✅ Tag 3: PostgreSQL Replication Setup (Primary + Standby)
- ✅ Tag 4-5: WAF Deployment (ModSecurity + OWASP CRS)

**Woche 2: Scalability Foundations**
- ✅ Tag 1: PostgreSQL Connection Pool Tuning
- ✅ Tag 2-3: Mission Worker Pool (5 concurrent workers)
- ✅ Tag 4: EventStream Dual-Write Enforcement
- ✅ Tag 5: Dependency Version Pinning (Backend + Frontend)

**Woche 3: Observability & Testing**
- ✅ Tag 1-2: Frontend Testing Setup (Jest + Playwright)
- ✅ Tag 3: Load Testing Framework (k6)
- ✅ Tag 4: Governor Decision Caching
- ✅ Tag 5: Run Load Tests + Optimize

**Woche 4: Cleanup & Documentation**
- ✅ Tag 1: Remove Dual Mission System
- ✅ Tag 2: Complete IR Governance Stubs
- ✅ Tag 3-4: Resolve Critical TODOs (Security)
- ✅ Tag 5: Update CLAUDE.md (46 Modules, 17 Agents)

**Deliverable:** Production-ready BRAiN v2.0 (75% → 95%)

---

### 8.2 Phase B: Automation (Wochen 5-12)

**Woche 5-8: Modular Profiles**
- ✅ Woche 5: Profile System Implementation
- ✅ Woche 6: Profile Testing (minimal, standard, full)
- ✅ Woche 7: Profile Documentation
- ✅ Woche 8: Profile Deployment (all environments)

**Woche 9-12: Phase 2 Enforcement**
- ✅ Woche 9: Canary 10% (Timeout Enforcement)
- ✅ Woche 10: Canary 50% (Timeout Enforcement)
- ✅ Woche 11: Canary 50% + Budget Enforcement
- ✅ Woche 12: Full Rollout 100% + Reflex System

**Deliverable:** BRAiN v2.1 mit Modular Profiles + Phase 2 Enforcement

---

### 8.3 Phase C: Enterprise (Wochen 13-24)

**Woche 13-16: Multi-Tenancy**
- ✅ Woche 13: Tenant Isolation (RLS)
- ✅ Woche 14: Tenant Management UI
- ✅ Woche 15: Tenant Billing/Metering
- ✅ Woche 16: Security Testing (Penetration Test)

**Woche 17-20: Compliance**
- ✅ Woche 17: SOC 2 Evidence Collection
- ✅ Woche 18: ISO 27001 Assessment
- ✅ Woche 19: GDPR Automation (Data Deletion)
- ✅ Woche 20: External Audit Preparation

**Woche 21-24: High Availability**
- ✅ Woche 21: Multi-Region Setup (EU + US)
- ✅ Woche 22: Disaster Recovery Testing
- ✅ Woche 23: Chaos Engineering
- ✅ Woche 24: 99.99% Uptime Certification

**Deliverable:** BRAiN v3.0 Enterprise (100% production-ready)

---

## 9. Acceptance Criteria (Gesamt)

### 9.1 Security

- ✅ Zero Critical Vulnerabilities (OWASP Top 10)
- ✅ Secrets Management (Vault) aktiv
- ✅ WAF (ModSecurity) deployed
- ✅ PostgreSQL Replication (HA)
- ✅ Redis Cluster (HA)
- ✅ Encrypted Data at Rest (pgcrypto)
- ✅ mTLS zwischen Services (Sovereign Mode)
- ✅ Rate Limiting (3-Tier: Global, Endpoint, User)

### 9.2 Performance

- ✅ P95 Latency <150ms (Full Profile)
- ✅ Throughput >150 missions/min (Worker Pool)
- ✅ Governor Decision Cache Hit Rate >90%
- ✅ PostgreSQL Connection Pool: 20+10 (keine Exhaustion)
- ✅ Redis Cluster: 50K concurrent missions (5x capacity)

### 9.3 Scalability

- ✅ Horizontal Scaling (2+ Backend Pods)
- ✅ Load Balancer (Nginx Round Robin)
- ✅ Auto-Scaling (CPU >70% → scale up)
- ✅ Graceful Shutdown (keine Connection Loss)

### 9.4 Testing

- ✅ Backend Test Coverage: 70%+ (kritische Pfade)
- ✅ Frontend Test Coverage: 60%+ (kritische Pfade)
- ✅ E2E Tests: 5-10 Szenarien (Playwright)
- ✅ Load Tests: P95 <500ms bei 100 users
- ✅ Chaos Engineering: Tägliche Failure Injection

### 9.5 Code Quality

- ✅ Zero NotImplementedError in Production Code
- ✅ <20 TODO Markers (nur non-critical)
- ✅ All Dependencies Pinned (Backend + Frontend)
- ✅ No `--legacy-peer-deps` in Frontend
- ✅ Linting Passes (pylint, eslint)

### 9.6 Documentation

- ✅ CLAUDE.md Updated (46 Modules, 17 Agents)
- ✅ API Documentation (OpenAPI Spec)
- ✅ Deployment Runbooks (HA, DR, Chaos)
- ✅ Compliance Documentation (SOC 2, ISO 27001, GDPR)
- ✅ User Guides (Minimal, Standard, Full, Enterprise Profiles)

### 9.7 Compliance

- ✅ SOC 2 Type II Ready
- ✅ ISO 27001 Compliant
- ✅ GDPR Data Deletion Automation
- ✅ Consent Management funktional
- ✅ DPA Templates generiert

### 9.8 High Availability

- ✅ 99.99% Uptime SLA (gemessen über 30 Tage)
- ✅ Multi-Region Deployment (Active-Active)
- ✅ Automatic Failover <30 Sekunden
- ✅ RPO <1 Stunde, RTO <15 Minuten
- ✅ Disaster Recovery Tested (monatlich)

---

## 10. Success Metrics (KPIs)

### 10.1 Technical Metrics

| Metric | IST | SOLL | Phase |
|--------|-----|------|-------|
| **P95 Latency** | ~200ms | <150ms | A |
| **Throughput** | ~30 missions/min | >150 missions/min | A |
| **Error Rate** | ~5% | <1% | A |
| **Uptime** | ~95% | 99.99% | C |
| **Test Coverage** | ~60% backend, 0% frontend | 70% backend, 60% frontend | A |
| **Security Vulns** | 3 Critical | 0 Critical | A |
| **TODO Markers** | 125+ | <20 | A |

### 10.2 Business Metrics

| Metric | Target | Phase |
|--------|--------|-------|
| **Time to Production** | 6 Monate | C |
| **Development Cost** | Budget-neutral (internal) | - |
| **Operational Cost** | +30% (HA/DR) | C |
| **Customer SLA** | 99.99% uptime | C |
| **Compliance Certifications** | SOC 2, ISO 27001 | C |
| **Multi-Tenancy Revenue** | Billable per tenant | C |

---

## 11. Risks & Mitigation

### 11.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Phase 2 Breaking Changes** | Medium | High | Canary Deployment (10% → 50% → 100%) |
| **PostgreSQL Replication Issues** | Low | Critical | Test Failover weekly, Barman backups |
| **Redis Cluster Split-Brain** | Low | High | Use Redis Sentinel, Monitor cluster health |
| **Chaos Test False Positives** | Medium | Medium | Manual review before alerts |
| **External Audit Fails** | Low | High | Pre-audit internal assessment |

### 11.2 Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Team Capacity** | Medium | High | Prioritize Phase A, defer Phase C features |
| **Budget Overrun** | Low | Medium | Use open-source tools (Vault, Prometheus) |
| **Downtime During Migration** | Medium | High | Blue-Green Deployment, Rollback plan |
| **Compliance Audit Delay** | Low | Medium | Start early (Woche 17), continuous monitoring |

---

## 12. Zusammenfassung

### 12.1 SOLL-Zustand in Zahlen

| Aspekt | IST | SOLL | Verbesserung |
|--------|-----|------|--------------|
| **Production Readiness** | 75% | 100% | +25% |
| **Security Gaps** | 3 Critical | 0 Critical | -100% |
| **Uptime** | 95% | 99.99% | +5% |
| **P95 Latency** | 200ms | <150ms | -25% |
| **Throughput** | 30/min | 150/min | +400% |
| **Test Coverage** | 60% | 70% | +10% |
| **Frontend Tests** | 0% | 60% | +60% |
| **TODO Markers** | 125+ | <20 | -84% |
| **NotImplementedError** | 8 | 0 | -100% |

### 12.2 Timeline

**Phase A (Woche 1-4):** Stabilization → 95% Production-Ready
**Phase B (Woche 5-12):** Automation → Modular Profiles + Phase 2
**Phase C (Woche 13-24):** Enterprise → 100% Production-Ready + Compliance

**Gesamt:** 6 Monate (24 Wochen)

### 12.3 Investment

**Zeit:** 6 Monate Full-Time (1-2 Senior Engineers)
**Infrastruktur:** +30% Operational Cost (HA/DR/Multi-Region)
**Tools:** Open-Source (Vault, Prometheus, k6, Barman)

**ROI:** Enterprise-grade Platform mit SOC 2, 99.99% uptime, Multi-Tenancy Revenue

---

**Ende SOLL-Zustand Dokumentation**

**Erstellt:** 2026-02-03
**Basis:** IST_ZUSTAND_2026-02-03.md
**Zweck:** Roadmap für Production-Ready Enterprise Platform

**Nächster Schritt:** Phase A Kick-off (Woche 1, Tag 1: Secrets Management)
