"""Notification channels for BRAiN Governance."""

from .base import BaseNotificationChannel
from .email import EmailChannel
from .webhook import WebhookChannel
from .slack import SlackChannel
from .discord import DiscordChannel

__all__ = [
    "BaseNotificationChannel",
    "EmailChannel",
    "WebhookChannel",
    "SlackChannel",
    "DiscordChannel",
]
