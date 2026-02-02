"""
WhatsApp Connector - Message & Webhook Handlers

Processes incoming Twilio webhook payloads, manages sessions,
routes messages through AXE Core, and formats responses.

Handles:
- Text messages -> AXE Core -> Reply
- Media messages (images, audio, documents, video)
- Location sharing
- Delivery status callbacks
- Rate limiting per phone number
- Twilio request signature validation
"""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from base64 import b64encode
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode

from loguru import logger

from app.modules.connectors.schemas import (
    BrainResponse,
    IncomingMessage,
    MessageContentType,
    UserInfo,
)
from app.modules.connectors.whatsapp.schemas import (
    MediaMessage,
    MediaType,
    MessageStatus,
    TwilioStatusPayload,
    TwilioWebhookPayload,
    WhatsAppConfig,
    WhatsAppSession,
)


class WhatsAppSessionManager:
    """Manages WhatsApp user sessions by phone number."""

    def __init__(self) -> None:
        self._sessions: Dict[str, WhatsAppSession] = {}

    def get_or_create(
        self,
        phone_number: str,
        profile_name: Optional[str] = None,
    ) -> WhatsAppSession:
        if phone_number not in self._sessions:
            self._sessions[phone_number] = WhatsAppSession(
                phone_number=phone_number,
                profile_name=profile_name,
                session_id=f"wa_{phone_number.replace('+', '')}_{uuid.uuid4().hex[:6]}",
            )
        session = self._sessions[phone_number]
        session.message_count += 1
        session.last_message_at = time.time()
        if profile_name and not session.profile_name:
            session.profile_name = profile_name
        return session

    def get(self, phone_number: str) -> Optional[WhatsAppSession]:
        return self._sessions.get(phone_number)

    def clear(self, phone_number: str) -> bool:
        if phone_number in self._sessions:
            del self._sessions[phone_number]
            return True
        return False

    def list_sessions(self) -> List[WhatsAppSession]:
        return list(self._sessions.values())

    @property
    def active_count(self) -> int:
        cutoff = time.time() - 3600
        return sum(1 for s in self._sessions.values() if s.last_message_at > cutoff)


class SignatureValidator:
    """Validates Twilio request signatures (HMAC-SHA1)."""

    def __init__(self, auth_token: str) -> None:
        self.auth_token = auth_token

    def validate(self, url: str, params: Dict[str, str], signature: str) -> bool:
        """
        Validate Twilio X-Twilio-Signature header.

        Twilio computes HMAC-SHA1 of: URL + sorted POST params concatenated.
        """
        if not self.auth_token or not signature:
            return False

        # Build data string: URL + sorted key-value pairs
        data = url
        for key in sorted(params.keys()):
            data += key + params[key]

        # Compute HMAC-SHA1
        expected = b64encode(
            hmac.new(
                self.auth_token.encode("utf-8"),
                data.encode("utf-8"),
                hashlib.sha1,
            ).digest()
        ).decode("utf-8")

        return hmac.compare_digest(expected, signature)


