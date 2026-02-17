"""
Connectors Module - Pydantic Models

Shared schemas for all connector implementations.
Defines the message contract between connectors and AXE Core.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Connector Identity & Status
# ============================================================================


class ConnectorType(str, Enum):
    """Types of connectors."""
    CLI = "cli"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    VOICE = "voice"
    DISCORD = "discord"
    WEB_WIDGET = "web_widget"
    EMAIL = "email"
    API = "api"


class ConnectorStatus(str, Enum):
    """Lifecycle status of a connector."""
    INITIALIZING = "initializing"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    STOPPED = "stopped"


class ConnectorCapability(str, Enum):
    """Capabilities a connector may support."""
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    FILE = "file"
    VIDEO = "video"
    LOCATION = "location"
    INLINE_BUTTONS = "inline_buttons"
    APPROVAL_FLOW = "approval_flow"
    RICH_FORMAT = "rich_format"
    STREAMING = "streaming"


class ConnectorHealth(BaseModel):
    """Health check result for a connector."""
    connector_id: str
    status: ConnectorStatus
    latency_ms: Optional[float] = None
    last_message_at: Optional[float] = None
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    checked_at: float = Field(default_factory=time.time)


class ConnectorInfo(BaseModel):
    """Public information about a connector."""
    connector_id: str
    connector_type: ConnectorType
    display_name: str
    description: str = ""
    version: str = "1.0.0"
    status: ConnectorStatus = ConnectorStatus.STOPPED
    capabilities: List[ConnectorCapability] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    stats: ConnectorStats = Field(default_factory=lambda: ConnectorStats())
    registered_at: float = Field(default_factory=time.time)


# ============================================================================
# Message Types
# ============================================================================


class MessageDirection(str, Enum):
    """Direction of a message."""
    INCOMING = "incoming"   # User -> Connector -> BRAIN
    OUTGOING = "outgoing"   # BRAIN -> Connector -> User


class MessageContentType(str, Enum):
    """Type of message content."""
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    FILE = "file"
    VIDEO = "video"
    LOCATION = "location"
    COMMAND = "command"
    SYSTEM = "system"


class Attachment(BaseModel):
    """File attachment in a message."""
    filename: str
    mime_type: str
    size_bytes: int = 0
    url: Optional[str] = None
    data: Optional[bytes] = None

    model_config = {"arbitrary_types_allowed": True}


class UserInfo(BaseModel):
    """Information about the message sender."""
    user_id: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    platform: Optional[str] = None
    language: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IncomingMessage(BaseModel):
    """Message from user to BRAIN via a connector."""
    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    connector_id: str
    connector_type: ConnectorType
    user: UserInfo
    content: str
    content_type: MessageContentType = MessageContentType.TEXT
    attachments: List[Attachment] = Field(default_factory=list)
    reply_to: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class OutgoingMessage(BaseModel):
    """Message from BRAIN to user via a connector."""
    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    content: str
    content_type: MessageContentType = MessageContentType.TEXT
    attachments: List[Attachment] = Field(default_factory=list)
    reply_to: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class BrainResponse(BaseModel):
    """Response from AXE Core after processing a message."""
    success: bool
    reply: str = ""
    mode: str = "unknown"  # "gateway" or "llm-fallback"
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


# ============================================================================
# Statistics
# ============================================================================


class ConnectorStats(BaseModel):
    """Runtime statistics for a connector."""
    messages_received: int = 0
    messages_sent: int = 0
    errors: int = 0
    avg_response_ms: float = 0.0
    active_sessions: int = 0
    uptime_seconds: float = 0.0
    last_activity: Optional[float] = None

    def record_incoming(self) -> None:
        self.messages_received += 1
        self.last_activity = time.time()

    def record_outgoing(self, response_ms: float = 0.0) -> None:
        self.messages_sent += 1
        self.last_activity = time.time()
        if response_ms > 0:
            total = self.avg_response_ms * (self.messages_sent - 1) + response_ms
            self.avg_response_ms = total / self.messages_sent

    def record_error(self) -> None:
        self.errors += 1
        self.last_activity = time.time()


# ============================================================================
# API Request/Response Schemas
# ============================================================================


class ConnectorListResponse(BaseModel):
    """Response for listing connectors."""
    connectors: List[ConnectorInfo]
    total: int


class ConnectorActionRequest(BaseModel):
    """Request to perform an action on a connector."""
    action: str  # start, stop, restart
    config: Dict[str, Any] = Field(default_factory=dict)


class ConnectorActionResponse(BaseModel):
    """Response from a connector action."""
    connector_id: str
    action: str
    success: bool
    message: str = ""
    error: Optional[str] = None


class SendMessageRequest(BaseModel):
    """Request to send a message through a connector."""
    connector_id: str
    user_id: str
    content: str
    content_type: MessageContentType = MessageContentType.TEXT
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SendMessageResponse(BaseModel):
    """Response after sending a message."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
