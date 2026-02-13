"""
BRAIN Mission System V1 - Mission Orchestrator
==============================================

Central orchestration engine for mission planning, agent assignment, and task routing.
Implements bio-inspired scheduling algorithms and agent selection logic.

Key Features:
- Intelligent agent selection based on skills and KARMA
- Task dependency resolution
- Load balancing across agents
- Mission decomposition and optimization
- Real-time coordination

Architecture Philosophy:
- Neural pathway simulation for task routing
- Mycelial network principles for agent coordination
- Emergent intelligence through distributed decision making

Author: Claude (Chief Developer)
Project: BRAIN Framework by FalkLabs / Olaf Falk
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import json

from .models import (
    Mission, MissionTask, MissionStatus, MissionPriority, MissionType,
    AgentRequirement
)
from .queue import MissionQueueManager


logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent availability status"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


@dataclass
class AgentProfile:
    """
    Represents an agent in the BRAIN ecosystem with capabilities and metrics.
    """
    agent_id: str
    agent_type: str
    skills: List[str]
    status: AgentStatus
    karma_score: float
    load_factor: float  # 0.0 = idle, 1.0 = fully loaded
    last_active: datetime
    success_rate: float
    average_task_time: float
    specializations: List[str]
    preferences: Dict[str, Any]
    
    def can_handle_mission(self, mission: Mission) -> bool:
        """Check if this agent can handle the given mission"""
        requirements = mission.agent_requirements
        
        # Check agent type match
        if requirements.agent_type and requirements.agent_type != self.agent_type:
            return False
        
        # Check required skills
        if requirements.skills_required:
            if not all(skill in self.skills for skill in requirements.skills_required):
                return False
        
        # Check minimum KARMA score
        if requirements.min_karma_score and self.karma_score < requirements.min_karma_score:
            return False
        
        # Check exclusion list
        if self.agent_id in requirements.exclude_agents:
            return False
        
        return True
    
    def calculate_suitability_score(self, mission: Mission) -> float:
        """
        Calculate how well-suited this agent is for the mission.
        Returns score between 0.0 and 1.0.
        """
        if not self.can_handle_mission(mission):
            return 0.0
        
        # Base score factors
        karma_factor = min(self.karma_score, 1.0) * 0.3
        success_factor = self.success_rate * 0.3
        load_factor = (1.0 - self.load_factor) * 0.2  # Lower load = better score
        
        # Skill match bonus
        required_skills = set(mission.agent_requirements.skills_required or [])
        agent_skills = set(self.skills)
        if required_skills:
            skill_match = len(required_skills & agent_skills) / len(required_skills)
        else:
            skill_match = 1.0
        skill_factor = skill_match * 0.2
        
        return karma_factor + success_factor + load_factor + skill_factor


class MissionOrchestrator:
    """
    Central orchestrator for mission management and agent coordination.
    Implements intelligent scheduling and resource allocation.
    """
    
    def __init__(self, queue_manager: MissionQueueManager):
        """
        Initialize the orchestrator.
        
        Args:
            queue_manager: Mission queue management instance
        """
        self.queue_manager = queue_manager
        self.agents: Dict[str, AgentProfile] = {}
        self.active_missions: Dict[str, Mission] = {}
        self.mission_assignments: Dict[str, str] = {}  # mission_id -> agent_id
        
        # Orchestration settings
        self.max_concurrent_missions_per_agent = 3
        self.agent_discovery_interval = 30  # seconds
        self.load_balancing_enabled = True
        self.priority_boost_threshold = timedelta(minutes=10)
        
        # Performance tracking
        self.orchestration_metrics = {
            "missions_assigned": 0,
            "assignments_failed": 0,
            "agents_discovered": 0,
            "last_orchestration": None
        }
    
    async def start(self) -> None:
        """Start the orchestration engine"""
        logger.info("Starting Mission Orchestrator")
        
        # Start background tasks
        asyncio.create_task(self._orchestration_loop())
        asyncio.create_task(self._agent_discovery_loop())
        asyncio.create_task(self._health_monitoring_loop())
        
        logger.info("Mission Orchestrator started successfully")
    
    async def register_agent(self, agent_profile: AgentProfile) -> bool:
        """
        Register a new agent with the orchestrator.
        
        Args:
            agent_profile: Agent to register
            
        Returns:
            True if successfully registered
        """
        try:
            self.agents[agent_profile.agent_id] = agent_profile
            self.orchestration_metrics["agents_discovered"] += 1
            
            logger.info(f"Agent {agent_profile.agent_id} registered: "
                       f"type={agent_profile.agent_type}, "
                       f"skills={agent_profile.skills}, "
                       f"karma={agent_profile.karma_score:.2f}")
            
            # Trigger immediate orchestration check
            asyncio.create_task(self._try_assign_pending_missions())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_profile.agent_id}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Remove agent from orchestration.
        
        Args:
            agent_id: Agent to remove
            
        Returns:
            True if successfully removed
        """
        try:
            if agent_id in self.agents:
                # Check for active assignments
                active_missions = [
                    mission_id for mission_id, assigned_agent 
                    in self.mission_assignments.items() 
                    if assigned_agent == agent_id
                ]
                
                if active_missions:
                    logger.warning(f"Agent {agent_id} has active missions: {active_missions}")
                    # In production, we'd implement graceful handover
                
                del self.agents[agent_id]
                
                # Clean up assignments
                for mission_id in active_missions:
                    if mission_id in self.mission_assignments:
                        del self.mission_assignments[mission_id]
                
                logger.info(f"Agent {agent_id} unregistered")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
    
    async def submit_mission(self, mission: Mission) -> bool:
        """
        Submit a new mission for orchestration.
        
        Args:
            mission: Mission to submit
            
        Returns:
            True if successfully submitted
        """
        try:
            # Validate mission
            if not self._validate_mission(mission):
                logger.error(f"Mission validation failed: {mission.id}")
                return False
            
            # Decompose complex missions into tasks if needed
            await self._decompose_mission(mission)
            
            # Calculate resource requirements
            await self._estimate_mission_resources(mission)
            
            # Submit to queue
            success = await self.queue_manager.enqueue_mission(mission)
            
            if success:
                self.active_missions[mission.id] = mission
                logger.info(f"Mission {mission.id} ({mission.name}) submitted successfully")
                
                # Try immediate assignment
                asyncio.create_task(self._try_assign_mission(mission.id))
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to submit mission {mission.id}: {e}")
            return False
    
    async def update_agent_status(
        self, 
        agent_id: str, 
        status: AgentStatus,
        load_factor: Optional[float] = None
    ) -> bool:
        """
        Update agent status and availability.
        
        Args:
            agent_id: Agent to update
            status: New status
            load_factor: Current load (0.0-1.0)
            
        Returns:
            True if successfully updated
        """
        try:
            if agent_id not in self.agents:
                logger.warning(f"Unknown agent {agent_id} status update")
                return False
            
            agent = self.agents[agent_id]
            agent.status = status
            agent.last_active = datetime.utcnow()
            
            if load_factor is not None:
                agent.load_factor = max(0.0, min(1.0, load_factor))
            
            logger.debug(f"Agent {agent_id} status: {status}, load: {agent.load_factor:.2f}")
            
            # If agent became available, try to assign pending missions
            if status == AgentStatus.AVAILABLE:
                asyncio.create_task(self._try_assign_pending_missions())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update agent {agent_id} status: {e}")
            return False
    
    async def get_orchestration_status(self) -> Dict[str, Any]:
        """
        Get current orchestration status and metrics.
        
        Returns:
            Status information dictionary
        """
        try:
            # Count agents by status
            agent_counts = {}
            for agent in self.agents.values():
                status = agent.status.value
                agent_counts[status] = agent_counts.get(status, 0) + 1
            
            # Get queue statistics
            queue_stats = await self.queue_manager.get_queue_statistics()
            
            # Calculate system load
            total_agents = len(self.agents)
            busy_agents = sum(1 for agent in self.agents.values() 
                            if agent.status == AgentStatus.BUSY)
            system_load = busy_agents / total_agents if total_agents > 0 else 0.0
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "agents": {
                    "total": total_agents,
                    "by_status": agent_counts,
                    "system_load": system_load
                },
                "missions": {
                    "active": len(self.active_missions),
                    "assignments": len(self.mission_assignments)
                },
                "queue_statistics": queue_stats,
                "performance_metrics": self.orchestration_metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to get orchestration status: {e}")
            return {}
    
    async def _orchestration_loop(self) -> None:
        """Main orchestration loop for continuous mission assignment"""
        while True:
            try:
                await self._try_assign_pending_missions()
                await self._rebalance_assignments()
                await self._handle_priority_escalation()
                
                self.orchestration_metrics["last_orchestration"] = datetime.utcnow().isoformat()
                
                # Sleep before next iteration
                await asyncio.sleep(5)  # 5 second orchestration cycle
                
            except Exception as e:
                logger.error(f"Error in orchestration loop: {e}")
                await asyncio.sleep(10)  # Longer sleep on error
    
    async def _agent_discovery_loop(self) -> None:
        """Background loop for agent health checking and discovery"""
        while True:
            try:
                await self._health_check_agents()
                await self._discover_new_agents()
                
                await asyncio.sleep(self.agent_discovery_interval)
                
            except Exception as e:
                logger.error(f"Error in agent discovery loop: {e}")
                await asyncio.sleep(30)
    
    async def _health_monitoring_loop(self) -> None:
        """Monitor system health and performance"""
        while True:
            try:
                await self._monitor_mission_timeouts()
                await self._cleanup_completed_missions()
                await self._update_performance_metrics()
                
                await asyncio.sleep(60)  # 1 minute health check cycle
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _try_assign_pending_missions(self) -> None:
        """Try to assign all pending missions to available agents"""
        try:
            # Get available agents
            available_agents = [
                agent for agent in self.agents.values()
                if (agent.status == AgentStatus.AVAILABLE and 
                    agent.load_factor < 0.8)  # Don't overload agents
            ]
            
            if not available_agents:
                return
            
            # Get pending missions from queue (simplified - in reality we'd peek)
            # For this implementation, we'll track missions we're trying to assign
            pending_missions = [
                mission for mission in self.active_missions.values()
                if mission.status == MissionStatus.PENDING
            ]
            
            for mission in pending_missions:
                if await self._try_assign_mission(mission.id):
                    self.orchestration_metrics["missions_assigned"] += 1
                else:
                    self.orchestration_metrics["assignments_failed"] += 1
                    
        except Exception as e:
            logger.error(f"Error in mission assignment: {e}")
    
    async def _try_assign_mission(self, mission_id: str) -> bool:
        """
        Try to assign a specific mission to the best available agent.
        
        Args:
            mission_id: Mission to assign
            
        Returns:
            True if successfully assigned
        """
        try:
            if mission_id not in self.active_missions:
                logger.warning(f"Mission {mission_id} not found in active missions")
                return False
            
            mission = self.active_missions[mission_id]
            
            if mission.status != MissionStatus.PENDING:
                return False  # Mission already assigned or completed
            
            # Find suitable agents
            suitable_agents = []
            for agent in self.agents.values():
                if (agent.status == AgentStatus.AVAILABLE and
                    agent.load_factor < 0.9 and
                    agent.can_handle_mission(mission)):
                    
                    suitability = agent.calculate_suitability_score(mission)
                    suitable_agents.append((agent, suitability))
            
            if not suitable_agents:
                logger.debug(f"No suitable agents for mission {mission_id}")
                return False
            
            # Sort by suitability score (highest first)
            suitable_agents.sort(key=lambda x: x[1], reverse=True)
            
            # Select best agent (could implement more sophisticated logic)
            best_agent, score = suitable_agents[0]
            
            # Attempt assignment through queue manager
            # Simulate agent requesting mission
            assigned_mission = await self.queue_manager.dequeue_mission(
                best_agent.agent_id,
                best_agent.skills
            )
            
            if assigned_mission and assigned_mission.id == mission_id:
                # Update tracking
                self.mission_assignments[mission_id] = best_agent.agent_id
                mission.status = MissionStatus.ASSIGNED
                mission.assigned_agent_id = best_agent.agent_id
                
                # Update agent status
                best_agent.status = AgentStatus.BUSY
                best_agent.load_factor = min(1.0, best_agent.load_factor + 0.3)
                
                logger.info(f"Mission {mission_id} assigned to agent {best_agent.agent_id} "
                           f"(suitability: {score:.3f})")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to assign mission {mission_id}: {e}")
            return False
    
    async def _rebalance_assignments(self) -> None:
        """Rebalance mission assignments across agents for optimal performance"""
        if not self.load_balancing_enabled:
            return
        
        try:
            # Simple load balancing - could be enhanced with more sophisticated algorithms
            overloaded_agents = [
                agent for agent in self.agents.values()
                if agent.load_factor > 0.8 and agent.status == AgentStatus.BUSY
            ]
            
            underutilized_agents = [
                agent for agent in self.agents.values()
                if agent.load_factor < 0.3 and agent.status == AgentStatus.AVAILABLE
            ]
            
            # In a full implementation, we'd implement mission migration logic here
            if overloaded_agents and underutilized_agents:
                logger.debug(f"Load imbalance detected: "
                           f"{len(overloaded_agents)} overloaded, "
                           f"{len(underutilized_agents)} underutilized agents")
            
        except Exception as e:
            logger.error(f"Error in load balancing: {e}")
    
    async def _handle_priority_escalation(self) -> None:
        """Escalate priority of missions that have been waiting too long"""
        try:
            current_time = datetime.utcnow()
            
            for mission in self.active_missions.values():
                if mission.status == MissionStatus.PENDING:
                    wait_time = current_time - mission.created_at
                    
                    if wait_time > self.priority_boost_threshold:
                        # Escalate priority (but don't exceed maximum)
                        if mission.priority.value < MissionPriority.CRITICAL.value:
                            old_priority = mission.priority
                            new_priority_value = min(
                                mission.priority.value + 1,
                                MissionPriority.CRITICAL.value
                            )
                            mission.priority = MissionPriority(new_priority_value)
                            
                            logger.info(f"Escalated mission {mission.id} priority: "
                                       f"{old_priority.name} -> {mission.priority.name}")
                            
                            # Update in queue (would need queue manager support)
                            # For now, just log the escalation
            
        except Exception as e:
            logger.error(f"Error in priority escalation: {e}")
    
    def _validate_mission(self, mission: Mission) -> bool:
        """
        Validate mission structure and requirements.
        
        Args:
            mission: Mission to validate
            
        Returns:
            True if mission is valid
        """
        if not mission.name or not mission.description:
            logger.error("Mission missing name or description")
            return False
        
        if not mission.agent_requirements:
            logger.error("Mission missing agent requirements")
            return False
        
        # Validate tasks have no circular dependencies
        if mission.tasks and not self._validate_task_dependencies(mission.tasks):
            logger.error("Mission has circular task dependencies")
            return False
        
        return True
    
    def _validate_task_dependencies(self, tasks: List[MissionTask]) -> bool:
        """
        Check for circular dependencies in task list.
        
        Args:
            tasks: List of tasks to validate
            
        Returns:
            True if no circular dependencies found
        """
        task_ids = {task.id for task in tasks}
        
        # Check all dependencies exist
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    logger.error(f"Task {task.id} depends on non-existent task {dep_id}")
                    return False
        
        # Simple circular dependency detection using DFS
        def has_cycle(task_id: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            # Find the task
            task = next((t for t in tasks if t.id == task_id), None)
            if not task:
                return False
            
            for dep_id in task.dependencies:
                if dep_id not in visited:
                    if has_cycle(dep_id, visited, rec_stack):
                        return True
                elif dep_id in rec_stack:
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        visited: Set[str] = set()
        for task in tasks:
            if task.id not in visited:
                if has_cycle(task.id, visited, set()):
                    return False
        
        return True
    
    async def _decompose_mission(self, mission: Mission) -> None:
        """
        Break down complex missions into manageable tasks.
        
        Args:
            mission: Mission to decompose
        """
        # Simple decomposition logic - can be enhanced with AI
        if not mission.tasks and mission.mission_type == MissionType.ANALYSIS:
            # Create default analysis tasks
            data_task = MissionTask(
                name="Data Collection",
                description="Collect and prepare data for analysis",
                task_type="data_collection",
                parameters={"source": mission.context.get("data_source", "unknown")}
            )
            
            analysis_task = MissionTask(
                name="Data Analysis",
                description="Perform the requested analysis",
                task_type="analysis",
                dependencies=[data_task.id],
                parameters=mission.context
            )
            
            report_task = MissionTask(
                name="Report Generation",
                description="Generate analysis report",
                task_type="reporting",
                dependencies=[analysis_task.id],
                parameters={"format": "json"}
            )
            
            mission.tasks = [data_task, analysis_task, report_task]
    
    async def _estimate_mission_resources(self, mission: Mission) -> None:
        """
        Estimate resource requirements for mission planning.
        
        Args:
            mission: Mission to estimate
        """
        # Simple resource estimation - can be enhanced with ML
        base_credits = 10.0
        
        # Factor in mission complexity
        if mission.tasks:
            base_credits *= len(mission.tasks)
        
        # Factor in priority
        priority_multiplier = {
            MissionPriority.LOW: 0.8,
            MissionPriority.NORMAL: 1.0,
            MissionPriority.HIGH: 1.5,
            MissionPriority.URGENT: 2.0,
            MissionPriority.CRITICAL: 3.0
        }
        
        mission.estimated_credits = base_credits * priority_multiplier.get(
            mission.priority, 1.0
        )
    
    async def _health_check_agents(self) -> None:
        """Check agent health and availability"""
        current_time = datetime.utcnow()
        timeout_threshold = timedelta(minutes=5)
        
        for agent_id, agent in list(self.agents.items()):
            if current_time - agent.last_active > timeout_threshold:
                if agent.status != AgentStatus.OFFLINE:
                    logger.warning(f"Agent {agent_id} appears offline")
                    agent.status = AgentStatus.OFFLINE
                    
                    # Handle missions assigned to offline agent
                    await self._handle_agent_offline(agent_id)
    
    async def _discover_new_agents(self) -> None:
        """Discover new agents that may have come online"""
        # In a real implementation, this would query the agent registry
        # or listen to agent registration events
        pass
    
    async def _monitor_mission_timeouts(self) -> None:
        """Monitor for missions that have exceeded their expected duration"""
        current_time = datetime.utcnow()
        timeout_threshold = timedelta(hours=1)  # Default timeout
        
        for mission in self.active_missions.values():
            if (mission.status == MissionStatus.RUNNING and 
                mission.started_at and
                current_time - mission.started_at > timeout_threshold):
                
                logger.warning(f"Mission {mission.id} appears to have timed out")
                
                # Could implement automatic timeout handling here
                await self.queue_manager.update_mission_status(
                    mission.id,
                    MissionStatus.TIMEOUT,
                    error_message="Mission exceeded timeout threshold"
                )
    
    async def _cleanup_completed_missions(self) -> None:
        """Clean up completed missions from active tracking"""
        completed_missions = [
            mission_id for mission_id, mission in self.active_missions.items()
            if mission.status in [
                MissionStatus.COMPLETED, 
                MissionStatus.FAILED, 
                MissionStatus.CANCELLED,
                MissionStatus.TIMEOUT
            ]
        ]
        
        for mission_id in completed_missions:
            # Remove from active tracking (but keep in queue manager for history)
            if mission_id in self.active_missions:
                del self.active_missions[mission_id]
            
            if mission_id in self.mission_assignments:
                agent_id = self.mission_assignments[mission_id]
                
                # Update agent availability
                if agent_id in self.agents:
                    agent = self.agents[agent_id]
                    agent.load_factor = max(0.0, agent.load_factor - 0.3)
                    if agent.load_factor < 0.1:
                        agent.status = AgentStatus.AVAILABLE
                
                del self.mission_assignments[mission_id]
    
    async def _update_performance_metrics(self) -> None:
        """Update performance metrics for monitoring"""
        # Calculate success rates, average completion times, etc.
        # This would integrate with the KARMA system
        pass
    
    async def _handle_agent_offline(self, agent_id: str) -> None:
        """Handle an agent going offline"""
        # Find missions assigned to this agent
        affected_missions = [
            mission_id for mission_id, assigned_agent 
            in self.mission_assignments.items()
            if assigned_agent == agent_id
        ]
        
        for mission_id in affected_missions:
            logger.warning(f"Reassigning mission {mission_id} due to agent {agent_id} offline")
            
            # Mark for reassignment (simplified implementation)
            if mission_id in self.active_missions:
                mission = self.active_missions[mission_id]
                mission.status = MissionStatus.PENDING
                mission.assigned_agent_id = None
                
            # Remove assignment
            if mission_id in self.mission_assignments:
                del self.mission_assignments[mission_id]


# Create global orchestrator instance (will be initialized with queue manager)
orchestrator: Optional[MissionOrchestrator] = None


def get_orchestrator() -> MissionOrchestrator:
    """Get the global orchestrator instance"""
    global orchestrator
    if orchestrator is None:
        raise RuntimeError("Orchestrator not initialized. Call initialize_orchestrator() first.")
    return orchestrator


def initialize_orchestrator(queue_manager: MissionQueueManager) -> MissionOrchestrator:
    """Initialize the global orchestrator"""
    global orchestrator
    orchestrator = MissionOrchestrator(queue_manager)
    return orchestrator
