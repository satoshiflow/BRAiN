"""Foundational services for the Domain Agent layer."""

from __future__ import annotations

import hashlib
import os
import uuid
from typing import Any, Dict, Iterable, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.core.control_plane_events import record_control_plane_event

from .models import DomainAgentConfigModel
from .schemas import (
    ControlMode,
    DecisionOutcome,
    DecisionContext,
    DomainAgentConfig,
    DomainDecompositionRequest,
    DomainResolution,
    DomainReviewDecision,
    PurposeEvaluation,
    PurposeEvaluationResponse,
    RoutingDecision,
    RoutingDecisionResponse,
    DomainStatus,
    DomainSkillRunDraft,
    SensitivityClass,
    DomainReviewOutcome,
    SpecialistCandidate,
)
from .models import PurposeEvaluationModel, RoutingDecisionModel
from .models import RoutingAdaptationProposalModel, RoutingMemoryProjectionModel


class DomainAgentRegistry:
    """Small in-memory registry used as the first integration surface.

    This keeps the first implementation simple and non-breaking while the domain
    contract hardens. A later implementation may back the same interface with a
    durable store.
    """

    def __init__(self) -> None:
        self._domains: Dict[str, DomainAgentConfig] = {}

    def register(self, config: DomainAgentConfig) -> DomainAgentConfig:
        self._domains[config.domain_key] = config
        return config

    def get(self, domain_key: str) -> Optional[DomainAgentConfig]:
        return self._domains.get(domain_key)

    def list(self) -> Iterable[DomainAgentConfig]:
        return self._domains.values()

    async def register_db(self, db: AsyncSession, config: DomainAgentConfig) -> DomainAgentConfig:
        query = select(DomainAgentConfigModel).where(
            DomainAgentConfigModel.domain_key == config.domain_key,
            DomainAgentConfigModel.owner_scope == config.owner_scope,
        )
        if config.owner_scope == "tenant":
            query = query.where(DomainAgentConfigModel.tenant_id == config.tenant_id)
        else:
            query = query.where(DomainAgentConfigModel.tenant_id.is_(None))

        existing = (await db.execute(query.limit(1))).scalar_one_or_none()
        if existing is None:
            model = DomainAgentConfigModel(
                tenant_id=config.tenant_id,
                owner_scope=config.owner_scope,
                domain_key=config.domain_key,
                display_name=config.display_name,
                description=config.description,
                status=config.status.value,
                allowed_skill_keys=config.allowed_skill_keys,
                allowed_capability_keys=config.allowed_capability_keys,
                allowed_specialist_roles=config.allowed_specialist_roles,
                review_profile=config.review_profile,
                risk_profile=config.risk_profile,
                escalation_profile=config.escalation_profile,
                budget_profile=config.budget_profile.model_dump(mode="json"),
                metadata_json=config.metadata,
            )
            db.add(model)
            await db.commit()
            await db.refresh(model)
            return self._model_to_config(model)

        existing.display_name = config.display_name
        existing.description = config.description
        existing.status = config.status.value
        existing.allowed_skill_keys = config.allowed_skill_keys
        existing.allowed_capability_keys = config.allowed_capability_keys
        existing.allowed_specialist_roles = config.allowed_specialist_roles
        existing.review_profile = config.review_profile
        existing.risk_profile = config.risk_profile
        existing.escalation_profile = config.escalation_profile
        existing.budget_profile = config.budget_profile.model_dump(mode="json")
        existing.metadata_json = config.metadata
        await db.commit()
        await db.refresh(existing)
        return self._model_to_config(existing)

    async def get_db(self, db: AsyncSession, domain_key: str, tenant_id: str | None) -> Optional[DomainAgentConfig]:
        query = select(DomainAgentConfigModel).where(
            DomainAgentConfigModel.domain_key == domain_key,
            DomainAgentConfigModel.owner_scope == "tenant",
            DomainAgentConfigModel.tenant_id == tenant_id,
        )
        item = (await db.execute(query.limit(1))).scalar_one_or_none()
        if item is not None:
            return self._model_to_config(item)

        system_query = select(DomainAgentConfigModel).where(
            DomainAgentConfigModel.domain_key == domain_key,
            DomainAgentConfigModel.owner_scope == "system",
            DomainAgentConfigModel.tenant_id.is_(None),
        )
        item = (await db.execute(system_query.limit(1))).scalar_one_or_none()
        if item is not None:
            return self._model_to_config(item)
        return None

    async def list_db(self, db: AsyncSession, tenant_id: str | None) -> list[DomainAgentConfig]:
        tenant_query = select(DomainAgentConfigModel).where(
            DomainAgentConfigModel.owner_scope == "tenant",
            DomainAgentConfigModel.tenant_id == tenant_id,
        )
        system_query = select(DomainAgentConfigModel).where(
            DomainAgentConfigModel.owner_scope == "system",
            DomainAgentConfigModel.tenant_id.is_(None),
        )
        tenant_items = list((await db.execute(tenant_query)).scalars().all())
        system_items = list((await db.execute(system_query)).scalars().all())
        return [self._model_to_config(item) for item in [*tenant_items, *system_items]]

    @staticmethod
    def _model_to_config(model: DomainAgentConfigModel) -> DomainAgentConfig:
        return DomainAgentConfig(
            tenant_id=model.tenant_id,
            owner_scope=model.owner_scope,
            domain_key=model.domain_key,
            display_name=model.display_name,
            description=model.description,
            status=model.status,
            allowed_skill_keys=model.allowed_skill_keys or [],
            allowed_capability_keys=model.allowed_capability_keys or [],
            allowed_specialist_roles=model.allowed_specialist_roles or [],
            review_profile=model.review_profile or {},
            risk_profile=model.risk_profile or {},
            escalation_profile=model.escalation_profile or {},
            budget_profile=model.budget_profile or {},
            metadata=model.metadata_json or {},
        )


