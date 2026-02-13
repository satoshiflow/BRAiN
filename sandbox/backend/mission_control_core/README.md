# 🚀 BRAIN Mission Control Core - Deployment Guide

## Quick Start

### 1. Integration with your existing BRAIN system

```python
# In your existing FastAPI app (main.py)
from mission_control_core import create_mission_control_app

# Option A: Add to existing app
from mission_control_core.api.routes import (
    mission_router, task_router, agent_router, system_router
)

app.include_router(mission_router)
app.include_router(task_router) 
app.include_router(agent_router)
app.include_router(system_router)

# Option B: Use standalone app
mission_app = create_mission_control_app("redis://localhost:6379")
```

### 2. Docker Integration

```bash
# Add to your existing docker-compose.yml
cp mission_control_core/ /path/to/brain/backend/
pip install -r mission_control_core/requirements.txt
```

### 3. Redis Configuration

Ensure your Redis instance supports:
- Sorted Sets (for priority queues)
- Streams (for event logging) 
- Pub/Sub (for real-time communication)

```bash
# Redis minimal config
redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

## API Endpoints

Once deployed, you'll have:

### Missions
- `POST /api/v1/missions/` - Create mission
- `GET /api/v1/missions/{id}` - Get mission status
- `POST /api/v1/missions/{id}/start` - Start mission
- `POST /api/v1/missions/{id}/cancel` - Cancel mission

### Tasks  
- `POST /api/v1/tasks/` - Create task
- `GET /api/v1/tasks/{id}` - Get task details
- `POST /api/v1/tasks/{id}/retry` - Retry failed task

### Agents
- `POST /api/v1/agents/register` - Register agent
- `POST /api/v1/agents/heartbeat` - Update heartbeat
- `DELETE /api/v1/agents/{id}` - Unregister agent

### System
- `GET /api/v1/system/stats` - System statistics
- `POST /api/v1/system/cleanup` - Clean old tasks
- `WS /api/v1/system/ws` - WebSocket real-time updates

## Example Usage

### Create and Execute a Mission

```python
import httpx

# Create mission
mission_data = {
    "name": "Analyze Market Data", 
    "description": "Process and analyze market trends",
    "objectives": [
        {
            "description": "Fetch market data",
            "required_capabilities": ["data_fetcher"],
            "priority": "high"
        },
        {
            "description": "Analyze trends", 
            "required_capabilities": ["data_analyzer"],
            "priority": "normal"
        }
    ],
    "priority": "high"
}

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://brain.falklabs.de/api/v1/missions/",
        json=mission_data
    )
    mission_id = response.json()["mission_id"]
    
    # Check status
    status = await client.get(f"/api/v1/missions/{mission_id}")
    print(status.json())
```

### Register an Agent

```python
agent_data = {
    "agent_id": "data_analyzer_01",
    "capabilities": ["data_analysis", "trend_detection"],
    "max_tasks": 3
}

await client.post("/api/v1/agents/register", json=agent_data)

# Send heartbeat
heartbeat = {
    "agent_id": "data_analyzer_01",
    "current_tasks": 1,
    "metrics": {
        "success_rate": 0.95,
        "avg_response_time": 45.2
    }
}

await client.post("/api/v1/agents/heartbeat", json=heartbeat)
```

## Production Considerations

### Performance
- Redis: Use persistent storage for production
- Task cleanup: Configure regular cleanup jobs
- Monitoring: Set up Prometheus metrics endpoint

### Security  
- Enable Redis AUTH
- Use TLS for Redis connections
- Rate limit API endpoints
- Validate all input data

### Scaling
- Use Redis Cluster for horizontal scaling
- Deploy multiple orchestrator instances
- Load balance API endpoints

### Monitoring

```python
# Health check
response = await client.get("/health")
health = response.json()

print(f"Status: {health['status']}")
print(f"Components: {health['components']}")
```

## Integration Points

This Mission Control Core integrates with:

1. **Existing Health Agent** - Auto-registers with orchestrator
2. **Agent Registry** - Provides agent lifecycle management
3. **Event System** - Publishes mission/task events
4. **WebSocket** - Real-time updates for frontend

## Next Steps

1. Deploy Mission Control Core to brain.falklabs.de
2. Register your existing Health Agent
3. Create your first test mission
4. Build frontend dashboard for mission monitoring
5. Add more specialized agents (Odoo, Analytics, etc.)

The system is designed to be production-ready and scales with your BRAIN ecosystem!
