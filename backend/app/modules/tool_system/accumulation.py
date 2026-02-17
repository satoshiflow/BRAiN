"""
Accumulation Engine - Intelligent tool acquisition and retention.

BRAIN doesn't just *use* tools - it *accumulates* them:
    - Learns optimal parameters from usage patterns
    - Identifies failure modes and avoids them
    - Discovers cross-tool synergies
    - Scores retention value (drop unused/harmful, keep essential)
    - Integrates with KARMA for ethical tool governance

This is what differentiates BRAIN from frameworks that merely "call" tools.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from loguru import logger

from .schemas import (
    ToolAccumulationRecord,
    ToolDefinition,
    ToolExecutionResult,
    ToolStatus,
)
from .registry import ToolRegistry


# Thresholds for accumulation decisions
MIN_KARMA_FOR_RETENTION = 25.0        # Below this → candidate for removal
MIN_SUCCESS_RATE_FOR_RETENTION = 0.3  # Below 30% success → review
MAX_IDLE_DAYS = 30                     # No use in 30 days → candidate for deprecation
SYNERGY_MIN_COOCCURRENCE = 3          # Min co-occurrences to detect synergy


class AccumulationEngine:
    """
    Manages BRAIN's tool knowledge accumulation.

    Unlike simple tool registries, the AccumulationEngine:
    1. Learns from every execution (parameters, failures, timing)
    2. Computes retention scores (should BRAIN keep this tool?)
    3. Detects synergies between tools
    4. Triggers automatic status changes (suspend, deprecate)
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

        # Co-occurrence tracking for synergy detection
        # Key: frozenset({tool_a, tool_b}), Value: count
        self._cooccurrences: Dict[frozenset, int] = {}

        # Recent execution log for learning (circular buffer)
        self._recent_executions: List[Tuple[str, bool, Dict]] = []  # (tool_id, success, params)
        self._max_recent = 500

        logger.info("🧠 AccumulationEngine initialized")

    # ------------------------------------------------------------------
    # Learn from execution
    # ------------------------------------------------------------------

    async def record_execution(
        self,
        tool_id: str,
        result: ToolExecutionResult,
        parameters: Dict,
    ) -> None:
        """
        Record an execution and update accumulated knowledge.

        Called after every tool execution to:
        1. Update registry metrics
        2. Learn optimal parameters
        3. Record failure patterns
        4. Update retention score
        """
        # Update registry accumulation record
        await self.registry.record_execution(
            tool_id=tool_id,
            success=result.success,
            duration_ms=result.duration_ms,
        )

        # Track in recent executions
        self._recent_executions.append((tool_id, result.success, parameters))
        if len(self._recent_executions) > self._max_recent:
            self._recent_executions = self._recent_executions[-self._max_recent:]

        # Learn from success
        if result.success:
            await self._learn_successful_params(tool_id, parameters)

        # Learn from failure
        if not result.success and result.error:
            await self._learn_failure_pattern(tool_id, result.error)

        # Update retention score
        await self._update_retention(tool_id)

    # ------------------------------------------------------------------
    # Parameter learning
    # ------------------------------------------------------------------

    async def _learn_successful_params(self, tool_id: str, params: Dict) -> None:
        """
        Track which parameter combinations lead to success.

        Over time, builds up 'learned_defaults' that can be suggested
        to agents using this tool.
        """
        acc = await self.registry.get_accumulation(tool_id)
        if not acc:
            return

        for key, value in params.items():
            if key.startswith("_"):
                continue  # Skip internal params
            # Simple heuristic: if a param value appears in >50% of successes,
            # consider it a good default
            existing = acc.learned_defaults.get(key)
            if existing is None:
                acc.learned_defaults[key] = value
            # For now just keep the most recent successful value
            # Future: statistical tracking with frequency counts

    async def _learn_failure_pattern(self, tool_id: str, error: str) -> None:
        """Record failure patterns to avoid repeat errors."""
        acc = await self.registry.get_accumulation(tool_id)
        if not acc:
            return

        # Normalize error (first 100 chars)
        pattern = error[:100].strip()
        if pattern not in acc.failure_patterns:
            acc.failure_patterns.append(pattern)
            # Keep only last 20 patterns
            if len(acc.failure_patterns) > 20:
                acc.failure_patterns = acc.failure_patterns[-20:]

    # ------------------------------------------------------------------
    # Retention scoring
    # ------------------------------------------------------------------

    async def _update_retention(self, tool_id: str) -> None:
        """
        Compute retention score: should BRAIN keep accumulating this tool?

        Factors:
            +30  High success rate (>80%)
            +20  Used recently (within 7 days)
            +20  High KARMA score (>70)
            +15  Has synergies with other active tools
            +15  Low avg duration (fast tool)
            -20  Low success rate (<30%)
            -15  Not used in >14 days
            -20  Low KARMA score (<25)
        """
        acc = await self.registry.get_accumulation(tool_id)
        tool = await self.registry.get(tool_id)
        if not acc or not tool:
            return

        score = 50.0  # Base score

        # Success rate
        if acc.total_executions > 0:
            rate = acc.successful_executions / acc.total_executions
            if rate > 0.8:
                score += 30.0
            elif rate < MIN_SUCCESS_RATE_FOR_RETENTION:
                score -= 20.0

        # Recency
        if tool.last_used_at:
            days_idle = (datetime.utcnow() - tool.last_used_at).days
            if days_idle <= 7:
                score += 20.0
            elif days_idle > 14:
                score -= 15.0

        # KARMA
        if tool.karma_score > 70:
            score += 20.0
        elif tool.karma_score < MIN_KARMA_FOR_RETENTION:
            score -= 20.0

        # Synergies
        if acc.synergies:
            score += 15.0

        # Speed (under 500ms average is good)
        if acc.avg_duration_ms > 0 and acc.avg_duration_ms < 500:
            score += 15.0

        acc.retention_score = max(0.0, min(100.0, score))
        acc.last_evaluated_at = datetime.utcnow()

    # ------------------------------------------------------------------
    # Synergy detection
    # ------------------------------------------------------------------

    async def record_cooccurrence(self, tool_ids: List[str]) -> None:
        """
        Record that multiple tools were used together in one mission/session.

        After enough co-occurrences, mark them as synergies.
        """
        if len(tool_ids) < 2:
            return

        # Track pairwise co-occurrences
        for i in range(len(tool_ids)):
            for j in range(i + 1, len(tool_ids)):
                pair = frozenset({tool_ids[i], tool_ids[j]})
                self._cooccurrences[pair] = self._cooccurrences.get(pair, 0) + 1

                if self._cooccurrences[pair] >= SYNERGY_MIN_COOCCURRENCE:
                    await self._register_synergy(tool_ids[i], tool_ids[j])

    async def _register_synergy(self, tool_a: str, tool_b: str) -> None:
        """Mark two tools as synergistic."""
        acc_a = await self.registry.get_accumulation(tool_a)
        acc_b = await self.registry.get_accumulation(tool_b)

        if acc_a and tool_b not in acc_a.synergies:
            acc_a.synergies.append(tool_b)
            logger.info("🔗 Synergy detected: %s ↔ %s", tool_a, tool_b)

        if acc_b and tool_a not in acc_b.synergies:
            acc_b.synergies.append(tool_a)

    # ------------------------------------------------------------------
    # Maintenance: auto-suspend / auto-deprecate
    # ------------------------------------------------------------------

    async def run_maintenance(self) -> Dict:
        """
        Periodic maintenance pass over all tools.

        Automatically:
        - Suspends tools with retention_score < 15
        - Deprecates tools not used in MAX_IDLE_DAYS
        - Logs recommendations

        Returns summary of actions taken.
        """
        actions = {"suspended": [], "deprecated": [], "warnings": []}

        tools = await self.registry.list_tools(status=ToolStatus.ACTIVE)

        for tool in tools:
            acc = await self.registry.get_accumulation(tool.tool_id)
            if not acc:
                continue

            # Auto-suspend: very low retention
            if acc.retention_score < 15.0 and acc.total_executions >= 5:
                await self.registry.set_status(
                    tool.tool_id,
                    ToolStatus.SUSPENDED,
                    reason=f"Low retention score: {acc.retention_score:.1f}",
                )
                actions["suspended"].append(tool.tool_id)
                continue

            # Auto-deprecate: long idle
            if tool.last_used_at:
                days_idle = (datetime.utcnow() - tool.last_used_at).days
                if days_idle > MAX_IDLE_DAYS:
                    await self.registry.set_status(
                        tool.tool_id,
                        ToolStatus.DEPRECATED,
                        reason=f"Idle for {days_idle} days",
                    )
                    actions["deprecated"].append(tool.tool_id)
                    continue

            # Warning: declining KARMA trend
            if len(acc.karma_trend) >= 5:
                recent = acc.karma_trend[-5:]
                if all(recent[i] > recent[i + 1] for i in range(len(recent) - 1)):
                    actions["warnings"].append(
                        f"{tool.tool_id}: declining KARMA trend"
                    )

        if actions["suspended"] or actions["deprecated"]:
            logger.info(
                "🧹 Accumulation maintenance: suspended=%d, deprecated=%d",
                len(actions["suspended"]),
                len(actions["deprecated"]),
            )

        return actions

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    async def get_recommendations(self, tool_id: str) -> Dict:
        """
        Get usage recommendations for a tool based on accumulated knowledge.

        Returns learned defaults, known failure patterns, and synergies.
        """
        acc = await self.registry.get_accumulation(tool_id)
        if not acc:
            return {"error": "No accumulation record found"}

        return {
            "tool_id": tool_id,
            "learned_defaults": acc.learned_defaults,
            "failure_patterns": acc.failure_patterns,
            "synergies": acc.synergies,
            "retention_score": acc.retention_score,
            "success_rate": (
                acc.successful_executions / acc.total_executions
                if acc.total_executions > 0
                else None
            ),
            "avg_duration_ms": acc.avg_duration_ms,
        }
