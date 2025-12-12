"""
BRAIN Mission Control Core - low-level primitives
-------------------------------------------------

Stellt die zentralen Bausteine aus dem Core-Paket zur Verfügung:

- EventStream / Event / EventType
- TaskQueue / Task / TaskStatus / TaskPriority
- Orchestrator / AgentCapability / AgentMetrics / AgentStatus
- MissionController / Mission / MissionObjective / MissionStatus / MissionPriority
"""

from .event_stream import (
    EventStream,
    Event,
    EventType,
    emit_task_event,
    emit_agent_event,
)

from .task_queue import (
    TaskQueue,
    Task,
    TaskStatus,
    TaskPriority,
)

from .orchestrator import (
    Orchestrator,
    AgentCapability,
    AgentMetrics,
    AgentStatus,
)

from .mission_control import (
    MissionController,
    Mission,
    MissionObjective,
    MissionStatus,
    MissionPriority,
)

__all__ = [
    # Event system
    "EventStream",
    "Event",
    "EventType",
    "emit_task_event",
    "emit_agent_event",

    # Task queue
    "TaskQueue",
    "Task",
    "TaskStatus",
    "TaskPriority",

    # Orchestrator
    "Orchestrator",
    "AgentCapability",
    "AgentMetrics",
    "AgentStatus",

    # Mission control
    "MissionController",
    "Mission",
    "MissionObjective",
    "MissionStatus",
    "MissionPriority",
]
