from datetime import datetime, timedelta
from typing import List, Optional, Callable, Dict, Any
import gc
import asyncio

from loguru import logger

from app.modules.immune.schemas import (
    ImmuneEvent,
    ImmuneHealthSummary,
    ImmuneSeverity,
    ImmuneEventType,
)

# EventStream integration (Sprint 3)
try:
    from backend.mission_control_core.core import EventStream, Event
except ImportError:
    EventStream = None
    Event = None
    import warnings
    warnings.warn(
        "[ImmuneService] EventStream not available (mission_control_core not installed)",
        RuntimeWarning
    )


class ImmuneService:
    """
    In-Memory Immunsystem with Self-Protection.

    Features:
    - Event tracking and health monitoring
    - Automatic self-protection responses to critical events
    - EventStream integration
    - Circuit breaker pattern for cascading failures
    - Resource management (garbage collection, backpressure)

    EventStream Integration:
    - immune.event_published: Every immune event
    - immune.critical_event: CRITICAL severity events
    - immune.self_protection_triggered: When self-protection activated
    """

    def __init__(
        self,
        event_stream: Optional["EventStream"] = None,
        enable_auto_protection: bool = True,
    ) -> None:
        self._events: List[ImmuneEvent] = []
        self._id_counter: int = 1
        self.event_stream = event_stream  # EventStream integration (Sprint 3)
        self.enable_auto_protection = enable_auto_protection

        # Self-protection state
        self.backpressure_enabled = False
        self.circuit_breaker_open = False
        self.protection_actions_log: List[Dict[str, Any]] = []

        logger.info(
            f"[ImmuneService] Initialized with auto_protection={'enabled' if enable_auto_protection else 'disabled'}"
        )

    async def _emit_event_safe(
        self,
        event_type: str,
        immune_event: ImmuneEvent,
    ) -> None:
        """
        Emit immune event with error handling (non-blocking).

        Charter v1.0 Compliance:
        - Event publishing MUST NOT block business logic
        - Failures are logged but NOT raised
        - Graceful degradation when EventStream unavailable
        """
        if self.event_stream is None or Event is None:
            logger.debug("[ImmuneService] EventStream not available, skipping event: %s", event_type)
            return

        try:
            # Build base payload
            payload = {
                "event_id": immune_event.id,
                "severity": immune_event.severity.value,
                "type": immune_event.type.value,
                "message": immune_event.message,
            }

            # Add optional fields
            if immune_event.agent_id:
                payload["agent_id"] = immune_event.agent_id
            if immune_event.module:
                payload["module"] = immune_event.module
            if immune_event.meta:
                payload["meta"] = immune_event.meta

            # Add timestamp
            timestamp_field = "critical_at" if event_type == "immune.critical_event" else "published_at"
            payload[timestamp_field] = immune_event.created_at.timestamp()

            # Create and publish event
            event = Event(
                type=event_type,
                source="immune_service",
                target=None,
                payload=payload,
            )

            await self.event_stream.publish(event)

            logger.debug(
                "[ImmuneService] Event published: %s (event_id=%s)",
                event_type,
                immune_event.id,
            )

        except Exception as e:
            logger.error(
                "[ImmuneService] Event publishing failed: %s (event_type=%s, event_id=%s)",
                e,
                event_type,
                immune_event.id,
                exc_info=True,
            )
            # DO NOT raise - business logic must continue

    async def publish_event(self, event: ImmuneEvent) -> int:
        now = datetime.utcnow()
        stored = ImmuneEvent(
            **event.model_dump(exclude={"id", "created_at"}),
            id=self._id_counter,
            created_at=now,
        )
        self._id_counter += 1
        self._events.append(stored)

        # EVENT: immune.event_published (always emit)
        await self._emit_event_safe(
            event_type="immune.event_published",
            immune_event=stored,
        )

        # EVENT: immune.critical_event (conditional: if severity is CRITICAL)
        if stored.severity == ImmuneSeverity.CRITICAL:
            await self._emit_event_safe(
                event_type="immune.critical_event",
                immune_event=stored,
            )

            # PHASE 3: Trigger self-protection for critical events
            if self.enable_auto_protection:
                await self.trigger_self_protection(stored)

        return stored.id

    def get_recent_events(self, minutes: int = 60) -> List[ImmuneEvent]:
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=minutes)
        return [e for e in self._events if e.created_at >= cutoff]

    def health_summary(self, minutes: int = 60) -> ImmuneHealthSummary:
        events = self.get_recent_events(minutes=minutes)
        active_issues = len(events)
        critical_issues = sum(1 for e in events if e.severity == ImmuneSeverity.CRITICAL)
        # letzte 10
        last_events = events[-10:]
        return ImmuneHealthSummary(
            active_issues=active_issues,
            critical_issues=critical_issues,
            last_events=last_events,
        )

    # =========================================================================
    # PHASE 3: SELF-PROTECTION FUNCTIONS
    # =========================================================================

    async def trigger_self_protection(self, event: ImmuneEvent):
        """
        Trigger automatic self-protection based on event type.

        Implements ChatGPT's "Immun- & Selbstschutz-Layer" concept:
        - Memory leaks → Garbage collection
        - Deadlocks → Restart affected agents
        - Overload → Enable backpressure
        - Cascade failures → Circuit breaker

        Args:
            event: The critical ImmuneEvent that triggered protection
        """
        logger.warning(
            f"[ImmuneService] Triggering self-protection for: {event.type.value}"
        )

        action = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_id": event.id,
            "event_type": event.type.value,
            "action": None,
            "success": False,
        }

        try:
            # Dispatch based on event type
            if event.type == ImmuneEventType.RESOURCE_EXHAUSTION:
                if "memory" in event.message.lower():
                    await self._trigger_garbage_collection()
                    action["action"] = "garbage_collection"
                else:
                    await self._enable_backpressure()
                    action["action"] = "backpressure"

            elif event.type == ImmuneEventType.AGENT_FAILURE:
                if "deadlock" in event.message.lower():
                    await self._restart_affected_agents(event)
                    action["action"] = "restart_agents"
                elif "cascade" in event.message.lower():
                    await self._enable_circuit_breaker()
                    action["action"] = "circuit_breaker"

            elif event.type == ImmuneEventType.PERFORMANCE_DEGRADATION:
                if "queue" in event.message.lower() or "overload" in event.message.lower():
                    await self._enable_backpressure()
                    action["action"] = "backpressure"

            else:
                logger.info(
                    f"[ImmuneService] No specific self-protection action for type: {event.type.value}"
                )
                action["action"] = "none"

            action["success"] = True

            # Emit self-protection event
            await self._emit_event_safe(
                event_type="immune.self_protection_triggered",
                immune_event=event,
            )

        except Exception as e:
            logger.error(
                f"[ImmuneService] Self-protection failed: {e}",
                exc_info=True,
            )
            action["error"] = str(e)

        finally:
            self.protection_actions_log.append(action)

    async def _trigger_garbage_collection(self):
        """
        Trigger Python garbage collection.

        Use case: Memory leak detected
        """
        logger.info("[ImmuneService] Triggering garbage collection...")

        # Run garbage collection
        collected = gc.collect()

        logger.info(f"[ImmuneService] Garbage collection completed: {collected} objects collected")

    async def _enable_backpressure(self):
        """
        Enable backpressure mechanisms.

        Use case: Queue saturation, overload
        Actions:
        - Set flag for mission system to rate-limit enqueues
        - Trigger queue depth limits
        """
        if self.backpressure_enabled:
            logger.debug("[ImmuneService] Backpressure already enabled")
            return

        logger.warning("[ImmuneService] Enabling backpressure...")

        self.backpressure_enabled = True

        # TODO: Integration with Mission Queue
        # await mission_queue.set_max_depth(500)
        # await mission_queue.enable_rate_limiting(10)  # 10 req/s

        logger.info("[ImmuneService] Backpressure enabled")

    async def _enable_circuit_breaker(self):
        """
        Open circuit breaker to prevent cascading failures.

        Use case: Cascade failure detected
        Actions:
        - Block new mission enqueues temporarily
        - Allow system to recover
        """
        if self.circuit_breaker_open:
            logger.debug("[ImmuneService] Circuit breaker already open")
            return

        logger.critical("[ImmuneService] Opening circuit breaker...")

        self.circuit_breaker_open = True

        # Auto-close after recovery period (30 seconds)
        asyncio.create_task(self._auto_close_circuit_breaker(delay=30.0))

        logger.info("[ImmuneService] Circuit breaker opened")

    async def _auto_close_circuit_breaker(self, delay: float):
        """
        Automatically close circuit breaker after delay.

        Args:
            delay: Seconds to wait before closing
        """
        await asyncio.sleep(delay)

        logger.info(f"[ImmuneService] Closing circuit breaker after {delay}s recovery period")
        self.circuit_breaker_open = False

    async def _restart_affected_agents(self, event: ImmuneEvent):
        """
        Restart affected agents.

        Use case: Deadlock detected
        Actions:
        - Identify affected agents from event metadata
        - Send restart signals

        Args:
            event: Event containing agent_id or meta information
        """
        logger.warning("[ImmuneService] Restarting affected agents...")

        agent_id = event.agent_id
        if not agent_id:
            # Try to extract from metadata
            if event.meta and "agent_id" in event.meta:
                agent_id = event.meta["agent_id"]

        if agent_id:
            logger.info(f"[ImmuneService] Sending restart signal to agent: {agent_id}")
            # TODO: Integration with Agent Manager
            # await agent_manager.restart_agent(agent_id)
        else:
            logger.warning("[ImmuneService] No agent_id found in event - cannot restart specific agent")

    # =========================================================================
    # SELF-PROTECTION STATE
    # =========================================================================

    def get_protection_status(self) -> Dict[str, Any]:
        """Get current self-protection status"""
        return {
            "backpressure_enabled": self.backpressure_enabled,
            "circuit_breaker_open": self.circuit_breaker_open,
            "protection_actions_count": len(self.protection_actions_log),
            "last_action": self.protection_actions_log[-1] if self.protection_actions_log else None,
        }

    def disable_backpressure(self):
        """Manually disable backpressure"""
        logger.info("[ImmuneService] Disabling backpressure (manual)")
        self.backpressure_enabled = False

    def close_circuit_breaker(self):
        """Manually close circuit breaker"""
        logger.info("[ImmuneService] Closing circuit breaker (manual)")
        self.circuit_breaker_open = False
