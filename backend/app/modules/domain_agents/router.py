"""Domain Agent API routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.auth_deps import (
    Principal,
    SystemRole as UserRole,
    require_auth,
    require_role,
)
from .schemas import (
    DomainAgentConfig,
    DomainDecompositionRequest,
    DomainSkillRunPlanRequest,
    DomainSkillRunPlanResponse,
    DomainResolution,
    DomainReviewDecision,
)
from .service import execute_skill_run_drafts, get_domain_agent_registry, get_domain_agent_service


router = APIRouter(
    prefix="/api/domain-agents",
    tags=["domain-agents"],
    dependencies=[Depends(require_auth)],
)


# EventStream integration (optional, non-blocking)
try:
    from mission_control_core.core import EventStream, Event
except ImportError:  # pragma: no cover
    EventStream = None
    Event = None

_event_stream: EventStream | None = None


def set_event_stream(stream: EventStream) -> None:
    global _event_stream
    _event_stream = stream


async def _emit_domain_event_safe(event_type: str, payload: dict) -> None:
    if _event_stream is None or Event is None:
        return
    try:
        event = Event(type=event_type, source="domain_agents", target=None, payload=payload)
        await _event_stream.publish(event)
    except Exception as exc:  # pragma: no cover
        logger.warning("[DomainAgent] event publish failed: %s", exc)


async def _get_db():
    from app.core.database import get_db

    async for session in get_db():
        yield session


async def _write_escalation_audit(*, db: AsyncSession, principal: Principal, resource_id: str, summary: str, reasons: list[str], recommended_next_actions: list[str], correlation_id: str | None) -> None:
    try:
        from app.core.audit_bridge import write_unified_audit

        await write_unified_audit(
            event_type="domain.agent.escalation.requested.v1",
            action="escalate",
            actor=principal.principal_id,
            actor_type=principal.principal_type.value,
            resource_type="domain_agent",
            resource_id=resource_id,
            severity="warning",
            message=summary,
            correlation_id=correlation_id,
            details={
                "domain_key": resource_id,
                "reasons": reasons,
                "recommended_next_actions": recommended_next_actions,
            },
            db=db,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("[DomainAgent] escalation audit skipped: %s", exc)


async def _resolve_domain_config(
    *,
    domain_key: str,
    db: AsyncSession,
    tenant_id: str | None,
) -> DomainAgentConfig | None:
    registry = get_domain_agent_registry()
    try:
        config = await registry.get_db(db, domain_key, tenant_id=tenant_id)
        if config is not None:
            return config
    except Exception as exc:
        logger.warning("[DomainAgent] get_db failed, falling back to in-memory registry: %s", exc)
    return registry.get(domain_key)


async def _get_supervisor_escalation_safe(
    *,
    escalation_id: str,
    db: AsyncSession,
    tenant_id: str | None,
) -> dict | None:
    try:
        from app.modules.supervisor.service import get_domain_escalation_handoff
    except ImportError as exc:  # pragma: no cover
        logger.error("[DomainAgent] supervisor module unavailable for escalation lookup: %s", exc)
        return None

    item = await get_domain_escalation_handoff(
        escalation_id,
        db=db,
        tenant_id=tenant_id,
    )
    if item is None:
        return None
    return item.model_dump(mode="json")


def _build_supervisor_handoff(
    *,
    principal: Principal,
    domain_key: str,
    summary: str,
    reasons: list[str],
    recommended_next_actions: list[str],
    correlation_id: str | None,
) -> dict:
    return {
        "domain_key": domain_key,
        "requested_by": principal.principal_id,
        "requested_by_type": principal.principal_type.value,
        "tenant_id": principal.tenant_id,
        "reason": summary,
        "reasons": reasons,
        "recommended_next_actions": recommended_next_actions,
        "risk_tier": "high",
        "correlation_id": correlation_id,
    }


async def _submit_supervisor_handoff_safe(handoff: dict, db: AsyncSession | None = None) -> dict | None:
    try:
        from app.modules.supervisor.schemas import DomainEscalationRequest
        from app.modules.supervisor.service import create_domain_escalation_handoff
    except ImportError as exc:  # pragma: no cover
        logger.error(
            "[DomainAgent] supervisor module unavailable — escalation handoff could not be submitted: %s. "
            "Audit record has been written but no supervisor record exists. "
            "Manual reconciliation may be required.",
            exc,
        )
        return None

    try:
        response = await create_domain_escalation_handoff(
            DomainEscalationRequest.model_validate(handoff),
            db=db,
        )
        return response.model_dump(mode="json")
    except Exception as exc:  # pragma: no cover
        logger.error(
            "[DomainAgent] supervisor handoff submission failed — audit record exists but no supervisor record: %s",
            exc,
        )
        return None


@router.get("/info")
async def get_domain_agents_info() -> dict:
    """Get module information."""
    return {
        "name": "Domain Agent Layer",
        "version": "0.1.0",
        "description": "Domain-aware orchestration layer for BRAiN",
        "capabilities": [
            "domain-resolution",
            "domain-decomposition",
            "domain-review",
            "specialist-and-skill-selection",
        ],
    }


@router.get("/domains", response_model=List[DomainAgentConfig])
async def list_domains(
    db: AsyncSession = Depends(_get_db),
    principal: Principal = Depends(require_auth),
) -> List[DomainAgentConfig]:
    registry = get_domain_agent_registry()
    try:
        items = await registry.list_db(db, tenant_id=principal.tenant_id)
        merged: dict[str, DomainAgentConfig] = {item.domain_key: item for item in items}
        for fallback in registry.list():
            merged.setdefault(fallback.domain_key, fallback)
        await _emit_domain_event_safe(
            "domain.agent.listed.v1",
            {
                "tenant_id": principal.tenant_id,
                "count": len(merged),
            },
        )
        return list(merged.values())
    except Exception as exc:
        logger.warning("[DomainAgent] list_db failed, falling back to in-memory registry: %s", exc)
        return list(registry.list())


@router.get("/domains/{domain_key}", response_model=DomainAgentConfig)
async def get_domain(
    domain_key: str,
    db: AsyncSession = Depends(_get_db),
    principal: Principal = Depends(require_auth),
) -> DomainAgentConfig:
    config = await _resolve_domain_config(
        domain_key=domain_key,
        db=db,
        tenant_id=principal.tenant_id,
    )
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain '{domain_key}' not found",
        )
    await _emit_domain_event_safe(
        "domain.agent.resolved.v1",
        {"tenant_id": principal.tenant_id, "domain_key": domain_key},
    )
    return config


@router.post("/domains/register", response_model=DomainAgentConfig, status_code=status.HTTP_201_CREATED)
async def register_domain(
    payload: DomainAgentConfig,
    db: AsyncSession = Depends(_get_db),
    principal: Principal = Depends(
        require_role(UserRole.OPERATOR, UserRole.ADMIN, UserRole.SYSTEM_ADMIN)
    ),
) -> DomainAgentConfig:
    """Register or update a domain config."""
    registry = get_domain_agent_registry()
    scoped_payload = payload.model_copy(
        update={
            "tenant_id": principal.tenant_id,
            "owner_scope": "tenant",
        }
    )

    registered = await registry.register_db(db, scoped_payload)
    registry.register(registered)
    await _emit_domain_event_safe(
        "domain.agent.registered.v1",
        {
            "tenant_id": principal.tenant_id,
            "domain_key": registered.domain_key,
            "owner_scope": registered.owner_scope,
        },
    )
    return registered


@router.post("/decompose", response_model=DomainResolution)
async def decompose_domain_task(
    payload: DomainDecompositionRequest,
    db: AsyncSession = Depends(_get_db),
    principal: Principal = Depends(require_auth),
) -> DomainResolution:
    """Resolve and decompose domain work for downstream execution."""
    service = get_domain_agent_service()
    scoped_payload = payload.model_copy(update={"tenant_id": principal.tenant_id})
    config = await _resolve_domain_config(
        domain_key=scoped_payload.domain_key,
        db=db,
        tenant_id=principal.tenant_id,
    )
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain '{scoped_payload.domain_key}' not found",
        )
    try:
        resolution = service.decompose_with_config(scoped_payload, config)
        await _emit_domain_event_safe(
            "domain.agent.decomposed.v1",
            {
                "tenant_id": principal.tenant_id,
                "domain_key": resolution.domain_key,
                "selected_skill_count": len(resolution.selected_skill_keys),
                "requires_supervisor_review": resolution.requires_supervisor_review,
            },
        )
        return resolution
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/review", response_model=DomainReviewDecision)
async def review_domain_resolution(
    payload: DomainResolution,
    db: AsyncSession = Depends(_get_db),
    principal: Principal = Depends(require_auth),
) -> DomainReviewDecision:
    """Perform base domain review on a decomposition outcome."""
    service = get_domain_agent_service()
    decision = service.review_resolution(payload)
    # Audit must complete before event publish (domain_agent_contract.md durability rule)
    if decision.should_escalate:
        await _write_escalation_audit(
            db=db,
            principal=principal,
            resource_id=payload.domain_key,
            summary=decision.summary,
            reasons=decision.reasons,
            recommended_next_actions=decision.recommended_next_actions,
            correlation_id=None,
        )
    await _emit_domain_event_safe(
        "domain.agent.review.completed.v1",
        {
            "tenant_id": principal.tenant_id,
            "domain_key": payload.domain_key,
            "outcome": decision.outcome.value,
            "should_escalate": decision.should_escalate,
        },
    )
    return decision


@router.post("/prepare-skill-runs", response_model=DomainSkillRunPlanResponse)
async def prepare_domain_skill_runs(
    payload: DomainSkillRunPlanRequest,
    db: AsyncSession = Depends(_get_db),
    principal: Principal = Depends(
        require_role(UserRole.OPERATOR, UserRole.ADMIN, UserRole.SYSTEM_ADMIN, UserRole.SERVICE)
    ),
) -> DomainSkillRunPlanResponse:
    """Prepare domain-driven SkillRun requests and optionally create runs."""
    domain_service = get_domain_agent_service()
    scoped_decomposition = payload.decomposition.model_copy(
        update={"tenant_id": principal.tenant_id}
    )
    config = await _resolve_domain_config(
        domain_key=scoped_decomposition.domain_key,
        db=db,
        tenant_id=principal.tenant_id,
    )
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain '{scoped_decomposition.domain_key}' not found",
        )

    resolution = domain_service.decompose_with_config(scoped_decomposition, config)
    review = domain_service.review_resolution(resolution)

    run_drafts = domain_service.build_skill_run_drafts(
        request=scoped_decomposition,
        config=config,
        resolution=resolution,
        trigger_type=payload.trigger_type,
        mission_id=payload.mission_id,
        causation_id=payload.causation_id,
        input_payload=payload.input_payload,
        tenant_id=principal.tenant_id,
    )

    created_run_ids: list[str] = []
    supervisor_handoff: dict | None = None
    approved_supervisor_escalation = False
    if payload.supervisor_escalation_id:
        supervisor_handoff = await _get_supervisor_escalation_safe(
            escalation_id=payload.supervisor_escalation_id,
            db=db,
            tenant_id=principal.tenant_id,
        )
        if supervisor_handoff is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supervisor escalation not found",
            )

        if supervisor_handoff.get("domain_key") != resolution.domain_key:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "supervisor_escalation_id domain does not match current domain resolution"
                ),
            )

        approved_supervisor_escalation = supervisor_handoff.get("status") == "approved"

    if review.should_escalate and not payload.supervisor_escalation_id:
        # Escalation path: write audit first, then submit handoff, then emit event
        await _write_escalation_audit(
            db=db,
            principal=principal,
            resource_id=resolution.domain_key,
            summary=review.summary,
            reasons=review.reasons,
            recommended_next_actions=review.recommended_next_actions,
            correlation_id=payload.causation_id,
        )
        supervisor_handoff = _build_supervisor_handoff(
            principal=principal,
            domain_key=resolution.domain_key,
            summary=review.summary,
            reasons=review.reasons,
            recommended_next_actions=review.recommended_next_actions,
            correlation_id=payload.causation_id,
        )
        persisted = await _submit_supervisor_handoff_safe(supervisor_handoff, db=db)
        if persisted is not None:
            supervisor_handoff["escalation_id"] = persisted.get("escalation_id")
            supervisor_handoff["status"] = persisted.get("status")

    if payload.execute_now:
        if payload.supervisor_escalation_id and not approved_supervisor_escalation:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Execution is gated: supervisor_escalation_id must be in approved state "
                    "before execute_now is allowed"
                ),
            )

        if review.should_escalate and not approved_supervisor_escalation:
            # Escalation is pending — execution is gated until supervisor approves.
            # Callers must re-invoke with supervisor_escalation_id once approved.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Execution is gated: domain review requires supervisor approval before execute_now is allowed",
            )

        # Non-escalated execute_now: delegate to skill engine via service layer.
        # The Domain Agent does not own SkillRun state — it only delegates here.
        try:
            created_run_ids = await execute_skill_run_drafts(db, run_drafts, principal)
        except ImportError as exc:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Skill engine is currently unavailable for execute_now",
            ) from exc

    # Emit events after all audit/DB writes are complete (contract durability rule)
    await _emit_domain_event_safe(
        "domain.agent.decompose.reviewed.v1",
        {
            "tenant_id": principal.tenant_id,
            "domain_key": resolution.domain_key,
            "outcome": review.outcome.value,
            "should_escalate": review.should_escalate,
        },
    )
    await _emit_domain_event_safe(
        "domain.agent.skillruns.prepared.v1",
        {
            "tenant_id": principal.tenant_id,
            "domain_key": resolution.domain_key,
            "draft_count": len(run_drafts),
            "created_count": len(created_run_ids),
            "execute_now": payload.execute_now,
        },
    )

    return DomainSkillRunPlanResponse(
        resolution=resolution,
        review=review,
        run_drafts=run_drafts,
        created_run_ids=created_run_ids,
        supervisor_handoff=supervisor_handoff,
    )
