"""
WhatsApp Connector - BaseConnector Implementation

Integrates with Twilio WhatsApp Business API for message
sending. Uses WhatsAppMessageHandler for incoming webhook processing.

Supports:
- Incoming: Twilio webhook -> handler -> AXE Core -> TwiML response
- Outgoing: send_to_user() -> Twilio REST API -> WhatsApp delivery
- Media messages, location sharing
- Delivery status tracking
- Request signature validation
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from loguru import logger

from app.modules.connectors.base_connector import BaseConnector
from app.modules.connectors.schemas import (
    ConnectorCapability,
    ConnectorHealth,
    ConnectorStatus,
    ConnectorType,
    OutgoingMessage,
)
from app.modules.connectors.whatsapp.handlers import WhatsAppMessageHandler
from app.modules.connectors.whatsapp.schemas import WhatsAppConfig


class WhatsAppConnector(BaseConnector):
    """
    WhatsApp connector via Twilio API.

    Incoming messages arrive via Twilio webhook (FastAPI route).
    Outgoing messages are sent via Twilio REST API.
    All message intelligence routes through AXE Core.
    """

    def __init__(
        self,
        config: Optional[WhatsAppConfig] = None,
        axe_base_url: str = "http://localhost:8000",
        dmz_shared_secret: str = "",
    ):
        super().__init__(
            connector_id="whatsapp_connector",
            connector_type=ConnectorType.WHATSAPP,
            display_name="BRAIN WhatsApp",
            description="WhatsApp Business connector via Twilio API",
            capabilities=[
                ConnectorCapability.TEXT,
                ConnectorCapability.IMAGE,
                ConnectorCapability.FILE,
                ConnectorCapability.VOICE,
                ConnectorCapability.VIDEO,
                ConnectorCapability.LOCATION,
            ],
            axe_base_url=axe_base_url,
            dmz_gateway_id="whatsapp_gateway",
            dmz_shared_secret=dmz_shared_secret,
        )

        self.config = config or WhatsAppConfig(
            account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            whatsapp_number=os.getenv("TWILIO_WHATSAPP_NUMBER", ""),
        )
        self.handler = WhatsAppMessageHandler(
            config=self.config,
            send_to_brain_fn=self.send_to_brain,
            connector_id=self.connector_id,
        )
        self._twilio_client = None

    # ========================================================================
    # Lifecycle
    # ========================================================================

    async def start(self) -> None:
        await self._on_start()

        if not self.config.account_sid or not self.config.auth_token:
            logger.warning(
                "Twilio credentials not set. Running in handler-only mode."
            )
            self._set_status(ConnectorStatus.CONNECTED)
            return

        try:
            self._init_twilio_client()
            self._set_status(ConnectorStatus.CONNECTED)
        except ImportError:
            logger.warning(
                "twilio package not installed. Running in handler-only mode."
            )
            self._set_status(ConnectorStatus.CONNECTED)
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            self._set_status(ConnectorStatus.ERROR)
            raise

    def _init_twilio_client(self) -> None:
        """Initialize the Twilio REST client."""
        try:
            from twilio.rest import Client
            self._twilio_client = Client(
                self.config.account_sid,
                self.config.auth_token,
            )
            logger.info(
                f"Twilio client initialized for {self.config.whatsapp_number}"
            )
        except ImportError:
            raise ImportError("twilio package is not installed")

    async def stop(self) -> None:
        self._twilio_client = None
        await self._on_stop()

    async def send_to_user(self, user_id: str, message: OutgoingMessage) -> bool:
        """Send WhatsApp message via Twilio API."""
        if not self._twilio_client:
            logger.debug(
                f"Handler-only mode: would send to {user_id}: {message.content[:50]}"
            )
            return True

        try:
            # Ensure whatsapp: prefix
            to_number = user_id if user_id.startswith("whatsapp:") else f"whatsapp:{user_id}"

            twilio_msg = self._twilio_client.messages.create(
                body=message.content,
                from_=self.config.whatsapp_number,
                to=to_number,
            )

            logger.debug(f"WhatsApp message sent: SID={twilio_msg.sid}")
            self._stats.record_outgoing()
            return True

        except Exception as e:
            logger.error(f"Failed to send WhatsApp message to {user_id}: {e}")
            self._stats.record_error()
            return False

    async def health_check(self) -> ConnectorHealth:
        details: Dict[str, Any] = {
            "account_sid_set": bool(self.config.account_sid),
            "auth_token_set": bool(self.config.auth_token),
            "whatsapp_number": self.config.whatsapp_number or "not set",
            "twilio_client": self._twilio_client is not None,
            "active_sessions": self.handler.sessions.active_count,
            "total_sessions": len(self.handler.sessions.list_sessions()),
            "delivery_stats": self.handler.delivery.get_stats(),
        }

        return ConnectorHealth(
            connector_id=self.connector_id,
            status=self._status,
            last_message_at=self._stats.last_activity,
            details=details,
        )