class DomainAgentService:
    """Base service for domain-aware orchestration.

    The service intentionally exposes only generic methods so later work can add
    domain-specific adapters without forcing a rewrite of the public contract.
    """

    def __init__(self, registry: DomainAgentRegistry) -> None:
        self.registry = registry

    def resolve_domain(self, domain_key: str) -> Optional[DomainAgentConfig]:
        return self.registry.get(domain_key)

    def decompose(self, request: DomainDecompositionRequest) -> DomainResolution:
        config = self.resolve_domain(request.domain_key)
        if config is None:
            raise ValueError(f"Unknown domain '{request.domain_key}'")
        return self.decompose_with_config(request, config)

    def decompose_with_config(
        self,
        request: DomainDecompositionRequest,
        config: DomainAgentConfig,
        selected_specialists: list[SpecialistCandidate] | None = None,
    ) -> DomainResolution:
        if config.domain_key != request.domain_key:
            raise ValueError(
                f"Domain config mismatch: request='{request.domain_key}' config='{config.domain_key}'"
            )
        if config.status.value == "blocked":
            raise PermissionError(f"Domain '{request.domain_key}' is blocked")

        selected_capabilities = [
            capability
            for capability in request.available_capabilities
            if capability in config.allowed_capability_keys
        ]

        if request.domain_key == "programming":
            return self._decompose_programming(
                request,
                config,
                selected_capabilities,
                selected_specialists,
            )

        return DomainResolution(
            domain_key=config.domain_key,
            confidence=0.5,
            selected_skill_keys=list(config.allowed_skill_keys),
            selected_capability_keys=selected_capabilities,
            selected_specialists=selected_specialists or [],
            decomposition_notes=[
                "Initial base decomposition produced by generic DomainAgentService.",
                "Replace with domain-specific decomposition logic in follow-up phases.",
            ],
            requires_supervisor_review=config.status.value != "active",
        )

    @staticmethod
    def _decompose_programming(
        request: DomainDecompositionRequest,
        config: DomainAgentConfig,
        selected_capabilities: list[str],
        selected_specialists: list[SpecialistCandidate] | None = None,
    ) -> DomainResolution:
        text = f"{request.task_name} {request.task_description}".lower()

        selected_skills: list[str] = []
        if "code.implement" in config.allowed_skill_keys:
            selected_skills.append("code.implement")

        if any(keyword in text for keyword in ["test", "coverage", "qa", "verify"]):
            if "code.test" in config.allowed_skill_keys:
                selected_skills.append("code.test")
        elif "code.test" in config.allowed_skill_keys:
            selected_skills.append("code.test")

        if any(keyword in text for keyword in ["review", "refactor", "quality", "security"]):
            if "code.review" in config.allowed_skill_keys:
                selected_skills.append("code.review")

        # Preserve order but remove duplicates
        selected_skills = list(dict.fromkeys(selected_skills))

        if selected_specialists is not None:
            specialists = selected_specialists
        else:
            max_specialists = max(1, config.budget_profile.max_specialists_per_task)
            specialists: list[SpecialistCandidate] = []
            for idx, role in enumerate(config.allowed_specialist_roles[:max_specialists]):
                specialists.append(
                    SpecialistCandidate(
                        agent_id=f"{request.domain_key}-{role}-{idx+1}",
                        role=role,
                        score=max(0.1, 1.0 - (idx * 0.1)),
                        reasons=["role whitelisted by domain profile"],
                    )
                )

        high_risk_markers = ["payment", "security", "auth", "production", "compliance"]
        requires_supervisor_review = any(marker in text for marker in high_risk_markers)

        return DomainResolution(
            domain_key=config.domain_key,
            confidence=0.75,
            selected_skill_keys=selected_skills,
            selected_capability_keys=selected_capabilities,
            selected_specialists=specialists,
            decomposition_notes=[
                "Programming decomposition applied.",
                "Includes implementation and verification defaults.",
            ],
            requires_supervisor_review=requires_supervisor_review,
        )

    async def select_specialists(
        self,
        db: AsyncSession | None,
        config: DomainAgentConfig,
    ) -> list[SpecialistCandidate]:
        """Resolve specialist candidates from Agent Management.

        Falls back to static domain role synthesis when DB/agent registry is not
        available.
        """
        max_specialists = max(1, config.budget_profile.max_specialists_per_task)
        if not config.allowed_specialist_roles:
            return []

        if db is None:
            return self._fallback_specialists(config, max_specialists)

        try:
            from app.modules.agent_management.models import AgentModel, AgentStatus

            query = (
                select(AgentModel)
                .where(AgentModel.agent_type.in_(config.allowed_specialist_roles))
                .where(AgentModel.status.in_([AgentStatus.ACTIVE, AgentStatus.DEGRADED]))
                .order_by(AgentModel.last_heartbeat.desc().nullslast(), AgentModel.registered_at.desc())
                .limit(max_specialists)
            )
            rows = list((await db.execute(query)).scalars().all())
            if not rows:
                return self._fallback_specialists(config, max_specialists)

            candidates: list[SpecialistCandidate] = []
            for idx, agent in enumerate(rows):
                candidates.append(
                    SpecialistCandidate(
                        agent_id=agent.agent_id,
                        role=agent.agent_type,
                        score=max(0.1, 1.0 - (idx * 0.1)),
                        reasons=[
                            "agent matched allowed_specialist_roles",
                            f"agent status={agent.status.value if hasattr(agent.status, 'value') else agent.status}",
                        ],
                    )
                )
            return candidates
        except Exception as exc:  # pragma: no cover
            logger.warning("[DomainAgent] specialist lookup failed, using fallback: %s", exc)
            return self._fallback_specialists(config, max_specialists)

    @staticmethod
    def _fallback_specialists(
        config: DomainAgentConfig,
        max_specialists: int,
    ) -> list[SpecialistCandidate]:
        candidates: list[SpecialistCandidate] = []
        for idx, role in enumerate(config.allowed_specialist_roles[:max_specialists]):
            candidates.append(
                SpecialistCandidate(
                    agent_id=f"fallback-{config.domain_key}-{role}-{idx+1}",
                    role=role,
                    score=max(0.1, 1.0 - (idx * 0.1)),
                    reasons=["fallback specialist synthesized from domain profile"],
                )
            )
        return candidates

    def review_resolution(self, resolution: DomainResolution) -> DomainReviewDecision:
        if resolution.domain_key == "programming":
            return self._review_programming_resolution(resolution)

        if resolution.requires_supervisor_review:
            return DomainReviewDecision(
                domain_key=resolution.domain_key,
                outcome=DomainReviewOutcome.ESCALATE,
                summary="Domain requires supervisor review before execution.",
                reasons=["Domain is not fully active or produced a gated resolution."],
                should_escalate=True,
                recommended_next_actions=["request_supervisor_review"],
            )

        return DomainReviewDecision(
            domain_key=resolution.domain_key,
            outcome=DomainReviewOutcome.PASS,
            summary="Domain resolution passed base review.",
            reasons=["No base-level escalation trigger was detected."],
            should_escalate=False,
            recommended_next_actions=["create_skill_runs"],
        )

    @staticmethod
    def _as_decision_outcome(value: str) -> DecisionOutcome:
        try:
            return DecisionOutcome(value)
        except ValueError:
            logger.warning("[DomainAgent] unknown purpose outcome '%s', defaulting reject", value)
            return DecisionOutcome.REJECT

    @staticmethod
    async def _evaluate_policy_snapshot(
        *,
        principal: Principal,
        action: str,
        resource: str,
        params: dict,
    ) -> dict:
        try:
            from app.modules.policy.schemas import PolicyEvaluationContext
            from app.modules.policy.service import get_policy_engine
        except Exception as exc:  # pragma: no cover
            logger.warning("[DomainAgent] policy module unavailable for evaluation: %s", exc)
            return {
                "available": False,
                "allowed": True,
                "requires_audit": False,
                "reason": "policy_module_unavailable",
            }

        try:
            engine = get_policy_engine()
            result = await engine.evaluate(
                PolicyEvaluationContext(
                    agent_id=principal.principal_id,
                    agent_role=principal.roles[0] if principal.roles else None,
                    action=action,
                    resource=resource,
                    params=params,
                    environment={
                        "tenant_id": principal.tenant_id,
                        "principal_type": principal.principal_type.value,
                    },
                )
            )
            no_policy_match = (
                isinstance(result.reason, str)
                and "No matching policies configured" in result.reason
            )
            return {
                "available": True,
                "allowed": bool(result.allowed) if not no_policy_match else True,
                "requires_audit": bool(result.requires_audit),
                "effect": result.effect.value,
                "reason": result.reason,
                "policy_defaulted": no_policy_match,
            }
        except Exception as exc:  # pragma: no cover
            logger.warning("[DomainAgent] policy evaluation failed, continuing with guarded fallback: %s", exc)
            return {
                "available": True,
                "allowed": True,
                "requires_audit": True,
                "reason": f"policy_evaluation_error:{exc}",
            }

    @staticmethod
    def _derive_control_mode(
        *,
        sensitivity_class: SensitivityClass,
        outcome: DecisionOutcome,
        policy_allowed: bool,
        policy_requires_audit: bool,
    ) -> ControlMode:
        if not policy_allowed:
            return ControlMode.HUMAN_REQUIRED
        if sensitivity_class == SensitivityClass.SENSITIVE_CORE:
            return ControlMode.HUMAN_REQUIRED
        if sensitivity_class == SensitivityClass.SENSITIVE and outcome == DecisionOutcome.MODIFIED_ACCEPT:
            return ControlMode.HUMAN_REQUIRED
        if sensitivity_class == SensitivityClass.SENSITIVE:
            return ControlMode.HUMAN_OPTIONAL
        if outcome == DecisionOutcome.MODIFIED_ACCEPT:
            return ControlMode.HUMAN_OPTIONAL
        if policy_requires_audit:
            return ControlMode.HUMAN_OPTIONAL
        return ControlMode.BRAIN_FIRST

    @classmethod
    def _to_purpose_evaluation_response(cls, model: PurposeEvaluationModel) -> PurposeEvaluationResponse:
        return PurposeEvaluationResponse(
            id=str(model.id),
            tenant_id=model.tenant_id,
            decision_context_id=model.decision_context_id,
            purpose_profile_id=model.purpose_profile_id,
            outcome=cls._as_decision_outcome(model.outcome),
            purpose_score=model.purpose_score,
            sovereignty_score=model.sovereignty_score,
            requires_human_review=model.requires_human_review,
            required_modifications=model.required_modifications or [],
            reasons=model.reasons or [],
            governance_snapshot=model.governance_snapshot or {},
            mission_id=model.mission_id,
            correlation_id=model.correlation_id,
            created_by=model.created_by,
        )

    @staticmethod
    def _to_routing_decision_response(model: RoutingDecisionModel) -> RoutingDecisionResponse:
        return RoutingDecisionResponse(
            id=str(model.id),
            tenant_id=model.tenant_id,
            decision_context_id=model.decision_context_id,
            task_profile_id=model.task_profile_id,
            purpose_evaluation_id=model.purpose_evaluation_id,
            worker_candidates=model.worker_candidates or [],
            filtered_candidates=model.filtered_candidates or [],
            scoring_breakdown=model.scoring_breakdown or {},
            selected_worker=model.selected_worker,
            selected_skill_or_plan=model.selected_skill_or_plan,
            strategy=model.strategy,
            reasoning=model.reasoning,
            governance_snapshot=model.governance_snapshot or {},
            mission_id=model.mission_id,
            correlation_id=model.correlation_id,
            created_by=model.created_by,
        )

    @staticmethod
    def _to_routing_memory_response(model: RoutingMemoryProjectionModel):
        from .schemas import RoutingMemoryProjectionResponse

        return RoutingMemoryProjectionResponse(
            id=str(model.id),
            tenant_id=model.tenant_id,
            task_profile_id=model.task_profile_id,
            task_profile_fingerprint=model.task_profile_fingerprint,
            worker_outcome_history=model.worker_outcome_history or [],
            summary_metrics=model.summary_metrics or {},
            routing_lessons=model.routing_lessons or [],
            sample_size=model.sample_size or 0,
            derived_from_runs=[str(item) for item in (model.derived_from_runs or [])],
        )

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_routing_adaptation_response(model: RoutingAdaptationProposalModel):
        from .schemas import RoutingAdaptationProposalResponse

        return RoutingAdaptationProposalResponse(
            id=str(model.id),
            tenant_id=model.tenant_id,
            task_profile_id=model.task_profile_id,
            routing_memory_id=str(model.routing_memory_id)
            if model.routing_memory_id
            else None,
            proposed_changes=model.proposed_changes or {},
            status=model.status,
            sandbox_validated=model.sandbox_validated,
            validation_evidence=model.validation_evidence or {},
            block_reason=model.block_reason,
            created_by=model.created_by,
        )

    @staticmethod
    def _build_task_profile_fingerprint(task_profile_id: str) -> str:
        digest = hashlib.sha1(task_profile_id.encode("utf-8")).hexdigest()[:24]
        return f"task:{task_profile_id}:{digest}"

    @staticmethod
    def _derive_routing_lessons(worker_rows: list[dict[str, Any]]) -> list[str]:
        if not worker_rows:
            return ["Insufficient data for routing lesson extraction"]
        sorted_rows = sorted(
            worker_rows,
            key=lambda row: (
                row.get("success_rate", 0.0),
                -1.0 * (row.get("avg_cost") or 0.0),
            ),
            reverse=True,
        )
        top = sorted_rows[0]
        lessons = [
            f"Best observed worker: {top.get('worker_id')} with success_rate={top.get('success_rate', 0.0):.3f}",
            f"Sampled workers: {len(worker_rows)}",
        ]
        low_cost = min(worker_rows, key=lambda row: row.get("avg_cost") or 999999.0)
        lessons.append(
            f"Most cost-efficient worker: {low_cost.get('worker_id')} with avg_cost={low_cost.get('avg_cost') or 0.0:.3f}"
        )
        return lessons

    async def create_purpose_evaluation(
        self,
        db: AsyncSession,
        *,
        decision_context: DecisionContext,
        evaluation: PurposeEvaluation,
        principal: Principal,
    ) -> PurposeEvaluationResponse:
        policy_snapshot = await self._evaluate_policy_snapshot(
            principal=principal,
            action="purpose.evaluate",
            resource=f"purpose_profile:{evaluation.purpose_profile_id}",
            params={
                "decision_context_id": decision_context.decision_context_id,
                "sensitivity_class": decision_context.sensitivity_class.value,
                "outcome": evaluation.outcome.value,
            },
        )
        control_mode = self._derive_control_mode(
            sensitivity_class=decision_context.sensitivity_class,
            outcome=evaluation.outcome,
            policy_allowed=bool(policy_snapshot.get("allowed", True)),
            policy_requires_audit=bool(policy_snapshot.get("requires_audit", False)),
        )
        requires_human_review = control_mode == ControlMode.HUMAN_REQUIRED
        merged_governance_snapshot = {
            **(evaluation.governance_snapshot or {}),
            "policy": policy_snapshot,
            "control_mode": control_mode.value,
            "autonomy_mode": "brain_first",
        }
        model = PurposeEvaluationModel(
            tenant_id=principal.tenant_id,
            decision_context_id=decision_context.decision_context_id,
            purpose_profile_id=evaluation.purpose_profile_id,
            outcome=evaluation.outcome.value,
            purpose_score=evaluation.purpose_score,
            sovereignty_score=evaluation.sovereignty_score,
            requires_human_review=requires_human_review,
            required_modifications=evaluation.required_modifications,
            reasons=evaluation.reasons,
            governance_snapshot=merged_governance_snapshot,
            mission_id=decision_context.mission_id,
            correlation_id=decision_context.correlation_id,
            created_by=principal.principal_id,
        )
        db.add(model)
        await db.flush()
        await record_control_plane_event(
            db=db,
            tenant_id=principal.tenant_id,
            entity_type="purpose_evaluation",
            entity_id=str(model.id),
            event_type="purpose.evaluation.created.v1",
            correlation_id=decision_context.correlation_id,
            mission_id=decision_context.mission_id,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "decision_context_id": decision_context.decision_context_id,
                "purpose_profile_id": evaluation.purpose_profile_id,
                "outcome": evaluation.outcome.value,
                "requires_human_review": requires_human_review,
                "control_mode": control_mode.value,
            },
            audit_required=True,
            audit_action="purpose_evaluation_create",
            audit_message="Purpose evaluation created",
        )
        if evaluation.outcome == DecisionOutcome.REJECT:
            await record_control_plane_event(
                db=db,
                tenant_id=principal.tenant_id,
                entity_type="purpose_evaluation",
                entity_id=str(model.id),
                event_type="purpose.evaluation.rejected.v1",
                correlation_id=decision_context.correlation_id,
                mission_id=decision_context.mission_id,
                actor_id=principal.principal_id,
                actor_type=principal.principal_type.value,
                payload={"decision_context_id": decision_context.decision_context_id},
                audit_required=True,
                audit_action="purpose_evaluation_reject",
                audit_message="Purpose evaluation rejected",
            )
        if requires_human_review:
            await record_control_plane_event(
                db=db,
                tenant_id=principal.tenant_id,
                entity_type="purpose_evaluation",
                entity_id=str(model.id),
                event_type="purpose.evaluation.human_review_required.v1",
                correlation_id=decision_context.correlation_id,
                mission_id=decision_context.mission_id,
                actor_id=principal.principal_id,
                actor_type=principal.principal_type.value,
                payload={
                    "decision_context_id": decision_context.decision_context_id,
                    "control_mode": control_mode.value,
                },
                audit_required=True,
                audit_action="purpose_evaluation_human_review_required",
                audit_message="Purpose evaluation requires human review",
            )
        await db.commit()
        await db.refresh(model)
        return self._to_purpose_evaluation_response(model)

    async def get_purpose_evaluation(
        self,
        db: AsyncSession,
        *,
        evaluation_id: str,
        tenant_id: str | None,
    ) -> PurposeEvaluationResponse | None:
        try:
            identifier = uuid.UUID(evaluation_id)
        except (TypeError, ValueError):
            return None
        model = await db.get(PurposeEvaluationModel, identifier)
        if model is None:
            return None
        if model.tenant_id and model.tenant_id != tenant_id:
            return None
        return self._to_purpose_evaluation_response(model)

    async def list_purpose_evaluations(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
        mission_id: str | None = None,
        limit: int = 100,
    ) -> list[PurposeEvaluationResponse]:
        query = select(PurposeEvaluationModel)
        if tenant_id:
            query = query.where(PurposeEvaluationModel.tenant_id == tenant_id)
        else:
            query = query.where(PurposeEvaluationModel.tenant_id.is_(None))
        if mission_id:
            query = query.where(PurposeEvaluationModel.mission_id == mission_id)
        query = query.order_by(PurposeEvaluationModel.created_at.desc()).limit(max(1, min(limit, 500)))
        rows = list((await db.execute(query)).scalars().all())
        return [self._to_purpose_evaluation_response(model) for model in rows]

    async def create_routing_decision(
        self,
        db: AsyncSession,
        *,
        decision_context: DecisionContext,
        decision: RoutingDecision,
        principal: Principal,
    ) -> RoutingDecisionResponse:
        policy_snapshot = await self._evaluate_policy_snapshot(
            principal=principal,
            action="routing.decision.create",
            resource=f"task_profile:{decision.task_profile_id}",
            params={
                "decision_context_id": decision_context.decision_context_id,
                "sensitivity_class": decision_context.sensitivity_class.value,
                "selected_worker": decision.selected_worker,
                "strategy": decision.strategy,
            },
        )
        purpose_requires_human_review = False
        if decision.purpose_evaluation_id:
            try:
                purpose_identifier = uuid.UUID(decision.purpose_evaluation_id)
                purpose_record = await db.get(PurposeEvaluationModel, purpose_identifier)
                if purpose_record is not None:
                    purpose_requires_human_review = bool(purpose_record.requires_human_review)
            except (TypeError, ValueError):
                purpose_requires_human_review = False

        control_mode = self._derive_control_mode(
            sensitivity_class=decision_context.sensitivity_class,
            outcome=DecisionOutcome.MODIFIED_ACCEPT if purpose_requires_human_review else DecisionOutcome.ACCEPT,
            policy_allowed=bool(policy_snapshot.get("allowed", True)),
            policy_requires_audit=bool(policy_snapshot.get("requires_audit", False)),
        )
        if purpose_requires_human_review and control_mode != ControlMode.HUMAN_REQUIRED:
            control_mode = ControlMode.HUMAN_REQUIRED

        governance_snapshot = {
            "policy": policy_snapshot,
            "control_mode": control_mode.value,
            "autonomy_mode": "brain_first",
            "purpose_requires_human_review": purpose_requires_human_review,
        }
        model = RoutingDecisionModel(
            tenant_id=principal.tenant_id,
            decision_context_id=decision_context.decision_context_id,
            task_profile_id=decision.task_profile_id,
            purpose_evaluation_id=decision.purpose_evaluation_id,
            worker_candidates=decision.worker_candidates,
            filtered_candidates=decision.filtered_candidates,
            scoring_breakdown=decision.scoring_breakdown,
            selected_worker=decision.selected_worker,
            selected_skill_or_plan=decision.selected_skill_or_plan,
            strategy=decision.strategy,
            reasoning=decision.reasoning,
            governance_snapshot=governance_snapshot,
            mission_id=decision_context.mission_id,
            correlation_id=decision_context.correlation_id,
            created_by=principal.principal_id,
        )
        db.add(model)
        await db.flush()
        await record_control_plane_event(
            db=db,
            tenant_id=principal.tenant_id,
            entity_type="routing_decision",
            entity_id=str(model.id),
            event_type="routing.decision.created.v1",
            correlation_id=decision_context.correlation_id,
            mission_id=decision_context.mission_id,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "decision_context_id": decision_context.decision_context_id,
                "task_profile_id": decision.task_profile_id,
                "selected_worker": decision.selected_worker,
                "strategy": decision.strategy,
                "control_mode": control_mode.value,
            },
            audit_required=True,
            audit_action="routing_decision_create",
            audit_message="Routing decision created",
        )
        if control_mode == ControlMode.HUMAN_REQUIRED:
            await record_control_plane_event(
                db=db,
                tenant_id=principal.tenant_id,
                entity_type="routing_decision",
                entity_id=str(model.id),
                event_type="routing.decision.escalated.v1",
                correlation_id=decision_context.correlation_id,
                mission_id=decision_context.mission_id,
                actor_id=principal.principal_id,
                actor_type=principal.principal_type.value,
                payload={
                    "decision_context_id": decision_context.decision_context_id,
                    "control_mode": control_mode.value,
                },
                audit_required=True,
                audit_action="routing_decision_escalate",
                audit_message="Routing decision requires human review",
            )
        await db.commit()
        await db.refresh(model)
        return self._to_routing_decision_response(model)

    async def get_routing_decision(
        self,
        db: AsyncSession,
        *,
        routing_decision_id: str,
        tenant_id: str | None,
    ) -> RoutingDecisionResponse | None:
        try:
            identifier = uuid.UUID(routing_decision_id)
        except (TypeError, ValueError):
            return None
        model = await db.get(RoutingDecisionModel, identifier)
        if model is None:
            return None
        if model.tenant_id and model.tenant_id != tenant_id:
            return None
        return self._to_routing_decision_response(model)

    async def list_routing_decisions(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
        mission_id: str | None = None,
        limit: int = 100,
    ) -> list[RoutingDecisionResponse]:
        query = select(RoutingDecisionModel)
        if tenant_id:
            query = query.where(RoutingDecisionModel.tenant_id == tenant_id)
        else:
            query = query.where(RoutingDecisionModel.tenant_id.is_(None))
        if mission_id:
            query = query.where(RoutingDecisionModel.mission_id == mission_id)
        query = query.order_by(RoutingDecisionModel.created_at.desc()).limit(max(1, min(limit, 500)))
        rows = list((await db.execute(query)).scalars().all())
        return [self._to_routing_decision_response(model) for model in rows]

    async def rebuild_routing_memory_projection(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
        task_profile_id: str,
        principal: Principal,
        limit: int = 200,
    ):
        from app.modules.skill_engine.models import SkillRunModel

        query = select(RoutingDecisionModel).where(
            RoutingDecisionModel.task_profile_id == task_profile_id
        )
        if tenant_id:
            query = query.where(RoutingDecisionModel.tenant_id == tenant_id)
        else:
            query = query.where(RoutingDecisionModel.tenant_id.is_(None))
        query = query.order_by(RoutingDecisionModel.created_at.desc()).limit(max(1, min(limit, 2000)))
        routing_rows = list((await db.execute(query)).scalars().all())

        decision_ids = {str(item.id) for item in routing_rows}
        run_query = select(SkillRunModel)
        if tenant_id:
            run_query = run_query.where(SkillRunModel.tenant_id == tenant_id)
        else:
            run_query = run_query.where(SkillRunModel.tenant_id.is_(None))
        run_query = run_query.order_by(SkillRunModel.created_at.desc()).limit(max(500, len(decision_ids) * 5))
        runs = list((await db.execute(run_query)).scalars().all())

        run_index: dict[str, list[Any]] = {}
        for run in runs:
            upstream = ((run.plan_snapshot or {}).get("upstream_decision") or {})
            rid = upstream.get("routing_decision_id")
            if isinstance(rid, str) and rid in decision_ids:
                run_index.setdefault(rid, []).append(run)

        worker_stats: dict[str, dict[str, Any]] = {}
        derived_runs: list[str] = []
        for decision in routing_rows:
            worker_id = decision.selected_worker or "unassigned"
            bucket = worker_stats.setdefault(
                worker_id,
                {
                    "worker_id": worker_id,
                    "attempts": 0,
                    "successes": 0,
                    "cost_total": 0.0,
                    "cost_count": 0,
                    "latency_total_seconds": 0.0,
                    "latency_count": 0,
                },
            )
            runs_for_decision = run_index.get(str(decision.id), [])
            for run in runs_for_decision:
                derived_runs.append(str(run.id))
                bucket["attempts"] += 1
                if run.state == "succeeded":
                    bucket["successes"] += 1
                cost_value = self._safe_float(run.cost_actual)
                if cost_value is None:
                    cost_value = self._safe_float(run.cost_estimate)
                if cost_value is not None:
                    bucket["cost_total"] += cost_value
                    bucket["cost_count"] += 1
                if run.started_at and run.finished_at:
                    delta = (run.finished_at - run.started_at).total_seconds()
                    if delta >= 0:
                        bucket["latency_total_seconds"] += delta
                        bucket["latency_count"] += 1

        worker_rows: list[dict[str, Any]] = []
        total_attempts = 0
        total_successes = 0
        for worker_id, stats in worker_stats.items():
            attempts = int(stats["attempts"])
            successes = int(stats["successes"])
            total_attempts += attempts
            total_successes += successes
            avg_cost = (
                round(stats["cost_total"] / stats["cost_count"], 6)
                if stats["cost_count"] > 0
                else None
            )
            avg_latency = (
                round(stats["latency_total_seconds"] / stats["latency_count"], 6)
                if stats["latency_count"] > 0
                else None
            )
            worker_rows.append(
                {
                    "worker_id": worker_id,
                    "attempts": attempts,
                    "success_rate": round((successes / attempts), 6) if attempts > 0 else 0.0,
                    "avg_cost": avg_cost,
                    "avg_latency_seconds": avg_latency,
                }
            )

        worker_rows.sort(
            key=lambda row: (row.get("success_rate", 0.0), -1.0 * (row.get("avg_cost") or 0.0)),
            reverse=True,
        )
        summary_metrics = {
            "sample_size": total_attempts,
            "overall_success_rate": round((total_successes / total_attempts), 6)
            if total_attempts > 0
            else 0.0,
            "worker_count": len(worker_rows),
        }

        fingerprint = self._build_task_profile_fingerprint(task_profile_id)
        existing_query = select(RoutingMemoryProjectionModel).where(
            RoutingMemoryProjectionModel.task_profile_fingerprint == fingerprint
        )
        if tenant_id:
            existing_query = existing_query.where(RoutingMemoryProjectionModel.tenant_id == tenant_id)
        else:
            existing_query = existing_query.where(RoutingMemoryProjectionModel.tenant_id.is_(None))
        existing = (await db.execute(existing_query.limit(1))).scalar_one_or_none()
        if existing is None:
            existing = RoutingMemoryProjectionModel(
                tenant_id=tenant_id,
                task_profile_id=task_profile_id,
                task_profile_fingerprint=fingerprint,
                worker_outcome_history=worker_rows,
                summary_metrics=summary_metrics,
                routing_lessons=self._derive_routing_lessons(worker_rows),
                sample_size=total_attempts,
                derived_from_runs=derived_runs,
            )
            db.add(existing)
        else:
            existing.worker_outcome_history = worker_rows
            existing.summary_metrics = summary_metrics
            existing.routing_lessons = self._derive_routing_lessons(worker_rows)
            existing.sample_size = total_attempts
            existing.derived_from_runs = derived_runs
        await record_control_plane_event(
            db=db,
            tenant_id=tenant_id,
            entity_type="routing_memory_projection",
            entity_id=str(existing.id),
            event_type="routing.memory.rebuilt.v1",
            correlation_id=None,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "task_profile_id": task_profile_id,
                "sample_size": total_attempts,
                "worker_count": len(worker_rows),
            },
            audit_required=True,
            audit_action="routing_memory_rebuild",
            audit_message="Routing memory projection rebuilt",
        )
        await db.commit()
        await db.refresh(existing)
        return self._to_routing_memory_response(existing)

    async def list_routing_memory_projections(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
        task_profile_id: str | None = None,
        limit: int = 100,
    ):
        query = select(RoutingMemoryProjectionModel)
        if tenant_id:
            query = query.where(RoutingMemoryProjectionModel.tenant_id == tenant_id)
        else:
            query = query.where(RoutingMemoryProjectionModel.tenant_id.is_(None))
        if task_profile_id:
            query = query.where(RoutingMemoryProjectionModel.task_profile_id == task_profile_id)
        query = query.order_by(RoutingMemoryProjectionModel.updated_at.desc()).limit(max(1, min(limit, 500)))
        rows = list((await db.execute(query)).scalars().all())
        return [self._to_routing_memory_response(row) for row in rows]

    async def get_routing_memory_projection(
        self,
        db: AsyncSession,
        *,
        projection_id: str,
        tenant_id: str | None,
    ):
        try:
            identifier = uuid.UUID(projection_id)
        except (TypeError, ValueError):
            return None
        item = await db.get(RoutingMemoryProjectionModel, identifier)
        if item is None:
            return None
        if item.tenant_id and item.tenant_id != tenant_id:
            return None
        return self._to_routing_memory_response(item)

    async def replay_routing_comparison(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
        task_profile_id: str,
    ):
        from .schemas import RoutingReplayComparisonResponse

        rows = await self.list_routing_memory_projections(
            db,
            tenant_id=tenant_id,
            task_profile_id=task_profile_id,
            limit=1,
        )
        if not rows:
            return RoutingReplayComparisonResponse(
                task_profile_id=task_profile_id,
                sample_size=0,
                recommendation_reason="No routing memory projection available",
            )

        memory = rows[0]
        worker_rows = memory.worker_outcome_history
        if not worker_rows:
            return RoutingReplayComparisonResponse(
                task_profile_id=task_profile_id,
                sample_size=0,
                recommendation_reason="No worker outcomes recorded",
            )

        baseline = max(worker_rows, key=lambda row: row.get("attempts", 0))
        recommended = max(
            worker_rows,
            key=lambda row: (row.get("success_rate", 0.0), -1.0 * (row.get("avg_cost") or 0.0)),
        )
        return RoutingReplayComparisonResponse(
            task_profile_id=task_profile_id,
            sample_size=int(memory.sample_size or 0),
            baseline_worker=baseline.get("worker_id"),
            recommended_worker=recommended.get("worker_id"),
            baseline_success_rate=float(baseline.get("success_rate") or 0.0),
            recommended_success_rate=float(recommended.get("success_rate") or 0.0),
            baseline_avg_cost=self._safe_float(baseline.get("avg_cost")),
            recommended_avg_cost=self._safe_float(recommended.get("avg_cost")),
            recommendation_reason="Recommendation favors highest success_rate with cost tie-break",
        )

    async def create_routing_adaptation_proposal(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
        principal: Principal,
        task_profile_id: str,
        routing_memory_id: str | None,
        proposed_changes: dict[str, Any],
        sandbox_validated: bool,
        validation_evidence: dict[str, Any],
    ):
        from app.modules.evolution_control.service import get_evolution_control_service

        sandbox_mode = os.getenv("BRAIN_SANDBOX_MODE", "false").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        block_reason: str | None = None
        status = "review"
        if not sandbox_mode:
            block_reason = "sandbox_mode_required"
            status = "blocked"
        elif not sandbox_validated:
            block_reason = "sandbox_validation_required"
            status = "blocked"

        if tenant_id:
            freeze = await get_evolution_control_service().get_freeze_status(db, tenant_id)
            if freeze.adaptive_frozen == "true":
                block_reason = "adaptive_frozen"
                status = "blocked"

        routing_memory_uuid = None
        if routing_memory_id:
            try:
                routing_memory_uuid = uuid.UUID(routing_memory_id)
            except (TypeError, ValueError):
                block_reason = "invalid_routing_memory_id"
                status = "blocked"

        model = RoutingAdaptationProposalModel(
            tenant_id=tenant_id,
            task_profile_id=task_profile_id,
            routing_memory_id=routing_memory_uuid,
            proposed_changes=proposed_changes,
            status=status,
            sandbox_validated=sandbox_validated,
            validation_evidence=validation_evidence,
            block_reason=block_reason,
            created_by=principal.principal_id,
        )
        db.add(model)
        await db.flush()
        await record_control_plane_event(
            db=db,
            tenant_id=tenant_id,
            entity_type="routing_adaptation",
            entity_id=str(model.id),
            event_type=(
                "routing.adaptation.proposed.v1"
                if status != "blocked"
                else "routing.adaptation.blocked.v1"
            ),
            correlation_id=None,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "task_profile_id": task_profile_id,
                "status": status,
                "block_reason": block_reason,
            },
            audit_required=True,
            audit_action="routing_adaptation_propose",
            audit_message="Routing adaptation proposal created",
            severity="warning" if status == "blocked" else "info",
        )
        await db.commit()
        await db.refresh(model)
        return self._to_routing_adaptation_response(model)

    async def get_routing_adaptation_proposal(
        self,
        db: AsyncSession,
        *,
        proposal_id: str,
        tenant_id: str | None,
    ):
        try:
            identifier = uuid.UUID(proposal_id)
        except (TypeError, ValueError):
            return None
        model = await db.get(RoutingAdaptationProposalModel, identifier)
        if model is None:
            return None
        if model.tenant_id and model.tenant_id != tenant_id:
            return None
        return self._to_routing_adaptation_response(model)

    async def list_routing_adaptation_proposals(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
        task_profile_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ):
        query = select(RoutingAdaptationProposalModel)
        if tenant_id:
            query = query.where(RoutingAdaptationProposalModel.tenant_id == tenant_id)
        else:
            query = query.where(RoutingAdaptationProposalModel.tenant_id.is_(None))
        if task_profile_id:
            query = query.where(
                RoutingAdaptationProposalModel.task_profile_id == task_profile_id
            )
        if status:
            query = query.where(RoutingAdaptationProposalModel.status == status)
        query = query.order_by(RoutingAdaptationProposalModel.updated_at.desc()).limit(
            max(1, min(limit, 500))
        )
        rows = list((await db.execute(query)).scalars().all())
        return [self._to_routing_adaptation_response(row) for row in rows]

    async def transition_routing_adaptation_proposal(
        self,
        db: AsyncSession,
        *,
        proposal_id: str,
        tenant_id: str | None,
        principal: Principal,
        status: str,
        block_reason: str | None,
        validation_evidence_patch: dict[str, Any],
    ):
        try:
            identifier = uuid.UUID(proposal_id)
        except (TypeError, ValueError):
            raise ValueError("Invalid proposal id") from None

        model = await db.get(RoutingAdaptationProposalModel, identifier)
        if model is None or (model.tenant_id and model.tenant_id != tenant_id):
            raise ValueError("Routing adaptation proposal not found")

        allowed_transitions = {
            "draft": {"review", "blocked"},
            "review": {"approved", "rejected", "blocked"},
            "approved": {"applied", "blocked"},
            "blocked": {"review", "rejected"},
            "rejected": set(),
            "applied": set(),
        }
        next_status = status.strip().lower()
        if next_status not in {"draft", "review", "approved", "blocked", "rejected", "applied"}:
            raise ValueError("Invalid adaptation proposal status")
        current_status = model.status
        if next_status not in allowed_transitions.get(current_status, set()):
            raise ValueError(
                f"Illegal adaptation status transition {current_status} -> {next_status}"
            )

        if next_status in {"approved", "applied"} and not bool(model.sandbox_validated):
            raise ValueError("Sandbox validation required before approval or apply")

        model.status = next_status
        if block_reason is not None:
            model.block_reason = block_reason
        merged_validation = {**(model.validation_evidence or {})}
        merged_validation.update(validation_evidence_patch or {})
        model.validation_evidence = merged_validation

        await record_control_plane_event(
            db=db,
            tenant_id=tenant_id,
            entity_type="routing_adaptation",
            entity_id=str(model.id),
            event_type="routing.adaptation.transitioned.v1",
            correlation_id=None,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "from_status": current_status,
                "to_status": next_status,
                "task_profile_id": model.task_profile_id,
            },
            audit_required=True,
            audit_action="routing_adaptation_transition",
            audit_message="Routing adaptation proposal transitioned",
        )
        await db.commit()
        await db.refresh(model)
        return self._to_routing_adaptation_response(model)

    async def simulate_routing_adaptation(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
        task_profile_id: str,
        proposed_changes: dict[str, Any],
    ):
        from .schemas import RoutingAdaptationSimulationResponse

        comparison = await self.replay_routing_comparison(
            db,
            tenant_id=tenant_id,
            task_profile_id=task_profile_id,
        )
        sandbox_mode = os.getenv("BRAIN_SANDBOX_MODE", "false").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        projected_delta = {
            "success_rate_gain": round(
                comparison.recommended_success_rate - comparison.baseline_success_rate,
                6,
            ),
            "avg_cost_delta": (
                None
                if comparison.baseline_avg_cost is None
                or comparison.recommended_avg_cost is None
                else round(
                    comparison.recommended_avg_cost - comparison.baseline_avg_cost,
                    6,
                )
            ),
            "proposed_change_keys": sorted(list((proposed_changes or {}).keys())),
        }
        notes = [comparison.recommendation_reason]
        if not sandbox_mode:
            notes.append("Sandbox mode is disabled; simulation is informational only")
        return RoutingAdaptationSimulationResponse(
            task_profile_id=task_profile_id,
            sandbox_mode=sandbox_mode,
            baseline_worker=comparison.baseline_worker,
            recommended_worker=comparison.recommended_worker,
            baseline_success_rate=comparison.baseline_success_rate,
            recommended_success_rate=comparison.recommended_success_rate,
            baseline_avg_cost=comparison.baseline_avg_cost,
            recommended_avg_cost=comparison.recommended_avg_cost,
            projected_delta=projected_delta,
            notes=notes,
        )

    @staticmethod
    def _review_programming_resolution(resolution: DomainResolution) -> DomainReviewDecision:
        selected = set(resolution.selected_skill_keys)

        if "code.implement" not in selected:
            return DomainReviewDecision(
                domain_key=resolution.domain_key,
                outcome=DomainReviewOutcome.REJECT,
                summary="Programming resolution missing implementation skill.",
                reasons=["code.implement is required for programming domain tasks"],
                should_escalate=False,
                recommended_next_actions=["adjust_decomposition"],
            )

        if "code.test" not in selected:
            return DomainReviewDecision(
                domain_key=resolution.domain_key,
                outcome=DomainReviewOutcome.REVISE,
                summary="Programming resolution missing test coverage path.",
                reasons=["code.test should be present for domain quality baseline"],
                should_escalate=False,
                recommended_next_actions=["add_test_skill"],
            )

        if resolution.requires_supervisor_review:
            return DomainReviewDecision(
                domain_key=resolution.domain_key,
                outcome=DomainReviewOutcome.ESCALATE,
                summary="Programming resolution flagged for supervisor review.",
                reasons=["high-risk markers detected for programming task"],
                should_escalate=True,
                recommended_next_actions=["request_supervisor_review"],
            )

        return DomainReviewDecision(
            domain_key=resolution.domain_key,
            outcome=DomainReviewOutcome.PASS,
            summary="Programming resolution passed domain quality checks.",
            reasons=["implementation and testing paths are present"],
            should_escalate=False,
            recommended_next_actions=["create_skill_runs"],
        )

    @staticmethod
    def build_skill_run_drafts(
        *,
        request: DomainDecompositionRequest,
        config: DomainAgentConfig,
        resolution: DomainResolution,
        trigger_type,
        mission_id: str | None,
        causation_id: str | None,
        input_payload: dict,
        tenant_id: str | None,
        decision_context_id: str | None = None,
        purpose_evaluation_id: str | None = None,
        routing_decision_id: str | None = None,
        governance_snapshot: dict[str, Any] | None = None,
    ) -> list[DomainSkillRunDraft]:
        """Build deterministic SkillRun drafts from domain resolution."""
        drafts: list[DomainSkillRunDraft] = []
        max_parallel_runs = max(1, config.budget_profile.max_parallel_runs)
        selected_skill_keys = resolution.selected_skill_keys[:max_parallel_runs]
        for idx, skill_key in enumerate(selected_skill_keys, start=1):
            identity = "|".join(
                [
                    request.domain_key,
                    request.task_name,
                    skill_key,
                    mission_id or request.mission_id or "",
                    tenant_id or request.tenant_id or "",
                    str(idx),
                ]
            )
            digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:32]
            drafts.append(
                DomainSkillRunDraft(
                    skill_key=skill_key,
                    idempotency_key=f"domain-{request.domain_key}-{digest}",
                    trigger_type=trigger_type,
                    mission_id=mission_id or request.mission_id,
                    causation_id=causation_id,
                    input_payload=input_payload,
                    decision_context_id=decision_context_id,
                    purpose_evaluation_id=purpose_evaluation_id,
                    routing_decision_id=routing_decision_id,
                    governance_snapshot=governance_snapshot or {},
                )
            )
        return drafts


