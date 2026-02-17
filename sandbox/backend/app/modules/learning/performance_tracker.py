"""
Performance Tracker - Metric collection and time-series aggregation.

Collects raw metrics from agents, aggregates into time windows,
computes summaries with percentiles, and detects trends.
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from loguru import logger

from .schemas import (
    AggregationWindow,
    MetricAggregation,
    MetricEntry,
    MetricQuery,
    MetricSummary,
    MetricType,
)

# Window durations in seconds
WINDOW_SECONDS = {
    AggregationWindow.MINUTE_1: 60,
    AggregationWindow.MINUTE_5: 300,
    AggregationWindow.MINUTE_15: 900,
    AggregationWindow.HOUR_1: 3600,
    AggregationWindow.HOUR_6: 21600,
    AggregationWindow.DAY_1: 86400,
}

# Max raw metrics to retain per agent+type
MAX_RAW_ENTRIES = 5000


class PerformanceTracker:
    """
    Collects metrics, aggregates over windows, computes summaries.

    Storage is in-memory with circular buffers per agent+metric_type.
    """

    def __init__(self) -> None:
        # Raw storage: (agent_id, metric_type) → list of MetricEntry
        self._raw: Dict[Tuple[str, MetricType], List[MetricEntry]] = defaultdict(list)

        # Pre-computed aggregations: (agent_id, metric_type, window) → MetricAggregation
        self._aggregations: Dict[Tuple[str, MetricType, AggregationWindow], MetricAggregation] = {}

        self._total_recorded = 0

        logger.info("📊 PerformanceTracker initialized")

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------

    def record(self, entry: MetricEntry) -> MetricEntry:
        """Record a metric data point."""
        key = (entry.agent_id, entry.metric_type)
        buf = self._raw[key]
        buf.append(entry)

        # Cap buffer
        if len(buf) > MAX_RAW_ENTRIES:
            self._raw[key] = buf[-MAX_RAW_ENTRIES:]

        self._total_recorded += 1

        # Update rolling aggregations
        self._update_aggregations(entry)

        return entry

    def record_batch(self, entries: List[MetricEntry]) -> int:
        """Record multiple metrics at once."""
        for e in entries:
            self.record(e)
        return len(entries)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(self, q: MetricQuery) -> List[MetricEntry]:
        """Query raw metrics with filters."""
        results: List[MetricEntry] = []

        for (agent_id, metric_type), entries in self._raw.items():
            if q.agent_id and agent_id != q.agent_id:
                continue
            if q.metric_type and metric_type != q.metric_type:
                continue

            for e in entries:
                if q.since and e.timestamp < q.since:
                    continue
                if q.until and e.timestamp > q.until:
                    continue
                if q.tags:
                    if not all(e.tags.get(k) == v for k, v in q.tags.items()):
                        continue
                results.append(e)

        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[: q.limit]

    # ------------------------------------------------------------------
    # Summaries
    # ------------------------------------------------------------------

    def summarize(
        self,
        agent_id: str,
        metric_type: MetricType,
        since: Optional[float] = None,
    ) -> MetricSummary:
        """Compute summary statistics for an agent's metric."""
        key = (agent_id, metric_type)
        entries = self._raw.get(key, [])

        if since:
            entries = [e for e in entries if e.timestamp >= since]

        if not entries:
            return MetricSummary(
                metric_type=metric_type,
                agent_id=agent_id,
                count=0,
                mean=0.0,
                min_value=0.0,
                max_value=0.0,
            )

        values = sorted(e.value for e in entries)
        n = len(values)

        return MetricSummary(
            metric_type=metric_type,
            agent_id=agent_id,
            count=n,
            mean=sum(values) / n,
            min_value=values[0],
            max_value=values[-1],
            p50=self._percentile(values, 50),
            p95=self._percentile(values, 95),
            p99=self._percentile(values, 99),
            trend=self._compute_trend(entries),
        )

    def get_aggregation(
        self,
        agent_id: str,
        metric_type: MetricType,
        window: AggregationWindow,
    ) -> Optional[MetricAggregation]:
        """Get pre-computed aggregation for a window."""
        return self._aggregations.get((agent_id, metric_type, window))

    # ------------------------------------------------------------------
    # Agent summaries
    # ------------------------------------------------------------------

    def get_agent_metrics(self, agent_id: str) -> Dict[str, MetricSummary]:
        """Get summaries for all metric types of an agent."""
        result = {}
        for (aid, mtype) in self._raw:
            if aid == agent_id:
                result[mtype.value] = self.summarize(agent_id, mtype)
        return result

    def list_tracked_agents(self) -> List[str]:
        """List all agents with recorded metrics."""
        agents = set()
        for aid, _ in self._raw:
            agents.add(aid)
        return sorted(agents)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _update_aggregations(self, entry: MetricEntry) -> None:
        """Update rolling aggregations for all windows."""
        now = entry.timestamp
        for window in AggregationWindow:
            duration = WINDOW_SECONDS[window]
            key = (entry.agent_id, entry.metric_type, window)

            agg = self._aggregations.get(key)
            if agg is None or now - agg.window_start > duration:
                # Start new window
                agg = MetricAggregation(
                    agent_id=entry.agent_id,
                    metric_type=entry.metric_type,
                    window=window,
                    window_start=now,
                    window_end=now + duration,
                )
                self._aggregations[key] = agg

            agg.add(entry.value)

    @staticmethod
    def _percentile(sorted_values: List[float], p: float) -> float:
        """Compute p-th percentile from sorted values."""
        if not sorted_values:
            return 0.0
        k = (len(sorted_values) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_values[int(k)]
        return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)

    @staticmethod
    def _compute_trend(entries: List[MetricEntry]) -> float:
        """
        Compute trend as slope of linear regression on values over time.

        Positive = improving (for metrics where higher is better).
        Returns normalized slope per hour.
        """
        if len(entries) < 3:
            return 0.0

        n = len(entries)
        t0 = entries[0].timestamp
        xs = [(e.timestamp - t0) / 3600.0 for e in entries]  # hours
        ys = [e.value for e in entries]

        x_mean = sum(xs) / n
        y_mean = sum(ys) / n

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
        denominator = sum((x - x_mean) ** 2 for x in xs)

        if denominator == 0:
            return 0.0
        return numerator / denominator

    @property
    def stats(self) -> Dict:
        return {
            "total_recorded": self._total_recorded,
            "tracked_agents": len(self.list_tracked_agents()),
            "metric_streams": len(self._raw),
            "active_aggregations": len(self._aggregations),
        }
