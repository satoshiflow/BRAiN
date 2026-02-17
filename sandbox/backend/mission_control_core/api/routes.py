"""
🎯 BRAIN Mission Control - REST API Endpoints
FastAPI routes for mission and task management

Philosophy: Myzelkapitalismus
- RESTful API design for easy integration
- Real-time updates via WebSocket
- Comprehensive error handling and logging
- OpenAPI documentation for transparency
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
import json
import asyncio
import logging

from .mission_control import (
    MissionController, Mission, MissionObjective, 
    MissionStatus, MissionPriority
)
from .task_queue import TaskQueue, Task, TaskStatus, TaskPriority
from .orchestrator import Orchestrator, AgentCapability
from .event_stream import EventStream, EventType

logger = logging.getLogger(__name__)

# Initialize router
mission_router = APIRouter(prefix="/api/v1/missions", tags=["missions"])
task_router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
agent_router = APIRouter(prefix="/api/v1/agents", tags=["agents"])
system_router = APIRouter(prefix="/api/v1/system", tags=["system"])

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Pydantic models for API

class ObjectiveCreate(BaseModel):
    description: str = Field(..., description="Objective description")
    required_capabilities: List[str] = Field(default=[], description="Required agent capabilities")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    dependencies: List[str] = Field(default=[], description="Task dependencies")
    estimated_duration: int = Field(default=300, description="Estimated duration in seconds")
    success_criteria: Dict[str, Any] = Field(default={}, description="Success criteria")

class MissionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Mission name")
    description: str = Field(..., min_length=1, description="Mission description")
    objectives: List[ObjectiveCreate] = Field(..., min_items=1, description="Mission objectives")
    priority: MissionPriority = Field(default=MissionPriority.NORMAL, description="Mission priority")
    deadline: Optional[datetime] = Field(None, description="Mission deadline")
    context: Optional[Dict[str, Any]] = Field(default={}, description="Mission context")
    created_by: str = Field(default="api_user", description="Creator identifier")

class TaskCreate(BaseModel):
    mission_id: str = Field(..., description="Mission ID")
    task_type: str = Field(..., description="Task type")
    agent_type: Optional[str] = Field(None, description="Required agent type")
    payload: Dict[str, Any] = Field(..., description="Task payload")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    dependencies: List[str] = Field(default=[], description="Task dependencies")
    timeout_seconds: int = Field(default=300, description="Task timeout")

class AgentRegister(BaseModel):
    agent_id: str = Field(..., description="Agent identifier")
    capabilities: List[str] = Field(..., description="Agent capabilities")
    max_tasks: int = Field(default=5, description="Maximum concurrent tasks")

class AgentHeartbeat(BaseModel):
    agent_id: str = Field(..., description="Agent identifier")
    current_tasks: Optional[int] = Field(None, description="Current task count")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Agent metrics")

# Global instances (will be injected in real app)
mission_controller: Optional[MissionController] = None
task_queue: Optional[TaskQueue] = None
orchestrator: Optional[Orchestrator] = None
event_stream: Optional[EventStream] = None

def get_mission_controller() -> MissionController:
    if mission_controller is None:
        raise HTTPException(status_code=500, detail="Mission controller not initialized")
    return mission_controller

def get_task_queue() -> TaskQueue:
    if task_queue is None:
        raise HTTPException(status_code=500, detail="Task queue not initialized")
    return task_queue

def get_orchestrator() -> Orchestrator:
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    return orchestrator

def get_event_stream() -> EventStream:
    if event_stream is None:
        raise HTTPException(status_code=500, detail="Event stream not initialized")
    return event_stream

# Mission endpoints

@mission_router.post("/", response_model=Dict[str, str])
async def create_mission(
    mission_data: MissionCreate,
    controller: MissionController = Depends(get_mission_controller)
):
    """Create a new mission"""
    try:
        # Convert objectives
        objectives = []
        for i, obj_data in enumerate(mission_data.objectives):
            objective = MissionObjective(
                id=f"obj_{i+1}",
                description=obj_data.description,
                required_capabilities=obj_data.required_capabilities,
                priority=obj_data.priority,
                dependencies=obj_data.dependencies,
                estimated_duration=obj_data.estimated_duration,
                success_criteria=obj_data.success_criteria
            )
            objectives.append(objective)
        
        mission_id = await controller.create_mission(
            name=mission_data.name,
            description=mission_data.description,
            objectives=objectives,
            priority=mission_data.priority,
            deadline=mission_data.deadline,
            context=mission_data.context,
            created_by=mission_data.created_by
        )
        
        if not mission_id:
            raise HTTPException(status_code=500, detail="Failed to create mission")
        
        # Auto-plan and start mission if no dependencies
        await controller.plan_mission(mission_id)
        await controller.start_mission(mission_id)
        
        return {"mission_id": mission_id, "status": "created"}
        
    except Exception as e:
        logger.error(f"Error creating mission: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@mission_router.get("/{mission_id}")
async def get_mission(
    mission_id: str,
    controller: MissionController = Depends(get_mission_controller)
):
    """Get mission details and status"""
    try:
        mission_status = await controller.get_mission_status(mission_id)
        if not mission_status:
            raise HTTPException(status_code=404, detail="Mission not found")
        
        return mission_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting mission {mission_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@mission_router.get("/")
async def list_missions(
    status: Optional[MissionStatus] = None,
    priority: Optional[MissionPriority] = None,
    limit: int = 50,
    controller: MissionController = Depends(get_mission_controller)
):
    """List missions with optional filtering"""
    try:
        missions = await controller.list_missions(status, priority, limit)
        return {"missions": missions, "count": len(missions)}
        
    except Exception as e:
        logger.error(f"Error listing missions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@mission_router.post("/{mission_id}/start")
async def start_mission(
    mission_id: str,
    controller: MissionController = Depends(get_mission_controller)
):
    """Start mission execution"""
    try:
        success = await controller.start_mission(mission_id)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot start mission")
        
        return {"status": "started"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting mission {mission_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@mission_router.post("/{mission_id}/pause")
async def pause_mission(
    mission_id: str,
    controller: MissionController = Depends(get_mission_controller)
):
    """Pause mission execution"""
    try:
        success = await controller.pause_mission(mission_id)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot pause mission")
        
        return {"status": "paused"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing mission {mission_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@mission_router.post("/{mission_id}/cancel")
async def cancel_mission(
    mission_id: str,
    controller: MissionController = Depends(get_mission_controller)
):
    """Cancel mission execution"""
    try:
        success = await controller.cancel_mission(mission_id)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot cancel mission")
        
        return {"status": "cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling mission {mission_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Task endpoints

@task_router.post("/", response_model=Dict[str, str])
async def create_task(
    task_data: TaskCreate,
    queue: TaskQueue = Depends(get_task_queue)
):
    """Create a new task"""
    try:
        import uuid
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            mission_id=task_data.mission_id,
            task_type=task_data.task_type,
            agent_type=task_data.agent_type,
            payload=task_data.payload,
            priority=task_data.priority,
            status=TaskStatus.PENDING,
            dependencies=task_data.dependencies,
            timeout_seconds=task_data.timeout_seconds
        )
        
        success = await queue.enqueue_task(task)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to enqueue task")
        
        return {"task_id": task_id, "status": "created"}
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@task_router.get("/{task_id}")
async def get_task(
    task_id: str,
    queue: TaskQueue = Depends(get_task_queue)
):
    """Get task details"""
    try:
        task = await queue.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return task.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@task_router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    queue: TaskQueue = Depends(get_task_queue)
):
    """Retry a failed task"""
    try:
        success = await queue.retry_task(task_id)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot retry task")
        
        return {"status": "retrying"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@task_router.get("/mission/{mission_id}")
async def get_mission_tasks(
    mission_id: str,
    queue: TaskQueue = Depends(get_task_queue)
):
    """Get all tasks for a mission"""
    try:
        tasks = await queue.get_mission_tasks(mission_id)
        return {"tasks": [task.to_dict() for task in tasks]}
        
    except Exception as e:
        logger.error(f"Error getting mission tasks {mission_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Agent endpoints

@agent_router.post("/register")
async def register_agent(
    agent_data: AgentRegister,
    orch: Orchestrator = Depends(get_orchestrator)
):
    """Register a new agent"""
    try:
        capabilities = [
            AgentCapability(name=cap, confidence=0.8)
            for cap in agent_data.capabilities
        ]
        
        success = await orch.register_agent(
            agent_data.agent_id,
            capabilities,
            agent_data.max_tasks
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to register agent")
        
        return {"status": "registered"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@agent_router.post("/heartbeat")
async def agent_heartbeat(
    heartbeat_data: AgentHeartbeat,
    orch: Orchestrator = Depends(get_orchestrator)
):
    """Update agent heartbeat"""
    try:
        success = await orch.update_agent_heartbeat(
            heartbeat_data.agent_id,
            heartbeat_data.current_tasks,
            heartbeat_data.metrics
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return {"status": "updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent heartbeat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@agent_router.delete("/{agent_id}")
async def unregister_agent(
    agent_id: str,
    orch: Orchestrator = Depends(get_orchestrator)
):
    """Unregister an agent"""
    try:
        success = await orch.unregister_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return {"status": "unregistered"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System endpoints

@system_router.get("/stats")
async def get_system_stats(
    orch: Orchestrator = Depends(get_orchestrator),
    queue: TaskQueue = Depends(get_task_queue),
    stream: EventStream = Depends(get_event_stream)
):
    """Get comprehensive system statistics"""
    try:
        orchestrator_stats = await orch.get_orchestrator_stats()
        queue_stats = await queue.get_queue_stats()
        stream_stats = await stream.get_stream_stats()
        
        return {
            "orchestrator": orchestrator_stats,
            "task_queue": queue_stats,
            "event_stream": stream_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@system_router.post("/cleanup")
async def cleanup_system(
    max_age_hours: int = 24,
    queue: TaskQueue = Depends(get_task_queue)
):
    """Clean up old completed tasks"""
    try:
        cleaned = await queue.cleanup_old_tasks(max_age_hours)
        return {"cleaned_tasks": cleaned}
        
    except Exception as e:
        logger.error(f"Error cleaning up system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates

@system_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Event handler for WebSocket broadcasts
async def broadcast_event_handler(event):
    """Handle events by broadcasting to WebSocket clients"""
    message = {
        "type": "event",
        "event_type": event.type.value,
        "source": event.source,
        "payload": event.payload,
        "timestamp": event.timestamp.isoformat()
    }
    await manager.broadcast(message)

# Initialization function
async def initialize_mission_control_api(
    mc: MissionController,
    tq: TaskQueue, 
    orch: Orchestrator,
    es: EventStream
):
    """Initialize API with mission control components"""
    global mission_controller, task_queue, orchestrator, event_stream
    
    mission_controller = mc
    task_queue = tq
    orchestrator = orch
    event_stream = es
    
    # Register event handler for WebSocket broadcasts
    for event_type in EventType:
        await event_stream.register_handler(event_type, broadcast_event_handler)
    
    logger.info("Mission Control API initialized")

# Export routers
__all__ = [
    'mission_router', 'task_router', 'agent_router', 'system_router',
    'initialize_mission_control_api'
]
