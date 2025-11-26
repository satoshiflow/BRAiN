# backend/mission_control_core/__init__.py
"""
BRAIN Mission Control Core
==========================

Thin wrapper um das Core-Paket.

WICHTIG:
- Im neuen BRAIN-Backend nutzen wir NUR die low-level Primitives aus
  `mission_control_core.core`.
- Die alte Standalone-FastAPI-App (`main.py` + `api/*`) wird hier NICHT
  mehr automatisch importiert, um Seiteneffekte und Import-Fehler zu vermeiden.
"""

from .core import (  # type: ignore[F401]
    EventStream,
    Event,
    EventType,
    emit_task_event,
    emit_agent_event,
    TaskQueue,
    Task,
    TaskStatus,
    TaskPriority,
    Orchestrator,
    AgentCapability,
    AgentMetrics,
    AgentStatus,
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
