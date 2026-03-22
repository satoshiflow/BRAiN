from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.core.control_plane_events import record_control_plane_event
from app.core.redis_client import get_redis
from app.modules.skills_registry.schemas import OwnerScope

from .models import ProviderBindingModel
from .schemas import ProviderBindingCreate, ProviderBindingResponse, ProviderBindingStatus, ResolvedProviderSelection


class ProviderBindingService:
    HEALTH_KEY = "brain:provider_bindings:health:{binding_id}"
    TRANSITIONS = {
        ProviderBindingStatus.DRAFT.value: {ProviderBindingStatus.ENABLED.value, ProviderBindingStatus.DISABLED.value},
        ProviderBindingStatus.ENABLED.value: {ProviderBindingStatus.DISABLED.value, ProviderBindingStatus.QUARANTINED.value},
        ProviderBindingStatus.QUARANTINED.value: {ProviderBindingStatus.ENABLED.value, ProviderBindingStatus.DISABLED.value},
        ProviderBindingStatus.DISABLED.value: {ProviderBindingStatus.ENABLED.value},
    }

    @staticmethod
    def is_transition_allowed(current: str, target: str) -> bool:
        return target in ProviderBindingService.TRANSITIONS.get(current, set())

    def _derive_scope(self, principal: Principal, requested_scope: OwnerScope) -> tuple[str | None, str]:
        if requested_scope == OwnerScope.SYSTEM:
            if not principal.has_scope("platform:catalog:write"):
                raise PermissionError("System scope requires platform:catalog:write")
            return None, OwnerScope.SYSTEM.value
        if not principal.tenant_id:
            raise ValueError("Tenant-scoped provider bindings require a tenant-bound principal")
        return principal.tenant_id, OwnerScope.TENANT.value

    async def create_binding(self, db: AsyncSession, payload: ProviderBindingCreate, principal: Principal) -> ProviderBindingModel:
        tenant_id, owner_scope = self._derive_scope(principal, payload.owner_scope)
        existing = await db.execute(
            select(ProviderBindingModel).where(
                ProviderBindingModel.capability_key == payload.capability_key,
                ProviderBindingModel.capability_version == payload.capability_version,
                ProviderBindingModel.provider_key == payload.provider_key,
                ProviderBindingModel.tenant_id.is_(tenant_id) if tenant_id is None else ProviderBindingModel.tenant_id == tenant_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("Provider binding already exists for this capability/provider scope")
        if payload.valid_from and payload.valid_to and payload.valid_to <= payload.valid_from:
            raise ValueError("valid_to must be greater than valid_from")
        model = ProviderBindingModel(
            tenant_id=tenant_id,
            owner_scope=owner_scope,
            capability_key=payload.capability_key,
            capability_version=payload.capability_version,
            provider_key=payload.provider_key,
            provider_type=payload.provider_type.value,
            adapter_key=payload.adapter_key,
            endpoint_ref=payload.endpoint_ref,
            model_or_tool_ref=payload.model_or_tool_ref,
            region=payload.region,
            priority=payload.priority,
            weight=payload.weight,
            cost_profile=payload.cost_profile,
            sla_profile=payload.sla_profile,
            policy_constraints=payload.policy_constraints,
            valid_from=payload.valid_from,
            valid_to=payload.valid_to,
            config=payload.config,
            definition_artifact_refs=payload.definition_artifact_refs,
            evidence_artifact_refs=payload.evidence_artifact_refs,
            created_by=principal.principal_id,
            updated_by=principal.principal_id,
        )
        db.add(model)
        await db.flush()
        await record_control_plane_event(
            db=db,
            tenant_id=tenant_id,
            entity_type="provider_binding",
            entity_id=str(model.id),
            event_type="provider.binding.created.v1",
            correlation_id=None,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={"capability_key": model.capability_key, "provider_key": model.provider_key, "status": model.status},
            audit_required=True,
            audit_action="provider_binding_create",
            audit_message="Provider binding created",
        )
        await db.commit()
        await db.refresh(model)
        return model

    async def list_bindings(
        self,
        db: AsyncSession,
        capability_key: str,
        capability_version: int,
        tenant_id: str | None,
    ) -> list[ProviderBindingModel]:
        query = select(ProviderBindingModel).where(
            ProviderBindingModel.capability_key == capability_key,
            ProviderBindingModel.capability_version == capability_version,
        )
        if tenant_id:
            query = query.where(
                or_(
                    and_(ProviderBindingModel.owner_scope == OwnerScope.TENANT.value, ProviderBindingModel.tenant_id == tenant_id),
                    ProviderBindingModel.owner_scope == OwnerScope.SYSTEM.value,
                )
            )
        else:
            query = query.where(ProviderBindingModel.owner_scope == OwnerScope.SYSTEM.value)
        query = query.order_by(ProviderBindingModel.priority.asc(), ProviderBindingModel.created_at.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_binding(self, db: AsyncSession, binding_id, tenant_id: str | None) -> ProviderBindingModel | None:
        binding = await db.get(ProviderBindingModel, binding_id)
        if binding is None:
            return None
        if binding.owner_scope == OwnerScope.TENANT.value and binding.tenant_id != tenant_id:
            return None
        return binding

    async def transition_binding(
        self,
        db: AsyncSession,
        binding_id,
        target_status: ProviderBindingStatus,
        principal: Principal,
    ) -> ProviderBindingModel | None:
        binding = await db.get(ProviderBindingModel, binding_id)
        if binding is None:
            return None
        if binding.owner_scope == OwnerScope.TENANT.value and binding.tenant_id != principal.tenant_id:
            raise PermissionError("Provider binding is not accessible for current tenant")
        if not self.is_transition_allowed(binding.status, target_status.value):
            raise ValueError(f"Illegal provider binding transition: {binding.status} -> {target_status.value}")
        binding.status = target_status.value
        binding.updated_by = principal.principal_id
        await record_control_plane_event(
            db=db,
            tenant_id=binding.tenant_id,
            entity_type="provider_binding",
            entity_id=str(binding.id),
            event_type=f"provider.binding.{target_status.value}.v1",
            correlation_id=None,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={"capability_key": binding.capability_key, "provider_key": binding.provider_key, "status": binding.status},
            audit_required=True,
            audit_action=f"provider_binding_{target_status.value}",
            audit_message=f"Provider binding moved to {target_status.value}",
        )
        await db.commit()
        await db.refresh(binding)
        return binding

    async def update_health_projection(
        self,
        *,
        binding_id: str,
        health_status: str,
        latency_p95_ms: float | None = None,
        error_rate_5m: float | None = None,
        circuit_state: str | None = None,
        ttl_seconds: int = 300,
        db: AsyncSession | None = None,
        principal: Principal | None = None,
    ) -> dict[str, Any]:
        projection = {
            "health_status": health_status,
            "latency_p95_ms": latency_p95_ms,
            "error_rate_5m": error_rate_5m,
            "circuit_state": circuit_state,
            "last_probe_at": datetime.now(timezone.utc).isoformat(),
        }
        redis = await get_redis()
        await redis.setex(self.HEALTH_KEY.format(binding_id=binding_id), ttl_seconds, json.dumps(projection))
        if db is not None:
            binding = await db.get(ProviderBindingModel, binding_id)
            if binding is not None:
                await record_control_plane_event(
                    db=db,
                    tenant_id=binding.tenant_id,
                    entity_type="provider_binding",
                    entity_id=str(binding.id),
                    event_type="provider.binding.health.updated.v1",
                    correlation_id=None,
                    mission_id=None,
                    actor_id=principal.principal_id if principal else "provider_binding_health",
                    actor_type=principal.principal_type.value if principal else "system",
                    payload=projection,
                    audit_required=False,
                )
                await db.commit()
        return projection

    async def get_health_projection(self, binding_id: str) -> dict[str, Any] | None:
        redis = await get_redis()
        raw = await redis.get(self.HEALTH_KEY.format(binding_id=binding_id))
        if not raw:
            return None
        return json.loads(raw)

    async def resolve_binding_for_execution(
        self,
        db: AsyncSession,
        *,
        capability_key: str,
        capability_version: int,
        tenant_id: str | None,
        policy_context: dict[str, Any],
    ) -> ResolvedProviderSelection | None:
        now = datetime.now(timezone.utc)
        bindings = await self.list_bindings(db, capability_key, capability_version, tenant_id)
        eligible = []
        for binding in bindings:
            if binding.status != ProviderBindingStatus.ENABLED.value:
                continue
            if binding.valid_from and binding.valid_from > now:
                continue
            if binding.valid_to and binding.valid_to <= now:
                continue
            eligible.append(binding)
        if not eligible:
            return None
        chosen = eligible[0]
        return ResolvedProviderSelection(
            provider_binding_id=str(chosen.id),
            selection_reason="persistent_binding_priority",
            policy_context=policy_context,
            resolved_at=now,
            binding_snapshot=ProviderBindingResponse.model_validate(chosen).model_dump(mode="json"),
        )

    async def find_binding_by_provider(
        self,
        db: AsyncSession,
        *,
        capability_key: str,
        capability_version: int,
        provider_key: str,
        tenant_id: str | None,
    ) -> ProviderBindingModel | None:
        bindings = await self.list_bindings(db, capability_key, capability_version, tenant_id)
        now = datetime.now(timezone.utc)
        for binding in bindings:
            if binding.provider_key != provider_key or binding.status != ProviderBindingStatus.ENABLED.value:
                continue
            if binding.valid_from and binding.valid_from > now:
                continue
            if binding.valid_to and binding.valid_to <= now:
                continue
            return binding
        return None


_provider_binding_service: ProviderBindingService | None = None


def get_provider_binding_service() -> ProviderBindingService:
    global _provider_binding_service
    if _provider_binding_service is None:
        _provider_binding_service = ProviderBindingService()
    return _provider_binding_service
