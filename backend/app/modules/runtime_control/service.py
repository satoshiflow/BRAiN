from __future__ import annotations

import os
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.core.control_plane_events import ControlPlaneEventModel, record_control_plane_event

from .schemas import (
    AppliedOverride,
    AppliedPolicy,
    ExplainTraceStep,
    OverrideRequestStatus,
    ResolverResponse,
    ResolverValidation,
    RuntimeActiveOverride,
    RuntimeActiveOverrideListResponse,
    RuntimeDecisionContext,
    RuntimeOverrideRequestCreate,
    RuntimeOverrideRequestDecision,
    RuntimeOverrideRequestItem,
    RuntimeOverrideRequestListResponse,
    RuntimeRegistryVersionCreate,
    RuntimeRegistryVersionItem,
    RuntimeRegistryVersionListResponse,
    RuntimeRegistryVersionPromoteRequest,
    RegistryVersionStatus,
    RuntimeControlTimelineEvent,
    RuntimeControlTimelineResponse,
    RuntimeOverrideLevel,
)


class RuntimeControlResolverService:
    OVERRIDE_PRIORITY: list[RuntimeOverrideLevel] = [
        RuntimeOverrideLevel.EMERGENCY,
        RuntimeOverrideLevel.GOVERNOR,
        RuntimeOverrideLevel.MANUAL,
        RuntimeOverrideLevel.POLICY,
        RuntimeOverrideLevel.FEATURE_FLAGS,
        RuntimeOverrideLevel.REGISTRY,
        RuntimeOverrideLevel.DEFAULTS,
    ]

    def _hard_defaults(self) -> dict[str, Any]:
        return {
            "routing": {
                "llm": {
                    "default_provider": "ollama",
                    "allowed_providers": ["ollama", "openai", "openrouter", "anthropic"],
                    "default_model": "llama3.2:latest",
                }
            },
            "workers": {
                "selection": {
                    "default_executor": "miniworker",
                    "allowed_executors": ["miniworker", "opencode", "openclaw"],
                }
            },
            "budgets": {"skillrun": {"credit_limit": 5000, "soft_stop_threshold": 500}},
            "limits": {"parallel": {"max_worker_tasks": 3}},
            "timeouts": {"skillrun": {"default_seconds": 300}},
            "governance": {"approval_required": False},
            "flags": {"safe_mode": False},
        }

    def _registry_config(self) -> dict[str, Any]:
        local_mode = os.getenv("LOCAL_LLM_MODE", "ollama").strip().lower()
        if local_mode not in {"ollama", "openai", "openrouter", "anthropic"}:
            local_mode = "ollama"
        return {
            "routing": {"llm": {"default_provider": local_mode}},
            "timeouts": {
                "skillrun": {
                    "default_seconds": int(os.getenv("AXE_MINIWORKER_TIMEOUT_SECONDS", "300"))
                }
            },
        }

    @staticmethod
    def _set_path(target: dict[str, Any], key_path: str, value: Any) -> None:
        parts = key_path.split(".")
        cursor: dict[str, Any] = target
        for part in parts[:-1]:
            if part not in cursor or not isinstance(cursor[part], dict):
                cursor[part] = {}
            cursor = cursor[part]
        cursor[parts[-1]] = value

    def _merge(self, target: dict[str, Any], patch: dict[str, Any]) -> None:
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                self._merge(target[key], value)
            else:
                target[key] = value

    @staticmethod
    def is_connector_allowed(effective_config: dict[str, Any], connector_name: str) -> bool:
        security_cfg = effective_config.get("security", {}) if isinstance(effective_config, dict) else {}
        allowed = security_cfg.get("allowed_connectors") if isinstance(security_cfg, dict) else None
        if isinstance(allowed, list) and allowed:
            allowed_set = {str(item).strip().lower() for item in allowed}
            return connector_name.strip().lower() in allowed_set
        return True

    @staticmethod
    def _to_iso(ts: datetime | None) -> str | None:
        if ts is None:
            return None
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc).isoformat()
        return ts.isoformat()

    @staticmethod
    def _is_active_request(item: RuntimeOverrideRequestItem) -> bool:
        if item.status != OverrideRequestStatus.APPROVED:
            return False
        if not item.expires_at:
            return True
        try:
            expiry = datetime.fromisoformat(item.expires_at.replace("Z", "+00:00"))
        except Exception:
            return True
        return datetime.now(timezone.utc) <= expiry

    async def list_override_requests(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
    ) -> RuntimeOverrideRequestListResponse:
        result = await db.execute(
            select(ControlPlaneEventModel)
            .where(ControlPlaneEventModel.entity_type == "runtime_override_request")
            .order_by(desc(ControlPlaneEventModel.created_at))
            .limit(1000)
        )
        events = list(result.scalars().all())

        by_request_id: dict[str, RuntimeOverrideRequestItem] = {}
        for event in sorted(events, key=lambda item: item.created_at or datetime.now(timezone.utc)):
            payload = event.payload if isinstance(event.payload, dict) else {}
            request_id = str(payload.get("request_id") or event.entity_id)
            scope = str(payload.get("tenant_scope") or "tenant")

            if scope == "tenant" and tenant_id and payload.get("tenant_id") not in {tenant_id, None}:
                continue
            if scope == "tenant" and tenant_id is None:
                continue

            existing = by_request_id.get(request_id)
            created_at = self._to_iso(event.created_at) or datetime.now(timezone.utc).isoformat()
            if existing is None:
                existing = RuntimeOverrideRequestItem(
                    request_id=request_id,
                    tenant_id=payload.get("tenant_id"),
                    tenant_scope=scope,
                    key=str(payload.get("key") or ""),
                    value=payload.get("value"),
                    reason=str(payload.get("reason") or ""),
                    status=OverrideRequestStatus.PENDING,
                    created_by=str(payload.get("created_by") or event.actor_id or "unknown"),
                    created_at=created_at,
                    updated_at=created_at,
                    expires_at=payload.get("expires_at"),
                )
                by_request_id[request_id] = existing

            event_type = event.event_type
            existing.updated_at = created_at
            if event_type.endswith("created.v1"):
                existing.status = OverrideRequestStatus.PENDING
            elif event_type.endswith("approved.v1"):
                existing.status = OverrideRequestStatus.APPROVED
                existing.approved_by = str(payload.get("approved_by") or event.actor_id or "unknown")
                existing.approved_at = created_at
                existing.decision_reason = str(payload.get("decision_reason") or "")
            elif event_type.endswith("rejected.v1"):
                existing.status = OverrideRequestStatus.REJECTED
                existing.rejected_by = str(payload.get("rejected_by") or event.actor_id or "unknown")
                existing.rejected_at = created_at
                existing.decision_reason = str(payload.get("decision_reason") or "")

        items = sorted(by_request_id.values(), key=lambda item: item.updated_at, reverse=True)
        return RuntimeOverrideRequestListResponse(items=items, total=len(items))

    async def list_registry_versions(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
    ) -> RuntimeRegistryVersionListResponse:
        result = await db.execute(
            select(ControlPlaneEventModel)
            .where(ControlPlaneEventModel.entity_type == "runtime_registry_version")
            .order_by(desc(ControlPlaneEventModel.created_at))
            .limit(1000)
        )
        events = list(result.scalars().all())

        by_version: dict[str, RuntimeRegistryVersionItem] = {}
        for event in sorted(events, key=lambda item: item.created_at or datetime.now(timezone.utc)):
            payload = event.payload if isinstance(event.payload, dict) else {}
            version_id = str(payload.get("version_id") or event.entity_id)
            scope = str(payload.get("scope") or "tenant")
            version_tenant_id = payload.get("tenant_id")
            if scope == "tenant" and tenant_id and version_tenant_id not in {tenant_id, None}:
                continue
            if scope == "tenant" and tenant_id is None:
                continue

            created_at = self._to_iso(event.created_at) or datetime.now(timezone.utc).isoformat()
            existing = by_version.get(version_id)
            if existing is None:
                existing = RuntimeRegistryVersionItem(
                    version_id=version_id,
                    scope=scope,
                    tenant_id=version_tenant_id,
                    status=RegistryVersionStatus.DRAFT,
                    config_patch=payload.get("config_patch") or {},
                    reason=str(payload.get("reason") or ""),
                    created_by=str(payload.get("created_by") or event.actor_id or "unknown"),
                    created_at=created_at,
                    updated_at=created_at,
                )
                by_version[version_id] = existing

            existing.updated_at = created_at
            if event.event_type.endswith("created.v1"):
                existing.status = RegistryVersionStatus.DRAFT
            elif event.event_type.endswith("promoted.v1"):
                existing.status = RegistryVersionStatus.PROMOTED
                existing.promoted_by = str(payload.get("promoted_by") or event.actor_id or "unknown")
                existing.promoted_at = created_at
                existing.promotion_reason = str(payload.get("promotion_reason") or "")
            elif event.event_type.endswith("superseded.v1"):
                existing.status = RegistryVersionStatus.SUPERSEDED

        items = sorted(by_version.values(), key=lambda item: item.updated_at, reverse=True)
        return RuntimeRegistryVersionListResponse(items=items, total=len(items))

    async def create_registry_version(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
        payload: RuntimeRegistryVersionCreate,
    ) -> RuntimeRegistryVersionItem:
        version_id = f"rcv_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        tenant_id = principal.tenant_id if payload.scope == "tenant" else None
        event_payload = {
            "version_id": version_id,
            "scope": payload.scope,
            "tenant_id": tenant_id,
            "config_patch": payload.config_patch,
            "reason": payload.reason,
            "created_by": principal.principal_id,
        }
        await record_control_plane_event(
            db=db,
            tenant_id=tenant_id,
            entity_type="runtime_registry_version",
            entity_id=version_id,
            event_type="runtime.registry.version.created.v1",
            correlation_id=version_id,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload=event_payload,
            audit_required=True,
            audit_action="runtime_registry_version_create",
            audit_message="Runtime registry version created",
        )
        await db.commit()
        return RuntimeRegistryVersionItem(
            version_id=version_id,
            scope=payload.scope,
            tenant_id=tenant_id,
            status=RegistryVersionStatus.DRAFT,
            config_patch=payload.config_patch,
            reason=payload.reason,
            created_by=principal.principal_id,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
        )

    async def promote_registry_version(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
        version_id: str,
        payload: RuntimeRegistryVersionPromoteRequest,
    ) -> RuntimeRegistryVersionItem:
        versions = await self.list_registry_versions(db, tenant_id=principal.tenant_id)
        target = next((item for item in versions.items if item.version_id == version_id), None)
        if target is None:
            raise ValueError("Registry version not found")
        if target.status != RegistryVersionStatus.DRAFT:
            raise ValueError("Only draft versions can be promoted")

        for item in versions.items:
            if item.scope == target.scope and item.tenant_id == target.tenant_id and item.status == RegistryVersionStatus.PROMOTED:
                await record_control_plane_event(
                    db=db,
                    tenant_id=item.tenant_id,
                    entity_type="runtime_registry_version",
                    entity_id=item.version_id,
                    event_type="runtime.registry.version.superseded.v1",
                    correlation_id=version_id,
                    mission_id=None,
                    actor_id=principal.principal_id,
                    actor_type=principal.principal_type.value,
                    payload={
                        "version_id": item.version_id,
                        "scope": item.scope,
                        "tenant_id": item.tenant_id,
                        "superseded_by": version_id,
                    },
                    audit_required=True,
                    audit_action="runtime_registry_version_supersede",
                    audit_message="Runtime registry version superseded",
                )

        await record_control_plane_event(
            db=db,
            tenant_id=target.tenant_id,
            entity_type="runtime_registry_version",
            entity_id=version_id,
            event_type="runtime.registry.version.promoted.v1",
            correlation_id=version_id,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "version_id": version_id,
                "scope": target.scope,
                "tenant_id": target.tenant_id,
                "config_patch": target.config_patch,
                "reason": target.reason,
                "promotion_reason": payload.reason,
                "promoted_by": principal.principal_id,
            },
            audit_required=True,
            audit_action="runtime_registry_version_promote",
            audit_message="Runtime registry version promoted",
        )
        await db.commit()

        refreshed = await self.list_registry_versions(db, tenant_id=principal.tenant_id)
        promoted = next((item for item in refreshed.items if item.version_id == version_id), None)
        if promoted is None:
            raise ValueError("Registry version not found after promotion")
        return promoted

    async def list_timeline(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
        limit: int = 200,
    ) -> RuntimeControlTimelineResponse:
        result = await db.execute(
            select(ControlPlaneEventModel)
            .where(ControlPlaneEventModel.entity_type.in_([
                "runtime_override_request",
                "runtime_registry_version",
            ]))
            .order_by(desc(ControlPlaneEventModel.created_at))
            .limit(limit)
        )
        events = list(result.scalars().all())
        items: list[RuntimeControlTimelineEvent] = []
        for event in events:
            if tenant_id and event.tenant_id not in {tenant_id, None}:
                continue
            items.append(
                RuntimeControlTimelineEvent(
                    event_id=str(event.id),
                    event_type=event.event_type,
                    entity_type=event.entity_type,
                    entity_id=event.entity_id,
                    actor_id=event.actor_id,
                    actor_type=event.actor_type,
                    tenant_id=event.tenant_id,
                    correlation_id=event.correlation_id,
                    created_at=self._to_iso(event.created_at) or datetime.now(timezone.utc).isoformat(),
                    payload=event.payload if isinstance(event.payload, dict) else {},
                )
            )
        return RuntimeControlTimelineResponse(items=items, total=len(items))

    async def _active_registry_patch(self, db: AsyncSession, tenant_id: str | None) -> dict[str, Any]:
        versions = await self.list_registry_versions(db, tenant_id=tenant_id)
        for item in versions.items:
            if item.status == RegistryVersionStatus.PROMOTED:
                return item.config_patch or {}
        return {}

    async def list_active_overrides(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
    ) -> RuntimeActiveOverrideListResponse:
        requests = await self.list_override_requests(db, tenant_id=tenant_id)
        active_items = [
            RuntimeActiveOverride(
                request_id=item.request_id,
                key=item.key,
                value=item.value,
                reason=item.reason,
                tenant_id=item.tenant_id,
                expires_at=item.expires_at,
            )
            for item in requests.items
            if self._is_active_request(item)
        ]
        return RuntimeActiveOverrideListResponse(items=active_items, total=len(active_items))

    async def create_override_request(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
        payload: RuntimeOverrideRequestCreate,
    ) -> RuntimeOverrideRequestItem:
        request_id = f"rov_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        tenant_id = principal.tenant_id if payload.tenant_scope == "tenant" else None

        event_payload = {
            "request_id": request_id,
            "tenant_id": tenant_id,
            "tenant_scope": payload.tenant_scope,
            "key": payload.key,
            "value": payload.value,
            "reason": payload.reason,
            "created_by": principal.principal_id,
            "expires_at": payload.expires_at,
        }
        await record_control_plane_event(
            db=db,
            tenant_id=tenant_id,
            entity_type="runtime_override_request",
            entity_id=request_id,
            event_type="runtime.override.request.created.v1",
            correlation_id=request_id,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload=event_payload,
            audit_required=True,
            audit_action="runtime_override_request_create",
            audit_message="Runtime override change request created",
        )
        await db.commit()

        return RuntimeOverrideRequestItem(
            request_id=request_id,
            tenant_id=tenant_id,
            tenant_scope=payload.tenant_scope,
            key=payload.key,
            value=payload.value,
            reason=payload.reason,
            status=OverrideRequestStatus.PENDING,
            created_by=principal.principal_id,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            expires_at=payload.expires_at,
        )

    async def approve_override_request(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
        request_id: str,
        payload: RuntimeOverrideRequestDecision,
    ) -> RuntimeOverrideRequestItem:
        requests = await self.list_override_requests(db, tenant_id=principal.tenant_id)
        current = next((item for item in requests.items if item.request_id == request_id), None)
        if current is None:
            raise ValueError("Override request not found")
        if current.status != OverrideRequestStatus.PENDING:
            raise ValueError("Only pending requests can be approved")

        event_payload = {
            "request_id": request_id,
            "tenant_id": current.tenant_id,
            "tenant_scope": current.tenant_scope,
            "key": current.key,
            "value": current.value,
            "reason": current.reason,
            "decision_reason": payload.reason,
            "approved_by": principal.principal_id,
            "expires_at": current.expires_at,
        }
        await record_control_plane_event(
            db=db,
            tenant_id=current.tenant_id,
            entity_type="runtime_override_request",
            entity_id=request_id,
            event_type="runtime.override.request.approved.v1",
            correlation_id=request_id,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload=event_payload,
            audit_required=True,
            audit_action="runtime_override_request_approve",
            audit_message="Runtime override change request approved",
        )
        await db.commit()

        refreshed = await self.list_override_requests(db, tenant_id=principal.tenant_id)
        resolved = next((item for item in refreshed.items if item.request_id == request_id), None)
        if resolved is None:
            raise ValueError("Override request not found after approval")
        return resolved

    async def reject_override_request(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
        request_id: str,
        payload: RuntimeOverrideRequestDecision,
    ) -> RuntimeOverrideRequestItem:
        requests = await self.list_override_requests(db, tenant_id=principal.tenant_id)
        current = next((item for item in requests.items if item.request_id == request_id), None)
        if current is None:
            raise ValueError("Override request not found")
        if current.status != OverrideRequestStatus.PENDING:
            raise ValueError("Only pending requests can be rejected")

        event_payload = {
            "request_id": request_id,
            "tenant_id": current.tenant_id,
            "tenant_scope": current.tenant_scope,
            "key": current.key,
            "value": current.value,
            "reason": current.reason,
            "decision_reason": payload.reason,
            "rejected_by": principal.principal_id,
            "expires_at": current.expires_at,
        }
        await record_control_plane_event(
            db=db,
            tenant_id=current.tenant_id,
            entity_type="runtime_override_request",
            entity_id=request_id,
            event_type="runtime.override.request.rejected.v1",
            correlation_id=request_id,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload=event_payload,
            audit_required=True,
            audit_action="runtime_override_request_reject",
            audit_message="Runtime override change request rejected",
        )
        await db.commit()

        refreshed = await self.list_override_requests(db, tenant_id=principal.tenant_id)
        resolved = next((item for item in refreshed.items if item.request_id == request_id), None)
        if resolved is None:
            raise ValueError("Override request not found after rejection")
        return resolved

    async def resolve_with_persisted_overrides(
        self,
        ctx: RuntimeDecisionContext,
        *,
        db: AsyncSession,
    ) -> ResolverResponse:
        response = self.resolve(ctx)
        registry_patch = await self._active_registry_patch(db, ctx.tenant_id)
        effective = deepcopy(response.effective_config)
        applied = list(response.applied_overrides)
        trace = list(response.explain_trace)

        if registry_patch:
            self._merge(effective, registry_patch)
            trace.append(
                ExplainTraceStep(
                    level=RuntimeOverrideLevel.REGISTRY,
                    summary="Applied promoted registry version",
                    changes=registry_patch,
                )
            )

        active = await self.list_active_overrides(db, tenant_id=ctx.tenant_id)
        if active.total == 0 and not registry_patch:
            return response

        manual_changes: dict[str, Any] = {}
        for item in active.items:
            self._set_path(effective, item.key, item.value)
            manual_changes[item.key] = item.value
            applied.append(
                AppliedOverride(
                    level=RuntimeOverrideLevel.MANUAL,
                    key=item.key,
                    value=item.value,
                    reason=f"Approved request {item.request_id}",
                )
            )

        if manual_changes:
            trace.append(
                ExplainTraceStep(
                    level=RuntimeOverrideLevel.MANUAL,
                    summary="Applied persisted approved overrides",
                    changes=manual_changes,
                )
            )

        worker = str(effective.get("workers", {}).get("selection", {}).get("default_executor", "miniworker"))
        provider = str(effective.get("routing", {}).get("llm", {}).get("default_provider", "ollama"))
        route = "skillrun.bridge" if worker in {"miniworker", "openclaw"} else "direct.executor"
        model_map = {
            "ollama": "llama3.2:latest",
            "openai": "gpt-4o-mini",
            "openrouter": "anthropic/claude-3.5-sonnet",
            "anthropic": "claude-3-5-sonnet-20241022",
        }

        return ResolverResponse(
            decision_id=response.decision_id,
            effective_config=effective,
            selected_model=model_map.get(provider, "llama3.2:latest"),
            selected_worker=worker,
            selected_route=route,
            applied_policies=response.applied_policies,
            applied_overrides=applied,
            explain_trace=trace,
            validation=response.validation,
        )

    def resolve(self, ctx: RuntimeDecisionContext) -> ResolverResponse:
        decision_id = f"rdec_{uuid.uuid4().hex[:16]}"
        effective = self._hard_defaults()
        trace: list[ExplainTraceStep] = []
        policies: list[AppliedPolicy] = []
        overrides: list[AppliedOverride] = []

        registry_patch = self._registry_config()
        self._merge(effective, registry_patch)
        trace.append(
            ExplainTraceStep(
                level=RuntimeOverrideLevel.REGISTRY,
                summary="Applied registry configuration",
                changes=registry_patch,
            )
        )

        feature_flags = ctx.feature_context.get("feature_flags", {})
        if isinstance(feature_flags, dict) and feature_flags:
            flags_patch = {"flags": feature_flags}
            self._merge(effective, flags_patch)
            trace.append(
                ExplainTraceStep(
                    level=RuntimeOverrideLevel.FEATURE_FLAGS,
                    summary="Applied runtime feature flags",
                    changes=flags_patch,
                )
            )

        remaining_credits = float(ctx.budget_state.get("remaining_credits", 0) or 0)
        if remaining_credits > 0 and remaining_credits < 100:
            patch = {
                "routing": {"llm": {"default_provider": "ollama"}},
                "limits": {"parallel": {"max_worker_tasks": 1}},
            }
            self._merge(effective, patch)
            policies.append(
                AppliedPolicy(
                    policy_id="policy.budget.low_remaining_credits",
                    reason="Remaining credits below low-watermark",
                    effect="downgrade_provider_and_parallelism",
                )
            )
            trace.append(
                ExplainTraceStep(
                    level=RuntimeOverrideLevel.POLICY,
                    summary="Applied low-budget policy",
                    changes=patch,
                )
            )

        if ctx.risk_score >= 0.85:
            patch = {
                "routing": {"llm": {"default_provider": "ollama"}},
                "governance": {"approval_required": True},
                "limits": {"parallel": {"max_worker_tasks": 1}},
            }
            self._merge(effective, patch)
            policies.append(
                AppliedPolicy(
                    policy_id="policy.risk.high",
                    reason="Risk score >= 0.85",
                    effect="force_local_provider_and_approval",
                )
            )
            trace.append(
                ExplainTraceStep(
                    level=RuntimeOverrideLevel.POLICY,
                    summary="Applied high-risk policy",
                    changes=patch,
                )
            )

        manual_overrides = ctx.feature_context.get("manual_overrides", [])
        if isinstance(manual_overrides, list):
            for item in manual_overrides:
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key", "")).strip()
                if not key:
                    continue
                value = item.get("value")
                reason = str(item.get("reason", "Manual approved override"))
                self._set_path(effective, key, value)
                overrides.append(
                    AppliedOverride(
                        level=RuntimeOverrideLevel.MANUAL,
                        key=key,
                        value=value,
                        reason=reason,
                    )
                )

        governor_override = ctx.feature_context.get("governor_override")
        if isinstance(governor_override, dict):
            for key, value in governor_override.items():
                self._set_path(effective, key, value)
                overrides.append(
                    AppliedOverride(
                        level=RuntimeOverrideLevel.GOVERNOR,
                        key=key,
                        value=value,
                        reason="Governor override",
                    )
                )

        safe_mode_enabled = bool(ctx.system_health.get("safe_mode", False) or ctx.feature_context.get("emergency_override", False))
        if safe_mode_enabled:
            patch = {
                "flags": {"safe_mode": True},
                "routing": {"llm": {"default_provider": "ollama"}},
                "workers": {"selection": {"default_executor": "miniworker"}},
                "limits": {"parallel": {"max_worker_tasks": 1}},
                "timeouts": {"skillrun": {"default_seconds": 120}},
            }
            self._merge(effective, patch)
            overrides.append(
                AppliedOverride(
                    level=RuntimeOverrideLevel.EMERGENCY,
                    key="flags.safe_mode",
                    value=True,
                    reason="Emergency or safe mode active",
                )
            )
            trace.append(
                ExplainTraceStep(
                    level=RuntimeOverrideLevel.EMERGENCY,
                    summary="Applied emergency safety override",
                    changes=patch,
                )
            )

        provider = str(effective["routing"]["llm"].get("default_provider", "ollama"))
        allowed_providers = set(effective["routing"]["llm"].get("allowed_providers", []))
        issues: list[str] = []
        if provider not in allowed_providers:
            issues.append(f"Selected provider '{provider}' is not allowed")

        worker = str(effective["workers"]["selection"].get("default_executor", "miniworker"))
        route = "skillrun.bridge" if worker in {"miniworker", "openclaw"} else "direct.executor"
        model_map = {
            "ollama": "llama3.2:latest",
            "openai": "gpt-4o-mini",
            "openrouter": "anthropic/claude-3.5-sonnet",
            "anthropic": "claude-3-5-sonnet-20241022",
        }
        model = model_map.get(provider, "llama3.2:latest")

        return ResolverResponse(
            decision_id=decision_id,
            effective_config=deepcopy(effective),
            selected_model=model,
            selected_worker=worker,
            selected_route=route,
            applied_policies=policies,
            applied_overrides=overrides,
            explain_trace=trace,
            validation=ResolverValidation(valid=len(issues) == 0, issues=issues),
        )


_runtime_control_service: RuntimeControlResolverService | None = None


def get_runtime_control_service() -> RuntimeControlResolverService:
    global _runtime_control_service
    if _runtime_control_service is None:
        _runtime_control_service = RuntimeControlResolverService()
    return _runtime_control_service
