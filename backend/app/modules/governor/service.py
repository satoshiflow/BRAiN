"""
Governor Service (Phase 1 Stub).

Provides minimal governance for mode decision:
- Direct vs. Rail mode selection
- Dry-run logging (no enforcement)
- Shadow evaluation hooks

Phase 1: Observation only, mode decision logged but not enforced
Phase 2: Full budget enforcement, manifest-driven governance
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.governor.schemas import (
    ModeDecision,
    ManifestSpec,
    ShadowEvaluation,
    DecisionRequest,
)


class GovernorService:
    """
    Minimal Governor service for Phase 1.

    Responsibilities:
    - Decide execution mode (direct vs. rail)
    - Log decisions to audit (dry-run)
    - Shadow evaluation (compare manifest versions)

    Phase 1: Decisions logged but NOT enforced
    Phase 2: Full enforcement with budget checks
    """

    # Default mode selection rules (hard-coded for Phase 1)
    DEFAULT_RULES = [
        {
            "condition": {"job_type": "llm_call"},
            "mode": "rail",
            "reason": "LLM calls require governance for token tracking"
        },
        {
            "condition": {"uses_personal_data": True},
            "mode": "rail",
            "reason": "Personal data processing requires governance (DSGVO Art. 25)"
        },
        {
            "condition": {"environment": "production"},
            "mode": "rail",
            "reason": "Production deployments require governance"
        },
        {
            "condition": {},  # Default fallback
            "mode": "direct",
            "reason": "Default: low-risk operations use direct execution"
        }
    ]

    def __init__(self):
        self.active_manifest = ManifestSpec(
            name="default_phase1",
            description="Default Phase 1 manifest (hard-coded rules)",
            mode_rules=self.DEFAULT_RULES
        )
        self.shadow_manifest: Optional[ManifestSpec] = None

    # ========================================================================
    # Mode Decision
    # ========================================================================

    async def decide_mode(
        self,
        request: DecisionRequest,
        db: AsyncSession
    ) -> ModeDecision:
        """
        Decide execution mode for a job.

        Args:
            request: Decision request with job context
            db: Database session for logging

        Returns:
            Mode decision (direct or rail)
        """
        # Evaluate active manifest
        mode, reason, matched_rules = self._evaluate_manifest(
            self.active_manifest,
            request.job_type,
            request.context
        )

        # Create decision
        decision = ModeDecision(
            mode=mode,
            reason=reason,
            mission_id=request.mission_id,
            job_id=request.job_id,
            job_type=request.job_type,
            matched_rules=matched_rules,
            evidence=request.context,
            shadow_mode=False
        )

        # Log decision to PostgreSQL
        await self._log_decision(decision, db)

        # Shadow evaluation (if requested)
        if request.shadow_evaluate and self.shadow_manifest:
            await self._evaluate_shadow(request, decision, db)

        logger.info(
            f"Governor decision: mode={mode} for {request.job_type} "
            f"(reason: {reason}) [PHASE 1: NOT ENFORCED]"
        )

        return decision

    def _evaluate_manifest(
        self,
        manifest: ManifestSpec,
        job_type: str,
        context: Dict[str, Any]
    ) -> tuple[str, str, List[str]]:
        """
        Evaluate manifest rules to determine mode.

        Returns:
            (mode, reason, matched_rule_ids)
        """
        matched_rules = []

        for idx, rule in enumerate(manifest.mode_rules):
            condition = rule.get("condition", {})

            # Check if all conditions match
            if self._matches_condition(condition, job_type, context):
                matched_rules.append(f"rule_{idx}")
                return rule["mode"], rule["reason"], matched_rules

        # Fallback: direct mode
        return "direct", "No matching rules - default to direct", []

    def _matches_condition(
        self,
        condition: Dict[str, Any],
        job_type: str,
        context: Dict[str, Any]
    ) -> bool:
        """Check if condition matches job context."""
        # Empty condition matches everything (fallback rule)
        if not condition:
            return True

        # Check job_type
        if "job_type" in condition and condition["job_type"] != job_type:
            return False

        # Check context fields
        for key, expected_value in condition.items():
            if key == "job_type":
                continue  # Already checked

            if key not in context or context[key] != expected_value:
                return False

        return True

    async def _log_decision(
        self,
        decision: ModeDecision,
        db: AsyncSession
    ) -> None:
        """Log governance decision to PostgreSQL."""
        query = text("""
            INSERT INTO governor_decisions
                (decision_id, timestamp, decision_type, context, allowed, reason,
                 actions, mission_id, job_id, manifest_version, shadow_mode, created_at)
            VALUES
                (:decision_id, :timestamp, 'mode_decision', :context, TRUE, :reason,
                 NULL, :mission_id, :job_id, :manifest_version, :shadow_mode, NOW())
        """)

        import json
        await db.execute(query, {
            "decision_id": decision.decision_id,
            "timestamp": decision.timestamp,
            "context": json.dumps({
                "mode": decision.mode,
                "job_type": decision.job_type,
                "matched_rules": decision.matched_rules,
                "evidence": decision.evidence
            }),
            "reason": decision.reason,
            "mission_id": decision.mission_id,
            "job_id": decision.job_id,
            "manifest_version": self.active_manifest.version,
            "shadow_mode": decision.shadow_mode
        })
        await db.commit()

    # ========================================================================
    # Shadow Evaluation
    # ========================================================================

    async def _evaluate_shadow(
        self,
        request: DecisionRequest,
        active_decision: ModeDecision,
        db: AsyncSession
    ) -> ShadowEvaluation:
        """
        Evaluate what shadow manifest would have decided.

        Args:
            request: Original request
            active_decision: Decision from active manifest
            db: Database session

        Returns:
            Shadow evaluation result
        """
        if not self.shadow_manifest:
            return None

        # Evaluate shadow manifest
        shadow_mode, shadow_reason, _ = self._evaluate_manifest(
            self.shadow_manifest,
            request.job_type,
            request.context
        )

        # Compare decisions
        delta = (shadow_mode != active_decision.mode)

        evaluation = ShadowEvaluation(
            active_version=self.active_manifest.version,
            shadow_version=self.shadow_manifest.version,
            active_mode=active_decision.mode,
            shadow_mode=shadow_mode,
            delta=delta,
            mission_id=request.mission_id,
            job_id=request.job_id,
            job_type=request.job_type,
            impact_assessment=f"Shadow would have chosen {shadow_mode} instead of {active_decision.mode}"
                               if delta else "No difference"
        )

        # Log shadow evaluation
        logger.info(
            f"Shadow evaluation: active={active_decision.mode}, shadow={shadow_mode}, "
            f"delta={delta}"
        )

        return evaluation

    # ========================================================================
    # Manifest Management (Phase 2)
    # ========================================================================

    def set_shadow_manifest(self, manifest: ManifestSpec) -> None:
        """
        Set shadow manifest for evaluation.

        Args:
            manifest: Shadow manifest to evaluate against
        """
        self.shadow_manifest = manifest
        logger.info(f"Shadow manifest set: {manifest.name} v{manifest.version}")


# Singleton instance
_governor_service: Optional[GovernorService] = None


def get_governor_service() -> GovernorService:
    """Get singleton governor service instance."""
    global _governor_service
    if _governor_service is None:
        _governor_service = GovernorService()
    return _governor_service