def _bootstrap_default_domains(registry: DomainAgentRegistry) -> None:
    """Bootstrap minimal default domains for MVP startup behavior."""
    if registry.get("programming") is not None:
        return

    registry.register(
        DomainAgentConfig(
            domain_key="programming",
            display_name="Programming",
            description="Software engineering delivery and verification domain.",
            status=DomainStatus.ACTIVE,
            allowed_skill_keys=[
                "code.implement",
                "code.test",
                "code.review",
            ],
            allowed_capability_keys=[
                "code.write",
                "code.test",
                "code.analyze",
            ],
            allowed_specialist_roles=["runtime-engineer", "verification-engineer"],
            review_profile={"requires_tests": True, "requires_review": True},
            risk_profile={"default_risk_tier": "medium"},
            escalation_profile={"escalate_on_policy_conflict": True},
            metadata={"bootstrap": True},
        )
    )
    logger.info("[DomainAgent] Bootstrapped default domain: programming")

    # Odoo Domain Clusters
    _bootstrap_odoo_domains(registry)


def _bootstrap_odoo_domains(registry: DomainAgentRegistry) -> None:
    """Bootstrap Odoo ERP Domain Agents"""
    
    # Accounting Cluster
    registry.register(
        DomainAgentConfig(
            domain_key="odoo.accounting",
            display_name="Odoo Accounting",
            description="Odoo ERP accounting operations - invoices, payments, journal entries.",
            status=DomainStatus.ACTIVE,
            allowed_skill_keys=[
                "odoo.invoice.create",
                "odoo.invoice.list",
                "odoo.invoice.send",
            ],
            allowed_capability_keys=[
                "account.move",
                "account.payment",
                "account.move.line",
            ],
            allowed_specialist_roles=["accountant", "bookkeeper"],
            review_profile={"requires_approval": True, "requires_review": False},
            risk_profile={"default_risk_tier": "high"},
            escalation_profile={"escalate_on_high_risk": True},
            metadata={"odoo_module": "account", "bootstrap": True},
        )
    )
    logger.info("[DomainAgent] Bootstrapped Odoo domain: odoo.accounting")
    
    # Sales Cluster
    registry.register(
        DomainAgentConfig(
            domain_key="odoo.sales",
            display_name="Odoo Sales",
            description="Odoo ERP sales operations - partners, orders, quotes.",
            status=DomainStatus.ACTIVE,
            allowed_skill_keys=[
                "odoo.partner.create",
                "odoo.partner.search",
                "odoo.order.create",
                "odoo.order.confirm",
            ],
            allowed_capability_keys=[
                "res.partner",
                "sale.order",
                "sale.order.line",
            ],
            allowed_specialist_roles=["salesman", "sales_manager"],
            review_profile={"requires_approval": False, "requires_review": False},
            risk_profile={"default_risk_tier": "medium"},
            escalation_profile={"escalate_on_policy_conflict": True},
            metadata={"odoo_module": "sale", "bootstrap": True},
        )
    )
    logger.info("[DomainAgent] Bootstrapped Odoo domain: odoo.sales")
    
    # Manufacturing Cluster
    registry.register(
        DomainAgentConfig(
            domain_key="odoo.manufacturing",
            display_name="Odoo Manufacturing",
            description="Odoo ERP manufacturing operations - BoM, workorders, production.",
            status=DomainStatus.ACTIVE,
            allowed_skill_keys=[
                "odoo.manufacturing.bom",
                "odoo.manufacturing.workorder",
            ],
            allowed_capability_keys=[
                "mrp.bom",
                "mrp.production",
                "mrp.workorder",
            ],
            allowed_specialist_roles=["manufacturing_manager", "production_planner"],
            review_profile={"requires_approval": True, "requires_review": True},
            risk_profile={"default_risk_tier": "high"},
            escalation_profile={"escalate_on_high_risk": True},
            metadata={"odoo_module": "mrp", "bootstrap": True},
        )
    )
    logger.info("[DomainAgent] Bootstrapped Odoo domain: odoo.manufacturing")
    
    # Inventory Cluster
    registry.register(
        DomainAgentConfig(
            domain_key="odoo.inventory",
            display_name="Odoo Inventory",
            description="Odoo ERP inventory operations - stock, receipts, transfers.",
            status=DomainStatus.ACTIVE,
            allowed_skill_keys=[
                "odoo.inventory.stock",
                "odoo.inventory.receipt",
                "odoo.inventory.transfer",
            ],
            allowed_capability_keys=[
                "stock.quant",
                "stock.picking",
                "stock.move",
            ],
            allowed_specialist_roles=["warehouse_manager", "inventory_clerk"],
            review_profile={"requires_approval": False, "requires_review": False},
            risk_profile={"default_risk_tier": "medium"},
            escalation_profile={"escalate_on_policy_conflict": True},
            metadata={"odoo_module": "stock", "bootstrap": True},
        )
    )
    logger.info("[DomainAgent] Bootstrapped Odoo domain: odoo.inventory")
    
    # Purchase Cluster
    registry.register(
        DomainAgentConfig(
            domain_key="odoo.purchase",
            display_name="Odoo Purchase",
            description="Odoo ERP purchase operations - purchase orders, suppliers.",
            status=DomainStatus.ACTIVE,
            allowed_skill_keys=[
                "odoo.purchase.create",
                "odoo.purchase.list",
            ],
            allowed_capability_keys=[
                "purchase.order",
                "purchase.order.line",
            ],
            allowed_specialist_roles=["purchase_manager", "procurement_specialist"],
            review_profile={"requires_approval": True, "requires_review": False},
            risk_profile={"default_risk_tier": "high"},
            escalation_profile={"escalate_on_high_risk": True},
            metadata={"odoo_module": "purchase", "bootstrap": True},
        )
    )
    logger.info("[DomainAgent] Bootstrapped Odoo domain: odoo.purchase")


