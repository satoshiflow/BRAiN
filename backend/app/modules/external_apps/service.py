from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.core.control_plane_events import ControlPlaneEventModel, record_control_plane_event
from app.modules.skill_engine.schemas import SkillRunCreate, SkillRunResponse, TriggerType
from app.modules.skill_engine.service import get_skill_engine_service
from app.modules.supervisor.schemas import DomainEscalationRequest
from app.modules.supervisor.service import create_domain_escalation_handoff
from app.modules.task_queue.schemas import TaskCreate, TaskPriority, TaskResponse
from app.modules.task_queue.service import get_task_queue_service
from app.modules.runtime_control.schemas import RuntimeDecisionContext
from app.modules.runtime_control.service import get_runtime_control_service

from .schemas import (
    ExternalAppSlug,
    PaperclipActionRequest,
    PaperclipActionRequestDecision,
    PaperclipActionRequestItem,
    PaperclipActionRequestListResponse,
    PaperclipActionRequestResponse,
    PaperclipExecutionContextResponse,
    PaperclipHandoffExchangeRequest,
    PaperclipHandoffExchangeResponse,
    PaperclipHandoffRequest,
    PaperclipHandoffResponse,
)


@dataclass(frozen=True)
class ExternalAppConfig:
    app_slug: ExternalAppSlug
    display_name: str
    audience: str
    app_base_env: str
    app_base_default: str
    handoff_path_env: str
    handoff_path_default: str
    runtime_mission_type: str
    runtime_skill_type: str
    executor_name: str
    connector_name: str
    handoff_risk_score: float


PAPERCLIP_CONFIG = ExternalAppConfig(
    app_slug="paperclip",
    display_name="Paperclip",
    audience="paperclip-ui",
    app_base_env="PAPERCLIP_APP_BASE_URL",
    app_base_default="http://localhost:3111",
    handoff_path_env="PAPERCLIP_HANDOFF_PATH",
    handoff_path_default="/handoff/paperclip",
    runtime_mission_type="connector.paperclip",
    runtime_skill_type="paperclip.handoff",
    executor_name="paperclip",
    connector_name="paperclip",
    handoff_risk_score=0.2,
)


OPENCLAW_CONFIG = ExternalAppConfig(
    app_slug="openclaw",
    display_name="OpenClaw",
    audience="openclaw-ui",
    app_base_env="OPENCLAW_APP_BASE_URL",
    app_base_default="http://localhost:3112",
    handoff_path_env="OPENCLAW_HANDOFF_PATH",
    handoff_path_default="/handoff/openclaw",
    runtime_mission_type="connector.openclaw",
    runtime_skill_type="openclaw.handoff",
    executor_name="openclaw",
    connector_name="openclaw",
    handoff_risk_score=0.3,
)


