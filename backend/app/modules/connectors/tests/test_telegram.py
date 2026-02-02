"""
Tests for the Telegram Connector - Phase 3

Covers:
- Telegram schemas (config, sessions, approvals, commands)
- SessionManager (create, get, clear, rate limiting)
- ApprovalManager (create, resolve, list pending, expiration)
- TelegramMessageHandler (commands, text, voice, file, callbacks)
- TelegramConnector (lifecycle, health, handler-only mode)
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.connectors.schemas import (
    BrainResponse,
    ConnectorStatus,
    IncomingMessage,
    OutgoingMessage,
)
from app.modules.connectors.telegram.schemas import (
    ApprovalRequest,
    ApprovalStatus,
    DEFAULT_COMMANDS,
    TelegramBotConfig,
    TelegramCommand,
    TelegramUserSession,
)
from app.modules.connectors.telegram.handlers import (
    ApprovalManager,
    SessionManager,
    TelegramMessageHandler,
)
from app.modules.connectors.telegram.connector import TelegramConnector


# ============================================================================
# Helpers
# ============================================================================


def make_handler(
    allowed_chat_ids: list = None,
    admin_chat_ids: list = None,
) -> TelegramMessageHandler:
    """Create a TelegramMessageHandler with a mocked send_to_brain."""
    config = TelegramBotConfig(
        bot_token="test_token",
        allowed_chat_ids=allowed_chat_ids or [],
        admin_chat_ids=admin_chat_ids or [],
        rate_limit_messages=5,
        rate_limit_window=60.0,
    )
    mock_brain = AsyncMock(
        return_value=BrainResponse(
            success=True, reply="Brain reply", mode="llm-fallback", duration_ms=50.0
        )
    )
    return TelegramMessageHandler(
        config=config,
        send_to_brain_fn=mock_brain,
        connector_id="test_telegram",
    )


# ============================================================================
# Test Schemas
# ============================================================================


class TestTelegramSchemas:
    def test_bot_config_defaults(self) -> None:
        config = TelegramBotConfig()
        assert config.bot_token == ""
        assert config.use_polling is True
        assert config.max_message_length == 4096
        assert config.parse_mode == "Markdown"

    def test_user_session(self) -> None:
        session = TelegramUserSession(
            chat_id=123, user_id=456, username="alice"
        )
        assert session.chat_id == 123
        assert session.message_count == 0
        assert session.session_id == ""

    def test_session_rate_limit_not_exceeded(self) -> None:
        session = TelegramUserSession(
            chat_id=123, user_id=456, message_count=3, last_message_at=time.time()
        )
        assert session.is_rate_limited(max_messages=5) is False

    def test_session_rate_limit_exceeded(self) -> None:
        session = TelegramUserSession(
            chat_id=123, user_id=456, message_count=10, last_message_at=time.time()
        )
        assert session.is_rate_limited(max_messages=5) is True

    def test_session_rate_limit_window_expired(self) -> None:
        session = TelegramUserSession(
            chat_id=123, user_id=456, message_count=100,
            last_message_at=time.time() - 120,
        )
        assert session.is_rate_limited(max_messages=5, window=60.0) is False

    def test_approval_request(self) -> None:
        req = ApprovalRequest(
            approval_id="apr_test",
            chat_id=123,
            description="Deploy v1.2",
            requested_by="ops_agent",
        )
        assert req.status == ApprovalStatus.PENDING
        assert req.created_at > 0

    def test_default_commands(self) -> None:
        assert len(DEFAULT_COMMANDS) >= 5
        cmds = {c.command for c in DEFAULT_COMMANDS}
        assert "start" in cmds
        assert "help" in cmds
        assert "status" in cmds

    def test_telegram_command(self) -> None:
        cmd = TelegramCommand(command="test", description="Test cmd", admin_only=True)
        assert cmd.admin_only is True


# ============================================================================
# Test SessionManager
# ============================================================================


class TestSessionManager:
    def test_get_or_create(self) -> None:
        sm = SessionManager()
        session = sm.get_or_create(100, 200, "alice")
        assert session.chat_id == 100
        assert session.user_id == 200
        assert session.username == "alice"
        assert session.session_id.startswith("tg_100_")
        assert session.message_count == 1

    def test_get_existing(self) -> None:
        sm = SessionManager()
        s1 = sm.get_or_create(100, 200)
        s2 = sm.get_or_create(100, 200)
        assert s1.session_id == s2.session_id
        assert s2.message_count == 2

    def test_get_not_found(self) -> None:
        sm = SessionManager()
        assert sm.get(999) is None

    def test_clear_session(self) -> None:
        sm = SessionManager()
        sm.get_or_create(100, 200)
        assert sm.clear_session(100) is True
        assert sm.get(100) is None

    def test_clear_not_found(self) -> None:
        sm = SessionManager()
        assert sm.clear_session(999) is False

    def test_list_sessions(self) -> None:
        sm = SessionManager()
        sm.get_or_create(100, 200)
        sm.get_or_create(101, 201)
        assert len(sm.list_sessions()) == 2

    def test_active_count(self) -> None:
        sm = SessionManager()
        sm.get_or_create(100, 200)
        assert sm.active_count == 1


# ============================================================================
# Test ApprovalManager
# ============================================================================


class TestApprovalManager:
    def test_create_approval(self) -> None:
        am = ApprovalManager()
        a = am.create(100, "Deploy v1.2", "ops_agent")
        assert a.approval_id.startswith("apr_")
        assert a.status == ApprovalStatus.PENDING
        assert a.chat_id == 100

    def test_get_approval(self) -> None:
        am = ApprovalManager()
        a = am.create(100, "Test", "agent")
        result = am.get(a.approval_id)
        assert result is not None
        assert result.approval_id == a.approval_id

    def test_get_not_found(self) -> None:
        am = ApprovalManager()
        assert am.get("nonexistent") is None

    def test_resolve_approve(self) -> None:
        am = ApprovalManager()
        a = am.create(100, "Test", "agent")
        result = am.resolve(a.approval_id, ApprovalStatus.APPROVED)
        assert result is not None
        assert result.status == ApprovalStatus.APPROVED

    def test_resolve_reject(self) -> None:
        am = ApprovalManager()
        a = am.create(100, "Test", "agent")
        result = am.resolve(a.approval_id, ApprovalStatus.REJECTED)
        assert result.status == ApprovalStatus.REJECTED

    def test_resolve_already_resolved(self) -> None:
        am = ApprovalManager()
        a = am.create(100, "Test", "agent")
        am.resolve(a.approval_id, ApprovalStatus.APPROVED)
        result = am.resolve(a.approval_id, ApprovalStatus.REJECTED)
        assert result is None  # Already resolved

    def test_resolve_not_found(self) -> None:
        am = ApprovalManager()
        assert am.resolve("nonexistent", ApprovalStatus.APPROVED) is None

    def test_list_pending(self) -> None:
        am = ApprovalManager()
        am.create(100, "A", "agent")
        am.create(100, "B", "agent")
        am.create(200, "C", "agent")
        assert len(am.list_pending()) == 3
        assert len(am.list_pending(chat_id=100)) == 2

    def test_list_pending_excludes_resolved(self) -> None:
        am = ApprovalManager()
        a = am.create(100, "A", "agent")
        am.create(100, "B", "agent")
        am.resolve(a.approval_id, ApprovalStatus.APPROVED)
        assert len(am.list_pending()) == 1

    def test_list_pending_expires(self) -> None:
        am = ApprovalManager()
        a = am.create(100, "A", "agent", expires_in=-1)  # Already expired
        pending = am.list_pending()
        assert len(pending) == 0
        assert am.get(a.approval_id).status == ApprovalStatus.EXPIRED


# ============================================================================
# Test TelegramMessageHandler - Commands
# ============================================================================


class TestTelegramCommands:
    @pytest.mark.asyncio
    async def test_cmd_start(self) -> None:
        h = make_handler()
        reply = await h.handle_command("/start", 100, 200, "alice")
        assert "Welcome" in reply
        assert "alice" in reply

    @pytest.mark.asyncio
    async def test_cmd_help(self) -> None:
        h = make_handler()
        reply = await h.handle_command("/help", 100, 200)
        assert "/start" in reply
        assert "/help" in reply

    @pytest.mark.asyncio
    async def test_cmd_help_admin(self) -> None:
        h = make_handler(admin_chat_ids=[100])
        reply = await h.handle_command("/help", 100, 200)
        assert "/approve" in reply

    @pytest.mark.asyncio
    async def test_cmd_status_no_session(self) -> None:
        h = make_handler()
        reply = await h.handle_command("/status", 100, 200)
        assert "No active session" in reply

    @pytest.mark.asyncio
    async def test_cmd_status_with_session(self) -> None:
        h = make_handler()
        h.sessions.get_or_create(100, 200)
        reply = await h.handle_command("/status", 100, 200)
        assert "Session" in reply

    @pytest.mark.asyncio
    async def test_cmd_history_empty(self) -> None:
        h = make_handler()
        reply = await h.handle_command("/history", 100, 200)
        assert "No conversation" in reply

    @pytest.mark.asyncio
    async def test_cmd_clear(self) -> None:
        h = make_handler()
        h.sessions.get_or_create(100, 200)
        h._history[100] = [{"role": "user", "content": "test"}]
        reply = await h.handle_command("/clear", 100, 200)
        assert "cleared" in reply
        assert 100 not in h._history

    @pytest.mark.asyncio
    async def test_cmd_approve_non_admin(self) -> None:
        h = make_handler(admin_chat_ids=[999])
        reply = await h.handle_command("/approve", 100, 200)
        assert "admin-only" in reply

    @pytest.mark.asyncio
    async def test_cmd_approve_admin_no_pending(self) -> None:
        h = make_handler(admin_chat_ids=[100])
        reply = await h.handle_command("/approve", 100, 200)
        assert "No pending" in reply

    @pytest.mark.asyncio
    async def test_cmd_approve_admin_with_pending(self) -> None:
        h = make_handler(admin_chat_ids=[100])
        h.approvals.create(100, "Deploy v1.2", "ops")
        reply = await h.handle_command("/approve", 100, 200)
        assert "Deploy v1.2" in reply

    @pytest.mark.asyncio
    async def test_cmd_unknown(self) -> None:
        h = make_handler()
        reply = await h.handle_command("/foobar", 100, 200)
        assert "Unknown command" in reply


# ============================================================================
# Test TelegramMessageHandler - Messages
# ============================================================================


class TestTelegramMessages:
    @pytest.mark.asyncio
    async def test_text_message(self) -> None:
        h = make_handler()
        reply = await h.handle_text_message("Hello", 100, 200, "alice")
        assert reply == "Brain reply"
        assert len(h._history[100]) == 2
        assert h._history[100][0]["role"] == "user"
        assert h._history[100][1]["role"] == "brain"

    @pytest.mark.asyncio
    async def test_text_message_unauthorized_chat(self) -> None:
        h = make_handler(allowed_chat_ids=[999])
        reply = await h.handle_text_message("Hello", 100, 200)
        assert "not authorized" in reply

    @pytest.mark.asyncio
    async def test_text_message_rate_limited(self) -> None:
        h = make_handler()
        # Simulate rate limit: create session with high message count
        session = h.sessions.get_or_create(100, 200)
        session.message_count = 10
        session.last_message_at = time.time()
        reply = await h.handle_text_message("Hello", 100, 200)
        assert "Rate limit" in reply

    @pytest.mark.asyncio
    async def test_text_message_brain_error(self) -> None:
        h = make_handler()
        h.send_to_brain = AsyncMock(
            return_value=BrainResponse(success=False, error="Service down")
        )
        reply = await h.handle_text_message("Hello", 100, 200)
        assert "Error" in reply

    @pytest.mark.asyncio
    async def test_text_message_truncation(self) -> None:
        h = make_handler()
        long_reply = "x" * 5000
        h.send_to_brain = AsyncMock(
            return_value=BrainResponse(success=True, reply=long_reply, mode="llm")
        )
        reply = await h.handle_text_message("Hello", 100, 200)
        assert len(reply) <= 4096
        assert "[truncated]" in reply

    @pytest.mark.asyncio
    async def test_voice_message(self) -> None:
        h = make_handler()
        reply = await h.handle_voice_message(100, 200, "file_123", 5)
        assert "Voice messages" in reply

    @pytest.mark.asyncio
    async def test_file_message(self) -> None:
        h = make_handler()
        reply = await h.handle_file(100, 200, "report.pdf", 10240, "application/pdf")
        assert "report.pdf" in reply
        assert "10.0 KB" in reply

    @pytest.mark.asyncio
    async def test_approval_callback_approve(self) -> None:
        h = make_handler(admin_chat_ids=[100])
        a = h.approvals.create(100, "Test", "agent")
        reply = await h.handle_approval_callback(a.approval_id, "approve", 100)
        assert "approved" in reply

    @pytest.mark.asyncio
    async def test_approval_callback_reject(self) -> None:
        h = make_handler(admin_chat_ids=[100])
        a = h.approvals.create(100, "Test", "agent")
        reply = await h.handle_approval_callback(a.approval_id, "reject", 100)
        assert "rejected" in reply

    @pytest.mark.asyncio
    async def test_approval_callback_non_admin(self) -> None:
        h = make_handler(admin_chat_ids=[999])
        a = h.approvals.create(100, "Test", "agent")
        reply = await h.handle_approval_callback(a.approval_id, "approve", 100)
        assert "admin" in reply.lower()

    @pytest.mark.asyncio
    async def test_approval_callback_not_found(self) -> None:
        h = make_handler(admin_chat_ids=[100])
        reply = await h.handle_approval_callback("nonexistent", "approve", 100)
        assert "not found" in reply

    @pytest.mark.asyncio
    async def test_access_control_allowed(self) -> None:
        h = make_handler(allowed_chat_ids=[100, 200])
        assert h.is_chat_allowed(100) is True
        assert h.is_chat_allowed(999) is False

    @pytest.mark.asyncio
    async def test_access_control_empty_allows_all(self) -> None:
        h = make_handler(allowed_chat_ids=[])
        assert h.is_chat_allowed(100) is True
        assert h.is_chat_allowed(999) is True


# ============================================================================
# Test TelegramConnector
# ============================================================================


class TestTelegramConnector:
    @pytest.fixture
    def connector(self) -> TelegramConnector:
        return TelegramConnector(
            config=TelegramBotConfig(bot_token=""),
            axe_base_url="http://localhost:8000",
        )

    @pytest.mark.asyncio
    async def test_start_handler_only_mode(self, connector: TelegramConnector) -> None:
        """Without bot token, starts in handler-only mode."""
        await connector.start()
        assert connector.status == ConnectorStatus.CONNECTED
        assert connector._application is None
        await connector.stop()

    @pytest.mark.asyncio
    async def test_stop(self, connector: TelegramConnector) -> None:
        await connector.start()
        await connector.stop()
        assert connector.status == ConnectorStatus.STOPPED

    @pytest.mark.asyncio
    async def test_health_check(self, connector: TelegramConnector) -> None:
        await connector.start()
        health = await connector.health_check()
        assert health.connector_id == "telegram_connector"
        assert health.details["bot_token_set"] is False
        assert health.details["mode"] == "polling"
        await connector.stop()

    @pytest.mark.asyncio
    async def test_send_to_user_handler_only(self, connector: TelegramConnector) -> None:
        await connector.start()
        msg = OutgoingMessage(content="Hello")
        result = await connector.send_to_user("123", msg)
        assert result is True  # Succeeds in handler-only mode
        await connector.stop()

    @pytest.mark.asyncio
    async def test_handler_integration(self, connector: TelegramConnector) -> None:
        """Test that handler works through connector."""
        await connector.start()
        reply = await connector.handler.handle_command("/help", 100, 200)
        assert "/help" in reply
        await connector.stop()
