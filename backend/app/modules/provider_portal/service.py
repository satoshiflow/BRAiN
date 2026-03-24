from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.core.control_plane_events import record_control_plane_event
from app.modules.skills_registry.schemas import OwnerScope

from .credential_service import get_provider_credential_service
from .models import (
    ProviderAccountModel,
    ProviderCredentialModel,
    ProviderHealthCheckModel,
    ProviderModelModel,
)
from .schemas import (
    AuthMode,
    HealthStatus,
    ProviderAccountCreate,
    ProviderAccountUpdate,
    ProviderCredentialSetRequest,
    ProviderModelCreate,
    ProviderModelUpdate,
    ProviderTestRequest,
)


class ProviderPortalService:
    def __init__(self) -> None:
        self.credential_service = get_provider_credential_service()

    @staticmethod
    def _derive_scope(principal: Principal, requested_scope: OwnerScope) -> tuple[str | None, str]:
        if requested_scope == OwnerScope.SYSTEM:
            return None, OwnerScope.SYSTEM.value
        if not principal.tenant_id:
            raise ValueError("Tenant-scoped provider account requires tenant-bound principal")
        return principal.tenant_id, OwnerScope.TENANT.value

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _classify_status(status_code: int) -> tuple[HealthStatus, str | None]:
        if 200 <= status_code < 300:
            return HealthStatus.HEALTHY, None
        if status_code in {401, 403}:
            return HealthStatus.FAILED, "auth_error"
        if status_code >= 500:
            return HealthStatus.DEGRADED, "upstream_error"
        return HealthStatus.FAILED, "invalid_response"

    async def _record_event(
        self,
        db: AsyncSession,
        principal: Principal,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
        audit_required: bool,
        audit_action: str,
        audit_message: str,
    ) -> None:
        await record_control_plane_event(
            db=db,
            tenant_id=principal.tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            correlation_id=None,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload=payload,
            audit_required=audit_required,
            audit_action=audit_action,
            audit_message=audit_message,
        )

    async def _active_credential(self, db: AsyncSession, provider_id: UUID) -> ProviderCredentialModel | None:
        result = await db.execute(
            select(ProviderCredentialModel)
            .where(
                ProviderCredentialModel.provider_id == provider_id,
                ProviderCredentialModel.is_active.is_(True),
            )
            .order_by(ProviderCredentialModel.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_provider(self, db: AsyncSession, payload: ProviderAccountCreate, principal: Principal) -> ProviderAccountModel:
        tenant_id, owner_scope = self._derive_scope(principal, payload.owner_scope)
        existing = await db.execute(
            select(ProviderAccountModel).where(
                ProviderAccountModel.slug == payload.slug,
                ProviderAccountModel.owner_scope == owner_scope,
                ProviderAccountModel.tenant_id.is_(tenant_id) if tenant_id is None else ProviderAccountModel.tenant_id == tenant_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("Provider slug already exists in this scope")

        model = ProviderAccountModel(
            tenant_id=tenant_id,
            owner_scope=owner_scope,
            slug=payload.slug,
            display_name=payload.display_name,
            provider_type=payload.provider_type.value,
            base_url=payload.base_url,
            auth_mode=payload.auth_mode.value,
            is_enabled=payload.is_enabled,
            is_local=payload.is_local,
            supports_chat=payload.supports_chat,
            supports_embeddings=payload.supports_embeddings,
            supports_responses=payload.supports_responses,
            notes=payload.notes,
            created_by=principal.principal_id,
            updated_by=principal.principal_id,
        )
        db.add(model)
        await db.flush()
        await self._record_event(
            db,
            principal,
            event_type="provider.portal.account.created.v1",
            entity_type="provider_account",
            entity_id=str(model.id),
            payload={"slug": model.slug, "provider_type": model.provider_type},
            audit_required=True,
            audit_action="provider_account_create",
            audit_message="Provider account created",
        )
        await db.commit()
        await db.refresh(model)
        return model

    async def list_providers(self, db: AsyncSession, tenant_id: str | None) -> list[ProviderAccountModel]:
        query = select(ProviderAccountModel)
        if tenant_id:
            query = query.where(
                or_(
                    and_(ProviderAccountModel.owner_scope == OwnerScope.TENANT.value, ProviderAccountModel.tenant_id == tenant_id),
                    ProviderAccountModel.owner_scope == OwnerScope.SYSTEM.value,
                )
            )
        else:
            query = query.where(ProviderAccountModel.owner_scope == OwnerScope.SYSTEM.value)
        query = query.order_by(ProviderAccountModel.display_name.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_provider(self, db: AsyncSession, provider_id: UUID, tenant_id: str | None) -> ProviderAccountModel | None:
        provider = await db.get(ProviderAccountModel, provider_id)
        if provider is None:
            return None
        if provider.owner_scope == OwnerScope.TENANT.value and provider.tenant_id != tenant_id:
            return None
        return provider

    async def update_provider(
        self,
        db: AsyncSession,
        provider_id: UUID,
        payload: ProviderAccountUpdate,
        principal: Principal,
    ) -> ProviderAccountModel | None:
        provider = await self.get_provider(db, provider_id, principal.tenant_id)
        if provider is None:
            return None

        updates = payload.model_dump(exclude_none=True)
        if not updates:
            return provider

        for key, value in updates.items():
            if hasattr(value, "value"):
                value = value.value
            setattr(provider, key, value)
        provider.updated_by = principal.principal_id
        provider.updated_at = self._now()

        await self._record_event(
            db,
            principal,
            event_type="provider.portal.account.updated.v1",
            entity_type="provider_account",
            entity_id=str(provider.id),
            payload={"updated_fields": sorted(list(updates.keys()))},
            audit_required=True,
            audit_action="provider_account_update",
            audit_message="Provider account updated",
        )
        await db.commit()
        await db.refresh(provider)
        return provider

    async def set_credential(
        self,
        db: AsyncSession,
        provider_id: UUID,
        payload: ProviderCredentialSetRequest,
        principal: Principal,
    ) -> ProviderCredentialModel | None:
        provider = await self.get_provider(db, provider_id, principal.tenant_id)
        if provider is None:
            return None

        if payload.activate:
            await db.execute(
                update(ProviderCredentialModel)
                .where(
                    ProviderCredentialModel.provider_id == provider_id,
                    ProviderCredentialModel.is_active.is_(True),
                )
                .values(is_active=False, updated_by=principal.principal_id, updated_at=self._now())
            )

        secret_ciphertext = self.credential_service.encrypt(payload.api_key)
        key_hint = self.credential_service.masked_hint(payload.api_key)
        credential = ProviderCredentialModel(
            provider_id=provider_id,
            secret_ciphertext=secret_ciphertext,
            key_hint_last4=key_hint,
            is_active=payload.activate,
            created_by=principal.principal_id,
            updated_by=principal.principal_id,
        )
        db.add(credential)
        await db.flush()

        await self._record_event(
            db,
            principal,
            event_type="provider.portal.credential.set.v1",
            entity_type="provider_credential",
            entity_id=str(credential.id),
            payload={"provider_id": str(provider_id), "is_active": credential.is_active},
            audit_required=True,
            audit_action="provider_credential_set",
            audit_message="Provider credential updated",
        )
        await db.commit()
        await db.refresh(credential)
        return credential

    async def deactivate_credential(
        self,
        db: AsyncSession,
        provider_id: UUID,
        principal: Principal,
    ) -> ProviderCredentialModel | None:
        provider = await self.get_provider(db, provider_id, principal.tenant_id)
        if provider is None:
            return None
        credential = await self._active_credential(db, provider_id)
        if credential is None:
            return None
        credential.is_active = False
        credential.updated_by = principal.principal_id
        credential.updated_at = self._now()

        await self._record_event(
            db,
            principal,
            event_type="provider.portal.credential.deactivated.v1",
            entity_type="provider_credential",
            entity_id=str(credential.id),
            payload={"provider_id": str(provider_id)},
            audit_required=True,
            audit_action="provider_credential_deactivate",
            audit_message="Provider credential deactivated",
        )
        await db.commit()
        await db.refresh(credential)
        return credential

    async def list_models(
        self,
        db: AsyncSession,
        tenant_id: str | None,
        provider_id: UUID | None = None,
    ) -> list[ProviderModelModel]:
        query = select(ProviderModelModel)
        if provider_id is not None:
            query = query.where(ProviderModelModel.provider_id == provider_id)
        result = await db.execute(query.order_by(ProviderModelModel.priority.asc(), ProviderModelModel.model_name.asc()))
        models = list(result.scalars().all())
        if provider_id is not None:
            provider = await self.get_provider(db, provider_id, tenant_id)
            if provider is None:
                return []
            return models
        if tenant_id is None:
            return models

        filtered: list[ProviderModelModel] = []
        for model in models:
            provider = await self.get_provider(db, model.provider_id, tenant_id)
            if provider is not None:
                filtered.append(model)
        return filtered

    async def create_model(self, db: AsyncSession, payload: ProviderModelCreate, principal: Principal) -> ProviderModelModel | None:
        provider = await self.get_provider(db, payload.provider_id, principal.tenant_id)
        if provider is None:
            return None

        existing = await db.execute(
            select(ProviderModelModel).where(
                ProviderModelModel.provider_id == payload.provider_id,
                ProviderModelModel.model_name == payload.model_name,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("Provider model already exists")

        model = ProviderModelModel(**payload.model_dump())
        db.add(model)
        await db.flush()
        await self._record_event(
            db,
            principal,
            event_type="provider.portal.model.created.v1",
            entity_type="provider_model",
            entity_id=str(model.id),
            payload={"provider_id": str(model.provider_id), "model_name": model.model_name},
            audit_required=False,
            audit_action="provider_model_create",
            audit_message="Provider model created",
        )
        await db.commit()
        await db.refresh(model)
        return model

    async def update_model(
        self,
        db: AsyncSession,
        model_id: UUID,
        payload: ProviderModelUpdate,
        principal: Principal,
    ) -> ProviderModelModel | None:
        model = await db.get(ProviderModelModel, model_id)
        if model is None:
            return None
        provider = await self.get_provider(db, model.provider_id, principal.tenant_id)
        if provider is None:
            return None

        updates = payload.model_dump(exclude_none=True)
        if not updates:
            return model
        for key, value in updates.items():
            setattr(model, key, value)
        model.updated_at = self._now()
        await self._record_event(
            db,
            principal,
            event_type="provider.portal.model.updated.v1",
            entity_type="provider_model",
            entity_id=str(model.id),
            payload={"updated_fields": sorted(list(updates.keys()))},
            audit_required=False,
            audit_action="provider_model_update",
            audit_message="Provider model updated",
        )
        await db.commit()
        await db.refresh(model)
        return model

    async def binding_projection(
        self,
        db: AsyncSession,
        provider_id: UUID,
        model_name: str | None,
        tenant_id: str | None,
    ) -> dict[str, Any] | None:
        provider = await self.get_provider(db, provider_id, tenant_id)
        if provider is None:
            return None
        selected_model = model_name
        if selected_model is None:
            models = await self.list_models(db, tenant_id, provider_id=provider_id)
            enabled = [item for item in models if item.is_enabled]
            selected_model = enabled[0].model_name if enabled else None

        adapter_key = "generic_openai_compatible_adapter"
        lower_slug = provider.slug.lower()
        if lower_slug == "ollama" or "11434" in provider.base_url:
            adapter_key = "ollama_adapter"
        elif lower_slug == "openai":
            adapter_key = "openai_adapter"

        return {
            "owner_scope": provider.owner_scope,
            "provider_key": provider.slug,
            "provider_type": "llm",
            "adapter_key": adapter_key,
            "endpoint_ref": provider.base_url,
            "model_or_tool_ref": selected_model,
            "status": "enabled" if provider.is_enabled else "disabled",
            "capability_key": "text.generate",
            "capability_version": 1,
            "config": {"provider": provider.slug},
        }

    async def test_provider(
        self,
        db: AsyncSession,
        provider_id: UUID,
        payload: ProviderTestRequest,
        principal: Principal,
    ) -> dict[str, Any] | None:
        provider = await self.get_provider(db, provider_id, principal.tenant_id)
        if provider is None:
            return None

        projection = await self.binding_projection(db, provider_id, payload.model_name, principal.tenant_id)
        if projection is None:
            return None

        credential = await self._active_credential(db, provider_id)
        headers = {"Content-Type": "application/json"}
        if provider.auth_mode == AuthMode.API_KEY.value:
            if credential is None:
                status_value = HealthStatus.FAILED
                error_code = "missing_credential"
                error_message = "No active credential configured"
                latency_ms = None
                checked_at = self._now()
            else:
                raw_secret = self.credential_service.decrypt(credential.secret_ciphertext)
                headers["Authorization"] = f"Bearer {raw_secret}"
                status_value, error_code, error_message, latency_ms, checked_at = await self._probe_provider(
                    base_url=provider.base_url,
                    model_name=projection.get("model_or_tool_ref") or "gpt-4o-mini",
                    timeout_seconds=payload.timeout_seconds,
                    headers=headers,
                )
        else:
            status_value, error_code, error_message, latency_ms, checked_at = await self._probe_provider(
                base_url=provider.base_url,
                model_name=projection.get("model_or_tool_ref") or "qwen2.5:0.5b",
                timeout_seconds=payload.timeout_seconds,
                headers=headers,
            )

        provider.health_status = status_value.value
        provider.last_health_at = checked_at
        provider.last_health_error = error_message if status_value != HealthStatus.HEALTHY else None
        provider.updated_by = principal.principal_id
        provider.updated_at = self._now()

        probe = ProviderHealthCheckModel(
            provider_id=provider.id,
            status=status_value.value,
            latency_ms=latency_ms,
            error_code=error_code,
            error_message=error_message,
            checked_at=checked_at,
            created_by=principal.principal_id,
        )
        db.add(probe)

        await self._record_event(
            db,
            principal,
            event_type="provider.portal.test.executed.v1",
            entity_type="provider_account",
            entity_id=str(provider.id),
            payload={"status": status_value.value, "error_code": error_code},
            audit_required=False,
            audit_action="provider_test",
            audit_message="Provider connection tested",
        )
        await db.commit()
        await db.refresh(provider)

        return {
            "provider_id": provider.id,
            "status": status_value,
            "success": status_value == HealthStatus.HEALTHY,
            "latency_ms": latency_ms,
            "error_code": error_code,
            "error_message": error_message,
            "checked_at": checked_at,
            "binding_projection": projection,
        }

    async def _probe_provider(
        self,
        *,
        base_url: str,
        model_name: str,
        timeout_seconds: float,
        headers: dict[str, str],
    ) -> tuple[HealthStatus, str | None, str | None, int | None, datetime]:
        checked_at = self._now()
        start = time.monotonic()
        url = base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": "Health check: return 'ok'."}],
            "max_tokens": 8,
            "temperature": 0,
        }
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
            latency_ms = int((time.monotonic() - start) * 1000)
            status_value, error_code = self._classify_status(response.status_code)
            error_message = None
            if error_code is not None:
                error_message = f"HTTP {response.status_code}"
            return status_value, error_code, error_message, latency_ms, checked_at
        except httpx.TimeoutException:
            latency_ms = int((time.monotonic() - start) * 1000)
            return HealthStatus.DEGRADED, "timeout", "Probe timed out", latency_ms, checked_at
        except httpx.HTTPError as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            return HealthStatus.FAILED, "connection_error", str(exc)[:240], latency_ms, checked_at


_provider_portal_service: ProviderPortalService | None = None


def get_provider_portal_service() -> ProviderPortalService:
    global _provider_portal_service
    if _provider_portal_service is None:
        _provider_portal_service = ProviderPortalService()
    return _provider_portal_service
