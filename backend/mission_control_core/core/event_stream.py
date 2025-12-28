"""
🎯 BRAIN Mission Control - Event Stream System
Redis Pub/Sub Event Bus for Agent Communication

Philosophy: Myzelkapitalismus  
- Transparent communication between all agents
- Event-driven coordination and collaboration
- Audit trail for ethical oversight
- Real-time mission progress tracking
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event types in the BRAIN ecosystem"""
    # Task Events
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned" 
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_RETRYING = "task.retrying"
    
    # Mission Events
    MISSION_CREATED = "mission.created"
    MISSION_STARTED = "mission.started"
    MISSION_COMPLETED = "mission.completed"
    MISSION_FAILED = "mission.failed"
    MISSION_CANCELLED = "mission.cancelled"
    
    # Agent Events
    AGENT_ONLINE = "agent.online"
    AGENT_OFFLINE = "agent.offline"
    AGENT_HEARTBEAT = "agent.heartbeat"
    AGENT_ERROR = "agent.error"
    AGENT_TASK_REQUEST = "agent.task_request"
    
    # System Events
    SYSTEM_HEALTH = "system.health"
    SYSTEM_ALERT = "system.alert"
    SYSTEM_MAINTENANCE = "system.maintenance"
    
    # Ethics Events (KARMA System)
    ETHICS_REVIEW = "ethics.review"
    ETHICS_VIOLATION = "ethics.violation"
    ETHICS_APPROVAL = "ethics.approval"
    
    # Communication Events
    AGENT_MESSAGE = "agent.message"
    BROADCAST = "broadcast"

    # Course Factory Events (Sprint 1)
    COURSE_GENERATION_REQUESTED = "course.generation.requested"
    COURSE_OUTLINE_CREATED = "course.outline.created"
    COURSE_LESSON_GENERATED = "course.lesson.generated"
    COURSE_QUIZ_CREATED = "course.quiz.created"
    COURSE_LANDING_PAGE_CREATED = "course.landing_page.created"
    COURSE_GENERATION_COMPLETED = "course.generation.completed"
    COURSE_GENERATION_FAILED = "course.generation.failed"
    COURSE_WORKFLOW_TRANSITIONED = "course.workflow.transitioned"
    COURSE_DEPLOYED_STAGING = "course.deployed.staging"

    # Course Distribution Events (Sprint 1)
    DISTRIBUTION_CREATED = "distribution.created"
    DISTRIBUTION_UPDATED = "distribution.updated"
    DISTRIBUTION_DELETED = "distribution.deleted"
    DISTRIBUTION_PUBLISHED = "distribution.published"
    DISTRIBUTION_UNPUBLISHED = "distribution.unpublished"
    DISTRIBUTION_VIEWED = "distribution.viewed"
    DISTRIBUTION_ENROLLMENT_CLICKED = "distribution.enrollment_clicked"
    DISTRIBUTION_MICRO_NICHE_CREATED = "distribution.micro_niche_created"
    DISTRIBUTION_VERSION_BUMPED = "distribution.version_bumped"


@dataclass
class Event:
    """
    Event data structure with multi-tenancy, audit support, and metadata (Charter v1.0)

    Charter Compliance (HARD GATE):
    - id: UUID v4 (secon dary dedup key)
    - type: EventType enum
    - timestamp: UTC ISO-8601
    - tenant_id: Tenant isolation
    - actor_id: User attribution
    - correlation_id: Request tracing
    - payload: Event-specific data
    - meta: Schema version, producer, source_module (NEW in v1.3)
    """
    id: str
    type: EventType
    source: str              # Agent ID or system component
    target: Optional[str]    # Target agent (None for broadcast)
    payload: Dict[str, Any]
    timestamp: datetime
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    correlation_id: Optional[str] = None

    # Multi-tenancy & Audit fields (added in consolidation v1.1)
    tenant_id: Optional[str] = None      # Tenant/organization ID for multi-tenancy
    actor_id: Optional[str] = None       # User/actor who triggered the event
    severity: Optional[str] = None       # Event severity: INFO, WARNING, ERROR, CRITICAL

    # Metadata fields (added in Charter v1.0 compliance - v1.3)
    meta: Dict[str, Any] = field(default_factory=lambda: {
        "schema_version": 1,
        "producer": "event_stream",
        "source_module": "core"
    })

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event for Redis"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['type'] = self.type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Deserialize event from Redis (backward compatible)"""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['type'] = EventType(data['type'])

        # Backward compatibility: add default meta if missing (pre-v1.3 events)
        if 'meta' not in data:
            data['meta'] = {
                "schema_version": 1,
                "producer": "legacy",
                "source_module": "unknown"
            }

        return cls(**data)


