"""
Error Handler - Comprehensive exception tracking and management

Provides centralized error handling with categorization, context capture,
automatic reporting, and recovery suggestions.
"""

from __future__ import annotations

import sys
import traceback
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class ErrorCategory(str, Enum):
    """Error categories for classification"""
    NETWORK = "network"
    FILE_IO = "file_io"
    TOKEN_LIMIT = "token_limit"
    VALIDATION = "validation"
    API_ERROR = "api_error"
    AGENT_ERROR = "agent_error"
    CODE_GENERATION = "code_generation"
    AUTHENTICATION = "authentication"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Contextual information about an error"""
    operation: str
    component: str
    user_action: Optional[str] = None
    input_data: Optional[Dict] = None
    system_state: Optional[Dict] = None
    environment: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ErrorRecord:
    """Complete error record with all metadata"""
    error_id: str
    timestamp: float
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    exception_type: str
    exception_message: str
    stack_trace: List[str]
    context: ErrorContext
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_actions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "stack_trace": self.stack_trace,
            "context": self.context.to_dict(),
            "recovery_attempted": self.recovery_attempted,
            "recovery_successful": self.recovery_successful,
            "recovery_actions": self.recovery_actions,
            "metadata": self.metadata
        }


class ErrorHandler:
    """
    Comprehensive error handling system with tracking, reporting,
    and recovery capabilities.

    Features:
    - Automatic error categorization
    - Contextual error capture
    - Stack trace collection
    - Error history tracking
    - Recovery suggestion system
    - Escalation paths
    - Persistent error logging
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        max_history: int = 1000,
        auto_report: bool = True
    ):
        """
        Initialize error handler

        Args:
            storage_path: Path to persist error logs
            max_history: Maximum number of errors to keep in memory
            auto_report: Automatically log errors
        """
        self.storage_path = storage_path or Path(
            "/srv/dev/BRAIN-V2/agents/webdev/data/error_log.json"
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.max_history = max_history
        self.auto_report = auto_report

        self._lock = Lock()
        self._error_history: List[ErrorRecord] = []
        self._error_counts: Dict[ErrorCategory, int] = {cat: 0 for cat in ErrorCategory}
        self._recovery_handlers: Dict[ErrorCategory, List[Callable]] = {}

        # Load historical errors
        self._load_history()

        logger.info("ErrorHandler initialized")

    def handle_error(
        self,
        exception: Exception,
        context: ErrorContext,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: Optional[ErrorCategory] = None,
        attempt_recovery: bool = True
    ) -> ErrorRecord:
        """
        Handle an exception with full context capture

        Args:
            exception: The exception to handle
            context: Error context information
            severity: Error severity level
            category: Error category (auto-detected if None)
            attempt_recovery: Whether to attempt automatic recovery

        Returns:
            ErrorRecord with all error details
        """
        # Auto-detect category if not provided
        if category is None:
            category = self._categorize_error(exception)

        # Generate error ID
        error_id = f"{category.value}_{int(time.time() * 1000)}"

        # Capture stack trace
        stack_trace = traceback.format_exception(
            type(exception),
            exception,
            exception.__traceback__
        )

        # Create error record
        error_record = ErrorRecord(
            error_id=error_id,
            timestamp=time.time(),
            severity=severity,
            category=category,
            message=str(exception),
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            stack_trace=stack_trace,
            context=context
        )

        # Attempt recovery if requested
        if attempt_recovery and category in self._recovery_handlers:
            recovery_success = self._attempt_recovery(error_record, exception)
            error_record.recovery_attempted = True
            error_record.recovery_successful = recovery_success

        # Log error
        if self.auto_report:
            self._log_error(error_record)

        # Store in history
        with self._lock:
            self._error_history.append(error_record)
            self._error_counts[category] += 1

            # Trim history if needed
            if len(self._error_history) > self.max_history:
                self._error_history = self._error_history[-self.max_history:]

        # Persist to storage
        self._save_to_storage(error_record)

        return error_record

    def handle_error_with_context(
        self,
        exception: Exception,
        operation: str,
        component: str,
        **context_kwargs
    ) -> ErrorRecord:
        """
        Convenience method to handle error with context creation

        Args:
            exception: The exception to handle
            operation: Operation being performed
            component: Component where error occurred
            **context_kwargs: Additional context parameters

        Returns:
            ErrorRecord
        """
        context = ErrorContext(
            operation=operation,
            component=component,
            **context_kwargs
        )
        return self.handle_error(exception, context)

    def register_recovery_handler(
        self,
        category: ErrorCategory,
        handler: Callable[[ErrorRecord, Exception], bool]
    ) -> None:
        """
        Register a recovery handler for a specific error category

        Args:
            category: Error category to handle
            handler: Recovery function returning True if recovery successful
        """
        if category not in self._recovery_handlers:
            self._recovery_handlers[category] = []

        self._recovery_handlers[category].append(handler)
        logger.info(f"Registered recovery handler for {category.value}")

    def get_error_statistics(self) -> Dict:
        """Get error statistics and metrics"""
        with self._lock:
            total_errors = len(self._error_history)

            if total_errors == 0:
                return {
                    "total_errors": 0,
                    "by_category": {},
                    "by_severity": {},
                    "recovery_rate": 0.0
                }

            # Count by severity
            severity_counts = {}
            for error in self._error_history:
                sev = error.severity.value
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            # Recovery statistics
            recovery_attempted = sum(1 for e in self._error_history if e.recovery_attempted)
            recovery_successful = sum(1 for e in self._error_history if e.recovery_successful)
            recovery_rate = (recovery_successful / recovery_attempted * 100) if recovery_attempted > 0 else 0

            # Recent errors (last hour)
            recent_threshold = time.time() - 3600
            recent_errors = [e for e in self._error_history if e.timestamp > recent_threshold]

            return {
                "total_errors": total_errors,
                "by_category": dict(self._error_counts),
                "by_severity": severity_counts,
                "recovery_stats": {
                    "attempted": recovery_attempted,
                    "successful": recovery_successful,
                    "rate_pct": round(recovery_rate, 2)
                },
                "recent_errors": {
                    "count": len(recent_errors),
                    "categories": [e.category.value for e in recent_errors[-10:]]
                }
            }

    def get_recovery_suggestions(self, error_record: ErrorRecord) -> List[str]:
        """
        Get recovery suggestions for an error

        Args:
            error_record: Error to suggest recovery for

        Returns:
            List of recovery suggestions
        """
        suggestions = []

        # Category-specific suggestions
        category_suggestions = {
            ErrorCategory.NETWORK: [
                "Check network connectivity",
                "Verify API endpoint is accessible",
                "Check for firewall/proxy issues",
                "Retry with exponential backoff"
            ],
            ErrorCategory.TOKEN_LIMIT: [
                "Reduce input context size",
                "Split operation into smaller chunks",
                "Wait for token budget to reset",
                "Use a more efficient operation type"
            ],
            ErrorCategory.FILE_IO: [
                "Verify file path exists",
                "Check file permissions",
                "Ensure parent directory exists",
                "Check disk space availability"
            ],
            ErrorCategory.VALIDATION: [
                "Verify input data format",
                "Check required fields are present",
                "Validate data types and constraints",
                "Review input schema requirements"
            ],
            ErrorCategory.API_ERROR: [
                "Check API credentials",
                "Verify API endpoint configuration",
                "Review API rate limits",
                "Check API service status"
            ],
            ErrorCategory.CONFIGURATION: [
                "Verify configuration file exists",
                "Check configuration syntax",
                "Validate configuration values",
                "Reset to default configuration"
            ]
        }

        suggestions.extend(category_suggestions.get(error_record.category, []))

        # Add severity-based suggestions
        if error_record.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            suggestions.append("Consider escalating to administrator")
            suggestions.append("Review system logs for related issues")

        return suggestions

    def _categorize_error(self, exception: Exception) -> ErrorCategory:
        """Auto-categorize error based on exception type"""
        exception_name = type(exception).__name__
        exception_msg = str(exception).lower()

        # Network errors
        if any(keyword in exception_name.lower() for keyword in ["connection", "timeout", "network"]):
            return ErrorCategory.NETWORK

        # File I/O errors
        if any(keyword in exception_name.lower() for keyword in ["file", "io", "path"]):
            return ErrorCategory.FILE_IO

        # Token limit errors
        if "token" in exception_msg or "limit" in exception_msg:
            return ErrorCategory.TOKEN_LIMIT

        # Validation errors
        if any(keyword in exception_name.lower() for keyword in ["validation", "value"]):
            return ErrorCategory.VALIDATION

        # API errors
        if "api" in exception_msg or "http" in exception_msg:
            return ErrorCategory.API_ERROR

        # Authentication errors
        if any(keyword in exception_msg for keyword in ["auth", "credential", "permission"]):
            return ErrorCategory.AUTHENTICATION

        return ErrorCategory.UNKNOWN

    def _attempt_recovery(
        self,
        error_record: ErrorRecord,
        exception: Exception
    ) -> bool:
        """
        Attempt automatic recovery using registered handlers

        Args:
            error_record: Error record
            exception: Original exception

        Returns:
            True if recovery successful
        """
        handlers = self._recovery_handlers.get(error_record.category, [])

        for handler in handlers:
            try:
                action = handler.__name__
                logger.info(f"Attempting recovery: {action}")

                success = handler(error_record, exception)
                error_record.recovery_actions.append(action)

                if success:
                    logger.info(f"Recovery successful: {action}")
                    return True
                else:
                    logger.warning(f"Recovery failed: {action}")
            except Exception as recovery_error:
                logger.error(f"Recovery handler failed: {recovery_error}")
                error_record.recovery_actions.append(f"{action} (failed)")

        return False

    def _log_error(self, error_record: ErrorRecord) -> None:
        """Log error to logger"""
        log_level_map = {
            ErrorSeverity.DEBUG: logging.DEBUG,
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.FATAL: logging.CRITICAL
        }

        level = log_level_map.get(error_record.severity, logging.ERROR)

        logger.log(
            level,
            f"[{error_record.error_id}] {error_record.category.value}: "
            f"{error_record.message} (component: {error_record.context.component}, "
            f"operation: {error_record.context.operation})"
        )

        # Log stack trace for errors and above
        if error_record.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            for line in error_record.stack_trace:
                logger.debug(line.rstrip())

    def _save_to_storage(self, error_record: ErrorRecord) -> None:
        """Persist error to storage"""
        try:
            # Append to error log file
            with open(self.storage_path, "a") as f:
                f.write(json.dumps(error_record.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to save error to storage: {e}")

    def _load_history(self) -> None:
        """Load error history from storage"""
        if not self.storage_path.exists():
            logger.info("No error history found")
            return

        try:
            # Load recent errors (last 1000)
            with open(self.storage_path) as f:
                lines = f.readlines()

            recent_lines = lines[-self.max_history:]

            for line in recent_lines:
                try:
                    data = json.loads(line)
                    # Reconstruct error record (simplified)
                    # In production, you'd fully reconstruct ErrorRecord
                    category = ErrorCategory(data.get("category", "unknown"))
                    self._error_counts[category] = self._error_counts.get(category, 0) + 1
                except json.JSONDecodeError:
                    continue

            logger.info(f"Loaded error history with {sum(self._error_counts.values())} errors")
        except Exception as e:
            logger.error(f"Failed to load error history: {e}")


# Singleton instance
_error_handler: Optional[ErrorHandler] = None
_handler_lock = Lock()


def get_error_handler(
    storage_path: Optional[Path] = None,
    max_history: int = 1000,
    auto_report: bool = True
) -> ErrorHandler:
    """
    Get or create the global error handler instance

    Args:
        storage_path: Storage path (only used on first call)
        max_history: Max history size (only used on first call)
        auto_report: Auto-report setting (only used on first call)

    Returns:
        ErrorHandler singleton instance
    """
    global _error_handler

    with _handler_lock:
        if _error_handler is None:
            _error_handler = ErrorHandler(
                storage_path=storage_path,
                max_history=max_history,
                auto_report=auto_report
            )
        return _error_handler


# Decorator for automatic error handling
def with_error_handling(
    operation: str,
    component: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    category: Optional[ErrorCategory] = None,
    reraise: bool = True
):
    """
    Decorator to automatically handle errors in functions

    Args:
        operation: Operation being performed
        component: Component name
        severity: Error severity
        category: Error category
        reraise: Whether to reraise exception after handling
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = get_error_handler()
                context = ErrorContext(
                    operation=operation,
                    component=component,
                    input_data={"args": str(args)[:200], "kwargs": str(kwargs)[:200]}
                )
                handler.handle_error(e, context, severity=severity, category=category)

                if reraise:
                    raise
                return None

        return wrapper
    return decorator
