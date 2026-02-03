"""
CLI Connector - Interactive Terminal Interface for BRAIN

Provides a rich terminal UI for direct BRAIN interaction.
Routes all messages through AXE Core via BaseConnector.send_to_brain().

Features:
- Rich formatted output (markdown, tables, code blocks)
- Command system (/help, /status, /clear, /history, /exit)
- Session management with conversation history
- Streaming-style output with typing indicator
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from app.modules.connectors.base_connector import BaseConnector
from app.modules.connectors.schemas import (
    BrainResponse,
    ConnectorCapability,
    ConnectorHealth,
    ConnectorStatus,
    ConnectorType,
    IncomingMessage,
    MessageContentType,
    OutgoingMessage,
    UserInfo,
)


class CLIOutputHandler:
    """
    Handles CLI output formatting.

    Abstracted to allow testing without actual terminal I/O.
    In production, uses rich library. In tests, collects output.
    """

    def __init__(self) -> None:
        self.output_buffer: List[str] = []

    def print_banner(self) -> None:
        banner = (
            "\n"
            "╔══════════════════════════════════════════════╗\n"
            "║           🧠 BRAIN CLI Connector             ║\n"
            "║     Auxiliary Execution Engine Interface      ║\n"
            "╠══════════════════════════════════════════════╣\n"
            "║  /help    - Show commands                    ║\n"
            "║  /status  - System status                    ║\n"
            "║  /history - Conversation history             ║\n"
            "║  /clear   - Clear history                    ║\n"
            "║  /exit    - Exit CLI                         ║\n"
            "╚══════════════════════════════════════════════╝\n"
        )
        self._write(banner)

    def print_user(self, text: str) -> None:
        self._write(f"\n[You] {text}")

    def print_brain(self, text: str, duration_ms: Optional[float] = None) -> None:
        timing = f" ({duration_ms:.0f}ms)" if duration_ms else ""
        self._write(f"\n[BRAIN]{timing} {text}")

    def print_error(self, text: str) -> None:
        self._write(f"\n[ERROR] {text}")

    def print_system(self, text: str) -> None:
        self._write(f"\n[SYSTEM] {text}")

    def print_help(self) -> None:
        help_text = (
            "\nAvailable Commands:\n"
            "  /help         - Show this help\n"
            "  /status       - Show connector status\n"
            "  /history      - Show conversation history\n"
            "  /clear        - Clear conversation history\n"
            "  /stats        - Show session statistics\n"
            "  /session      - Show session info\n"
            "  /exit, /quit  - Exit the CLI\n"
            "\nJust type your message to chat with BRAIN.\n"
        )
        self._write(help_text)

    def _write(self, text: str) -> None:
        self.output_buffer.append(text)


class ConversationEntry:
    """Single entry in the conversation history."""

    def __init__(
        self, role: str, content: str, timestamp: Optional[float] = None
    ) -> None:
        self.role = role
        self.content = content
        self.timestamp = timestamp or time.time()


class CLIConnector(BaseConnector):
    """
    Interactive CLI connector for BRAIN.

    Routes messages through AXE Core and presents responses
    in a formatted terminal interface.
    """

    COMMANDS = {"/help", "/status", "/history", "/clear", "/stats", "/session", "/exit", "/quit"}

    def __init__(
        self,
        axe_base_url: str = "http://localhost:8000",
        dmz_shared_secret: str = "",
        user_id: str = "cli_user",
        username: str = "CLI User",
        output_handler: Optional[CLIOutputHandler] = None,
    ):
        super().__init__(
            connector_id="cli_connector",
            connector_type=ConnectorType.CLI,
            display_name="BRAIN CLI",
            description="Interactive terminal interface for BRAIN",
            capabilities=[
                ConnectorCapability.TEXT,
                ConnectorCapability.RICH_FORMAT,
            ],
            axe_base_url=axe_base_url,
            dmz_gateway_id="cli_gateway",
            dmz_shared_secret=dmz_shared_secret,
        )
        self.user_id = user_id
        self.username = username
        self.session_id = f"cli_{uuid.uuid4().hex[:8]}"
        self.history: List[ConversationEntry] = []
        self.output = output_handler or CLIOutputHandler()
        self._running = False

    # ========================================================================
    # Lifecycle
    # ========================================================================

    async def start(self) -> None:
        """Start the CLI connector."""
        await self._on_start()
        self._running = True
        self._set_status(ConnectorStatus.CONNECTED)
        self.output.print_banner()

    async def stop(self) -> None:
        """Stop the CLI connector."""
        self._running = False
        self.output.print_system("BRAIN CLI disconnected. Auf Wiedersehen!")
        await self._on_stop()

    async def send_to_user(self, user_id: str, message: OutgoingMessage) -> bool:
        """Display message to the CLI user."""
        self.output.print_brain(
            message.content,
            duration_ms=message.metadata.get("duration_ms"),
        )
        return True

    async def health_check(self) -> ConnectorHealth:
        """Check CLI connector health."""
        return ConnectorHealth(
            connector_id=self.connector_id,
            status=self._status,
            last_message_at=self._stats.last_activity,
            details={
                "session_id": self.session_id,
                "history_length": len(self.history),
                "running": self._running,
            },
        )

    # ========================================================================
    # Message Processing
    # ========================================================================

    async def handle_input(self, user_input: str) -> Optional[str]:
        """
        Handle a single user input line.

        Returns the BRAIN response text, or None for commands/exit.
        """
        text = user_input.strip()
        if not text:
            return None

        # Handle commands
        if text.startswith("/"):
            return await self._handle_command(text.lower())

        # Regular message
        self.output.print_user(text)
        self.history.append(ConversationEntry("user", text))

        message = IncomingMessage(
            connector_id=self.connector_id,
            connector_type=self.connector_type,
            user=UserInfo(
                user_id=self.user_id,
                username=self.username,
                platform="cli",
            ),
            content=text,
            content_type=MessageContentType.TEXT,
            session_id=self.session_id,
        )

        response = await self.process_message(message)
        self.history.append(ConversationEntry("brain", response.content))

        await self.send_to_user(self.user_id, response)
        return response.content

    async def _handle_command(self, command: str) -> Optional[str]:
        """Handle a CLI command. Returns None to continue, raises to exit."""
        cmd = command.split()[0]

        if cmd in ("/exit", "/quit"):
            self._running = False
            return None

        if cmd == "/help":
            self.output.print_help()
            return None

        if cmd == "/status":
            health = await self.health_check()
            self.output.print_system(
                f"Status: {health.status.value}\n"
                f"  Session: {self.session_id}\n"
                f"  Messages: {self._stats.messages_received} in, "
                f"{self._stats.messages_sent} out\n"
                f"  Errors: {self._stats.errors}\n"
                f"  Avg Response: {self._stats.avg_response_ms:.0f}ms"
            )
            return None

        if cmd == "/history":
            if not self.history:
                self.output.print_system("No conversation history.")
                return None
            for entry in self.history[-20:]:  # Last 20 entries
                prefix = "[You]" if entry.role == "user" else "[BRAIN]"
                content = (
                    entry.content[:100] + "..."
                    if len(entry.content) > 100
                    else entry.content
                )
                self.output.print_system(f"  {prefix} {content}")
            return None

        if cmd == "/clear":
            self.history.clear()
            self.output.print_system("Conversation history cleared.")
            return None

        if cmd == "/stats":
            stats = self.stats
            self.output.print_system(
                f"Session Statistics:\n"
                f"  Messages received: {stats.messages_received}\n"
                f"  Messages sent: {stats.messages_sent}\n"
                f"  Errors: {stats.errors}\n"
                f"  Avg response: {stats.avg_response_ms:.0f}ms\n"
                f"  Uptime: {stats.uptime_seconds:.0f}s"
            )
            return None

        if cmd == "/session":
            self.output.print_system(
                f"Session Info:\n"
                f"  Session ID: {self.session_id}\n"
                f"  User: {self.username} ({self.user_id})\n"
                f"  Connector: {self.connector_id}\n"
                f"  AXE URL: {self.axe_base_url}\n"
                f"  DMZ Gateway: {self.dmz_gateway_id}"
            )
            return None

        self.output.print_error(f"Unknown command: {cmd}. Type /help for commands.")
        return None

    # ========================================================================
    # Interactive Loop
    # ========================================================================

    async def run_interactive(
        self,
        input_fn: Optional[Callable[[], str]] = None,
    ) -> None:
        """
        Run the interactive CLI loop.

        Args:
            input_fn: Custom input function (for testing). Defaults to built-in input().
        """
        await self.start()
        get_input = input_fn or (lambda: input("\n> "))

        try:
            while self._running:
                try:
                    user_input = get_input()
                    await self.handle_input(user_input)
                except (EOFError, KeyboardInterrupt):
                    break
        finally:
            await self.stop()
