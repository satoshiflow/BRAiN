# BRAiN Worker Pool

**Version:** 0.1.0
**Status:** 🔧 In Development (Phase 4)

Horizontal scalable worker pool for async task processing with Redis queue backend.

---

## 🎯 Overview

The Worker Pool enables BRAiN to scale task processing horizontally by running multiple worker processes that pull tasks from Redis queues. Each worker can process multiple tasks concurrently.

### Key Features

- ✅ **Horizontal Scaling**: Run 1-100+ workers in parallel
- ✅ **Redis Queue**: FIFO task queue with blocking pop
- ✅ **Graceful Shutdown**: Waits for tasks to complete
- ✅ **Concurrency Control**: Semaphore-based limiting per worker
- ✅ **Heartbeat**: Workers send periodic heartbeats to Redis
- ✅ **Task Results**: Results published to Redis channel
- ✅ **Type-Based Routing**: Different workers for different task types

---

## 📂 Module Structure

```
backend/
├── worker.py                       # Main entry point
│
└── app/workers/
    ├── __init__.py
    ├── base_worker.py              # BaseWorker class
    ├── cluster_worker.py           # Cluster operations
    │
    ├── handlers/                   # Task handlers
    │   ├── cluster_task.py
    │   └── ...
    │
    └── utils/                      # Utilities
        ├── queue.py                # Queue operations
        └── ...
```

---

## 🚀 Quick Start

### Local Development

```bash
# Terminal 1: Start worker
cd backend
python worker.py

# Terminal 2: Push test task
python
>>> from app.workers.utils.queue import TaskQueue
>>> queue = TaskQueue()
>>> await queue.connect()
>>> await queue.push_task("spawn_agent", {"cluster_id": "test"})
```

### Docker

```bash
# Build worker image
docker build -f Dockerfile.worker -t brain-worker:latest .

# Run single worker
docker run --rm \
  -e REDIS_URL=redis://redis:6379/0 \
  -e DATABASE_URL=postgresql+asyncpg://... \
  -e OLLAMA_HOST=http://ollama:11434 \
  -e WORKER_CONCURRENCY=2 \
  --network brain_network \
  brain-worker:latest

# Run with docker-compose (3 replicas)
docker-compose up -d --scale worker=3
```

### Coolify Deployment

1. **New Service** → Docker Compose Service
2. **Image:** Build from `Dockerfile.worker`
3. **Replicas:** 3 (can scale 1-50+)
4. **Environment:**
   ```bash
   REDIS_URL=redis://redis:6379/0
   DATABASE_URL=postgresql+asyncpg://brain:brain@postgres:5432/brain
   OLLAMA_HOST=http://ollama:11434
   OLLAMA_MODEL=qwen2.5:0.5b
   WORKER_CONCURRENCY=2
   ```
5. **Network:** `brain-network` (same as backend)
6. **Deploy** → Workers start pulling tasks

---

## 🔧 Worker Types

### ClusterWorker

Processes cluster-related tasks:

| Task Type | Description | Payload |
|-----------|-------------|---------|
| `spawn_agent` | Create agent in cluster | `{cluster_id, agent_def}` |
| `scale_cluster` | Add/remove workers | `{cluster_id, target_workers}` |
| `delegate_task` | Supervisor → subordinate | `{cluster_id, task, target_role}` |
| `health_check` | Check cluster health | `{cluster_id}` |
| `collect_metrics` | Gather metrics | `{cluster_id}` |

**Queue:** `brain:cluster_tasks`

### MissionWorker (Existing)

Processes mission tasks:

**Queue:** `brain:mission_tasks`

---

## 📋 Task Format

Tasks are JSON objects with this structure:

```json
{
  "id": "uuid-v4",
  "type": "spawn_agent",
  "payload": {
    "cluster_id": "marketing-001",
    "agent_def": {
      "role": "worker",
      "name": "Content Creator",
      "capabilities": ["copywriting"]
    }
  },
  "created_at": "2024-02-17T10:30:00Z"
}
```

---

## 🔄 Task Flow

```
┌─────────────────┐
│   API/Service   │
│  (Push Task)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Redis Queue    │
│  RPUSH → BLPOP  │
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┐
    ▼         ▼        ▼        ▼
┌────────┐ ┌────────┐ ┌────────┐
│Worker 1│ │Worker 2│ │Worker 3│
│ (2/2)  │ │ (1/2)  │ │ (0/2)  │
└────┬───┘ └────┬───┘ └────┬───┘
     │          │           │
     └──────────┴───────────┘
         │
         ▼
┌─────────────────┐
│  Task Result    │
│  (Redis Pub)    │
└─────────────────┘
```

**Steps:**
1. Service pushes task to queue (RPUSH)
2. Worker pulls task (BLPOP, atomic)
3. Worker processes task
4. Worker publishes result to Redis channel
5. Worker stores result in Redis (1h TTL)

---

## 🎛️ Configuration

### Environment Variables

