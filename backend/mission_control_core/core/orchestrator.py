"""
🎯 BRAIN Mission Control - Orchestrator Engine
Intelligent Agent Selection & Load Balancing

Philosophy: Myzelkapitalismus
- Optimal resource allocation based on agent capabilities
- Dynamic load balancing to prevent agent overload
- Self-healing agent health monitoring
- Cooperative task distribution
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from .task_queue import TaskQueue, Task, TaskStatus, TaskPriority

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent operational status"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class AgentCapability:
    """Agent capability definition"""
    name: str
    confidence: float  # 0.0 - 1.0
    max_concurrent: int = 1
    avg_execution_time: float = 60.0  # seconds


@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    agent_id: str
    status: AgentStatus
    capabilities: List[AgentCapability]
    current_tasks: int = 0
    max_tasks: int = 5
    success_rate: float = 1.0
    avg_response_time: float = 60.0
    last_heartbeat: datetime = None
    total_completed: int = 0
    total_failed: int = 0
    health_score: float = 1.0

    def __post_init__(self):
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.utcnow()

    def calculate_health_score(self) -> float:
        """Calculate overall agent health score (0.0 - 1.0)"""
        factors = []
        
        # Success rate factor (weight: 40%)
        factors.append(self.success_rate * 0.4)
        
        # Load factor (weight: 30%) - lower load = higher score
        if self.max_tasks > 0:
            load_factor = 1.0 - (self.current_tasks / self.max_tasks)
            factors.append(load_factor * 0.3)
        
        # Responsiveness factor (weight: 20%) - faster = better
        response_factor = min(1.0, 60.0 / max(1.0, self.avg_response_time))
        factors.append(response_factor * 0.2)
        
        # Availability factor (weight: 10%)
        heartbeat_age = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        availability_factor = 1.0 if heartbeat_age < 60 else max(0.0, 1.0 - (heartbeat_age - 60) / 300)
        factors.append(availability_factor * 0.1)
        
        self.health_score = sum(factors)
        return self.health_score

    def can_accept_task(self, task_type: str) -> bool:
        """Check if agent can accept a specific task type"""
        if self.status != AgentStatus.ONLINE:
            return False
            
        if self.current_tasks >= self.max_tasks:
            return False
            
        # Check capability
        for capability in self.capabilities:
            if capability.name == task_type:
                return capability.confidence > 0.5  # Minimum confidence threshold
                
        return False

    def get_capability_score(self, task_type: str) -> float:
        """Get agent's capability score for a task type"""
        for capability in self.capabilities:
            if capability.name == task_type:
                return capability.confidence
        return 0.0


