## BRAiN Cluster System

**Version:** 0.1.0
**Status:** 🔧 In Development (Phase 3)

Dynamic Multi-Agent Cluster Management with Blueprint-based creation, auto-scaling, and lifecycle management based on the **Myzel-Prinzip** (organic growth pattern).

---

## 🎯 Overview

The Cluster System enables BRAiN to dynamically create, scale, and manage groups of agents working together on complex tasks. Clusters can represent:
- **Departments** (Marketing, Einkauf, HR)
- **Projects** (Campaign-specific teams)
- **Temporary** task forces
- **Persistent** always-on services

### Key Features

- ✅ **Blueprint-based Creation**: YAML templates define cluster structure
- ✅ **Hierarchical Agents**: Supervisor → Lead → Specialist → Worker
- ✅ **Auto-Scaling**: Grows/shrinks based on load
- ✅ **Lifecycle Management**: Create → Scale → Hibernate → Destroy
- ✅ **Metrics & Monitoring**: Real-time performance tracking
- ✅ **Resource Sharing**: Shared memory and knowledge bases

---

## 📂 Module Structure

```
cluster_system/
├── __init__.py             # Module initialization
├── models.py               # SQLAlchemy models (4 tables)
├── schemas.py              # Pydantic request/response schemas
├── service.py              # Business logic layer
├── router.py               # FastAPI endpoints
│
├── blueprints/             # Blueprint System
│   ├── loader.py           # YAML loading
│   └── validator.py        # Schema validation
│
├── creator/                # Cluster Creation
│   ├── planner.py          # AI-based planning
│   ├── spawner.py          # Agent spawning
│   └── configurator.py     # Config generation
│
├── manager/                # Lifecycle Management
│   ├── lifecycle.py        # State transitions
│   ├── health.py           # Health monitoring
│   └── scaler.py           # Auto-scaling logic
│
└── manifests/              # Documentation Generation
    ├── generator.py        # .md manifest creation
    ├── parser.py           # Manifest parsing
    └── templates/          # Manifest templates
```

---

## 🗄️ Database Schema

### Tables

1. **clusters** - Main cluster entities
2. **cluster_agents** - Agents within clusters
3. **cluster_blueprints** - Reusable templates
4. **cluster_metrics** - Time-series metrics

### Entity Relationships

```
ClusterBlueprint (1) ──< (N) Cluster
Cluster (1) ──< (N) ClusterAgent
Cluster (1) ──< (N) ClusterMetrics
ClusterAgent (1) ──< (N) ClusterAgent  (hierarchy)
```

---

## 🚀 Quick Start

### 1. Create Cluster from Blueprint

```python
from app.modules.cluster_system.service import ClusterService
from app.modules.cluster_system.schemas import ClusterCreate

service = ClusterService(db_session)

cluster = await service.create_from_blueprint(
    ClusterCreate(
        blueprint_id="marketing-v1",
        name="Marketing Q1 2024",
        type="department",
        target_workers=5
    )
)

print(f"Cluster created: {cluster.id}")
print(f"Status: {cluster.status}")
print(f"Workers: {cluster.current_workers}/{cluster.max_workers}")
```

### 2. Scale Cluster

```python
from app.modules.cluster_system.schemas import ClusterScale

await service.scale_cluster(
    cluster_id=cluster.id,
    data=ClusterScale(target_workers=10)
)
```

### 3. Get Cluster Hierarchy

```python
hierarchy = await service.get_cluster_hierarchy(cluster.id)

print(f"Supervisor: {hierarchy.agent.agent_id}")
for sub in hierarchy.subordinates:
    print(f"  └─ {sub.agent.role}: {sub.agent.agent_id}")
```

---

## 📋 API Endpoints

### Cluster Management

```
POST   /api/clusters                Create from blueprint
GET    /api/clusters                List all clusters
GET    /api/clusters/{id}           Get cluster details
PUT    /api/clusters/{id}           Update configuration
DELETE /api/clusters/{id}           Soft delete
```

### Scaling Operations

```
POST   /api/clusters/{id}/scale     Manual scaling
POST   /api/clusters/{id}/hibernate Pause cluster
POST   /api/clusters/{id}/reactivate Wake up cluster
```

### Agent Management

```
GET    /api/clusters/{id}/agents    List agents
GET    /api/clusters/{id}/hierarchy Get hierarchy tree
POST   /api/clusters/{id}/agents    Add agent (manual)
```

### Blueprints

```
POST   /api/blueprints              Upload new blueprint
GET    /api/blueprints              List all blueprints
GET    /api/blueprints/{id}         Get blueprint details
```

---

## 📄 Blueprint Format

Blueprints are YAML files defining cluster structure:

```yaml
metadata:
  id: marketing-v1
  name: Marketing Department
  version: 1.0.0

cluster:
  type: department
  min_workers: 3
  max_workers: 20

  scaling:
    metric: task_queue_length
    scale_up_threshold: 10
    scale_down_threshold: 2

agents:
  - role: supervisor
    name: Marketing Supervisor
    count: 1
    capabilities: [strategy, coordination]

  - role: worker
    name: Content Creator
    count: 0-5  # Dynamic
    reports_to: supervisor
    capabilities: [copywriting, content_creation]
```

