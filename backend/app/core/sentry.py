"""
Sentry Error Tracking and Performance Monitoring

Integrates Sentry for:
- Automatic error tracking and alerting
- Performance monitoring (APM)
- Release tracking
- User context enrichment
- Custom tags and contexts

Sentry Features:
- Error grouping and deduplication
- Stack trace analysis
- Breadcrumbs for debugging
- Performance transaction tracking
- Real-time alerting
- Trend analysis
"""

import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from typing import Optional, Dict, Any

from loguru import logger

from .config import get_settings

settings = get_settings()


def init_sentry() -> None:
    """
    Initialize Sentry error tracking and performance monitoring.

    Configuration via environment variables:
    - SENTRY_DSN: Sentry project DSN (required)
    - SENTRY_ENVIRONMENT: Environment name (development, staging, production)
    - SENTRY_TRACES_SAMPLE_RATE: Performance sampling rate (0.0 to 1.0)
    - SENTRY_PROFILES_SAMPLE_RATE: Profiling sampling rate (0.0 to 1.0)
    - SENTRY_SEND_DEFAULT_PII: Send personally identifiable information (true/false)
    - SENTRY_DEBUG: Enable Sentry debug mode (true/false)

    Example .env:
        SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
        SENTRY_ENVIRONMENT=production
        SENTRY_TRACES_SAMPLE_RATE=0.1
    """
    sentry_dsn = os.getenv("SENTRY_DSN")

    # Skip initialization if DSN not configured
    if not sentry_dsn:
        logger.info("Sentry DSN not configured - error tracking disabled")
        return

    # Get configuration from environment
    environment = os.getenv("SENTRY_ENVIRONMENT", settings.environment)
    traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))
    send_default_pii = os.getenv("SENTRY_SEND_DEFAULT_PII", "false").lower() == "true"
    debug = os.getenv("SENTRY_DEBUG", "false").lower() == "true"

    # Adjust sampling rates based on environment
    if environment == "development":
        traces_sample_rate = 1.0  # 100% in development
        profiles_sample_rate = 1.0
    elif environment == "production":
        # Keep configured rates for production (to manage quota)
        pass

    # Get release version (from git commit, environment, or default)
    release = os.getenv("SENTRY_RELEASE") or os.getenv("GIT_COMMIT") or "0.3.0"

    # Initialize Sentry
    sentry_sdk.init(
        dsn=sentry_dsn,
        # Environment
        environment=environment,
        release=release,
        # Performance Monitoring
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        # Privacy
        send_default_pii=send_default_pii,
        # Integrations
        integrations=[
            # FastAPI integration (automatic request tracking)
            FastApiIntegration(
                transaction_style="endpoint",  # Group by endpoint
            ),
            # Starlette integration (underlying ASGI framework)
            StarletteIntegration(
                transaction_style="endpoint",
            ),
            # Asyncio integration (async exception tracking)
            AsyncioIntegration(),
            # Redis integration (Redis operation tracking)
            RedisIntegration(),
            # SQLAlchemy integration (database query tracking)
            SqlalchemyIntegration(),
            # HTTPX integration (HTTP client tracking)
            HttpxIntegration(),
            # Logging integration (capture log breadcrumbs)
            LoggingIntegration(
                level=20,  # INFO
                event_level=40,  # ERROR - only send ERROR+ as events
            ),
        ],
        # Options
        debug=debug,
        attach_stacktrace=True,  # Include stack traces
        before_send=_before_send,  # Pre-process events
        before_send_transaction=_before_send_transaction,  # Pre-process transactions
        # Ignore certain errors
        ignore_errors=[
            KeyboardInterrupt,
            SystemExit,
        ],
        # Max breadcrumbs to keep
        max_breadcrumbs=50,
        # Request body size limit (characters)
        max_request_body_size="medium",  # small, medium, always
    )

    logger.info(
        "Sentry initialized",
        extra={
            "environment": environment,
            "release": release,
            "traces_sample_rate": traces_sample_rate,
            "profiles_sample_rate": profiles_sample_rate,
        }
    )


def _before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Pre-process events before sending to Sentry.

    Can be used to:
    - Filter sensitive data
    - Add custom context
    - Skip certain errors
    - Modify event data

    Args:
        event: Sentry event dictionary
        hint: Additional context about the event

    Returns:
        Modified event or None to skip sending
    """
    # Example: Filter out certain errors
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        # Skip certain exception types
        if exc_type.__name__ in ["HTTPException"]:
            # HTTP exceptions are usually handled gracefully
            # Only send to Sentry if status >= 500
            if hasattr(exc_value, "status_code") and exc_value.status_code < 500:
                return None

    # Example: Add custom context
    event.setdefault("tags", {})
    event["tags"]["application"] = "brain-core"

    # Example: Remove sensitive data from request body
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        if isinstance(data, dict):
            # Remove password fields
            for key in list(data.keys()):
                if "password" in key.lower() or "secret" in key.lower():
                    data[key] = "[FILTERED]"

    return event


def _before_send_transaction(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Pre-process performance transactions before sending to Sentry.

    Args:
        event: Sentry transaction event
        hint: Additional context

    Returns:
        Modified event or None to skip sending
    """
    # Example: Skip health check transactions (reduce noise)
    if event.get("transaction") in ["/health", "/health/live", "/health/ready", "/metrics"]:
        return None

    # Example: Add custom tags
    event.setdefault("tags", {})
    event["tags"]["transaction_type"] = "backend"

    return event