_registry: Optional[DomainAgentRegistry] = None
_service: Optional[DomainAgentService] = None


def get_domain_agent_registry() -> DomainAgentRegistry:
    global _registry
    if _registry is None:
        _registry = DomainAgentRegistry()
        _bootstrap_default_domains(_registry)
    return _registry


def get_domain_agent_service() -> DomainAgentService:
    global _service
    if _service is None:
        _service = DomainAgentService(registry=get_domain_agent_registry())
    return _service


async def execute_skill_run_drafts(
    db,
    drafts: list[DomainSkillRunDraft],
    principal,
) -> list[str]:
    """Delegate prepared SkillRun drafts to the Skill Engine.

    This function is the only sanctioned path for Domain Agent -> SkillRun
    delegation. Keeping execution here (rather than inline in a router) ensures
    that the Domain Agent layer never owns SkillRun runtime state directly.

    Returns a list of created SkillRun IDs.

    Raises:
        ImportError: if skill_engine module is unavailable (caller must handle as 503).
        Exception: any SkillRun creation failure is propagated to the caller.
    """
    from types import SimpleNamespace
    from typing import cast, Any

    from app.modules.skill_engine.service import get_skill_engine_service

    skill_service = get_skill_engine_service()
    created_ids: list[str] = []
    for draft in drafts:
        create_payload = SimpleNamespace(
            skill_key=draft.skill_key,
            version=None,
            input_payload=draft.input_payload,
            idempotency_key=draft.idempotency_key,
            trigger_type=draft.trigger_type.value,
            mission_id=draft.mission_id,
            deadline_at=None,
            causation_id=draft.causation_id,
            decision_context_id=draft.decision_context_id,
            purpose_evaluation_id=draft.purpose_evaluation_id,
            routing_decision_id=draft.routing_decision_id,
            governance_snapshot=draft.governance_snapshot,
        )
        skill_run = await skill_service.create_run(
            db,
            cast(Any, create_payload),  # type: ignore[arg-type]
            principal,
        )
        created_ids.append(str(skill_run.id))
    return created_ids
