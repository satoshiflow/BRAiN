# BRAiN Roadmap: Phase 3 + 4 - Dynamic Multi-Cluster System

**Verantwortlich:** Claude (Senior Developer)
**Support:** Max (Junior Developer) führt Implementierung aus
**Geschätzte Zeit:** 6-8 Stunden Development
**Status:** 🔧 In Planning

---

## 🎯 VISION

**Selbst-organisierende Agent-Cluster**, die von BRAiN dynamisch erstellt, skaliert und verwaltet werden:

```
Marketing Campaign erkannt
     ↓
BRAiN plant Cluster
     ↓
Cluster Blueprint erstellt (YAML + .md Manifest)
     ↓
Cluster spawned (Supervisor + 5 Workers)
     ↓
Task ausgeführt
     ↓
Cluster skaliert (10 Workers bei hoher Last)
     ↓
Task fertig
     ↓
Cluster schrumpft (3 Workers)
     ↓
Cluster hiberniert (0 Workers, Blueprint bleibt)
     ↓
Cluster destroyed (wenn nicht mehr gebraucht)
```

---

## 📊 ARCHITEKTUR-ÜBERBLICK

### Myzel-Prinzip (Organisches Wachstum)

```
┌─────────────────────────────────────────────────────────┐
│                    BRAiN Core                           │
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │         Cluster Orchestrator                  │    │
│  │  - Bedarf erkennen                            │    │
│  │  - Blueprint planen                           │    │
│  │  - Cluster spawnen                            │    │
│  │  - Scaling entscheiden                        │    │
│  └───────────────┬───────────────────────────────┘    │
│                  │                                      │
│  ┌───────────────▼───────────────────────────────┐    │
│  │         Cluster Manager                       │    │
│  │  - Lifecycle (create/scale/destroy)           │    │
│  │  - Health Monitoring                          │    │
│  │  - Resource Allocation                        │    │
│  └───────────────┬───────────────────────────────┘    │
│                  │                                      │
└──────────────────┼──────────────────────────────────────┘
                   │
    ┌──────────────┴──────────────┐
    │                             │
┌───▼────────────┐      ┌─────────▼─────────┐
│ Marketing      │      │ Einkauf           │
│ Cluster        │      │ Cluster           │
│                │      │                   │
│ Supervisor ────┤      │ Supervisor ────   │
│   ├─ Analyst   │      │   ├─ Supplier     │
│   ├─ Creator   │      │   ├─ Pricer       │
│   │   ├─ Image │      │   └─ Orderer      │
│   │   └─ Video │      │                   │
│   └─ Publisher │      │ Workers: 3/10     │
│       ├─ FB    │      │ Status: Active    │
│       ├─ Insta │      │ Load: 45%         │
│       └─ LI    │      └───────────────────┘
│                │
│ Workers: 8/20  │      ┌───────────────────┐
│ Status: Scaling│      │ Project-X         │
│ Load: 87%      │      │ Cluster           │
└────────────────┘      │                   │
                        │ Status: Hibernated│
                        │ Workers: 0/5      │
                        └───────────────────┘
```

---

## 📂 PHASE 3: Cluster Creator System

### **Ziel:** Blueprint-basierte Cluster-Erstellung

---

### 3.1 Module Structure (Claude erstellt)

```
backend/app/modules/cluster_system/
├── __init__.py
├── README.md
│
├── blueprints/                    # Cluster-Templates
│   ├── base.py                    # Base Blueprint Class
│   ├── loader.py                  # YAML Blueprint Loader
│   └── validator.py               # Blueprint Validation
│
├── creator/                       # Cluster Creation
│   ├── planner.py                 # AI-basierte Cluster-Planung
│   ├── spawner.py                 # Agent Spawning aus Blueprint
│   └── configurator.py            # Cluster Config Generation
│
├── manager/                       # Cluster Lifecycle
│   ├── lifecycle.py               # Create/Scale/Destroy
│   ├── health.py                  # Health Monitoring
│   └── scaler.py                  # Auto-Scaling Logic
│
├── manifests/                     # Manifest System
│   ├── generator.py               # .md Manifest Generator
│   ├── parser.py                  # Manifest Parser
│   └── templates/                 # Manifest Templates
│       ├── README.template.md
│       ├── skills.template.md
│       └── memory.template.md
│
├── models.py                      # SQLAlchemy Models
├── schemas.py                     # Pydantic Schemas
├── service.py                     # Business Logic
└── router.py                      # FastAPI Endpoints
```

