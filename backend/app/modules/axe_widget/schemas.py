"""
AXE Widget Pydantic Schemas

Request/Response models for AXE Widget API endpoints with validation.

Security Notes:
- All text fields have max_length to prevent DoS
- Session IDs validated for format
- Project IDs restricted to alphanumeric and hyphens (no path traversal)
- Messages sanitized to reject script tags
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


# ============================================================================
# Request Schemas
# ============================================================================

class WidgetSessionCreate(BaseModel):
    """
    Request schema for creating a new widget session.

    Attributes:
        project_id: Website project identifier (must be alphanumeric + hyphens)
        position: Widget position on page (bottom-right, top-left, etc.)
        theme: Color theme (dark or light)
        metadata: Optional custom metadata (max 5 keys)
    """
    project_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        regex="^[a-zA-Z0-9_-]+$",
        description="Website project ID (alphanumeric, underscore, hyphen only)"
    )
    position: str = Field(
        default="bottom-right",
        regex="^(bottom|top)-(left|right)$",
        description="Widget position on page"
    )
    theme: str = Field(
        default="dark",
        regex="^(dark|light)$",
        description="Color theme"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Custom metadata (max 5 keys)",
        max_items=5
    )

    @validator('metadata')
    def validate_metadata(cls, v):
        """Limit metadata to 5 keys to prevent payload bloat"""
        if len(v) > 5:
            raise ValueError("Metadata must have at most 5 keys")
        return v


class WidgetMessageRequest(BaseModel):
    """
    Request schema for sending a message in a widget session.

    Security:
    - Messages checked for script tags (XSS protection)
    - Max 10000 characters to prevent DoS
    - Session ID validated

    Attributes:
        session_id: Widget session ID
        message: User message content
        context: Optional context (page URL, metadata, etc.)
    """
    session_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="Widget session ID (UUID string)"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User message"
    )
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context"
    )

    @validator('message')
    def validate_message(cls, v):
        """Prevent XSS attacks by rejecting script tags"""
        if '<script' in v.lower() or '<?php' in v.lower() or '<iframe' in v.lower():
            raise ValueError("Message contains invalid content")
        return v.strip()

    @validator('context')
    def validate_context(cls, v):
        """Limit context to 10 keys"""
        if len(v) > 10:
            raise ValueError("Context must have at most 10 keys")
        return v


class WidgetCredentialCreate(BaseModel):
    """
    Request schema for creating widget credentials.

    Only admin users can create credentials.
    API key and secret are generated server-side.

    Attributes:
        project_id: Website project identifier
        rate_limit: Max requests per minute (default 30, max 100)
        scopes: List of allowed scopes
        expires_at: Optional expiration date
    """
    project_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        regex="^[a-zA-Z0-9_-]+$",
        description="Website project ID"
    )
    rate_limit: int = Field(
        default=30,
        ge=1,
        le=100,
        description="Max requests per minute"
    )
    scopes: Optional[List[str]] = Field(
        default_factory=list,
        description="Allowed scopes"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Custom metadata"
    )


# ============================================================================
# Response Schemas
# ============================================================================

class WidgetSessionResponse(BaseModel):
    """
    Response schema for widget sessions.

    Returned from POST /sessions, GET /sessions/{id}, etc.

    Attributes:
        session_id: Unique session identifier
        project_id: Website project ID
        created_at: Creation timestamp
        expires_at: Expiration timestamp
        message_count: Number of messages in session
        status: Session status
    """
    session_id: str
    project_id: str
    created_at: datetime
    expires_at: datetime
    message_count: int
    status: str

    class Config:
        from_attributes = True


class WidgetMessageResponse(BaseModel):
    """
    Response schema for widget messages.

    Returned from message endpoints and history.

    Attributes:
        id: Message UUID
        role: Message role (user or assistant)
        content: Message content
        created_at: Creation timestamp
    """
    id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class WidgetMessageHistoryResponse(BaseModel):
    """
    Response schema for message history.

    Attributes:
        session_id: Session ID
        messages: List of messages in session
        total: Total message count
    """
    session_id: str
    messages: List[WidgetMessageResponse]
    total: int


class WidgetCredentialResponse(BaseModel):
    """
    Response schema for widget credentials.

    Note: Secret is never returned in responses.
    API key is only shown once during creation.

    Attributes:
        id: Credential ID
        project_id: Website project ID
        is_active: Whether credential is active
        rate_limit: Max requests per minute
        created_at: Creation timestamp
        last_used_at: Last usage timestamp
        scopes: Allowed scopes
    """
    id: UUID
    project_id: str
    is_active: bool
    rate_limit: int
    created_at: datetime
    last_used_at: Optional[datetime]
    scopes: Optional[List[str]]

    class Config:
        from_attributes = True


class WidgetCredentialWithKeyResponse(WidgetCredentialResponse):
    """
    Response schema for credential creation (includes API key once).

    Only returned immediately after credential creation.

    Attributes:
        api_key: Plain text API key (shown only once)
        secret: Plain text secret (shown only once)
    """
    api_key: str
    secret: str


class WidgetSessionListResponse(BaseModel):
    """
    Response schema for listing sessions.

    Attributes:
        sessions: List of session responses
        total: Total count of sessions
    """
    sessions: List[WidgetSessionResponse]
    total: int


# ============================================================================
# Error Response Schemas
# ============================================================================

class WidgetErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