class EventStream:
    """
    Redis-based Event Stream for Agent Communication
    Implements Myzelkapitalismus principles of transparent cooperation
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self._initialized = False
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None
        
        # Event handlers: event_type -> list of callback functions
        self._event_handlers: Dict[EventType, List[Callable]] = {}
        
        # Subscriptions: agent_id -> set of event types
        self._subscriptions: Dict[str, Set[EventType]] = {}
        
        # Redis key patterns (unified naming: brain:events:{type})
        self.keys = {
            'event_stream': 'brain:events:stream',       # Main event stream (Redis Stream)
            'event_log': 'brain:events:log:{}',          # Event logs by date
            'agent_inbox': 'brain:agent:{}:inbox',       # Agent-specific message queues
            'broadcast': 'brain:events:broadcast',       # Broadcast channel
            'system': 'brain:events:system',             # System events channel
            'ethics': 'brain:events:ethics',             # Ethics events channel
            'missions': 'brain:events:missions',         # Mission events channel
            'tasks': 'brain:events:tasks',               # Task events channel
        }

    async def initialize(self) -> None:
        """Initialize Redis connection and event stream"""
        if self._initialized:
            return
            
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            
            # Initialize pubsub
            self.pubsub = self.redis.pubsub()

            # Subscribe to all topic channels
            await self.pubsub.subscribe(
                self.keys['broadcast'],
                self.keys['system'],
                self.keys['ethics'],
                self.keys['missions'],
                self.keys['tasks']
            )
            
            logger.info("Event Stream initialized successfully")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Event Stream: {e}")
            raise

    async def start(self) -> None:
        """Start event stream listener"""
        if not self._initialized:
            await self.initialize()
            
        if self._running:
            return
            
        self._running = True
        self._listener_task = asyncio.create_task(self._event_listener())
        logger.info("Event Stream started")

    async def stop(self) -> None:
        """Stop event stream listener"""
        self._running = False
        
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
                
        if self.pubsub:
            await self.pubsub.close()
            
        logger.info("Event Stream stopped")

    async def publish_event(self, event: Event) -> bool:
        """
        Publish event to the stream
        Routes to appropriate channels based on event type and target
        """
        try:
            # Add to main event stream (for audit trail)
            await self.redis.xadd(
                self.keys['event_stream'],
                event.to_dict(),
                maxlen=10000  # Keep last 10k events
            )
            
            # Route to specific channels
            await self._route_event(event)
            
            # Store in daily log for long-term audit
            log_key = self.keys['event_log'].format(event.timestamp.date().isoformat())
            await self.redis.lpush(log_key, json.dumps(event.to_dict()))
            await self.redis.expire(log_key, 86400 * 90)  # Keep for 90 days
            
            logger.debug(f"Published event {event.id} of type {event.type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.id}: {e}")
            return False

    async def subscribe_agent(self, agent_id: str, event_types: Set[EventType]) -> bool:
        """Subscribe agent to specific event types"""
        try:
            self._subscriptions[agent_id] = event_types
            
            # Subscribe to agent's inbox
            inbox_channel = self.keys['agent_inbox'].format(agent_id)
            await self.pubsub.subscribe(inbox_channel)
            
            logger.info(f"Agent {agent_id} subscribed to {len(event_types)} event types")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe agent {agent_id}: {e}")
            return False

    async def unsubscribe_agent(self, agent_id: str) -> bool:
        """Unsubscribe agent from all events"""
        try:
            if agent_id in self._subscriptions:
                del self._subscriptions[agent_id]
                
            # Unsubscribe from agent's inbox
            inbox_channel = self.keys['agent_inbox'].format(agent_id)
            await self.pubsub.unsubscribe(inbox_channel)
            
            logger.info(f"Agent {agent_id} unsubscribed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe agent {agent_id}: {e}")
            return False

    async def send_message(self, from_agent: str, to_agent: str, 
                          message: Dict[str, Any], 
                          correlation_id: Optional[str] = None) -> str:
        """Send direct message between agents"""
        try:
            import uuid
            event_id = str(uuid.uuid4())
            
            event = Event(
                id=event_id,
                type=EventType.AGENT_MESSAGE,
                source=from_agent,
                target=to_agent,
                payload={
                    'message': message,
                    'from': from_agent,
                    'to': to_agent
                },
                timestamp=datetime.utcnow(),
                correlation_id=correlation_id
            )
            
            await self.publish_event(event)
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to send message from {from_agent} to {to_agent}: {e}")
            return ""

    async def broadcast_message(self, source: str, message: Dict[str, Any]) -> str:
        """Broadcast message to all agents"""
        try:
            import uuid
            event_id = str(uuid.uuid4())
            
            event = Event(
                id=event_id,
                type=EventType.BROADCAST,
                source=source,
                target=None,
                payload={
                    'message': message,
                    'from': source
                },
                timestamp=datetime.utcnow()
            )
            
            await self.publish_event(event)
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to broadcast message from {source}: {e}")
            return ""

    async def register_handler(self, event_type: EventType, handler: Callable) -> None:
        """Register event handler function"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        logger.debug(f"Handler registered for event type {event_type.value}")

    async def get_event_history(self, agent_id: Optional[str] = None,
                               event_types: Optional[Set[EventType]] = None,
                               tenant_id: Optional[str] = None,
                               actor_id: Optional[str] = None,
                               limit: int = 100) -> List[Event]:
        """
        Get recent event history with optional filtering.

        Args:
            agent_id: Filter by source or target agent ID
            event_types: Filter by event types
            tenant_id: Filter by tenant ID (multi-tenancy support)
            actor_id: Filter by actor ID (user attribution)
            limit: Maximum number of events to return

        Returns:
            List of Event objects matching filters
        """
        try:
            # Get events from main stream
            events_data = await self.redis.xrevrange(
                self.keys['event_stream'],
                max='+',
                min='-',
                count=limit
            )

            events = []
            for event_id, fields in events_data:
                try:
                    event = Event.from_dict(fields)

                    # Apply filters
                    if agent_id and event.source != agent_id and event.target != agent_id:
                        continue

                    if event_types and event.type not in event_types:
                        continue

                    if tenant_id and event.tenant_id != tenant_id:
                        continue

                    if actor_id and event.actor_id != actor_id:
                        continue

                    events.append(event)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse event {event_id}: {e}")
                    continue
                    
            return events
            
        except Exception as e:
            logger.error(f"Failed to get event history: {e}")
            return []

    async def get_stream_stats(self) -> Dict[str, Any]:
        """Get event stream statistics"""
        try:
            # Get stream info
            stream_info = await self.redis.xinfo_stream(self.keys['event_stream'])
            
            # Count events by type in recent history
            recent_events = await self.get_event_history(limit=1000)
            event_type_counts = {}
            for event in recent_events:
                event_type_counts[event.type.value] = event_type_counts.get(event.type.value, 0) + 1
            
            return {
                'stream_length': stream_info.get('length', 0),
                'active_subscriptions': len(self._subscriptions),
                'event_handlers': len(self._event_handlers),
                'event_type_counts': event_type_counts,
                'stream_running': self._running,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get stream stats: {e}")
            return {}

    # Private methods

    async def _event_listener(self) -> None:
        """Main event listener loop"""
        logger.info("Event listener started")
        
        try:
            async for message in self.pubsub.listen():
                if not self._running:
                    break
                    
                if message['type'] != 'message':
                    continue
                    
                try:
                    # Parse event data
                    event_data = json.loads(message['data'])
                    event = Event.from_dict(event_data)
                    
                    # Handle event
                    await self._handle_event(event)
                    
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Event listener error: {e}")

    async def _route_event(self, event: Event) -> None:
        """Route event to appropriate channels based on event type"""
        try:
            event_json = json.dumps(event.to_dict())

            # Route to specific agent if targeted
            if event.target:
                inbox_channel = self.keys['agent_inbox'].format(event.target)
                await self.redis.publish(inbox_channel, event_json)
            else:
                # Route to appropriate topic channel based on event type
                if event.type in [EventType.BROADCAST]:
                    await self.redis.publish(self.keys['broadcast'], event_json)
                elif event.type.value.startswith('mission.'):
                    await self.redis.publish(self.keys['missions'], event_json)
                elif event.type.value.startswith('task.'):
                    await self.redis.publish(self.keys['tasks'], event_json)
                elif event.type.value.startswith('ethics.'):
                    await self.redis.publish(self.keys['ethics'], event_json)
                elif event.type.value.startswith('system.'):
                    await self.redis.publish(self.keys['system'], event_json)
                else:
                    # General broadcast for other events (agent.*, etc.)
                    await self.redis.publish(self.keys['broadcast'], event_json)

        except Exception as e:
            logger.error(f"Failed to route event {event.id}: {e}")

    async def _handle_event(self, event: Event) -> None:
        """Handle received event by calling registered handlers"""
        try:
            handlers = self._event_handlers.get(event.type, [])
            
            # Execute all handlers for this event type
            for handler in handlers:
                try:
                    # Check if handler is async
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                        
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to handle event {event.id}: {e}")


# Convenience functions for common events

async def emit_task_event(event_stream: EventStream, task_id: str, 
                         event_type: EventType, source: str, 
                         mission_id: Optional[str] = None,
                         extra_data: Optional[Dict[str, Any]] = None) -> str:
    """Emit a task-related event"""
    import uuid
    event_id = str(uuid.uuid4())
    
    payload = {'task_id': task_id}
    if extra_data:
        payload.update(extra_data)
    
    event = Event(
        id=event_id,
        type=event_type,
        source=source,
        target=None,
        payload=payload,
        timestamp=datetime.utcnow(),
        task_id=task_id,
        mission_id=mission_id
    )
    
    await event_stream.publish_event(event)
    return event_id


async def emit_agent_event(event_stream: EventStream, agent_id: str,
                          event_type: EventType,
                          extra_data: Optional[Dict[str, Any]] = None) -> str:
    """Emit an agent-related event"""
    import uuid
    event_id = str(uuid.uuid4())
    
    payload = {'agent_id': agent_id}
    if extra_data:
        payload.update(extra_data)
    
    event = Event(
        id=event_id,
        type=event_type,
        source=agent_id,
        target=None,
        payload=payload,
        timestamp=datetime.utcnow()
    )
    
    await event_stream.publish_event(event)
    return event_id


# Charter v1.0: Idempotent Event Consumer Infrastructure
# ========================================================

class EventConsumer:
    """
    Charter-compliant event consumer with idempotent processing.

    Primary dedup key: (subscriber_name, stream_message_id)
    event.id is SECONDARY (audit/trace only)

    Usage:
        consumer = EventConsumer(
            subscriber_name="course_access_handler",
            event_stream=event_stream,
            db_session_factory=get_db_session
        )
        await consumer.start()
    """

    def __init__(
        self,
        subscriber_name: str,
        event_stream: EventStream,
        db_session_factory: Callable,
        stream_name: str = "brain:events:stream",
        consumer_group: Optional[str] = None,
        batch_size: int = 10,
        block_ms: int = 5000
    ):
        self.subscriber_name = subscriber_name
        self.event_stream = event_stream
        self.db_session_factory = db_session_factory
        self.stream_name = stream_name
        self.consumer_group = consumer_group or f"group_{subscriber_name}"
        self.batch_size = batch_size
        self.block_ms = block_ms

        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None
        self._handlers: Dict[EventType, Callable] = {}

        logger.info(
            f"EventConsumer '{subscriber_name}' initialized "
            f"(group={self.consumer_group}, stream={stream_name})"
        )

    def register_handler(self, event_type: EventType, handler: Callable) -> None:
        """Register handler for specific event type"""
        self._handlers[event_type] = handler
        logger.debug(f"Handler registered: {event_type.value} → {handler.__name__}")

    async def start(self) -> None:
        """Start consumer loop"""
        if self._running:
            logger.warning(f"Consumer '{self.subscriber_name}' already running")
            return

        # Ensure consumer group exists
        try:
            await self.event_stream.redis.xgroup_create(
                self.stream_name,
                self.consumer_group,
                id='0',
                mkstream=True
            )
            logger.info(f"Created consumer group '{self.consumer_group}'")
        except Exception as e:
            # Group might already exist
            logger.debug(f"Consumer group exists or creation failed: {e}")

        self._running = True
        self._consumer_task = asyncio.create_task(self._consume_loop())
        logger.info(f"EventConsumer '{self.subscriber_name}' started")

    async def stop(self) -> None:
        """Stop consumer loop gracefully"""
        self._running = False
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        logger.info(f"EventConsumer '{self.subscriber_name}' stopped")

    async def _consume_loop(self) -> None:
        """Main consumer loop (Charter-compliant)"""
        logger.info(f"Consumer loop started: {self.subscriber_name}")

        try:
            while self._running:
                try:
                    # Read from stream (consumer group pattern)
                    messages = await self.event_stream.redis.xreadgroup(
                        groupname=self.consumer_group,
                        consumername=self.subscriber_name,
                        streams={self.stream_name: '>'},
                        count=self.batch_size,
                        block=self.block_ms
                    )

                    if not messages:
                        continue  # Timeout, retry

                    # Process each message
                    for stream_name, message_list in messages:
                        for stream_message_id, fields in message_list:
                            await self._process_message(
                                stream_message_id=stream_message_id,
                                fields=fields
                            )

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Consumer loop error: {e}", exc_info=True)
                    await asyncio.sleep(5)  # Backoff on error

        except Exception as e:
            logger.error(f"Fatal consumer error: {e}", exc_info=True)
        finally:
            logger.info(f"Consumer loop exited: {self.subscriber_name}")

    async def _process_message(
        self,
        stream_message_id: str,
        fields: Dict[str, Any]
    ) -> None:
        """
        Process single message with idempotent dedup (Charter v1.0)

        Args:
            stream_message_id: Redis Stream Message ID (PRIMARY dedup key)
            fields: Event data fields
        """
        try:
            # Parse event
            event = Event.from_dict(fields)

            # CHARTER COMPLIANCE: Check dedup (stream_message_id PRIMARY)
            db_session = self.db_session_factory()
            try:
                is_duplicate = await self._check_duplicate(
                    db_session,
                    stream_message_id,
                    event.id  # SECONDARY, audit only
                )

                if is_duplicate:
                    logger.debug(
                        f"Skipping duplicate message: {stream_message_id} "
                        f"(event_id={event.id})"
                    )
                    # ACK duplicate (idempotent: no effect)
                    await self._ack_message(stream_message_id)
                    return

                # Find handler for this event type
                handler = self._handlers.get(event.type)
                if not handler:
                    logger.warning(
                        f"No handler for {event.type.value}, skipping "
                        f"(stream_msg={stream_message_id})"
                    )
                    await self._ack_message(stream_message_id)
                    return

                # Execute handler
                logger.debug(
                    f"Processing {event.type.value}: {stream_message_id} "
                    f"(event_id={event.id})"
                )

                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)

                # Mark as processed (DEDUP)
                await self._mark_processed(
                    db_session,
                    stream_message_id,
                    event
                )

                # ACK message
                await self._ack_message(stream_message_id)

                logger.debug(f"Successfully processed: {stream_message_id}")

            finally:
                await db_session.close()

        except Exception as e:
            # ERROR HANDLING (Charter compliance)
            if self._is_permanent_error(e):
                # Permanent error: ACK + Log (avoid infinite retry)
                logger.error(
                    f"PERMANENT ERROR processing {stream_message_id}: {e}",
                    exc_info=True
                )
                await self._ack_message(stream_message_id)
                # Optional: Send to DLQ (not implemented yet)
            else:
                # Transient error: NO ACK (will retry)
                logger.warning(
                    f"TRANSIENT ERROR processing {stream_message_id}: {e}. "
                    f"Will retry."
                )
                # Do NOT ack, let retry happen

    async def _check_duplicate(
        self,
        db_session,
        stream_message_id: str,
        event_id: str
    ) -> bool:
        """
        Check if message already processed (Charter PRIMARY key)

        Returns:
            True if duplicate (already processed)
        """
        from sqlalchemy import text

        query = text("""
            SELECT 1 FROM processed_events
            WHERE subscriber_name = :subscriber
            AND stream_message_id = :stream_msg_id
            LIMIT 1
        """)

        result = await db_session.execute(
            query,
            {
                "subscriber": self.subscriber_name,
                "stream_msg_id": stream_message_id
            }
        )

        return result.scalar() is not None

    async def _mark_processed(
        self,
        db_session,
        stream_message_id: str,
        event: Event
    ) -> None:
        """Mark message as processed (idempotency tracking)"""
        from sqlalchemy import text

        query = text("""
            INSERT INTO processed_events (
                subscriber_name,
                stream_name,
                stream_message_id,
                event_id,
                event_type,
                tenant_id,
                metadata
            ) VALUES (
                :subscriber,
                :stream,
                :stream_msg_id,
                :event_id,
                :event_type,
                :tenant_id,
                :metadata
            )
            ON CONFLICT (subscriber_name, stream_message_id) DO NOTHING
        """)

        await db_session.execute(
            query,
            {
                "subscriber": self.subscriber_name,
                "stream": self.stream_name,
                "stream_msg_id": stream_message_id,
                "event_id": event.id,
                "event_type": event.type.value,
                "tenant_id": event.tenant_id,
                "metadata": json.dumps(event.meta)
            }
        )
        await db_session.commit()

    async def _ack_message(self, stream_message_id: str) -> None:
        """Acknowledge message (remove from pending)"""
        try:
            await self.event_stream.redis.xack(
                self.stream_name,
                self.consumer_group,
                stream_message_id
            )
        except Exception as e:
            logger.warning(f"Failed to ACK {stream_message_id}: {e}")

    def _is_permanent_error(self, error: Exception) -> bool:
        """
        Determine if error is permanent (ACK) or transient (retry)

        Permanent: ValidationError, KeyError, TypeError, etc.
        Transient: ConnectionError, TimeoutError, etc.
        """
        permanent_types = (
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
            # Add more as needed
        )

        transient_types = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            # Add more as needed
        )

        if isinstance(error, permanent_types):
            return True
        if isinstance(error, transient_types):
            return False

        # Default: transient (safer, will retry)
        return False


# Export public interface
__all__ = [
    'EventStream', 'Event', 'EventType',
    'EventConsumer',  # NEW
    'emit_task_event', 'emit_agent_event'
]