---

### 3.2 Data Models (Claude erstellt)

**File:** `backend/app/modules/cluster_system/models.py`

```python
from sqlalchemy import Column, String, Integer, Float, ForeignKey, JSON, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import enum

class ClusterType(str, enum.Enum):
    DEPARTMENT = "department"      # Marketing, Einkauf
    PROJECT = "project"            # Projekt-spezifisch
    TEMPORARY = "temporary"        # Einmalige Tasks
    PERSISTENT = "persistent"      # Langlebig

class ClusterStatus(str, enum.Enum):
    PLANNING = "planning"          # Blueprint wird erstellt
    SPAWNING = "spawning"          # Agents werden spawned
    ACTIVE = "active"              # Läuft normal
    SCALING_UP = "scaling_up"      # Wächst
    SCALING_DOWN = "scaling_down"  # Schrumpft
    HIBERNATED = "hibernated"      # 0 Workers, kann reaktiviert werden
    DESTROYING = "destroying"      # Wird abgebaut
    DESTROYED = "destroyed"        # Gelöscht

class AgentRole(str, enum.Enum):
    SUPERVISOR = "supervisor"      # 1 pro Cluster
    LEAD = "lead"                  # 0-N Team Leads
    SPECIALIST = "specialist"      # Fach-Agents
    WORKER = "worker"              # Task Executors

class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(Enum(ClusterType), nullable=False)
    status = Column(Enum(ClusterStatus), default=ClusterStatus.PLANNING)

    # Blueprint Reference
    blueprint_id = Column(String, nullable=False)  # z.B. "marketing-v1"
    blueprint_version = Column(String, default="1.0.0")

    # Hierarchy
    parent_cluster_id = Column(String, ForeignKey("clusters.id"), nullable=True)

    # Scaling Config
    min_workers = Column(Integer, default=1)
    max_workers = Column(Integer, default=10)
    current_workers = Column(Integer, default=0)
    target_workers = Column(Integer, default=1)

    # Health & Performance
    health_score = Column(Float, default=1.0)  # 0.0 - 1.0
    load_percentage = Column(Float, default=0.0)  # 0.0 - 100.0

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    hibernated_at = Column(DateTime, nullable=True)
    destroyed_at = Column(DateTime, nullable=True)

    # Metadata
    description = Column(String)
    tags = Column(JSON, default=list)  # ["marketing", "content"]
    config = Column(JSON, default=dict)  # Custom config

    # Relationships
    agents = relationship("ClusterAgent", back_populates="cluster", cascade="all, delete-orphan")
    parent = relationship("Cluster", remote_side=[id], backref="children")
    metrics = relationship("ClusterMetrics", back_populates="cluster")

class ClusterAgent(Base):
    __tablename__ = "cluster_agents"

    id = Column(String, primary_key=True)
    cluster_id = Column(String, ForeignKey("clusters.id"))

    # Agent Info
    agent_id = Column(String, nullable=False)  # Genesis Agent ID
    role = Column(Enum(AgentRole), nullable=False)

    # Hierarchy
    supervisor_id = Column(String, ForeignKey("cluster_agents.id"), nullable=True)

    # Capabilities
    capabilities = Column(JSON, default=list)  # ["image_gen", "video_edit"]
    skills = Column(JSON, default=list)  # Skill IDs

    # Status
    status = Column(String, default="active")  # active, idle, busy, failed
    health_score = Column(Float, default=1.0)

    # Performance
    tasks_completed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)
    avg_task_duration = Column(Float, default=0.0)  # seconds

    # Lifecycle
    spawned_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    # Relationships
    cluster = relationship("Cluster", back_populates="agents")
    supervisor = relationship("ClusterAgent", remote_side=[id], backref="subordinates")

class ClusterBlueprint(Base):
    __tablename__ = "cluster_blueprints"

    id = Column(String, primary_key=True)  # "marketing-v1"
    name = Column(String, nullable=False)
    version = Column(String, default="1.0.0")

    # Blueprint Content
    blueprint_yaml = Column(String, nullable=False)  # YAML content
    manifest_path = Column(String)  # Path to manifest files

    # Metadata
    description = Column(String)
    author = Column(String, default="brain-system")
    tags = Column(JSON, default=list)

    # Versioning
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Usage Stats
    instances_created = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

class ClusterMetrics(Base):
    __tablename__ = "cluster_metrics"

    id = Column(String, primary_key=True)
    cluster_id = Column(String, ForeignKey("clusters.id"))

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Resource Metrics
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)

    # Performance Metrics
    tasks_per_minute = Column(Float, default=0.0)
    avg_response_time = Column(Float, default=0.0)
    error_rate = Column(Float, default=0.0)

    # Agent Metrics
    active_agents = Column(Integer, default=0)
    idle_agents = Column(Integer, default=0)
    busy_agents = Column(Integer, default=0)

    # Relationships
    cluster = relationship("Cluster", back_populates="metrics")
```

