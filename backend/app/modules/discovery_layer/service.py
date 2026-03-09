from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import String, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.consolidation_layer.service import get_consolidation_layer_service
from app.modules.evolution_control.service import get_evolution_control_service
from app.modules.knowledge_layer.models import KnowledgeItemModel
from app.modules.observer_core.models import ObserverSignalModel

from .models import CapabilityGapModel, SkillGapModel, SkillProposalModel


def _dict_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


class DiscoveryLayerService:
    _MIN_PATTERN_CONFIDENCE = 0.55
    _MIN_RECURRENCE_SUPPORT = 0.45
    _MIN_OBSERVER_SIGNALS = 1
    _MIN_KNOWLEDGE_ITEMS = 1

    async def get_proposal_by_id(
        self, db: AsyncSession, proposal_id, tenant_id: str
    ) -> SkillProposalModel | None:
        query = select(SkillProposalModel).where(
            SkillProposalModel.id == proposal_id,
            SkillProposalModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def list_proposals(
        self,
        db: AsyncSession,
        tenant_id: str,
        *,
        status_filter: str | None = None,
        limit: int = 50,
    ) -> list[SkillProposalModel]:
        query = select(SkillProposalModel).where(
            SkillProposalModel.tenant_id == tenant_id
        )
        if status_filter:
            query = query.where(SkillProposalModel.status == status_filter)
        query = query.order_by(
            desc(SkillProposalModel.priority_score), desc(SkillProposalModel.updated_at)
        ).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_observer_signals(
        self, db: AsyncSession, tenant_id: str, skill_run_id
    ) -> int:
        query = (
            select(func.count())
            .select_from(ObserverSignalModel)
            .where(
                ObserverSignalModel.tenant_id == tenant_id,
                ObserverSignalModel.entity_id == str(skill_run_id),
            )
        )
        result = await db.execute(query)
        return int(result.scalar_one() or 0)

    async def count_knowledge_items(
        self, db: AsyncSession, tenant_id: str, skill_run_id
    ) -> int:
        run_token = str(skill_run_id)
        query = (
            select(func.count())
            .select_from(KnowledgeItemModel)
            .where(
                KnowledgeItemModel.tenant_id == tenant_id,
                KnowledgeItemModel.provenance_refs.cast(String).ilike(f"%{run_token}%"),
            )
        )
        result = await db.execute(query)
        return int(result.scalar_one() or 0)

    def _thresholds(self) -> dict[str, float | int]:
        return {
            "min_pattern_confidence": self._MIN_PATTERN_CONFIDENCE,
            "min_recurrence_support": self._MIN_RECURRENCE_SUPPORT,
            "min_observer_signals": self._MIN_OBSERVER_SIGNALS,
            "min_knowledge_items": self._MIN_KNOWLEDGE_ITEMS,
        }

    def _compute_evidence_score(
        self,
        *,
        confidence: float,
        recurrence_support: float,
        observer_signal_count: int,
        knowledge_item_count: int,
    ) -> float:
        observer_score = min(1.0, observer_signal_count / 5)
        knowledge_score = min(1.0, knowledge_item_count / 5)
        return round(
            (confidence * 0.4)
            + (recurrence_support * 0.3)
            + (observer_score * 0.2)
            + (knowledge_score * 0.1),
            3,
        )

    def _thresholds_met(
        self,
        *,
        confidence: float,
        recurrence_support: float,
        observer_signal_count: int,
        knowledge_item_count: int,
    ) -> bool:
        return (
            confidence >= self._MIN_PATTERN_CONFIDENCE
            and recurrence_support >= self._MIN_RECURRENCE_SUPPORT
            and observer_signal_count >= self._MIN_OBSERVER_SIGNALS
            and knowledge_item_count >= self._MIN_KNOWLEDGE_ITEMS
        )

    async def analyze_skill_run(
        self, db: AsyncSession, skill_run_id, principal: Principal
    ) -> tuple[SkillGapModel, CapabilityGapModel, SkillProposalModel, dict[str, Any]]:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")

        existing_query = select(SkillProposalModel).where(
            SkillProposalModel.tenant_id == principal.tenant_id,
            SkillProposalModel.skill_run_id == skill_run_id,
        )
        existing_result = await db.execute(
            existing_query.order_by(SkillProposalModel.created_at.desc()).limit(1)
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            skill_gap = await db.execute(
                select(SkillGapModel)
                .where(
                    SkillGapModel.id == existing.skill_gap_id,
                    SkillGapModel.tenant_id == principal.tenant_id,
                )
                .limit(1)
            )
            capability_gap = await db.execute(
                select(CapabilityGapModel)
                .where(
                    CapabilityGapModel.id == existing.capability_gap_id,
                    CapabilityGapModel.tenant_id == principal.tenant_id,
                )
                .limit(1)
            )
            skill_gap_item = skill_gap.scalar_one_or_none()
            capability_gap_item = capability_gap.scalar_one_or_none()
            if skill_gap_item is None or capability_gap_item is None:
                raise ValueError("Discovery proposal linked gaps not found")
            return (
                skill_gap_item,
                capability_gap_item,
                existing,
                _dict_payload(getattr(existing, "proposal_evidence", {})),
            )

        pattern = await get_consolidation_layer_service().get_by_skill_run_id(
            db, skill_run_id, principal.tenant_id
        )
        if pattern is None:
            raise ValueError("Pattern candidate not found")

        pattern_item = cast(Any, pattern)
        pattern_confidence = float(getattr(pattern_item, "confidence", 0.0) or 0.0)
        recurrence_support = float(
            getattr(pattern_item, "recurrence_support", 0.0) or 0.0
        )

        observer_signal_count = await self.count_observer_signals(
            db, principal.tenant_id, skill_run_id
        )
        knowledge_item_count = await self.count_knowledge_items(
            db, principal.tenant_id, skill_run_id
        )
        if not self._thresholds_met(
            confidence=pattern_confidence,
            recurrence_support=recurrence_support,
            observer_signal_count=observer_signal_count,
            knowledge_item_count=knowledge_item_count,
        ):
            raise ValueError("Discovery evidence thresholds not met")

        pattern_evidence = _dict_payload(getattr(pattern_item, "evidence", {}))
        insight_evidence = _dict_payload(pattern_evidence.get("insight_evidence", {}))
        signals = _dict_payload(insight_evidence.get("signals", {}))
        target_skill_key = str(signals.get("skill_key", "unknown"))

        evidence_score = self._compute_evidence_score(
            confidence=pattern_confidence,
            recurrence_support=recurrence_support,
            observer_signal_count=observer_signal_count,
            knowledge_item_count=knowledge_item_count,
        )
        priority_score = round(
            min(1.0, (evidence_score * 0.75) + (recurrence_support * 0.25)), 3
        )
        dedup_key = f"{skill_run_id}:{target_skill_key}"

        skill_gap = SkillGapModel(
            tenant_id=principal.tenant_id,
            skill_run_id=pattern_item.skill_run_id,
            pattern_id=pattern_item.id,
            gap_type="skill",
            summary=f"Skill gap detected for {target_skill_key}",
            severity="medium",
            confidence=pattern_confidence,
            evidence={
                "pattern_id": str(pattern_item.id),
                "pattern_summary": pattern_item.pattern_summary,
            },
        )
        db.add(skill_gap)
        await db.flush()

        capability_gap = CapabilityGapModel(
            tenant_id=principal.tenant_id,
            skill_run_id=pattern_item.skill_run_id,
            pattern_id=pattern_item.id,
            capability_key=target_skill_key,
            summary=f"Capability gap indicates improvement opportunity for {target_skill_key}",
            severity="medium",
            confidence=recurrence_support,
            evidence={"failure_modes": getattr(pattern_item, "failure_modes", [])},
        )
        db.add(capability_gap)
        await db.flush()

        proposal_evidence: dict[str, Any] = {
            "skill_gap_id": str(skill_gap.id),
            "capability_gap_id": str(capability_gap.id),
            "pattern_id": str(pattern_item.id),
            "evidence_sources": ["consolidation", "knowledge", "observer"],
            "observer_signal_count": observer_signal_count,
            "knowledge_item_count": knowledge_item_count,
            "thresholds": self._thresholds(),
            "evidence_score": evidence_score,
        }

        proposal = SkillProposalModel(
            tenant_id=principal.tenant_id,
            skill_run_id=pattern_item.skill_run_id,
            pattern_id=pattern_item.id,
            skill_gap_id=skill_gap.id,
            capability_gap_id=capability_gap.id,
            target_skill_key=target_skill_key,
            status="draft",
            proposal_summary=f"Propose refinement for {target_skill_key} based on consolidated pattern",
            proposal_evidence=proposal_evidence,
            dedup_key=dedup_key,
            evidence_score=evidence_score,
            priority_score=priority_score,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(proposal)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            existing_after_race = await db.execute(
                select(SkillProposalModel)
                .where(
                    SkillProposalModel.tenant_id == principal.tenant_id,
                    SkillProposalModel.skill_run_id == skill_run_id,
                )
                .order_by(SkillProposalModel.created_at.desc())
                .limit(1)
            )
            existing = existing_after_race.scalar_one_or_none()
            if existing is None:
                raise
            skill_gap = await db.execute(
                select(SkillGapModel)
                .where(
                    SkillGapModel.id == existing.skill_gap_id,
                    SkillGapModel.tenant_id == principal.tenant_id,
                )
                .limit(1)
            )
            capability_gap = await db.execute(
                select(CapabilityGapModel)
                .where(
                    CapabilityGapModel.id == existing.capability_gap_id,
                    CapabilityGapModel.tenant_id == principal.tenant_id,
                )
                .limit(1)
            )
            skill_gap_item = skill_gap.scalar_one_or_none()
            capability_gap_item = capability_gap.scalar_one_or_none()
            if skill_gap_item is None or capability_gap_item is None:
                raise
            return (
                skill_gap_item,
                capability_gap_item,
                existing,
                _dict_payload(getattr(existing, "proposal_evidence", {})),
            )

        await db.refresh(skill_gap)
        await db.refresh(capability_gap)
        await db.refresh(proposal)
        return (
            skill_gap,
            capability_gap,
            proposal,
            _dict_payload(getattr(proposal, "proposal_evidence", {})),
        )

    async def queue_for_review(
        self, db: AsyncSession, proposal_id, principal: Principal
    ) -> tuple[SkillProposalModel, str]:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")

        proposal = await self.get_proposal_by_id(db, proposal_id, principal.tenant_id)
        if proposal is None:
            raise ValueError("Skill proposal not found")

        evolution_proposal = await get_evolution_control_service().create_from_pattern(
            db,
            proposal.pattern_id,
            principal,
            commit=False,
        )
        if evolution_proposal.status not in {"draft", "review", "approved"}:
            raise ValueError("Evolution proposal is not reviewable")

        evolution_metadata = _dict_payload(
            getattr(evolution_proposal, "proposal_metadata", {})
        )
        evolution_metadata["discovery_priority_score"] = float(
            getattr(proposal, "priority_score", 0.0) or 0.0
        )
        evolution_metadata["discovery_evidence_score"] = float(
            getattr(proposal, "evidence_score", 0.0) or 0.0
        )
        setattr(evolution_proposal, "proposal_metadata", evolution_metadata)

        setattr(proposal, "status", "review_queued")
        setattr(proposal, "updated_at", datetime.now(timezone.utc))
        proposal_evidence = _dict_payload(getattr(proposal, "proposal_evidence", {}))
        proposal_evidence["evolution_proposal_id"] = str(evolution_proposal.id)
        setattr(proposal, "proposal_evidence", proposal_evidence)

        await db.commit()
        await db.refresh(proposal)
        return proposal, str(evolution_proposal.id)


_discovery_layer_service: DiscoveryLayerService | None = None


def get_discovery_layer_service() -> DiscoveryLayerService:
    global _discovery_layer_service
    if _discovery_layer_service is None:
        _discovery_layer_service = DiscoveryLayerService()
    return _discovery_layer_service
