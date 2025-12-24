"""
BRAiN DMZ Email Gateway (Transport-Only)

SECURITY CONSTRAINTS:
- NO business logic
- NO state storage
- NO database access
- ONLY message forwarding (Email ↔ Core API)
"""

import os
import asyncio
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from loguru import logger
import aiohttp
from aiohttp import web
import aioimaplib
import aiosmtplib


class EmailGateway:
    """
    Minimal Email gateway for BRAiN DMZ.
    Forwards messages between Email and Core API only.
    """

    def __init__(self):
        # Environment configuration
        self.imap_host = os.getenv("EMAIL_IMAP_HOST")
        self.imap_port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
        self.smtp_host = os.getenv("EMAIL_SMTP_HOST")
        self.smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self.email_address = os.getenv("EMAIL_ADDRESS")
        self.email_password = os.getenv("EMAIL_PASSWORD")

        if not all([self.imap_host, self.smtp_host, self.email_address, self.email_password]):
            raise ValueError("Email configuration incomplete (IMAP_HOST, SMTP_HOST, EMAIL_ADDRESS, EMAIL_PASSWORD required)")

        self.core_api_url = os.getenv("BRAIN_API_URL", "http://host.docker.internal:8000")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.poll_interval = int(os.getenv("EMAIL_POLL_INTERVAL", "60"))  # seconds

        # Configure logging
        logger.remove()
        logger.add(
            lambda msg: print(msg, end=""),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level=self.log_level,
        )

        # HTTP session for Core API calls
        self.session: Optional[aiohttp.ClientSession] = None

        # IMAP client
        self.imap_client: Optional[aioimaplib.IMAP4_SSL] = None

        logger.info(f"Email Gateway initialized")
        logger.info(f"IMAP: {self.imap_host}:{self.imap_port}")
        logger.info(f"SMTP: {self.smtp_host}:{self.smtp_port}")
        logger.info(f"Core API URL: {self.core_api_url}")

    async def connect_imap(self):
        """Connect to IMAP server."""
        self.imap_client = aioimaplib.IMAP4_SSL(host=self.imap_host, port=self.imap_port)
        await self.imap_client.wait_hello_from_server()
        await self.imap_client.login(self.email_address, self.email_password)
        await self.imap_client.select("INBOX")
        logger.info("Connected to IMAP server")

    async def poll_emails(self):
        """Poll for new emails."""
        while True:
            try:
                # Search for unseen messages
                _, messages = await self.imap_client.search("UNSEEN")

                if messages and messages[0]:
                    message_ids = messages[0].split()

                    for msg_id in message_ids:
                        await self.handle_email(msg_id)

            except Exception as e:
                logger.error(f"Error polling emails: {e}")

            # Wait before next poll
            await asyncio.sleep(self.poll_interval)

    async def handle_email(self, message_id: bytes):
        """
        Handle incoming email.
        Forwards to Core API WITHOUT any business logic.
        """
        try:
            # Fetch email
            _, msg_data = await self.imap_client.fetch(message_id, "(RFC822)")

            if not msg_data or not msg_data[1]:
                return

            # Parse email
            email_message = email.message_from_bytes(msg_data[1])

            sender = email_message.get("From", "unknown")
            subject = email_message.get("Subject", "")
            body = self._extract_body(email_message)

            # Sanitize: DO NOT log email content (security)
            logger.info(f"Email from {sender}")

            # Prepare payload for Core API
            payload = {
                "message": body,
                "metadata": {
                    "source": "email",
                    "from": sender,
                    "subject": subject,
                    "message_id": email_message.get("Message-ID", ""),
                },
            }

            # Forward to Core API
            async with self.session.post(
                f"{self.core_api_url}/api/axe/message",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    reply = data.get("reply", "Message processed.")

                    # Send reply email
                    await self.send_email(sender, f"Re: {subject}", reply)
                    logger.info(f"Response sent to {sender}")

                else:
                    error_text = await response.text()
                    logger.error(
                        f"Core API returned {response.status}: {error_text[:100]}"
                    )
                    await self.send_email(
                        sender,
                        f"Re: {subject}",
                        "⚠️ Gateway error. Please try again later."
                    )

            # Mark as seen
            await self.imap_client.store(message_id, "+FLAGS", "\\Seen")

        except aiohttp.ClientError as e:
            logger.error(f"Failed to reach Core API: {e}")

        except Exception as e:
            logger.error(f"Error handling email: {e}")

    def _extract_body(self, email_message) -> str:
        """Extract plain text body from email."""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode("utf-8", errors="ignore")
        else:
            return email_message.get_payload(decode=True).decode("utf-8", errors="ignore")

        return ""

    async def send_email(self, to: str, subject: str, body: str):
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.email_address,
                password=self.email_password,
                start_tls=True,
            )

            logger.info(f"Email sent to {to}")

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")

    async def setup(self):
        """Initialize HTTP session and IMAP connection."""
        # HTTP session for Core API
        self.session = aiohttp.ClientSession()

        # Connect to IMAP
        await self.connect_imap()

        logger.info("Email gateway setup complete")

    async def run(self):
        """Run email gateway."""
        logger.info("Starting email gateway...")

        # Start polling
        await self.poll_emails()

    async def health_check_handler(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "email",
            "imap_connected": self.imap_client is not None,
        })

    async def shutdown(self):
        """Cleanup on shutdown."""
        if self.session:
            await self.session.close()

        if self.imap_client:
            await self.imap_client.logout()

        logger.info("Email gateway shutdown complete")


async def main():
    """Main entry point."""
    gateway = EmailGateway()

    try:
        await gateway.setup()

        # Start health check server
        app = web.Application()
        app.router.add_get("/health", gateway.health_check_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8004)
        await site.start()

        logger.info("Health check server running on port 8004")

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