---

### 3.3 Blueprint System (Claude erstellt)

**File:** `storage/blueprints/marketing.yaml`

```yaml
# BRAiN Cluster Blueprint: Marketing Department
metadata:
  id: marketing-v1
  name: Marketing Department
  version: 1.0.0
  author: brain-system
  description: Multi-agent cluster for marketing campaign execution
  tags: [marketing, content, social-media]

# Cluster Configuration
cluster:
  type: department
  min_workers: 3
  max_workers: 20
  default_workers: 5

  # Auto-scaling rules
  scaling:
    metric: task_queue_length
    scale_up_threshold: 10  # Tasks waiting
    scale_down_threshold: 2
    cooldown_period: 300  # 5 minutes

# Agent Hierarchy
agents:
  # Level 1: Supervisor (Abteilungsleiter)
  - role: supervisor
    name: Marketing Supervisor
    count: 1
    capabilities:
      - strategy_planning
      - team_coordination
      - budget_management
      - campaign_oversight
    skills:
      - strategic_thinking
      - delegation
      - reporting
    config:
      llm_model: qwen2.5:0.5b
      temperature: 0.7
      max_tokens: 2000

  # Level 2: Specialists
  - role: specialist
    name: Market Analyst
    count: 1
    reports_to: supervisor
    capabilities:
      - market_research
      - competitor_analysis
      - trend_analysis
      - data_analysis
    skills:
      - web_scraping
      - data_processing
      - report_generation

  - role: specialist
    name: Content Creator
    count: 1
    reports_to: supervisor
    capabilities:
      - copywriting
      - content_planning
      - brand_voice
    skills:
      - text_generation
      - content_optimization

  - role: specialist
    name: Publishing Coordinator
    count: 1
    reports_to: supervisor
    capabilities:
      - social_media_management
      - scheduling
      - cross_platform_publishing
    skills:
      - social_media_apis
      - scheduling_tools

  # Level 3: Workers (spawned on demand)
  - role: worker
    name: Image Generator
    count: 0-5  # Dynamic
    reports_to: Content Creator
    capabilities:
      - image_generation
      - image_editing
    skills:
      - stable_diffusion
      - image_processing

  - role: worker
    name: Video Creator
    count: 0-3
    reports_to: Content Creator
    capabilities:
      - video_editing
      - animation
    skills:
      - video_processing
      - ffmpeg

  - role: worker
    name: Facebook Publisher
    count: 0-2
    reports_to: Publishing Coordinator
    capabilities:
      - facebook_api
      - post_scheduling
    skills:
      - facebook_graph_api
      - content_formatting

  - role: worker
    name: Instagram Publisher
    count: 0-2
    reports_to: Publishing Coordinator
    capabilities:
      - instagram_api
      - story_creation
    skills:
      - instagram_graph_api
      - image_optimization

  - role: worker
    name: LinkedIn Publisher
    count: 0-2
    reports_to: Publishing Coordinator
    capabilities:
      - linkedin_api
      - professional_content
    skills:
      - linkedin_api
      - b2b_content

# Shared Resources
resources:
  memory:
    type: shared
    size: 10GB
    retention: 30 days

  knowledge_base:
    collections:
      - brand_guidelines
      - content_templates
      - campaign_history

  tools:
    - web_browser
    - image_editor
    - video_editor
    - social_media_scheduler

# Lifecycle Rules
lifecycle:
  # Wann hibernieren?
  hibernate_conditions:
    - idle_time: 1 hour
    - task_queue_empty: true
    - load_below: 10%

  # Wann destroyen?
  destroy_conditions:
    - hibernated_duration: 7 days
    - manual_trigger: true

  # Wann reaktivieren?
  reactivate_triggers:
    - new_task_received
    - manual_trigger
    - scheduled_campaign

# Monitoring
monitoring:
  metrics:
    - task_completion_rate
    - average_response_time
    - error_rate
    - resource_utilization

  alerts:
    - condition: error_rate > 10%
      action: notify_admin
    - condition: load > 90%
      action: scale_up
    - condition: worker_failure > 3
      action: spawn_replacement
```

