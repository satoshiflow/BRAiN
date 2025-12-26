"""
BRAiN DMZ Discord Gateway (Transport-Only)

SECURITY CONSTRAINTS:
- NO business logic
- NO state storage
- NO database access
- ONLY message forwarding (Discord ↔ Core API)
"""

import os
import asyncio
from typing import Optional
from loguru import logger
import discord
from discord.ext import commands
import aiohttp
from aiohttp import web


class DiscordGateway:
    """
    Minimal Discord gateway for BRAiN DMZ.
    Forwards messages between Discord and Core API only.
    """

    def __init__(self):
        # Environment configuration
        self.bot_token = os.getenv("DISCORD_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable required")

        self.core_api_url = os.getenv("BRAIN_API_URL", "http://host.docker.internal:8000")
        self.command_prefix = os.getenv("DISCORD_COMMAND_PREFIX", "!")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Configure logging
        logger.remove()
        logger.add(
            lambda msg: print(msg, end=""),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level=self.log_level,
        )

        # Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix=self.command_prefix, intents=intents)

        # HTTP session for Core API calls
        self.session: Optional[aiohttp.ClientSession] = None

        # Register event handlers
        self.bot.event(self.on_ready)
        self.bot.event(self.on_message)

        logger.info(f"Discord Gateway initialized")
        logger.info(f"Core API URL: {self.core_api_url}")

    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(f"Discord bot logged in as {self.bot.user}")

    async def on_message(self, message: discord.Message):
        """
        Handle incoming Discord message.
        Forwards to Core API WITHOUT any business logic.
        """
        # Ignore bot's own messages
        if message.author == self.bot.user:
            return

        # Ignore messages that don't start with command prefix
        if not message.content.startswith(self.command_prefix):
            return

        # Extract command (remove prefix)
        content = message.content[len(self.command_prefix):].strip()

        # Sanitize: DO NOT log message content (security)
        logger.info(f"Message from user {message.author.id} in channel {message.channel.id}")

        # Prepare payload for Core API
        payload = {
            "message": content,
            "metadata": {
                "source": "discord",
                "user_id": str(message.author.id),
                "username": str(message.author.name),
                "channel_id": str(message.channel.id),
                "message_id": str(message.id),
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

                    # Send reply back to Discord
                    await message.channel.send(reply)
                    logger.info(f"Response sent to channel {message.channel.id}")

                else:
                    error_text = await response.text()
                    logger.error(
                        f"Core API returned {response.status}: {error_text[:100]}"
                    )
                    await message.channel.send(
                        "⚠️ Gateway error. Please try again later."
                    )

        except aiohttp.ClientError as e:
            logger.error(f"Failed to reach Core API: {e}")
            await message.channel.send("❌ Core system unreachable.")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await message.channel.send("❌ Internal gateway error.")

    async def setup(self):
        """Initialize HTTP session."""
        # HTTP session for Core API
        self.session = aiohttp.ClientSession()

        logger.info("Discord gateway setup complete")

    async def run(self):
        """Run Discord bot."""
        logger.info("Starting Discord bot...")

        await self.bot.start(self.bot_token)

    async def health_check_handler(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "discord",
            "bot_user": str(self.bot.user) if self.bot.user else None,
        })

    async def shutdown(self):
        """Cleanup on shutdown."""
        if self.session:
            await self.session.close()

        if self.bot:
            await self.bot.close()

        logger.info("Discord gateway shutdown complete")


async def main():
    """Main entry point."""
    gateway = DiscordGateway()

    try:
        await gateway.setup()

        # Start health check server
        app = web.Application()
        app.router.add_get("/health", gateway.health_check_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8003)
        await site.start()

        logger.info("Health check server running on port 8003")

        # Start bot
        await gateway.run()

    except KeyboardInterrupt:
        logger.info("Shutdown signal received")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

    finally:
        await gateway.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
