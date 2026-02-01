"""
Tests for the Connectors Module - Phase 1

Covers:
- Schemas and models
- BaseConnector ABC (via MockConnector)
- ConnectorService (registry, lifecycle, health, stats)
- CLIConnector (commands, message handling, session)
- Router endpoints
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.modules.connectors.schemas import (
    Attachment,
    BrainResponse,
    ConnectorActionRequest,
    ConnectorCapability,
    ConnectorHealth,
    ConnectorInfo,
    ConnectorListResponse,
    ConnectorStats,
    ConnectorStatus,
    ConnectorType,
    IncomingMessage,
    MessageContentType,
    MessageDirection,
    OutgoingMessage,
    SendMessageRequest,
    UserInfo,
)
from app.modules.connectors.base_connector import BaseConnector
from app.modules.connectors.service import ConnectorService
from app.modules.connectors.cli.connector import (
    CLIConnector,
    CLIOutputHandler,
    ConversationEntry,
)


# ============================================================================
# Mock Connector for testing BaseConnector
# ============================================================================


class MockConnector(BaseConnector):
    """Concrete implementation of BaseConnector for testing."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            connector_id=kwargs.get("connector_id", "mock_connector"),
            connector_type=kwargs.get("connector_type", ConnectorType.API),
            display_name=kwargs.get("display_name", "Mock Connector"),
            description=kwargs.get("description", "Test connector"),
            capabilities=kwargs.get("capabilities", [ConnectorCapability.TEXT]),
            axe_base_url=kwargs.get("axe_base_url", "http://localhost:8000"),
            dmz_gateway_id=kwargs.get("dmz_gateway_id", "mock_gateway"),
            dmz_shared_secret=kwargs.get("dmz_shared_secret", "test_secret"),
        )
        self.sent_messages: List[OutgoingMessage] = []
        self._fail_start = kwargs.get("fail_start", False)
        self._fail_health = kwargs.get("fail_health", False)

    async def start(self) -> None:
        await self._on_start()
        if self._fail_start:
            self._set_status(ConnectorStatus.ERROR)
            raise RuntimeError("Mock start failure")
        self._set_status(ConnectorStatus.CONNECTED)

    async def stop(self) -> None:
        await self._on_stop()

    async def send_to_user(self, user_id: str, message: OutgoingMessage) -> bool:
        self.sent_messages.append(message)
        return True

    async def health_check(self) -> ConnectorHealth:
        if self._fail_health:
            raise RuntimeError("Health check failed")
        return ConnectorHealth(
            connector_id=self.connector_id,
            status=self._status,
            latency_ms=5.0,
        )


# ============================================================================
# Test Schemas
# ============================================================================


class TestSchemas:
    """Test Pydantic schema models."""

    def test_connector_type_values(self) -> None:
        assert ConnectorType.CLI == "cli"
        assert ConnectorType.TELEGRAM == "telegram"
        assert ConnectorType.WHATSAPP == "whatsapp"
        assert ConnectorType.VOICE == "voice"

    def test_connector_status_values(self) -> None:
        assert ConnectorStatus.CONNECTED == "connected"
        assert ConnectorStatus.STOPPED == "stopped"
        assert ConnectorStatus.ERROR == "error"

    def test_user_info(self) -> None:
        user = UserInfo(user_id="u1", username="alice", display_name="Alice")
        assert user.user_id == "u1"
        assert user.platform is None

    def test_incoming_message(self) -> None:
        msg = IncomingMessage(
            connector_id="test",
            connector_type=ConnectorType.CLI,
            user=UserInfo(user_id="u1"),
            content="Hello",
        )
        assert msg.content == "Hello"
        assert msg.content_type == MessageContentType.TEXT
        assert msg.message_id.startswith("msg_")
        assert msg.timestamp > 0

    def test_outgoing_message(self) -> None:
        msg = OutgoingMessage(content="Response", reply_to="msg_123")
        assert msg.content == "Response"
        assert msg.reply_to == "msg_123"

    def test_brain_response(self) -> None:
        resp = BrainResponse(success=True, reply="Hello!", mode="llm-fallback")
        assert resp.success
        assert resp.reply == "Hello!"

    def test_connector_stats_record(self) -> None:
        stats = ConnectorStats()
        stats.record_incoming()
        assert stats.messages_received == 1
        stats.record_outgoing(100.0)
        assert stats.messages_sent == 1
        assert stats.avg_response_ms == 100.0
        stats.record_outgoing(200.0)
        assert stats.messages_sent == 2
        assert stats.avg_response_ms == 150.0
        stats.record_error()
        assert stats.errors == 1

    def test_attachment(self) -> None:
        att = Attachment(filename="test.pdf", mime_type="application/pdf", size_bytes=1024)
        assert att.filename == "test.pdf"

    def test_connector_info(self) -> None:
        info = ConnectorInfo(
            connector_id="test",
            connector_type=ConnectorType.CLI,
            display_name="Test",
        )
        assert info.version == "1.0.0"
        assert info.status == ConnectorStatus.STOPPED

    def test_connector_health(self) -> None:
        health = ConnectorHealth(
            connector_id="test",
            status=ConnectorStatus.CONNECTED,
            latency_ms=10.5,
        )
        assert health.checked_at > 0