# ============================================================================
# Context Management
# ============================================================================

def set_user_context(
    user_id: str,
    email: Optional[str] = None,
    username: Optional[str] = None,
    **extra: Any
) -> None:
    """
    Set user context for Sentry error tracking.

    Args:
        user_id: User ID
        email: User email (optional)
        username: Username (optional)
        **extra: Additional user attributes

    Example:
        from app.core.sentry import set_user_context

        set_user_context(
            user_id="user_123",
            email="user@example.com",
            username="john_doe",
            subscription_tier="premium"
        )
    """
    user_data = {"id": user_id}
    if email:
        user_data["email"] = email
    if username:
        user_data["username"] = username
    user_data.update(extra)

    sentry_sdk.set_user(user_data)


def set_tag(key: str, value: str) -> None:
    """
    Set a custom tag for Sentry events.

    Tags are indexed and searchable in Sentry.

    Args:
        key: Tag key
        value: Tag value

    Example:
        set_tag("mission_type", "deployment")
        set_tag("agent_type", "ops_agent")
    """
    sentry_sdk.set_tag(key, value)


def set_context(name: str, context: Dict[str, Any]) -> None:
    """
    Set custom context for Sentry events.

    Context provides additional structured data.

    Args:
        name: Context name
        context: Context dictionary

    Example:
        set_context("mission", {
            "id": "mission_123",
            "priority": "HIGH",
            "status": "running"
        })
    """
    sentry_sdk.set_context(name, context)


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Add a breadcrumb for debugging.

    Breadcrumbs are a trail of events leading up to an error.

    Args:
        message: Breadcrumb message
        category: Category (e.g., "http", "database", "cache")
        level: Level (debug, info, warning, error, critical)
        data: Additional data

    Example:
        add_breadcrumb(
            message="Database query executed",
            category="database",
            level="info",
            data={"query_time": 0.05, "rows": 42}
        )
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {}
    )


# ============================================================================
# Error Tracking
# ============================================================================

def capture_exception(
    error: Exception,
    **context: Any
) -> str:
    """
    Manually capture an exception to Sentry.

    Args:
        error: Exception to capture
        **context: Additional context (tags, user, etc.)

    Returns:
        Event ID

    Example:
        try:
            risky_operation()
        except Exception as e:
            event_id = capture_exception(
                e,
                mission_id="mission_123",
                agent_type="ops_agent"
            )
            logger.error(f"Error captured: {event_id}")
    """
    # Set context before capturing
    for key, value in context.items():
        if isinstance(value, dict):
            set_context(key, value)
        else:
            set_tag(key, str(value))

    return sentry_sdk.capture_exception(error)


def capture_message(
    message: str,
    level: str = "info",
    **context: Any
) -> str:
    """
    Capture a message to Sentry.

    Args:
        message: Message to capture
        level: Level (debug, info, warning, error, fatal)
        **context: Additional context

    Returns:
        Event ID

    Example:
        capture_message(
            "Unusual activity detected",
            level="warning",
            activity_type="multiple_failed_logins",
            user_id="user_123"
        )
    """
    # Set context
    for key, value in context.items():
        if isinstance(value, dict):
            set_context(key, value)
        else:
            set_tag(key, str(value))

    return sentry_sdk.capture_message(message, level=level)


# ============================================================================
# Performance Monitoring
# ============================================================================

from contextlib import contextmanager
from typing import Iterator, Optional

@contextmanager
def start_transaction(
    name: str,
    op: str,
    **metadata: Any
) -> Iterator[Any]:
    """
    Start a performance transaction.

    Args:
        name: Transaction name
        op: Operation type (e.g., "http.server", "db.query", "task.run")
        **metadata: Additional metadata (tags, data)

    Example:
        with start_transaction(name="process_mission", op="task.run") as transaction:
            transaction.set_tag("mission_id", "mission_123")
            process_mission()
    """
    with sentry_sdk.start_transaction(name=name, op=op) as transaction:
        # Set metadata
        for key, value in metadata.items():
            if isinstance(value, dict):
                transaction.set_context(key, value)
            else:
                transaction.set_tag(key, str(value))

        yield transaction


@contextmanager
def start_span(
    op: str,
    description: Optional[str] = None,
    **metadata: Any
) -> Iterator[Any]:
    """
    Start a performance span (child of current transaction).

    Args:
        op: Operation type (e.g., "db.query", "http.client", "cache.get")
        description: Span description
        **metadata: Additional metadata

    Example:
        with start_transaction(name="process_request", op="http.server"):
            with start_span(op="db.query", description="SELECT * FROM users"):
                users = await db.execute(query)

            with start_span(op="cache.set", description="Cache user data"):
                await redis.set(key, value)
    """
    with sentry_sdk.start_span(op=op, description=description) as span:
        # Set metadata
        for key, value in metadata.items():
            span.set_tag(key, str(value))

        yield span


# ============================================================================
# Utility Functions
# ============================================================================

def is_enabled() -> bool:
    """
    Check if Sentry is enabled.

    Returns:
        True if Sentry DSN is configured
    """
    return bool(os.getenv("SENTRY_DSN"))


def flush(timeout: float = 2.0) -> bool:
    """
    Flush pending Sentry events.

    Useful before application shutdown to ensure all events are sent.

    Args:
        timeout: Maximum time to wait (seconds)

    Returns:
        True if all events were sent
    """
    return sentry_sdk.flush(timeout=timeout)