**Example Blueprints:**
- `storage/blueprints/marketing.yaml` - Marketing department
- `storage/blueprints/einkauf.yaml` - Procurement team
- `storage/blueprints/project-template.yaml` - Generic project

---

## 🔄 Lifecycle States

```
PLANNING → SPAWNING → ACTIVE ⟷ SCALING_UP
                       ↓            ↓
                   SCALING_DOWN → HIBERNATED
                       ↓
                   DESTROYING → DESTROYED
```

### State Transitions

- **PLANNING** → **SPAWNING**: Blueprint validated, agents being created
- **SPAWNING** → **ACTIVE**: All agents spawned successfully
- **ACTIVE** → **SCALING_UP**: Load > threshold, adding workers
- **SCALING_UP** → **ACTIVE**: Target workers reached
- **ACTIVE** → **SCALING_DOWN**: Load < threshold, removing workers
- **ACTIVE** → **HIBERNATED**: Idle timeout reached, all workers stopped
- **HIBERNATED** → **ACTIVE**: Reactivation triggered
- **ACTIVE** → **DESTROYING**: Delete requested
- **DESTROYING** → **DESTROYED**: All agents stopped, data archived

---

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://...

# Auto-Scaling
CLUSTER_AUTO_SCALE_ENABLED=true
CLUSTER_AUTO_SCALE_INTERVAL=60  # seconds
CLUSTER_MAX_CLUSTERS=50

# Hibernation
CLUSTER_IDLE_TIMEOUT=3600  # 1 hour
CLUSTER_HIBERNATION_ENABLED=true

# Blueprints
CLUSTER_BLUEPRINTS_DIR=storage/blueprints
```

---

## 🧪 Testing

```bash
# Run tests
pytest tests/modules/cluster_system/

# Test coverage
pytest --cov=app.modules.cluster_system --cov-report=html

# Integration tests
pytest tests/integration/test_cluster_lifecycle.py
```

---

## 📊 Monitoring

### Metrics Collected

- **Resource Usage**: CPU, Memory per cluster
- **Performance**: Tasks/min, avg response time, error rate
- **Agent Health**: Active, idle, busy, failed counts
- **Queue Metrics**: Queue length, wait time

### Auto-Scaling Triggers

```python
# Scale UP if:
- queue_length > scale_up_threshold
- load_percentage > 80%
- avg_response_time > 5s

# Scale DOWN if:
- queue_length < scale_down_threshold
- load_percentage < 20%
- idle_agents > 50%
```

---

## 🔐 Security

### Authentication

All endpoints require authentication (JWT):

```python
@router.post("/clusters")
async def create_cluster(
    principal: Principal = Depends(get_current_principal)
):
    # Only authenticated users
```

### Role-Based Access

- **VIEWER**: Read-only access
- **OPERATOR**: Create, scale, hibernate clusters
- **ADMIN**: Delete clusters, manage blueprints

---

## 🐛 Troubleshooting

### Cluster stuck in SPAWNING

```python
# Check agent creation logs
cluster = await service.get_cluster(cluster_id)
print(f"Current workers: {cluster.current_workers}/{cluster.target_workers}")

# Manually set to ACTIVE if needed (debug only)
cluster.status = ClusterStatus.ACTIVE
await db.commit()
```

### Auto-scaling not working

```bash
# Check scaler service is running
docker logs brain-worker | grep "auto-scaling"

# Verify metrics are being collected
curl /api/clusters/{id}/metrics
```

### High error rate

```python
# Get recent metrics
metrics = await service.get_metrics(
    cluster_id,
    start_time=datetime.now() - timedelta(hours=1)
)

for m in metrics:
    print(f"{m.timestamp}: {m.error_rate}% errors")
```

---

## 📚 Related Modules

- **Genesis** - Agent creation and blueprints
- **Skills** - Agent capabilities
- **Memory** - Shared cluster memory
- **Missions** - Task orchestration
- **Fleet** - Multi-cluster coordination

---

## 🛠️ Development Status

### ✅ Completed
- Database models
- Pydantic schemas
- API router skeleton
- Service method stubs
- Blueprint example (marketing.yaml)

### 🔧 In Progress (Max's Tasks)
- [ ] Task 3.1: Database migration
- [ ] Task 3.2: Blueprint loader/validator
- [ ] Task 3.3: Cluster creator service
- [ ] Task 3.4: API endpoint implementation

### ⏳ TODO
- [ ] Auto-scaling implementation
- [ ] Manifest generation
- [ ] Integration with Genesis
- [ ] Worker pool integration (Phase 4)
- [ ] Unit tests (80% coverage)
- [ ] Integration tests

---

## 📖 References

- **Blueprint Schema**: See `storage/blueprints/marketing.yaml`
- **API Docs**: `/api/docs` (OpenAPI/Swagger)
- **Database Schema**: `alembic/versions/cluster_system_*.py`
- **Roadmap**: `docs/ROADMAP_PHASE3_PHASE4.md`

---

**Last Updated:** 2024-02-17
**Maintainer:** BRAiN Core Team
**License:** MIT
