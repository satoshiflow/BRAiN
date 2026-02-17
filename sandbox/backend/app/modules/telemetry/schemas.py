"""
AXE Event Telemetry Schemas

Pydantic models for AXE widget event validation and serialization.
"""
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid


class AxeEventType(str, Enum):
    """
    AXE event types for telemetry tracking.

    Covers user interactions, system events, and error tracking.
    """
    MESSAGE = "axe_message"
    FEEDBACK = "axe_feedback"
    CLICK = "axe_click"
    CONTEXT_SNAPSHOT = "axe_context_snapshot"
    ERROR = "axe_error"
    FILE_OPEN = "axe_file_open"
    FILE_SAVE = "axe_file_save"
    DIFF_APPLIED = "axe_diff_applied"
    DIFF_REJECTED = "axe_diff_rejected"
    SESSION_START = "axe_session_start"
    SESSION_END = "axe_session_end"


class AnonymizationLevel(str, Enum):
    """
    Privacy levels for event data anonymization (DSGVO-compliant).

    - NONE: Full data collection (requires explicit consent)
    - PSEUDONYMIZED: Hash user IDs, remove IP addresses (default)
    - STRICT: Remove all PII, only aggregate data
    """
    NONE = "none"
    PSEUDONYMIZED = "pseudonymized"
    STRICT = "strict"


class AxeEventCreate(BaseModel):
    """
    Schema for creating a new AXE event (from frontend).

    **Usage:**
    ```typescript
    const event: AxeEventCreate = {
      event_type: "axe_message",
      session_id: "session-abc123",
      app_id: "widget-test",
      event_data: {
        message: "Hello AXE",
        role: "user"
      },
      client_timestamp: new Date().toISOString()
    };
    ```
    """
    event_type: AxeEventType
    session_id: str = Field(..., min_length=1, max_length=255)
    app_id: str = Field(..., min_length=1, max_length=255)
    user_id: Optional[str] = Field(None, max_length=255)
    anonymization_level: AnonymizationLevel = AnonymizationLevel.PSEUDONYMIZED
    event_data: Dict[str, Any] = Field(default_factory=dict)
    client_timestamp: Optional[datetime] = None
    is_training_data: bool = False
    client_version: Optional[str] = Field(None, max_length=50)
    client_platform: Optional[str] = Field(None, max_length=50)

    @validator('event_data')
    def validate_event_data(cls, v, values):
        """Validate event_data based on event_type."""
        event_type = values.get('event_type')

        # Validation rules per event type
        if event_type == AxeEventType.MESSAGE:
            if 'message' not in v:
                raise ValueError("axe_message requires 'message' field in event_data")
            if 'role' not in v:
                raise ValueError("axe_message requires 'role' field in event_data")

        elif event_type == AxeEventType.ERROR:
            if 'error' not in v and 'message' not in v:
                raise ValueError("axe_error requires 'error' or 'message' field")

        elif event_type == AxeEventType.DIFF_APPLIED or event_type == AxeEventType.DIFF_REJECTED:
            if 'diff_id' not in v:
                raise ValueError(f"{event_type} requires 'diff_id' field")

        elif event_type == AxeEventType.CLICK:
            if 'element' not in v:
                raise ValueError("axe_click requires 'element' field")

        return v

    class Config:
        use_enum_values = True


class AxeEventBatchCreate(BaseModel):
    """
    Batch upload of multiple AXE events.

    **Usage:**
    Frontend batches events every 30 seconds to reduce HTTP requests.
    ```typescript
    const batch: AxeEventBatchCreate = {
      events: [event1, event2, event3]
    };
    ```
    """
    events: list[AxeEventCreate] = Field(..., min_items=1, max_items=100)

    @validator('events')
    def validate_batch_size(cls, v):
        """Ensure batch doesn't exceed 100 events."""
        if len(v) > 100:
            raise ValueError("Batch size limited to 100 events per request")
        return v


class AxeEventResponse(BaseModel):
    """
    Response schema for stored AXE events.

    **Usage:**
    Returned by GET /api/axe/events endpoints for analytics.
    """
    id: str
    event_type: AxeEventType
    session_id: str
    app_id: str
    user_id: Optional[str]
    anonymization_level: AnonymizationLevel
    event_data: Dict[str, Any]
    client_timestamp: Optional[datetime]
    created_at: datetime
    retention_days: int
    is_training_data: bool
    client_version: Optional[str]
    client_platform: Optional[str]

    class Config:
        from_attributes = True
        use_enum_values = True


class AxeEventStats(BaseModel):
    """
    Statistics for AXE events.

    **Usage:**
    GET /api/axe/events/stats?session_id=xxx
    """
    total_events: int
    event_type_counts: Dict[str, int]
    sessions: int
    apps: list[str]
    date_range: Dict[str, Optional[datetime]]
    anonymization_breakdown: Dict[str, int]


class AxeEventQuery(BaseModel):
    """
    Query parameters for filtering AXE events.

    **Usage:**
    ```python
    query = AxeEventQuery(
        session_id="session-abc123",
        event_types=["axe_message", "axe_click"],
        limit=50
    )
    ```
    """
    session_id: Optional[str] = None
    app_id: Optional[str] = None
    user_id: Optional[str] = None
    event_types: Optional[list[AxeEventType]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_training_data: Optional[bool] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

    class Config:
        use_enum_values = True


class PrivacySettings(BaseModel):
    """
    User privacy settings for AXE telemetry.

    **Usage:**
    Stored per app_id or per user_id.
    ```python
    settings = PrivacySettings(
        anonymization_level=AnonymizationLevel.STRICT,
        telemetry_enabled=False,
        training_opt_in=False
    )
    ```
    """
    anonymization_level: AnonymizationLevel = AnonymizationLevel.PSEUDONYMIZED
    telemetry_enabled: bool = True
    training_opt_in: bool = False
    retention_days: int = Field(default=90, ge=7, le=730)  # 7 days to 2 years

    class Config:
        use_enum_values = True


class AnonymizationResult(BaseModel):
    """
    Result of anonymization process.

    **Usage:**
    Internal, for logging and auditing anonymization actions.
    """
    original_user_id: Optional[str]
    anonymized_user_id: Optional[str]
    level: AnonymizationLevel
    fields_removed: list[str]
    fields_hashed: list[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
