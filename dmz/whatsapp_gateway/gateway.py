"""
BRAiN DMZ WhatsApp Gateway (Transport-Only)

SECURITY CONSTRAINTS:
- NO business logic
- NO state storage
- NO database access
- ONLY message forwarding (WhatsApp ↔ Core API)
"""

import os
import asyncio
from typing import Optional
from loguru import logger
import aiohttp
from aiohttp import web
from whatsapp import WhatsApp


class WhatsAppGateway:
    """
    Minimal WhatsApp gateway for BRAiN DMZ.
    Forwards messages between WhatsApp and Core API only.
    """

    def __init__(self):
        # Environment configuration
        self.phone_number = os.getenv("WHATSAPP_PHONE_NUMBER")
        if not self.phone_number:
            raise ValueError("WHATSAPP_PHONE_NUMBER environment variable required")

        self.core_api_url = os.getenv("BRAIN_API_URL", "http://host.docker.internal:8000")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Configure logging
        logger.remove()
        logger.add(
            lambda msg: print(msg, end=""),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level=self.log_level,
        )

        # WhatsApp client
        self.client: Optional[WhatsApp] = None

        # HTTP session for Core API calls
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info(f"WhatsApp Gateway initialized")
        logger.info(f"Core API URL: {self.core_api_url}")

    async def handle_message(self, message: dict) -> None:
        """
        Handle incoming WhatsApp message.
        Forwards to Core API WITHOUT any business logic.
        """
        # Extract message data
        sender = message.get("from", "unknown")
        text = message.get("body", "")
        message_id = message.get("id", "")

        # Sanitize: DO NOT log message content (security)
        logger.info(f"Message from {sender}")

        # Prepare payload for Core API
        payload = {
            "message": text,
            "metadata": {
                "source": "whatsapp",
                "user_id": sender,
                "message_id": message_id,
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

                    # Send reply back to WhatsApp
                    await self.send_message(sender, reply)
                    logger.info(f"Response sent to {sender}")

                else:
                    error_text = await response.text()
                    logger.error(
                        f"Core API returned {response.status}: {error_text[:100]}"
                    )
                    await self.send_message(
                        sender, "⚠️ Gateway error. Please try again later."
                    )

        except aiohttp.ClientError as e:
            logger.error(f"Failed to reach Core API: {e}")
            await self.send_message(sender, "❌ Core system unreachable.")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await self.send_message(sender, "❌ Internal gateway error.")

    async def send_message(self, recipient: str, text: str) -> None:
        """Send message via WhatsApp."""
        try:
            await self.client.send_message(recipient, text)
        except Exception as e:
            logger.error(f"Failed to send message to {recipient}: {e}")

    async def setup(self):
        """Initialize WhatsApp client and HTTP session."""
        # HTTP session for Core API
        self.session = aiohttp.ClientSession()

        # WhatsApp client
        self.client = WhatsApp(
            phone_number=self.phone_number,
            on_message=self.handle_message,
        )

        logger.info("WhatsApp gateway setup complete")

    async def run(self):
        """Run WhatsApp gateway."""
        logger.info("Starting WhatsApp gateway...")

        await self.client.start()

        logger.info("WhatsApp gateway is running")

        # Keep running
        await asyncio.Event().wait()

    async def health_check_handler(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "healthy", "service": "whatsapp"})

    async def shutdown(self):
        """Cleanup on shutdown."""
        if self.session:
            await self.session.close()

        if self.client:
            await self.client.stop()

        logger.info("WhatsApp gateway shutdown complete")


async def main():
    """Main entry point."""
    gateway = WhatsAppGateway()

    try:
        await gateway.setup()

        # Start health check server
        app = web.Application()
        app.router.add_get("/health", gateway.health_check_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8002)
        await site.start()

        logger.info("Health check server running on port 8002")

        # Start gateway
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