# ============================================================================
# Test BaseConnector
# ============================================================================


class TestBaseConnector:
    """Test BaseConnector via MockConnector."""

    @pytest.fixture
    def connector(self) -> MockConnector:
        return MockConnector()

    @pytest.mark.asyncio
    async def test_initial_status(self, connector: MockConnector) -> None:
        assert connector.status == ConnectorStatus.STOPPED

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self, connector: MockConnector) -> None:
        await connector.start()
        assert connector.status == ConnectorStatus.CONNECTED
        assert connector._started_at is not None
        await connector.stop()
        assert connector.status == ConnectorStatus.STOPPED
        assert connector._started_at is None

    @pytest.mark.asyncio
    async def test_info_property(self, connector: MockConnector) -> None:
        info = connector.info
        assert info.connector_id == "mock_connector"
        assert info.connector_type == ConnectorType.API
        assert info.display_name == "Mock Connector"

    @pytest.mark.asyncio
    async def test_stats_tracking(self, connector: MockConnector) -> None:
        await connector.start()
        connector._stats.record_incoming()
        connector._stats.record_outgoing(50.0)
        stats = connector.stats
        assert stats.messages_received == 1
        assert stats.messages_sent == 1
        assert stats.uptime_seconds > 0
        await connector.stop()

    @pytest.mark.asyncio
    async def test_dmz_headers(self, connector: MockConnector) -> None:
        headers = connector._build_dmz_headers()
        assert headers["X-DMZ-Gateway-ID"] == "mock_gateway"
        expected_token = hashlib.sha256(b"mock_gateway:test_secret").hexdigest()
        assert headers["X-DMZ-Gateway-Token"] == expected_token

    @pytest.mark.asyncio
    async def test_dmz_headers_no_secret(self) -> None:
        c = MockConnector(dmz_shared_secret="")
        assert c._build_dmz_headers() == {}

    @pytest.mark.asyncio
    async def test_send_to_user(self, connector: MockConnector) -> None:
        msg = OutgoingMessage(content="Hi")
        result = await connector.send_to_user("u1", msg)
        assert result is True
        assert len(connector.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_health_check(self, connector: MockConnector) -> None:
        health = await connector.health_check()
        assert health.connector_id == "mock_connector"
        assert health.latency_ms == 5.0

    @pytest.mark.asyncio
    async def test_process_message_success(self, connector: MockConnector) -> None:
        """Test process_message with mocked send_to_brain."""
        await connector.start()

        mock_response = BrainResponse(
            success=True, reply="Brain says hi", mode="llm-fallback", duration_ms=42.0
        )

        with patch.object(connector, "send_to_brain", return_value=mock_response):
            msg = IncomingMessage(
                connector_id="mock_connector",
                connector_type=ConnectorType.API,
                user=UserInfo(user_id="u1"),
                content="Hello",
            )
            result = await connector.process_message(msg)
            assert result.content == "Brain says hi"
            assert result.metadata["mode"] == "llm-fallback"

        await connector.stop()

    @pytest.mark.asyncio
    async def test_process_message_error(self, connector: MockConnector) -> None:
        """Test process_message when BRAIN returns error."""
        await connector.start()

        mock_response = BrainResponse(success=False, error="Service unavailable")

        with patch.object(connector, "send_to_brain", return_value=mock_response):
            msg = IncomingMessage(
                connector_id="mock_connector",
                connector_type=ConnectorType.API,
                user=UserInfo(user_id="u1"),
                content="Hello",
            )
            result = await connector.process_message(msg)
            assert "Fehler" in result.content
            assert result.metadata.get("error") is True

        await connector.stop()


# ============================================================================
# Test ConnectorService
# ============================================================================


class TestConnectorService:
    """Test ConnectorService registry, lifecycle, and health."""

    @pytest.fixture
    def service(self) -> ConnectorService:
        return ConnectorService()

    @pytest.fixture
    def mock_conn(self) -> MockConnector:
        return MockConnector()

    def test_register(self, service: ConnectorService, mock_conn: MockConnector) -> None:
        service.register(mock_conn)
        assert service.get("mock_connector") is mock_conn

    def test_register_replace(self, service: ConnectorService) -> None:
        c1 = MockConnector(display_name="First")
        c2 = MockConnector(display_name="Second")
        service.register(c1)
        service.register(c2)
        assert service.get("mock_connector").display_name == "Second"

    def test_unregister(self, service: ConnectorService, mock_conn: MockConnector) -> None:
        service.register(mock_conn)
        assert service.unregister("mock_connector") is True
        assert service.get("mock_connector") is None

    def test_unregister_not_found(self, service: ConnectorService) -> None:
        assert service.unregister("nonexistent") is False

    def test_list_connectors(self, service: ConnectorService) -> None:
        service.register(MockConnector(connector_id="a"))
        service.register(MockConnector(connector_id="b"))
        infos = service.list_connectors()
        assert len(infos) == 2

    def test_list_by_type(self, service: ConnectorService) -> None:
        service.register(MockConnector(connector_id="a", connector_type=ConnectorType.CLI))
        service.register(MockConnector(connector_id="b", connector_type=ConnectorType.API))
        cli_list = service.list_by_type(ConnectorType.CLI)
        assert len(cli_list) == 1
        assert cli_list[0].connector_id == "a"

    @pytest.mark.asyncio
    async def test_list_active(self, service: ConnectorService) -> None:
        c1 = MockConnector(connector_id="a")
        c2 = MockConnector(connector_id="b")
        service.register(c1)
        service.register(c2)
        await service.start_connector("a")
        active = service.list_active()
        assert len(active) == 1
        assert active[0].connector_id == "a"
        await service.stop_connector("a")

    @pytest.mark.asyncio
    async def test_start_connector(self, service: ConnectorService, mock_conn: MockConnector) -> None:
        service.register(mock_conn)
        result = await service.start_connector("mock_connector")
        assert result is True
        assert mock_conn.status == ConnectorStatus.CONNECTED
        await service.stop_connector("mock_connector")

    @pytest.mark.asyncio
    async def test_start_not_found(self, service: ConnectorService) -> None:
        result = await service.start_connector("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_start_already_running(self, service: ConnectorService, mock_conn: MockConnector) -> None:
        service.register(mock_conn)
        await service.start_connector("mock_connector")
        result = await service.start_connector("mock_connector")
        assert result is True  # Already running returns True
        await service.stop_connector("mock_connector")

    @pytest.mark.asyncio
    async def test_stop_connector(self, service: ConnectorService, mock_conn: MockConnector) -> None:
        service.register(mock_conn)
        await service.start_connector("mock_connector")
        result = await service.stop_connector("mock_connector")
        assert result is True
        assert mock_conn.status == ConnectorStatus.STOPPED

    @pytest.mark.asyncio
    async def test_stop_not_found(self, service: ConnectorService) -> None:
        result = await service.stop_connector("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_restart_connector(self, service: ConnectorService, mock_conn: MockConnector) -> None:
        service.register(mock_conn)
        await service.start_connector("mock_connector")
        result = await service.restart_connector("mock_connector")
        assert result is True
        assert mock_conn.status == ConnectorStatus.CONNECTED
        await service.stop_connector("mock_connector")

    @pytest.mark.asyncio
    async def test_start_all_stop_all(self, service: ConnectorService) -> None:
        c1 = MockConnector(connector_id="a")
        c2 = MockConnector(connector_id="b")
        service.register(c1)
        service.register(c2)
        results = await service.start_all()
        assert results == {"a": True, "b": True}
        assert c1.status == ConnectorStatus.CONNECTED
        results = await service.stop_all()
        assert results == {"a": True, "b": True}
        assert c1.status == ConnectorStatus.STOPPED

    @pytest.mark.asyncio
    async def test_health_check(self, service: ConnectorService, mock_conn: MockConnector) -> None:
        service.register(mock_conn)
        health = await service.health_check("mock_connector")
        assert health is not None
        assert health.latency_ms == 5.0

    @pytest.mark.asyncio
    async def test_health_check_not_found(self, service: ConnectorService) -> None:
        health = await service.health_check("nonexistent")
        assert health is None

    @pytest.mark.asyncio
    async def test_health_check_error(self, service: ConnectorService) -> None:
        c = MockConnector(fail_health=True)
        service.register(c)
        health = await service.health_check("mock_connector")
        assert health is not None
        assert health.status == ConnectorStatus.ERROR

    @pytest.mark.asyncio
    async def test_health_check_all(self, service: ConnectorService) -> None:
        service.register(MockConnector(connector_id="a"))
        service.register(MockConnector(connector_id="b"))
        results = await service.health_check_all()
        assert len(results) == 2

    def test_get_stats(self, service: ConnectorService, mock_conn: MockConnector) -> None:
        service.register(mock_conn)
        stats = service.get_stats("mock_connector")
        assert stats is not None
        assert stats.messages_received == 0

    def test_get_stats_not_found(self, service: ConnectorService) -> None:
        assert service.get_stats("nonexistent") is None

    def test_aggregate_stats(self, service: ConnectorService) -> None:
        c1 = MockConnector(connector_id="a", connector_type=ConnectorType.CLI)
        c2 = MockConnector(connector_id="b", connector_type=ConnectorType.TELEGRAM)
        service.register(c1)
        service.register(c2)
        agg = service.get_aggregate_stats()
        assert agg["total_connectors"] == 2
        assert agg["active_connectors"] == 0
        assert agg["by_type"]["cli"] == 1
        assert agg["by_type"]["telegram"] == 1


# ============================================================================
# Test CLIConnector
# ============================================================================


class TestCLIOutputHandler:
    """Test CLI output formatting."""

    def test_print_banner(self) -> None:
        handler = CLIOutputHandler()
        handler.print_banner()
        assert len(handler.output_buffer) == 1
        assert "BRAIN CLI" in handler.output_buffer[0]

    def test_print_user(self) -> None:
        handler = CLIOutputHandler()
        handler.print_user("Hello")
        assert "[You] Hello" in handler.output_buffer[0]

    def test_print_brain(self) -> None:
        handler = CLIOutputHandler()
        handler.print_brain("Response", duration_ms=42.0)
        assert "[BRAIN]" in handler.output_buffer[0]
        assert "42ms" in handler.output_buffer[0]

    def test_print_error(self) -> None:
        handler = CLIOutputHandler()
        handler.print_error("Something broke")
        assert "[ERROR]" in handler.output_buffer[0]

    def test_print_help(self) -> None:
        handler = CLIOutputHandler()
        handler.print_help()
        assert "/help" in handler.output_buffer[0]
        assert "/exit" in handler.output_buffer[0]


class TestCLIConnector:
    """Test CLI connector commands and message handling."""

    @pytest.fixture
    def cli(self) -> CLIConnector:
        return CLIConnector(
            axe_base_url="http://localhost:8000",
            user_id="test_user",
            username="Tester",
        )

    @pytest.mark.asyncio
    async def test_start_stop(self, cli: CLIConnector) -> None:
        await cli.start()
        assert cli.status == ConnectorStatus.CONNECTED
        assert cli._running is True
        assert "BRAIN CLI" in cli.output.output_buffer[0]
        await cli.stop()
        assert cli.status == ConnectorStatus.STOPPED
        assert cli._running is False

    @pytest.mark.asyncio
    async def test_health_check(self, cli: CLIConnector) -> None:
        await cli.start()
        health = await cli.health_check()
        assert health.connector_id == "cli_connector"
        assert health.details["running"] is True
        await cli.stop()

    @pytest.mark.asyncio
    async def test_command_help(self, cli: CLIConnector) -> None:
        await cli.start()
        result = await cli.handle_input("/help")
        assert result is None
        assert any("/help" in o for o in cli.output.output_buffer)
        await cli.stop()

    @pytest.mark.asyncio
    async def test_command_status(self, cli: CLIConnector) -> None:
        await cli.start()
        result = await cli.handle_input("/status")
        assert result is None
        assert any("Session" in o for o in cli.output.output_buffer)
        await cli.stop()

    @pytest.mark.asyncio
    async def test_command_session(self, cli: CLIConnector) -> None:
        await cli.start()
        await cli.handle_input("/session")
        assert any("test_user" in o for o in cli.output.output_buffer)
        await cli.stop()

    @pytest.mark.asyncio
    async def test_command_stats(self, cli: CLIConnector) -> None:
        await cli.start()
        await cli.handle_input("/stats")
        assert any("Messages received" in o for o in cli.output.output_buffer)
        await cli.stop()

    @pytest.mark.asyncio
    async def test_command_history_empty(self, cli: CLIConnector) -> None:
        await cli.start()
        await cli.handle_input("/history")
        assert any("No conversation" in o for o in cli.output.output_buffer)
        await cli.stop()

    @pytest.mark.asyncio
    async def test_command_clear(self, cli: CLIConnector) -> None:
        await cli.start()
        cli.history.append(ConversationEntry("user", "test"))
        await cli.handle_input("/clear")
        assert len(cli.history) == 0
        await cli.stop()

    @pytest.mark.asyncio
    async def test_command_exit(self, cli: CLIConnector) -> None:
        await cli.start()
        await cli.handle_input("/exit")
        assert cli._running is False
        await cli.stop()

    @pytest.mark.asyncio
    async def test_command_quit(self, cli: CLIConnector) -> None:
        await cli.start()
        await cli.handle_input("/quit")
        assert cli._running is False
        await cli.stop()

    @pytest.mark.asyncio
    async def test_unknown_command(self, cli: CLIConnector) -> None:
        await cli.start()
        await cli.handle_input("/unknown")
        assert any("Unknown command" in o for o in cli.output.output_buffer)
        await cli.stop()

    @pytest.mark.asyncio
    async def test_empty_input(self, cli: CLIConnector) -> None:
        await cli.start()
        result = await cli.handle_input("")
        assert result is None
        result = await cli.handle_input("   ")
        assert result is None
        await cli.stop()

    @pytest.mark.asyncio
    async def test_message_handling(self, cli: CLIConnector) -> None:
        """Test regular message routing through process_message."""
        await cli.start()

        mock_response = BrainResponse(
            success=True, reply="Brain response", mode="llm-fallback", duration_ms=50.0
        )

        with patch.object(cli, "send_to_brain", return_value=mock_response):
            result = await cli.handle_input("Hello Brain")
            assert result == "Brain response"
            assert len(cli.history) == 2  # user + brain
            assert cli.history[0].role == "user"
            assert cli.history[0].content == "Hello Brain"
            assert cli.history[1].role == "brain"
            assert cli.history[1].content == "Brain response"

        await cli.stop()

    @pytest.mark.asyncio
    async def test_history_display(self, cli: CLIConnector) -> None:
        await cli.start()
        cli.history.append(ConversationEntry("user", "msg1"))
        cli.history.append(ConversationEntry("brain", "reply1"))
        await cli.handle_input("/history")
        output = "\n".join(cli.output.output_buffer)
        assert "[You]" in output
        assert "[BRAIN]" in output
        await cli.stop()

    @pytest.mark.asyncio
    async def test_send_to_user(self, cli: CLIConnector) -> None:
        await cli.start()
        msg = OutgoingMessage(content="Test output", metadata={"duration_ms": 25.0})
        result = await cli.send_to_user("test_user", msg)
        assert result is True
        assert any("Test output" in o for o in cli.output.output_buffer)
        await cli.stop()

    @pytest.mark.asyncio
    async def test_interactive_loop(self, cli: CLIConnector) -> None:
        """Test run_interactive with scripted inputs."""
        inputs = iter(["Hello", "/exit"])

        mock_response = BrainResponse(
            success=True, reply="Hi!", mode="llm-fallback"
        )

        with patch.object(cli, "send_to_brain", return_value=mock_response):
            await cli.run_interactive(input_fn=lambda: next(inputs))

        assert cli.status == ConnectorStatus.STOPPED
        assert len(cli.history) == 2  # user + brain

    @pytest.mark.asyncio
    async def test_interactive_eof(self, cli: CLIConnector) -> None:
        """Test run_interactive handles EOFError (Ctrl+D)."""
        def raise_eof() -> str:
            raise EOFError()

        await cli.run_interactive(input_fn=raise_eof)
        assert cli.status == ConnectorStatus.STOPPED


# ============================================================================
# Test Conversation Entry
# ============================================================================


class TestConversationEntry:
    def test_creation(self) -> None:
        entry = ConversationEntry("user", "Hello")
        assert entry.role == "user"
        assert entry.content == "Hello"
        assert entry.timestamp > 0

    def test_custom_timestamp(self) -> None:
        entry = ConversationEntry("brain", "Hi", timestamp=1000.0)
        assert entry.timestamp == 1000.0