---

### 3.4 Manifest Templates (Claude erstellt)

**File:** `storage/manifests/templates/README.template.md`

```markdown
# {{cluster_name}} Cluster

**Type:** {{cluster_type}}
**Status:** {{cluster_status}}
**Created:** {{created_at}}
**Blueprint:** {{blueprint_id}} v{{blueprint_version}}

---

## Overview

{{description}}

---

## Current State

- **Workers:** {{current_workers}} / {{max_workers}}
- **Load:** {{load_percentage}}%
- **Health:** {{health_score * 100}}%
- **Tasks Completed:** {{tasks_completed}}
- **Uptime:** {{uptime}}

---

## Agent Hierarchy

{{agent_hierarchy}}

---

## Capabilities

{{capabilities_list}}

---

## Recent Activity

{{recent_activity}}

---

## Metrics

{{metrics_summary}}
```

**File:** `storage/manifests/templates/skills.template.md`

```markdown
# {{cluster_name}} - Skills & Capabilities

## Required Skills

{{#each required_skills}}
### {{this.name}}
- **Category:** {{this.category}}
- **Agents:** {{this.agent_count}}
- **Usage:** {{this.usage_percentage}}%
{{/each}}

---

## Skill Distribution

{{skill_distribution_table}}

---

## Missing Skills

{{#each missing_skills}}
- **{{this.name}}**: {{this.reason}}
{{/each}}
```

---

## 📂 PHASE 4: Worker Pool System

### **Ziel:** Horizontal skalierbare Workers für Cluster

---

### 4.1 Worker Service Structure (Claude erstellt)

```
backend/
├── worker.py                      # Main Worker Entry
├── Dockerfile.worker              # Worker Container Build
│
└── app/workers/
    ├── __init__.py
    ├── base_worker.py             # Base Worker Class
    ├── cluster_worker.py          # Cluster Task Worker
    ├── mission_worker.py          # Mission Worker (existing)
    │
    ├── handlers/                  # Task Handlers
    │   ├── llm_task.py
    │   ├── skill_task.py
    │   ├── agent_task.py
    │   └── cluster_task.py
    │
    └── utils/
        ├── queue.py               # Redis Queue Utils
        ├── health.py              # Worker Health Check
        └── metrics.py             # Worker Metrics
```

