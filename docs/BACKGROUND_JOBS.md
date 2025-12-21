**# BRAiN Background Jobs & Task Queue**

**Version:** 1.0.0
**Created:** 2025-12-20
**Phase:** 5 - Developer Experience & Advanced Features

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Task Queues](#task-queues)
4. [Available Tasks](#available-tasks)
5. [Scheduled Tasks](#scheduled-tasks)
6. [API Reference](#api-reference)
7. [CLI Usage](#cli-usage)
8. [Monitoring](#monitoring)
9. [Development](#development)
10. [Best Practices](#best-practices)

---

## Overview

BRAiN uses **Celery** for distributed task queue management, enabling:

- **Asynchronous task execution** - Long-running operations don't block API responses
- **Scheduled tasks** - Periodic maintenance and monitoring (Celery Beat)
- **Task prioritization** - Multiple queues with different priorities
- **Retry logic** - Automatic retry with exponential backoff
- **Monitoring** - Flower UI for real-time task tracking
- **Horizontal scalability** - Add workers to handle more load

**Technology Stack:**
- **Celery** 5.3.6 - Distributed task queue
- **Redis** 7+ - Message broker and result backend
- **Flower** 2.0.1 - Web-based monitoring UI
- **Kombu** 5.3.5 - Messaging library

---

## Architecture

### Components

```
┌─────────────┐
│   FastAPI   │  (Enqueues tasks via API)
│   Backend   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Redis    │  (Message Broker + Result Backend)
└──────┬──────┘
       │
       ├──────────────────┬──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Worker    │  │   Worker    │  │   Worker    │
│  (default)  │  │  (system)   │  │ (missions)  │
└─────────────┘  └─────────────┘  └─────────────┘
       │
       ▼
┌─────────────┐
│Celery Beat  │  (Scheduler for periodic tasks)
└─────────────┘
       │
       ▼
┌─────────────┐
│   Flower    │  (Monitoring UI)
│  :5555      │
└─────────────┘
```

### Task Flow

1. **Client** (API/CLI) enqueues task
2. **Redis** stores task in appropriate queue
3. **Worker** picks up task based on priority
4. **Worker** executes task with retry logic
5. **Result** stored in Redis backend
6. **Client** polls for result or receives callback

---

## Task Queues

BRAiN uses **5 priority queues** to organize task execution:

| Queue | Priority | Purpose | Example Tasks |
|-------|----------|---------|---------------|
| `system` | 10 | System-critical operations | Health checks, metrics |
| `missions` | 8 | Mission execution | Mission processing, notifications |
| `agents` | 6 | Agent operations | Agent health checks, metrics |
| `default` | 5 | General tasks | Default queue |
| `maintenance` | 3 | Background maintenance | Cleanup, optimization |

**Priority Rules:**
- Higher number = higher priority
- Tasks picked from highest priority queue first
- Within a queue, FIFO (First In, First Out)

**Queue Selection:**
```python
# Automatic routing (based on task module)
task.delay()  # Uses task_routes in celery_app.py

# Explicit queue
task.apply_async(queue="system")
```

---

## Available Tasks

### System Tasks (`backend.app.tasks.system_tasks`)

**Health Check**
```python
from backend.app.tasks.system_tasks import health_check

# Execute
result = health_check.delay()

# Response
{
    "timestamp": "2025-12-20T10:30:00Z",
    "checks": {
        "redis": {"status": "healthy"},
        "disk": {"status": "healthy", "free_gb": 50.2, "percent_free": 45.3},
        "memory": {"status": "healthy", "used_gb": 8.2, "percent_used": 51.2}
    },
    "healthy": true
}
```

**Generate Daily Metrics**
```python
from backend.app.tasks.system_tasks import generate_daily_metrics

# Execute
result = generate_daily_metrics.delay()

# Response
{
    "date": "2025-12-19",
    "generated_at": "2025-12-20T00:00:00Z",
    "metrics": {
        "api_requests": {"total": 1523, "avg_response_time_ms": 45.3},
        "errors": {"total": 12, "error_rate": 0.79},
        "users": {"unique_active": 45}
    }
}
```

**Monitor Task Queue**
```python
from backend.app.tasks.system_tasks import monitor_task_queue

result = monitor_task_queue.delay()
```

**Test Tasks**
```python
from backend.app.tasks.system_tasks import test_task, test_retry_task

# Basic test (waits 5 seconds)
test_task.delay(wait_seconds=5)

# Test retry logic
test_retry_task.delay(max_retries=3)
```

### Mission Tasks (`backend.app.tasks.mission_tasks`)

**Mission Queue Health**
```python
from backend.app.tasks.mission_tasks import check_mission_queue_health

result = check_mission_queue_health.delay()
# Returns: queue size, stuck missions, health status
```

**Cleanup Completed Missions**
```python
from backend.app.tasks.mission_tasks import cleanup_completed_missions

# Cleanup missions older than 30 days
result = cleanup_completed_missions.delay(days_old=30)
# Returns: {"deleted": 42, "cutoff_date": "..."}
```

**Process Mission Asynchronously**
```python
from backend.app.tasks.mission_tasks import process_mission_async

result = process_mission_async.delay(mission_id="mission_123")
```

**Calculate Mission Metrics**
```python
from backend.app.tasks.mission_tasks import calculate_mission_metrics

result = calculate_mission_metrics.delay(
    start_date="2025-12-01T00:00:00Z",
    end_date="2025-12-31T23:59:59Z"
)
# Returns: mission statistics (total, completed, failed, success rate)
```

**Send Mission Notifications**
```python
from backend.app.tasks.mission_tasks import send_mission_notification

result = send_mission_notification.delay(
    mission_id="mission_123",
    status="completed",
    recipients=["user@example.com"],
    notification_type="email"
)
```

### Agent Tasks (`backend.app.tasks.agent_tasks`)

**Check Agent Heartbeats**
```python
from backend.app.tasks.agent_tasks import check_agent_heartbeats

result = check_agent_heartbeats.delay()
# Returns: active/inactive agents list
```

**Cleanup Inactive Agents**
```python
from backend.app.tasks.agent_tasks import cleanup_inactive_agents

result = cleanup_inactive_agents.delay(inactive_threshold_minutes=60)
```

**Run Agent Health Check**
```python
from backend.app.tasks.agent_tasks import run_agent_health_check

result = run_agent_health_check.delay(agent_id="ops_agent")
```

**Calculate Agent Metrics**
```python
from backend.app.tasks.agent_tasks import calculate_agent_metrics

result = calculate_agent_metrics.delay(
    agent_id="ops_agent",
    start_date="2025-12-01T00:00:00Z",
    end_date="2025-12-31T23:59:59Z"
)
```

**Execute Agent Task**
```python
from backend.app.tasks.agent_tasks import execute_agent_task_async

result = execute_agent_task_async.delay(
    agent_id="ops_agent",
    task_data={"action": "deploy", "environment": "production"}
)
```

### Maintenance Tasks (`backend.app.tasks.maintenance_tasks`)

**Cleanup Audit Logs**
```python
from backend.app.tasks.maintenance_tasks import cleanup_audit_logs

# Cleanup logs older than 90 days
result = cleanup_audit_logs.delay(retention_days=90)
```

**Cleanup Task Results**
```python
from backend.app.tasks.maintenance_tasks import cleanup_task_results

result = cleanup_task_results.delay(days_old=7)
```

**Cleanup Expired Cache**
```python
from backend.app.tasks.maintenance_tasks import cleanup_expired_cache

result = cleanup_expired_cache.delay()
```

**Rotate Encryption Keys**
```python
from backend.app.tasks.maintenance_tasks import rotate_encryption_keys

result = rotate_encryption_keys.delay()
```

**Cleanup Expired API Keys**
```python
from backend.app.tasks.maintenance_tasks import cleanup_expired_api_keys

result = cleanup_expired_api_keys.delay()
```

**Database Maintenance**
```python
from backend.app.tasks.maintenance_tasks import vacuum_database, analyze_database_tables

# Reclaim space
vacuum_database.delay()

# Update statistics
analyze_database_tables.delay()
```

**Optimize Redis Memory**
```python
from backend.app.tasks.maintenance_tasks import optimize_redis_memory

result = optimize_redis_memory.delay()
# Returns: memory before/after, keys deleted
```

**Full System Maintenance**
```python
from backend.app.tasks.maintenance_tasks import full_system_maintenance

# Runs all maintenance tasks
result = full_system_maintenance.delay()
```

---

## Scheduled Tasks

**Celery Beat** runs periodic tasks on a schedule:

| Task | Schedule | Queue | Purpose |
|------|----------|-------|---------|
| `health_check` | Every 5 minutes | system | System health monitoring |
| `cleanup_audit_logs` | Daily at 2 AM | maintenance | Cleanup old audit logs |
| `cleanup_task_results` | Daily at 3 AM | maintenance | Cleanup old task results |
| `check_mission_queue_health` | Every 1 minute | missions | Mission queue monitoring |
| `check_agent_heartbeats` | Every 30 seconds | agents | Agent heartbeat check |
| `rotate_encryption_keys` | Monthly (1st at 4 AM) | maintenance | Key rotation |
| `generate_daily_metrics` | Daily at midnight | system | Daily metrics report |

**Customizing Schedules:**

Edit `backend/app/core/celery_app.py`:

```python
beat_schedule={
    "my-custom-task": {
        "task": "backend.app.tasks.system_tasks.health_check",
        "schedule": 300.0,  # 5 minutes (seconds)
        # OR crontab
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight
        "options": {"queue": "system"},
    },
}
```

**Crontab Examples:**

```python
from celery.schedules import crontab

# Every day at midnight
crontab(hour=0, minute=0)

# Every Monday at 9 AM
crontab(day_of_week=1, hour=9, minute=0)

# Every 1st of month at 4 AM
crontab(day_of_month=1, hour=4, minute=0)

# Every 15 minutes
crontab(minute='*/15')
```

---

## API Reference

### Execute Task

```http
POST /api/tasks/execute
```

**Request:**
```json
{
    "task_name": "backend.app.tasks.system_tasks.health_check",
    "args": [],
    "kwargs": {},
    "queue": "system",
    "countdown": 60
}
```

**Response:**
```json
{
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "task_name": "backend.app.tasks.system_tasks.health_check",
    "status": "PENDING",
    "queue": "system"
}
```

### Get Task Status

```http
GET /api/tasks/{task_id}
```

**Response:**
```json
{
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "SUCCESS",
    "ready": true,
    "successful": true,
    "result": {
        "timestamp": "2025-12-20T10:30:00Z",
        "checks": {...},
        "healthy": true
    }
}
```

**Task Statuses:**
- `PENDING` - Task waiting to be executed
- `STARTED` - Task has been started by a worker
- `SUCCESS` - Task completed successfully
- `FAILURE` - Task failed with exception
- `RETRY` - Task is being retried after failure
- `REVOKED` - Task was cancelled

### Cancel Task

```http
DELETE /api/tasks/{task_id}?terminate=false
```

**Parameters:**
- `terminate` (boolean) - If true, terminate if already running

### List Active Tasks

```http
GET /api/tasks/active/list
```

**Response:**
```json
[
    {
        "worker": "brain-celery-worker",
        "task_id": "a1b2c3d4...",
        "task_name": "backend.app.tasks.system_tasks.health_check",
        "args": [],
        "kwargs": {},
        "time_start": "2025-12-20T10:30:00Z"
    }
]
```

### List Scheduled Tasks

```http
GET /api/tasks/scheduled/list
```

### Get Worker Stats

```http
GET /api/tasks/workers/stats
```

**Response:**
```json
{
    "workers": {
        "brain-celery-worker": {
            "pool": {"implementation": "prefork", "max-concurrency": 4},
            "total": {"tasks": 1523}
        }
    },
    "total_workers": 1
}
```

### List Registered Tasks

```http
GET /api/tasks/registered/list
```

**Response:**
```json
{
    "tasks": [
        "backend.app.tasks.system_tasks.health_check",
        "backend.app.tasks.mission_tasks.process_mission_async",
        ...
    ],
    "total": 25
}
```

### Purge Task Results

```http
POST /api/tasks/purge/results
```

### Purge Queue

```http
POST /api/tasks/purge/queue?queue_name=default
```

### Cancel All Tasks

```http
POST /api/tasks/cancel/all?terminate=false
```

---

## CLI Usage

### Worker Management

**Start Worker:**
```bash
python -m brain_cli.tasks_cli worker start --queue=default --concurrency=4
```

**Stop Workers:**
```bash
python -m brain_cli.tasks_cli worker stop
```

**Worker Stats:**
```bash
python -m brain_cli.tasks_cli worker stats
```

### Beat Scheduler

**Start Beat:**
```bash
python -m brain_cli.tasks_cli beat start
```

**Stop Beat:**
```bash
python -m brain_cli.tasks_cli beat stop
```

### Task Management

**List Tasks:**
```bash
python -m brain_cli.tasks_cli tasks list
```

**List Active Tasks:**
```bash
python -m brain_cli.tasks_cli tasks active
```

**Execute Task:**
```bash
python -m brain_cli.tasks_cli tasks execute backend.app.tasks.system_tasks.health_check
```

**Get Task Status:**
```bash
python -m brain_cli.tasks_cli tasks status <task_id>
```

**Cancel Task:**
```bash
python -m brain_cli.tasks_cli tasks cancel <task_id> --terminate
```

### Flower Monitoring

**Start Flower UI:**
```bash
python -m brain_cli.tasks_cli flower start --port=5555
```

Access at: http://localhost:5555

### System Info

```bash
python -m brain_cli.tasks_cli info
```

---

## Monitoring

### Flower UI

**Access:** http://localhost:5555

**Features:**
- Real-time task monitoring
- Worker status and stats
- Task execution history
- Task success/failure rates
- Worker resource usage
- Task result inspection
- Task revocation (cancellation)

**Screenshots:**

- **Dashboard:** Overview of workers and tasks
- **Tasks:** List of all tasks with status
- **Workers:** Worker details and stats
- **Broker:** Message broker stats (Redis)

### Metrics & Alerts

**Health Checks:**
- System health check runs every 5 minutes
- Mission queue health check runs every 1 minute
- Agent heartbeat check runs every 30 seconds

**Automatic Alerts:**
- Queue depth exceeds 1000 tasks
- Stuck tasks (running > 30 minutes)
- No active workers
- Disk space < 10%
- Memory usage > 90%

**Prometheus Metrics:**
```python
# Task execution time
task_execution_seconds{task="health_check", status="success"}

# Task count by status
task_total{task="health_check", status="success"} 1523

# Worker count
celery_workers_total 3
```

---

## Development

### Creating a New Task

1. **Define Task:**

```python
# backend/app/tasks/my_tasks.py
from backend.app.core.celery_app import task_with_retry
from loguru import logger

@task_with_retry(max_retries=3)
def my_custom_task(self, param1: str, param2: int) -> dict:
    """
    Custom task description.

    Args:
        param1: First parameter
        param2: Second parameter

    Returns:
        Task result
    """
    logger.info(f"Executing my_custom_task: {param1}, {param2}")

    try:
        # Task logic here
        result = {"status": "success", "data": param1}
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise
```

2. **Register Task Module:**

Edit `backend/app/core/celery_app.py`:

```python
celery_app = Celery(
    "brain",
    include=[
        "backend.app.tasks.system_tasks",
        "backend.app.tasks.my_tasks",  # Add this
    ]
)
```

3. **Add to Routing (optional):**

```python
task_routes={
    "backend.app.tasks.my_tasks.*": {"queue": "default"},
}
```

4. **Use Task:**

```python
from backend.app.tasks.my_tasks import my_custom_task

# Synchronous (blocks until complete)
result = my_custom_task("test", 42)

# Asynchronous (returns immediately)
async_result = my_custom_task.delay("test", 42)

# Asynchronous with options
async_result = my_custom_task.apply_async(
    args=["test", 42],
    queue="default",
    countdown=60,  # Delay 60 seconds
)

# Get result (blocks)
result = async_result.get(timeout=10)
```

### Task Options

**Retry Configuration:**
```python
@task_with_retry(
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def my_task(self):
    pass
```

**Time Limits:**
```python
@celery_app.task(
    time_limit=300,  # Hard limit (kills task)
    soft_time_limit=240  # Soft limit (raises exception)
)
def my_task(self):
    pass
```

**Priority:**
```python
# Higher number = higher priority (0-9)
task.apply_async(priority=9)
```

**ETA (Exact Time):**
```python
from datetime import datetime, timedelta

eta = datetime.utcnow() + timedelta(hours=1)
task.apply_async(eta=eta)
```

**Countdown:**
```python
# Delay execution by 60 seconds
task.apply_async(countdown=60)
```

### Testing Tasks

```python
# tests/test_tasks.py
import pytest
from backend.app.tasks.system_tasks import health_check

def test_health_check_task():
    """Test health check task execution."""
    # Run task synchronously
    result = health_check()

    assert result["healthy"] is not None
    assert "checks" in result
    assert "redis" in result["checks"]
```

**Run Tests:**
```bash
pytest tests/test_tasks.py -v
```

---

## Best Practices

### Task Design

✅ **DO:**
- Keep tasks **idempotent** (safe to run multiple times)
- Use **explicit task names** (fully qualified paths)
- Add **comprehensive logging**
- Set appropriate **time limits**
- Use **retry logic** with exponential backoff
- Return **structured results** (dicts/models)
- Handle **exceptions gracefully**

❌ **DON'T:**
- Don't pass large objects as arguments (use IDs and fetch in task)
- Don't use blocking I/O without timeouts
- Don't store sensitive data in task arguments
- Don't rely on task execution order
- Don't use tasks for real-time operations

### Performance

**Concurrency:**
```bash
# Adjust based on CPU cores and task type
# I/O bound: 2-4x CPU cores
# CPU bound: 1x CPU cores
celery worker --concurrency=4
```

**Prefetch Multiplier:**
```python
# Lower = better distribution, higher = better throughput
worker_prefetch_multiplier=4
```

**Task Acks:**
```python
# Late ack = better reliability (ack after completion)
task_acks_late=True
```

### Error Handling

**Automatic Retry:**
```python
@task_with_retry(
    max_retries=3,
    autoretry_for=(ConnectionError, TimeoutError)
)
def my_task(self):
    pass
```

**Manual Retry:**
```python
@celery_app.task(bind=True)
def my_task(self):
    try:
        # Task logic
        pass
    except SomeException as e:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
```

**Error Callbacks:**
```python
task.apply_async(
    link_error=handle_error.s()
)

@celery_app.task
def handle_error(request, exc, traceback):
    # Handle error
    logger.error(f"Task failed: {exc}")
```

### Security

**Sensitive Data:**
```python
# ❌ BAD
task.delay(password="secret123")

# ✅ GOOD
task.delay(user_id="user_123")
# Then fetch password in task from secure storage
```

**Result Expiration:**
```python
# Don't store results indefinitely
result_expires=3600  # 1 hour
```

**Task Permissions:**
```python
# Use API permissions to control who can execute tasks
@router.post("/tasks/execute")
async def execute_task(
    request: TaskExecuteRequest,
    principal: Principal = Depends(require_admin)
):
    pass
```

---

## Troubleshooting

### Workers Not Processing Tasks

**Check Workers:**
```bash
celery -A backend.app.core.celery_app inspect active
celery -A backend.app.core.celery_app inspect stats
```

**Check Broker Connection:**
```bash
redis-cli ping
```

**Check Task Routing:**
```python
# Ensure task is in correct queue
task.apply_async(queue="default")
```

### Tasks Stuck in PENDING

**Causes:**
- No workers running
- Workers not listening to the queue
- Broker connection issues

**Solutions:**
```bash
# Start workers
docker-compose up celery_worker

# Check worker logs
docker-compose logs celery_worker

# Purge stuck tasks
celery -A backend.app.core.celery_app purge
```

### High Memory Usage

**Solutions:**
- Reduce worker concurrency
- Enable `max_tasks_per_child` (worker restarts after N tasks)
- Clean up task results regularly

```python
worker_max_tasks_per_child=1000
```

### Task Timeout

**Increase Time Limits:**
```python
task_time_limit=600  # 10 minutes
task_soft_time_limit=300  # 5 minutes
```

---

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [Flower Documentation](https://flower.readthedocs.io/)
- [Redis Documentation](https://redis.io/docs/)
- [BRAiN CLAUDE.md](../CLAUDE.md)

---

**Last Updated:** 2025-12-20
**Maintainer:** BRAiN Development Team
**Phase:** 5 - Developer Experience & Advanced Features
