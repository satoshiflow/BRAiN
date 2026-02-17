"""
Conflict Resolver - Constitution-based conflict resolution.

When agents disagree (resource contention, contradictory actions,
overlapping tasks), the resolver applies BRAIN's Constitution
principles to decide the outcome.

Resolution strategies:
    1. Priority-based:  Higher-priority task wins
    2. KARMA-based:     Agent with higher KARMA prevails
    3. Vote:            Democratic vote among peers
    4. Supervisor:      Escalate to supervisor for decision
    5. Constitution:    Apply constitutional rules (safety first)
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from .schemas import (
    ConflictReport,
    ConflictSeverity,
)


class ConflictResolver:
    """
    Resolves conflicts between agents using Constitution-based rules.

    Resolution order:
    1. CRITICAL conflicts → immediate supervisor escalation
    2. HIGH conflicts → Constitution rules (safety > ethics > efficiency)
    3. MEDIUM conflicts → KARMA-weighted resolution
    4. LOW conflicts → first-come-first-served
    """

    # Constitutional priority: safety > ethics > efficiency > preference
    CONSTITUTION_PRIORITIES = [
        "safety",
        "ethics",
        "privacy",
        "efficiency",
        "preference",
    ]

    def __init__(self) -> None:
        self._conflicts: Dict[str, ConflictReport] = {}
        self._resolved_count = 0
        self._escalated_count = 0

        logger.info("⚖️ ConflictResolver initialized")

    # ------------------------------------------------------------------
    # Conflict reporting
    # ------------------------------------------------------------------

    def report_conflict(self, conflict: ConflictReport) -> ConflictReport:
        """Register a new conflict."""
        self._conflicts[conflict.conflict_id] = conflict
        logger.warning(
            "⚠️ Conflict reported: %s (severity=%s, agents=%s)",
            conflict.description,
            conflict.severity.value,
            conflict.agent_ids,
        )
        return conflict

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    async def resolve(
        self,
        conflict_id: str,
        agent_karma_scores: Optional[Dict[str, float]] = None,
    ) -> ConflictReport:
        """
        Resolve a conflict using Constitution-based strategy.

        Returns the updated ConflictReport with resolution details.
        """
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            raise ValueError(f"Conflict '{conflict_id}' not found")

        if conflict.resolution:
            return conflict  # Already resolved

        # Strategy selection based on severity
        if conflict.severity == ConflictSeverity.CRITICAL:
            resolution = self._resolve_critical(conflict)
        elif conflict.severity == ConflictSeverity.HIGH:
            resolution = self._resolve_constitution(conflict)
        elif conflict.severity == ConflictSeverity.MEDIUM:
            resolution = self._resolve_karma(conflict, agent_karma_scores or {})
        else:
            resolution = self._resolve_default(conflict)

        conflict.resolution = resolution
        conflict.resolved_by = "conflict_resolver"
        conflict.resolved_at = datetime.utcnow()
        self._resolved_count += 1

        logger.info("✅ Conflict resolved: %s → %s", conflict_id, resolution)
        return conflict

    def _resolve_critical(self, conflict: ConflictReport) -> str:
        """CRITICAL: Escalate to supervisor, apply safety-first."""
        self._escalated_count += 1
        return (
            "ESCALATED: Critical conflict escalated to supervisor. "
            "Safety-first principle applied. All conflicting actions paused."
        )

    def _resolve_constitution(self, conflict: ConflictReport) -> str:
        """HIGH: Apply constitutional priority rules."""
        context = conflict.context
        category = context.get("category", "preference")

        # Find highest constitutional priority among conflict aspects
        for principle in self.CONSTITUTION_PRIORITIES:
            if principle in category or principle in conflict.description.lower():
                return (
                    f"CONSTITUTION: Resolved by '{principle}' principle. "
                    f"Constitutional priority applied to agents {conflict.agent_ids}."
                )

        return (
            "CONSTITUTION: No specific principle matched. "
            "Defaulting to safety-first resolution."
        )

    def _resolve_karma(
        self,
        conflict: ConflictReport,
        karma_scores: Dict[str, float],
    ) -> str:
        """MEDIUM: Agent with higher KARMA prevails."""
        if not karma_scores:
            return self._resolve_default(conflict)

        scored = [
            (aid, karma_scores.get(aid, 50.0))
            for aid in conflict.agent_ids
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        winner = scored[0][0]
        winner_score = scored[0][1]

        return (
            f"KARMA: Agent '{winner}' prevails (karma={winner_score:.1f}). "
            f"Higher KARMA score used as tiebreaker."
        )

    def _resolve_default(self, conflict: ConflictReport) -> str:
        """LOW: First agent in list gets priority."""
        winner = conflict.agent_ids[0] if conflict.agent_ids else "unknown"
        return f"DEFAULT: Agent '{winner}' given priority (first-come-first-served)."

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_conflict(self, conflict_id: str) -> Optional[ConflictReport]:
        return self._conflicts.get(conflict_id)

    def list_conflicts(
        self,
        resolved: Optional[bool] = None,
        severity: Optional[ConflictSeverity] = None,
    ) -> List[ConflictReport]:
        conflicts = list(self._conflicts.values())
        if resolved is not None:
            if resolved:
                conflicts = [c for c in conflicts if c.resolution is not None]
            else:
                conflicts = [c for c in conflicts if c.resolution is None]
        if severity:
            conflicts = [c for c in conflicts if c.severity == severity]
        return conflicts

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def stats(self) -> Dict:
        unresolved = sum(1 for c in self._conflicts.values() if c.resolution is None)
        return {
            "total_conflicts": len(self._conflicts),
            "resolved": self._resolved_count,
            "escalated": self._escalated_count,
            "unresolved": unresolved,
        }
