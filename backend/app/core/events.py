"""
Event Broadcasting System

Helper functions for broadcasting events via WebSocket.

Channels:
- missions - Mission status updates
- agents - Agent state changes
- system - System events and announcements
- tasks - Background task updates

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from loguru import logger

from backend.app.core.websocket import get_websocket_manager


# ============================================================================
# Event Channels
# ============================================================================

class EventChannel(str, Enum):
    """Standard event channels."""

    MISSIONS = "missions"
    AGENTS = "agents"
    SYSTEM = "system"
    TASKS = "tasks"
    AUDIT = "audit"
    METRICS = "metrics"


# ============================================================================
# Event Types
# ============================================================================

class EventType(str, Enum):
    """Standard event types."""

    # Mission events
    MISSION_CREATED = "mission_created"
    MISSION_STARTED = "mission_started"
    MISSION_COMPLETED = "mission_completed"
    MISSION_FAILED = "mission_failed"
    MISSION_CANCELLED = "mission_cancelled"

    # Agent events
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_HEARTBEAT = "agent_heartbeat"
    AGENT_ERROR = "agent_error"

    # System events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_HEALTH = "system_health"
    SYSTEM_ALERT = "system_alert"

    # Task events
    TASK_QUEUED = "task_queued"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Audit events
    AUDIT_LOG = "audit_log"

    # Metrics events
    METRICS_UPDATE = "metrics_update"


# ============================================================================
# Event Emitters
# ============================================================================

async def emit_event(
    channel: str | EventChannel,
    event_type: str | EventType,
    data: Dict[str, Any],
    user_id: Optional[str] = None,
):
    """
    Emit event to WebSocket channel.

    Args:
        channel: Target channel (or EventChannel enum)
        event_type: Event type (or EventType enum)
        data: Event payload
        user_id: Optional user ID for user-specific events
    """
    try:
        manager = get_websocket_manager()

        # Convert enums to strings
        if isinstance(channel, EventChannel):
            channel = channel.value
        if isinstance(event_type, EventType):
            event_type = event_type.value

        message = {
            "type": event_type,
            "data": data,
        }

        if user_id:
            # Send to specific user
            await manager.send_to_user(user_id, message)
        else:
            # Broadcast to channel
            await manager.broadcast_to_channel(channel, message)

        logger.debug(f"Event emitted: {channel}/{event_type}")

    except Exception as e:
        logger.error(f"Failed to emit event {event_type}: {e}")


async def emit_system_event(
    event_type: str | EventType,
    data: Dict[str, Any],
):
    """
    Emit system event.

    Args:
        event_type: Event type
        data: Event payload
    """
    await emit_event(EventChannel.SYSTEM, event_type, data)


# ============================================================================
# Mission Events
# ============================================================================

async def emit_mission_created(mission_id: str, mission_data: Dict[str, Any]):
    """Emit mission created event."""
    await emit_event(
        EventChannel.MISSIONS,
        EventType.MISSION_CREATED,
        {
            "mission_id": mission_id,
            **mission_data,
        },
    )


async def emit_mission_started(mission_id: str):
    """Emit mission started event."""
    await emit_event(
        EventChannel.MISSIONS,
        EventType.MISSION_STARTED,
        {"mission_id": mission_id},
    )


async def emit_mission_completed(mission_id: str, result: Optional[Dict[str, Any]] = None):
    """Emit mission completed event."""
    await emit_event(
        EventChannel.MISSIONS,
        EventType.MISSION_COMPLETED,
        {
            "mission_id": mission_id,
            "result": result,
        },
    )


async def emit_mission_failed(mission_id: str, error: str):
    """Emit mission failed event."""
    await emit_event(
        EventChannel.MISSIONS,
        EventType.MISSION_FAILED,
        {
            "mission_id": mission_id,
            "error": error,
        },
    )


async def emit_mission_cancelled(mission_id: str, reason: Optional[str] = None):
    """Emit mission cancelled event."""
    await emit_event(
        EventChannel.MISSIONS,
        EventType.MISSION_CANCELLED,
        {
            "mission_id": mission_id,
            "reason": reason,
        },
    )


# ============================================================================
# Agent Events
# ============================================================================

async def emit_agent_started(agent_id: str):
    """Emit agent started event."""
    await emit_event(
        EventChannel.AGENTS,
        EventType.AGENT_STARTED,
        {"agent_id": agent_id},
    )


async def emit_agent_stopped(agent_id: str):
    """Emit agent stopped event."""
    await emit_event(
        EventChannel.AGENTS,
        EventType.AGENT_STOPPED,
        {"agent_id": agent_id},
    )


async def emit_agent_heartbeat(agent_id: str, status: Dict[str, Any]):
    """Emit agent heartbeat event."""
    await emit_event(
        EventChannel.AGENTS,
        EventType.AGENT_HEARTBEAT,
        {
            "agent_id": agent_id,
            "status": status,
        },
    )


async def emit_agent_error(agent_id: str, error: str):
    """Emit agent error event."""
    await emit_event(
        EventChannel.AGENTS,
        EventType.AGENT_ERROR,
        {
            "agent_id": agent_id,
            "error": error,
        },
    )


# ============================================================================
# System Events
# ============================================================================

async def emit_system_startup():
    """Emit system startup event."""
    await emit_system_event(
        EventType.SYSTEM_STARTUP,
        {"status": "started"},
    )


async def emit_system_shutdown():
    """Emit system shutdown event."""
    await emit_system_event(
        EventType.SYSTEM_SHUTDOWN,
        {"status": "stopping"},
    )


async def emit_system_health(health_status: Dict[str, Any]):
    """Emit system health event."""
    await emit_system_event(
        EventType.SYSTEM_HEALTH,
        health_status,
    )


async def emit_system_alert(
    level: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
):
    """Emit system alert event."""
    await emit_system_event(
        EventType.SYSTEM_ALERT,
        {
            "level": level,
            "message": message,
            "details": details or {},
        },
    )


# ============================================================================
# Task Events
# ============================================================================

async def emit_task_queued(task_id: str, task_name: str):
    """Emit task queued event."""
    await emit_event(
        EventChannel.TASKS,
        EventType.TASK_QUEUED,
        {
            "task_id": task_id,
            "task_name": task_name,
        },
    )


async def emit_task_started(task_id: str, task_name: str):
    """Emit task started event."""
    await emit_event(
        EventChannel.TASKS,
        EventType.TASK_STARTED,
        {
            "task_id": task_id,
            "task_name": task_name,
        },
    )


async def emit_task_completed(task_id: str, task_name: str, result: Optional[Dict[str, Any]] = None):
    """Emit task completed event."""
    await emit_event(
        EventChannel.TASKS,
        EventType.TASK_COMPLETED,
        {
            "task_id": task_id,
            "task_name": task_name,
            "result": result,
        },
    )


async def emit_task_failed(task_id: str, task_name: str, error: str):
    """Emit task failed event."""
    await emit_event(
        EventChannel.TASKS,
        EventType.TASK_FAILED,
        {
            "task_id": task_id,
            "task_name": task_name,
            "error": error,
        },
    )


# ============================================================================
# Metrics Events
# ============================================================================

async def emit_metrics_update(metrics: Dict[str, Any]):
    """Emit metrics update event."""
    await emit_event(
        EventChannel.METRICS,
        EventType.METRICS_UPDATE,
        metrics,
    )


# ============================================================================
# Audit Events
# ============================================================================

async def emit_audit_log(
    action: str,
    user_id: Optional[str],
    resource: Optional[str],
    details: Optional[Dict[str, Any]] = None,
):
    """Emit audit log event."""
    await emit_event(
        EventChannel.AUDIT,
        EventType.AUDIT_LOG,
        {
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "details": details or {},
        },
    )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "EventChannel",
    "EventType",
    "emit_event",
    "emit_system_event",
    "emit_mission_created",
    "emit_mission_started",
    "emit_mission_completed",
    "emit_mission_failed",
    "emit_mission_cancelled",
    "emit_agent_started",
    "emit_agent_stopped",
    "emit_agent_heartbeat",
    "emit_agent_error",
    "emit_system_startup",
    "emit_system_shutdown",
    "emit_system_health",
    "emit_system_alert",
    "emit_task_queued",
    "emit_task_started",
    "emit_task_completed",
    "emit_task_failed",
    "emit_metrics_update",
    "emit_audit_log",
]
