"""
Governor Decision Store (Phase 2).

Persists governance decisions to database with:
- Immutable append-only storage
- Query by mission/job/manifest
- Statistics aggregation
- Audit trail integration
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.governor.decision.models import (
    GovernorDecision,
    DecisionStatistics,
    DecisionQuery,
)
from backend.app.modules.neurorail.errors import NeuroRailErrorCode


class DecisionStore:
    """
    Persistent storage for governance decisions.

    Responsibilities:
    - Store decisions (append-only, immutable)
    - Query decisions by various criteria
    - Generate statistics
    - Integration with audit trail
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize decision store.

        Args:
            db: Async database session
        """
        self.db = db

    # ========================================================================
    # CRUD Operations
    # ========================================================================

    async def create(self, decision: GovernorDecision) -> GovernorDecision:
        """
        Store decision in database.

        Args:
            decision: Decision to store

        Returns:
            Stored decision
        """
        logger.debug(
            f"Storing decision: {decision.decision_id} "
            f"({decision.job_type}, mode={decision.mode})"
        )

        query = text("""
            INSERT INTO governor_decisions
                (decision_id, timestamp, mission_id, plan_id, job_id, job_type,
                 mode, budget_resolution, recovery_strategy,
                 manifest_id, manifest_version, triggered_rules,
                 reason, shadow_mode, evidence,
                 immune_alert_required, health_impact,
                 created_at)
            VALUES
                (:decision_id, :timestamp, :mission_id, :plan_id, :job_id, :job_type,
                 :mode, :budget_resolution, :recovery_strategy,
                 :manifest_id, :manifest_version, :triggered_rules,
                 :reason, :shadow_mode, :evidence,
                 :immune_alert_required, :health_impact,
                 NOW())
        """)

        import json
        await self.db.execute(query, {
            "decision_id": decision.decision_id,
            "timestamp": decision.timestamp,
            "mission_id": decision.mission_id,
            "plan_id": decision.plan_id,
            "job_id": decision.job_id,
            "job_type": decision.job_type,
            "mode": decision.mode,
            "budget_resolution": json.dumps(decision.budget_resolution.model_dump()),
            "recovery_strategy": decision.recovery_strategy,
            "manifest_id": decision.manifest_id,
            "manifest_version": decision.manifest_version,
            "triggered_rules": json.dumps(decision.triggered_rules),
            "reason": decision.reason,
            "shadow_mode": decision.shadow_mode,
            "evidence": json.dumps(decision.evidence) if decision.evidence else None,
            "immune_alert_required": decision.immune_alert_required,
            "health_impact": decision.health_impact,
        })
        await self.db.commit()

        logger.info(
            f"Decision stored: {decision.decision_id} "
            f"(manifest={decision.manifest_version})"
        )

        return decision

    async def get(self, decision_id: str) -> Optional[GovernorDecision]:
        """
        Get decision by ID.

        Args:
            decision_id: Decision ID

        Returns:
            Decision, or None if not found
        """
        query = text("""
            SELECT decision_id, timestamp, mission_id, plan_id, job_id, job_type,
                   mode, budget_resolution, recovery_strategy,
                   manifest_id, manifest_version, triggered_rules,
                   reason, shadow_mode, evidence,
                   immune_alert_required, health_impact
            FROM governor_decisions
            WHERE decision_id = :decision_id
        """)

        result = await self.db.execute(query, {"decision_id": decision_id})
        row = result.fetchone()

        if not row:
            return None

        return self._row_to_decision(row)

    async def query(self, q: DecisionQuery) -> List[GovernorDecision]:
        """
        Query decisions by criteria.

        Args:
            q: Query parameters

        Returns:
            List of matching decisions
        """
        # Build WHERE clause
        conditions = []
        params: Dict[str, Any] = {}

        if q.mission_id:
            conditions.append("mission_id = :mission_id")
            params["mission_id"] = q.mission_id

        if q.job_id:
            conditions.append("job_id = :job_id")
            params["job_id"] = q.job_id

        if q.job_type:
            conditions.append("job_type = :job_type")
            params["job_type"] = q.job_type

        if q.mode:
            conditions.append("mode = :mode")
            params["mode"] = q.mode

        if q.manifest_version:
            conditions.append("manifest_version = :manifest_version")
            params["manifest_version"] = q.manifest_version

        if q.recovery_strategy:
            conditions.append("recovery_strategy = :recovery_strategy")
            params["recovery_strategy"] = q.recovery_strategy

        if q.shadow_mode is not None:
            conditions.append("shadow_mode = :shadow_mode")
            params["shadow_mode"] = q.shadow_mode

        if q.start_time:
            conditions.append("timestamp >= :start_time")
            params["start_time"] = q.start_time

        if q.end_time:
            conditions.append("timestamp <= :end_time")
            params["end_time"] = q.end_time

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Execute query
        query_text = text(f"""
            SELECT decision_id, timestamp, mission_id, plan_id, job_id, job_type,
                   mode, budget_resolution, recovery_strategy,
                   manifest_id, manifest_version, triggered_rules,
                   reason, shadow_mode, evidence,
                   immune_alert_required, health_impact
            FROM governor_decisions
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """)

        params["limit"] = q.limit
        params["offset"] = q.offset

        result = await self.db.execute(query_text, params)
        rows = result.fetchall()

        return [self._row_to_decision(row) for row in rows]

    # ========================================================================
    # Statistics
    # ========================================================================

    async def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> DecisionStatistics:
        """
        Get decision statistics.

        Args:
            start_time: Filter by start time
            end_time: Filter by end time

        Returns:
            Decision statistics
        """
        # Build time filter
        time_filter = "1=1"
        params: Dict[str, Any] = {}

        if start_time:
            time_filter += " AND timestamp >= :start_time"
            params["start_time"] = start_time

        if end_time:
            time_filter += " AND timestamp <= :end_time"
            params["end_time"] = end_time

        # Total decisions
        query_total = text(f"""
            SELECT COUNT(*) FROM governor_decisions WHERE {time_filter}
        """)
        total = (await self.db.execute(query_total, params)).scalar()

        # Decisions by mode
        query_by_mode = text(f"""
            SELECT mode, COUNT(*) FROM governor_decisions
            WHERE {time_filter}
            GROUP BY mode
        """)
        by_mode_rows = (await self.db.execute(query_by_mode, params)).fetchall()
        decisions_by_mode = {row[0]: row[1] for row in by_mode_rows}

        # Decisions by manifest
        query_by_manifest = text(f"""
            SELECT manifest_version, COUNT(*) FROM governor_decisions
            WHERE {time_filter}
            GROUP BY manifest_version
        """)
        by_manifest_rows = (await self.db.execute(query_by_manifest, params)).fetchall()
        decisions_by_manifest = {row[0]: row[1] for row in by_manifest_rows}

        # Decisions by recovery
        query_by_recovery = text(f"""
            SELECT recovery_strategy, COUNT(*) FROM governor_decisions
            WHERE {time_filter}
            GROUP BY recovery_strategy
        """)
        by_recovery_rows = (await self.db.execute(query_by_recovery, params)).fetchall()
        decisions_by_recovery = {row[0]: row[1] for row in by_recovery_rows}

        # Immune alerts
        query_immune = text(f"""
            SELECT COUNT(*) FROM governor_decisions
            WHERE {time_filter} AND immune_alert_required = TRUE
        """)
        immune_alerts = (await self.db.execute(query_immune, params)).scalar()

        return DecisionStatistics(
            total_decisions=total or 0,
            decisions_by_mode=decisions_by_mode,
            decisions_by_manifest=decisions_by_manifest,
            decisions_by_recovery=decisions_by_recovery,
            rule_trigger_counts={},  # TODO: Extract from triggered_rules JSON
            average_decision_time_ms=0.0,  # TODO: Track decision eval time
            immune_alerts_triggered=immune_alerts or 0,
        )

    # ========================================================================
    # Helpers
    # ========================================================================

    def _row_to_decision(self, row: Any) -> GovernorDecision:
        """
        Convert database row to decision.

        Args:
            row: Database row

        Returns:
            GovernorDecision
        """
        import json
        from backend.app.modules.governor.decision.models import BudgetResolution

        budget_resolution_data = json.loads(row[7])  # budget_resolution column
        triggered_rules_data = json.loads(row[11])  # triggered_rules column
        evidence_data = json.loads(row[14]) if row[14] else {}  # evidence column

        return GovernorDecision(
            decision_id=row[0],
            timestamp=row[1],
            mission_id=row[2],
            plan_id=row[3],
            job_id=row[4],
            job_type=row[5],
            mode=row[6],
            budget_resolution=BudgetResolution(**budget_resolution_data),
            recovery_strategy=row[8],
            manifest_id=row[9],
            manifest_version=row[10],
            triggered_rules=triggered_rules_data,
            reason=row[12],
            shadow_mode=row[13],
            evidence=evidence_data,
            immune_alert_required=row[15],
            health_impact=row[16],
        )


# ============================================================================
# Singleton Helper
# ============================================================================

def get_decision_store(db: AsyncSession) -> DecisionStore:
    """Get decision store instance (scoped to DB session)."""
    return DecisionStore(db)
