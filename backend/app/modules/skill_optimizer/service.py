from __future__ import annotations

from statistics import mean
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.control_plane_events import record_control_plane_event
from app.modules.skill_engine.models import SkillRunModel
from app.modules.skill_evaluator.models import EvaluationResultModel

from .models import SkillOptimizerRecommendationModel
from .schemas import OptimizerRecommendationStatus


class SkillOptimizerService:
    async def _emit_recommendation_event(
        self,
        db: AsyncSession,
        recommendation: SkillOptimizerRecommendationModel,
    ) -> None:
        await record_control_plane_event(
            db=db,
            tenant_id=recommendation.tenant_id,
            entity_type="optimizer_recommendation",
            entity_id=str(recommendation.id),
            event_type="optimizer.recommendation.created.v1",
            correlation_id=None,
            mission_id=None,
            actor_id="skill_optimizer",
            actor_type="system",
            payload={
                "skill_key": recommendation.skill_key,
                "skill_version": recommendation.skill_version,
                "recommendation_type": recommendation.recommendation_type,
                "status": recommendation.status,
                "confidence": recommendation.confidence,
            },
            audit_required=False,
        )

    async def _emit_status_transition_event(
        self,
        db: AsyncSession,
        recommendation: SkillOptimizerRecommendationModel,
        previous_status: str,
        actor_id: str,
        reason: str | None,
    ) -> None:
        payload: dict[str, Any] = {
            "skill_key": recommendation.skill_key,
            "skill_version": recommendation.skill_version,
            "recommendation_type": recommendation.recommendation_type,
            "previous_status": previous_status,
            "new_status": recommendation.status,
        }
        if reason:
            payload["reason"] = reason

        await record_control_plane_event(
            db=db,
            tenant_id=recommendation.tenant_id,
            entity_type="optimizer_recommendation",
            entity_id=str(recommendation.id),
            event_type="optimizer.recommendation.status_changed.v1",
            correlation_id=None,
            mission_id=None,
            actor_id=actor_id,
            actor_type="human",
            payload=payload,
            audit_required=True,
            audit_action="optimizer_recommendation_status_changed",
            audit_message="Optimizer recommendation status changed",
            severity="info",
        )

    async def generate_for_skill(self, db: AsyncSession, tenant_id: str | None, skill_key: str) -> list[SkillOptimizerRecommendationModel]:
        query = select(SkillRunModel).where(SkillRunModel.skill_key == skill_key)
        if tenant_id:
            query = query.where(SkillRunModel.tenant_id == tenant_id)
        query = query.order_by(desc(SkillRunModel.created_at)).limit(20)
        result = await db.execute(query)
        runs = list(result.scalars().all())
        if not runs:
            return []

        evaluation_query = select(EvaluationResultModel).where(EvaluationResultModel.skill_key == skill_key)
        if tenant_id:
            evaluation_query = evaluation_query.where(EvaluationResultModel.tenant_id == tenant_id)
        evaluation_query = evaluation_query.order_by(desc(EvaluationResultModel.created_at)).limit(20)
        evaluation_result = await db.execute(evaluation_query)
        evaluations = list(evaluation_result.scalars().all())

        recommendations: list[SkillOptimizerRecommendationModel] = []
        failure_runs = [run for run in runs if run.state == "failed"]
        avg_cost = mean([(run.cost_actual or 0.0) for run in runs]) if runs else 0.0
        latest_version = max(run.skill_version for run in runs)
        avg_score = mean([item.overall_score for item in evaluations if item.overall_score is not None]) if evaluations else None
        failing_evaluations = [item for item in evaluations if item.passed is False]

        if failure_runs:
            recommendations.append(
                SkillOptimizerRecommendationModel(
                    tenant_id=tenant_id,
                    skill_key=skill_key,
                    skill_version=latest_version,
                    recommendation_type="review_capability_sequence",
                    confidence=min(1.0, len(failure_runs) / max(1, len(runs))),
                    status="open",
                    rationale="Recent skill runs show repeated execution failures; review capability order, provider selection, or fallback strategy.",
                    evidence={"recent_failures": len(failure_runs), "sample_size": len(runs), "failed_evaluations": len(failing_evaluations)},
                    source_snapshot={
                        "run_ids": [str(run.id) for run in failure_runs[:5]],
                        "evaluation_ids": [str(item.id) for item in failing_evaluations[:5]],
                        "average_score": avg_score,
                    },
                )
            )

        high_cost_runs = [run for run in runs if (run.cost_actual or 0.0) > (run.cost_estimate or 0.0) and (run.cost_estimate or 0.0) > 0.0]
        if high_cost_runs:
            recommendations.append(
                SkillOptimizerRecommendationModel(
                    tenant_id=tenant_id,
                    skill_key=skill_key,
                    skill_version=latest_version,
                    recommendation_type="tighten_cost_profile",
                    confidence=min(1.0, len(high_cost_runs) / max(1, len(runs))),
                    status="open",
                    rationale="Actual execution cost exceeds estimates on multiple recent runs; tighten provider or planning cost constraints.",
                    evidence={"high_cost_runs": len(high_cost_runs), "average_cost": avg_cost},
                    source_snapshot={
                        "run_ids": [str(run.id) for run in high_cost_runs[:5]],
                        "evaluation_ids": [str(item.id) for item in evaluations[:5]],
                        "average_score": avg_score,
                    },
                )
            )

        created = []
        for recommendation in recommendations:
            db.add(recommendation)
            created.append(recommendation)
        if created:
            await db.commit()
            for item in created:
                await db.refresh(item)
            for item in created:
                await self._emit_recommendation_event(db, item)
            await db.commit()
        return created

    async def list_for_skill(self, db: AsyncSession, tenant_id: str | None, skill_key: str) -> list[SkillOptimizerRecommendationModel]:
        query = select(SkillOptimizerRecommendationModel).where(SkillOptimizerRecommendationModel.skill_key == skill_key)
        if tenant_id:
            query = query.where(SkillOptimizerRecommendationModel.tenant_id == tenant_id)
        query = query.order_by(desc(SkillOptimizerRecommendationModel.created_at))
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_recommendation(
        self,
        db: AsyncSession,
        recommendation_id,
        tenant_id: str | None,
    ) -> SkillOptimizerRecommendationModel | None:
        query = select(SkillOptimizerRecommendationModel).where(SkillOptimizerRecommendationModel.id == recommendation_id)
        if tenant_id:
            query = query.where(SkillOptimizerRecommendationModel.tenant_id == tenant_id)
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def update_status(
        self,
        db: AsyncSession,
        recommendation_id,
        tenant_id: str | None,
        status: OptimizerRecommendationStatus,
        actor_id: str,
        reason: str | None = None,
    ) -> SkillOptimizerRecommendationModel | None:
        recommendation = await self.get_recommendation(db, recommendation_id, tenant_id)
        if recommendation is None:
            return None

        previous_status = str(recommendation.status)
        target_status = status.value
        if previous_status == target_status:
            return recommendation
        if previous_status != OptimizerRecommendationStatus.OPEN.value:
            raise ValueError(
                f"Recommendation status transition not allowed: {previous_status} -> {target_status}"
            )
        if target_status == OptimizerRecommendationStatus.OPEN.value:
            raise ValueError("Recommendation status transition not allowed: open -> open")

        recommendation.status = target_status
        await self._emit_status_transition_event(
            db,
            recommendation,
            previous_status=previous_status,
            actor_id=actor_id,
            reason=reason,
        )
        await db.commit()
        await db.refresh(recommendation)
        return recommendation


_skill_optimizer_service: SkillOptimizerService | None = None


def get_skill_optimizer_service() -> SkillOptimizerService:
    global _skill_optimizer_service
    if _skill_optimizer_service is None:
        _skill_optimizer_service = SkillOptimizerService()
    return _skill_optimizer_service
