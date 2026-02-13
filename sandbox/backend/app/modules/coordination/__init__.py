"""
Multi-Agent Coordination System - Sprint 7A

Agent-to-agent communication, task delegation, shared knowledge,
and Constitution-based conflict resolution.

Architecture:
    MessageBus       → Async message passing between agents
    TaskDelegation   → Supervisor-mediated task assignment
    SharedKnowledge  → Cross-agent knowledge base
    ConflictResolver → Constitution + KARMA conflict resolution
"""

from .schemas import (
    AgentMessage,
    MessageType,
    CoordinationTask,
    TaskDelegationRequest,
    TaskDelegationResult,
    ConflictReport,
)

__all__ = [
    "AgentMessage",
    "MessageType",
    "CoordinationTask",
    "TaskDelegationRequest",
    "TaskDelegationResult",
    "ConflictReport",
]
