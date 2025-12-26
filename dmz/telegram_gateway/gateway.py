"""
BRAiN DMZ Telegram Gateway (Transport-Only)

SECURITY CONSTRAINTS:
- NO business logic
- NO state storage
- NO database access
- ONLY message forwarding (Telegram ↔ Core API)
"""

import os
import asyncio
from typing import Optional
from loguru import logger
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import aiohttp
from aiohttp import web


class TelegramGateway:
    """
    Minimal Telegram gateway for BRAiN DMZ.
    Forwards messages between Telegram and Core API only.
    """

    def __init__(self):
        # Environment configuration
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable required")

        self.core_api_url = os.getenv("BRAIN_API_URL", "http://host.docker.internal:8000")
        self.mode = os.getenv("TELEGRAM_MODE", "polling")  # polling or webhook
        self.webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Configure logging
        logger.remove()
        logger.add(
            lambda msg: print(msg, end=""),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level=self.log_level,
        )

        # Telegram application
        self.app: Optional[Application] = None

        # HTTP session for Core API calls
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info(f"Telegram Gateway initialized (mode: {self.mode})")
        logger.info(f"Core API URL: {self.core_api_url}")

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command."""
        user = update.effective_user
        logger.info(f"User {user.id} started conversation")

        # NO business logic - just acknowledge
        await update.message.reply_text(
            "✅ Connected to BRAiN Gateway\n\n"
            "Messages are forwarded to the core system."
        )

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle incoming Telegram message.
        Forwards to Core API WITHOUT any business logic.
        """
        message = update.message
        user = update.effective_user

        # Sanitize: DO NOT log message content (security)
        logger.info(f"Message from user {user.id}")

        # Prepare payload for Core API
        payload = {
            "message": message.text,
            "metadata": {
                "source": "telegram",
                "user_id": str(user.id),
                "username": user.username or "unknown",
                "chat_id": str(message.chat_id),
                "message_id": message.message_id,
            },
        }

        try:
            # Forward to Core API (e.g., /api/axe/message)
            async with self.session.post(
                f"{self.core_api_url}/api/axe/message",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    reply = data.get("reply", "Message processed.")

                    # Send reply back to Telegram
                    await message.reply_text(reply)
                    logger.info(f"Response sent to user {user.id}")

                else:
                    error_text = await response.text()
                    logger.error(
                        f"Core API returned {response.status}: {error_text[:100]}"
                    )
                    await message.reply_text(
                        "⚠️ Gateway error. Please try again later."
                    )

        except aiohttp.ClientError as e:
            logger.error(f"Failed to reach Core API: {e}")
            await message.reply_text("❌ Core system unreachable.")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await message.reply_text("❌ Internal gateway error.")

    async def setup(self):
        """Initialize Telegram bot and HTTP session."""
        # HTTP session for Core API
        self.session = aiohttp.ClientSession()

        # Telegram bot application
        self.app = Application.builder().token(self.bot_token).build()

        # Register handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        logger.info("Telegram gateway setup complete")

    async def run_polling(self):
        """Run bot in polling mode (recommended for development)."""
        logger.info("Starting Telegram bot in POLLING mode...")

        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)

        logger.info("Telegram bot is running (polling)")

        # Keep running
        await asyncio.Event().wait()

    async def run_webhook(self):
        """Run bot in webhook mode (recommended for production)."""
        if not self.webhook_url:
            raise ValueError("TELEGRAM_WEBHOOK_URL required for webhook mode")

        logger.info(f"Starting Telegram bot in WEBHOOK mode: {self.webhook_url}")

        await self.app.initialize()
        await self.app.start()
        await self.app.bot.set_webhook(url=self.webhook_url)

        # Start webhook server
        web_app = web.Application()
        web_app.router.add_post("/webhook", self.webhook_handler)
        web_app.router.add_get("/health", self.health_check)

        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8001)
        await site.start()

        logger.info("Webhook server running on port 8001")

        # Keep running
        await asyncio.Event().wait()

    async def webhook_handler(self, request: web.Request) -> web.Response:
        """Handle incoming webhook from Telegram."""
        try:
            data = await request.json()
            update = Update.de_json(data, self.app.bot)
            await self.app.process_update(update)
            return web.Response(status=200)

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return web.Response(status=500)

    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "healthy", "mode": self.mode})

    async def shutdown(self):
        """Cleanup on shutdown."""
        if self.session:
            await self.session.close()

        if self.app:
            await self.app.stop()
            await self.app.shutdown()

        logger.info("Telegram gateway shutdown complete")


async def main():
    """Main entry point."""
    gateway = TelegramGateway()

    try:
        await gateway.setup()

        if gateway.mode == "webhook":
            await gateway.run_webhook()
        else:
            await gateway.run_polling()

    except KeyboardInterrupt:
        logger.info("Shutdown signal received")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

    finally:
        await gateway.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
