"""
WhatsApp Connector - Schemas

Models for Twilio WhatsApp Business API integration:
config, webhook payloads, template messages, media handling.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Configuration
# ============================================================================


class WhatsAppConfig(BaseModel):
    """Configuration for WhatsApp via Twilio."""
    account_sid: str = ""
    auth_token: str = ""
    whatsapp_number: str = ""          # e.g., "whatsapp:+14155238886"
    webhook_path: str = "/api/connectors/v2/whatsapp/webhook"
    status_callback_path: str = "/api/connectors/v2/whatsapp/status"
    verify_signature: bool = True       # Validate Twilio request signatures
    allowed_numbers: List[str] = Field(default_factory=list)  # Empty = all
    admin_numbers: List[str] = Field(default_factory=list)
    max_message_length: int = 1600      # WhatsApp limit
    rate_limit_messages: int = 20       # Per minute per user
    rate_limit_window: float = 60.0
    media_download_timeout: float = 30.0


# ============================================================================
# Webhook Payloads (Twilio format)
# ============================================================================


class TwilioWebhookPayload(BaseModel):
    """Incoming webhook payload from Twilio."""
    MessageSid: str = ""
    AccountSid: str = ""
    From: str = ""                      # "whatsapp:+491234567890"
    To: str = ""                        # "whatsapp:+14155238886"
    Body: str = ""
    NumMedia: int = 0
    # Media fields (populated when NumMedia > 0)
    MediaUrl0: Optional[str] = None
    MediaContentType0: Optional[str] = None
    MediaUrl1: Optional[str] = None
    MediaContentType1: Optional[str] = None
    MediaUrl2: Optional[str] = None
    MediaContentType2: Optional[str] = None
    # Location (if shared)
    Latitude: Optional[str] = None
    Longitude: Optional[str] = None
    # Profile info
    ProfileName: Optional[str] = None

    def get_phone_number(self) -> str:
        """Extract phone number without whatsapp: prefix."""
        return self.From.replace("whatsapp:", "")

    def get_media_urls(self) -> List[Dict[str, str]]:
        """Get all media attachments as list of {url, content_type}."""
        media = []
        for i in range(self.NumMedia):
            url = getattr(self, f"MediaUrl{i}", None)
            ct = getattr(self, f"MediaContentType{i}", None)
            if url:
                media.append({"url": url, "content_type": ct or "application/octet-stream"})
        return media


class MessageStatus(str, Enum):
    """WhatsApp message delivery status."""
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    UNDELIVERED = "undelivered"


class TwilioStatusPayload(BaseModel):
    """Status callback payload from Twilio."""
    MessageSid: str = ""
    MessageStatus: str = ""
    To: str = ""
    From: str = ""
    ErrorCode: Optional[str] = None
    ErrorMessage: Optional[str] = None


# ============================================================================
# Sessions
# ============================================================================


class WhatsAppSession(BaseModel):
    """Tracks a WhatsApp user's session state."""
    phone_number: str
    profile_name: Optional[str] = None
    session_id: str = ""
    message_count: int = 0
    last_message_at: float = 0.0
    created_at: float = Field(default_factory=time.time)
    context: Dict[str, Any] = Field(default_factory=dict)

    def is_rate_limited(self, max_messages: int = 20, window: float = 60.0) -> bool:
        if time.time() - self.last_message_at > window:
            return False
        return self.message_count >= max_messages


# ============================================================================
# Template Messages
# ============================================================================


class TemplateParameter(BaseModel):
    """Parameter for a WhatsApp template message."""
    type: str = "text"                  # text, currency, date_time, image, document, video
    text: Optional[str] = None
    currency: Optional[Dict[str, Any]] = None
    date_time: Optional[Dict[str, Any]] = None


class TemplateMessage(BaseModel):
    """WhatsApp Business API template message."""
    template_name: str
    language_code: str = "en"
    header_params: List[TemplateParameter] = Field(default_factory=list)
    body_params: List[TemplateParameter] = Field(default_factory=list)
    button_params: List[TemplateParameter] = Field(default_factory=list)


# ============================================================================
# Media
# ============================================================================


class MediaType(str, Enum):
    """WhatsApp supported media types."""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"


class MediaMessage(BaseModel):
    """Media attachment in a WhatsApp message."""
    media_type: MediaType
    url: Optional[str] = None
    content_type: str = ""
    filename: Optional[str] = None
    caption: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
