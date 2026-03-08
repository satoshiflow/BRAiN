from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from loguru import logger
from sqlalchemy import Select, and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.capabilities_registry.models import CapabilityDefinitionModel

from .models import SkillDefinitionModel
from .schemas import CapabilityRef, OwnerScope, SkillDefinitionCreate, SkillDefinitionStatus, SkillDefinitionUpdate, VersionSelector


@dataclass(slots=True)
class ResolutionCandidate:
    owner_scope: str
    tenant_id: str | None
    version: int
    status: str


class SkillRegistryService:
    TERMINAL_STATUSES = {
        SkillDefinitionStatus.REJECTED.value,
        SkillDefinitionStatus.RETIRED.value,
    }

    TRANSITIONS = {
        SkillDefinitionStatus.DRAFT.value: {SkillDefinitionStatus.REVIEW.value},
        SkillDefinitionStatus.REVIEW.value: {
            SkillDefinitionStatus.APPROVED.value,
            SkillDefinitionStatus.REJECTED.value,
        },
        SkillDefinitionStatus.APPROVED.value: {SkillDefinitionStatus.ACTIVE.value},
        SkillDefinitionStatus.ACTIVE.value: {SkillDefinitionStatus.DEPRECATED.value},
        SkillDefinitionStatus.DEPRECATED.value: {SkillDefinitionStatus.RETIRED.value},
    }

    def _derive_scope(self, principal: Principal, requested_scope: OwnerScope) -> tuple[str | None, str]:
        if requested_scope == OwnerScope.SYSTEM:
            if not principal.has_scope("platform:catalog:write"):
                raise PermissionError("System scope requires platform:catalog:write")
            return None, OwnerScope.SYSTEM.value

        if not principal.tenant_id:
            raise ValueError("Tenant-scoped definitions require a tenant-bound principal")
        return principal.tenant_id, OwnerScope.TENANT.value

    async def _next_version(
        self,
        db: AsyncSession,
        tenant_id: str | None,
        owner_scope: str,
        skill_key: str,
    ) -> int:
        result = await db.execute(
            select(SkillDefinitionModel.version)
            .where(
                SkillDefinitionModel.skill_key == skill_key,
                SkillDefinitionModel.owner_scope == owner_scope,
                SkillDefinitionModel.tenant_id.is_(tenant_id) if tenant_id is None else SkillDefinitionModel.tenant_id == tenant_id,
            )
            .order_by(desc(SkillDefinitionModel.version))
            .limit(1)
        )
        current = result.scalar_one_or_none()
        return (current or 0) + 1

    @staticmethod
    def _payload_for_checksum(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "skill_key": data["skill_key"],
            "purpose": data["purpose"],
            "input_schema": data["input_schema"],
            "output_schema": data["output_schema"],
            "required_capabilities": data["required_capabilities"],
            "optional_capabilities": data["optional_capabilities"],
            "constraints": data["constraints"],
            "quality_profile": data["quality_profile"],
            "fallback_policy": data["fallback_policy"],
            "evaluation_criteria": data["evaluation_criteria"],
            "risk_tier": data["risk_tier"],
            "policy_pack_ref": data["policy_pack_ref"],
            "trust_tier_min": data["trust_tier_min"],
        }

    @staticmethod
    def is_transition_allowed(current: str, target: str) -> bool:
        return target in SkillRegistryService.TRANSITIONS.get(current, set())

    @staticmethod
    def pick_resolution_candidate(candidates: Sequence[ResolutionCandidate]) -> ResolutionCandidate | None:
        if not candidates:
            return None

        precedence = {
            (OwnerScope.TENANT.value, SkillDefinitionStatus.ACTIVE.value): 0,
            (OwnerScope.TENANT.value, SkillDefinitionStatus.DEPRECATED.value): 1,
            (OwnerScope.SYSTEM.value, SkillDefinitionStatus.ACTIVE.value): 2,
            (OwnerScope.SYSTEM.value, SkillDefinitionStatus.DEPRECATED.value): 3,
        }
        ranked = sorted(candidates, key=lambda item: (precedence.get((item.owner_scope, item.status), 100), item.version))
        best = ranked[0]
        if len(ranked) > 1:
            contender = ranked[1]
            if precedence.get((best.owner_scope, best.status), 100) == precedence.get((contender.owner_scope, contender.status), 100) and best.version == contender.version:
                raise ValueError("Resolution is ambiguous for the requested selector")
        return best

    async def _ensure_required_capabilities(self, db: AsyncSession, tenant_id: str | None, refs: Iterable[dict[str, Any]]) -> None:
        for ref in refs:
            await self._resolve_capability_ref(db, tenant_id, CapabilityRef.model_validate(ref))

    async def _resolve_capability_ref(self, db: AsyncSession, tenant_id: str | None, ref: CapabilityRef) -> CapabilityDefinitionModel:
        query = select(CapabilityDefinitionModel).where(
            CapabilityDefinitionModel.capability_key == ref.capability_key,
            CapabilityDefinitionModel.owner_scope.in_([OwnerScope.TENANT.value, OwnerScope.SYSTEM.value]),
        )
        if tenant_id:
            query = query.where(
                or_(
                    CapabilityDefinitionModel.tenant_id == tenant_id,
                    CapabilityDefinitionModel.owner_scope == OwnerScope.SYSTEM.value,
                )
            )
        else:
            query = query.where(CapabilityDefinitionModel.owner_scope == OwnerScope.SYSTEM.value)

        if ref.version_selector == VersionSelector.ACTIVE:
            query = query.where(CapabilityDefinitionModel.status == "active")
        elif ref.version_selector == VersionSelector.EXACT:
            query = query.where(CapabilityDefinitionModel.version == ref.version_value)
        else:
            query = query.where(CapabilityDefinitionModel.version >= int(ref.version_value or 1))
        result = await db.execute(query)
        candidates = list(result.scalars().all())
        candidates.sort(
            key=lambda item: (
                0 if tenant_id and item.owner_scope == OwnerScope.TENANT.value and item.tenant_id == tenant_id else 1,
                item.version if ref.version_selector == VersionSelector.MIN else -item.version,
            )
        )
        capability = candidates[0] if candidates else None
        if capability is None:
            raise ValueError(f"Required capability '{ref.capability_key}' cannot be resolved")
        if capability.status not in {"active", "deprecated"}:
            raise ValueError(f"Capability '{ref.capability_key}' is not execution-eligible")
        return capability

    async def list_definitions(
        self,
        db: AsyncSession,
        tenant_id: str | None,
        include_system: bool = True,
        skill_key: str | None = None,
        status: str | None = None,
    ) -> list[SkillDefinitionModel]:
        query: Select[Any] = select(SkillDefinitionModel)
        if tenant_id:
            allowed = [and_(SkillDefinitionModel.owner_scope == OwnerScope.TENANT.value, SkillDefinitionModel.tenant_id == tenant_id)]
            if include_system:
                allowed.append(SkillDefinitionModel.owner_scope == OwnerScope.SYSTEM.value)
            query = query.where(or_(*allowed))
        else:
            query = query.where(SkillDefinitionModel.owner_scope == OwnerScope.SYSTEM.value)
        if skill_key:
            query = query.where(SkillDefinitionModel.skill_key == skill_key)
        if status:
            query = query.where(SkillDefinitionModel.status == status)
        query = query.order_by(SkillDefinitionModel.skill_key.asc(), SkillDefinitionModel.version.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_definition(
        self,
        db: AsyncSession,
        skill_key: str,
        version: int,
        tenant_id: str | None,
        include_system: bool = True,
        owner_scope: str | None = None,
    ) -> SkillDefinitionModel | None:
        query = select(SkillDefinitionModel).where(
            SkillDefinitionModel.skill_key == skill_key,
            SkillDefinitionModel.version == version,
        )
        if owner_scope:
            query = query.where(SkillDefinitionModel.owner_scope == owner_scope)
        if tenant_id:
            allowed = [and_(SkillDefinitionModel.owner_scope == OwnerScope.TENANT.value, SkillDefinitionModel.tenant_id == tenant_id)]
            if include_system:
                allowed.append(SkillDefinitionModel.owner_scope == OwnerScope.SYSTEM.value)
            query = query.where(or_(*allowed))
        else:
            query = query.where(SkillDefinitionModel.owner_scope == OwnerScope.SYSTEM.value)
        result = await db.execute(query)
        items = list(result.scalars().all())
        if not items:
            return None
        items.sort(key=lambda item: (0 if tenant_id and item.owner_scope == OwnerScope.TENANT.value and item.tenant_id == tenant_id else 1))
        return items[0]

    async def create_definition(self, db: AsyncSession, payload: SkillDefinitionCreate, principal: Principal) -> SkillDefinitionModel:
        if not payload.required_capabilities:
            raise ValueError("required_capabilities must not be empty")

        tenant_id, owner_scope = self._derive_scope(principal, payload.owner_scope)
        version = payload.version or await self._next_version(db, tenant_id, owner_scope, payload.skill_key)

        existing = await self.get_definition(db, payload.skill_key, version, tenant_id, include_system=owner_scope == OwnerScope.SYSTEM.value)
        if existing is not None and existing.owner_scope == owner_scope:
            raise ValueError(f"Skill definition '{payload.skill_key}' version {version} already exists")

        raw = payload.model_dump(mode="json")
        raw["skill_key"] = payload.skill_key
        checksum = SkillDefinitionModel.build_checksum(self._payload_for_checksum(raw))

        await self._ensure_required_capabilities(db, tenant_id, raw["required_capabilities"])

        model = SkillDefinitionModel(
            tenant_id=tenant_id,
            owner_scope=owner_scope,
            skill_key=payload.skill_key,
            version=version,
            status=SkillDefinitionStatus.DRAFT.value,
            purpose=payload.purpose,
            input_schema=payload.input_schema,
            output_schema=payload.output_schema,
            required_capabilities=raw["required_capabilities"],
            optional_capabilities=raw["optional_capabilities"],
            constraints=payload.constraints,
            quality_profile=payload.quality_profile.value,
            fallback_policy=payload.fallback_policy.value,
            evaluation_criteria=payload.evaluation_criteria,
            risk_tier=payload.risk_tier.value,
            policy_pack_ref=payload.policy_pack_ref,
            trust_tier_min=payload.trust_tier_min.value,
            checksum_sha256=checksum,
            created_by=principal.principal_id,
            updated_by=principal.principal_id,
        )
        db.add(model)
        await db.commit()
        await db.refresh(model)
        logger.info("Created skill definition {} v{}", model.skill_key, model.version)
        return model

    async def update_definition(
        self,
        db: AsyncSession,
        skill_key: str,
        version: int,
        payload: SkillDefinitionUpdate,
        principal: Principal,
        owner_scope: str | None = None,
    ) -> SkillDefinitionModel | None:
        definition = await self.get_definition(
            db,
            skill_key,
            version,
            principal.tenant_id,
            include_system=principal.has_scope("platform:catalog:write"),
            owner_scope=owner_scope,
        )
        if definition is None:
            return None
        if definition.status not in {SkillDefinitionStatus.DRAFT.value, SkillDefinitionStatus.REVIEW.value}:
            raise ValueError("Only draft or review definitions may be updated")

        changes = payload.model_dump(exclude_unset=True, mode="json")
        if "required_capabilities" in changes:
            if not changes["required_capabilities"]:
                raise ValueError("required_capabilities must not be empty")
            await self._ensure_required_capabilities(db, definition.tenant_id, changes["required_capabilities"])
        for field, value in changes.items():
            if hasattr(value, "value"):
                value = value.value
            setattr(definition, field, value)

        checksum_payload = self._payload_for_checksum(
            {
                "skill_key": definition.skill_key,
                "purpose": definition.purpose,
                "input_schema": definition.input_schema,
                "output_schema": definition.output_schema,
                "required_capabilities": definition.required_capabilities,
                "optional_capabilities": definition.optional_capabilities,
                "constraints": definition.constraints,
                "quality_profile": definition.quality_profile,
                "fallback_policy": definition.fallback_policy,
                "evaluation_criteria": definition.evaluation_criteria,
                "risk_tier": definition.risk_tier,
                "policy_pack_ref": definition.policy_pack_ref,
                "trust_tier_min": definition.trust_tier_min,
            }
        )
        definition.checksum_sha256 = SkillDefinitionModel.build_checksum(checksum_payload)
        definition.updated_by = principal.principal_id
        await db.commit()
        await db.refresh(definition)
        return definition

    async def transition_definition(
        self,
        db: AsyncSession,
        skill_key: str,
        version: int,
        target_status: SkillDefinitionStatus,
        principal: Principal,
        owner_scope: str | None = None,
    ) -> SkillDefinitionModel | None:
        definition = await self.get_definition(
            db,
            skill_key,
            version,
            principal.tenant_id,
            include_system=principal.has_scope("platform:catalog:write"),
            owner_scope=owner_scope,
        )
        if definition is None:
            return None
        if not self.is_transition_allowed(definition.status, target_status.value):
            raise ValueError(f"Illegal status transition: {definition.status} -> {target_status.value}")
        if target_status == SkillDefinitionStatus.ACTIVE:
            await self._ensure_required_capabilities(db, definition.tenant_id, definition.required_capabilities)
            active_result = await db.execute(
                select(SkillDefinitionModel).where(
                    SkillDefinitionModel.skill_key == definition.skill_key,
                    SkillDefinitionModel.status == SkillDefinitionStatus.ACTIVE.value,
                    SkillDefinitionModel.owner_scope == definition.owner_scope,
                    SkillDefinitionModel.tenant_id.is_(definition.tenant_id) if definition.tenant_id is None else SkillDefinitionModel.tenant_id == definition.tenant_id,
                )
            )
            active = active_result.scalar_one_or_none()
            if active is not None:
                active.status = SkillDefinitionStatus.DEPRECATED.value
                active.updated_by = principal.principal_id
        definition.status = target_status.value
        definition.updated_by = principal.principal_id
        if target_status in {SkillDefinitionStatus.APPROVED, SkillDefinitionStatus.ACTIVE}:
            definition.approved_by = principal.principal_id
            definition.approved_at = definition.approved_at or definition.updated_at
        await db.commit()
        await db.refresh(definition)
        return definition

    async def resolve_definition(
        self,
        db: AsyncSession,
        skill_key: str,
        tenant_id: str | None,
        selector: VersionSelector = VersionSelector.ACTIVE,
        version_value: int | None = None,
    ) -> SkillDefinitionModel:
        query = select(SkillDefinitionModel).where(SkillDefinitionModel.skill_key == skill_key)
        if tenant_id:
            query = query.where(
                or_(
                    and_(SkillDefinitionModel.owner_scope == OwnerScope.TENANT.value, SkillDefinitionModel.tenant_id == tenant_id),
                    SkillDefinitionModel.owner_scope == OwnerScope.SYSTEM.value,
                )
            )
        else:
            query = query.where(SkillDefinitionModel.owner_scope == OwnerScope.SYSTEM.value)

        if selector == VersionSelector.ACTIVE:
            query = query.where(SkillDefinitionModel.status.in_([SkillDefinitionStatus.ACTIVE.value, SkillDefinitionStatus.DEPRECATED.value]))
        elif selector == VersionSelector.EXACT:
            if version_value is None:
                raise ValueError("version_value is required for exact resolution")
            query = query.where(SkillDefinitionModel.version == version_value)
        elif selector == VersionSelector.MIN:
            if version_value is None:
                raise ValueError("version_value is required for min resolution")
            query = query.where(SkillDefinitionModel.version >= version_value)

        result = await db.execute(query)
        definitions = list(result.scalars().all())
        if selector == VersionSelector.EXACT:
            execution_eligible = [item for item in definitions if item.status in {SkillDefinitionStatus.ACTIVE.value, SkillDefinitionStatus.DEPRECATED.value}]
            if not execution_eligible:
                raise ValueError(f"No execution-eligible definition found for '{skill_key}'")
            candidates = execution_eligible
        elif selector == VersionSelector.MIN:
            candidates = [item for item in definitions if item.status in {SkillDefinitionStatus.ACTIVE.value, SkillDefinitionStatus.DEPRECATED.value}]
        else:
            candidates = [item for item in definitions if item.status in {SkillDefinitionStatus.ACTIVE.value, SkillDefinitionStatus.DEPRECATED.value}]
        picked = self.pick_resolution_candidate(
            [ResolutionCandidate(item.owner_scope, item.tenant_id, item.version, item.status) for item in candidates]
        )
        if picked is None:
            raise ValueError(f"No matching definition found for '{skill_key}'")
        for item in candidates:
            if item.owner_scope == picked.owner_scope and item.tenant_id == picked.tenant_id and item.version == picked.version:
                return item
        raise ValueError(f"Unable to resolve definition for '{skill_key}'")


_skill_registry_service: SkillRegistryService | None = None


def get_skill_registry_service() -> SkillRegistryService:
    global _skill_registry_service
    if _skill_registry_service is None:
        _skill_registry_service = SkillRegistryService()
    return _skill_registry_service