class Orchestrator:
    """
    Mission Control Orchestrator
    Implements Myzelkapitalismus principles for optimal resource allocation
    """
    
    def __init__(self, task_queue: TaskQueue):
        self.task_queue = task_queue
        self.agents: Dict[str, AgentMetrics] = {}
        self._running = False
        self._orchestration_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.config = {
            'orchestration_interval': 5.0,  # seconds
            'agent_timeout': 300,            # seconds  
            'max_assignment_attempts': 3,
            'load_balancing_factor': 0.7,   # Weight for load vs capability
            'health_check_interval': 30,    # seconds
        }

    async def start(self) -> None:
        """Start the orchestration engine"""
        if self._running:
            return
            
        self._running = True
        self._orchestration_task = asyncio.create_task(self._orchestration_loop())
        logger.info("Orchestrator started")

    async def stop(self) -> None:
        """Stop the orchestration engine"""
        self._running = False
        if self._orchestration_task:
            self._orchestration_task.cancel()
            try:
                await self._orchestration_task
            except asyncio.CancelledError:
                pass
        logger.info("Orchestrator stopped")

    async def register_agent(self, agent_id: str, capabilities: List[AgentCapability], 
                           max_tasks: int = 5) -> bool:
        """Register a new agent with the orchestrator"""
        try:
            agent_metrics = AgentMetrics(
                agent_id=agent_id,
                status=AgentStatus.ONLINE,
                capabilities=capabilities,
                max_tasks=max_tasks
            )
            
            self.agents[agent_id] = agent_metrics
            logger.info(f"Agent {agent_id} registered with {len(capabilities)} capabilities")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent"""
        try:
            if agent_id in self.agents:
                # TODO: Reassign any running tasks
                del self.agents[agent_id]
                logger.info(f"Agent {agent_id} unregistered")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False

    async def update_agent_heartbeat(self, agent_id: str, 
                                   current_tasks: Optional[int] = None,
                                   metrics: Optional[Dict[str, Any]] = None) -> bool:
        """Update agent heartbeat and metrics"""
        try:
            if agent_id not in self.agents:
                return False
                
            agent = self.agents[agent_id]
            agent.last_heartbeat = datetime.utcnow()
            agent.status = AgentStatus.ONLINE
            
            if current_tasks is not None:
                agent.current_tasks = current_tasks
                
            if metrics:
                # Update performance metrics
                if 'success_rate' in metrics:
                    agent.success_rate = metrics['success_rate']
                if 'avg_response_time' in metrics:
                    agent.avg_response_time = metrics['avg_response_time']
                if 'total_completed' in metrics:
                    agent.total_completed = metrics['total_completed']
                if 'total_failed' in metrics:
                    agent.total_failed = metrics['total_failed']
            
            # Recalculate health score
            agent.calculate_health_score()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update heartbeat for agent {agent_id}: {e}")
            return False

    async def assign_task(self, task_id: str) -> Optional[str]:
        """
        Manually assign a specific task to the best available agent
        Returns agent_id if successful, None otherwise
        """
        try:
            task = await self.task_queue.get_task(task_id)
            if not task or task.status != TaskStatus.QUEUED:
                return None
                
            agent_id = await self._select_best_agent(task)
            if not agent_id:
                return None
                
            # Attempt assignment
            if await self._assign_task_to_agent(task, agent_id):
                return agent_id
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to assign task {task_id}: {e}")
            return None

    async def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        try:
            online_agents = sum(1 for a in self.agents.values() if a.status == AgentStatus.ONLINE)
            total_tasks = sum(a.current_tasks for a in self.agents.values())
            avg_health = sum(a.health_score for a in self.agents.values()) / max(1, len(self.agents))
            
            queue_stats = await self.task_queue.get_queue_stats()
            
            return {
                'agents': {
                    'total': len(self.agents),
                    'online': online_agents,
                    'offline': len(self.agents) - online_agents,
                    'avg_health_score': round(avg_health, 3),
                    'total_current_tasks': total_tasks,
                },
                'tasks': queue_stats,
                'orchestrator': {
                    'running': self._running,
                    'assignment_interval': self.config['orchestration_interval'],
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get orchestrator stats: {e}")
            return {}

    # Private methods

    async def _orchestration_loop(self) -> None:
        """Main orchestration loop - continuously assigns tasks to agents"""
        logger.info("Orchestration loop started")
        
        while self._running:
            try:
                # Health check agents
                await self._health_check_agents()
                
                # Assign pending tasks
                await self._assign_pending_tasks()
                
                # Wait before next iteration
                await asyncio.sleep(self.config['orchestration_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in orchestration loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def _health_check_agents(self) -> None:
        """Check agent health and update statuses"""
        now = datetime.utcnow()
        timeout = timedelta(seconds=self.config['agent_timeout'])
        
        for agent_id, agent in self.agents.items():
            # Check if agent is responsive
            if now - agent.last_heartbeat > timeout:
                if agent.status == AgentStatus.ONLINE:
                    agent.status = AgentStatus.OFFLINE
                    logger.warning(f"Agent {agent_id} marked as offline (no heartbeat)")
                    
                    # TODO: Reassign tasks from offline agents
                    
            # Recalculate health scores
            agent.calculate_health_score()

    async def _assign_pending_tasks(self) -> None:
        """Assign pending tasks to available agents"""
        try:
            # Get available agents sorted by health score
            available_agents = [
                (agent_id, agent) for agent_id, agent in self.agents.items()
                if agent.status == AgentStatus.ONLINE and agent.current_tasks < agent.max_tasks
            ]
            
            if not available_agents:
                return  # No agents available
                
            # Sort by health score (best first)
            available_agents.sort(key=lambda x: x[1].health_score, reverse=True)
            
            # Try to assign tasks to each available agent
            assignments_made = 0
            for agent_id, agent in available_agents:
                if agent.current_tasks >= agent.max_tasks:
                    continue
                    
                # Find suitable task for this agent
                task = await self._find_suitable_task(agent)
                if task:
                    if await self._assign_task_to_agent(task, agent_id):
                        assignments_made += 1
                        
            if assignments_made > 0:
                logger.info(f"Assigned {assignments_made} tasks to agents")
                
        except Exception as e:
            logger.error(f"Error assigning pending tasks: {e}")

    async def _find_suitable_task(self, agent: AgentMetrics) -> Optional[Task]:
        """Find the best suitable task for a specific agent"""
        try:
            # Get agent capabilities as set
            capabilities = {cap.name for cap in agent.capabilities}
            
            # Use task queue's dequeue method which handles priority and capability matching
            task = await self.task_queue.dequeue_task(agent.agent_id, capabilities)
            return task
            
        except Exception as e:
            logger.error(f"Error finding suitable task for agent {agent.agent_id}: {e}")
            return None

    async def _select_best_agent(self, task: Task) -> Optional[str]:
        """
        Select the best agent for a task using Myzelkapitalismus principles
        Balances capability, load, and health
        """
        try:
            # Get agents that can handle this task type
            candidate_agents = []
            
            for agent_id, agent in self.agents.items():
                if agent.can_accept_task(task.task_type or 'general'):
                    capability_score = agent.get_capability_score(task.task_type or 'general')
                    
                    # Calculate combined score
                    load_factor = 1.0 - (agent.current_tasks / agent.max_tasks)
                    
                    # Weighted combination: capability vs load vs health
                    combined_score = (
                        capability_score * 0.4 +           # 40% capability
                        load_factor * 0.3 +                # 30% load
                        agent.health_score * 0.3           # 30% health
                    )
                    
                    candidate_agents.append((agent_id, combined_score))
            
            if not candidate_agents:
                logger.warning(f"No agents available for task type: {task.task_type}")
                return None
                
            # Sort by score (best first) and return the best agent
            candidate_agents.sort(key=lambda x: x[1], reverse=True)
            best_agent_id = candidate_agents[0][0]
            
            logger.debug(f"Selected agent {best_agent_id} for task {task.id} (score: {candidate_agents[0][1]:.3f})")
            return best_agent_id
            
        except Exception as e:
            logger.error(f"Error selecting best agent for task {task.id}: {e}")
            return None

    async def _assign_task_to_agent(self, task: Task, agent_id: str) -> bool:
        """Assign task to agent and update tracking"""
        try:
            # Use task queue's assignment method
            success = await self.task_queue._assign_task_to_agent(task, agent_id)
            
            if success:
                # Update agent metrics
                if agent_id in self.agents:
                    self.agents[agent_id].current_tasks += 1
                    
                logger.info(f"Task {task.id} assigned to agent {agent_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to assign task {task.id} to agent {agent_id}: {e}")
            return False


# Export public interface
__all__ = ['Orchestrator', 'AgentCapability', 'AgentMetrics', 'AgentStatus']