---

### 4.2 Worker Implementation (Max implementiert)

**File:** `backend/worker.py` (Claude erstellt Grundstruktur)

```python
"""
BRAiN Worker Service
Horizontal skalierbare Worker für Cluster-Tasks
"""

import asyncio
import signal
import sys
from loguru import logger
from app.core.config import settings
from app.workers.cluster_worker import ClusterWorker

# Graceful Shutdown Handler
shutdown_event = asyncio.Event()

def signal_handler(sig, frame):
    logger.warning(f"Received signal {sig}, initiating graceful shutdown...")
    shutdown_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def main():
    logger.info("🚀 Starting BRAiN Worker...")
    logger.info(f"Worker ID: {settings.worker_id}")
    logger.info(f"Concurrency: {settings.worker_concurrency}")
    logger.info(f"Redis: {settings.redis_url}")

    # Initialize Worker
    worker = ClusterWorker(
        worker_id=settings.worker_id,
        concurrency=settings.worker_concurrency
    )

    try:
        # Start Worker
        await worker.start()

        # Run until shutdown signal
        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Worker crashed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Graceful Shutdown
        logger.info("Shutting down worker...")
        await worker.stop()
        logger.info("Worker stopped gracefully")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        sys.exit(0)
```

---

### 4.3 Docker Compose Integration (Max implementiert)

**File:** `docker-compose.prod.yml` (Claude gibt Vorlage)

```yaml
services:
  # Existing services...

  # NEW: Worker Pool
  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.worker
    image: brain-worker:latest

    command: python worker.py

    environment:
      # Database
      - DATABASE_URL=${DATABASE_URL}

      # Redis
      - REDIS_URL=redis://redis:6379/0

      # LLM
      - OLLAMA_HOST=http://ollama:11434
      - OLLAMA_MODEL=qwen2.5:0.5b

      # Worker Config
      - WORKER_ID=${HOSTNAME}  # Auto-generated
      - WORKER_CONCURRENCY=2
      - WORKER_QUEUE=cluster_tasks

      # Qdrant
      - QDRANT_URL=http://qdrant:6333

    depends_on:
      - postgres
      - redis
      - ollama
      - qdrant

    networks:
      - brain_network

    # Horizontal Scaling
    deploy:
      replicas: 3  # Start with 3 workers

      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G

      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

    # Health Check
    healthcheck:
      test: ["CMD", "python", "-c", "import redis; r=redis.Redis(host='redis'); r.ping()"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  brain_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  ollama_data:
  qdrant_data:
```

---

### 4.4 Coolify Deployment (Max setzt um)

**Coolify Service Config:**

```yaml
# In Coolify: New Service → Docker Compose

Service Name: brain-workers
Type: Docker Compose Service
Network: brain-network

# Scaling
Replicas: 3  # Start
Min Replicas: 1
Max Replicas: 20
Auto-scale: Enabled
  - Metric: CPU
  - Threshold: 70%
  - Scale Up: +2 replicas
  - Scale Down: -1 replica
  - Cooldown: 5 minutes

# Environment
[Same as docker-compose.prod.yml]

# Monitoring
Health Check: Enabled
Metrics: Prometheus
Logs: Loki
```

---

## 🎯 MAX'S TASKS (Konkret)

### **Task 3.1: Cluster System Database Models** ⏱️ 30 Min

**Was:** SQLAlchemy Models erstellen

**Files:**
```bash
backend/app/modules/cluster_system/models.py
```

**Vorlage:** Siehe Section 3.2 (oben)

**Acceptance:**
- [ ] 4 Models: Cluster, ClusterAgent, ClusterBlueprint, ClusterMetrics
- [ ] Alle Enums definiert
- [ ] Relationships korrekt
- [ ] Migration erstellt: `alembic revision --autogenerate -m "cluster_system"`