```bash
# Required
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+asyncpg://brain:brain@postgres:5432/brain

# Optional
WORKER_ID=auto-generated           # Worker identifier
WORKER_CONCURRENCY=2               # Tasks per worker (default: 2)
OLLAMA_HOST=http://ollama:11434
QDRANT_URL=http://qdrant:6333
```

### Concurrency Tuning

**Low concurrency (1-2):**
- Each task gets more CPU/memory
- Better for CPU-intensive tasks
- Lower throughput

**High concurrency (5-10):**
- More tasks processed in parallel
- Better for I/O-bound tasks
- Higher throughput
- Watch memory usage!

**Formula:**
```
Total Capacity = Workers × Concurrency per Worker

Example:
10 workers × 2 concurrency = 20 parallel tasks
```

---

## 📊 Monitoring

### Worker Heartbeats

Workers send heartbeats every 30 seconds to Redis:

```bash
# Check active workers
redis-cli KEYS "brain:worker:*:heartbeat"

# Get worker status
redis-cli GET "brain:worker:worker-1:heartbeat"
# {
#   "worker_id": "worker-1",
#   "timestamp": "2024-02-17T10:30:00Z",
#   "tasks_processed": 42,
#   "tasks_failed": 2,
#   "active_tasks": 1
# }
```

### Queue Metrics

```bash
# Queue length
redis-cli LLEN brain:cluster_tasks

# Peek at next task (without removing)
redis-cli LINDEX brain:cluster_tasks 0
```

### Task Results

```bash
# Subscribe to results channel
redis-cli SUBSCRIBE brain:task_results

# Get specific task result
redis-cli GET "brain:task:{task_id}:result"
```

---

## 🧪 Testing

### Unit Tests

```bash
# Run worker tests
pytest tests/workers/

# With coverage
pytest --cov=app.workers --cov-report=html tests/workers/
```

### Integration Tests

```python
import pytest
from app.workers.utils.queue import TaskQueue

@pytest.mark.asyncio
async def test_task_processing(redis_client):
    # Push task
    queue = TaskQueue()
    task_id = await queue.push_task("health_check", {"cluster_id": "test"})

    # Wait for result
    result = await queue.get_task_result(task_id, timeout=10)

    assert result["success"] is True
```

---

## 🔐 Security

### Worker Isolation

- **Non-root user**: Workers run as `worker` user (UID 1000)
- **No privileged mode**: No Docker socket access
- **Network isolation**: Only internal `brain-network`
- **Resource limits**: CPU/memory limits enforced

### Task Validation

- All payloads validated before processing
- Unknown task types rejected
- Malformed JSON rejected

---

## 🐛 Troubleshooting

### Worker not processing tasks

```bash
# Check worker logs
docker logs brain-worker-1 --tail=50

# Check Redis connection
docker exec brain-worker-1 python -c "
import redis
r = redis.from_url('redis://redis:6379/0')
print(r.ping())
"

# Check queue
docker exec redis redis-cli LLEN brain:cluster_tasks
```

### High memory usage

```bash
# Check worker stats
docker stats brain-worker-1

# If memory is high:
# 1. Reduce WORKER_CONCURRENCY (5 → 2)
# 2. Add more workers with lower concurrency
# 3. Add resource limits in docker-compose
```

### Tasks timing out

```bash
# Check task processing time
# In worker logs, look for:
# "Processing task {id}" → "Task {id} completed"

# If too slow:
# 1. Check Ollama/database latency
# 2. Increase worker count
# 3. Profile task handlers
```

---

## 📚 Related Modules

- **Cluster System** (`app.modules.cluster_system`) - Task source
- **Mission Control** (`mission_control_core`) - Orchestration
- **Event Stream** (`core.event_stream`) - Event publishing
- **Redis** - Queue backend

---

## 🛠️ Development Status

### ✅ Completed
- BaseWorker class with queue integration
- ClusterWorker with task routing
- Graceful shutdown
- Heartbeat system
- Dockerfile.worker
- docker-compose integration

### 🔧 In Progress (Max's Tasks)
- [ ] Task 4.1: Queue utils testing
- [ ] Task 4.2: Cluster task handlers
- [ ] Task 4.3: Coolify deployment
- [ ] Task 4.4: Load testing

### ⏳ TODO
- [ ] Dead letter queue for failed tasks
- [ ] Task retry with exponential backoff
- [ ] Worker auto-scaling based on queue length
- [ ] Metrics dashboard (Grafana)
- [ ] Distributed tracing (OpenTelemetry)

---

## 📖 References

- **Worker Entry Point**: `backend/worker.py`
- **Base Worker**: `app/workers/base_worker.py`
- **Cluster Worker**: `app/workers/cluster_worker.py`
- **Queue Utils**: `app/workers/utils/queue.py`
- **Dockerfile**: `backend/Dockerfile.worker`
- **Roadmap**: `docs/ROADMAP_PHASE3_PHASE4.md`

---

**Last Updated:** 2024-02-17
**Maintainer:** BRAiN Core Team
**License:** MIT
