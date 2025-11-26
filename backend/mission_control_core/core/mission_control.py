"""
🎯 BRAIN Mission Control - Mission Management System
High-level mission coordination and execution

Philosophy: Myzelkapitalismus
- Cooperative mission planning and execution
- Dynamic task decomposition based on available agents
- Self-healing mission recovery and adaptation
- Transparent progress tracking and reporting
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from .task_queue import TaskQueue, Task, TaskStatus, TaskPriority
from .orchestrator import Orchestrator, AgentCapability
from .event_stream import EventStream, EventType, emit_task_event

logger = logging.getLogger(__name__)


class MissionStatus(str, Enum):
    """Mission execution states"""
    PLANNING = "planning"        # Mission created, planning tasks
    READY = "ready"             # All tasks planned, ready to start
    RUNNING = "running"         # Mission executing
    PAUSED = "paused"           # Temporarily paused
    COMPLETED = "completed"     # Successfully completed
    FAILED = "failed"           # Failed with errors
    CANCELLED = "cancelled"     # Manually cancelled
    PARTIAL = "partial"         # Partially completed


class MissionPriority(str, Enum):
    """Mission priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class MissionObjective:
    """Individual mission objective"""
    id: str
    description: str
    required_capabilities: List[str]
    priority: TaskPriority
    dependencies: List[str] = None
    estimated_duration: int = 300  # seconds
    success_criteria: Dict[str, Any] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.success_criteria is None:
            self.success_criteria = {}


