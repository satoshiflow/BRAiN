"""
BRAIN Mission System V1 - Core Models
=====================================

This module defines the core data models for the BRAIN mission system,
implementing Pydantic models for type safety and validation.

Key concepts:
- Mission: High-level task that can contain multiple tasks
- MissionTask: Individual executable unit within a mission
- MissionResult: Outcome and metadata from mission execution
- KarmaEvent: KARMA system integration for mission evaluation

Architecture Philosophy:
- Bio-inspired: Missions flow like neural impulses
- Myzelkapitalismus: Cooperative resource sharing
- KARMA-driven: Every mission is evaluated for impact

Author: Claude (Chief Developer)
Project: BRAIN Framework by FalkLabs / Olaf Falk
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


class MissionStatus(str, Enum):
    """
    Mission lifecycle states following biological inspiration
    """
    PENDING = "pending"      # Mission created, waiting for assignment
    ASSIGNED = "assigned"    # Assigned to agent, not yet started
    RUNNING = "running"      # Currently being executed
    PAUSED = "paused"       # Temporarily suspended
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"       # Execution failed
    CANCELLED = "cancelled" # Manually cancelled
    TIMEOUT = "timeout"     # Exceeded time limit


class MissionPriority(int, Enum):
    """
    Priority levels inspired by neural urgency signals
    """
    LOW = 1
    NORMAL = 3
    HIGH = 5
    URGENT = 7
    CRITICAL = 9


class MissionType(str, Enum):
    """
    Categories of missions in the BRAIN ecosystem
    """
    ANALYSIS = "analysis"           # Data analysis tasks
    COMMUNICATION = "communication" # Inter-agent communication
    EXECUTION = "execution"         # System operations
    LEARNING = "learning"          # Knowledge acquisition
    COORDINATION = "coordination"   # Multi-agent coordination
    MAINTENANCE = "maintenance"     # System health tasks
    CREATION = "creation"          # Genesis tasks (future)


class AgentRequirement(BaseModel):
    """
    Defines what type of agent is needed for a mission
    """
    agent_type: str = Field(..., description="Type of agent required")
    skills_required: List[str] = Field(default=[], description="Required skills")
    min_karma_score: Optional[float] = Field(default=None, description="Minimum KARMA score")
    exclude_agents: List[str] = Field(default=[], description="Agents to exclude")


class MissionTask(BaseModel):
    """
    Individual executable task within a mission
    Represents atomic units of work
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Human-readable task name")
    description: str = Field(..., description="Detailed task description")
    task_type: str = Field(..., description="Type of task to execute")
    parameters: Dict[str, Any] = Field(default={}, description="Task execution parameters")
    dependencies: List[str] = Field(default=[], description="IDs of tasks that must complete first")
    estimated_duration: Optional[int] = Field(default=None, description="Expected duration in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    current_retries: int = Field(default=0, description="Current retry count")
    
    # Execution tracking
    assigned_agent: Optional[str] = Field(default=None, description="ID of assigned agent")
    started_at: Optional[datetime] = Field(default=None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Task completion timestamp")
    status: MissionStatus = Field(default=MissionStatus.PENDING)
    
    # Results
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task execution result")
    error_message: Optional[str] = Field(default=None, description="Error details if failed")


class Mission(BaseModel):
    """
    High-level mission representing a coordinated set of tasks
    Core entity in the BRAIN mission system
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Mission name")
    description: str = Field(..., description="Mission description")
    mission_type: MissionType = Field(..., description="Category of mission")
    priority: MissionPriority = Field(default=MissionPriority.NORMAL)
    
    # Mission structure
    tasks: List[MissionTask] = Field(default=[], description="List of tasks in this mission")
    agent_requirements: AgentRequirement = Field(..., description="Agent selection criteria")
    
    # Execution tracking
    status: MissionStatus = Field(default=MissionStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Assignment
    assigned_agent_id: Optional[str] = Field(default=None, description="Primary agent assigned")
    assigned_agents: List[str] = Field(default=[], description="All agents involved")
    
    # Context and metadata
    context: Dict[str, Any] = Field(default={}, description="Mission context data")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")
    
    # Resource management (BRAIN Credit System integration)
    estimated_credits: Optional[float] = Field(default=None, description="Estimated credit cost")
    actual_credits: Optional[float] = Field(default=None, description="Actual credits consumed")
    
    # Outcomes
    result: Optional[Dict[str, Any]] = Field(default=None, description="Mission results")
    error_message: Optional[str] = Field(default=None, description="Error details if failed")
    
    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        return datetime.utcnow()
    
    def add_task(self, task: MissionTask) -> None:
        """Add a task to this mission"""
        self.tasks.append(task)
        self.updated_at = datetime.utcnow()
    
    def get_pending_tasks(self) -> List[MissionTask]:
        """Get all tasks that are ready to execute (dependencies met)"""
        completed_task_ids = {
            task.id for task in self.tasks 
            if task.status == MissionStatus.COMPLETED
        }
        
        return [
            task for task in self.tasks
            if (task.status == MissionStatus.PENDING and
                all(dep_id in completed_task_ids for dep_id in task.dependencies))
        ]
    
    def calculate_progress(self) -> float:
        """Calculate mission completion percentage"""
        if not self.tasks:
            return 0.0
        
        completed = sum(1 for task in self.tasks if task.status == MissionStatus.COMPLETED)
        return (completed / len(self.tasks)) * 100.0


class MissionResult(BaseModel):
    """
    Comprehensive result of mission execution
    """
    mission_id: str = Field(..., description="ID of the executed mission")
    execution_start: datetime = Field(..., description="When execution began")
    execution_end: datetime = Field(..., description="When execution completed")
    final_status: MissionStatus = Field(..., description="Final mission status")
    
    # Performance metrics
    total_tasks: int = Field(..., description="Total number of tasks")
    completed_tasks: int = Field(..., description="Successfully completed tasks")
    failed_tasks: int = Field(..., description="Failed tasks")
    execution_time: float = Field(..., description="Total execution time in seconds")
    
    # Resource consumption
    credits_consumed: float = Field(default=0.0, description="Total credits used")
    agents_involved: List[str] = Field(default=[], description="List of agent IDs involved")
    
    # Results and artifacts
    outputs: Dict[str, Any] = Field(default={}, description="Mission outputs")
    artifacts: List[str] = Field(default=[], description="Generated artifacts")
    
    # Error tracking
    errors: List[Dict[str, Any]] = Field(default=[], description="Errors encountered")
    warnings: List[str] = Field(default=[], description="Warnings generated")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class KarmaEvent(BaseModel):
    """
    KARMA system integration for mission evaluation
    Represents ethical and impact scoring of missions
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str = Field(..., description="Related mission ID")
    agent_id: str = Field(..., description="Agent responsible")
    
    # KARMA scoring dimensions
    efficiency_score: float = Field(..., ge=0, le=1, description="Task efficiency (0-1)")
    impact_score: float = Field(..., ge=-1, le=1, description="Positive/negative impact (-1 to 1)")
    empathy_score: float = Field(..., ge=0, le=1, description="Empathetic consideration (0-1)")
    sustainability_score: float = Field(..., ge=0, le=1, description="Long-term sustainability (0-1)")
    
    # Calculated overall KARMA
    total_karma: Optional[float] = Field(default=None, description="Weighted total KARMA score")
    
    # Context
    evaluation_criteria: List[str] = Field(default=[], description="Criteria used for evaluation")
    evaluator_agent: Optional[str] = Field(default=None, description="Agent that performed evaluation")
    evaluation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Feedback
    feedback: Optional[str] = Field(default=None, description="Qualitative feedback")
    improvement_suggestions: List[str] = Field(default=[], description="Suggestions for improvement")
    
    @validator('total_karma', pre=True, always=True)
    def calculate_total_karma(cls, v, values):
        """Calculate weighted total KARMA score"""
        if v is not None:
            return v
        
        # BRAIN Framework KARMA calculation
        # Weights: efficiency (30%), impact (40%), empathy (20%), sustainability (10%)
        efficiency = values.get('efficiency_score', 0) * 0.3
        impact = values.get('impact_score', 0) * 0.4
        empathy = values.get('empathy_score', 0) * 0.2
        sustainability = values.get('sustainability_score', 0) * 0.1
        
        return efficiency + impact + empathy + sustainability


class MissionQueue(BaseModel):
    """
    Represents a mission in the execution queue
    """
    mission_id: str = Field(..., description="Mission identifier")
    priority: MissionPriority = Field(..., description="Mission priority")
    queued_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_start: Optional[datetime] = Field(default=None, description="Estimated start time")
    agent_preferences: List[str] = Field(default=[], description="Preferred agent types")


class MissionLog(BaseModel):
    """
    Log entry for mission execution tracking
    """
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str = Field(..., description="Related mission ID")
    task_id: Optional[str] = Field(default=None, description="Related task ID if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str = Field(..., description="Log level (INFO, WARNING, ERROR, DEBUG)")
    message: str = Field(..., description="Log message")
    agent_id: Optional[str] = Field(default=None, description="Agent that generated the log")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional structured data")


# Export all models
__all__ = [
    'Mission', 'MissionTask', 'MissionResult', 'KarmaEvent', 'MissionQueue', 'MissionLog',
    'MissionStatus', 'MissionPriority', 'MissionType', 'AgentRequirement'
]
