"""
Message Bus - Agent-to-agent async message passing.

Features:
    - Point-to-point messaging (sender → target)
    - Broadcast messaging (sender → all subscribers)
    - Request/reply pattern with correlation IDs
    - Message handlers per agent per message type
    - TTL-based message expiry
    - Priority-based ordering
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List, Optional

from loguru import logger

from .schemas import (
    AgentMessage,
    MessagePriority,
    MessageType,
)

# Handler type: async function(message) → optional response payload
MessageHandler = Callable[[AgentMessage], Coroutine[Any, Any, Optional[Dict[str, Any]]]]

# Priority weights for ordering
PRIORITY_WEIGHTS = {
    MessagePriority.URGENT: 40,
    MessagePriority.HIGH: 30,
    MessagePriority.NORMAL: 20,
    MessagePriority.LOW: 10,
}


class MessageBus:
    """
    Async message bus for inter-agent communication.

    Agents register handlers for message types. Messages are
    delivered asynchronously with priority ordering.
    """

    def __init__(self) -> None:
        # Handler registry: agent_id → {message_type → handler}
        self._handlers: Dict[str, Dict[MessageType, MessageHandler]] = {}

        # Inbox per agent (for polling pattern)
        self._inboxes: Dict[str, List[AgentMessage]] = defaultdict(list)

        # Pending request/reply futures
        self._pending_replies: Dict[str, asyncio.Future] = {}

        # Message log (circular buffer)
        self._message_log: List[AgentMessage] = []
        self._max_log = 1000

        # Metrics
        self._total_sent = 0
        self._total_delivered = 0
        self._total_expired = 0

        logger.info("📬 MessageBus initialized")

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str) -> None:
        """Register an agent on the bus."""
        if agent_id not in self._handlers:
            self._handlers[agent_id] = {}
            logger.debug("Agent registered on MessageBus: %s", agent_id)

    def register_handler(
        self,
        agent_id: str,
        message_type: MessageType,
        handler: MessageHandler,
    ) -> None:
        """Register a message handler for an agent."""
        self.register_agent(agent_id)
        self._handlers[agent_id][message_type] = handler

    def unregister_agent(self, agent_id: str) -> None:
        self._handlers.pop(agent_id, None)
        self._inboxes.pop(agent_id, None)

    def get_registered_agents(self) -> List[str]:
        return list(self._handlers.keys())

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------

    async def send(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        """
        Send a message to a specific agent or broadcast.

        For REQUEST messages, waits for a RESPONSE (up to TTL).
        For other types, delivers and returns immediately.

        Returns response payload for REQUEST, None otherwise.
        """
        if message.is_expired():
            self._total_expired += 1
            return None

        self._log_message(message)
        self._total_sent += 1

        if message.target_id is None:
            # Broadcast to all registered agents
            await self._broadcast(message)
            return None

        # Deliver to target
        delivered = await self._deliver(message)
        if not delivered:
            logger.warning(
                "Message %s undelivered: target %s not registered",
                message.message_id, message.target_id,
            )
            return None

        # For REQUEST, wait for reply
        if message.message_type == MessageType.REQUEST:
            return await self._wait_for_reply(message)

        return None

    async def reply(self, original: AgentMessage, payload: Dict[str, Any], sender_id: str) -> None:
        """Send a reply to a request message."""
        response = AgentMessage(
            message_type=MessageType.RESPONSE,
            sender_id=sender_id,
            target_id=original.sender_id,
            reply_to=original.message_id,
            subject=f"Re: {original.subject}",
            payload=payload,
        )

        self._log_message(response)
        self._total_sent += 1

        # Resolve pending future if exists
        future = self._pending_replies.pop(original.message_id, None)
        if future and not future.done():
            future.set_result(payload)
        else:
            # Deliver as regular message
            await self._deliver(response)

    # ------------------------------------------------------------------
    # Inbox (polling pattern)
    # ------------------------------------------------------------------

    async def get_inbox(
        self,
        agent_id: str,
        limit: int = 50,
        message_type: Optional[MessageType] = None,
    ) -> List[AgentMessage]:
        """Get messages from an agent's inbox (polling pattern)."""
        inbox = self._inboxes.get(agent_id, [])

        # Filter expired
        now = time.time()
        inbox = [m for m in inbox if not m.is_expired()]

        if message_type:
            inbox = [m for m in inbox if m.message_type == message_type]

        # Sort by priority then timestamp
        inbox.sort(
            key=lambda m: (PRIORITY_WEIGHTS.get(m.priority, 20), m.timestamp),
            reverse=True,
        )

        return inbox[:limit]

    async def clear_inbox(self, agent_id: str) -> int:
        count = len(self._inboxes.get(agent_id, []))
        self._inboxes[agent_id] = []
        return count

    # ------------------------------------------------------------------
    # Internal delivery
    # ------------------------------------------------------------------

    async def _deliver(self, message: AgentMessage) -> bool:
        """Deliver a message to its target agent."""
        target_id = message.target_id
        if not target_id:
            return False

        # Try handler first
        handlers = self._handlers.get(target_id, {})
        handler = handlers.get(message.message_type)

        if handler:
            try:
                response = await handler(message)
                self._total_delivered += 1

                # If handler returned a dict and this is a request, auto-reply
                if response and message.message_type == MessageType.REQUEST:
                    await self.reply(message, response, target_id)

                return True
            except Exception as e:
                logger.error("Handler error for agent %s: %s", target_id, e)
                # Still put in inbox as fallback
                self._inboxes[target_id].append(message)
                self._total_delivered += 1
                return True

        # No handler → put in inbox
        self._inboxes[target_id].append(message)
        self._total_delivered += 1

        # Cap inbox size
        if len(self._inboxes[target_id]) > 200:
            self._inboxes[target_id] = self._inboxes[target_id][-200:]

        return True

    async def _broadcast(self, message: AgentMessage) -> int:
        """Broadcast a message to all registered agents except sender."""
        delivered = 0
        for agent_id in list(self._handlers.keys()):
            if agent_id == message.sender_id:
                continue
            msg_copy = message.model_copy(update={"target_id": agent_id})
            if await self._deliver(msg_copy):
                delivered += 1
        return delivered

    async def _wait_for_reply(
        self,
        message: AgentMessage,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Wait for a reply to a request message."""
        timeout = timeout or (message.ttl_seconds or 30.0)
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_replies[message.message_id] = future

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_replies.pop(message.message_id, None)
            logger.warning("Reply timeout for message %s", message.message_id)
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log_message(self, message: AgentMessage) -> None:
        self._message_log.append(message)
        if len(self._message_log) > self._max_log:
            self._message_log = self._message_log[-self._max_log:]

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "total_sent": self._total_sent,
            "total_delivered": self._total_delivered,
            "total_expired": self._total_expired,
            "registered_agents": len(self._handlers),
            "pending_replies": len(self._pending_replies),
        }
