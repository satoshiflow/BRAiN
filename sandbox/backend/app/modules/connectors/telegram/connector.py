"""
Telegram Connector - BaseConnector Implementation

Integrates with python-telegram-bot library for actual Telegram API
communication. Uses TelegramMessageHandler for message processing logic.

Supports:
- Polling mode (development)
- Webhook mode (production) - via FastAPI route
- Text, voice (placeholder), file messages
- Inline keyboard approval flow
- Rate limiting per user
"""

from __future__ import annotations

import os
import time
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
from app.modules.connectors.telegram.handlers import TelegramMessageHandler
from app.modules.connectors.telegram.schemas import TelegramBotConfig


class TelegramConnector(BaseConnector):
    """
    Telegram bot connector for BRAIN.

    Routes all messages through AXE Core via BaseConnector.send_to_brain().
    The actual python-telegram-bot integration is optional - if the library
    is not installed, the connector works in "handler-only" mode for testing.
    """

    def __init__(
        self,
        config: Optional[TelegramBotConfig] = None,
        axe_base_url: str = "http://localhost:8000",
        dmz_shared_secret: str = "",
    ):
        super().__init__(
            connector_id="telegram_connector",
            connector_type=ConnectorType.TELEGRAM,
            display_name="BRAIN Telegram Bot",
            description="Telegram bot interface for BRAIN via AXE Core",
            capabilities=[
                ConnectorCapability.TEXT,
                ConnectorCapability.VOICE,
                ConnectorCapability.IMAGE,
                ConnectorCapability.FILE,
                ConnectorCapability.INLINE_BUTTONS,
                ConnectorCapability.APPROVAL_FLOW,
            ],
            axe_base_url=axe_base_url,
            dmz_gateway_id="telegram_gateway",
            dmz_shared_secret=dmz_shared_secret,
        )

        self.config = config or TelegramBotConfig(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        )
        self.handler = TelegramMessageHandler(
            config=self.config,
            send_to_brain_fn=self.send_to_brain,
            connector_id=self.connector_id,
        )
        self._application = None  # python-telegram-bot Application

    # ========================================================================
    # Lifecycle
    # ========================================================================

    async def start(self) -> None:
        """Start the Telegram connector."""
        await self._on_start()

        if not self.config.bot_token:
            logger.warning(
                "Telegram bot token not set. Running in handler-only mode."
            )
            self._set_status(ConnectorStatus.CONNECTED)
            return

        try:
            await self._start_bot()
            self._set_status(ConnectorStatus.CONNECTED)
        except ImportError:
            logger.warning(
                "python-telegram-bot not installed. Running in handler-only mode."
            )
            self._set_status(ConnectorStatus.CONNECTED)
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            self._set_status(ConnectorStatus.ERROR)
            raise

    async def _start_bot(self) -> None:
        """Initialize python-telegram-bot Application."""
        try:
            from telegram.ext import (
                Application,
                CommandHandler,
                MessageHandler,
                CallbackQueryHandler,
                filters,
            )
        except ImportError:
            raise ImportError("python-telegram-bot is not installed")

        builder = Application.builder().token(self.config.bot_token)
        self._application = builder.build()

        # Register handlers
        self._application.add_handler(
            CommandHandler("start", self._ptb_command_handler)
        )
        self._application.add_handler(
            CommandHandler("help", self._ptb_command_handler)
        )
        self._application.add_handler(
            CommandHandler("status", self._ptb_command_handler)
        )
        self._application.add_handler(
            CommandHandler("history", self._ptb_command_handler)
        )
        self._application.add_handler(
            CommandHandler("clear", self._ptb_command_handler)
        )
        self._application.add_handler(
            CommandHandler("approve", self._ptb_command_handler)
        )
        self._application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._ptb_text_handler)
        )
        self._application.add_handler(
            MessageHandler(filters.VOICE, self._ptb_voice_handler)
        )
        self._application.add_handler(
            MessageHandler(filters.Document.ALL, self._ptb_file_handler)
        )
        self._application.add_handler(
            CallbackQueryHandler(self._ptb_callback_handler)
        )

        if self.config.use_polling:
            await self._application.initialize()
            await self._application.start()
            await self._application.updater.start_polling()
            logger.info("Telegram bot started in polling mode")
        else:
            logger.info("Telegram bot ready for webhook mode")

    async def stop(self) -> None:
        """Stop the Telegram connector."""
        if self._application:
            try:
                if self._application.updater and self._application.updater.running:
                    await self._application.updater.stop()
                await self._application.stop()
                await self._application.shutdown()
            except Exception as e:
                logger.error(f"Error stopping Telegram bot: {e}")
            self._application = None
        await self._on_stop()

    async def send_to_user(self, user_id: str, message: OutgoingMessage) -> bool:
        """Send message to Telegram user/chat."""
        if not self._application:
            logger.debug(
                f"Handler-only mode: would send to {user_id}: {message.content[:50]}"
            )
            return True

        try:
            chat_id = int(user_id)
            await self._application.bot.send_message(
                chat_id=chat_id,
                text=message.content,
                parse_mode=self.config.parse_mode,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {user_id}: {e}")
            self._stats.record_error()
            return False

    async def health_check(self) -> ConnectorHealth:
        """Check Telegram connector health."""
        details: Dict[str, Any] = {
            "bot_token_set": bool(self.config.bot_token),
            "mode": "polling" if self.config.use_polling else "webhook",
            "active_sessions": self.handler.sessions.active_count,
            "total_sessions": len(self.handler.sessions.list_sessions()),
        }

        if self._application:
            try:
                me = await self._application.bot.get_me()
                details["bot_username"] = me.username
                details["bot_id"] = me.id
            except Exception:
                pass

        return ConnectorHealth(
            connector_id=self.connector_id,
            status=self._status,
            last_message_at=self._stats.last_activity,
            details=details,
        )

    # ========================================================================
    # python-telegram-bot Handlers (bridge to our handlers)
    # ========================================================================

    async def _ptb_command_handler(self, update: Any, context: Any) -> None:
        """Bridge PTB command to our handler."""
        msg = update.message
        if not msg:
            return
        command = msg.text
        reply = await self.handler.handle_command(
            command=command,
            chat_id=msg.chat_id,
            user_id=msg.from_user.id,
            username=msg.from_user.username,
        )
        await msg.reply_text(reply, parse_mode=self.config.parse_mode)

    async def _ptb_text_handler(self, update: Any, context: Any) -> None:
        """Bridge PTB text message to our handler."""
        msg = update.message
        if not msg or not msg.text:
            return
        reply = await self.handler.handle_text_message(
            text=msg.text,
            chat_id=msg.chat_id,
            user_id=msg.from_user.id,
            username=msg.from_user.username,
            first_name=msg.from_user.first_name,
            message_id=msg.message_id,
        )
        await msg.reply_text(reply, parse_mode=self.config.parse_mode)

    async def _ptb_voice_handler(self, update: Any, context: Any) -> None:
        """Bridge PTB voice message to our handler."""
        msg = update.message
        if not msg or not msg.voice:
            return
        reply = await self.handler.handle_voice_message(
            chat_id=msg.chat_id,
            user_id=msg.from_user.id,
            file_id=msg.voice.file_id,
            duration=msg.voice.duration,
            username=msg.from_user.username,
        )
        await msg.reply_text(reply)

    async def _ptb_file_handler(self, update: Any, context: Any) -> None:
        """Bridge PTB file message to our handler."""
        msg = update.message
        if not msg or not msg.document:
            return
        reply = await self.handler.handle_file(
            chat_id=msg.chat_id,
            user_id=msg.from_user.id,
            file_name=msg.document.file_name or "unknown",
            file_size=msg.document.file_size or 0,
            mime_type=msg.document.mime_type,
            username=msg.from_user.username,
        )
        await msg.reply_text(reply)

    async def _ptb_callback_handler(self, update: Any, context: Any) -> None:
        """Bridge PTB callback query (inline keyboard) to our handler."""
        query = update.callback_query
        if not query or not query.data:
            return

        # Expected format: "approve:<approval_id>" or "reject:<approval_id>"
        parts = query.data.split(":", 1)
        if len(parts) != 2:
            await query.answer("Invalid callback data")
            return

        action, approval_id = parts
        reply = await self.handler.handle_approval_callback(
            approval_id=approval_id,
            action=action,
            chat_id=query.message.chat_id,
        )
        await query.answer(reply)
        await query.message.reply_text(reply)
