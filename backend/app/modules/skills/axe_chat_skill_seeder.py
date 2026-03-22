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
    SkillDefinitionCreate,
    SkillDefinitionStatus,
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
    capability = await capability_service.resolve_definition(
        db,
        tenant_id=None,
        owner_scope=OwnerScope.SYSTEM.value,
        capability_key=capability_key,
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
    if capability.status == CapabilityDefinitionStatus.DRAFT.value:
        capability = await capability_service.transition_status(
            db, capability.id, CapabilityDefinitionStatus.ACTIVE, principal
        )

    # Ensure chat bridge skill exists and is active
    skill = await skill_service.resolve_definition(
        db,
        tenant_id=None,
        owner_scope=OwnerScope.SYSTEM.value,
        skill_key=skill_key,
        version_value=skill_version,
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
                risk_tier="medium",
                policy_pack_ref="default",
                trust_tier_min="internal",
                builder_role="axe_chat_bridge",
            ),
            principal,
        )

    if skill.status == SkillDefinitionStatus.DRAFT.value:
        skill = await skill_service.transition_status(
            db, skill.id, SkillDefinitionStatus.REVIEW, principal
        )
    if skill.status == SkillDefinitionStatus.REVIEW.value:
        skill = await skill_service.transition_status(
            db, skill.id, SkillDefinitionStatus.APPROVED, principal
        )
    if skill.status == SkillDefinitionStatus.APPROVED.value:
        skill = await skill_service.transition_status(
            db, skill.id, SkillDefinitionStatus.ACTIVE, principal
        )

    logger.info(
        "AXE chat bridge skill contract ready: skill_key={} version={} capability_key={}",
        skill_key,
        skill_version,
        capability_key,
    )
