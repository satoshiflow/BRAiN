"""Notification system data models for BRAiN Governance.

This module defines all data models for the notification system including
notification channels, events, preferences, and notification records.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time


class NotificationChannel(str, Enum):
    """Supported notification channels."""

    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"


class NotificationEvent(str, Enum):
    """Events that trigger notifications."""

    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_EXPIRING = "approval_expiring"  # 24h before expiry
    APPROVAL_EXPIRED = "approval_expired"
    HIGH_RISK_APPROVAL = "high_risk_approval"  # Immediate alert for high/critical


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationPreference(BaseModel):
    """User notification preferences."""

    user_id: str = Field(..., description="User identifier")
    email: Optional[str] = Field(None, description="Email address for notifications")
    channels: List[NotificationChannel] = Field(
        default_factory=list, description="Enabled notification channels"
    )
    events: List[NotificationEvent] = Field(
        default_factory=list, description="Events to receive notifications for"
    )
    enabled: bool = Field(True, description="Whether notifications are enabled")
    quiet_hours_start: Optional[int] = Field(
        None, description="Quiet hours start (0-23)", ge=0, le=23
    )
    quiet_hours_end: Optional[int] = Field(
        None, description="Quiet hours end (0-23)", ge=0, le=23
    )
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "admin",
                "email": "admin@brain.ai",
                "channels": ["email", "slack"],
                "events": [
                    "approval_requested",
                    "high_risk_approval",
                    "approval_expiring",
                ],
                "enabled": True,
                "quiet_hours_start": 22,
                "quiet_hours_end": 8,
            }
        }


class Notification(BaseModel):
    """A notification record."""

    notification_id: str = Field(..., description="Unique notification ID")
    event: NotificationEvent = Field(..., description="Event that triggered notification")
    approval_id: str = Field(..., description="Related approval ID")
    recipients: List[str] = Field(..., description="List of recipient user IDs")
    channels: List[NotificationChannel] = Field(
        ..., description="Channels to send notification through"
    )
    priority: NotificationPriority = Field(
        NotificationPriority.NORMAL, description="Notification priority"
    )
    subject: str = Field(..., description="Notification subject/title")
    message: str = Field(..., description="Notification message body")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    # Delivery tracking
    created_at: float = Field(default_factory=time.time)
    sent_at: Optional[float] = Field(None, description="When notification was sent")
    delivered: bool = Field(False, description="Whether notification was delivered")
    delivery_attempts: int = Field(0, description="Number of delivery attempts")
    max_retries: int = Field(3, description="Maximum delivery retries")
    retry_count: int = Field(0, description="Current retry count")
    last_error: Optional[str] = Field(None, description="Last delivery error")
    delivered_channels: List[NotificationChannel] = Field(
        default_factory=list, description="Channels that successfully delivered"
    )
    failed_channels: List[NotificationChannel] = Field(
        default_factory=list, description="Channels that failed to deliver"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "notification_id": "notif_abc123",
                "event": "approval_requested",
                "approval_id": "approval_xyz789",
                "recipients": ["admin", "approver_1"],
                "channels": ["email", "slack"],
                "priority": "high",
                "subject": "New High-Risk Approval Required",
                "message": "A new IR escalation approval requires your attention.",
                "delivered": True,
                "delivered_channels": ["email", "slack"],
            }
        }


class NotificationTemplate(BaseModel):
    """Notification template for an event type."""

    template_id: str = Field(..., description="Template identifier")
    event: NotificationEvent = Field(..., description="Event this template is for")
    channel: NotificationChannel = Field(..., description="Channel this template is for")
    subject_template: str = Field(..., description="Subject/title template")
    body_template: str = Field(..., description="Body template (supports Jinja2)")
    enabled: bool = Field(True, description="Whether template is enabled")

    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "email_approval_requested",
                "event": "approval_requested",
                "channel": "email",
                "subject_template": "🔔 New {{ risk_tier }} Risk Approval Required",
                "body_template": "A new {{ approval_type }} approval requires your attention...",
                "enabled": True,
            }
        }


class NotificationStats(BaseModel):
    """Notification system statistics."""

    total_sent: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    by_channel: Dict[str, int] = Field(default_factory=dict)
    by_event: Dict[str, int] = Field(default_factory=dict)
    average_delivery_time: float = 0.0  # seconds

    class Config:
        json_schema_extra = {
            "example": {
                "total_sent": 150,
                "total_delivered": 145,
                "total_failed": 5,
                "by_channel": {"email": 80, "slack": 65, "webhook": 5},
                "by_event": {
                    "approval_requested": 60,
                    "approval_approved": 45,
                    "high_risk_approval": 25,
                },
                "average_delivery_time": 2.3,
            }
        }


# Request/Response models for API

class NotificationPreferenceCreate(BaseModel):
    """Request to create notification preferences."""

    user_id: str
    email: Optional[str] = None
    channels: List[NotificationChannel] = Field(default_factory=lambda: [NotificationChannel.EMAIL])
    events: List[NotificationEvent] = Field(
        default_factory=lambda: [
            NotificationEvent.APPROVAL_REQUESTED,
            NotificationEvent.HIGH_RISK_APPROVAL,
        ]
    )
    enabled: bool = True
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None


class NotificationPreferenceUpdate(BaseModel):
    """Request to update notification preferences."""

    email: Optional[str] = None
    channels: Optional[List[NotificationChannel]] = None
    events: Optional[List[NotificationEvent]] = None
    enabled: Optional[bool] = None
    quiet_hours_start: Optional[int] = Field(None, ge=0, le=23)
    quiet_hours_end: Optional[int] = Field(None, ge=0, le=23)


class SendTestNotificationRequest(BaseModel):
    """Request to send a test notification."""

    recipient: str = Field(..., description="Recipient user ID or email")
    channel: NotificationChannel = Field(..., description="Channel to test")
    message: Optional[str] = Field(None, description="Custom test message")


class SendTestNotificationResponse(BaseModel):
    """Response from sending test notification."""

    success: bool
    notification_id: str
    channel: NotificationChannel
    delivered: bool
    error: Optional[str] = None
    message: str


class NotificationStatsResponse(BaseModel):
    """Response with notification statistics."""

    stats: NotificationStats
    last_updated: float = Field(default_factory=time.time)
