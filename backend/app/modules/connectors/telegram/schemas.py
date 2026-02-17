"""
Telegram Connector - Schemas

Telegram-specific models for bot configuration, user sessions,
inline keyboards (approval flow), and webhook payloads.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TelegramBotConfig(BaseModel):
    """Configuration for the Telegram bot."""
    bot_token: str = ""
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    use_polling: bool = True  # Polling (dev) vs Webhook (prod)
    allowed_chat_ids: List[int] = Field(default_factory=list)  # Empty = allow all
    admin_chat_ids: List[int] = Field(default_factory=list)
    max_message_length: int = 4096
    parse_mode: str = "Markdown"
    rate_limit_messages: int = 30  # Per minute per user
    rate_limit_window: float = 60.0


class TelegramUserSession(BaseModel):
    """Tracks a Telegram user's session state."""
    chat_id: int
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    language_code: Optional[str] = None
    session_id: str = ""
    message_count: int = 0
    last_message_at: float = 0.0
    created_at: float = Field(default_factory=time.time)
    context: Dict[str, Any] = Field(default_factory=dict)

    def is_rate_limited(self, max_messages: int = 30, window: float = 60.0) -> bool:
        """Check if user has exceeded rate limit."""
        if time.time() - self.last_message_at > window:
            return False
        return self.message_count >= max_messages


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequest(BaseModel):
    """An approval request sent via inline keyboard."""
    approval_id: str
    chat_id: int
    message_id: Optional[int] = None
    description: str
    requested_by: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TelegramCommand(BaseModel):
    """Represents a bot command."""
    command: str  # Without /
    description: str
    admin_only: bool = False


# Default bot commands
DEFAULT_COMMANDS: List[TelegramCommand] = [
    TelegramCommand(command="start", description="Start BRAIN bot"),
    TelegramCommand(command="help", description="Show available commands"),
    TelegramCommand(command="status", description="Show system status"),
    TelegramCommand(command="history", description="Show conversation history"),
    TelegramCommand(command="clear", description="Clear conversation history"),
    TelegramCommand(command="approve", description="List pending approvals", admin_only=True),
]