---

### **Task 3.2: Blueprint Loader** ⏱️ 45 Min

**Was:** YAML Blueprint laden und validieren

**Files:**
```bash
backend/app/modules/cluster_system/blueprints/loader.py
backend/app/modules/cluster_system/blueprints/validator.py
```

**Functionality:**
```python
class BlueprintLoader:
    def load_from_file(self, path: str) -> Blueprint
    def load_from_string(self, yaml_content: str) -> Blueprint
    def save_to_db(self, blueprint: Blueprint) -> ClusterBlueprint

class BlueprintValidator:
    def validate_schema(self, blueprint: dict) -> bool
    def validate_agents(self, agents: list) -> bool
    def validate_scaling(self, scaling: dict) -> bool
```

**Acceptance:**
- [ ] YAML parsing funktioniert
- [ ] Validation wirft Fehler bei invaliden Blueprints
- [ ] Blueprint kann in DB gespeichert werden

---

### **Task 3.3: Cluster Creator Service** ⏱️ 1.5 Stunden

**Was:** Cluster aus Blueprint erstellen

**Files:**
```bash
backend/app/modules/cluster_system/creator/spawner.py
backend/app/modules/cluster_system/service.py
```

**Functionality:**
```python
class ClusterService:
    async def create_from_blueprint(
        self,
        blueprint_id: str,
        name: str,
        config_overrides: dict = None
    ) -> Cluster:
        # 1. Load Blueprint
        # 2. Create Cluster DB entry
        # 3. Spawn Supervisor Agent
        # 4. Spawn initial Workers
        # 5. Create Manifest files
        # 6. Return Cluster
        pass
```

**Acceptance:**
- [ ] Blueprint → Cluster Conversion funktioniert
- [ ] Agents werden via Genesis spawned
- [ ] Hierarchy wird korrekt erstellt
- [ ] Manifests werden generiert

---

### **Task 3.4: Cluster API Endpoints** ⏱️ 1 Stunde

**Was:** FastAPI Endpoints für Cluster Management

**Files:**
```bash
backend/app/modules/cluster_system/router.py
```

**Endpoints:**
```python
POST   /api/clusters                        # Create from blueprint
GET    /api/clusters                        # List all
GET    /api/clusters/{id}                   # Get details
PUT    /api/clusters/{id}/scale             # Manual scaling
POST   /api/clusters/{id}/hibernate         # Hibernate
POST   /api/clusters/{id}/reactivate        # Wake up
DELETE /api/clusters/{id}                   # Destroy

GET    /api/blueprints                      # List blueprints
POST   /api/blueprints                      # Upload new blueprint
GET    /api/blueprints/{id}                 # Get blueprint
```

**Acceptance:**
- [ ] Alle Endpoints implementiert
- [ ] Authentication required
- [ ] Pydantic Schemas für Request/Response
- [ ] OpenAPI Docs korrekt

---

### **Task 4.1: Base Worker Implementation** ⏱️ 1 Stunde

**Was:** Base Worker Class mit Redis Queue

**Files:**
```bash
backend/app/workers/base_worker.py
backend/app/workers/utils/queue.py
```

**Functionality:**
```python
class BaseWorker:
    def __init__(self, worker_id: str, concurrency: int)
    async def start(self)
    async def stop(self)
    async def process_task(self, task: dict) -> dict
    async def heartbeat(self)
```

**Acceptance:**
- [ ] Worker kann Tasks aus Redis Queue ziehen
- [ ] Concurrency Limiting funktioniert
- [ ] Graceful Shutdown implementiert
- [ ] Heartbeat an Redis

---

### **Task 4.2: Cluster Worker** ⏱️ 1.5 Stunden

**Was:** Spezialisierter Worker für Cluster Tasks

**Files:**
```bash
backend/app/workers/cluster_worker.py
backend/app/workers/handlers/cluster_task.py
```

