"""Foundational services for the Domain Agent layer."""

from __future__ import annotations

import hashlib
from typing import Dict, Iterable, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DomainAgentConfigModel
from .schemas import (
    DomainAgentConfig,
    DomainDecompositionRequest,
    DomainResolution,
    DomainReviewDecision,
    DomainStatus,
    DomainSkillRunDraft,
    DomainReviewOutcome,
    SpecialistCandidate,
)


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
            return self._decompose_programming(request, config, selected_capabilities)

        return DomainResolution(
            domain_key=config.domain_key,
            confidence=0.5,
            selected_skill_keys=list(config.allowed_skill_keys),
            selected_capability_keys=selected_capabilities,
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

        specialists: list[SpecialistCandidate] = []
        for idx, role in enumerate(config.allowed_specialist_roles):
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
        resolution: DomainResolution,
        trigger_type,
        mission_id: str | None,
        causation_id: str | None,
        input_payload: dict,
        tenant_id: str | None,
    ) -> list[DomainSkillRunDraft]:
        """Build deterministic SkillRun drafts from domain resolution."""
        drafts: list[DomainSkillRunDraft] = []
        for idx, skill_key in enumerate(resolution.selected_skill_keys, start=1):
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
        )
        skill_run = await skill_service.create_run(
            db,
            cast(Any, create_payload),  # type: ignore[arg-type]
            principal,
        )
        created_ids.append(str(skill_run.id))
    return created_ids
