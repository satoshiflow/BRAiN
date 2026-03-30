from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.discovery_layer.service import get_discovery_layer_service
from app.modules.evolution_control.service import get_evolution_control_service

from .models import EconomyAssessmentModel


def _evidence_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


class EconomyLayerService:
    @staticmethod
    def _complexity_weight(level: str) -> float:
        normalized = (level or "medium").strip().lower()
        mapping = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.85,
            "critical": 1.0,
        }
        return mapping.get(normalized, 0.6)

    @staticmethod
    def _risk_weight(risk_tier: str) -> float:
        normalized = (risk_tier or "medium").strip().lower()
        mapping = {
            "low": 0.95,
            "medium": 1.0,
            "high": 1.05,
            "critical": 1.1,
        }
        return mapping.get(normalized, 1.0)

    def calculate_skill_value(
        self,
        *,
        risk_tier: str,
        value_score: float | None,
        effort_saved_hours: float | None,
        complexity_level: str | None,
        quality_impact: float | None,
    ) -> dict[str, Any]:
        explicit_score = _clamp_score(float(value_score or 0.0))
        effort_component = _clamp_score(float(effort_saved_hours or 0.0) / 40.0)
        quality_component = _clamp_score(float(quality_impact or 0.0))
        complexity_component = _clamp_score(self._complexity_weight(complexity_level or "medium"))
        risk_weight = self._risk_weight(risk_tier)

        computed_score = _clamp_score(
            (
                (effort_component * 0.45)
                + (quality_component * 0.35)
                + (complexity_component * 0.2)
            )
            * risk_weight
        )

        score = explicit_score if explicit_score > 0 else computed_score
        source = "explicit" if explicit_score > 0 else "derived"

        return {
            "value_score": score,
            "source": source,
            "breakdown": {
                "effort_component": effort_component,
                "quality_component": quality_component,
                "complexity_component": complexity_component,
                "risk_weight": risk_weight,
                "computed_score": computed_score,
                "explicit_score": explicit_score,
            },
        }

    async def _resolve_skill_definition_for_run(self, db: AsyncSession, run) -> Any | None:
        from app.modules.skills_registry.models import SkillDefinitionModel

        if run.tenant_id:
            tenant_result = await db.execute(
                select(SkillDefinitionModel)
                .where(
                    SkillDefinitionModel.skill_key == run.skill_key,
                    SkillDefinitionModel.version == run.skill_version,
                    SkillDefinitionModel.tenant_id == run.tenant_id,
                )
                .limit(1)
            )
            tenant_definition = tenant_result.scalar_one_or_none()
            if tenant_definition is not None:
                return tenant_definition

        system_result = await db.execute(
            select(SkillDefinitionModel)
            .where(
                SkillDefinitionModel.skill_key == run.skill_key,
                SkillDefinitionModel.version == run.skill_version,
                SkillDefinitionModel.tenant_id.is_(None),
            )
            .limit(1)
        )
        return system_result.scalar_one_or_none()

    async def ingest_skill_run_feedback(self, db: AsyncSession, run, evaluation) -> dict[str, Any] | None:
        definition = await self._resolve_skill_definition_for_run(db, run)
        if definition is None:
            return None

        metrics = dict(getattr(evaluation, "metrics_summary", {}) or {})
        capability_count = int(metrics.get("capability_count") or 0)
        latency_ms = float(metrics.get("latency_ms") or 0.0)
        overall_score = _clamp_score(float(getattr(evaluation, "overall_score", 0.0) or 0.0))

        observed_effort_hours = max(0.1, (capability_count * 0.6) + (latency_ms / 5000.0))
        existing_effort = float(getattr(definition, "effort_saved_hours", 0.0) or 0.0)
        definition.effort_saved_hours = round((existing_effort * 0.8) + (observed_effort_hours * 0.2), 2)

        existing_quality = float(getattr(definition, "quality_impact", 0.0) or 0.0)
        definition.quality_impact = _clamp_score((existing_quality * 0.7) + (overall_score * 0.3))

        observed_complexity = "low"
        if capability_count >= 8:
            observed_complexity = "critical"
        elif capability_count >= 5:
            observed_complexity = "high"
        elif capability_count >= 3:
            observed_complexity = "medium"

        complexity_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        existing_complexity = str(getattr(definition, "complexity_level", "medium") or "medium").lower()
        existing_rank = complexity_rank.get(existing_complexity, 1)
        observed_rank = complexity_rank.get(observed_complexity, 1)
        definition.complexity_level = observed_complexity if observed_rank > existing_rank else existing_complexity

        profile = self.calculate_skill_value(
            risk_tier=str(getattr(definition, "risk_tier", run.risk_tier) or run.risk_tier),
            value_score=0.0,
            effort_saved_hours=float(definition.effort_saved_hours or 0.0),
            complexity_level=str(definition.complexity_level or "medium"),
            quality_impact=float(definition.quality_impact or 0.0),
        )
        computed_score = float(profile["value_score"])
        existing_value_score = _clamp_score(float(getattr(definition, "value_score", 0.0) or 0.0))
        definition.value_score = (
            computed_score if existing_value_score <= 0 else _clamp_score((existing_value_score * 0.7) + (computed_score * 0.3))
        )

        definition.updated_at = datetime.now(timezone.utc)
        await db.flush()

        return {
            "value_score": float(definition.value_score),
            "effort_saved_hours": float(definition.effort_saved_hours),
            "quality_impact": float(definition.quality_impact),
            "complexity_level": str(definition.complexity_level),
            "source": "skill_run_feedback",
        }

    @staticmethod
    def _run_volume_score(total_runs: int) -> float:
        # Saturates near 1.0 around 20 runs/window
        return _clamp_score(min(1.0, float(total_runs) / 20.0))

    def _market_score(self, item: dict[str, Any]) -> float:
        return _clamp_score(
            (float(item.get("value_score") or 0.0) * 0.45)
            + (float(item.get("success_rate") or 0.0) * 0.2)
            + (float(item.get("avg_overall_score") or 0.0) * 0.2)
            + (self._run_volume_score(int(item.get("total_runs") or 0)) * 0.15)
        )

    async def get_skill_lifecycle_analytics(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
        window_days: int = 30,
        limit: int = 100,
    ) -> dict[str, Any]:
        from app.modules.skill_engine.models import SkillRunModel
        from app.modules.skills_registry.models import SkillDefinitionModel

        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, window_days))

        tenant_definitions: list[Any] = []
        if tenant_id:
            definitions_result = await db.execute(
                select(SkillDefinitionModel).where(
                    SkillDefinitionModel.tenant_id == tenant_id,
                )
            )
            tenant_definitions = list(definitions_result.scalars().all())

        system_definitions_result = await db.execute(
            select(SkillDefinitionModel).where(
                SkillDefinitionModel.tenant_id.is_(None),
            )
        )
        system_definitions = list(system_definitions_result.scalars().all())

        latest_by_skill: dict[str, Any] = {}
        for item in [*system_definitions, *tenant_definitions]:
            current = latest_by_skill.get(item.skill_key)
            if current is None or int(item.version) > int(current.version):
                latest_by_skill[item.skill_key] = item

        run_query = select(SkillRunModel).where(SkillRunModel.created_at >= cutoff)
        if tenant_id:
            run_query = run_query.where(SkillRunModel.tenant_id == tenant_id)
        else:
            run_query = run_query.where(SkillRunModel.tenant_id.is_(None))

        runs_result = await db.execute(
            run_query.order_by(desc(SkillRunModel.created_at)).limit(max(200, limit * 20))
        )
        runs = list(runs_result.scalars().all())

        by_skill: dict[str, dict[str, Any]] = {}
        for run in runs:
            bucket = by_skill.setdefault(
                run.skill_key,
                {
                    "total_runs": 0,
                    "succeeded_runs": 0,
                    "failed_runs": 0,
                    "overall_scores": [],
                    "history_scores": [],
                    "last_run_at": None,
                },
            )
            bucket["total_runs"] += 1
            if run.state == "succeeded":
                bucket["succeeded_runs"] += 1
            if run.state in {"failed", "timed_out"}:
                bucket["failed_runs"] += 1
            if bucket["last_run_at"] is None:
                bucket["last_run_at"] = run.created_at

            evaluation_summary = dict(getattr(run, "evaluation_summary", {}) or {})
            overall_score = evaluation_summary.get("overall_score")
            if isinstance(overall_score, (int, float)):
                bucket["overall_scores"].append(_clamp_score(float(overall_score)))

            economy_feedback = dict(evaluation_summary.get("economy_feedback") or {})
            history_value = economy_feedback.get("value_score")
            if isinstance(history_value, (int, float)):
                bucket["history_scores"].append(_clamp_score(float(history_value)))

        items: list[dict[str, Any]] = []
        for skill_key, definition in latest_by_skill.items():
            run_bucket = by_skill.get(skill_key, {})
            total_runs = int(run_bucket.get("total_runs") or 0)
            succeeded_runs = int(run_bucket.get("succeeded_runs") or 0)
            failed_runs = int(run_bucket.get("failed_runs") or 0)
            success_rate = _clamp_score((succeeded_runs / total_runs) if total_runs > 0 else 0.0)

            overall_scores = list(run_bucket.get("overall_scores") or [])
            avg_overall_score = _clamp_score(
                (sum(overall_scores) / len(overall_scores)) if overall_scores else 0.0
            )

            history_scores = list(run_bucket.get("history_scores") or [])
            trend_delta = 0.0
            if len(history_scores) >= 2:
                trend_delta = round(history_scores[0] - history_scores[-1], 3)

            item = {
                "skill_key": skill_key,
                "latest_version": int(definition.version),
                "value_score": _clamp_score(float(getattr(definition, "value_score", 0.0) or 0.0)),
                "success_rate": success_rate,
                "avg_overall_score": avg_overall_score,
                "total_runs": total_runs,
                "succeeded_runs": succeeded_runs,
                "failed_runs": failed_runs,
                "trend_delta": trend_delta,
                "last_run_at": run_bucket.get("last_run_at"),
            }
            items.append(item)

        items.sort(key=lambda entry: (entry["value_score"], entry["total_runs"]), reverse=True)
        items = items[:limit]

        total_skills = len(items)
        total_runs = sum(int(item["total_runs"]) for item in items)
        avg_value_score = _clamp_score(
            (sum(float(item["value_score"]) for item in items) / total_skills)
            if total_skills > 0
            else 0.0
        )
        avg_success_rate = _clamp_score(
            (sum(float(item["success_rate"]) for item in items) / total_skills)
            if total_skills > 0
            else 0.0
        )

        return {
            "summary": {
                "total_skills": total_skills,
                "total_runs": total_runs,
                "avg_value_score": avg_value_score,
                "avg_success_rate": avg_success_rate,
                "window_days": int(window_days),
            },
            "items": items,
        }

    async def get_marketplace_ranking(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
        window_days: int = 30,
        limit: int = 25,
    ) -> dict[str, Any]:
        analytics = await self.get_skill_lifecycle_analytics(
            db,
            tenant_id=tenant_id,
            window_days=window_days,
            limit=max(limit, 50),
        )

        ranked = []
        for item in analytics["items"]:
            run_volume_score = self._run_volume_score(int(item["total_runs"]))
            market_score = self._market_score(item)
            ranked.append(
                {
                    **item,
                    "run_volume_score": run_volume_score,
                    "market_score": market_score,
                }
            )

        ranked.sort(key=lambda entry: (entry["market_score"], entry["value_score"], entry["total_runs"]), reverse=True)
        ranked = ranked[:limit]

        items = []
        for index, item in enumerate(ranked, start=1):
            items.append(
                {
                    "rank": index,
                    "skill_key": item["skill_key"],
                    "latest_version": item["latest_version"],
                    "market_score": item["market_score"],
                    "value_score": item["value_score"],
                    "success_rate": item["success_rate"],
                    "avg_overall_score": item["avg_overall_score"],
                    "run_volume_score": item["run_volume_score"],
                    "trend_delta": item["trend_delta"],
                    "last_run_at": item["last_run_at"],
                }
            )

        return {
            "window_days": int(window_days),
            "generated_at": datetime.now(timezone.utc),
            "items": items,
        }

    async def get_assessment_by_id(
        self, db: AsyncSession, assessment_id, tenant_id: str
    ) -> EconomyAssessmentModel | None:
        query = select(EconomyAssessmentModel).where(
            EconomyAssessmentModel.id == assessment_id,
            EconomyAssessmentModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_assessment_by_proposal_id(
        self, db: AsyncSession, proposal_id, tenant_id: str
    ) -> EconomyAssessmentModel | None:
        query = select(EconomyAssessmentModel).where(
            EconomyAssessmentModel.discovery_proposal_id == proposal_id,
            EconomyAssessmentModel.tenant_id == tenant_id,
        )
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def analyze_proposal(
        self, db: AsyncSession, proposal_id, principal: Principal
    ) -> tuple[EconomyAssessmentModel, Any]:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")

        proposal = await get_discovery_layer_service().get_proposal_by_id(
            db, proposal_id, principal.tenant_id
        )
        if proposal is None:
            raise ValueError("Skill proposal not found")

        existing = await self.get_assessment_by_proposal_id(
            db, proposal_id, principal.tenant_id
        )
        if existing is not None:
            return existing, proposal

        evidence = _evidence_dict(getattr(proposal, "proposal_evidence", {}))
        observer_count = int(evidence.get("observer_signal_count", 0) or 0)
        knowledge_count = int(evidence.get("knowledge_item_count", 0) or 0)
        discovery_evidence_score = float(
            getattr(proposal, "evidence_score", 0.0) or 0.0
        )
        discovery_priority = float(getattr(proposal, "priority_score", 0.0) or 0.0)

        confidence_score = _clamp_score(discovery_evidence_score)
        frequency_score = _clamp_score((observer_count + knowledge_count) / 10)
        impact_score = _clamp_score(
            (discovery_priority * 0.6) + (confidence_score * 0.4)
        )
        cost_score = _clamp_score(max(0.0, 1.0 - (confidence_score * 0.7)))
        weighted_score = _clamp_score(
            (confidence_score * 0.35)
            + (frequency_score * 0.25)
            + (impact_score * 0.3)
            + ((1.0 - cost_score) * 0.1)
        )

        assessment = EconomyAssessmentModel(
            tenant_id=principal.tenant_id,
            discovery_proposal_id=proposal.id,
            skill_run_id=proposal.skill_run_id,
            status="draft",
            confidence_score=confidence_score,
            frequency_score=frequency_score,
            impact_score=impact_score,
            cost_score=cost_score,
            weighted_score=weighted_score,
            score_breakdown={
                "dimensions": {
                    "confidence": confidence_score,
                    "frequency": frequency_score,
                    "impact": impact_score,
                    "cost": cost_score,
                },
                "weights": {
                    "confidence": 0.35,
                    "frequency": 0.25,
                    "impact": 0.3,
                    "cost_inverse": 0.1,
                },
            },
            updated_at=datetime.now(timezone.utc),
        )
        db.add(assessment)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            existing = await self.get_assessment_by_proposal_id(
                db, proposal_id, principal.tenant_id
            )
            if existing is None:
                raise
            return existing, proposal

        proposal_evidence = dict(evidence)
        proposal_evidence["economy_assessment_id"] = str(assessment.id)
        proposal_evidence["economy_weighted_score"] = weighted_score
        setattr(proposal, "proposal_evidence", proposal_evidence)
        setattr(
            proposal,
            "priority_score",
            _clamp_score((discovery_priority * 0.7) + (weighted_score * 0.3)),
        )
        setattr(proposal, "updated_at", datetime.now(timezone.utc))

        evolution_proposal = await get_evolution_control_service().get_by_pattern_id(
            db,
            proposal.pattern_id,
            principal.tenant_id,
        )
        if evolution_proposal is not None:
            metadata = _evidence_dict(
                getattr(evolution_proposal, "proposal_metadata", {})
            )
            metadata["economy_weighted_score"] = weighted_score
            metadata["economy_assessment_id"] = str(assessment.id)
            setattr(evolution_proposal, "proposal_metadata", metadata)
            setattr(evolution_proposal, "updated_at", datetime.now(timezone.utc))

        await db.commit()
        await db.refresh(assessment)
        await db.refresh(proposal)
        return assessment, proposal

    async def queue_for_review(
        self, db: AsyncSession, assessment_id, principal: Principal
    ) -> EconomyAssessmentModel:
        if not principal.tenant_id:
            raise ValueError("Tenant context required")

        assessment = await self.get_assessment_by_id(
            db, assessment_id, principal.tenant_id
        )
        if assessment is None:
            raise ValueError("Economy assessment not found")

        setattr(assessment, "status", "review_queued")
        setattr(assessment, "updated_at", datetime.now(timezone.utc))
        await db.commit()
        await db.refresh(assessment)
        return assessment


_economy_layer_service: EconomyLayerService | None = None


def get_economy_layer_service() -> EconomyLayerService:
    global _economy_layer_service
    if _economy_layer_service is None:
        _economy_layer_service = EconomyLayerService()
    return _economy_layer_service
