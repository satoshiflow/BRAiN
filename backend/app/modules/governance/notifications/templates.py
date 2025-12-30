"""Notification templates for BRAiN Governance.

This module provides email and Slack templates for various governance events.
"""

from typing import Dict, Any
from jinja2 import Template
from .models import NotificationEvent, NotificationChannel


# ============================================================================
# EMAIL TEMPLATES
# ============================================================================

EMAIL_APPROVAL_REQUESTED = """
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
    .container { max-width: 600px; margin: 0 auto; }
    .header { background: #1e40af; color: white; padding: 20px; text-align: center; }
    .content { padding: 30px 20px; background: #ffffff; }
    .footer { background: #f3f4f6; padding: 15px; text-align: center; font-size: 12px; color: #6b7280; }
    .button {
      display: inline-block;
      background: #10b981;
      color: white !important;
      padding: 12px 24px;
      text-decoration: none;
      border-radius: 5px;
      margin: 15px 0;
    }
    .risk-high, .risk-critical { color: #dc2626; font-weight: bold; }
    .risk-medium { color: #f59e0b; font-weight: bold; }
    .risk-low { color: #10b981; font-weight: bold; }
    .metadata { background: #f9fafb; padding: 15px; border-left: 3px solid #1e40af; margin: 15px 0; }
    .metadata-item { margin: 8px 0; }
    .label { font-weight: bold; color: #4b5563; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🔔 BRAiN Governance Alert</h1>
    </div>
    <div class="content">
      <h2>New Approval Request</h2>
      <p>A new governance approval requires your attention.</p>

      <div class="metadata">
        <div class="metadata-item">
          <span class="label">Type:</span> {{ approval_type }}
        </div>
        <div class="metadata-item">
          <span class="label">Risk Tier:</span>
          <span class="risk-{{ risk_tier }}">{{ risk_tier | upper }}</span>
        </div>
        <div class="metadata-item">
          <span class="label">Requested By:</span> {{ requested_by }}
        </div>
        <div class="metadata-item">
          <span class="label">Description:</span> {{ description }}
        </div>
        <div class="metadata-item">
          <span class="label">Expires:</span> {{ expires_at }}
        </div>
      </div>

      {% if token_required %}
      <p><strong>⚠️ This is a high-risk approval and requires a single-use token for approval.</strong></p>
      {% endif %}

      <div style="text-align: center;">
        <a href="{{ approval_url }}" class="button">Review Approval →</a>
      </div>

      <p style="color: #6b7280; font-size: 14px; margin-top: 20px;">
        Please review this approval request promptly. If you have questions, contact your governance administrator.
      </p>
    </div>
    <div class="footer">
      <p>BRAiN Governance System | Powered by BRAiN v2.0</p>
      <p>This is an automated notification. Please do not reply to this email.</p>
    </div>
  </div>
</body>
</html>
"""

EMAIL_APPROVAL_APPROVED = """
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
    .container { max-width: 600px; margin: 0 auto; }
    .header { background: #10b981; color: white; padding: 20px; text-align: center; }
    .content { padding: 30px 20px; background: #ffffff; }
    .footer { background: #f3f4f6; padding: 15px; text-align: center; font-size: 12px; color: #6b7280; }
    .metadata { background: #f0fdf4; padding: 15px; border-left: 3px solid #10b981; margin: 15px 0; }
    .metadata-item { margin: 8px 0; }
    .label { font-weight: bold; color: #4b5563; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>✅ Approval Granted</h1>
    </div>
    <div class="content">
      <h2>Your Request Was Approved</h2>
      <p>Good news! Your governance approval request has been approved.</p>

      <div class="metadata">
        <div class="metadata-item">
          <span class="label">Approval ID:</span> {{ approval_id }}
        </div>
        <div class="metadata-item">
          <span class="label">Type:</span> {{ approval_type }}
        </div>
        <div class="metadata-item">
          <span class="label">Approved By:</span> {{ approved_by }}
        </div>
        <div class="metadata-item">
          <span class="label">Approved At:</span> {{ approved_at }}
        </div>
        {% if notes %}
        <div class="metadata-item">
          <span class="label">Notes:</span> {{ notes }}
        </div>
        {% endif %}
      </div>

      <p>You can now proceed with the approved action.</p>
    </div>
    <div class="footer">
      <p>BRAiN Governance System | Powered by BRAiN v2.0</p>
    </div>
  </div>
</body>
</html>
"""

EMAIL_APPROVAL_REJECTED = """
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
    .container { max-width: 600px; margin: 0 auto; }
    .header { background: #dc2626; color: white; padding: 20px; text-align: center; }
    .content { padding: 30px 20px; background: #ffffff; }
    .footer { background: #f3f4f6; padding: 15px; text-align: center; font-size: 12px; color: #6b7280; }
    .metadata { background: #fef2f2; padding: 15px; border-left: 3px solid #dc2626; margin: 15px 0; }
    .metadata-item { margin: 8px 0; }
    .label { font-weight: bold; color: #4b5563; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>❌ Approval Rejected</h1>
    </div>
    <div class="content">
      <h2>Your Request Was Rejected</h2>
      <p>Your governance approval request has been rejected.</p>

      <div class="metadata">
        <div class="metadata-item">
          <span class="label">Approval ID:</span> {{ approval_id }}
        </div>
        <div class="metadata-item">
          <span class="label">Type:</span> {{ approval_type }}
        </div>
        <div class="metadata-item">
          <span class="label">Rejected By:</span> {{ rejected_by }}
        </div>
        <div class="metadata-item">
          <span class="label">Rejected At:</span> {{ rejected_at }}
        </div>
        <div class="metadata-item">
          <span class="label">Reason:</span> {{ rejection_reason }}
        </div>
      </div>

      <p>Please review the rejection reason and take appropriate action. You may submit a new request if needed.</p>
    </div>
    <div class="footer">
      <p>BRAiN Governance System | Powered by BRAiN v2.0</p>
    </div>
  </div>
</body>
</html>
"""