class PaperclipHandoffService:
    TERMINAL_TASK_STATES = {"failed", "cancelled", "timeout"}
    TERMINAL_SKILL_STATES = {"failed", "cancelled", "timed_out"}

    def __init__(self, config: ExternalAppConfig = PAPERCLIP_CONFIG) -> None:
        self.config = config

    def _handoff_event_type(self, suffix: str) -> str:
        return f"external.handoff.{self.config.app_slug}.{suffix}.v1"

    def _action_request_event_type(self, suffix: str) -> str:
        return f"external.action_request.{self.config.app_slug}.{suffix}.v1"

    def _handoff_secret(self) -> str:
        secret = (
            os.getenv("BRAIN_EXTERNAL_APP_HANDOFF_SECRET")
            or os.getenv("BRAIN_EXTERNAL_EXECUTOR_PERMIT_SECRET")
            or ""
        ).strip()
        if not secret:
            raise RuntimeError("BRAIN_EXTERNAL_APP_HANDOFF_SECRET missing")
        return secret

    def _paperclip_app_base_url(self) -> str:
        base_url = (
            os.getenv(self.config.app_base_env)
            or os.getenv(f"{self.config.executor_name.upper()}_BASE_URL")
            or self.config.app_base_default
        ).strip()
        return base_url.rstrip("/")

    def _paperclip_handoff_path(self) -> str:
        path = os.getenv(self.config.handoff_path_env, self.config.handoff_path_default).strip()
        if not path.startswith("/"):
            path = f"/{path}"
        return path

    def _handoff_ttl_seconds(self) -> int:
        raw_value = os.getenv("PAPERCLIP_HANDOFF_TTL_SECONDS", "180").strip()
        try:
            parsed = int(raw_value)
        except ValueError:
            parsed = 180
        return min(max(parsed, 60), 300)

    def _handoff_max_uses(self) -> int:
        raw_value = os.getenv("PAPERCLIP_HANDOFF_MAX_USES", "1").strip()
        try:
            parsed = int(raw_value)
        except ValueError:
            parsed = 1
        return min(max(parsed, 1), 5)

    def _suggested_path(self, target_type: str, target_ref: str) -> str:
        if target_type == "issue":
            return f"/app/issues/{target_ref}"
        if target_type == "project":
            return f"/app/projects/{target_ref}"
        if target_type == "agent":
            return f"/app/agents/{target_ref}"
        if target_type == "company":
            return f"/app/companies/{target_ref}"
        return f"/app/executions/{target_ref}"

    def _decode_handoff_token(self, token: str) -> dict[str, Any]:
        return jwt.decode(token, self._handoff_secret(), algorithms=["HS256"], audience=self.config.audience)

    @staticmethod
    def _task_state(task: Any) -> str:
        value = getattr(task, "status", None)
        return str(value.value if hasattr(value, "value") else value or "").lower()

    @staticmethod
    def _skill_state(skill_run: Any | None) -> str:
        if skill_run is None:
            return ""
        value = getattr(skill_run, "state", None)
        return str(value.value if hasattr(value, "value") else value or "").lower()

    def _available_actions(self, task: Any, skill_run: Any | None) -> list[str]:
        actions: list[str] = ["request_escalation"]
        if self._skill_state(skill_run) == "waiting_approval":
            actions.append("request_approval")
        if self._task_state(task) in self.TERMINAL_TASK_STATES or self._skill_state(skill_run) in self.TERMINAL_SKILL_STATES:
            actions.append("request_retry")
        return actions

    @staticmethod
    def _serialize_action_execution_result(payload: dict[str, Any]) -> dict[str, str]:
        return {str(key): str(value) for key, value in payload.items() if value is not None}

    @staticmethod
    def _action_request_visible(tenant_id: str | None, principal: Principal) -> bool:
        roles = {str(role).strip().lower() for role in (principal.roles or [])}
        if roles.intersection({"admin", "system_admin", "service"}):
            return True
        if principal.tenant_id is None:
            return tenant_id is None
        return tenant_id in {principal.tenant_id, None}

    def _build_execution_permit(
        self,
        *,
        executor_type: str,
        skill_run_id: str,
        task_id: str,
        correlation_id: str | None,
        ttl_seconds: int = 900,
    ) -> dict[str, Any]:
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(seconds=max(60, ttl_seconds))
        permit_payload: dict[str, Any] = {
            "executor_type": executor_type,
            "skill_run_id": skill_run_id,
            "allowed_actions": ["worker_bridge_execute"],
            "allowed_connectors": [executor_type],
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "task_id": task_id,
            "correlation_id": correlation_id,
        }
        secret = os.getenv("BRAIN_EXTERNAL_EXECUTOR_PERMIT_SECRET", "").strip()
        if not secret:
            raise ValueError("BRAIN_EXTERNAL_EXECUTOR_PERMIT_SECRET missing")
        message = json.dumps(permit_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return {**permit_payload, "signature": signature}

    @staticmethod
    def _sanitize_domain_fragment(value: str) -> str:
        sanitized = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        return sanitized.strip("_") or "unknown"

    def _resolve_supervisor_domain_key(
        self,
        *,
        task: Any | None,
        skill_run: Any | None,
        request: PaperclipActionRequestItem,
    ) -> str:
        task_payload = getattr(task, "payload", {}) or {}
        target_type = str(request.target_type or task_payload.get("target_type") or "execution")
        fragments = ["external_apps", self.config.app_slug, self._sanitize_domain_fragment(target_type)]

        if target_type == "execution":
            nested_target_type = task_payload.get("target_type")
            if isinstance(nested_target_type, str) and nested_target_type in {"company", "project", "issue", "agent"}:
                fragments = ["external_apps", self.config.app_slug, self._sanitize_domain_fragment(nested_target_type)]
            skill_key = getattr(skill_run, "skill_key", None) or task_payload.get("skill_key")
            intent = task_payload.get("intent")
            task_type = getattr(task, "task_type", None)
            if skill_key:
                fragments.append(self._sanitize_domain_fragment(str(skill_key)))
            elif intent:
                fragments.append(self._sanitize_domain_fragment(str(intent)))
            elif task_type:
                fragments.append(self._sanitize_domain_fragment(str(task_type)))

        domain_key = ".".join(fragment for fragment in fragments if fragment)
        return domain_key[:100]

    async def list_action_requests(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
    ) -> PaperclipActionRequestListResponse:
        result = await db.execute(
            select(ControlPlaneEventModel)
            .where(ControlPlaneEventModel.entity_type == "external_action_request")
            .order_by(ControlPlaneEventModel.created_at.desc())
            .limit(1000)
        )
        events = list(result.scalars().all())

        by_request_id: dict[str, PaperclipActionRequestItem] = {}
        for event in sorted(events, key=lambda item: item.created_at or datetime.now(timezone.utc)):
            if f".{self.config.app_slug}." not in event.event_type:
                continue
            payload = event.payload if isinstance(event.payload, dict) else {}
            request_id = str(payload.get("request_id") or event.entity_id)
            tenant_id = payload.get("tenant_id")
            if not self._action_request_visible(tenant_id, principal):
                continue

            created_at = (event.created_at or datetime.now(timezone.utc)).isoformat()
            existing = by_request_id.get(request_id)
            if existing is None:
                existing = PaperclipActionRequestItem(
                    request_id=request_id,
                    app_slug=self.config.app_slug,
                    tenant_id=tenant_id,
                    principal_id=str(payload.get("principal_id") or event.actor_id or "unknown"),
                    action=str(payload.get("action") or "request_escalation"),
                    reason=str(payload.get("reason") or ""),
                    status="pending",
                    target_type=str(payload.get("target_type") or "execution"),
                    target_ref=str(payload.get("target_ref") or ""),
                    skill_run_id=str(payload.get("skill_run_id")) if payload.get("skill_run_id") else None,
                    mission_id=str(payload.get("mission_id")) if payload.get("mission_id") else None,
                    decision_id=str(payload.get("decision_id")) if payload.get("decision_id") else None,
                    correlation_id=str(payload.get("correlation_id")) if payload.get("correlation_id") else None,
                    created_at=created_at,
                    updated_at=created_at,
                )
                by_request_id[request_id] = existing

            existing.updated_at = created_at
            if event.event_type.endswith("requested.v1"):
                existing.status = "pending"
            elif event.event_type.endswith("approved.v1"):
                existing.status = "approved"
                existing.approved_by = str(payload.get("approved_by") or event.actor_id or "unknown")
                existing.approved_at = created_at
                existing.decision_reason = str(payload.get("decision_reason") or "")
                existing.execution_result = self._serialize_action_execution_result(payload.get("execution_result") or {})
            elif event.event_type.endswith("rejected.v1"):
                existing.status = "rejected"
                existing.rejected_by = str(payload.get("rejected_by") or event.actor_id or "unknown")
                existing.rejected_at = created_at
                existing.decision_reason = str(payload.get("decision_reason") or "")

        items = sorted(by_request_id.values(), key=lambda item: item.updated_at, reverse=True)
        return PaperclipActionRequestListResponse(items=items, total=len(items))

    async def _get_action_request_or_raise(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
        request_id: str,
    ) -> PaperclipActionRequestItem:
        requests = await self.list_action_requests(db, principal=principal)
        for item in requests.items:
            if item.request_id == request_id:
                return item
        raise ValueError(f"Action request {request_id} not found")

    async def _retry_execution_request(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
        request: PaperclipActionRequestItem,
    ) -> dict[str, str]:
        if not request.skill_run_id:
            raise ValueError("Retry request requires linked SkillRun")

        task, previous_run = await self._load_execution_entities(
            db,
            task_id=request.target_ref,
            principal_tenant_id=principal.tenant_id,
            cross_tenant=self._principal_has_cross_tenant_read(principal),
        )
        if previous_run is None:
            raise ValueError("Retry request requires linked SkillRun")

        new_run = await get_skill_engine_service().create_run(
            db,
            SkillRunCreate(
                skill_key=previous_run.skill_key,
                version=previous_run.skill_version,
                input_payload=getattr(previous_run, "input_payload", {}) or {},
                idempotency_key=f"external-retry-{request.request_id}-{uuid.uuid4().hex[:8]}",
                trigger_type=TriggerType.RETRY,
                mission_id=previous_run.mission_id,
                deadline_at=previous_run.deadline_at,
                causation_id=previous_run.correlation_id,
                governance_snapshot={
                    **((getattr(previous_run, "policy_snapshot", {}) or {}).get("upstream_decision", {}).get("governance_snapshot", {}) or {}),
                    "source": f"{self.config.app_slug}_action_request_retry",
                    "retry_request_id": request.request_id,
                    "retry_of_skill_run_id": str(previous_run.id),
                    "retry_of_task_id": request.target_ref,
                },
            ),
            principal,
        )

        original_payload = getattr(task, "payload", {}) or {}
        executor_type = str(original_payload.get("executor_type") or original_payload.get("worker_type") or self.config.executor_name)
        new_task_id = f"task-{uuid.uuid4().hex[:12]}"
        payload = {
            **original_payload,
            "skill_run_id": str(new_run.id),
            "skill_key": new_run.skill_key,
            "skill_version": new_run.skill_version,
            "correlation_id": new_run.correlation_id,
            "mission_id": new_run.mission_id,
            "retry_of_task_id": request.target_ref,
            "retry_request_id": request.request_id,
            "execution_permit": self._build_execution_permit(
                executor_type=executor_type,
                skill_run_id=str(new_run.id),
                task_id=new_task_id,
                correlation_id=new_run.correlation_id,
            ),
        }
        payload["request_id"] = f"retry-{request.request_id}"

        config = {**(getattr(task, "config", {}) or {}), "retry_requested_via": f"{self.config.app_slug}_action_request"}
        task_tags = list(dict.fromkeys([*list(getattr(task, "tags", []) or []), "retry"]))
        priority_value = int(getattr(task, "priority", TaskPriority.HIGH.value) or TaskPriority.HIGH.value)
        priority = TaskPriority(priority_value) if priority_value in {item.value for item in TaskPriority} else TaskPriority.HIGH

        new_task = await get_task_queue_service().create_task(
            db=db,
            task_data=TaskCreate(
                task_id=new_task_id,
                name=f"Retry {getattr(task, 'name', f'{self.config.display_name} TaskLease')}",
                description=getattr(task, "description", None),
                task_type=getattr(task, "task_type", f"{self.config.executor_name}_work"),
                category=getattr(task, "category", None),
                tags=task_tags,
                priority=priority,
                payload=payload,
                config=config,
                tenant_id=new_run.tenant_id,
                mission_id=new_run.mission_id,
                skill_run_id=new_run.id,
                correlation_id=new_run.correlation_id,
                deadline_at=new_run.deadline_at,
                max_retries=getattr(task, "max_retries", 3),
                retry_delay_seconds=getattr(task, "retry_delay_seconds", 60),
            ),
            created_by=principal.principal_id,
            created_by_type=principal.principal_type.value,
        )
        return {
            "new_skill_run_id": str(new_run.id),
            "new_task_id": str(new_task.task_id),
            "retry_of_task_id": request.target_ref,
        }

    async def _escalate_request(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
        request: PaperclipActionRequestItem,
    ) -> dict[str, str]:
        task = None
        skill_run = None
        context_payload: dict[str, Any] = {}
        if request.target_type == "execution":
            task, skill_run = await self._load_execution_entities(
                db,
                task_id=request.target_ref,
                principal_tenant_id=principal.tenant_id,
                cross_tenant=self._principal_has_cross_tenant_read(principal),
            )
            context_payload = {
                "task_id": getattr(task, "task_id", request.target_ref),
                "task_payload": getattr(task, "payload", {}) or {},
                "task_config": getattr(task, "config", {}) or {},
            }

        escalation = await create_domain_escalation_handoff(
            DomainEscalationRequest(
                domain_key=self._resolve_supervisor_domain_key(task=task, skill_run=skill_run, request=request),
                requested_by=request.principal_id,
                requested_by_type="handoff_token",
                tenant_id=request.tenant_id,
                reason=request.reason,
                reasons=[
                    f"{self.config.display_name} requested supervisor escalation for {request.target_type} {request.target_ref}",
                    f"Governed action request {request.request_id} was approved in ControlDeck",
                ],
                recommended_next_actions=[
                    "Review linked execution and governance context",
                    "Decide whether supervisory intervention or deeper domain review is required",
                ],
                risk_tier=getattr(skill_run, "risk_tier", None) or "high",
                correlation_id=request.correlation_id,
                context={
                    "source": f"{self.config.app_slug}_action_request",
                    "action_request_id": request.request_id,
                    "target_type": request.target_type,
                    "target_ref": request.target_ref,
                    "skill_run_id": request.skill_run_id,
                    "decision_id": request.decision_id,
                    "mission_id": request.mission_id,
                    **context_payload,
                },
            ),
            db=db,
        )
        return {
            "supervisor_escalation_id": escalation.escalation_id,
            "supervisor_status": escalation.status,
        }

    async def _escalate_execution_request(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
        request: PaperclipActionRequestItem,
    ) -> dict[str, str]:
        return await self._escalate_request(db, principal=principal, request=request)

    async def approve_action_request(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
        request_id: str,
        payload: PaperclipActionRequestDecision,
    ) -> PaperclipActionRequestItem:
        request = await self._get_action_request_or_raise(db, principal=principal, request_id=request_id)
        if request.status != "pending":
            raise ValueError("Action request is not pending")

        execution_result: dict[str, str] = {}
        if request.action == "request_approval":
            if not request.skill_run_id:
                raise ValueError("Approval request requires linked SkillRun")
            run = await get_skill_engine_service().approve_run(db, uuid.UUID(str(request.skill_run_id)), principal)
            if run is None:
                raise ValueError(f"Skill run {request.skill_run_id} not found")
            execution_result = {"approved_skill_run_id": str(run.id)}
        elif request.action == "request_retry":
            execution_result = await self._retry_execution_request(db, principal=principal, request=request)
        elif request.action == "request_escalation":
            if request.target_type == "execution":
                execution_result = await self._escalate_execution_request(db, principal=principal, request=request)
            else:
                execution_result = await self._escalate_request(db, principal=principal, request=request)

        await record_control_plane_event(
            db=db,
            tenant_id=request.tenant_id,
            entity_type="external_action_request",
            entity_id=request.request_id,
            event_type=self._action_request_event_type("approved"),
            correlation_id=request.correlation_id,
            mission_id=request.mission_id,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "request_id": request.request_id,
                "app_slug": self.config.app_slug,
                "action": request.action,
                "target_type": request.target_type,
                "target_ref": request.target_ref,
                "skill_run_id": request.skill_run_id,
                "tenant_id": request.tenant_id,
                "approved_by": principal.principal_id,
                "decision_reason": payload.reason,
                "execution_result": execution_result,
                "correlation_id": request.correlation_id,
                "mission_id": request.mission_id,
                "decision_id": request.decision_id,
            },
            audit_required=True,
            audit_action="external_action_request_approve",
            audit_message=f"{self.config.display_name} action request approved: {request.action}",
        )
        await db.commit()
        return await self._get_action_request_or_raise(db, principal=principal, request_id=request_id)

    async def reject_action_request(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
        request_id: str,
        payload: PaperclipActionRequestDecision,
    ) -> PaperclipActionRequestItem:
        request = await self._get_action_request_or_raise(db, principal=principal, request_id=request_id)
        if request.status != "pending":
            raise ValueError("Action request is not pending")

        await record_control_plane_event(
            db=db,
            tenant_id=request.tenant_id,
            entity_type="external_action_request",
            entity_id=request.request_id,
            event_type=self._action_request_event_type("rejected"),
            correlation_id=request.correlation_id,
            mission_id=request.mission_id,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "request_id": request.request_id,
                "app_slug": self.config.app_slug,
                "action": request.action,
                "target_type": request.target_type,
                "target_ref": request.target_ref,
                "skill_run_id": request.skill_run_id,
                "tenant_id": request.tenant_id,
                "rejected_by": principal.principal_id,
                "decision_reason": payload.reason,
                "correlation_id": request.correlation_id,
                "mission_id": request.mission_id,
                "decision_id": request.decision_id,
            },
            audit_required=True,
            audit_action="external_action_request_reject",
            audit_message=f"{self.config.display_name} action request rejected: {request.action}",
            severity="warning",
        )
        await db.commit()
        return await self._get_action_request_or_raise(db, principal=principal, request_id=request_id)

    async def _load_execution_entities(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        principal_tenant_id: str | None,
        cross_tenant: bool,
    ) -> tuple[Any, Any | None]:
        task = await get_task_queue_service().get_task(db, task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        if not self._tenant_visible(task.tenant_id, principal_tenant_id, cross_tenant=cross_tenant):
            raise ValueError(f"Task {task_id} not found")

        skill_run = None
        if task.skill_run_id:
            skill_run = await get_skill_engine_service().get_run(db, task.skill_run_id, task.tenant_id if not cross_tenant else None)
        return task, skill_run

    @staticmethod
    def _tenant_visible(entity_tenant_id: str | None, principal_tenant_id: str | None, *, cross_tenant: bool = False) -> bool:
        if cross_tenant:
            return True
        if principal_tenant_id is None:
            return entity_tenant_id is None
        return entity_tenant_id in {principal_tenant_id, None}

    @staticmethod
    def _principal_has_cross_tenant_read(principal: Principal) -> bool:
        roles = {str(role).strip().lower() for role in (principal.roles or [])}
        return bool(roles.intersection({"admin", "service"}))

    async def _opened_exchange_count(self, db: AsyncSession, *, jti: str) -> int:
        if not jti:
            return 0
        result = await db.execute(
            select(ControlPlaneEventModel).where(
                ControlPlaneEventModel.entity_type == "external_handoff",
                ControlPlaneEventModel.entity_id == jti,
                ControlPlaneEventModel.event_type == self._handoff_event_type("opened"),
            )
        )
        return len(list(result.scalars().all()))

    async def record_exchange_failure(
        self,
        db: AsyncSession,
        *,
        payload: PaperclipHandoffExchangeRequest,
        reason: str,
    ) -> None:
        claims: dict[str, Any] = {}
        try:
            claims = jwt.get_unverified_claims(payload.token)
        except Exception:
            claims = {}

        jti = str(claims.get("jti") or f"handoff_failed_{uuid.uuid4().hex[:12]}")
        correlation_id = claims.get("correlation_id")
        mission_id = claims.get("mission_id")
        target_type = str(claims.get("target_type") or "unknown")
        target_ref = str(claims.get("target_ref") or "unknown")
        principal_id = str(claims.get("sub") or "unknown")

        await record_control_plane_event(
            db=db,
            tenant_id=claims.get("tenant_id"),
            entity_type="external_handoff",
            entity_id=jti,
            event_type=self._handoff_event_type("exchange_failed"),
            correlation_id=correlation_id,
            mission_id=mission_id,
            actor_id=principal_id,
            actor_type="handoff_token",
            payload={
                "jti": jti,
                "principal_id": principal_id,
                "tenant_id": claims.get("tenant_id"),
                "target_type": target_type,
                "target_ref": target_ref,
                "skill_run_id": claims.get("skill_run_id"),
                "mission_id": mission_id,
                "decision_id": claims.get("decision_id"),
                "correlation_id": correlation_id,
                "reason": reason,
            },
            audit_required=True,
            audit_action="external_handoff_exchange_failed",
            audit_message=f"{self.config.display_name} handoff exchange failed",
            severity="warning",
        )
        await db.commit()

    async def get_execution_context(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        principal: Principal,
    ) -> PaperclipExecutionContextResponse:
        cross_tenant = self._principal_has_cross_tenant_read(principal)
        task, skill_run = await self._load_execution_entities(
            db,
            task_id=task_id,
            principal_tenant_id=principal.tenant_id,
            cross_tenant=cross_tenant,
        )

        return PaperclipExecutionContextResponse(
            app_slug=self.config.app_slug,
            target_ref=task.task_id,
            task=TaskResponse.model_validate(task),
            skill_run=SkillRunResponse.model_validate(skill_run) if skill_run is not None else None,
            governance_banner=f"Governed by BRAiN. Sensitive actions in {self.config.display_name} require BRAiN approval.",
            available_actions=self._available_actions(task, skill_run),
        )

    async def create_handoff(
        self,
        db: AsyncSession,
        *,
        principal: Principal,
        payload: PaperclipHandoffRequest,
        backend_base_url: str,
    ) -> PaperclipHandoffResponse:
        runtime_context = RuntimeDecisionContext(
            tenant_id=principal.tenant_id,
            environment=os.getenv("BRAIN_RUNTIME_MODE", "local"),
            mission_type=self.config.runtime_mission_type,
            skill_type=self.config.runtime_skill_type,
            agent_role=(principal.roles[0] if principal.roles else "viewer"),
            risk_score=self.config.handoff_risk_score,
            budget_state={},
            system_health={},
            feature_context={
                "app_slug": self.config.app_slug,
                "target_type": payload.target_type,
                "target_ref": payload.target_ref,
                "permissions": payload.permissions,
            },
        )

        runtime_service = get_runtime_control_service()
        runtime_decision = await runtime_service.resolve_with_persisted_overrides(runtime_context, db=db)
        if not runtime_service.is_executor_allowed(runtime_decision.effective_config, self.config.executor_name):
            raise PermissionError(f"{self.config.display_name} executor is currently disabled by runtime policy")
        if not runtime_service.is_connector_allowed(runtime_decision.effective_config, self.config.connector_name):
            raise PermissionError(f"{self.config.display_name} connector is currently disabled by runtime policy")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._handoff_ttl_seconds())
        jti = f"handoff_{uuid.uuid4().hex[:16]}"
        correlation_id = payload.correlation_id or payload.skill_run_id or jti
        claims: dict[str, Any] = {
            "iss": "brain-backend",
            "aud": self.config.audience,
            "sub": principal.principal_id,
            "tenant_id": principal.tenant_id,
            "skill_run_id": payload.skill_run_id,
            "mission_id": payload.mission_id,
            "decision_id": payload.decision_id or runtime_decision.decision_id,
            "correlation_id": correlation_id,
            "target_type": payload.target_type,
            "target_ref": payload.target_ref,
            "permissions": payload.permissions,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": jti,
        }
        token = jwt.encode(claims, self._handoff_secret(), algorithm="HS256")
        exchange_url = f"{backend_base_url.rstrip('/')}/api/external-apps/{self.config.app_slug}/handoff/exchange"
        handoff_url = f"{self._paperclip_app_base_url()}{self._paperclip_handoff_path()}?{urlencode({'token': token, 'exchange_url': exchange_url})}"

        await record_control_plane_event(
            db=db,
            tenant_id=principal.tenant_id,
            entity_type="external_handoff",
            entity_id=jti,
            event_type=self._handoff_event_type("created"),
            correlation_id=correlation_id,
            mission_id=payload.mission_id,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "jti": jti,
                "tenant_id": principal.tenant_id,
                "principal_id": principal.principal_id,
                "target_type": payload.target_type,
                "target_ref": payload.target_ref,
                "app_slug": self.config.app_slug,
                "skill_run_id": payload.skill_run_id,
                "mission_id": payload.mission_id,
                "decision_id": claims["decision_id"],
                "correlation_id": correlation_id,
                "permissions": payload.permissions,
                "expires_at": expires_at.isoformat(),
            },
            audit_required=True,
            audit_action="external_handoff_create",
            audit_message=f"{self.config.display_name} handoff token created",
        )
        await db.commit()

        return PaperclipHandoffResponse(
            app_slug=self.config.app_slug,
            handoff_url=handoff_url,
            expires_at=expires_at.isoformat(),
            jti=jti,
            target_type=payload.target_type,
            target_ref=payload.target_ref,
        )

    async def exchange_handoff(
        self,
        db: AsyncSession,
        *,
        payload: PaperclipHandoffExchangeRequest,
    ) -> PaperclipHandoffExchangeResponse:
        claims = self._decode_handoff_token(payload.token)
        target_type = str(claims.get("target_type") or "execution")
        target_ref = str(claims.get("target_ref") or "")
        correlation_id = claims.get("correlation_id")
        mission_id = claims.get("mission_id")
        skill_run_id = claims.get("skill_run_id")
        decision_id = claims.get("decision_id")
        jti = str(claims.get("jti") or "")
        expires_at_ts = claims.get("exp")
        expires_at = datetime.fromtimestamp(int(expires_at_ts), tz=timezone.utc).isoformat() if expires_at_ts else None
        permissions = claims.get("permissions") or ["view"]
        if not target_ref:
            raise ValueError("handoff target_ref missing")

        opened_count = await self._opened_exchange_count(db, jti=jti)
        max_uses = self._handoff_max_uses()
        if opened_count >= max_uses:
            raise PermissionError("Handoff token already consumed")

        await record_control_plane_event(
            db=db,
            tenant_id=claims.get("tenant_id"),
            entity_type="external_handoff",
            entity_id=jti,
            event_type=self._handoff_event_type("opened"),
            correlation_id=correlation_id,
            mission_id=mission_id,
            actor_id=str(claims.get("sub") or "unknown"),
            actor_type="handoff_token",
            payload={
                "jti": jti,
                "principal_id": claims.get("sub"),
                "tenant_id": claims.get("tenant_id"),
                "app_slug": self.config.app_slug,
                "target_type": target_type,
                "target_ref": target_ref,
                "skill_run_id": skill_run_id,
                "mission_id": mission_id,
                "decision_id": decision_id,
                "correlation_id": correlation_id,
                "permissions": permissions,
                "exchange_use_count": opened_count + 1,
                "max_uses": max_uses,
            },
            audit_required=True,
            audit_action="external_handoff_open",
            audit_message=f"{self.config.display_name} handoff opened",
        )
        await db.commit()

        return PaperclipHandoffExchangeResponse(
            app_slug=self.config.app_slug,
            jti=jti,
            principal_id=str(claims.get("sub") or "unknown"),
            tenant_id=claims.get("tenant_id"),
            skill_run_id=skill_run_id,
            mission_id=mission_id,
            decision_id=decision_id,
            correlation_id=correlation_id,
            target_type=target_type,  # type: ignore[arg-type]
            target_ref=target_ref,
            permissions=list(permissions),
            suggested_path=self._suggested_path(target_type, target_ref),
            governance_banner=f"Governed by BRAiN. Sensitive actions in {self.config.display_name} require BRAiN approval.",
            expires_at=expires_at or datetime.now(timezone.utc).isoformat(),
        )

    async def request_action(
        self,
        db: AsyncSession,
        *,
        payload: PaperclipActionRequest,
    ) -> PaperclipActionRequestResponse:
        claims = self._decode_handoff_token(payload.token)
        target_type = str(claims.get("target_type") or "execution")

        permissions = list(claims.get("permissions") or ["view"])
        if payload.action not in permissions:
            raise PermissionError(f"Handoff token does not permit {payload.action}")
        if await self._opened_exchange_count(db, jti=str(claims.get("jti") or "")) == 0:
            raise PermissionError("Handoff token has not been activated")

        target_ref = str(claims.get("target_ref") or "")
        if not target_ref:
            raise ValueError("handoff target_ref missing")

        mission_id = claims.get("mission_id")
        skill_run_id = str(claims.get("skill_run_id") or "") or None
        correlation_id = claims.get("correlation_id")
        if target_type == "execution":
            task, skill_run = await self._load_execution_entities(
                db,
                task_id=target_ref,
                principal_tenant_id=claims.get("tenant_id"),
                cross_tenant=False,
            )
            available_actions = self._available_actions(task, skill_run)
            mission_id = getattr(task, "mission_id", None) or mission_id
            skill_run_id = str(getattr(task, "skill_run_id", None) or skill_run_id or "") or None
            correlation_id = getattr(task, "correlation_id", None) or correlation_id
        else:
            available_actions = ["request_escalation"]
        if payload.action not in available_actions:
            raise ValueError(f"Action {payload.action} is not available for current execution state")

        request_id = f"actreq_{uuid.uuid4().hex[:12]}"

        await record_control_plane_event(
            db=db,
            tenant_id=claims.get("tenant_id"),
            entity_type="external_action_request",
            entity_id=request_id,
            event_type=self._action_request_event_type("requested"),
            correlation_id=correlation_id,
            mission_id=mission_id,
            actor_id=str(claims.get("sub") or "unknown"),
            actor_type="handoff_token",
            payload={
                "request_id": request_id,
                "app_slug": self.config.app_slug,
                "action": payload.action,
                "reason": payload.reason,
                "target_type": target_type,
                "target_ref": target_ref,
                "skill_run_id": skill_run_id,
                "tenant_id": claims.get("tenant_id"),
                "principal_id": claims.get("sub"),
                "mission_id": mission_id,
                "decision_id": claims.get("decision_id"),
                "correlation_id": correlation_id,
            },
            audit_required=True,
            audit_action="external_action_request",
            audit_message=f"{self.config.display_name} requested {payload.action}",
            severity="warning" if payload.action != "request_retry" else "info",
        )
        await db.commit()

        message_by_action = {
            "request_approval": "Approval request recorded for the linked SkillRun.",
            "request_retry": "Retry request recorded for operator review.",
            "request_escalation": "Escalation request recorded for operator review.",
        }
        return PaperclipActionRequestResponse(
            request_id=request_id,
            app_slug=self.config.app_slug,
            action=payload.action,
            target_type=target_type,  # type: ignore[arg-type]
            target_ref=target_ref,
            skill_run_id=skill_run_id,
            message=message_by_action[payload.action],
        )


_services: dict[str, PaperclipHandoffService] = {}


def get_paperclip_handoff_service() -> PaperclipHandoffService:
    service = _services.get(PAPERCLIP_CONFIG.app_slug)
    if service is None:
        service = PaperclipHandoffService(PAPERCLIP_CONFIG)
        _services[PAPERCLIP_CONFIG.app_slug] = service
    return service


def get_openclaw_handoff_service() -> PaperclipHandoffService:
    service = _services.get(OPENCLAW_CONFIG.app_slug)
    if service is None:
        service = PaperclipHandoffService(OPENCLAW_CONFIG)
        _services[OPENCLAW_CONFIG.app_slug] = service
    return service
