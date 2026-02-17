"""
Telegram Connector - Message & Command Handlers

Processes incoming Telegram messages and commands, routes them
through AXE Core via BaseConnector, and formats responses.

Handles:
- Text messages -> AXE Core -> Reply
- Commands (/start, /help, /status, /history, /clear)
- Voice messages -> placeholder for Voice Service (Phase 4)
- File uploads -> metadata extraction
- Inline keyboard callbacks (approval flow)
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from app.modules.connectors.schemas import (
    BrainResponse,
    IncomingMessage,
    MessageContentType,
    OutgoingMessage,
    UserInfo,
)
from app.modules.connectors.telegram.schemas import (
    ApprovalRequest,
    ApprovalStatus,
    TelegramBotConfig,
    TelegramUserSession,
)


class SessionManager:
    """Manages Telegram user sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[int, TelegramUserSession] = {}

    def get_or_create(
        self,
        chat_id: int,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> TelegramUserSession:
        """Get existing session or create a new one."""
        if chat_id not in self._sessions:
            self._sessions[chat_id] = TelegramUserSession(
                chat_id=chat_id,
                user_id=user_id,
                username=username,
                first_name=first_name,
                language_code=language_code,
                session_id=f"tg_{chat_id}_{uuid.uuid4().hex[:8]}",
            )
        session = self._sessions[chat_id]
        session.message_count += 1
        session.last_message_at = time.time()
        return session

    def get(self, chat_id: int) -> Optional[TelegramUserSession]:
        return self._sessions.get(chat_id)

    def clear_session(self, chat_id: int) -> bool:
        if chat_id in self._sessions:
            del self._sessions[chat_id]
            return True
        return False

    def list_sessions(self) -> List[TelegramUserSession]:
        return list(self._sessions.values())

    @property
    def active_count(self) -> int:
        cutoff = time.time() - 3600  # Active within last hour
        return sum(1 for s in self._sessions.values() if s.last_message_at > cutoff)


class ApprovalManager:
    """Manages approval requests sent via inline keyboards."""

    def __init__(self) -> None:
        self._approvals: Dict[str, ApprovalRequest] = {}

    def create(
        self,
        chat_id: int,
        description: str,
        requested_by: str,
        expires_in: float = 3600.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        approval = ApprovalRequest(
            approval_id=f"apr_{uuid.uuid4().hex[:10]}",
            chat_id=chat_id,
            description=description,
            requested_by=requested_by,
            expires_at=time.time() + expires_in,
            metadata=metadata or {},
        )
        self._approvals[approval.approval_id] = approval
        return approval

    def get(self, approval_id: str) -> Optional[ApprovalRequest]:
        return self._approvals.get(approval_id)

    def resolve(self, approval_id: str, status: ApprovalStatus) -> Optional[ApprovalRequest]:
        approval = self._approvals.get(approval_id)
        if not approval:
            return None
        if approval.status != ApprovalStatus.PENDING:
            return None
        approval.status = status
        return approval

    def list_pending(self, chat_id: Optional[int] = None) -> List[ApprovalRequest]:
        now = time.time()
        pending = []
        for a in self._approvals.values():
            if a.status != ApprovalStatus.PENDING:
                continue
            if a.expires_at and a.expires_at < now:
                a.status = ApprovalStatus.EXPIRED
                continue
            if chat_id is not None and a.chat_id != chat_id:
                continue
            pending.append(a)
        return pending


class TelegramMessageHandler:
    """
    Core message processing logic for the Telegram connector.

    Separated from the actual python-telegram-bot integration
    to enable testing without the Telegram library.
    """

    def __init__(
        self,
        config: TelegramBotConfig,
        send_to_brain_fn: Callable,
        connector_id: str = "telegram_connector",
    ) -> None:
        self.config = config
        self.send_to_brain = send_to_brain_fn
        self.connector_id = connector_id
        self.sessions = SessionManager()
        self.approvals = ApprovalManager()
        self._history: Dict[int, List[Dict[str, str]]] = {}

    # ========================================================================
    # Access Control
    # ========================================================================

    def is_chat_allowed(self, chat_id: int) -> bool:
        """Check if chat is allowed (empty list = all allowed)."""
        if not self.config.allowed_chat_ids:
            return True
        return chat_id in self.config.allowed_chat_ids

    def is_admin(self, chat_id: int) -> bool:
        return chat_id in self.config.admin_chat_ids

    # ========================================================================
    # Command Handlers
    # ========================================================================

    async def handle_command(
        self, command: str, chat_id: int, user_id: int, username: Optional[str] = None
    ) -> str:
        """Handle a /command and return response text."""
        cmd = command.lower().strip().split()[0].lstrip("/")

        if cmd == "start":
            return self._cmd_start(chat_id, user_id, username)

        if cmd == "help":
            return self._cmd_help(chat_id)

        if cmd == "status":
            return self._cmd_status(chat_id)

        if cmd == "history":
            return self._cmd_history(chat_id)

        if cmd == "clear":
            return self._cmd_clear(chat_id)

        if cmd == "approve":
            if not self.is_admin(chat_id):
                return "This command is admin-only."
            return self._cmd_approve(chat_id)

        return f"Unknown command: /{cmd}. Use /help for available commands."

    def _cmd_start(self, chat_id: int, user_id: int, username: Optional[str]) -> str:
        session = self.sessions.get_or_create(chat_id, user_id, username)
        return (
            f"Welcome to BRAIN, {username or 'User'}!\n\n"
            f"I'm the Auxiliary Execution Engine (AXE). "
            f"Send me a message and I'll process it through BRAIN.\n\n"
            f"Session: `{session.session_id}`\n"
            f"Use /help for available commands."
        )

    def _cmd_help(self, chat_id: int) -> str:
        lines = [
            "Available Commands:\n",
            "/start - Start BRAIN bot",
            "/help - Show this help",
            "/status - System status",
            "/history - Conversation history",
            "/clear - Clear history",
        ]
        if self.is_admin(chat_id):
            lines.append("/approve - List pending approvals (admin)")
        return "\n".join(lines)

    def _cmd_status(self, chat_id: int) -> str:
        session = self.sessions.get(chat_id)
        if not session:
            return "No active session. Send /start first."
        return (
            f"Session Status:\n"
            f"  Session: `{session.session_id}`\n"
            f"  Messages: {session.message_count}\n"
            f"  Active sessions: {self.sessions.active_count}"
        )

    def _cmd_history(self, chat_id: int) -> str:
        history = self._history.get(chat_id, [])
        if not history:
            return "No conversation history."
        lines = ["Recent messages:\n"]
        for entry in history[-10:]:
            role = "You" if entry["role"] == "user" else "BRAIN"
            content = entry["content"][:80]
            if len(entry["content"]) > 80:
                content += "..."
            lines.append(f"[{role}] {content}")
        return "\n".join(lines)

    def _cmd_clear(self, chat_id: int) -> str:
        self._history.pop(chat_id, None)
        self.sessions.clear_session(chat_id)
        return "Conversation history cleared. Send /start to begin a new session."

    def _cmd_approve(self, chat_id: int) -> str:
        pending = self.approvals.list_pending(chat_id)
        if not pending:
            return "No pending approvals."
        lines = ["Pending Approvals:\n"]
        for a in pending:
            lines.append(f"  [{a.approval_id}] {a.description} (by {a.requested_by})")
        return "\n".join(lines)

    # ========================================================================
    # Message Processing
    # ========================================================================

    async def handle_text_message(
        self,
        text: str,
        chat_id: int,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        message_id: Optional[int] = None,
    ) -> str:
        """Process a text message through AXE Core and return reply."""
        # Access control
        if not self.is_chat_allowed(chat_id):
            return "This chat is not authorized to use BRAIN."

        # Session
        session = self.sessions.get_or_create(
            chat_id, user_id, username, first_name
        )

        # Rate limiting
        if session.is_rate_limited(
            self.config.rate_limit_messages, self.config.rate_limit_window
        ):
            return "Rate limit exceeded. Please wait before sending more messages."

        # Save to history
        if chat_id not in self._history:
            self._history[chat_id] = []
        self._history[chat_id].append({"role": "user", "content": text})

        # Build IncomingMessage
        message = IncomingMessage(
            connector_id=self.connector_id,
            connector_type="telegram",
            user=UserInfo(
                user_id=str(user_id),
                username=username,
                display_name=first_name,
                platform="telegram",
                language=session.language_code,
            ),
            content=text,
            content_type=MessageContentType.TEXT,
            session_id=session.session_id,
            metadata={
                "chat_id": chat_id,
                "telegram_message_id": message_id,
            },
        )

        # Route through AXE Core
        brain_response: BrainResponse = await self.send_to_brain(message)

        if brain_response.success:
            reply = brain_response.reply
        else:
            reply = f"Error: {brain_response.error or 'Unknown error'}"
            logger.error(
                f"Telegram handler: AXE Core error for chat {chat_id}: "
                f"{brain_response.error}"
            )

        # Save response to history
        self._history[chat_id].append({"role": "brain", "content": reply})

        # Truncate if too long
        if len(reply) > self.config.max_message_length:
            reply = reply[: self.config.max_message_length - 20] + "\n\n[truncated]"

        return reply

    async def handle_voice_message(
        self,
        chat_id: int,
        user_id: int,
        file_id: str,
        duration: int,
        username: Optional[str] = None,
    ) -> str:
        """Handle voice message - placeholder for Phase 4 Voice Service."""
        return (
            "Voice messages will be supported in a future update. "
            "Please send your message as text for now."
        )

    async def handle_file(
        self,
        chat_id: int,
        user_id: int,
        file_name: str,
        file_size: int,
        mime_type: Optional[str] = None,
        username: Optional[str] = None,
    ) -> str:
        """Handle file upload - extract metadata and acknowledge."""
        return (
            f"File received: `{file_name}` "
            f"({file_size / 1024:.1f} KB, {mime_type or 'unknown type'})\n"
            f"File processing is not yet supported. "
            f"Please describe what you need in text."
        )

    # ========================================================================
    # Approval Callbacks
    # ========================================================================

    async def handle_approval_callback(
        self, approval_id: str, action: str, chat_id: int
    ) -> str:
        """Handle inline keyboard callback for approval flow."""
        if not self.is_admin(chat_id):
            return "Only admins can approve/reject."

        if action == "approve":
            result = self.approvals.resolve(approval_id, ApprovalStatus.APPROVED)
        elif action == "reject":
            result = self.approvals.resolve(approval_id, ApprovalStatus.REJECTED)
        else:
            return f"Unknown action: {action}"

        if not result:
            return "Approval not found or already resolved."

        return f"Approval {approval_id}: {result.status.value}"
