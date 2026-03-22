from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from loguru import logger
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.core.control_plane_events import record_control_plane_event

from .models import CapabilityDefinitionModel
from .schemas import CapabilityDefinitionCreate, CapabilityDefinitionStatus, CapabilityDefinitionUpdate
from app.modules.skills_registry.schemas import OwnerScope, VersionSelector


@dataclass(slots=True)
class CapabilityCandidate:
    owner_scope: str
    tenant_id: str | None
    version: int
    status: str


class CapabilityRegistryService:
    TRANSITIONS = {
        CapabilityDefinitionStatus.DRAFT.value: {CapabilityDefinitionStatus.ACTIVE.value},
        CapabilityDefinitionStatus.ACTIVE.value: {
            CapabilityDefinitionStatus.DEPRECATED.value,
            CapabilityDefinitionStatus.BLOCKED.value,
        },
        CapabilityDefinitionStatus.BLOCKED.value: {CapabilityDefinitionStatus.ACTIVE.value},
        CapabilityDefinitionStatus.DEPRECATED.value: {CapabilityDefinitionStatus.RETIRED.value},
    }

    def _derive_scope(self, principal: Principal, requested_scope: OwnerScope) -> tuple[str | None, str]:
        if requested_scope == OwnerScope.SYSTEM:
            if not principal.has_scope("platform:catalog:write"):
                raise PermissionError("System scope requires platform:catalog:write")
            return None, OwnerScope.SYSTEM.value
        if not principal.tenant_id:
            raise ValueError("Tenant-scoped definitions require a tenant-bound principal")
        return principal.tenant_id, OwnerScope.TENANT.value

    async def _next_version(self, db: AsyncSession, tenant_id: str | None, owner_scope: str, capability_key: str) -> int:
        result = await db.execute(
            select(CapabilityDefinitionModel.version)
            .where(
                CapabilityDefinitionModel.capability_key == capability_key,
                CapabilityDefinitionModel.owner_scope == owner_scope,
                CapabilityDefinitionModel.tenant_id.is_(tenant_id) if tenant_id is None else CapabilityDefinitionModel.tenant_id == tenant_id,
            )
            .order_by(desc(CapabilityDefinitionModel.version))
            .limit(1)
        )
        current = result.scalar_one_or_none()
        return (current or 0) + 1

    @staticmethod
    def build_checksum_payload(item: CapabilityDefinitionModel | dict[str, Any]) -> dict[str, Any]:
        if isinstance(item, CapabilityDefinitionModel):
            return {
                "capability_key": item.capability_key,
                "domain": item.domain,
                "description": item.description,
                "input_schema": item.input_schema,
                "output_schema": item.output_schema,
                "default_timeout_ms": item.default_timeout_ms,
                "retry_policy": item.retry_policy,
                "qos_targets": item.qos_targets,
                "fallback_capability_key": item.fallback_capability_key,
                "policy_constraints": item.policy_constraints,
                "contract_artifact_refs": item.contract_artifact_refs,
                "adapter_test_artifact_refs": item.adapter_test_artifact_refs,
            }
        return item

    @staticmethod
    def is_transition_allowed(current: str, target: str) -> bool:
        return target in CapabilityRegistryService.TRANSITIONS.get(current, set())

    @staticmethod
    def pick_resolution_candidate(candidates: Sequence[CapabilityCandidate]) -> CapabilityCandidate | None:
        if not candidates:
            return None
        precedence = {
            (OwnerScope.TENANT.value, CapabilityDefinitionStatus.ACTIVE.value): 0,
            (OwnerScope.TENANT.value, CapabilityDefinitionStatus.DEPRECATED.value): 1,
            (OwnerScope.SYSTEM.value, CapabilityDefinitionStatus.ACTIVE.value): 2,
            (OwnerScope.SYSTEM.value, CapabilityDefinitionStatus.DEPRECATED.value): 3,
        }
        ranked = sorted(candidates, key=lambda item: (precedence.get((item.owner_scope, item.status), 100), item.version))
        best = ranked[0]
        if len(ranked) > 1:
            contender = ranked[1]
            if precedence.get((best.owner_scope, best.status), 100) == precedence.get((contender.owner_scope, contender.status), 100) and best.version == contender.version:
                raise ValueError("Resolution is ambiguous for the requested selector")
        return best

    async def _validate_fallback_cycle(
        self,
        db: AsyncSession,
        tenant_id: str | None,
        owner_scope: str,
        capability_key: str,
        fallback_capability_key: str | None,
    ) -> None:
        if not fallback_capability_key:
            return
        if fallback_capability_key == capability_key:
            raise ValueError("Fallback graph must not create cycles")

        current = fallback_capability_key
        seen = {capability_key}
        while current:
            if current in seen:
                raise ValueError("Fallback graph must not create cycles")
            seen.add(current)
            query = select(CapabilityDefinitionModel).where(
                CapabilityDefinitionModel.capability_key == current,
                CapabilityDefinitionModel.owner_scope.in_([owner_scope, OwnerScope.SYSTEM.value]),
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
            result = await db.execute(query.order_by(CapabilityDefinitionModel.version.desc()))
            found = result.scalars().first()
            current = found.fallback_capability_key if found else None

    async def list_definitions(
        self,
        db: AsyncSession,
        tenant_id: str | None,
        include_system: bool = True,
        capability_key: str | None = None,
        status: str | None = None,
        domain: str | None = None,
    ) -> list[CapabilityDefinitionModel]:
        query = select(CapabilityDefinitionModel)
        if tenant_id:
            allowed = [and_(CapabilityDefinitionModel.owner_scope == OwnerScope.TENANT.value, CapabilityDefinitionModel.tenant_id == tenant_id)]
            if include_system:
                allowed.append(CapabilityDefinitionModel.owner_scope == OwnerScope.SYSTEM.value)
            query = query.where(or_(*allowed))
        else:
            query = query.where(CapabilityDefinitionModel.owner_scope == OwnerScope.SYSTEM.value)
        if capability_key:
            query = query.where(CapabilityDefinitionModel.capability_key == capability_key)
        if status:
            query = query.where(CapabilityDefinitionModel.status == status)
        if domain:
            query = query.where(CapabilityDefinitionModel.domain == domain)
        query = query.order_by(CapabilityDefinitionModel.capability_key.asc(), CapabilityDefinitionModel.version.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_definition(
        self,
        db: AsyncSession,
        capability_key: str,
        version: int,
        tenant_id: str | None,
        include_system: bool = True,
        owner_scope: str | None = None,
    ) -> CapabilityDefinitionModel | None:
        query = select(CapabilityDefinitionModel).where(
            CapabilityDefinitionModel.capability_key == capability_key,
            CapabilityDefinitionModel.version == version,
        )
        if owner_scope:
            query = query.where(CapabilityDefinitionModel.owner_scope == owner_scope)
        if tenant_id:
            allowed = [and_(CapabilityDefinitionModel.owner_scope == OwnerScope.TENANT.value, CapabilityDefinitionModel.tenant_id == tenant_id)]
            if include_system:
                allowed.append(CapabilityDefinitionModel.owner_scope == OwnerScope.SYSTEM.value)
            query = query.where(or_(*allowed))
        else:
            query = query.where(CapabilityDefinitionModel.owner_scope == OwnerScope.SYSTEM.value)
        result = await db.execute(query)
        items = list(result.scalars().all())
        if not items:
            return None
        items.sort(key=lambda item: (0 if tenant_id and item.owner_scope == OwnerScope.TENANT.value and item.tenant_id == tenant_id else 1))
        return items[0]

    async def create_definition(self, db: AsyncSession, payload: CapabilityDefinitionCreate, principal: Principal) -> CapabilityDefinitionModel:
        tenant_id, owner_scope = self._derive_scope(principal, payload.owner_scope)
        await self._validate_fallback_cycle(db, tenant_id, owner_scope, payload.capability_key, payload.fallback_capability_key)
        version = payload.version or await self._next_version(db, tenant_id, owner_scope, payload.capability_key)
        existing = await self.get_definition(db, payload.capability_key, version, tenant_id, include_system=owner_scope == OwnerScope.SYSTEM.value)
        if existing is not None and existing.owner_scope == owner_scope:
            raise ValueError(f"Capability definition '{payload.capability_key}' version {version} already exists")
        raw = payload.model_dump(mode="json")
        checksum = CapabilityDefinitionModel.build_checksum(
            {
                "capability_key": payload.capability_key,
                "domain": payload.domain,
                "description": payload.description,
                "input_schema": payload.input_schema,
                "output_schema": payload.output_schema,
                "default_timeout_ms": payload.default_timeout_ms,
                "retry_policy": payload.retry_policy,
                "qos_targets": payload.qos_targets,
                "fallback_capability_key": payload.fallback_capability_key,
                "policy_constraints": payload.policy_constraints,
            }
        )
        model = CapabilityDefinitionModel(
            tenant_id=tenant_id,
            owner_scope=owner_scope,
            capability_key=payload.capability_key,
            version=version,
            status=CapabilityDefinitionStatus.DRAFT.value,
            domain=payload.domain,
            description=payload.description,
            input_schema=payload.input_schema,
            output_schema=payload.output_schema,
            default_timeout_ms=payload.default_timeout_ms,
            retry_policy=payload.retry_policy,
            qos_targets=payload.qos_targets,
            fallback_capability_key=payload.fallback_capability_key,
            policy_constraints=payload.policy_constraints,
            contract_artifact_refs=payload.contract_artifact_refs,
            adapter_test_artifact_refs=payload.adapter_test_artifact_refs,
            checksum_sha256=checksum,
            created_by=principal.principal_id,
            updated_by=principal.principal_id,
        )
        db.add(model)
        await db.flush()
        await record_control_plane_event(
            db=db,
            tenant_id=model.tenant_id,
            entity_type="capability_definition",
            entity_id=str(model.id),
            event_type="capability.definition.created.v1",
            correlation_id=None,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={"capability_key": model.capability_key, "version": model.version, "status": model.status},
            audit_required=True,
            audit_action="capability_definition_create",
            audit_message="Capability definition created",
        )
        await db.commit()
        await db.refresh(model)
        logger.info("Created capability definition {} v{}", model.capability_key, model.version)
        return model

    async def update_definition(
        self,
        db: AsyncSession,
        capability_key: str,
        version: int,
        payload: CapabilityDefinitionUpdate,
        principal: Principal,
        owner_scope: str | None = None,
    ) -> CapabilityDefinitionModel | None:
        definition = await self.get_definition(
            db,
            capability_key,
            version,
            principal.tenant_id,
            include_system=principal.has_scope("platform:catalog:write"),
            owner_scope=owner_scope,
        )
        if definition is None:
            return None
        if definition.status != CapabilityDefinitionStatus.DRAFT.value:
            raise ValueError("Only draft capability definitions may be updated")
        changes = payload.model_dump(exclude_unset=True, mode="json")
        if "fallback_capability_key" in changes:
            await self._validate_fallback_cycle(db, definition.tenant_id, definition.owner_scope, definition.capability_key, changes["fallback_capability_key"])
        for field, value in changes.items():
            setattr(definition, field, value)
        definition.checksum_sha256 = CapabilityDefinitionModel.build_checksum(self.build_checksum_payload(definition))
        definition.updated_by = principal.principal_id
        await db.commit()
        await db.refresh(definition)
        return definition

    async def transition_definition(
        self,
        db: AsyncSession,
        capability_key: str,
        version: int,
        target_status: CapabilityDefinitionStatus,
        principal: Principal,
        owner_scope: str | None = None,
    ) -> CapabilityDefinitionModel | None:
        definition = await self.get_definition(
            db,
            capability_key,
            version,
            principal.tenant_id,
            include_system=principal.has_scope("platform:catalog:write"),
            owner_scope=owner_scope,
        )
        if definition is None:
            return None
        if not self.is_transition_allowed(definition.status, target_status.value):
            raise ValueError(f"Illegal status transition: {definition.status} -> {target_status.value}")
        previous_status = definition.status
        if target_status == CapabilityDefinitionStatus.ACTIVE:
            await self._validate_fallback_cycle(db, definition.tenant_id, definition.owner_scope, definition.capability_key, definition.fallback_capability_key)
            active_result = await db.execute(
                select(CapabilityDefinitionModel).where(
                    CapabilityDefinitionModel.capability_key == definition.capability_key,
                    CapabilityDefinitionModel.status == CapabilityDefinitionStatus.ACTIVE.value,
                    CapabilityDefinitionModel.owner_scope == definition.owner_scope,
                    CapabilityDefinitionModel.tenant_id.is_(definition.tenant_id) if definition.tenant_id is None else CapabilityDefinitionModel.tenant_id == definition.tenant_id,
                )
            )
            active = active_result.scalar_one_or_none()
            if active is not None:
                active.status = CapabilityDefinitionStatus.DEPRECATED.value
                active.updated_by = principal.principal_id
        definition.status = target_status.value
        definition.updated_by = principal.principal_id
        event_map = {
            CapabilityDefinitionStatus.ACTIVE: "capability.definition.activated.v1",
            CapabilityDefinitionStatus.BLOCKED: "capability.definition.blocked.v1",
            CapabilityDefinitionStatus.DEPRECATED: "capability.definition.deprecated.v1",
            CapabilityDefinitionStatus.RETIRED: "capability.definition.retired.v1",
        }
        await record_control_plane_event(
            db=db,
            tenant_id=definition.tenant_id,
            entity_type="capability_definition",
            entity_id=str(definition.id),
            event_type=event_map.get(target_status, f"capability.definition.{target_status.value}.v1"),
            correlation_id=None,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "capability_key": definition.capability_key,
                "version": definition.version,
                "previous_status": previous_status,
                "status": target_status.value,
            },
            audit_required=True,
            audit_action=f"capability_definition_{target_status.value}",
            audit_message=f"Capability definition moved to {target_status.value}",
        )
        await db.commit()
        await db.refresh(definition)
        return definition

    async def resolve_definition(
        self,
        db: AsyncSession,
        capability_key: str,
        tenant_id: str | None,
        selector: VersionSelector = VersionSelector.ACTIVE,
        version_value: int | None = None,
    ) -> CapabilityDefinitionModel:
        query = select(CapabilityDefinitionModel).where(CapabilityDefinitionModel.capability_key == capability_key)
        if tenant_id:
            query = query.where(
                or_(
                    and_(CapabilityDefinitionModel.owner_scope == OwnerScope.TENANT.value, CapabilityDefinitionModel.tenant_id == tenant_id),
                    CapabilityDefinitionModel.owner_scope == OwnerScope.SYSTEM.value,
                )
            )
        else:
            query = query.where(CapabilityDefinitionModel.owner_scope == OwnerScope.SYSTEM.value)
        if selector == VersionSelector.ACTIVE:
            query = query.where(CapabilityDefinitionModel.status.in_([CapabilityDefinitionStatus.ACTIVE.value, CapabilityDefinitionStatus.DEPRECATED.value]))
        elif selector == VersionSelector.EXACT:
            if version_value is None:
                raise ValueError("version_value is required for exact resolution")
            query = query.where(CapabilityDefinitionModel.version == version_value)
        elif selector == VersionSelector.MIN:
            if version_value is None:
                raise ValueError("version_value is required for min resolution")
            query = query.where(CapabilityDefinitionModel.version >= version_value)

        result = await db.execute(query)
        definitions = list(result.scalars().all())
        candidates = [
            item
            for item in definitions
            if item.status in {CapabilityDefinitionStatus.ACTIVE.value, CapabilityDefinitionStatus.DEPRECATED.value}
        ]
        picked = self.pick_resolution_candidate(
            [CapabilityCandidate(item.owner_scope, item.tenant_id, item.version, item.status) for item in candidates]
        )
        if picked is None:
            raise ValueError(f"No matching capability definition found for '{capability_key}'")
        for item in candidates:
            if item.owner_scope == picked.owner_scope and item.tenant_id == picked.tenant_id and item.version == picked.version:
                return item
        raise ValueError(f"Unable to resolve capability '{capability_key}'")


_capability_registry_service: CapabilityRegistryService | None = None


def get_capability_registry_service() -> CapabilityRegistryService:
    global _capability_registry_service
    if _capability_registry_service is None:
        _capability_registry_service = CapabilityRegistryService()
    return _capability_registry_service