**Task Types:**
```python
- spawn_agent
- scale_cluster
- delegate_task
- health_check
- collect_metrics
```

**Acceptance:**
- [ ] Kann Agents spawnen
- [ ] Kann Cluster skalieren
- [ ] Task Results zurück an Orchestrator
- [ ] Error Handling + Retry Logic

---

### **Task 4.3: Worker Dockerfile** ⏱️ 30 Min

**Was:** Separates Docker Image für Workers

**Files:**
```bash
backend/Dockerfile.worker
```

**Content:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker.py .
COPY app/ ./app/
COPY mission_control_core/ ./mission_control_core/
CMD ["python", "worker.py"]
```

**Acceptance:**
- [ ] Image baut ohne Fehler
- [ ] Kann gestartet werden
- [ ] Worker läuft und zieht Tasks

---

### **Task 4.4: Coolify Worker Deployment** ⏱️ 45 Min

**Was:** Worker Pool in Coolify deployen

**Steps:**
1. New Service → Docker Compose
2. Copy docker-compose.prod.yml worker section
3. Set Replicas: 3
4. Deploy
5. Test scaling (3 → 10 → 3)

**Acceptance:**
- [ ] 3 Worker Replicas laufen
- [ ] Health Checks passing
- [ ] Tasks werden verarbeitet
- [ ] Scaling funktioniert

---

## ✅ ACCEPTANCE CRITERIA (Gesamt)

### Phase 3: Cluster Creator
- [ ] Cluster können aus Blueprints erstellt werden
- [ ] Agent-Hierarchie funktioniert
- [ ] Manifests werden generiert
- [ ] API Endpoints funktional
- [ ] Tests schreiben: Unit + Integration

### Phase 4: Worker Pool
- [ ] 3+ Worker laufen parallel
- [ ] Tasks werden aus Queue gezogen
- [ ] Load Balancing funktioniert
- [ ] Scaling (3 → 10 → 3) getestet
- [ ] Graceful Shutdown funktioniert

---

## 🔍 CODE REVIEW CHECKLIST (Claude überprüft)

### Models
- [ ] Alle Required Fields haben Defaults
- [ ] Enums vollständig
- [ ] Relationships bidirektional
- [ ] Indexes auf häufig gesuchte Felder
- [ ] Migration funktioniert

### Services
- [ ] Async/Await korrekt verwendet
- [ ] Keine blocking I/O Calls
- [ ] Error Handling mit try/except
- [ ] Logging mit loguru
- [ ] Type Hints überall

### APIs
- [ ] Authentication Decorator vorhanden
- [ ] Input Validation (Pydantic)
- [ ] HTTP Status Codes korrekt
- [ ] Error Responses strukturiert
- [ ] Rate Limiting konfiguriert

### Worker
- [ ] Graceful Shutdown implementiert
- [ ] Heartbeat funktioniert
- [ ] Task Retries konfiguriert
- [ ] Dead Letter Queue für failed tasks
- [ ] Metrics Publishing

### Docker
- [ ] Multi-stage build für kleinere Images
- [ ] Non-root user
- [ ] Health checks definiert
- [ ] Resource limits gesetzt
- [ ] Logs zu stdout

---

## 📅 TIMELINE

```
Week 1:
├── Tag 1-2: Max - Phase 1+2 (Ollama/Qdrant Deployment)
├── Tag 3-4: Claude - Phase 3 Grundstruktur
└── Tag 5: Max - Task 3.1 + 3.2

Week 2:
├── Tag 1-2: Max - Task 3.3 + 3.4
├── Tag 3-4: Max - Task 4.1 + 4.2
└── Tag 5: Max - Task 4.3 + 4.4

Week 3:
├── Tag 1-2: Testing & Bug Fixes
├── Tag 3-4: Documentation
└── Tag 5: Production Deployment
```

**Gesamt: ~15 Arbeitstage** (mit Puffer)

---

**Status:** 📝 Ready for Implementation
