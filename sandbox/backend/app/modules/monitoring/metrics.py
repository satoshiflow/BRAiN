"""
Monitoring Metrics Collection (Sprint 7)

Prometheus-compatible metrics collector with fail-safe design.
All metrics collection is non-blocking and failures do not affect runtime.
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime
from threading import RLock
from loguru import logger

from app.modules.sovereign_mode.schemas import OperationMode


class MetricsCollector:
    """
    Non-blocking metrics collector for BRAiN operational monitoring.

    Design Principles:
    - Metrics collection MUST NOT block runtime
    - Metrics failures MUST NOT affect core operations
    - No secrets, no payload data, no bundle content
    - Prometheus pull model

    Metrics:
    - brain_mode_current: Current operation mode (gauge)
    - brain_mode_switch_total: Total mode switches (counter)
    - brain_override_active: Active override flag (gauge, 0/1)
    - brain_quarantine_total: Bundles quarantined (counter)
    - brain_executor_failures_total: Executor hard failures (counter)
    - brain_last_success_timestamp: Last successful operation (gauge, unix timestamp)
    """

    # Mode value mapping for Prometheus (gauge)
    MODE_VALUES = {
        OperationMode.ONLINE: 0,
        OperationMode.OFFLINE: 1,
        OperationMode.SOVEREIGN: 2,
        OperationMode.QUARANTINE: 3,
    }

    def __init__(self):
        """Initialize metrics collector."""
        self.lock = RLock()

        # Metrics storage (in-memory)
        self._mode_switches_total: int = 0
        self._quarantine_total: int = 0
        self._executor_failures_total: int = 0
        self._override_active: bool = False
        self._last_success_timestamp: float = time.time()

        # Current state
        self._current_mode: OperationMode = OperationMode.ONLINE

        # Metadata
        self._started_at: float = time.time()

        logger.info("MetricsCollector initialized (fail-safe mode)")

    # === Metric Updaters (called by other components) ===

    def record_mode_switch(self, new_mode: OperationMode):
        """
        Record a mode switch.

        Args:
            new_mode: New operation mode
        """
        try:
            with self.lock:
                self._mode_switches_total += 1
                self._current_mode = new_mode
                logger.debug(f"Metrics: mode_switch recorded -> {new_mode.value}")
        except Exception as e:
            # Fail-safe: log but do not propagate
            logger.warning(f"Metrics collection failed (mode_switch): {e}")

    def record_quarantine(self):
        """Record a bundle quarantine."""
        try:
            with self.lock:
                self._quarantine_total += 1
                logger.debug("Metrics: quarantine recorded")
        except Exception as e:
            logger.warning(f"Metrics collection failed (quarantine): {e}")

    def record_executor_failure(self):
        """Record an executor hard failure."""
        try:
            with self.lock:
                self._executor_failures_total += 1
                logger.debug("Metrics: executor_failure recorded")
        except Exception as e:
            logger.warning(f"Metrics collection failed (executor_failure): {e}")

    def set_override_active(self, active: bool):
        """
        Set override active status.

        Args:
            active: Override is currently active
        """
        try:
            with self.lock:
                self._override_active = active
                logger.debug(f"Metrics: override_active={active}")
        except Exception as e:
            logger.warning(f"Metrics collection failed (override): {e}")

    def record_success(self):
        """Record a successful operation."""
        try:
            with self.lock:
                self._last_success_timestamp = time.time()
        except Exception as e:
            logger.warning(f"Metrics collection failed (success): {e}")

    # === Prometheus Export ===

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus text format.

        Format: https://prometheus.io/docs/instrumenting/exposition_formats/

        Returns:
            Prometheus-formatted metrics string
        """
        try:
            with self.lock:
                lines = []

                # Metadata
                lines.append("# HELP brain_info BRAiN monitoring metadata")
                lines.append("# TYPE brain_info gauge")
                lines.append(
                    f'brain_info{{version="1.0.0",started_at="{int(self._started_at)}"}} 1'
                )
                lines.append("")

                # brain_mode_current
                lines.append("# HELP brain_mode_current Current operation mode (0=online, 1=offline, 2=sovereign, 3=quarantine)")
                lines.append("# TYPE brain_mode_current gauge")
                mode_value = self.MODE_VALUES.get(self._current_mode, -1)
                lines.append(
                    f'brain_mode_current{{mode="{self._current_mode.value}"}} {mode_value}'
                )
                lines.append("")

                # brain_mode_switch_total
                lines.append("# HELP brain_mode_switch_total Total number of mode switches")
                lines.append("# TYPE brain_mode_switch_total counter")
                lines.append(f"brain_mode_switch_total {self._mode_switches_total}")
                lines.append("")

                # brain_override_active
                lines.append("# HELP brain_override_active Active override status (0=inactive, 1=active)")
                lines.append("# TYPE brain_override_active gauge")
                override_value = 1 if self._override_active else 0
                lines.append(f"brain_override_active {override_value}")
                lines.append("")

                # brain_quarantine_total
                lines.append("# HELP brain_quarantine_total Total bundles quarantined")
                lines.append("# TYPE brain_quarantine_total counter")
                lines.append(f"brain_quarantine_total {self._quarantine_total}")
                lines.append("")

                # brain_executor_failures_total
                lines.append("# HELP brain_executor_failures_total Total executor hard failures")
                lines.append("# TYPE brain_executor_failures_total counter")
                lines.append(f"brain_executor_failures_total {self._executor_failures_total}")
                lines.append("")

                # brain_last_success_timestamp
                lines.append("# HELP brain_last_success_timestamp Last successful operation (unix timestamp)")
                lines.append("# TYPE brain_last_success_timestamp gauge")
                lines.append(f"brain_last_success_timestamp {self._last_success_timestamp}")
                lines.append("")

                return "\n".join(lines)

        except Exception as e:
            # Fail-safe: return error metric instead of failing
            logger.error(f"Metrics export failed: {e}")
            return f"# ERROR: Metrics export failed: {e}\n"

    def get_summary(self) -> Dict[str, Any]:
        """
        Get human-readable metrics summary.

        Returns:
            Metrics summary dictionary
        """
        try:
            with self.lock:
                return {
                    "current_mode": self._current_mode.value,
                    "mode_switches_total": self._mode_switches_total,
                    "override_active": self._override_active,
                    "quarantine_total": self._quarantine_total,
                    "executor_failures_total": self._executor_failures_total,
                    "last_success_timestamp": self._last_success_timestamp,
                    "last_success_iso": datetime.fromtimestamp(
                        self._last_success_timestamp
                    ).isoformat(),
                    "uptime_seconds": int(time.time() - self._started_at),
                }
        except Exception as e:
            logger.error(f"Metrics summary failed: {e}")
            return {"error": str(e)}

    def health_check(self) -> bool:
        """
        Check if metrics collector is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Simple health check: can we acquire lock?
            with self.lock:
                return True
        except Exception as e:
            logger.error(f"Metrics health check failed: {e}")
            return False


# Singleton instance
_metrics_collector: Optional[MetricsCollector] = None
_metrics_lock = RLock()


def get_metrics_collector() -> MetricsCollector:
    """
    Get singleton metrics collector instance.

    Returns:
        MetricsCollector instance
    """
    global _metrics_collector

    with _metrics_lock:
        if _metrics_collector is None:
            _metrics_collector = MetricsCollector()
        return _metrics_collector
