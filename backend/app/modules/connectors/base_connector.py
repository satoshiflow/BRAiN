"""
BaseConnector - Abstract Base Class for all BRAIN Connectors

All connectors are "dumb clients" that route through AXE Core.
They handle platform-specific I/O but delegate intelligence to BRAIN.

Flow:
    User -> Connector.receive -> BaseConnector.send_to_brain() -> AXE Core
    AXE Core -> Response -> Connector.send_to_user() -> User
"""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.modules.connectors.schemas import (
    Attachment,
    BrainResponse,
    ConnectorCapability,
    ConnectorHealth,
    ConnectorInfo,
    ConnectorStats,
    ConnectorStatus,
    ConnectorType,
    IncomingMessage,
    OutgoingMessage,
)


class BaseConnector(ABC):
    """
    Abstract base class for all BRAIN connectors.

    Subclasses implement platform-specific I/O (CLI, Telegram, etc.).
    Message routing to BRAIN is handled by send_to_brain() via AXE Core.
    """

    def __init__(
        self,
        connector_id: str,
        connector_type: ConnectorType,
        display_name: str,
        description: str = "",
        capabilities: Optional[List[ConnectorCapability]] = None,
        axe_base_url: str = "http://localhost:8000",
        dmz_gateway_id: Optional[str] = None,
        dmz_shared_secret: Optional[str] = None,
    ):
        self.connector_id = connector_id
        self.connector_type = connector_type
        self.display_name = display_name
        self.description = description
        self.capabilities = capabilities or [ConnectorCapability.TEXT]
        self.axe_base_url = axe_base_url
        self.dmz_gateway_id = dmz_gateway_id or f"{connector_id}_gateway"
        self.dmz_shared_secret = dmz_shared_secret or ""

        self._status = ConnectorStatus.STOPPED
        self._stats = ConnectorStats()
        self._started_at: Optional[float] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    # ========================================================================
    # Properties
    # ========================================================================

    @property
    def status(self) -> ConnectorStatus:
        return self._status

    @property
    def stats(self) -> ConnectorStats:
        if self._started_at:
            self._stats.uptime_seconds = time.time() - self._started_at
        return self._stats

    @property
    def info(self) -> ConnectorInfo:
        return ConnectorInfo(
            connector_id=self.connector_id,
            connector_type=self.connector_type,
            display_name=self.display_name,
            description=self.description,
            status=self._status,
            capabilities=self.capabilities,
            stats=self.stats,
        )

    # ========================================================================
    # Lifecycle (must implement)
    # ========================================================================

    @abstractmethod
    async def start(self) -> None:
        """Start the connector. Set status to CONNECTED when ready."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the connector gracefully. Set status to STOPPED."""
        ...

    @abstractmethod
    async def send_to_user(self, user_id: str, message: OutgoingMessage) -> bool:
        """
        Send a message to a user on this platform.
        Returns True if delivery succeeded.
        """
        ...

    @abstractmethod
    async def health_check(self) -> ConnectorHealth:
        """Check connector health and return status."""
        ...

    # ========================================================================
    # Lifecycle Helpers
    # ========================================================================

    async def _init_http_client(self) -> None:
        """Initialize the shared HTTP client for AXE Core communication."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=self.axe_base_url,
                timeout=30.0,
            )

    async def _close_http_client(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    def _set_status(self, status: ConnectorStatus) -> None:
        """Update connector status with logging."""
        old = self._status
        self._status = status
        if old != status:
            logger.info(
                f"Connector {self.connector_id}: {old.value} -> {status.value}"
            )

    async def _on_start(self) -> None:
        """Common start logic. Call at beginning of start()."""
        self._set_status(ConnectorStatus.INITIALIZING)
        self._started_at = time.time()
        self._stats = ConnectorStats()
        await self._init_http_client()

    async def _on_stop(self) -> None:
        """Common stop logic. Call at end of stop()."""
        await self._close_http_client()
        self._set_status(ConnectorStatus.STOPPED)
        self._started_at = None

    # ========================================================================
    # AXE Core Communication
    # ========================================================================

    def _build_dmz_headers(self) -> Dict[str, str]:
        """Build DMZ gateway authentication headers for AXE Core."""
        if not self.dmz_shared_secret:
            return {}
        token_input = f"{self.dmz_gateway_id}:{self.dmz_shared_secret}"
        token = hashlib.sha256(token_input.encode()).hexdigest()
        return {
            "X-DMZ-Gateway-ID": self.dmz_gateway_id,
            "X-DMZ-Gateway-Token": token,
        }

    async def send_to_brain(self, message: IncomingMessage) -> BrainResponse:
        """
        Send a message to BRAIN via AXE Core POST /api/axe/message.

        This is the central routing point - all connectors use this method.
        """
        await self._init_http_client()
        assert self._http_client is not None

        self._stats.record_incoming()
        start_time = time.time()

        try:
            headers = self._build_dmz_headers()
            payload = {
                "message": message.content,
                "metadata": {
                    "connector_id": self.connector_id,
                    "connector_type": self.connector_type.value,
                    "user_id": message.user.user_id,
                    "username": message.user.username,
                    "message_id": message.message_id,
                    "content_type": message.content_type.value,
                    "session_id": message.session_id,
                    **message.metadata,
                },
            }

            response = await self._http_client.post(
                "/api/axe/message",
                json=payload,
                headers=headers,
            )

            duration_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                reply = (
                    data.get("reply")
                    or data.get("message")
                    or data.get("text")
                    or ""
                )
                brain_response = BrainResponse(
                    success=True,
                    reply=reply,
                    mode=data.get("mode", "unknown"),
                    model=data.get("result", {}).get("model"),
                    duration_ms=duration_ms,
                    metadata=data.get("governance", {}),
                )
                self._stats.record_outgoing(duration_ms)
                return brain_response

            error_msg = f"AXE Core returned {response.status_code}: {response.text}"
            logger.error(f"Connector {self.connector_id}: {error_msg}")
            self._stats.record_error()
            return BrainResponse(
                success=False,
                error=error_msg,
                duration_ms=duration_ms,
            )

        except httpx.ConnectError as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Cannot connect to AXE Core at {self.axe_base_url}: {e}"
            logger.error(f"Connector {self.connector_id}: {error_msg}")
            self._stats.record_error()
            return BrainResponse(
                success=False,
                error=error_msg,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Unexpected error: {e}"
            logger.error(f"Connector {self.connector_id}: {error_msg}")
            self._stats.record_error()
            return BrainResponse(
                success=False,
                error=error_msg,
                duration_ms=duration_ms,
            )

    # ========================================================================
    # Message Processing Helper
    # ========================================================================

    async def process_message(self, message: IncomingMessage) -> OutgoingMessage:
        """
        Full message round-trip: receive -> send to BRAIN -> format response.
        Subclasses can override for custom pre/post processing.
        """
        brain_response = await self.send_to_brain(message)

        if brain_response.success:
            return OutgoingMessage(
                content=brain_response.reply,
                reply_to=message.message_id,
                metadata={
                    "mode": brain_response.mode,
                    "model": brain_response.model,
                    "duration_ms": brain_response.duration_ms,
                },
            )
        else:
            return OutgoingMessage(
                content=f"Fehler: {brain_response.error or 'Unbekannter Fehler'}",
                reply_to=message.message_id,
                metadata={"error": True},
            )
