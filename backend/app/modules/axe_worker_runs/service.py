"""Service for AXE session-scoped worker run orchestration."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.axe_sessions.models import AXEChatMessageORM, AXEChatSessionORM
from app.modules.opencode_repair.schemas import (
    OpenCodeJobConstraints,
    OpenCodeJobContext,
    OpenCodeJobContractCreateRequest,
    OpenCodeJobMode,
    OpenCodeJobScope,
)
from app.modules.opencode_repair.service import get_opencode_repair_service

from .models import AXEWorkerRunORM
from .schemas import AXEWorkerArtifact, AXEWorkerRunCreateRequest, AXEWorkerRunResponse


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

        worker_run_id = f"wr_{uuid4().hex[:16]}"
        row = AXEWorkerRunORM(
            worker_run_id=worker_run_id,
            session_id=payload.session_id,
            message_id=payload.message_id,
            principal_id=principal.principal_id,
            tenant_id=principal.tenant_id,
            backend_run_type="opencode_job",
            status="queued",
            label="OpenCode worker queued",
            detail="Job accepted by BRAiN orchestrator",
            artifacts_json=[],
        )
        self.db.add(row)

        scope = OpenCodeJobScope(
            module=payload.module or "workspace",
            entity_id=payload.entity_id or str(payload.message_id),
            tenant_id=principal.tenant_id or session.tenant_id or "default",
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
        job = await self.opencode.dispatch_job_contract(contract, db=self.db)
        row.backend_run_id = job.job_id
        if row.updated_at is None:
            row.updated_at = datetime.utcnow()

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
            status=row.status,
            label=row.label,
            detail=row.detail,
            updated_at=row.updated_at or datetime.utcnow(),
            artifacts=artifacts,
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
