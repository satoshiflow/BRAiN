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
    @staticmethod
    def _build_summary(skill_key: str, items: list[SkillOptimizerRecommendationModel]) -> dict[str, Any]:
        by_status = {
            OptimizerRecommendationStatus.OPEN.value: 0,
            OptimizerRecommendationStatus.ACCEPTED.value: 0,
            OptimizerRecommendationStatus.DISMISSED.value: 0,
        }
        by_type: dict[str, int] = {}
        confidences: list[float] = []

        for item in items:
            status_value = str(item.status)
            by_status[status_value] = by_status.get(status_value, 0) + 1
            rec_type = str(item.recommendation_type)
            by_type[rec_type] = by_type.get(rec_type, 0) + 1
            confidences.append(float(item.confidence))

        average_confidence = mean(confidences) if confidences else None
        return {
            "skill_key": skill_key,
            "total": len(items),
            "by_status": by_status,
            "by_type": by_type,
            "average_confidence": average_confidence,
        }

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
        return await self.list_for_skill_with_status(db, tenant_id=tenant_id, skill_key=skill_key)

    async def list_for_skill_with_status(
        self,
        db: AsyncSession,
        tenant_id: str | None,
        skill_key: str,
        status: OptimizerRecommendationStatus | None = None,
    ) -> list[SkillOptimizerRecommendationModel]:
        query = select(SkillOptimizerRecommendationModel).where(SkillOptimizerRecommendationModel.skill_key == skill_key)
        if tenant_id:
            query = query.where(SkillOptimizerRecommendationModel.tenant_id == tenant_id)
        if status is not None:
            query = query.where(SkillOptimizerRecommendationModel.status == status.value)
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

    async def get_summary_for_skill(
        self,
        db: AsyncSession,
        tenant_id: str | None,
        skill_key: str,
    ) -> dict[str, Any]:
        items = await self.list_for_skill(db, tenant_id=tenant_id, skill_key=skill_key)
        return self._build_summary(skill_key=skill_key, items=items)

    async def get_ops_snapshot_for_skill(
        self,
        db: AsyncSession,
        tenant_id: str | None,
        skill_key: str,
    ) -> dict[str, Any]:
        recommendation_summary = await self.get_summary_for_skill(
            db,
            tenant_id=tenant_id,
            skill_key=skill_key,
        )

        eval_query = select(EvaluationResultModel).where(EvaluationResultModel.skill_key == skill_key)
        if tenant_id:
            eval_query = eval_query.where(EvaluationResultModel.tenant_id == tenant_id)
        eval_query = eval_query.order_by(desc(EvaluationResultModel.created_at)).limit(20)
        eval_result = await db.execute(eval_query)
        evaluations = list(eval_result.scalars().all())

        evaluation_total = len(evaluations)
        evaluation_passed = sum(1 for item in evaluations if bool(item.passed))
        evaluation_failed = sum(1 for item in evaluations if not bool(item.passed))
        evaluation_non_compliant = sum(
            1 for item in evaluations if str(item.policy_compliance) == "non_compliant"
        )
        latest_evaluation_score = (
            float(evaluations[0].overall_score)
            if evaluations and evaluations[0].overall_score is not None
            else None
        )

        return {
            "skill_key": skill_key,
            "recommendation_summary": recommendation_summary,
            "evaluation_total": evaluation_total,
            "evaluation_passed": evaluation_passed,
            "evaluation_failed": evaluation_failed,
            "evaluation_non_compliant": evaluation_non_compliant,
            "latest_evaluation_score": latest_evaluation_score,
        }

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