EMAIL_APPROVAL_EXPIRING = """
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
    .container { max-width: 600px; margin: 0 auto; }
    .header { background: #f59e0b; color: white; padding: 20px; text-align: center; }
    .content { padding: 30px 20px; background: #ffffff; }
    .footer { background: #f3f4f6; padding: 15px; text-align: center; font-size: 12px; color: #6b7280; }
    .button {
      display: inline-block;
      background: #f59e0b;
      color: white !important;
      padding: 12px 24px;
      text-decoration: none;
      border-radius: 5px;
      margin: 15px 0;
    }
    .metadata { background: #fffbeb; padding: 15px; border-left: 3px solid #f59e0b; margin: 15px 0; }
    .metadata-item { margin: 8px 0; }
    .label { font-weight: bold; color: #4b5563; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>⏰ Approval Expiring Soon</h1>
    </div>
    <div class="content">
      <h2>Urgent: Approval Expires in 24 Hours</h2>
      <p><strong>This approval request will expire soon!</strong> Please review and take action.</p>

      <div class="metadata">
        <div class="metadata-item">
          <span class="label">Type:</span> {{ approval_type }}
        </div>
        <div class="metadata-item">
          <span class="label">Requested By:</span> {{ requested_by }}
        </div>
        <div class="metadata-item">
          <span class="label">Expires At:</span> {{ expires_at }}
        </div>
        <div class="metadata-item">
          <span class="label">Time Remaining:</span> {{ time_remaining }}
        </div>
      </div>

      <div style="text-align: center;">
        <a href="{{ approval_url }}" class="button">Review Now →</a>
      </div>

      <p style="color: #dc2626; font-weight: bold; margin-top: 20px;">
        ⚠️ If not reviewed before expiry, this request will be automatically rejected.
      </p>
    </div>
    <div class="footer">
      <p>BRAiN Governance System | Powered by BRAiN v2.0</p>
    </div>
  </div>
</body>
</html>
"""


# ============================================================================
# SLACK TEMPLATES
# ============================================================================

def get_slack_approval_requested(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Slack message for approval requested."""
    risk_emoji = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🔴",
        "critical": "🔴🔴",
    }

    return {
        "text": f"🔔 New Governance Approval Required ({data['risk_tier'].upper()})",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{risk_emoji.get(data['risk_tier'], '🔵')} New Governance Approval Required",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:*\n{data['approval_type']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Risk Tier:*\n{risk_emoji.get(data['risk_tier'], '🔵')} {data['risk_tier'].upper()}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Requested By:*\n{data['requested_by']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Expires:*\n{data['expires_at']}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{data['description']}",
                },
            },
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Review Approval"},
                        "url": data.get("approval_url", "#"),
                        "style": "primary",
                    }
                ],
            },
        ],
    }


def get_slack_approval_approved(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Slack message for approval approved."""
    return {
        "text": "✅ Approval Granted",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "✅ Approval Granted"},
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Approval ID:*\n{data['approval_id']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:*\n{data['approval_type']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Approved By:*\n{data['approved_by']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Approved At:*\n{data['approved_at']}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "✓ Your request has been approved. You can now proceed with the action.",
                },
            },
        ],
    }


def get_slack_approval_rejected(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Slack message for approval rejected."""
    return {
        "text": "❌ Approval Rejected",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "❌ Approval Rejected"},
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Approval ID:*\n{data['approval_id']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:*\n{data['approval_type']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Rejected By:*\n{data['rejected_by']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Rejected At:*\n{data['rejected_at']}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Reason:*\n{data['rejection_reason']}",
                },
            },
        ],
    }


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

EMAIL_TEMPLATES = {
    NotificationEvent.APPROVAL_REQUESTED: EMAIL_APPROVAL_REQUESTED,
    NotificationEvent.APPROVAL_APPROVED: EMAIL_APPROVAL_APPROVED,
    NotificationEvent.APPROVAL_REJECTED: EMAIL_APPROVAL_REJECTED,
    NotificationEvent.APPROVAL_EXPIRING: EMAIL_APPROVAL_EXPIRING,
    NotificationEvent.HIGH_RISK_APPROVAL: EMAIL_APPROVAL_REQUESTED,  # Same as requested
    NotificationEvent.APPROVAL_EXPIRED: EMAIL_APPROVAL_EXPIRING,  # Similar to expiring
}

SLACK_TEMPLATES = {
    NotificationEvent.APPROVAL_REQUESTED: get_slack_approval_requested,
    NotificationEvent.APPROVAL_APPROVED: get_slack_approval_approved,
    NotificationEvent.APPROVAL_REJECTED: get_slack_approval_rejected,
    NotificationEvent.APPROVAL_EXPIRING: get_slack_approval_requested,  # Similar
    NotificationEvent.HIGH_RISK_APPROVAL: get_slack_approval_requested,
    NotificationEvent.APPROVAL_EXPIRED: get_slack_approval_rejected,  # Similar
}


def render_email_template(event: NotificationEvent, data: Dict[str, Any]) -> str:
    """Render email template for event with data."""
    template_str = EMAIL_TEMPLATES.get(event)
    if not template_str:
        raise ValueError(f"No email template for event: {event}")

    template = Template(template_str)
    return template.render(**data)


def render_slack_template(event: NotificationEvent, data: Dict[str, Any]) -> Dict[str, Any]:
    """Render Slack template for event with data."""
    template_func = SLACK_TEMPLATES.get(event)
    if not template_func:
        raise ValueError(f"No Slack template for event: {event}")

    return template_func(data)
