from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.core.capabilities.schemas import CapabilityExecutionRequest, CapabilityExecutionResponse
from app.core.capabilities.service import CapabilityExecutionService, get_capability_execution_service
from app.modules.planning.schemas import DecompositionRequest
from app.modules.planning.service import PlanningService, get_planning_service
from app.modules.policy.schemas import PolicyEvaluationContext
from app.modules.policy.service import get_policy_engine
from app.modules.skills_registry.models import SkillDefinitionModel
from app.modules.skills_registry.schemas import CapabilityRef, VersionSelector
from app.modules.skills_registry.service import SkillRegistryService, get_skill_registry_service
from app.modules.skill_evaluator.service import SkillEvaluatorService, get_skill_evaluator_service

from .models import SkillRunModel
from .schemas import SkillRunCreate, SkillRunExecutionReport, SkillRunResponse, SkillRunState


class SkillEngineService:
    def __init__(
        self,
        skill_registry: SkillRegistryService | None = None,
        capability_execution_service: CapabilityExecutionService | None = None,
        planning_service: PlanningService | None = None,
        evaluator_service: SkillEvaluatorService | None = None,
    ) -> None:
        self.skill_registry = skill_registry or get_skill_registry_service()
        self.capability_execution_service = capability_execution_service or get_capability_execution_service()
        self.planning_service = planning_service or get_planning_service()
        self.evaluator_service = evaluator_service or get_skill_evaluator_service()

    @staticmethod
    def build_correlation_id() -> str:
        return f"skillrun-{uuid4().hex[:16]}"

    @staticmethod
    def build_plan_snapshot(skill_definition: SkillDefinitionModel, capability_bindings: list[dict[str, Any]]) -> dict[str, Any]:
        nodes = []
        for idx, binding in enumerate(capability_bindings, start=1):
            nodes.append(
                {
                    "node_id": f"cap_{idx}_{binding['capability_key'].replace('.', '_')}",
                    "type": "capability_execution",
                    "capability_key": binding["capability_key"],
                    "capability_version": binding["capability_version"],
                    "provider_binding_id": binding["provider_binding_id"],
                    "depends_on": [] if idx == 1 else [nodes[-1]["node_id"]],
                }
            )
        return {
            "skill_key": skill_definition.skill_key,
            "skill_version": skill_definition.version,
            "quality_profile": skill_definition.quality_profile,
            "risk_tier": skill_definition.risk_tier,
            "nodes": nodes,
        }

    async def list_runs(self, db: AsyncSession, tenant_id: str | None, skill_key: str | None = None, state: str | None = None) -> list[SkillRunModel]:
        query = select(SkillRunModel)
        if tenant_id:
            query = query.where(SkillRunModel.tenant_id == tenant_id)
        if skill_key:
            query = query.where(SkillRunModel.skill_key == skill_key)
        if state:
            query = query.where(SkillRunModel.state == state)
        query = query.order_by(desc(SkillRunModel.created_at))
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_run(self, db: AsyncSession, run_id, tenant_id: str | None) -> SkillRunModel | None:
        query = select(SkillRunModel).where(SkillRunModel.id == run_id)
        if tenant_id:
            query = query.where(SkillRunModel.tenant_id == tenant_id)
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def _find_existing_by_idempotency(self, db: AsyncSession, tenant_id: str | None, principal: Principal, idempotency_key: str) -> SkillRunModel | None:
        query = select(SkillRunModel).where(
            SkillRunModel.idempotency_key == idempotency_key,
            SkillRunModel.requested_by == principal.principal_id,
        )
        if tenant_id:
            query = query.where(SkillRunModel.tenant_id == tenant_id)
        result = await db.execute(query.order_by(desc(SkillRunModel.created_at)).limit(1))
        return result.scalar_one_or_none()

    async def _resolve_capability_bindings(self, db: AsyncSession, skill_definition: SkillDefinitionModel) -> tuple[list[dict[str, Any]], float]:
        resolved: list[dict[str, Any]] = []
        cost_estimate = 0.0
        for raw_ref in skill_definition.required_capabilities:
            ref = CapabilityRef.model_validate(raw_ref)
            # exact resolution for plan freeze
            capability = await self.capability_execution_service.capability_registry.resolve_definition(
                db=db,
                capability_key=ref.capability_key,
                tenant_id=skill_definition.tenant_id,
                selector=VersionSelector.EXACT if ref.version_selector != VersionSelector.ACTIVE else VersionSelector.ACTIVE,
                version_value=ref.version_value,
            )
            bindings = self.capability_execution_service.list_bindings(capability.capability_key, capability.version)
            if not bindings:
                raise ValueError(f"No provider binding available for capability '{capability.capability_key}'")
            binding = bindings[0]
            resolved.append(
                {
                    "capability_key": capability.capability_key,
                    "capability_version": capability.version,
                    "provider_binding_id": binding.provider_binding_id,
                }
            )
            cost_estimate += 0.0
        return resolved, cost_estimate

    async def _evaluate_policy(self, db: AsyncSession, principal: Principal, skill_definition: SkillDefinitionModel, payload: SkillRunCreate) -> dict[str, Any]:
        engine = get_policy_engine(db_session=db)
        result = await engine.evaluate(
            PolicyEvaluationContext(
                agent_id=principal.principal_id,
                agent_role=principal.roles[0] if principal.roles else principal.principal_type.value,
                action="skill.run.execute",
                resource=skill_definition.skill_key,
                environment={
                    "tenant_id": principal.tenant_id,
                    "risk_tier": skill_definition.risk_tier,
                    "trigger_type": payload.trigger_type.value,
                },
                params={"skill_version": skill_definition.version},
            ),
            request_id=payload.idempotency_key,
        )
        if not result.allowed:
            raise PermissionError(result.reason)
        return {
            "allowed": result.allowed,
            "effect": result.effect.value,
            "matched_rule": result.matched_rule,
            "matched_policy": result.matched_policy,
            "reason": result.reason,
            "requires_audit": result.requires_audit,
        }

    async def create_run(self, db: AsyncSession, payload: SkillRunCreate, principal: Principal) -> SkillRunModel:
        existing = await self._find_existing_by_idempotency(db, principal.tenant_id, principal, payload.idempotency_key)
        if existing is not None:
            return existing

        selector = VersionSelector.EXACT if payload.version else VersionSelector.ACTIVE
        skill_definition = await self.skill_registry.resolve_definition(
            db,
            payload.skill_key,
            principal.tenant_id,
            selector=selector,
            version_value=payload.version,
        )
        capability_bindings, cost_estimate = await self._resolve_capability_bindings(db, skill_definition)
        policy_decision = await self._evaluate_policy(db, principal, skill_definition, payload)
        plan_snapshot = self.build_plan_snapshot(skill_definition, capability_bindings)

        # create lightweight plan object for deterministic traceability
        decomposition = DecompositionRequest(
            task_name=skill_definition.skill_key,
            task_description=skill_definition.purpose,
            agent_id=principal.principal_id,
            mission_id=payload.mission_id,
            available_capabilities=[item["capability_key"] for item in capability_bindings],
        )
        plan = self.planning_service.decompose_task(decomposition).plan
        plan_snapshot["planning_plan_id"] = plan.plan_id
        plan_snapshot["planning_node_count"] = len(plan.nodes)

        model = SkillRunModel(
            tenant_id=principal.tenant_id,
            skill_key=skill_definition.skill_key,
            skill_version=skill_definition.version,
            state=SkillRunState.QUEUED.value,
            input_payload=payload.input_payload,
            plan_snapshot=plan_snapshot,
            provider_selection_snapshot={"bindings": capability_bindings},
            requested_by=principal.principal_id,
            requested_by_type=principal.principal_type.value,
            trigger_type=payload.trigger_type.value,
            policy_decision=policy_decision,
            risk_tier=skill_definition.risk_tier,
            correlation_id=self.build_correlation_id(),
            causation_id=payload.causation_id,
            idempotency_key=payload.idempotency_key,
            mission_id=payload.mission_id,
            deadline_at=payload.deadline_at,
            cost_estimate=cost_estimate,
        )
        db.add(model)
        await db.commit()
        await db.refresh(model)
        logger.info("Created skill run {} for {} v{}", model.id, model.skill_key, model.skill_version)
        return model

    @staticmethod
    def summarize_evaluation(capability_results: list[CapabilityExecutionResponse]) -> dict[str, Any]:
        failures = [result for result in capability_results if result.result.status.value == "failed"]
        return {
            "overall_score": 1.0 if not failures else 0.0,
            "issues_detected": [getattr(item.result, "error_code", None) for item in failures],
            "error_classification": "execution_error" if failures else None,
        }

    @staticmethod
    def serialize_capability_results(results: list[CapabilityExecutionResponse]) -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in results]

    async def execute_run(self, db: AsyncSession, run_id, principal: Principal) -> SkillRunExecutionReport:
        run = await self.get_run(db, run_id, principal.tenant_id)
        if run is None:
            raise ValueError("Skill run not found")
        if run.state in {SkillRunState.SUCCEEDED.value, SkillRunState.FAILED.value, SkillRunState.CANCELLED.value, SkillRunState.TIMED_OUT.value}:
            return SkillRunExecutionReport(skill_run=SkillRunResponse.model_validate(run), capability_results=[])

        bindings = run.provider_selection_snapshot.get("bindings", [])
        run.state = SkillRunState.PLANNING.value
        await db.commit()

        results: list[CapabilityExecutionResponse] = []
        run.state = SkillRunState.RUNNING.value
        run.started_at = datetime.now(timezone.utc)
        await db.commit()

        for binding in bindings:
            capability_request = CapabilityExecutionRequest(
                tenant_id=run.tenant_id,
                skill_run_id=str(run.id),
                capability_key=binding["capability_key"],
                capability_version=binding["capability_version"],
                provider_binding_id=binding["provider_binding_id"],
                input_payload=run.input_payload,
                correlation_id=run.correlation_id,
                causation_id=run.causation_id,
                actor_id=principal.principal_id,
                risk_tier=run.risk_tier,
                deadline_at=run.deadline_at,
            )
            result = await self.capability_execution_service.execute(db, capability_request)
            results.append(result)
            if result.result.status.value == "failed":
                run.state = SkillRunState.FAILED.value
                run.finished_at = datetime.now(timezone.utc)
                run.failure_code = result.result.error_code
                run.failure_reason_sanitized = result.result.sanitized_message
                run.output_payload = {"_capability_results": self.serialize_capability_results(results)}
                run.evaluation_summary = self.summarize_evaluation(results)
                await db.commit()
                evaluation = await self.evaluator_service.create_for_run(db, run)
                run.evaluation_summary = {
                    **run.evaluation_summary,
                    "evaluation_result_id": str(evaluation.id),
                    "policy_compliance": evaluation.policy_compliance,
                }
                await db.commit()
                await db.refresh(run)
                return SkillRunExecutionReport(skill_run=SkillRunResponse.model_validate(run), capability_results=results)

        output_payload = {
            item.capability_key: item.result.output for item in results if item.result.status.value == "succeeded"
        }
        output_payload["_capability_results"] = self.serialize_capability_results(results)
        run.output_payload = output_payload
        run.evaluation_summary = self.summarize_evaluation(results)
        run.cost_actual = sum((item.result.cost_actual or 0.0) for item in results if item.result.status.value == "succeeded")
        run.state = SkillRunState.SUCCEEDED.value
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        evaluation = await self.evaluator_service.create_for_run(db, run)
        run.evaluation_summary = {
            **run.evaluation_summary,
            "evaluation_result_id": str(evaluation.id),
            "policy_compliance": evaluation.policy_compliance,
        }
        await db.commit()
        await db.refresh(run)
        return SkillRunExecutionReport(skill_run=SkillRunResponse.model_validate(run), capability_results=results)

    async def cancel_run(self, db: AsyncSession, run_id, principal: Principal) -> SkillRunModel | None:
        run = await self.get_run(db, run_id, principal.tenant_id)
        if run is None:
            return None
        if run.state in {SkillRunState.SUCCEEDED.value, SkillRunState.FAILED.value, SkillRunState.CANCELLED.value, SkillRunState.TIMED_OUT.value}:
            return run
        run.state = SkillRunState.CANCELLED.value
        run.finished_at = datetime.now(timezone.utc)
        run.failure_reason_sanitized = "Cancelled by caller"
        await db.commit()
        await db.refresh(run)
        return run

    async def finalize_external_run(
        self,
        db: AsyncSession,
        run_id,
        principal: Principal,
        *,
        success: bool,
        output_payload: dict[str, Any] | None = None,
        failure_code: str | None = None,
        failure_reason_sanitized: str | None = None,
    ) -> SkillRunModel:
        run = await self.get_run(db, run_id, principal.tenant_id)
        if run is None:
            raise ValueError("Skill run not found")
        if run.started_at is None:
            run.started_at = datetime.now(timezone.utc)
        run.finished_at = datetime.now(timezone.utc)
        run.output_payload = output_payload or {}
        run.cost_actual = 0.0
        if success:
            run.state = SkillRunState.SUCCEEDED.value
            run.failure_code = None
            run.failure_reason_sanitized = None
            run.evaluation_summary = {"overall_score": 1.0, "external_execution": True}
        else:
            run.state = SkillRunState.FAILED.value
            run.failure_code = failure_code or "EXTERNAL-FAIL"
            run.failure_reason_sanitized = failure_reason_sanitized or "External execution failed"
            run.evaluation_summary = {
                "overall_score": 0.0,
                "external_execution": True,
                "issues_detected": [run.failure_code],
                "error_classification": "execution_error",
            }
        await db.commit()
        evaluation = await self.evaluator_service.create_for_run(db, run)
        run.evaluation_summary = {
            **run.evaluation_summary,
            "evaluation_result_id": str(evaluation.id),
            "policy_compliance": evaluation.policy_compliance,
        }
        await db.commit()
        await db.refresh(run)
        return run


_skill_engine_service: SkillEngineService | None = None


def get_skill_engine_service() -> SkillEngineService:
    global _skill_engine_service
    if _skill_engine_service is None:
        _skill_engine_service = SkillEngineService()
    return _skill_engine_service
