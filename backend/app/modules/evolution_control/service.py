from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.core.control_plane_events import record_control_plane_event
from app.core.control_plane_events import ControlPlaneEventModel
from app.modules.safe_mode.service import get_safe_mode_service
from app.modules.skill_engine.service import get_skill_engine_service
from app.modules.skill_evaluator.service import get_skill_evaluator_service
from app.modules.consolidation_layer.service import get_consolidation_layer_service

from .models import EvolutionControlFlagModel, EvolutionProposalModel


_ALLOWED_STATUSES = {
    "draft",
    "review",
    "approved",
    "rejected",
    "applied",
    "rolled_back",
}
_ALLOWED_TRANSITIONS = {
    "draft": {"review", "rejected"},
    "review": {"approved", "rejected"},
    "approved": {"applied", "rolled_back"},
    "rejected": set(),
    "applied": {"rolled_back"},
    "rolled_back": set(),
}


class EvolutionControlService:
    @staticmethod
    def _metadata(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}

    @staticmethod
    def _queue_ranking_score(metadata: dict[str, Any]) -> float:
        economy_score = float(metadata.get("economy_weighted_score", 0.0) or 0.0)
        discovery_score = float(metadata.get("discovery_priority_score", 0.0) or 0.0)
        pattern_confidence = float(metadata.get("pattern_confidence", 0.0) or 0.0)
        return round(
            (economy_score * 0.5)
            + (discovery_score * 0.3)
            + (pattern_confidence * 0.2),
            3,
        )

    async def get_by_id(
        self, db: AsyncSession, proposal_id, tenant_id: str
    ) -> EvolutionProposalModel | None:
        query = select(EvolutionProposalModel).where(
            EvolutionProposalModel.id == proposal_id,
            EvolutionProposalModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_by_pattern_id(
        self, db: AsyncSession, pattern_id, tenant_id: str
    ) -> EvolutionProposalModel | None:
        query = select(EvolutionProposalModel).where(
            EvolutionProposalModel.pattern_id == pattern_id,
            EvolutionProposalModel.tenant_id == tenant_id,
        )
        result = await db.execute(
            query.order_by(EvolutionProposalModel.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_review_queue(
        self, db: AsyncSession, tenant_id: str, limit: int = 50
    ) -> list[tuple[EvolutionProposalModel, float]]:
        query = select(EvolutionProposalModel).where(
            EvolutionProposalModel.tenant_id == tenant_id,
            EvolutionProposalModel.status.in_(["draft", "review", "approved"]),
        )
        query = query.order_by(desc(EvolutionProposalModel.updated_at)).limit(limit)
        result = await db.execute(query)
        items = list(result.scalars().all())
        scored = [
            (
                item,
                self._queue_ranking_score(
                    self._metadata(getattr(item, "proposal_metadata", {}))
                ),
            )
            for item in items
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored

    async def get_ops_summary(self, db: AsyncSession, tenant_id: str) -> dict[str, Any]:
        counts_query = (
            select(EvolutionProposalModel.status, func.count(EvolutionProposalModel.id))
            .where(EvolutionProposalModel.tenant_id == tenant_id)
            .group_by(EvolutionProposalModel.status)
        )
        result = await db.execute(counts_query)
        proposal_counts = {status: int(count) for status, count in result.all()}

        events_query = (
            select(ControlPlaneEventModel)
            .where(
                ControlPlaneEventModel.tenant_id == tenant_id,
                ControlPlaneEventModel.event_type.like("learning.%"),
            )
            .order_by(ControlPlaneEventModel.created_at.desc())
            .limit(20)
        )
        events_result = await db.execute(events_query)
        recent_events = []
        for row in events_result.scalars().all():
            recent_events.append(
                {
                    "event_type": row.event_type,
                    "entity_type": row.entity_type,
                    "entity_id": row.entity_id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "payload": row.payload,
                }
            )

        freeze = await self.get_freeze_status(db, tenant_id)
        review_queue_count = proposal_counts.get("review", 0) + proposal_counts.get("approved", 0)
        return {
            "tenant_id": tenant_id,
            "adaptive_frozen": freeze.adaptive_frozen == "true",
            "proposal_counts": proposal_counts,
            "review_queue_count": review_queue_count,
            "blocked_count": proposal_counts.get("rejected", 0),
            "applied_count": proposal_counts.get("applied", 0),
            "recent_events": recent_events,
        }

    async def get_freeze_status(self, db: AsyncSession, tenant_id: str) -> EvolutionControlFlagModel:
        query = select(EvolutionControlFlagModel).where(EvolutionControlFlagModel.tenant_id == tenant_id)
        result = await db.execute(query.limit(1))
        if hasattr(result, "scalar_one_or_none"):
            item = result.scalar_one_or_none()
        else:
            item = None
        if item is not None:
            return item
        item = EvolutionControlFlagModel(tenant_id=tenant_id, adaptive_frozen="false")
        if not hasattr(db, "add"):
            return item
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    async def set_adaptive_freeze(
        self,
        db: AsyncSession,
        tenant_id: str,
        principal: Principal,
        *,
        enabled: bool,
        reason: str,
    ) -> EvolutionControlFlagModel:
        item = await self.get_freeze_status(db, tenant_id)
        item.adaptive_frozen = "true" if enabled else "false"
        item.freeze_reason = reason
        item.frozen_by = principal.principal_id if enabled else None
        item.frozen_at = datetime.now(timezone.utc) if enabled else None
        item.updated_at = datetime.now(timezone.utc)
        await record_control_plane_event(
            db=db,
            tenant_id=tenant_id,
            entity_type="evolution_control",
            entity_id=tenant_id,
            event_type="evolution.adaptive_freeze.changed.v1",
            correlation_id=None,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={"adaptive_frozen": enabled, "reason": reason},
            audit_required=True,
            audit_action="evolution_adaptive_freeze_toggle",
            audit_message="Adaptive freeze state changed",
            severity="warning" if enabled else "info",
        )
        await db.commit()
        await db.refresh(item)
        return item

    async def create_from_pattern(
        self,
        db: AsyncSession,
        pattern_id,
        principal: Principal,
        *,
        commit: bool = True,
    ) -> EvolutionProposalModel:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")

        existing = await self.get_by_pattern_id(db, pattern_id, principal.tenant_id)
        if existing is not None:
            return existing

        pattern = await get_consolidation_layer_service().get_by_id(
            db, pattern_id, principal.tenant_id
        )
        if pattern is None:
            raise ValueError("Pattern candidate not found")

        insight_evidence = pattern.evidence.get("insight_evidence", {})
        signals = (
            insight_evidence.get("signals", {})
            if isinstance(insight_evidence, dict)
            else {}
        )
        skill_key = str(signals.get("skill_key", "unknown"))

        proposal = EvolutionProposalModel(
            tenant_id=principal.tenant_id,
            pattern_id=pattern.id,
            skill_run_id=pattern.skill_run_id,
            status="draft",
            target_skill_key=skill_key,
            summary=f"Evolution proposal from pattern {pattern.id} for {skill_key}",
            governance_required="true",
            validation_state="required",
            proposal_metadata={
                "pattern_confidence": pattern.confidence,
                "pattern_recurrence_support": pattern.recurrence_support,
                "failure_modes": pattern.failure_modes,
            },
            updated_at=datetime.now(timezone.utc),
        )
        db.add(proposal)
        try:
            if commit:
                await db.commit()
            else:
                await db.flush()
        except IntegrityError:
            await db.rollback()
            existing_after_race = await self.get_by_pattern_id(
                db, pattern_id, principal.tenant_id
            )
            if existing_after_race is not None:
                return existing_after_race
            raise
        await db.refresh(proposal)
        return proposal

    async def create_from_skill_run(
        self,
        db: AsyncSession,
        skill_run_id,
        principal: Principal,
    ) -> tuple[EvolutionProposalModel, bool, str | None]:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")

        run = await get_skill_engine_service().get_run(db, skill_run_id, principal.tenant_id)
        if run is None:
            raise ValueError("Skill run not found")

        evaluation = await get_skill_evaluator_service().get_latest_for_run(db, run.id, principal.tenant_id)
        if evaluation is None:
            raise ValueError("Evaluation result not found")

        await record_control_plane_event(
            db=db,
            tenant_id=principal.tenant_id,
            entity_type="skill_run",
            entity_id=str(run.id),
            event_type="learning.observation.captured.v1",
            correlation_id=run.correlation_id,
            mission_id=run.mission_id,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={"state": run.state, "skill_key": run.skill_key, "skill_version": run.skill_version},
            audit_required=False,
        )
        await record_control_plane_event(
            db=db,
            tenant_id=principal.tenant_id,
            entity_type="evaluation_result",
            entity_id=str(evaluation.id),
            event_type="learning.evaluation.checked.v1",
            correlation_id=run.correlation_id,
            mission_id=run.mission_id,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "status": evaluation.status,
                "passed": evaluation.passed,
                "policy_compliance": evaluation.policy_compliance,
                "overall_score": evaluation.overall_score,
            },
            audit_required=False,
        )

        blocked = False
        block_reason: str | None = None
        if evaluation.status != "completed":
            blocked = True
            block_reason = "evaluation_not_completed"
        elif not bool(evaluation.passed):
            blocked = True
            block_reason = "evaluation_not_passed"
        elif evaluation.policy_compliance != "compliant":
            blocked = True
            block_reason = "policy_non_compliant"

        pattern = await get_consolidation_layer_service().derive_from_skill_run(db, run.id, principal)
        proposal = await self.create_from_pattern(db, pattern.id, principal, commit=False)

        metadata = self._metadata(getattr(proposal, "proposal_metadata", {}))
        metadata["learning_source"] = "skill_run"
        metadata["skill_run_id"] = str(run.id)
        metadata["evaluation_result_id"] = str(evaluation.id)
        metadata["policy_compliance"] = evaluation.policy_compliance
        metadata["evaluation_passed"] = bool(evaluation.passed)
        metadata["proposal_mode"] = "proposal_only"

        if blocked:
            proposal.status = "rejected"
            proposal.validation_state = "blocked"
            metadata["blocked"] = True
            metadata["block_reason"] = block_reason
            await record_control_plane_event(
                db=db,
                tenant_id=principal.tenant_id,
                entity_type="evolution_proposal",
                entity_id=str(proposal.id),
                event_type="learning.validation.completed.v1",
                correlation_id=run.correlation_id,
                mission_id=run.mission_id,
                actor_id=principal.principal_id,
                actor_type=principal.principal_type.value,
                payload={"blocked": True, "reason": block_reason},
                audit_required=True,
                audit_action="learning_validation_block",
                audit_message="Learning proposal blocked by validation gates",
                severity="warning",
            )
            await record_control_plane_event(
                db=db,
                tenant_id=principal.tenant_id,
                entity_type="evolution_proposal",
                entity_id=str(proposal.id),
                event_type="learning.promotion.decided.v1",
                correlation_id=run.correlation_id,
                mission_id=run.mission_id,
                actor_id=principal.principal_id,
                actor_type=principal.principal_type.value,
                payload={"decision": "blocked", "reason": block_reason, "status": proposal.status},
                audit_required=True,
                audit_action="learning_promotion_blocked",
                audit_message="Promotion decision blocked",
                severity="warning",
            )
        else:
            proposal.status = "review"
            proposal.validation_state = "validated"
            metadata["blocked"] = False
            await record_control_plane_event(
                db=db,
                tenant_id=principal.tenant_id,
                entity_type="evolution_proposal",
                entity_id=str(proposal.id),
                event_type="learning.validation.completed.v1",
                correlation_id=run.correlation_id,
                mission_id=run.mission_id,
                actor_id=principal.principal_id,
                actor_type=principal.principal_type.value,
                payload={"blocked": False, "reason": None},
                audit_required=False,
            )
            await record_control_plane_event(
                db=db,
                tenant_id=principal.tenant_id,
                entity_type="evolution_proposal",
                entity_id=str(proposal.id),
                event_type="learning.promotion.decided.v1",
                correlation_id=run.correlation_id,
                mission_id=run.mission_id,
                actor_id=principal.principal_id,
                actor_type=principal.principal_type.value,
                payload={"decision": "proposal_created", "status": proposal.status, "mode": "proposal_only"},
                audit_required=True,
                audit_action="learning_promotion_proposed",
                audit_message="Promotion candidate queued for review",
            )

        proposal.proposal_metadata = metadata
        proposal.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(proposal)
        return proposal, blocked, block_reason

    async def transition_status(
        self,
        db: AsyncSession,
        proposal_id,
        principal: Principal,
        new_status: str,
        metadata_patch: dict[str, Any] | None = None,
    ) -> EvolutionProposalModel:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")
        if new_status not in _ALLOWED_STATUSES:
            raise ValueError("Invalid proposal status")

        proposal = await self.get_by_id(db, proposal_id, principal.tenant_id)
        if proposal is None:
            raise ValueError("Evolution proposal not found")

        if new_status not in _ALLOWED_TRANSITIONS.get(proposal.status, set()):
            raise ValueError("Invalid proposal transition")

        metadata = self._metadata(getattr(proposal, "proposal_metadata", {}))
        if metadata_patch:
            metadata.update(metadata_patch)

        freeze_active = False
        if db is not None:
            freeze = await self.get_freeze_status(db, principal.tenant_id)
            freeze_active = freeze.adaptive_frozen == "true"
        if new_status == "applied" and freeze_active:
            raise ValueError("Adaptive freeze active; apply blocked")

        if new_status == "applied" and get_safe_mode_service().is_safe_mode_enabled():
            raise ValueError("Safe mode active; apply blocked")

        if new_status == "applied":
            if proposal.governance_required == "true":
                required_refs = {"approval_id", "policy_decision_id", "reviewer_id"}
                if not required_refs.issubset(set(metadata.keys())):
                    raise ValueError("Governance evidence required before apply")
            if proposal.validation_state != "validated":
                raise ValueError("Validation state must be 'validated' before apply")
            rollback_required = {"rollback_plan_id", "rollback_steps", "rollback_owner"}
            if not rollback_required.issubset(set(metadata.keys())):
                raise ValueError("Rollback plan metadata required before apply")

        transitions = list(metadata.get("transitions", []))
        transitions.append(
            {
                "from": proposal.status,
                "to": new_status,
                "actor": principal.principal_id,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        metadata["transitions"] = transitions

        proposal.status = new_status
        proposal.proposal_metadata = metadata
        proposal.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(proposal)
        return proposal


_evolution_control_service: EvolutionControlService | None = None


def get_evolution_control_service() -> EvolutionControlService:
    global _evolution_control_service
    if _evolution_control_service is None:
        _evolution_control_service = EvolutionControlService()
    return _evolution_control_service
