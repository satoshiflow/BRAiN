"""
AXE Floating Widget

A floating chat widget that can be embedded in any web project.
Provides support and assistant functionality with security.

Features:
- Embedded chat widget for websites
- Session-based conversation management
- API key authentication
- Rate limiting and credential management
- Audit logging

Security:
- X-API-Key authentication for session creation
- X-Session-Token validation for message access
- Rate limiting per project
- Admin-only credential management
- Message content validation (XSS protection)
"""

from .schemas import (
    WidgetSessionCreate,
    WidgetSessionResponse,
    WidgetMessageRequest,
    WidgetMessageResponse,
    WidgetMessageHistoryResponse,
    WidgetCredentialCreate,
    WidgetCredentialResponse,
    WidgetCredentialWithKeyResponse,
    WidgetSessionListResponse,
    WidgetErrorResponse,
)
from .service import WidgetService
from .router import router

__all__ = [
    "WidgetSessionCreate",
    "WidgetSessionResponse",
    "WidgetMessageRequest",
    "WidgetMessageResponse",
    "WidgetMessageHistoryResponse",
    "WidgetCredentialCreate",
    "WidgetCredentialResponse",
    "WidgetCredentialWithKeyResponse",
    "WidgetSessionListResponse",
    "WidgetErrorResponse",
    "WidgetService",
    "router",
]
