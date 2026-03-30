from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any
from uuid import uuid4

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.core.capabilities.schemas import CapabilityExecutionRequest, CapabilityExecutionResponse
from app.core.capabilities.service import CapabilityExecutionService, get_capability_execution_service
from app.core.control_plane_events import SkillRunTransitionModel, record_control_plane_event
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

AXE_STATE_MAP = {
    SkillRunState.QUEUED.value: "queued",
    SkillRunState.PLANNING.value: "planning",
    SkillRunState.WAITING_APPROVAL.value: "waiting_approval",
    SkillRunState.RUNNING.value: "running",
    SkillRunState.SUCCEEDED.value: "succeeded",
    SkillRunState.FAILED.value: "failed",
    SkillRunState.CANCELLED.value: "cancelled",
    SkillRunState.CANCEL_REQUESTED.value: "cancelled",
    SkillRunState.TIMED_OUT.value: "failed",
}


class SkillEngineService:
    _NO_POLICY_REASON_FRAGMENT = "No matching policies configured"

    TERMINAL_STATES = {
        SkillRunState.SUCCEEDED.value,
        SkillRunState.FAILED.value,
        SkillRunState.CANCELLED.value,
        SkillRunState.TIMED_OUT.value,
    }

    def _map_to_axe_state(self, skill_state: str) -> str:
        return AXE_STATE_MAP.get(skill_state, "queued")

    async def _emit_axe_stream_event(
        self,
        run_id: Any,
        previous_state: str | None,
        current_state: str,
        reason: str | None = None,
    ) -> None:
        try:
            from app.modules.axe_streams.service import get_axe_stream_service
            from app.modules.axe_streams.schemas import AXERunState

            stream_service = get_axe_stream_service()
            await stream_service.emit_state_changed(
                run_id=run_id,
                previous_state=AXERunState(self._map_to_axe_state(previous_state)) if previous_state else None,
                current_state=AXERunState(self._map_to_axe_state(current_state)),
                reason=reason,
            )

            if current_state == SkillRunState.SUCCEEDED.value:
                await stream_service.emit_run_succeeded(run_id=run_id, output={"state": "succeeded"})
            elif current_state == SkillRunState.FAILED.value:
                await stream_service.emit_run_failed(
                    run_id=run_id,
                    error_code="SKILL_RUN_FAILED",
                    message=reason or "Skill run failed",
                )
        except Exception as exc:
            logger.warning("Failed to emit AXE stream event for run {}: {}", run_id, exc)

    async def _trigger_self_healing_on_failure(
        self,
        db: AsyncSession,
        run: SkillRunModel,
        principal: Principal,
        failure_state: str,
    ) -> None:
        if failure_state != SkillRunState.FAILED.value:
            return
        try:
            from app.modules.immune_orchestrator.schemas import IncidentSignal, SignalSeverity
            from app.modules.immune_orchestrator.service import get_immune_orchestrator_service

            severity_map = {
                "timeout": SignalSeverity.WARNING,
                "provider": SignalSeverity.CRITICAL,
                "approval": SignalSeverity.WARNING,
            }
            failure_code = run.failure_code or ""
            severity = SignalSeverity.CRITICAL
            for key, sev in severity_map.items():
                if key in failure_code.lower():
                    severity = sev
                    break

            signal = IncidentSignal(
                id=str(uuid4()),
                type="skill_run_failure",
                source="skill_engine",
                severity=severity,
                entity=str(run.id),
                context={
                    "skill_key": run.skill_key,
                    "failure_code": run.failure_code,
                    "failure_reason": run.failure_reason_sanitized,
                },
                correlation_id=run.correlation_id,
                blast_radius=50,
                confidence=0.8,
                recurrence=0,
            )
            orchestrator = get_immune_orchestrator_service()
            await orchestrator.ingest_signal(signal, db)
        except Exception as exc:
            logger.warning("Failed to trigger self-healing for run {}: {}", run.id, exc)

    TRANSITIONS = {
        SkillRunState.QUEUED.value: {
            SkillRunState.PLANNING.value,
            SkillRunState.CANCEL_REQUESTED.value,
        },
        SkillRunState.PLANNING.value: {
            SkillRunState.WAITING_APPROVAL.value,
            SkillRunState.RUNNING.value,
            SkillRunState.FAILED.value,
            SkillRunState.CANCEL_REQUESTED.value,
        },
        SkillRunState.WAITING_APPROVAL.value: {
            SkillRunState.RUNNING.value,
            SkillRunState.FAILED.value,
            SkillRunState.CANCEL_REQUESTED.value,
        },
        SkillRunState.RUNNING.value: {
            SkillRunState.SUCCEEDED.value,
            SkillRunState.FAILED.value,
            SkillRunState.TIMED_OUT.value,
            SkillRunState.CANCEL_REQUESTED.value,
        },
        SkillRunState.CANCEL_REQUESTED.value: {SkillRunState.CANCELLED.value},
    }

    TRANSITION_EVENTS = {
        SkillRunState.PLANNING.value: "skill.run.planning.started.v1",
        SkillRunState.WAITING_APPROVAL.value: "skill.run.approval.required.v1",
        SkillRunState.RUNNING.value: "skill.run.started.v1",
        SkillRunState.SUCCEEDED.value: "skill.run.completed.v1",
        SkillRunState.FAILED.value: "skill.run.failed.v1",
        SkillRunState.CANCEL_REQUESTED.value: "skill.run.cancel_requested.v1",
        SkillRunState.CANCELLED.value: "skill.run.cancelled.v1",
        SkillRunState.TIMED_OUT.value: "skill.run.timed_out.v1",
    }

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
            "runtime_owner": "skill_engine",
            "provider_resolution_owner": "skill_engine",
        }

    @staticmethod
    def is_transition_allowed(current: str, target: str) -> bool:
        return target in SkillEngineService.TRANSITIONS.get(current, set())

    @staticmethod
    def requires_approval(risk_tier: str) -> bool:
        return risk_tier in {"high", "critical"}

    async def _record_transition(
        self,
        db: AsyncSession,
        run: SkillRunModel,
        *,
        from_state: str | None,
        to_state: str,
        principal: Principal,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event_type = self.TRANSITION_EVENTS[to_state]
        run.state = to_state
        run.state_sequence = (run.state_sequence or 0) + 1
        run.state_changed_at = datetime.now(timezone.utc)
        if to_state == SkillRunState.RUNNING.value and run.started_at is None:
            run.started_at = datetime.now(timezone.utc)
        if to_state in self.TERMINAL_STATES:
            run.finished_at = datetime.now(timezone.utc)
        db.add(
            SkillRunTransitionModel(
                skill_run_id=run.id,
                tenant_id=run.tenant_id,
                transition_index=run.state_sequence,
                from_state=from_state,
                to_state=to_state,
                event_type=event_type,
                correlation_id=run.correlation_id,
                actor_id=principal.principal_id,
                actor_type=principal.principal_type.value,
                reason=reason,
                transition_metadata=metadata or {},
            )
        )
        await record_control_plane_event(
            db=db,
            tenant_id=run.tenant_id,
            entity_type="skill_run",
            entity_id=str(run.id),
            event_type=event_type,
            correlation_id=run.correlation_id,
            mission_id=run.mission_id,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "from_state": from_state,
                "to_state": to_state,
                "skill_key": run.skill_key,
                "skill_version": run.skill_version,
                "reason": reason,
                "metadata": metadata or {},
            },
            audit_required=to_state in {
                SkillRunState.WAITING_APPROVAL.value,
                SkillRunState.CANCEL_REQUESTED.value,
                SkillRunState.SUCCEEDED.value,
                SkillRunState.FAILED.value,
                SkillRunState.CANCELLED.value,
                SkillRunState.TIMED_OUT.value,
            },
            audit_action=f"skill_run_{to_state}",
            audit_message=f"Skill run transitioned to {to_state}",
            severity="warning" if to_state in {SkillRunState.FAILED.value, SkillRunState.TIMED_OUT.value} else "info",
        )

    async def _transition_run(
        self,
        db: AsyncSession,
        run: SkillRunModel,
        target_state: SkillRunState,
        principal: Principal,
        *,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        current = run.state
        if current in self.TERMINAL_STATES:
            raise ValueError("SR-006 STATE_CONFLICT: terminal skill runs are immutable")
        if not self.is_transition_allowed(current, target_state.value):
            raise ValueError(f"SR-006 STATE_CONFLICT: illegal transition {current} -> {target_state.value}")
        await self._record_transition(
            db,
            run,
            from_state=current,
            to_state=target_state.value,
            principal=principal,
            reason=reason,
            metadata=metadata,
        )
        await self._emit_axe_stream_event(run.id, current, target_state.value, reason)
        if target_state == SkillRunState.FAILED:
            await self._trigger_self_healing_on_failure(db, run, principal, target_state.value)

    @staticmethod
    def project_evaluation_summary(evaluation: Any) -> dict[str, Any]:
        return {
            "evaluation_result_id": str(evaluation.id),
            "status": evaluation.status,
            "overall_score": evaluation.overall_score,
            "passed": evaluation.passed,
            "policy_compliance": evaluation.policy_compliance,
            "evaluation_revision": evaluation.evaluation_revision,
        }

    async def _ingest_learning_artifacts(self, db: AsyncSession, run_id, principal: Principal) -> None:
        if os.getenv("BRAIN_AUTO_LEARN_ON_SKILLRUN", "true").strip().lower() not in {"1", "true", "yes"}:
            return
        if not principal.tenant_id:
            return
        try:
            from app.modules.experience_layer.service import get_experience_layer_service
            from app.modules.knowledge_layer.service import get_knowledge_layer_service

            await get_experience_layer_service().ingest_skill_run(db, run_id, principal)
            await get_knowledge_layer_service().ingest_run_lesson(db, run_id, principal)
        except Exception as exc:
            logger.warning("SkillRun learning ingestion failed for {}: {}", run_id, exc)

    async def _ingest_economy_feedback(self, db: AsyncSession, run: SkillRunModel, evaluation) -> None:
        try:
            from app.modules.economy_layer.service import get_economy_layer_service

            feedback = await get_economy_layer_service().ingest_skill_run_feedback(
                db,
                run,
                evaluation,
            )
            if feedback is not None:
                run.evaluation_summary = {
                    **(run.evaluation_summary or {}),
                    "economy_feedback": feedback,
                }
        except Exception as exc:
            logger.warning("SkillRun economy feedback ingestion failed for {}: {}", run.id, exc)

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
            binding_result, selection = await self.capability_execution_service.resolve_binding_for_execution(
                db,
                tenant_id=skill_definition.tenant_id,
                capability_key=capability.capability_key,
                capability_version=capability.version,
                policy_context={
                    "risk_tier": skill_definition.risk_tier,
                    "skill_key": skill_definition.skill_key,
                    "skill_version": skill_definition.version,
                },
            )
            if not binding_result or not selection:
                raise ValueError(f"No provider binding available for capability '{capability.capability_key}'")
            resolved.append(
                {
                    "capability_key": capability.capability_key,
                    "capability_version": capability.version,
                    "provider_binding_id": binding_result.binding.provider_binding_id,
                    "selection_strategy": selection["selection_strategy"] if isinstance(selection, dict) else selection.selection_strategy,
                    "selection_reason": selection["selection_reason"] if isinstance(selection, dict) else selection.selection_reason,
                    "binding_snapshot": selection["binding_snapshot"] if isinstance(selection, dict) else selection.binding_snapshot,
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
        no_policy_match = (
            not result.allowed
            and result.reason
            and self._NO_POLICY_REASON_FRAGMENT in result.reason
        )
        fallback_policy = str(getattr(skill_definition, "fallback_policy", "allowed") or "allowed").lower()
        if no_policy_match and fallback_policy != "forbidden":
            logger.warning(
                "Policy engine returned unconfigured default deny for {} v{}; "
                "continuing with guarded audit fallback (fallback_policy={})",
                skill_definition.skill_key,
                skill_definition.version,
                fallback_policy,
            )
            return {
                "allowed": True,
                "effect": "audit",
                "matched_rule": None,
                "matched_policy": None,
                "reason": "No matching policies configured - guarded fallback allow",
                "requires_audit": True,
                "policy_defaulted": True,
                "fallback_policy": fallback_policy,
            }
        if not result.allowed:
            raise PermissionError(result.reason)
        return {
            "allowed": result.allowed,
            "effect": result.effect.value,
            "matched_rule": result.matched_rule,
            "matched_policy": result.matched_policy,
            "reason": result.reason,
            "requires_audit": result.requires_audit,
            "policy_defaulted": False,
            "fallback_policy": fallback_policy,
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
        upstream_decision_snapshot = {
            "decision_context_id": payload.decision_context_id,
            "purpose_evaluation_id": payload.purpose_evaluation_id,
            "routing_decision_id": payload.routing_decision_id,
            "governance_snapshot": payload.governance_snapshot or {},
        }

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
        plan_snapshot["upstream_decision"] = upstream_decision_snapshot

        policy_snapshot = {
            **policy_decision,
            "upstream_decision": upstream_decision_snapshot,
        }

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
            policy_decision_id=uuid4(),
            policy_decision=policy_decision,
            policy_snapshot=policy_snapshot,
            risk_tier=skill_definition.risk_tier,
            correlation_id=self.build_correlation_id(),
            causation_id=payload.causation_id,
            idempotency_key=payload.idempotency_key,
            mission_id=payload.mission_id,
            deadline_at=payload.deadline_at,
            cost_estimate=cost_estimate,
            state_changed_at=datetime.now(timezone.utc),
        )
        db.add(model)
        await db.flush()
        await record_control_plane_event(
            db=db,
            tenant_id=model.tenant_id,
            entity_type="skill_run",
            entity_id=str(model.id),
            event_type="skill.run.created.v1",
            correlation_id=model.correlation_id,
            mission_id=model.mission_id,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "skill_key": model.skill_key,
                "skill_version": model.skill_version,
                "state": model.state,
                "policy_decision_id": str(model.policy_decision_id) if model.policy_decision_id else None,
            },
            audit_required=True,
            audit_action="skill_run_create",
            audit_message="Skill run created",
        )
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
        if run.state in self.TERMINAL_STATES:
            return SkillRunExecutionReport(skill_run=SkillRunResponse.model_validate(run), capability_results=[])

        bindings = run.provider_selection_snapshot.get("bindings", [])
        if run.state == SkillRunState.CANCEL_REQUESTED.value:
            await self._transition_run(db, run, SkillRunState.CANCELLED, principal, reason="cancel_request_honored")
            await db.commit()
            await db.refresh(run)
            return SkillRunExecutionReport(skill_run=SkillRunResponse.model_validate(run), capability_results=[])

        if run.state == SkillRunState.QUEUED.value:
            await self._transition_run(db, run, SkillRunState.PLANNING, principal)
        if self.requires_approval(run.risk_tier) and run.state == SkillRunState.PLANNING.value:
            await self._transition_run(db, run, SkillRunState.WAITING_APPROVAL, principal, reason="risk_tier_requires_approval")
            await db.commit()
            await db.refresh(run)
            return SkillRunExecutionReport(skill_run=SkillRunResponse.model_validate(run), capability_results=[])
        if run.state == SkillRunState.WAITING_APPROVAL.value:
            return SkillRunExecutionReport(skill_run=SkillRunResponse.model_validate(run), capability_results=[])
        if run.state == SkillRunState.PLANNING.value:
            await self._transition_run(db, run, SkillRunState.RUNNING, principal)
        await db.commit()

        results: list[CapabilityExecutionResponse] = []

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
                run.failure_code = getattr(result.result, "error_code", "SR-005 PROVIDER_UNAVAILABLE")
                run.failure_reason_sanitized = getattr(result.result, "sanitized_message", "Capability execution failed")
                run.output_payload = {"_capability_results": self.serialize_capability_results(results)}
                run.evaluation_summary = self.summarize_evaluation(results)
                await self._transition_run(db, run, SkillRunState.FAILED, principal, reason=run.failure_code)
                evaluation = await self.evaluator_service.create_for_run(db, run)
                run.evaluation_summary = self.project_evaluation_summary(evaluation)
                await self._ingest_economy_feedback(db, run, evaluation)
                await db.commit()
                await db.refresh(run)
                await self._ingest_learning_artifacts(db, run.id, principal)
                return SkillRunExecutionReport(skill_run=SkillRunResponse.model_validate(run), capability_results=results)

        output_payload = {
            item.capability_key: item.result.output for item in results if item.result.status.value == "succeeded"
        }
        output_payload["_capability_results"] = self.serialize_capability_results(results)
        run.output_payload = output_payload
        run.evaluation_summary = self.summarize_evaluation(results)
        run.cost_actual = sum((item.result.cost_actual or 0.0) for item in results if item.result.status.value == "succeeded")
        await self._transition_run(db, run, SkillRunState.SUCCEEDED, principal)
        evaluation = await self.evaluator_service.create_for_run(db, run)
        run.evaluation_summary = self.project_evaluation_summary(evaluation)
        await self._ingest_economy_feedback(db, run, evaluation)
        await db.commit()
        await db.refresh(run)
        await self._ingest_learning_artifacts(db, run.id, principal)
        return SkillRunExecutionReport(skill_run=SkillRunResponse.model_validate(run), capability_results=results)

    async def cancel_run(self, db: AsyncSession, run_id, principal: Principal) -> SkillRunModel | None:
        run = await self.get_run(db, run_id, principal.tenant_id)
        if run is None:
            return None
        if run.state in self.TERMINAL_STATES:
            return run
        await self._transition_run(db, run, SkillRunState.CANCEL_REQUESTED, principal, reason="cancelled_by_caller")
        run.failure_reason_sanitized = "Cancellation requested by caller"
        await db.commit()
        await db.refresh(run)
        return run

    async def approve_run(self, db: AsyncSession, run_id, principal: Principal) -> SkillRunModel | None:
        run = await self.get_run(db, run_id, principal.tenant_id)
        if run is None:
            return None
        if run.state != SkillRunState.WAITING_APPROVAL.value:
            raise ValueError("SR-006 STATE_CONFLICT: run is not waiting approval")
        await self._transition_run(db, run, SkillRunState.RUNNING, principal, reason="approved")
        await db.commit()
        await db.refresh(run)
        return run

    async def reject_run(self, db: AsyncSession, run_id, principal: Principal, reason: str = "approval_rejected") -> SkillRunModel | None:
        run = await self.get_run(db, run_id, principal.tenant_id)
        if run is None:
            return None
        if run.state != SkillRunState.WAITING_APPROVAL.value:
            raise ValueError("SR-006 STATE_CONFLICT: run is not waiting approval")
        run.failure_code = "SR-004 APPROVAL_REQUIRED"
        run.failure_reason_sanitized = reason
        await self._transition_run(db, run, SkillRunState.FAILED, principal, reason=reason)
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
        if run.state == SkillRunState.QUEUED.value:
            await self._transition_run(db, run, SkillRunState.PLANNING, principal, reason="external_finalize_entry")
        if run.state == SkillRunState.PLANNING.value:
            await self._transition_run(db, run, SkillRunState.RUNNING, principal, reason="external_finalize_entry")
        if run.state == SkillRunState.WAITING_APPROVAL.value:
            raise ValueError("SR-004 APPROVAL_REQUIRED: approval pending")
        if run.state == SkillRunState.CANCEL_REQUESTED.value:
            await self._transition_run(db, run, SkillRunState.CANCELLED, principal, reason="cancel_request_honored")
            await db.commit()
            await db.refresh(run)
            return run
        run.output_payload = output_payload or {}
        run.cost_actual = 0.0
        if success:
            run.failure_code = None
            run.failure_reason_sanitized = None
            run.evaluation_summary = {"overall_score": 1.0, "external_execution": True}
            await self._transition_run(db, run, SkillRunState.SUCCEEDED, principal, reason="external_success")
        else:
            run.failure_code = failure_code or "EXTERNAL-FAIL"
            run.failure_reason_sanitized = failure_reason_sanitized or "External execution failed"
            run.evaluation_summary = {
                "overall_score": 0.0,
                "external_execution": True,
                "issues_detected": [run.failure_code],
                "error_classification": "execution_error",
            }
            await self._transition_run(db, run, SkillRunState.FAILED, principal, reason=run.failure_code)
        evaluation = await self.evaluator_service.create_for_run(db, run)
        run.evaluation_summary = self.project_evaluation_summary(evaluation)
        await db.commit()
        await db.refresh(run)
        await self._ingest_learning_artifacts(db, run.id, principal)
        return run


_skill_engine_service: SkillEngineService | None = None


def get_skill_engine_service() -> SkillEngineService:
    global _skill_engine_service
    if _skill_engine_service is None:
        _skill_engine_service = SkillEngineService()
    return _skill_engine_service
