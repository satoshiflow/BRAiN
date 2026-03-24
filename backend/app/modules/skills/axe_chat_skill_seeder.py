from __future__ import annotations

import os

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, PrincipalType
from app.modules.capabilities_registry.schemas import (
    CapabilityDefinitionCreate,
    CapabilityDefinitionStatus,
)
from app.modules.capabilities_registry.service import get_capability_registry_service
from app.modules.skills_registry.schemas import (
    CapabilityRef,
    OwnerScope,
    RiskTier,
    SkillDefinitionCreate,
    SkillDefinitionStatus,
    TrustTier,
    VersionSelector,
)
from app.modules.skills_registry.service import get_skill_registry_service


def _system_seed_principal() -> Principal:
    return Principal(
        principal_id="system-seed",
        principal_type=PrincipalType.SERVICE,
        name="System Seeder",
        roles=["SYSTEM_ADMIN"],
        scopes=["platform:catalog:write", "read", "write"],
        tenant_id=None,
    )


async def seed_axe_chat_skill_contract(db: AsyncSession) -> None:
    """Ensure AXE chat bridge has an active system SkillDefinition and CapabilityDefinition."""

    skill_key = os.getenv("AXE_CHAT_SKILL_KEY", "axe.chat.bridge").strip() or "axe.chat.bridge"
    skill_version = int(os.getenv("AXE_CHAT_SKILL_VERSION", "1"))
    capability_key = os.getenv("AXE_PROVIDER_CAPABILITY_KEY", "text.generate").strip() or "text.generate"

    principal = _system_seed_principal()
    capability_service = get_capability_registry_service()
    skill_service = get_skill_registry_service()

    # Ensure capability exists and is active
    try:
        capability = await capability_service.resolve_definition(
            db,
            capability_key=capability_key,
            tenant_id=None,
        )
    except ValueError:
        capability = None

    if capability is None:
        capability = await capability_service.get_definition(
            db,
            capability_key=capability_key,
            version=1,
            tenant_id=None,
            owner_scope=OwnerScope.SYSTEM.value,
        )

    if capability is None:
        capability = await capability_service.create_definition(
            db,
            CapabilityDefinitionCreate(
                owner_scope=OwnerScope.SYSTEM,
                capability_key=capability_key,
                version=1,
                domain="llm",
                description="Canonical text generation capability for AXE bridge",
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "messages": {"type": "array"},
                        "model": {"type": "string"},
                        "temperature": {"type": "number"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                    },
                },
                default_timeout_ms=45000,
                retry_policy={"max_retries": 1, "backoff_ms": 500},
                qos_targets={"p95_ms": 12000},
                policy_constraints={"allow_external": True},
            ),
            principal,
        )
    capability_status = getattr(capability, "status", None)
    if capability_status == CapabilityDefinitionStatus.DRAFT.value:
        resolved_capability_key = str(getattr(capability, "capability_key", capability_key))
        resolved_capability_version = int(getattr(capability, "version", 1))
        capability = await capability_service.transition_definition(
            db,
            capability_key=resolved_capability_key,
            version=resolved_capability_version,
            target_status=CapabilityDefinitionStatus.ACTIVE,
            principal=principal,
            owner_scope=OwnerScope.SYSTEM.value,
        )

    # Ensure chat bridge skill exists and is active
    try:
        skill = await skill_service.resolve_definition(
            db,
            skill_key=skill_key,
            tenant_id=None,
            selector=VersionSelector.EXACT,
            version_value=skill_version,
        )
    except ValueError:
        skill = None

    if skill is None:
        skill = await skill_service.get_definition(
            db,
            skill_key=skill_key,
            version=skill_version,
            tenant_id=None,
            owner_scope=OwnerScope.SYSTEM.value,
        )

    if skill is None:
        skill = await skill_service.create_definition(
            db,
            SkillDefinitionCreate(
                owner_scope=OwnerScope.SYSTEM,
                skill_key=skill_key,
                version=skill_version,
                purpose="AXE chat bridge skill routed through SkillRun",
                input_schema={
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "messages": {"type": "array"},
                        "temperature": {"type": "number"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "text.generate": {"type": "object"},
                    },
                },
                required_capabilities=[
                    CapabilityRef(capability_key=capability_key)
                ],
                evaluation_criteria={"min_score": 0.0},
                risk_tier=RiskTier.MEDIUM,
                policy_pack_ref="default",
                trust_tier_min=TrustTier.INTERNAL,
                builder_role="axe_chat_bridge",
            ),
            principal,
        )

    skill_status = getattr(skill, "status", None)
    if skill_status == SkillDefinitionStatus.DRAFT.value:
        resolved_skill_key = str(getattr(skill, "skill_key", skill_key))
        resolved_skill_version = int(getattr(skill, "version", skill_version))
        skill = await skill_service.transition_definition(
            db,
            skill_key=resolved_skill_key,
            version=resolved_skill_version,
            target_status=SkillDefinitionStatus.REVIEW,
            principal=principal,
            owner_scope=OwnerScope.SYSTEM.value,
        )
        skill_status = getattr(skill, "status", None)
    if skill_status == SkillDefinitionStatus.REVIEW.value:
        resolved_skill_key = str(getattr(skill, "skill_key", skill_key))
        resolved_skill_version = int(getattr(skill, "version", skill_version))
        skill = await skill_service.transition_definition(
            db,
            skill_key=resolved_skill_key,
            version=resolved_skill_version,
            target_status=SkillDefinitionStatus.APPROVED,
            principal=principal,
            owner_scope=OwnerScope.SYSTEM.value,
        )
        skill_status = getattr(skill, "status", None)
    if skill_status == SkillDefinitionStatus.APPROVED.value:
        resolved_skill_key = str(getattr(skill, "skill_key", skill_key))
        resolved_skill_version = int(getattr(skill, "version", skill_version))
        skill = await skill_service.transition_definition(
            db,
            skill_key=resolved_skill_key,
            version=resolved_skill_version,
            target_status=SkillDefinitionStatus.ACTIVE,
            principal=principal,
            owner_scope=OwnerScope.SYSTEM.value,
        )

    logger.info(
        "AXE chat bridge skill contract ready: skill_key={} version={} capability_key={}",
        skill_key,
        skill_version,
        capability_key,
    )
