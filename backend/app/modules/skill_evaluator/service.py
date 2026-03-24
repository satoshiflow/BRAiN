from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.control_plane_events import record_control_plane_event

from .models import EvaluationResultModel

if TYPE_CHECKING:
    from app.modules.skill_engine.models import SkillRunModel


class SkillEvaluatorService:
    @staticmethod
    def _classify_error(run: SkillRunModel, capability_results: list[dict[str, Any]]) -> str | None:
        if run.state != "failed":
            return None
        if run.failure_code:
            return "execution_error"
        if any(item.get("result", {}).get("timeout") for item in capability_results):
            return "execution_error"
        return "quality_error"

    @staticmethod
    def _build_metrics_summary(run: SkillRunModel, capability_results: list[dict[str, Any]]) -> dict[str, Any]:
        latency_total = 0.0
        success_count = 0
        failure_count = 0
        for item in capability_results:
            result = item.get("result", {})
            latency_total += float(result.get("latency_ms") or 0.0)
            if result.get("status") == "succeeded":
                success_count += 1
            elif result.get("status") == "failed":
                failure_count += 1
        return {
            "success": run.state == "succeeded",
            "failure_code": run.failure_code,
            "latency_ms": latency_total,
            "retry_count": run.retry_count,
            "fallback_used": False,
            "capability_count": len(capability_results),
            "success_count": success_count,
            "failure_count": failure_count,
            "cost_actual": run.cost_actual,
        }

    @staticmethod
    def _policy_snapshot_hash(run: SkillRunModel) -> str:
        payload = json.dumps(run.policy_decision or {}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _build_evaluation(self, run: SkillRunModel) -> dict[str, Any]:
        failures = []
        capability_results = run.output_payload.get("_capability_results", [])
        if run.failure_code:
            failures.append(run.failure_code)
        error_classification = self._classify_error(run, capability_results)
        metrics_summary = self._build_metrics_summary(run, capability_results)
        score = 0.0 if failures else 1.0
        dimensions = {
            "success": score,
            "policy": 1.0 if run.policy_decision.get("allowed") else 0.0,
            "cost": 1.0 if (run.cost_actual or 0.0) <= (run.cost_estimate or float("inf")) else 0.5,
        }
        findings = {
            "issues_detected": failures,
            "capability_count": len(capability_results),
            "skill_state": run.state,
        }
        recommendations = {}
        if failures:
            recommendations["next_action"] = "review_capability_failures"
        elif (run.cost_actual or 0.0) > (run.cost_estimate or 0.0) and (run.cost_estimate or 0.0) > 0:
            recommendations["next_action"] = "review_cost_profile"
        return {
            "overall_score": score,
            "dimension_scores": dimensions,
            "passed": not failures,
            "criteria_snapshot": {
                "required_threshold": 1.0,
                "max_review_cycles": 3,
                "policy_snapshot_hash": self._policy_snapshot_hash(run),
                "dimension_keys": list(dimensions.keys()),
            },
            "findings": findings,
            "recommendations": recommendations,
            "metrics_summary": metrics_summary,
            "provider_selection_snapshot": run.provider_selection_snapshot,
            "error_classification": error_classification,
            "policy_compliance": "compliant" if run.policy_decision.get("allowed") else "non_compliant",
            "policy_violations": [] if run.policy_decision.get("allowed") else [{"reason": run.policy_decision.get("reason", "policy denied")}],
        }

    async def create_for_run(self, db: AsyncSession, run: SkillRunModel) -> EvaluationResultModel:
        payload = self._build_evaluation(run)
        previous_result = await db.execute(
            select(EvaluationResultModel)
            .where(EvaluationResultModel.skill_run_id == run.id)
            .order_by(desc(EvaluationResultModel.evaluation_revision))
            .limit(1)
        )
        previous = previous_result.scalar_one_or_none()
        next_revision = (previous.evaluation_revision + 1) if previous is not None else 1
        record = EvaluationResultModel(
            tenant_id=run.tenant_id,
            skill_run_id=run.id,
            skill_key=run.skill_key,
            skill_version=run.skill_version,
            evaluator_type="rule",
            status="pending",
            overall_score=payload["overall_score"],
            dimension_scores=payload["dimension_scores"],
            passed=payload["passed"],
            criteria_snapshot=payload["criteria_snapshot"],
            findings=payload["findings"],
            recommendations=payload["recommendations"],
            metrics_summary=payload["metrics_summary"],
            provider_selection_snapshot=payload["provider_selection_snapshot"],
            error_classification=payload["error_classification"],
            policy_compliance=payload["policy_compliance"],
            policy_violations=payload["policy_violations"],
            correlation_id=run.correlation_id,
            evaluation_revision=next_revision,
            revision_of_id=previous.id if previous is not None else None,
            evidence_artifact_refs=run.evidence_artifact_refs,
            review_artifact_refs=[],
            comparison_artifact_refs=[],
            created_at=datetime.now(timezone.utc),
            created_by="skill_evaluator",
        )
        db.add(record)
        await db.flush()
        await record_control_plane_event(
            db=db,
            tenant_id=run.tenant_id,
            entity_type="evaluation_result",
            entity_id=str(record.id),
            event_type="evaluation.result.created.v1",
            correlation_id=run.correlation_id,
            mission_id=run.mission_id,
            actor_id="skill_evaluator",
            actor_type="system",
            payload={
                "skill_run_id": str(run.id),
                "status": record.status,
                "evaluation_revision": record.evaluation_revision,
            },
            audit_required=False,
        )
        record.status = "completed"
        record.completed_at = datetime.now(timezone.utc)
        await record_control_plane_event(
            db=db,
            tenant_id=run.tenant_id,
            entity_type="evaluation_result",
            entity_id=str(record.id),
            event_type="evaluation.result.completed.v1",
            correlation_id=run.correlation_id,
            mission_id=run.mission_id,
            actor_id="skill_evaluator",
            actor_type="system",
            payload={
                "skill_run_id": str(run.id),
                "status": record.status,
                "passed": record.passed,
                "policy_compliance": record.policy_compliance,
            },
            audit_required=record.policy_compliance == "non_compliant",
            audit_action="evaluation_complete",
            audit_message="Evaluation result completed",
            severity="warning" if record.policy_compliance == "non_compliant" else "info",
        )
        if record.policy_compliance == "non_compliant":
            await record_control_plane_event(
                db=db,
                tenant_id=run.tenant_id,
                entity_type="evaluation_result",
                entity_id=str(record.id),
                event_type="evaluation.result.non_compliant.v1",
                correlation_id=run.correlation_id,
                mission_id=run.mission_id,
                actor_id="skill_evaluator",
                actor_type="system",
                payload={"skill_run_id": str(run.id), "violations": record.policy_violations},
                audit_required=True,
                audit_action="evaluation_non_compliant",
                audit_message="Evaluation result marked non-compliant",
                severity="warning",
            )
        await db.commit()
        await db.refresh(record)
        return record

    async def list_for_run(self, db: AsyncSession, skill_run_id, tenant_id: str | None) -> list[EvaluationResultModel]:
        query = select(EvaluationResultModel).where(EvaluationResultModel.skill_run_id == skill_run_id)
        if tenant_id:
            query = query.where(EvaluationResultModel.tenant_id == tenant_id)
        query = query.order_by(desc(EvaluationResultModel.created_at))
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_latest_for_run(self, db: AsyncSession, skill_run_id, tenant_id: str | None) -> EvaluationResultModel | None:
        items = await self.list_for_run(db, skill_run_id, tenant_id)
        return items[0] if items else None

    async def get_evaluation(self, db: AsyncSession, evaluation_id, tenant_id: str | None) -> EvaluationResultModel | None:
        query = select(EvaluationResultModel).where(EvaluationResultModel.id == evaluation_id)
        if tenant_id:
            query = query.where(EvaluationResultModel.tenant_id == tenant_id)
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()


_skill_evaluator_service: SkillEvaluatorService | None = None


def get_skill_evaluator_service() -> SkillEvaluatorService:
    global _skill_evaluator_service
    if _skill_evaluator_service is None:
        _skill_evaluator_service = SkillEvaluatorService()
    return _skill_evaluator_service