class DeliveryTracker:
    """Tracks message delivery status."""

    def __init__(self) -> None:
        self._statuses: Dict[str, MessageStatus] = {}

    def update(self, message_sid: str, status: str) -> None:
        try:
            self._statuses[message_sid] = MessageStatus(status)
        except ValueError:
            logger.warning(f"Unknown message status: {status}")

    def get(self, message_sid: str) -> Optional[MessageStatus]:
        return self._statuses.get(message_sid)

    def get_stats(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for status in self._statuses.values():
            counts[status.value] = counts.get(status.value, 0) + 1
        return counts


class WhatsAppMessageHandler:
    """
    Core message processing for the WhatsApp connector.

    Separated from Twilio HTTP integration to enable testing
    without actual API calls.
    """

    def __init__(
        self,
        config: WhatsAppConfig,
        send_to_brain_fn: Callable,
        connector_id: str = "whatsapp_connector",
    ) -> None:
        self.config = config
        self.send_to_brain = send_to_brain_fn
        self.connector_id = connector_id
        self.sessions = WhatsAppSessionManager()
        self.delivery = DeliveryTracker()
        self.signature_validator = SignatureValidator(config.auth_token)
        self._history: Dict[str, List[Dict[str, str]]] = {}

    # ========================================================================
    # Access Control
    # ========================================================================

    def is_number_allowed(self, phone_number: str) -> bool:
        if not self.config.allowed_numbers:
            return True
        return phone_number in self.config.allowed_numbers

    def is_admin(self, phone_number: str) -> bool:
        return phone_number in self.config.admin_numbers

    # ========================================================================
    # Webhook Processing
    # ========================================================================

    async def handle_webhook(self, payload: TwilioWebhookPayload) -> str:
        """
        Process incoming Twilio webhook and return TwiML response body text.
        """
        phone = payload.get_phone_number()

        # Access control
        if not self.is_number_allowed(phone):
            return "This number is not authorized to use BRAIN."

        # Session
        session = self.sessions.get_or_create(phone, payload.ProfileName)

        # Rate limiting
        if session.is_rate_limited(
            self.config.rate_limit_messages, self.config.rate_limit_window
        ):
            return "Rate limit exceeded. Please wait before sending more messages."

        # Route by content type
        media_urls = payload.get_media_urls()

        if payload.Latitude and payload.Longitude:
            return await self._handle_location(payload, session)

        if media_urls:
            return await self._handle_media(payload, media_urls, session)

        if payload.Body.strip():
            return await self._handle_text(payload, session)

        return "Message received but could not be processed."

    async def handle_status_callback(self, payload: TwilioStatusPayload) -> None:
        """Process delivery status callback from Twilio."""
        self.delivery.update(payload.MessageSid, payload.MessageStatus)

        if payload.ErrorCode:
            logger.warning(
                f"WhatsApp delivery error: SID={payload.MessageSid} "
                f"code={payload.ErrorCode} msg={payload.ErrorMessage}"
            )

    # ========================================================================
    # Message Type Handlers
    # ========================================================================

    async def _handle_text(
        self, payload: TwilioWebhookPayload, session: WhatsAppSession
    ) -> str:
        """Process text message through AXE Core."""
        phone = payload.get_phone_number()
        text = payload.Body.strip()

        # Save history
        if phone not in self._history:
            self._history[phone] = []
        self._history[phone].append({"role": "user", "content": text})

        # Build IncomingMessage
        message = IncomingMessage(
            connector_id=self.connector_id,
            connector_type="whatsapp",
            user=UserInfo(
                user_id=phone,
                username=payload.ProfileName,
                display_name=payload.ProfileName,
                platform="whatsapp",
            ),
            content=text,
            content_type=MessageContentType.TEXT,
            session_id=session.session_id,
            metadata={
                "message_sid": payload.MessageSid,
                "whatsapp_from": payload.From,
                "whatsapp_to": payload.To,
            },
        )

        brain_response: BrainResponse = await self.send_to_brain(message)

        if brain_response.success:
            reply = brain_response.reply
        else:
            reply = f"Error processing your message. Please try again."
            logger.error(f"WhatsApp AXE error for {phone}: {brain_response.error}")

        self._history[phone].append({"role": "brain", "content": reply})

        # Truncate
        if len(reply) > self.config.max_message_length:
            reply = reply[: self.config.max_message_length - 20] + "\n\n[truncated]"

        return reply

    async def _handle_media(
        self,
        payload: TwilioWebhookPayload,
        media_urls: List[Dict[str, str]],
        session: WhatsAppSession,
    ) -> str:
        """Handle media message (image, audio, video, document)."""
        media_info = []
        for m in media_urls:
            ct = m["content_type"]
            if ct.startswith("image/"):
                media_info.append(f"Image ({ct})")
            elif ct.startswith("audio/"):
                media_info.append(f"Audio ({ct})")
            elif ct.startswith("video/"):
                media_info.append(f"Video ({ct})")
            else:
                media_info.append(f"File ({ct})")

        caption = payload.Body.strip() if payload.Body else ""
        media_desc = ", ".join(media_info)

        # For now, describe media and route caption text if present
        if caption:
            content = f"[Media: {media_desc}] {caption}"
        else:
            content = f"[Media: {media_desc}]"

        # Route through AXE with media metadata
        message = IncomingMessage(
            connector_id=self.connector_id,
            connector_type="whatsapp",
            user=UserInfo(
                user_id=payload.get_phone_number(),
                username=payload.ProfileName,
                platform="whatsapp",
            ),
            content=content,
            content_type=MessageContentType.IMAGE,
            session_id=session.session_id,
            metadata={
                "message_sid": payload.MessageSid,
                "media": media_urls,
                "num_media": payload.NumMedia,
            },
        )

        brain_response = await self.send_to_brain(message)

        if brain_response.success:
            return brain_response.reply
        return (
            f"Received {len(media_urls)} media file(s). "
            f"Media processing is limited at this time."
        )

    async def _handle_location(
        self, payload: TwilioWebhookPayload, session: WhatsAppSession
    ) -> str:
        """Handle shared location."""
        lat = payload.Latitude
        lon = payload.Longitude

        message = IncomingMessage(
            connector_id=self.connector_id,
            connector_type="whatsapp",
            user=UserInfo(
                user_id=payload.get_phone_number(),
                username=payload.ProfileName,
                platform="whatsapp",
            ),
            content=f"[Location: {lat}, {lon}]",
            content_type=MessageContentType.LOCATION,
            session_id=session.session_id,
            metadata={
                "message_sid": payload.MessageSid,
                "latitude": lat,
                "longitude": lon,
            },
        )

        brain_response = await self.send_to_brain(message)

        if brain_response.success:
            return brain_response.reply
        return f"Location received: {lat}, {lon}"

    # ========================================================================
    # History
    # ========================================================================

    def get_history(self, phone_number: str, limit: int = 20) -> List[Dict[str, str]]:
        return self._history.get(phone_number, [])[-limit:]

    def clear_history(self, phone_number: str) -> bool:
        if phone_number in self._history:
            del self._history[phone_number]
            return True
        return False