@dataclass
class Mission:
    """Mission data structure"""
    id: str
    name: str
    description: str
    objectives: List[MissionObjective]
    priority: MissionPriority
    status: MissionStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    tags: List[str] = None
    context: Dict[str, Any] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    
    # Task tracking
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.context is None:
            self.context = {}

    def calculate_progress(self) -> float:
        """Calculate mission progress based on task completion"""
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    def is_overdue(self) -> bool:
        """Check if mission has exceeded its deadline"""
        if not self.deadline:
            return False
        return datetime.utcnow() > self.deadline

    def to_dict(self) -> Dict[str, Any]:
        """Serialize mission for storage"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Mission':
        """Deserialize mission from storage"""
        data = data.copy()
        # Convert ISO strings back to datetime objects
        datetime_fields = ['created_at', 'updated_at', 'started_at', 'completed_at', 'deadline']
        for field in datetime_fields:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        # Convert objectives
        if 'objectives' in data:
            data['objectives'] = [MissionObjective(**obj) for obj in data['objectives']]
        
        return cls(**data)


class MissionController:
    """
    Mission Control System - Orchestrates complex multi-agent missions
    """
    
    def __init__(self, task_queue: TaskQueue, orchestrator: Orchestrator, 
                 event_stream: EventStream):
        self.task_queue = task_queue
        self.orchestrator = orchestrator  
        self.event_stream = event_stream
        
        # Mission storage (in production, this would be a database)
        self.missions: Dict[str, Mission] = {}
        
        # Mission monitoring
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.config = {
            'monitor_interval': 10.0,     # seconds
            'default_timeout': 3600,      # 1 hour default
            'max_parallel_tasks': 100,    # per mission
            'auto_retry_failed': True,
        }

    async def create_mission(self, name: str, description: str, 
                           objectives: List[MissionObjective],
                           priority: MissionPriority = MissionPriority.NORMAL,
                           deadline: Optional[datetime] = None,
                           context: Optional[Dict[str, Any]] = None,
                           created_by: str = "system") -> str:
        """
        Create a new mission
        Returns mission ID
        """
        try:
            mission_id = str(uuid.uuid4())
            
            mission = Mission(
                id=mission_id,
                name=name,
                description=description,
                objectives=objectives,
                priority=priority,
                status=MissionStatus.PLANNING,
                created_by=created_by,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                deadline=deadline,
                context=context or {}
            )
            
            self.missions[mission_id] = mission
            
            # Emit mission created event
            await self.event_stream.publish_event({
                'id': str(uuid.uuid4()),
                'type': EventType.MISSION_CREATED,
                'source': 'mission_controller',
                'target': None,
                'payload': {
                    'mission_id': mission_id,
                    'name': name,
                    'priority': priority.value,
                    'objectives_count': len(objectives)
                },
                'timestamp': datetime.utcnow(),
                'mission_id': mission_id
            })
            
            logger.info(f"Mission '{name}' created with {len(objectives)} objectives")
            return mission_id
            
        except Exception as e:
            logger.error(f"Failed to create mission: {e}")
            return ""

    async def plan_mission(self, mission_id: str) -> bool:
        """
        Plan mission execution by decomposing objectives into tasks
        """
        try:
            mission = self.missions.get(mission_id)
            if not mission or mission.status != MissionStatus.PLANNING:
                return False
                
            # Decompose objectives into tasks
            tasks_created = 0
            
            for objective in mission.objectives:
                # Create task for objective
                task_id = str(uuid.uuid4())
                
                # Map mission priority to task priority
                task_priority = TaskPriority(objective.priority.value)
                
                # Determine agent type based on required capabilities
                agent_type = None
                if objective.required_capabilities:
                    agent_type = objective.required_capabilities[0]  # Primary capability
                
                task = Task(
                    id=task_id,
                    mission_id=mission_id,
                    task_type=agent_type or 'general',
                    agent_type=agent_type,
                    payload={
                        'objective_id': objective.id,
                        'description': objective.description,
                        'success_criteria': objective.success_criteria,
                        'context': mission.context
                    },
                    priority=task_priority,
                    status=TaskStatus.PENDING,
                    dependencies=objective.dependencies,
                    timeout_seconds=objective.estimated_duration
                )
                
                # Enqueue task
                if await self.task_queue.enqueue_task(task):
                    tasks_created += 1
                    
                    # Emit task created event
                    await emit_task_event(
                        self.event_stream,
                        task_id,
                        EventType.TASK_CREATED,
                        'mission_controller',
                        mission_id
                    )
            
            # Update mission status
            mission.total_tasks = tasks_created
            mission.status = MissionStatus.READY if tasks_created > 0 else MissionStatus.FAILED
            mission.updated_at = datetime.utcnow()
            
            logger.info(f"Mission {mission_id} planned with {tasks_created} tasks")
            return tasks_created > 0
            
        except Exception as e:
            logger.error(f"Failed to plan mission {mission_id}: {e}")
            return False

    async def start_mission(self, mission_id: str) -> bool:
        """Start mission execution"""
        try:
            mission = self.missions.get(mission_id)
            if not mission or mission.status != MissionStatus.READY:
                return False
                
            mission.status = MissionStatus.RUNNING
            mission.started_at = datetime.utcnow()
            mission.updated_at = datetime.utcnow()
            
            # Emit mission started event
            await self.event_stream.publish_event({
                'id': str(uuid.uuid4()),
                'type': EventType.MISSION_STARTED,
                'source': 'mission_controller',
                'target': None,
                'payload': {
                    'mission_id': mission_id,
                    'name': mission.name,
                    'total_tasks': mission.total_tasks
                },
                'timestamp': datetime.utcnow(),
                'mission_id': mission_id
            })
            
            logger.info(f"Mission {mission_id} started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start mission {mission_id}: {e}")
            return False

    async def pause_mission(self, mission_id: str) -> bool:
        """Pause mission execution"""
        try:
            mission = self.missions.get(mission_id)
            if not mission or mission.status != MissionStatus.RUNNING:
                return False
                
            mission.status = MissionStatus.PAUSED
            mission.updated_at = datetime.utcnow()
            
            # TODO: Pause running tasks
            
            logger.info(f"Mission {mission_id} paused")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause mission {mission_id}: {e}")
            return False

    async def cancel_mission(self, mission_id: str) -> bool:
        """Cancel mission execution"""
        try:
            mission = self.missions.get(mission_id)
            if not mission:
                return False
                
            mission.status = MissionStatus.CANCELLED
            mission.completed_at = datetime.utcnow()
            mission.updated_at = datetime.utcnow()
            
            # Cancel all pending/running tasks
            tasks = await self.task_queue.get_mission_tasks(mission_id)
            for task in tasks:
                if task.status in [TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.ASSIGNED]:
                    await self.task_queue.update_task_status(
                        task.id, TaskStatus.CANCELLED
                    )
            
            # Emit mission cancelled event
            await self.event_stream.publish_event({
                'id': str(uuid.uuid4()),
                'type': EventType.MISSION_CANCELLED,
                'source': 'mission_controller',
                'target': None,
                'payload': {
                    'mission_id': mission_id,
                    'name': mission.name
                },
                'timestamp': datetime.utcnow(),
                'mission_id': mission_id
            })
            
            logger.info(f"Mission {mission_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel mission {mission_id}: {e}")
            return False

    async def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Get mission details"""
        return self.missions.get(mission_id)

    async def get_mission_status(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed mission status including task progress"""
        try:
            mission = self.missions.get(mission_id)
            if not mission:
                return None
                
            # Get task status
            tasks = await self.task_queue.get_mission_tasks(mission_id)
            task_status = {}
            completed_tasks = 0
            failed_tasks = 0
            
            for task in tasks:
                task_status[task.id] = {
                    'status': task.status.value,
                    'agent_id': task.assigned_agent_id,
                    'created_at': task.created_at.isoformat(),
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                }
                
                if task.status == TaskStatus.COMPLETED:
                    completed_tasks += 1
                elif task.status == TaskStatus.FAILED:
                    failed_tasks += 1
            
            # Update mission progress
            mission.completed_tasks = completed_tasks
            mission.failed_tasks = failed_tasks
            mission.progress = mission.calculate_progress()
            
            return {
                'mission': mission.to_dict(),
                'tasks': task_status,
                'summary': {
                    'total_tasks': mission.total_tasks,
                    'completed_tasks': completed_tasks,
                    'failed_tasks': failed_tasks,
                    'progress': mission.progress,
                    'is_overdue': mission.is_overdue()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get mission status {mission_id}: {e}")
            return None

    async def list_missions(self, status: Optional[MissionStatus] = None,
                          priority: Optional[MissionPriority] = None,
                          limit: int = 50) -> List[Dict[str, Any]]:
        """List missions with optional filtering"""
        try:
            missions = []
            
            for mission in self.missions.values():
                # Apply filters
                if status and mission.status != status:
                    continue
                if priority and mission.priority != priority:
                    continue
                    
                missions.append({
                    'id': mission.id,
                    'name': mission.name,
                    'status': mission.status.value,
                    'priority': mission.priority.value,
                    'progress': mission.progress,
                    'created_at': mission.created_at.isoformat(),
                    'started_at': mission.started_at.isoformat() if mission.started_at else None,
                    'deadline': mission.deadline.isoformat() if mission.deadline else None,
                    'is_overdue': mission.is_overdue()
                })
            
            # Sort by priority then creation time
            priority_order = {
                MissionPriority.URGENT: 3,
                MissionPriority.HIGH: 2,
                MissionPriority.NORMAL: 1,
                MissionPriority.LOW: 0
            }
            
            missions.sort(key=lambda m: (
                priority_order.get(MissionPriority(m['priority']), 0),
                m['created_at']
            ), reverse=True)
            
            return missions[:limit]
            
        except Exception as e:
            logger.error(f"Failed to list missions: {e}")
            return []

    async def start_monitoring(self) -> None:
        """Start mission monitoring loop"""
        if self._monitoring:
            return
            
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_missions())
        logger.info("Mission monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop mission monitoring"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Mission monitoring stopped")

    # Private methods

    async def _monitor_missions(self) -> None:
        """Monitor running missions and update their status"""
        while self._monitoring:
            try:
                for mission_id, mission in self.missions.items():
                    if mission.status == MissionStatus.RUNNING:
                        await self._check_mission_progress(mission_id)
                        
                await asyncio.sleep(self.config['monitor_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in mission monitoring: {e}")
                await asyncio.sleep(5)

    async def _check_mission_progress(self, mission_id: str) -> None:
        """Check and update mission progress"""
        try:
            mission = self.missions[mission_id]
            tasks = await self.task_queue.get_mission_tasks(mission_id)
            
            completed_tasks = 0
            failed_tasks = 0
            running_tasks = 0
            
            for task in tasks:
                if task.status == TaskStatus.COMPLETED:
                    completed_tasks += 1
                elif task.status == TaskStatus.FAILED:
                    failed_tasks += 1
                elif task.status == TaskStatus.RUNNING:
                    running_tasks += 1
            
            # Update mission metrics
            mission.completed_tasks = completed_tasks
            mission.failed_tasks = failed_tasks
            mission.progress = mission.calculate_progress()
            mission.updated_at = datetime.utcnow()
            
            # Check if mission should change status
            old_status = mission.status
            
            if completed_tasks == mission.total_tasks:
                # All tasks completed
                mission.status = MissionStatus.COMPLETED
                mission.completed_at = datetime.utcnow()
                
            elif failed_tasks > 0 and running_tasks == 0:
                # Some tasks failed and none running
                if completed_tasks > 0:
                    mission.status = MissionStatus.PARTIAL
                else:
                    mission.status = MissionStatus.FAILED
                mission.completed_at = datetime.utcnow()
            
            # Emit status change event if needed
            if old_status != mission.status:
                event_type = {
                    MissionStatus.COMPLETED: EventType.MISSION_COMPLETED,
                    MissionStatus.FAILED: EventType.MISSION_FAILED,
                    MissionStatus.PARTIAL: EventType.MISSION_COMPLETED  # Partial is still completion
                }.get(mission.status)
                
                if event_type:
                    await self.event_stream.publish_event({
                        'id': str(uuid.uuid4()),
                        'type': event_type,
                        'source': 'mission_controller',
                        'target': None,
                        'payload': {
                            'mission_id': mission_id,
                            'name': mission.name,
                            'final_status': mission.status.value,
                            'completed_tasks': completed_tasks,
                            'failed_tasks': failed_tasks,
                            'total_tasks': mission.total_tasks
                        },
                        'timestamp': datetime.utcnow(),
                        'mission_id': mission_id
                    })
                
                logger.info(f"Mission {mission_id} status changed: {old_status} -> {mission.status}")
                
        except Exception as e:
            logger.error(f"Error checking mission progress {mission_id}: {e}")


# Export public interface
__all__ = [
    'MissionController', 'Mission', 'MissionObjective', 
    'MissionStatus', 'MissionPriority'
]
