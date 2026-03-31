"""Service for AXE session-scoped worker run orchestration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.core.control_plane_events import record_control_plane_event
from app.modules.axe_miniworker.service import AXEMiniworkerService
from app.modules.axe_sessions.models import AXEChatMessageORM, AXEChatSessionORM
from app.modules.domain_agents.service import get_domain_agent_service
from app.modules.opencode_repair.schemas import (
    OpenCodeJobConstraints,
    OpenCodeJobContext,
    OpenCodeJobContractCreateRequest,
    OpenCodeJobMode,
    OpenCodeJobScope,
)
from app.modules.opencode_repair.service import get_opencode_repair_service

from .models import AXEWorkerRunORM
from .schemas import AXEWorkerArtifact, AXEWorkerRunCreateRequest, AXEWorkerRunResponse, WorkerType

logger = logging.getLogger(__name__)

OPENCODE_TO_AXE_STATUS = {
    "requested": "queued",
    "queued": "queued",
    "assigned": "running",
    "in_progress": "running",
    "verifying": "running",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "failed",
}


class WorkerAdapter(Protocol):
    async def dispatch(
        self,
        *,
        db: AsyncSession,
        principal: Principal,
        payload: AXEWorkerRunCreateRequest,
        worker_run_id: str,
    ) -> AXEWorkerRunResponse:
        ...


class WorkerAdapterRegistry:
    _adapters: dict[WorkerType, WorkerAdapter] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, worker_type: WorkerType, adapter: WorkerAdapter) -> None:
        cls._adapters[worker_type] = adapter
        logger.info("Registered worker adapter: %s", worker_type)

    @classmethod
    def get(cls, worker_type: WorkerType) -> WorkerAdapter | None:
        return cls._adapters.get(worker_type)

    @classmethod
    def list_supported(cls) -> list[WorkerType]:
        return list(cls._adapters.keys())


class OpenCodeWorkerAdapter:
    def __init__(self) -> None:
        self._service = get_opencode_repair_service()

    async def dispatch(
        self,
        *,
        db: AsyncSession,
        principal: Principal,
        payload: AXEWorkerRunCreateRequest,
        worker_run_id: str,
    ) -> AXEWorkerRunResponse:
        _ = db
        scope = OpenCodeJobScope(
            module=payload.module or "workspace",
            entity_id=payload.entity_id or str(payload.message_id),
            tenant_id=principal.tenant_id or "default",
        )
        contract = OpenCodeJobContractCreateRequest(
            correlation_id=f"axe-{worker_run_id}",
            mode=OpenCodeJobMode(payload.mode),
            scope=scope,
            constraints=OpenCodeJobConstraints(),
            context=OpenCodeJobContext(
                trigger_event="axe.worker.run.requested",
                original_request={
                    "source": "axe",
                    "session_id": str(payload.session_id),
                    "message_id": str(payload.message_id),
                    "prompt": payload.prompt,
                    "requested_by": principal.principal_id,
                },
            ),
            created_by=principal.principal_id,
        )
        job = await self._service.dispatch_job_contract(contract)
        return AXEWorkerRunResponse(
            worker_run_id=worker_run_id,
            session_id=payload.session_id,
            message_id=payload.message_id,
            worker_type="opencode",
            status="queued",
            label="OpenCode worker queued",
            detail=f"Job dispatched: {job.job_id}",
            updated_at=datetime.utcnow(),
            artifacts=[],
        )


class MiniworkerAdapter:
    def __init__(self) -> None:
        self._service = AXEMiniworkerService()

    async def dispatch(
        self,
        *,
        db: AsyncSession,
        principal: Principal,
        payload: AXEWorkerRunCreateRequest,
        worker_run_id: str,
    ) -> AXEWorkerRunResponse:
        result = await self._service.dispatch(
            db=db,
            principal=principal,
            payload=payload,
            worker_run_id=worker_run_id,
        )
        return AXEWorkerRunResponse(**result)


def _init_adapter_registry() -> None:
    if not WorkerAdapterRegistry._initialized:
        WorkerAdapterRegistry.register("opencode", OpenCodeWorkerAdapter())
        WorkerAdapterRegistry.register("miniworker", MiniworkerAdapter())
        WorkerAdapterRegistry._initialized = True
        logger.info("Worker adapter registry initialized")


class AXEWorkerRunService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.opencode = get_opencode_repair_service()

    async def create_worker_run(
        self,
        *,
        principal: Principal,
        payload: AXEWorkerRunCreateRequest,
    ) -> AXEWorkerRunResponse:
        if str(payload.worker_type) == "openclaw":
            raise ValueError(
                "openclaw worker runs must use SkillRun/TaskLease runtime path; "
                "direct axe_worker_runs dispatch is disabled"
            )

        _init_adapter_registry()

        session = await self._get_owned_session(
            principal=principal,
            session_id=payload.session_id,
        )
        if session is None:
            raise PermissionError("Session not found")

        message = await self._get_owned_message(
            principal=principal,
            session_id=payload.session_id,
            message_id=payload.message_id,
        )
        if message is None:
            raise LookupError("Message not found")

        routing_decision = await self._resolve_routing_decision(
            principal=principal,
            payload=payload,
        )
        effective_worker_type = routing_decision.selected_worker if routing_decision is not None else payload.worker_type

        worker_run_id = f"wr_{uuid4().hex[:16]}"
        routing_artifacts = []
        if routing_decision is not None:
            routing_artifacts.append(
                {
                    "type": "routing_decision",
                    "label": "BRAiN routing decision",
                    "url": f"inline://routing/{routing_decision.id}",
                    "metadata": {
                        "routing_decision_id": routing_decision.id,
                        "selected_worker": routing_decision.selected_worker,
                        "strategy": routing_decision.strategy,
                    },
                }
            )

        approval_gate_response = await self._handle_bounded_apply_gate(
            principal=principal,
            payload=payload,
            worker_run_id=worker_run_id,
            effective_worker_type=effective_worker_type,
            routing_artifacts=routing_artifacts,
        )
        if approval_gate_response is not None:
            return approval_gate_response

        row = AXEWorkerRunORM(
            worker_run_id=worker_run_id,
            session_id=payload.session_id,
            message_id=payload.message_id,
            principal_id=principal.principal_id,
            tenant_id=principal.tenant_id,
            backend_run_type=f"{effective_worker_type}_job",
            status="queued",
            label=f"{effective_worker_type.title()} worker queued",
            detail="Job accepted by BRAiN orchestrator",
            artifacts_json=routing_artifacts,
        )
        self.db.add(row)

        adapter = WorkerAdapterRegistry.get(effective_worker_type)
        if adapter is None:
            raise ValueError(f"Unsupported worker type: {effective_worker_type}")

        if effective_worker_type != payload.worker_type:
            payload = payload.model_copy(update={"worker_type": effective_worker_type})

        worker_response = await adapter.dispatch(
            db=self.db,
            principal=principal,
            payload=payload,
            worker_run_id=worker_run_id,
        )
        row.backend_run_id = worker_response.detail.split(": ")[-1] if ": " in worker_response.detail else worker_response.worker_run_id
        row.status = worker_response.status
        row.label = worker_response.label
        row.detail = worker_response.detail
        row.backend_run_type = f"{worker_response.worker_type}_job"
        row.artifacts_json = [
            *(row.artifacts_json or []),
            *[artifact.model_dump(mode="json") for artifact in worker_response.artifacts],
        ]

        await self.db.commit()
        await self.db.refresh(row)
        return self._to_response(row)

    async def get_worker_run(
        self,
        *,
        principal: Principal,
        worker_run_id: str,
    ) -> AXEWorkerRunResponse | None:
        row = await self._get_owned_worker_run(principal=principal, worker_run_id=worker_run_id)
        if row is None:
            return None

        await self._sync_backend_status(row)
        return self._to_response(row)

    async def approve_worker_run(
        self,
        *,
        principal: Principal,
        worker_run_id: str,
        approval_reason: str,
    ) -> AXEWorkerRunResponse:
        row = await self._get_owned_worker_run(principal=principal, worker_run_id=worker_run_id)
        if row is None:
            raise PermissionError("Worker run not found")
        if row.status != "waiting_input":
            raise ValueError("Worker run is not waiting for approval")

        pending_payload = self._extract_pending_payload(row)
        if pending_payload is None:
            raise LookupError("Pending approval payload missing")

        payload = AXEWorkerRunCreateRequest(**pending_payload).model_copy(
            update={"approval_confirmed": True, "approval_reason": approval_reason}
        )
        adapter = WorkerAdapterRegistry.get(payload.worker_type)
        if adapter is None:
            raise ValueError(f"Unsupported worker type: {payload.worker_type}")

        await record_control_plane_event(
            db=self.db,
            tenant_id=principal.tenant_id,
            entity_type="axe_worker_run",
            entity_id=row.worker_run_id,
            event_type="axe.miniworker.bounded_apply.approved.v1",
            correlation_id=row.worker_run_id,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "worker_type": payload.worker_type,
                "execution_mode": payload.execution_mode,
                "file_scope": payload.file_scope,
                "approval_reason": approval_reason,
            },
            audit_required=True,
            audit_action="axe_miniworker_bounded_apply_approve",
            audit_message="AXE miniworker bounded apply approved",
        )

        row.status = "queued"
        row.label = f"{payload.worker_type.title()} worker queued"
        row.detail = "Approval confirmed. Dispatching bounded execution."
        row.artifacts_json = self._without_pending_approval_artifacts(row.artifacts_json or [])

        worker_response = await adapter.dispatch(
            db=self.db,
            principal=principal,
            payload=payload,
            worker_run_id=row.worker_run_id,
        )
        row.backend_run_id = worker_response.detail.split(": ")[-1] if ": " in worker_response.detail else worker_response.worker_run_id
        row.status = worker_response.status
        row.label = worker_response.label
        row.detail = worker_response.detail
        row.backend_run_type = f"{worker_response.worker_type}_job"
        row.artifacts_json = [
            *(row.artifacts_json or []),
            {
                "type": "approval_history",
                "label": "Approval recorded",
                "url": "inline://approval-history",
                "metadata": {
                    "approved": True,
                    "approval_reason": approval_reason,
                    "worker_type": payload.worker_type,
                    "execution_mode": payload.execution_mode,
                },
            },
            *[artifact.model_dump(mode="json") for artifact in worker_response.artifacts],
        ]

        await self.db.commit()
        await self.db.refresh(row)
        return self._to_response(row)

    async def reject_worker_run(
        self,
        *,
        principal: Principal,
        worker_run_id: str,
        rejection_reason: str,
    ) -> AXEWorkerRunResponse:
        row = await self._get_owned_worker_run(principal=principal, worker_run_id=worker_run_id)
        if row is None:
            raise PermissionError("Worker run not found")
        if row.status != "waiting_input":
            raise ValueError("Worker run is not waiting for approval")

        await record_control_plane_event(
            db=self.db,
            tenant_id=principal.tenant_id,
            entity_type="axe_worker_run",
            entity_id=row.worker_run_id,
            event_type="axe.miniworker.bounded_apply.rejected.v1",
            correlation_id=row.worker_run_id,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={"rejection_reason": rejection_reason},
            audit_required=True,
            audit_action="axe_miniworker_bounded_apply_reject",
            audit_message="AXE miniworker bounded apply rejected",
            severity="warning",
        )

        row.status = "failed"
        row.label = "AXE miniworker approval rejected"
        row.detail = rejection_reason
        row.artifacts_json = [
            *self._without_pending_approval_artifacts(row.artifacts_json or []),
            {
                "type": "approval_history",
                "label": "Approval rejected",
                "url": "inline://approval-rejected",
                "metadata": {"rejected": True, "rejection_reason": rejection_reason},
            },
        ]
        await self.db.commit()
        await self.db.refresh(row)
        return self._to_response(row)

    async def list_worker_runs_for_session(
        self,
        *,
        principal: Principal,
        session_id: UUID,
    ) -> list[AXEWorkerRunResponse]:
        session = await self._get_owned_session(principal=principal, session_id=session_id)
        if session is None:
            raise PermissionError("Session not found")

        query = (
            select(AXEWorkerRunORM)
            .where(AXEWorkerRunORM.session_id == session_id)
            .where(AXEWorkerRunORM.principal_id == principal.principal_id)
            .order_by(desc(AXEWorkerRunORM.updated_at))
        )
        if principal.tenant_id is not None:
            query = query.where(AXEWorkerRunORM.tenant_id == principal.tenant_id)

        rows = list((await self.db.execute(query)).scalars().all())
        responses: list[AXEWorkerRunResponse] = []
        for row in rows:
            await self._sync_backend_status(row)
            responses.append(self._to_response(row))
        return responses

    async def update_worker_run(
        self,
        *,
        worker_run_id: str,
        status: str,
        label: str,
        detail: str,
        artifacts: list[dict] | None = None,
    ) -> AXEWorkerRunResponse | None:
        row = (
            await self.db.execute(
                select(AXEWorkerRunORM).where(AXEWorkerRunORM.worker_run_id == worker_run_id)
            )
        ).scalar_one_or_none()
        if row is None:
            return None

        row.status = status
        row.label = label
        row.detail = detail
        row.updated_at = datetime.utcnow()
        if artifacts is not None:
            row.artifacts_json = artifacts
        await self.db.commit()
        await self.db.refresh(row)
        return self._to_response(row)

    async def _sync_backend_status(self, row: AXEWorkerRunORM) -> None:
        if row.backend_run_type != "opencode_job" or not row.backend_run_id:
            return

        backend_job = await self.opencode.get_job_contract(row.backend_run_id)
        if backend_job is None:
            return

        mapped_status = OPENCODE_TO_AXE_STATUS.get(backend_job.status.value, row.status)
        if mapped_status == row.status:
            return

        row.status = mapped_status
        row.label = _status_label(mapped_status)
        row.detail = _status_detail(mapped_status)
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)

    async def _get_owned_session(
        self,
        *,
        principal: Principal,
        session_id: UUID,
    ) -> AXEChatSessionORM | None:
        query = (
            select(AXEChatSessionORM)
            .where(AXEChatSessionORM.id == session_id)
            .where(AXEChatSessionORM.principal_id == principal.principal_id)
        )
        if principal.tenant_id is not None:
            query = query.where(AXEChatSessionORM.tenant_id == principal.tenant_id)
        return (await self.db.execute(query)).scalar_one_or_none()

    async def _get_owned_message(
        self,
        *,
        principal: Principal,
        session_id: UUID,
        message_id: UUID,
    ) -> AXEChatMessageORM | None:
        session = await self._get_owned_session(principal=principal, session_id=session_id)
        if session is None:
            return None
        query = (
            select(AXEChatMessageORM)
            .where(AXEChatMessageORM.id == message_id)
            .where(AXEChatMessageORM.session_id == session_id)
        )
        return (await self.db.execute(query)).scalar_one_or_none()

    async def _get_owned_worker_run(
        self,
        *,
        principal: Principal,
        worker_run_id: str,
    ) -> AXEWorkerRunORM | None:
        query = (
            select(AXEWorkerRunORM)
            .where(AXEWorkerRunORM.worker_run_id == worker_run_id)
            .where(AXEWorkerRunORM.principal_id == principal.principal_id)
        )
        if principal.tenant_id is not None:
            query = query.where(AXEWorkerRunORM.tenant_id == principal.tenant_id)
        return (await self.db.execute(query)).scalar_one_or_none()

    @staticmethod
    def _to_response(row: AXEWorkerRunORM) -> AXEWorkerRunResponse:
        artifacts = []
        for item in row.artifacts_json or []:
            if isinstance(item, dict):
                try:
                    artifacts.append(AXEWorkerArtifact(**item))
                except Exception:
                    continue

        return AXEWorkerRunResponse(
            worker_run_id=row.worker_run_id,
            session_id=row.session_id,
            message_id=row.message_id,
            worker_type=_worker_type_from_backend_run_type(row.backend_run_type),
            status=row.status,
            label=row.label,
            detail=row.detail,
            updated_at=row.updated_at or datetime.utcnow(),
            artifacts=artifacts,
        )

    async def _handle_bounded_apply_gate(
        self,
        *,
        principal: Principal,
        payload: AXEWorkerRunCreateRequest,
        worker_run_id: str,
        effective_worker_type: WorkerType,
        routing_artifacts: list[dict],
    ) -> AXEWorkerRunResponse | None:
        if payload.execution_mode != "bounded_apply" or effective_worker_type != "miniworker":
            return None

        if not payload.approval_confirmed:
            await record_control_plane_event(
                db=self.db,
                tenant_id=principal.tenant_id,
                entity_type="axe_worker_run",
                entity_id=worker_run_id,
                event_type="axe.miniworker.bounded_apply.approval_required.v1",
                correlation_id=worker_run_id,
                mission_id=None,
                actor_id=principal.principal_id,
                actor_type=principal.principal_type.value,
                payload={
                    "worker_type": effective_worker_type,
                    "execution_mode": payload.execution_mode,
                    "file_scope": payload.file_scope,
                },
                audit_required=True,
                audit_action="axe_miniworker_bounded_apply_gate",
                audit_message="AXE miniworker bounded apply requires explicit approval",
                severity="warning",
            )
            row = AXEWorkerRunORM(
                worker_run_id=worker_run_id,
                session_id=payload.session_id,
                message_id=payload.message_id,
                principal_id=principal.principal_id,
                tenant_id=principal.tenant_id,
                backend_run_type=f"{effective_worker_type}_job",
                status="waiting_input",
                label="AXE miniworker waiting for approval",
                detail="bounded_apply requires approval_confirmed=true and an approval_reason before execution.",
                artifacts_json=[
                    *routing_artifacts,
                    {
                        "type": "pending_request",
                        "label": "Pending bounded apply request",
                        "url": "inline://pending-request",
                        "metadata": payload.model_dump(mode="json"),
                    },
                    {
                        "type": "approval",
                        "label": "Approval required",
                        "url": "inline://approval",
                        "metadata": {
                            "approval_required": True,
                            "execution_mode": payload.execution_mode,
                            "worker_type": effective_worker_type,
                        },
                    },
                ],
            )
            self.db.add(row)
            await self.db.commit()
            await self.db.refresh(row)
            return self._to_response(row)

        await record_control_plane_event(
            db=self.db,
            tenant_id=principal.tenant_id,
            entity_type="axe_worker_run",
            entity_id=worker_run_id,
            event_type="axe.miniworker.bounded_apply.approved.v1",
            correlation_id=worker_run_id,
            mission_id=None,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            payload={
                "worker_type": effective_worker_type,
                "execution_mode": payload.execution_mode,
                "file_scope": payload.file_scope,
                "approval_reason": payload.approval_reason,
            },
            audit_required=True,
            audit_action="axe_miniworker_bounded_apply_approve",
            audit_message="AXE miniworker bounded apply approved",
        )
        return None

    @staticmethod
    def _extract_pending_payload(row: AXEWorkerRunORM) -> dict | None:
        for artifact in row.artifacts_json or []:
            if isinstance(artifact, dict) and artifact.get("type") == "pending_request":
                metadata = artifact.get("metadata")
                if isinstance(metadata, dict):
                    return metadata
        return None

    @staticmethod
    def _without_pending_approval_artifacts(artifacts: list[dict]) -> list[dict]:
        filtered: list[dict] = []
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            if artifact.get("type") in {"pending_request", "approval"}:
                continue
            filtered.append(artifact)
        return filtered

    async def _resolve_routing_decision(
        self,
        *,
        principal: Principal,
        payload: AXEWorkerRunCreateRequest,
    ):
        if payload.worker_type != "auto":
            return None

        return await get_domain_agent_service().route_programming_worker(
            self.db,
            principal=principal,
            intent_summary=payload.prompt,
            file_scope=payload.file_scope,
            execution_mode=payload.execution_mode,
            message_id=str(payload.message_id),
            session_id=str(payload.session_id),
            tenant_id=principal.tenant_id,
        )


def _status_label(status: str) -> str:
    labels = {
        "queued": "OpenCode worker queued",
        "running": "OpenCode worker active",
        "waiting_input": "OpenCode worker waiting for input",
        "completed": "OpenCode worker completed",
        "failed": "OpenCode worker failed",
    }
    return labels.get(status, "OpenCode worker update")


def _status_detail(status: str) -> str:
    details = {
        "queued": "Job accepted by BRAiN orchestrator",
        "running": "Worker is processing the repository task",
        "waiting_input": "Worker is waiting for additional input",
        "completed": "Worker finished execution",
        "failed": "Worker execution failed",
    }
    return details.get(status, "Worker status updated")


def _worker_type_from_backend_run_type(backend_run_type: str | None) -> WorkerType:
    if backend_run_type == "miniworker_job":
        return "miniworker"
    if backend_run_type == "opencode_job":
        return "opencode"
    return "auto"
