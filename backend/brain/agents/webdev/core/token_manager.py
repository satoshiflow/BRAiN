"""
Token Manager - Real-time token tracking and consumption management

Provides comprehensive token management with consumption estimation,
prevention of over-consumption, and intelligent fallback mechanisms.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Callable
from threading import Lock
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Track token usage for a specific operation"""
    operation: str
    estimated: int
    actual: int = 0
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"  # pending, completed, aborted, failed
    metadata: Dict = field(default_factory=dict)


@dataclass
class TokenBudget:
    """Token budget configuration"""
    max_tokens_per_operation: int = 50_000
    max_tokens_per_hour: int = 200_000
    max_tokens_per_day: int = 1_000_000
    warning_threshold: float = 0.8  # Warn at 80% usage
    abort_threshold: float = 0.95  # Abort at 95% usage
    safety_buffer: int = 5_000  # Reserve buffer


class TokenManager:
    """
    Comprehensive token management system with real-time tracking,
    estimation, and consumption prevention.

    Features:
    - Real-time token tracking
    - Consumption estimation before operations
    - Automatic abort on insufficient tokens
    - Historical usage tracking
    - Configurable budgets and thresholds
    - Thread-safe operations
    """

    def __init__(
        self,
        budget: Optional[TokenBudget] = None,
        storage_path: Optional[Path] = None
    ):
        """
        Initialize token manager

        Args:
            budget: Token budget configuration
            storage_path: Path to persist token usage data
        """
        self.budget = budget or TokenBudget()
        self.storage_path = storage_path or Path("/srv/dev/BRAIN-V2/agents/webdev/data/token_usage.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = Lock()
        self._current_usage: Dict[str, TokenUsage] = {}
        self._history: list[TokenUsage] = []
        self._hourly_usage: int = 0
        self._daily_usage: int = 0
        self._last_reset_hour: float = time.time()
        self._last_reset_day: float = time.time()

        # Load historical data
        self._load_history()

        # Estimation callbacks for different operations
        self._estimators: Dict[str, Callable] = {
            "code_generation": self._estimate_code_generation,
            "code_completion": self._estimate_code_completion,
            "code_review": self._estimate_code_review,
            "ui_generation": self._estimate_ui_generation,
            "default": self._estimate_default
        }

        logger.info(f"TokenManager initialized with budget: {self.budget}")

    def estimate_consumption(
        self,
        operation_type: str,
        context_size: int = 0,
        output_size: int = 0,
        **kwargs
    ) -> int:
        """
        Estimate token consumption for an operation

        Args:
            operation_type: Type of operation (code_generation, etc.)
            context_size: Estimated context/input size in tokens
            output_size: Estimated output size in tokens
            **kwargs: Additional parameters for estimation

        Returns:
            Estimated token count
        """
        estimator = self._estimators.get(operation_type, self._estimators["default"])
        estimate = estimator(context_size, output_size, **kwargs)

        logger.debug(f"Estimated {estimate} tokens for {operation_type}")
        return estimate

    def check_availability(
        self,
        estimated_tokens: int,
        operation: str = "unknown"
    ) -> tuple[bool, str]:
        """
        Check if sufficient tokens are available

        Args:
            estimated_tokens: Number of tokens needed
            operation: Operation description

        Returns:
            Tuple of (available: bool, message: str)
        """
        with self._lock:
            self._reset_counters_if_needed()

            # Check against budget limits
            checks = [
                (
                    estimated_tokens <= self.budget.max_tokens_per_operation,
                    f"Operation exceeds max tokens per operation ({self.budget.max_tokens_per_operation})"
                ),
                (
                    self._hourly_usage + estimated_tokens <= self.budget.max_tokens_per_hour,
                    f"Would exceed hourly limit ({self.budget.max_tokens_per_hour})"
                ),
                (
                    self._daily_usage + estimated_tokens <= self.budget.max_tokens_per_day,
                    f"Would exceed daily limit ({self.budget.max_tokens_per_day})"
                ),
                (
                    estimated_tokens <= self.budget.max_tokens_per_operation - self.budget.safety_buffer,
                    f"Insufficient safety buffer (need {self.budget.safety_buffer} tokens)"
                )
            ]

            for available, message in checks:
                if not available:
                    logger.warning(f"Token check failed for {operation}: {message}")
                    return False, message

            # Check warning threshold
            hourly_usage_pct = (self._hourly_usage + estimated_tokens) / self.budget.max_tokens_per_hour
            if hourly_usage_pct >= self.budget.warning_threshold:
                logger.warning(
                    f"Token usage warning: {hourly_usage_pct*100:.1f}% of hourly budget "
                    f"(operation: {operation})"
                )

            return True, "Sufficient tokens available"

    def reserve_tokens(
        self,
        operation: str,
        estimated_tokens: int,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Reserve tokens for an operation

        Args:
            operation: Operation description
            estimated_tokens: Estimated token count
            metadata: Additional operation metadata

        Returns:
            Operation ID if successful, None if insufficient tokens
        """
        available, message = self.check_availability(estimated_tokens, operation)

        if not available:
            logger.error(f"Cannot reserve tokens for {operation}: {message}")
            return None

        with self._lock:
            operation_id = f"{operation}_{int(time.time()*1000)}"
            usage = TokenUsage(
                operation=operation,
                estimated=estimated_tokens,
                metadata=metadata or {},
                status="reserved"
            )
            self._current_usage[operation_id] = usage

            logger.info(
                f"Reserved {estimated_tokens} tokens for {operation} (ID: {operation_id})"
            )
            return operation_id

    def record_usage(
        self,
        operation_id: str,
        actual_tokens: int,
        status: str = "completed"
    ) -> None:
        """
        Record actual token usage for an operation

        Args:
            operation_id: Operation ID from reserve_tokens
            actual_tokens: Actual tokens consumed
            status: Operation status (completed, failed, aborted)
        """
        with self._lock:
            if operation_id not in self._current_usage:
                logger.warning(f"Unknown operation ID: {operation_id}")
                return

            usage = self._current_usage[operation_id]
            usage.actual = actual_tokens
            usage.status = status

            # Update counters
            self._hourly_usage += actual_tokens
            self._daily_usage += actual_tokens

            # Move to history
            self._history.append(usage)
            del self._current_usage[operation_id]

            # Persist
            self._save_history()

            logger.info(
                f"Recorded {actual_tokens} tokens for {usage.operation} "
                f"(estimated: {usage.estimated}, variance: {actual_tokens - usage.estimated})"
            )

    def abort_operation(self, operation_id: str, reason: str = "") -> None:
        """
        Abort an operation and release reserved tokens

        Args:
            operation_id: Operation ID to abort
            reason: Reason for abort
        """
        with self._lock:
            if operation_id in self._current_usage:
                usage = self._current_usage[operation_id]
                usage.status = "aborted"
                usage.metadata["abort_reason"] = reason

                self._history.append(usage)
                del self._current_usage[operation_id]

                logger.warning(f"Aborted operation {operation_id}: {reason}")

    def get_statistics(self) -> Dict:
        """Get current token usage statistics"""
        with self._lock:
            self._reset_counters_if_needed()

            return {
                "current": {
                    "hourly_usage": self._hourly_usage,
                    "daily_usage": self._daily_usage,
                    "active_operations": len(self._current_usage),
                    "reserved_tokens": sum(u.estimated for u in self._current_usage.values())
                },
                "limits": {
                    "max_per_operation": self.budget.max_tokens_per_operation,
                    "max_per_hour": self.budget.max_tokens_per_hour,
                    "max_per_day": self.budget.max_tokens_per_day
                },
                "utilization": {
                    "hourly_pct": (self._hourly_usage / self.budget.max_tokens_per_hour) * 100,
                    "daily_pct": (self._daily_usage / self.budget.max_tokens_per_day) * 100
                },
                "history": {
                    "total_operations": len(self._history),
                    "completed": sum(1 for h in self._history if h.status == "completed"),
                    "failed": sum(1 for h in self._history if h.status == "failed"),
                    "aborted": sum(1 for h in self._history if h.status == "aborted")
                }
            }

    def _reset_counters_if_needed(self) -> None:
        """Reset hourly/daily counters if time window passed"""
        current_time = time.time()

        # Reset hourly counter
        if current_time - self._last_reset_hour >= 3600:
            self._hourly_usage = 0
            self._last_reset_hour = current_time
            logger.info("Reset hourly token counter")

        # Reset daily counter
        if current_time - self._last_reset_day >= 86400:
            self._daily_usage = 0
            self._last_reset_day = current_time
            logger.info("Reset daily token counter")

    # Estimation methods for different operation types

    def _estimate_code_generation(
        self,
        context_size: int,
        output_size: int,
        **kwargs
    ) -> int:
        """Estimate tokens for code generation"""
        # Base: context + expected output
        # Add 20% overhead for prompting and formatting
        base = context_size + output_size
        overhead = int(base * 0.2)
        return base + overhead + 1000  # +1000 for system prompts

    def _estimate_code_completion(
        self,
        context_size: int,
        output_size: int,
        **kwargs
    ) -> int:
        """Estimate tokens for code completion"""
        # Completions are usually smaller
        base = context_size + output_size
        overhead = int(base * 0.15)
        return base + overhead + 500

    def _estimate_code_review(
        self,
        context_size: int,
        output_size: int,
        **kwargs
    ) -> int:
        """Estimate tokens for code review"""
        # Reviews require full context + detailed analysis
        base = context_size + output_size
        overhead = int(base * 0.3)  # More overhead for analysis
        return base + overhead + 1500

    def _estimate_ui_generation(
        self,
        context_size: int,
        output_size: int,
        **kwargs
    ) -> int:
        """Estimate tokens for UI generation"""
        # UI generation includes component specs, styling, etc.
        base = context_size + output_size
        overhead = int(base * 0.25)
        return base + overhead + 2000

    def _estimate_default(
        self,
        context_size: int,
        output_size: int,
        **kwargs
    ) -> int:
        """Default estimation for unknown operation types"""
        base = context_size + output_size
        overhead = int(base * 0.25)
        return base + overhead + 1000

    def _load_history(self) -> None:
        """Load historical token usage from storage"""
        if not self.storage_path.exists():
            logger.info("No historical token data found")
            return

        try:
            with open(self.storage_path) as f:
                data = json.load(f)

            # Reconstruct history from JSON
            self._history = [
                TokenUsage(**item) for item in data.get("history", [])
            ]

            # Load counters
            self._hourly_usage = data.get("hourly_usage", 0)
            self._daily_usage = data.get("daily_usage", 0)
            self._last_reset_hour = data.get("last_reset_hour", time.time())
            self._last_reset_day = data.get("last_reset_day", time.time())

            logger.info(f"Loaded {len(self._history)} historical token records")
        except Exception as e:
            logger.error(f"Failed to load token history: {e}")

    def _save_history(self) -> None:
        """Persist token usage history to storage"""
        try:
            data = {
                "history": [
                    {
                        "operation": h.operation,
                        "estimated": h.estimated,
                        "actual": h.actual,
                        "timestamp": h.timestamp,
                        "status": h.status,
                        "metadata": h.metadata
                    }
                    for h in self._history[-1000:]  # Keep last 1000 records
                ],
                "hourly_usage": self._hourly_usage,
                "daily_usage": self._daily_usage,
                "last_reset_hour": self._last_reset_hour,
                "last_reset_day": self._last_reset_day
            }

            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug("Token history saved")
        except Exception as e:
            logger.error(f"Failed to save token history: {e}")


# Singleton instance
_token_manager: Optional[TokenManager] = None
_manager_lock = Lock()


def get_token_manager(
    budget: Optional[TokenBudget] = None,
    storage_path: Optional[Path] = None
) -> TokenManager:
    """
    Get or create the global token manager instance

    Args:
        budget: Token budget configuration (only used on first call)
        storage_path: Storage path (only used on first call)

    Returns:
        TokenManager singleton instance
    """
    global _token_manager

    with _manager_lock:
        if _token_manager is None:
            _token_manager = TokenManager(budget=budget, storage_path=storage_path)
        return _token_manager
