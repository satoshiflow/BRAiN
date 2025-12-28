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
from dataclasses import dataclass, asdict
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


@dataclass
class Event:
    """Event data structure"""
    id: str
    type: EventType
    source: str              # Agent ID or system component
    target: Optional[str]    # Target agent (None for broadcast)
    payload: Dict[str, Any]
    timestamp: datetime
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize event for Redis"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['type'] = self.type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Deserialize event from Redis"""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['type'] = EventType(data['type'])
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
                               limit: int = 100) -> List[Event]:
        """Get recent event history with optional filtering"""
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


# Export public interface
__all__ = [
    'EventStream', 'Event', 'EventType', 
    'emit_task_event', 'emit_agent_event'
]
