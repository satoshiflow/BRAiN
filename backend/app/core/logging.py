"""
Structured Logging Configuration for BRAiN Core

Features:
- JSON-formatted logs for production (machine-readable)
- Human-readable logs for development (colorized)
- Context injection (request_id, user_id, etc.)
- File rotation with compression
- Environment-based log levels
- Async logging for high throughput
- Integration with existing logging module

Uses Loguru for modern logging capabilities:
- Better performance than stdlib logging
- Automatic serialization of exceptions
- Context-aware logging
- Thread-safe by default
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from loguru import logger
from pythonjsonlogger import jsonlogger

from .config import get_settings

settings = get_settings()


# ============================================================================
# Loguru Configuration
# ============================================================================

def configure_logging() -> None:
    """
    Configure structured logging for the application.

    Behavior:
    - Development: Colorized console output with detailed formatting
    - Production: JSON-formatted logs for log aggregation
    - File logging: Rotation with compression (optional)
    - Context injection: request_id, user_id, component, etc.
    """
    # Remove default logger
    logger.remove()

    # Determine log level from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    if settings.environment == "development":
        log_level = "DEBUG"  # More verbose in development

    # Get log directory from environment
    log_dir = os.getenv("LOG_DIR", "logs")
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # ========== Console Logging ==========

    if settings.environment == "development":
        # Development: Human-readable colorized output
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level> | "
                   "{extra}",
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    else:
        # Production: JSON-formatted logs
        logger.add(
            sys.stdout,
            format="{message}",
            level=log_level,
            serialize=True,  # Output as JSON
            backtrace=False,  # Don't include full traceback (security)
            diagnose=False,   # Don't include variable values (security)
        )

    # ========== File Logging (Optional) ==========

    if os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true":
        # Rotating file handler with compression
        logger.add(
            f"{log_dir}/brain_{{time:YYYY-MM-DD}}.log",
            format="{message}",
            level=log_level,
            serialize=True,  # JSON format
            rotation="00:00",  # Rotate daily at midnight
            retention="30 days",  # Keep logs for 30 days
            compression="gz",  # Compress rotated logs
            enqueue=True,  # Async logging (thread-safe)
            backtrace=True,
            diagnose=True,
        )

        # Separate error log file
        logger.add(
            f"{log_dir}/brain_errors_{{time:YYYY-MM-DD}}.log",
            format="{message}",
            level="ERROR",
            serialize=True,
            rotation="00:00",
            retention="90 days",  # Keep error logs longer
            compression="gz",
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )

    # ========== Intercept Standard Logging ==========
    # This captures logs from libraries using stdlib logging

    class InterceptHandler(logging.Handler):
        """
        Intercept standard logging and redirect to Loguru.

        This ensures all logs (from FastAPI, uvicorn, sqlalchemy, etc.)
        go through Loguru for consistent formatting.
        """

        def emit(self, record: logging.LogRecord) -> None:
            # Get corresponding Loguru level
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Find caller from where the logged message originated
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            # Log with context
            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # Intercept all standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Configure specific loggers
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error",
                       "fastapi", "sqlalchemy.engine"]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    # Silence overly noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger.info(
        "Logging configured",
        extra={
            "environment": settings.environment,
            "log_level": log_level,
            "file_logging": os.getenv("ENABLE_FILE_LOGGING", "false"),
        }
    )


# ============================================================================
# Context Logging Utilities
# ============================================================================

def get_logger(name: str) -> "logger":
    """
    Get a logger with the given name.

    Usage:
        from app.core.logging import get_logger

        logger = get_logger(__name__)
        logger.info("Processing request")
    """
    return logger.bind(component=name)


def log_with_context(
    level: str,
    message: str,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **extra: Any
) -> None:
    """
    Log a message with context.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Log message
        request_id: Request ID (from middleware)
        user_id: User ID (from auth)
        **extra: Additional context fields

    Example:
        log_with_context(
            "INFO",
            "User logged in",
            request_id="abc-123",
            user_id="user_456",
            ip_address="192.168.1.1"
        )
    """
    context = {}
    if request_id:
        context["request_id"] = request_id
    if user_id:
        context["user_id"] = user_id
    context.update(extra)

    logger.bind(**context).log(level, message)


def log_exception(
    exc: Exception,
    request_id: Optional[str] = None,
    **extra: Any
) -> None:
    """
    Log an exception with full traceback and context.

    Args:
        exc: Exception to log
        request_id: Request ID (from middleware)
        **extra: Additional context fields

    Example:
        try:
            risky_operation()
        except Exception as e:
            log_exception(e, request_id=request.state.request_id)
    """
    context = {}
    if request_id:
        context["request_id"] = request_id
    context.update(extra)

    logger.bind(**context).exception(str(exc))


# ============================================================================
# Structured Log Builder
# ============================================================================

class LogContext:
    """
    Context manager for structured logging with automatic field injection.

    Usage:
        with LogContext(request_id="abc-123", user_id="user_456"):
            logger.info("Processing request")
            # Logs will include request_id and user_id

            with LogContext(operation="database_query"):
                logger.info("Executing query")
                # Logs will include request_id, user_id, AND operation
    """

    def __init__(self, **context: Any):
        self.context = context
        self.token = None

    def __enter__(self):
        self.token = logger.contextualize(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Context is automatically removed by loguru
        return False


# ============================================================================
# Performance Logging
# ============================================================================

import time
from contextlib import contextmanager
from typing import Iterator

@contextmanager
def log_performance(
    operation: str,
    request_id: Optional[str] = None,
    **extra: Any
) -> Iterator[None]:
    """
    Context manager for logging operation performance.

    Args:
        operation: Name of the operation
        request_id: Request ID (from middleware)
        **extra: Additional context fields

    Example:
        with log_performance("database_query", request_id=request.state.request_id):
            result = await db.execute(query)
    """
    start_time = time.time()
    context = {"operation": operation}
    if request_id:
        context["request_id"] = request_id
    context.update(extra)

    logger.bind(**context).debug(f"Starting {operation}")

    try:
        yield
    except Exception as e:
        duration = time.time() - start_time
        logger.bind(**context).error(
            f"{operation} failed",
            duration_seconds=duration,
            error=str(e)
        )
        raise
    else:
        duration = time.time() - start_time
        logger.bind(**context).info(
            f"{operation} completed",
            duration_seconds=duration
        )


# ============================================================================
# Backwards Compatibility (stdlib logging)
# ============================================================================

def setup_stdlib_logging() -> None:
    """
    DEPRECATED: Use configure_logging() instead.

    Kept for backwards compatibility.
    """
    configure_logging()
