"""
Governance Metrics for BRAiN Sovereign Mode

Prometheus-compatible metrics for governance observability.

**G4 Module** - No business data, no PII, only governance signals.
"""

from typing import Dict, Any
from threading import RLock
from datetime import datetime


class Counter:
    """
    Simple thread-safe counter for governance metrics.

    Prometheus-compatible naming and structure.
    """

    def __init__(self, name: str, description: str, labels: list[str] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self._values: Dict[tuple, float] = {}
        self._lock = RLock()

    def inc(self, label_values: Dict[str, Any] = None, amount: float = 1.0):
        """Increment counter."""
        label_tuple = self._make_label_tuple(label_values or {})

        with self._lock:
            if label_tuple not in self._values:
                self._values[label_tuple] = 0.0
            self._values[label_tuple] += amount

    def get(self, label_values: Dict[str, Any] = None) -> float:
        """Get current counter value."""
        label_tuple = self._make_label_tuple(label_values or {})

        with self._lock:
            return self._values.get(label_tuple, 0.0)

    def get_all(self) -> Dict[tuple, float]:
        """Get all counter values with labels."""
        with self._lock:
            return dict(self._values)

    def _make_label_tuple(self, label_values: Dict[str, Any]) -> tuple:
        """Create hashable label tuple."""
        return tuple(sorted((k, str(v)) for k, v in label_values.items()))

    def reset(self):
        """Reset all counters (for testing)."""
        with self._lock:
            self._values.clear()


class Gauge:
    """
    Simple thread-safe gauge for governance metrics.

    Prometheus-compatible naming and structure.
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._value: float = 0.0
        self._lock = RLock()

    def set(self, value: float):
        """Set gauge value."""
        with self._lock:
            self._value = value

    def get(self) -> float:
        """Get current gauge value."""
        with self._lock:
            return self._value

    def inc(self, amount: float = 1.0):
        """Increment gauge."""
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0):
        """Decrement gauge."""
        with self._lock:
            self._value -= amount

    def reset(self):
        """Reset gauge to 0 (for testing)."""
        with self._lock:
            self._value = 0.0


# =============================================================================
# G4.1: Governance Metrics Registry
# =============================================================================


class GovernanceMetrics:
    """
    Central registry for governance metrics.

    **Metrics Categories:**
    - Mode Switch Governance (G2)
    - Bundle Trust (G1)
    - AXE Trust Tiers (G3)
    - Override Usage (G2)

    **No Business Data:**
    - No payloads
    - No PII
    - Only governance signals
    """

    def __init__(self):
        # Mode Switch Governance (G2)
        self.mode_switch_count = Counter(
            name="sovereign_mode_switch_total",
            description="Total mode switches by target mode",
            labels=["target_mode"],
        )

        self.preflight_failure_count = Counter(
            name="sovereign_preflight_failure_total",
            description="Total preflight failures by gate",
            labels=["gate"],
        )

        self.override_usage_count = Counter(
            name="sovereign_override_usage_total",
            description="Total owner override usage count",
            labels=[],
        )

        # Bundle Trust (G1)
        self.bundle_signature_failure_count = Counter(
            name="sovereign_bundle_signature_failure_total",
            description="Total bundle signature validation failures",
            labels=[],
        )

        self.bundle_quarantine_count = Counter(
            name="sovereign_bundle_quarantine_total",
            description="Total bundles quarantined",
            labels=[],
        )

        # AXE Trust Tiers (G3)
        self.axe_trust_violation_count = Counter(
            name="axe_trust_violation_total",
            description="Total AXE trust tier violations",
            labels=["trust_tier"],
        )

        # Override Status (G2)
        self.override_active_gauge = Gauge(
            name="sovereign_override_active",
            description="Whether an override is currently active (0|1)",
        )

        # Last update timestamp
        self.last_update = datetime.utcnow()

    def record_mode_switch(self, target_mode: str):
        """Record a mode switch."""
        self.mode_switch_count.inc({"target_mode": target_mode})
        self.last_update = datetime.utcnow()

    def record_preflight_failure(self, gate_name: str):
        """Record a preflight gate failure."""
        self.preflight_failure_count.inc({"gate": gate_name})
        self.last_update = datetime.utcnow()

    def record_override_usage(self):
        """Record owner override usage."""
        self.override_usage_count.inc()
        self.last_update = datetime.utcnow()

    def record_bundle_signature_failure(self):
        """Record bundle signature validation failure."""
        self.bundle_signature_failure_count.inc()
        self.last_update = datetime.utcnow()

    def record_bundle_quarantine(self):
        """Record bundle quarantine."""
        self.bundle_quarantine_count.inc()
        self.last_update = datetime.utcnow()

    def record_axe_trust_violation(self, trust_tier: str):
        """Record AXE trust tier violation."""
        self.axe_trust_violation_count.inc({"trust_tier": trust_tier})
        self.last_update = datetime.utcnow()

    def set_override_active(self, active: bool):
        """Set override active status (0 or 1)."""
        self.override_active_gauge.set(1.0 if active else 0.0)
        self.last_update = datetime.utcnow()

    def get_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus text format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = []

        # Helper to format metric lines
        def add_metric(metric_name: str, metric_type: str, description: str, values: dict):
            lines.append(f"# HELP {metric_name} {description}")
            lines.append(f"# TYPE {metric_name} {metric_type}")

            for label_tuple, value in values.items():
                if label_tuple:
                    labels_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                    lines.append(f"{metric_name}{{{labels_str}}} {value}")
                else:
                    lines.append(f"{metric_name} {value}")

        # Mode switch counter
        add_metric(
            self.mode_switch_count.name,
            "counter",
            self.mode_switch_count.description,
            self.mode_switch_count.get_all(),
        )

        # Preflight failure counter
        add_metric(
            self.preflight_failure_count.name,
            "counter",
            self.preflight_failure_count.description,
            self.preflight_failure_count.get_all(),
        )

        # Override usage counter
        add_metric(
            self.override_usage_count.name,
            "counter",
            self.override_usage_count.description,
            {(): self.override_usage_count.get()},
        )

        # Bundle signature failure counter
        add_metric(
            self.bundle_signature_failure_count.name,
            "counter",
            self.bundle_signature_failure_count.description,
            {(): self.bundle_signature_failure_count.get()},
        )

        # Bundle quarantine counter
        add_metric(
            self.bundle_quarantine_count.name,
            "counter",
            self.bundle_quarantine_count.description,
            {(): self.bundle_quarantine_count.get()},
        )

        # AXE trust violation counter
        add_metric(
            self.axe_trust_violation_count.name,
            "counter",
            self.axe_trust_violation_count.description,
            self.axe_trust_violation_count.get_all(),
        )

        # Override active gauge
        lines.append(f"# HELP {self.override_active_gauge.name} {self.override_active_gauge.description}")
        lines.append(f"# TYPE {self.override_active_gauge.name} gauge")
        lines.append(f"{self.override_active_gauge.name} {self.override_active_gauge.get()}")

        return "\n".join(lines) + "\n"

    def get_summary(self) -> Dict[str, Any]:
        """
        Get metrics summary as JSON-serializable dict.

        Returns:
            Metrics summary
        """
        return {
            "mode_switches": {
                label_tuple[0][1] if label_tuple else "total": value
                for label_tuple, value in self.mode_switch_count.get_all().items()
            },
            "preflight_failures": {
                label_tuple[0][1] if label_tuple else "total": value
                for label_tuple, value in self.preflight_failure_count.get_all().items()
            },
            "override_usage_total": self.override_usage_count.get(),
            "bundle_signature_failures": self.bundle_signature_failure_count.get(),
            "bundle_quarantines": self.bundle_quarantine_count.get(),
            "axe_trust_violations": {
                label_tuple[0][1] if label_tuple else "total": value
                for label_tuple, value in self.axe_trust_violation_count.get_all().items()
            },
            "override_active": self.override_active_gauge.get() == 1.0,
            "last_update": self.last_update.isoformat(),
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_governance_metrics: GovernanceMetrics | None = None
_metrics_lock = RLock()


def get_governance_metrics() -> GovernanceMetrics:
    """
    Get singleton governance metrics instance.

    Returns:
        GovernanceMetrics singleton
    """
    global _governance_metrics

    with _metrics_lock:
        if _governance_metrics is None:
            _governance_metrics = GovernanceMetrics()

        return _governance_metrics


def reset_governance_metrics():
    """
    Reset all governance metrics (for testing).

    **WARNING:** This should only be used in tests.
    """
    global _governance_metrics

    with _metrics_lock:
        _governance_metrics = GovernanceMetrics()
