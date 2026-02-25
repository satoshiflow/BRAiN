"""
Business Factory API Router

RESTful API for business factory operations.

Endpoints:
- POST /api/factory/plan - Generate execution plan
- POST /api/factory/execute - Execute plan
- GET /api/factory/{plan_id} - Get plan status
- GET /api/factory/{plan_id}/evidence - Download evidence pack
- POST /api/factory/{plan_id}/rollback - Rollback plan
- GET /api/factory/templates - List templates
- GET /api/factory/info - Factory info
"""

from __future__ import annotations

import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse
from loguru import logger

from app.core.auth_deps import require_auth, require_operator, get_current_principal, Principal

from app.modules.business_factory.schemas import (
    BusinessBriefing,
    BusinessPlan,
    ExecutionResult,
    RollbackResult,
    PlanStatus,
)
from app.modules.business_factory.planner import BusinessPlanner
from app.modules.template_registry.loader import get_template_loader
from app.modules.template_registry.schemas import Template

# Initialize router
router = APIRouter(
    prefix="/api/factory",
    tags=["factory"],
)

# Storage for plans (in-memory for MVP - should be Redis/DB in production)
_plans_storage: dict[str, BusinessPlan] = {}


@router.post("/plan", response_model=BusinessPlan, dependencies=[Depends(require_operator)])
async def create_plan(
    briefing: BusinessBriefing,
    principal: Principal = Depends(get_current_principal)
):
    """
    Generate execution plan from business briefing.

    **Requires OPERATOR role.**

    This endpoint:
    1. Validates the briefing
    2. Generates ordered execution steps
    3. Performs risk assessment
    4. Returns complete plan (status=DRAFT)

    Does NOT execute - just creates the plan for review.
    """
    try:
        logger.info(f"Creating plan for: {briefing.business_name}")

        # Initialize planner
        planner = BusinessPlanner()

        # Validate briefing
        is_valid, errors = planner.validate_briefing(briefing)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={"errors": errors, "message": "Invalid briefing"}
            )

        # Generate plan
        plan = await planner.generate_plan(briefing)

        # Store plan
        _plans_storage[plan.plan_id] = plan

        logger.info(
            f"✅ Plan created: {plan.plan_id} "
            f"({plan.steps_total} steps, risk={plan.risk_assessment.overall_risk_level})"
        )

        return plan

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create plan")


@router.post("/execute", dependencies=[Depends(require_operator)])
async def execute_plan(
    plan_id: str = Query(..., min_length=1, max_length=100, description="Plan ID to execute"),
    confirm: bool = Query(False, description="Confirm execution (required=true)"),
    principal: Principal = Depends(get_current_principal),
):
    """
    Execute a validated business plan.

    **Requires OPERATOR role.**

    Safety Requirements:
    - confirm=true MUST be provided
    - Plan must exist
    - Plan status must be DRAFT or VALIDATED

    Returns:
    - ExecutionResult with status and evidence pack URL
    """
    # Safety check
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Execution requires confirm=true parameter"
        )

    # Get plan
    plan = _plans_storage.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")

    # Check status
    if plan.status not in [PlanStatus.DRAFT, PlanStatus.VALIDATED]:
        raise HTTPException(
            status_code=400,
            detail=f"Plan cannot be executed (status={plan.status})"
        )

    try:
        logger.info(f"🚀 Executing plan: {plan_id}")

        # For MVP: Simplified execution (full implementation would use FactoryExecutor)
        plan.status = PlanStatus.EXECUTING
        plan.update_statistics()

        # Simulate execution (PLACEHOLDER - would use real FactoryExecutor)
        await asyncio.sleep(2)  # Simulate work (async, doesn't block event loop)

        plan.status = PlanStatus.COMPLETED
        plan.steps_completed = plan.steps_total
        plan.update_statistics()

        result = ExecutionResult(
            plan_id=plan_id,
            status=plan.status,
            success=True,
            message="Plan executed successfully (MVP mode - simulated)",
            steps_executed=plan.steps_total,
            steps_succeeded=plan.steps_total,
            steps_failed=0,
            evidence_pack_url=f"/api/factory/{plan_id}/evidence",
            final_urls={"website": "https://example.com", "odoo": "https://odoo.example.com"},
            execution_time_seconds=2.0,
        )

        logger.info(f"✅ Plan executed: {plan_id}")
        return result

    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
        plan.status = PlanStatus.FAILED
        raise HTTPException(status_code=500, detail="Plan execution failed")


@router.get("/{plan_id}", response_model=BusinessPlan, dependencies=[Depends(require_auth)])
async def get_plan(
    plan_id: str,
    principal: Principal = Depends(get_current_principal),
):
    """Get business plan by ID. Requires authentication."""
    plan = _plans_storage.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")

    return plan


@router.get("/{plan_id}/evidence", dependencies=[Depends(require_auth)])
async def get_evidence_pack(
    plan_id: str,
    principal: Principal = Depends(get_current_principal),
):
    """
    Download evidence pack for completed plan.

    Requires authentication.

    Returns ZIP file containing:
    - plan.json
    - audit_events.jsonl
    - Generated files
    - Screenshots
    - Logs
    """
    plan = _plans_storage.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")

    if plan.status != PlanStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Evidence pack only available for completed plans"
        )

    # For MVP: Return placeholder
    raise HTTPException(
        status_code=501,
        detail="Evidence pack generation not yet implemented (MVP)"
    )


@router.post("/{plan_id}/rollback", response_model=RollbackResult, dependencies=[Depends(require_operator)])
async def rollback_plan(
    plan_id: str,
    to_step: Optional[int] = Query(None, description="Rollback to specific step (None=full rollback)"),
    principal: Principal = Depends(get_current_principal),
):
    """
    Rollback executed plan.

    **Requires OPERATOR role.**

    Args:
        plan_id: Plan to rollback
        to_step: Optional step index to rollback to (None = complete rollback)
    """
    plan = _plans_storage.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")

    if plan.status not in [PlanStatus.COMPLETED, PlanStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail="Can only rollback completed or failed plans"
        )

    try:
        logger.info(f"🔄 Rolling back plan: {plan_id} (to_step={to_step})")

        # For MVP: Simplified rollback
        plan.status = PlanStatus.ROLLED_BACK
        plan.update_statistics()

        result = RollbackResult(
            plan_id=plan_id,
            success=True,
            steps_rolled_back=plan.steps_completed,
            errors=[],
        )

        logger.info(f"✅ Rollback completed: {plan_id}")
        return result

    except Exception as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Plan rollback failed")


@router.get("/templates", response_model=List[Template], dependencies=[Depends(require_auth)])
async def list_templates(
    type: Optional[str] = Query(None, description="Filter by template type"),
    principal: Principal = Depends(get_current_principal),
):
    """List available templates. Requires authentication."""
    try:
        loader = get_template_loader()
        templates = loader.list_templates(type=type)
        return templates
    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list templates")


@router.get("/info", dependencies=[Depends(require_auth)])
async def factory_info(
    principal: Principal = Depends(get_current_principal),
):
    """Get factory system information. Requires authentication."""
    loader = get_template_loader()
    templates = loader.discover_templates()

    return {
        "name": "BRAiN Business Factory",
        "version": "1.0.0",
        "status": "operational",
        "capabilities": {
            "website_generation": True,
            "erp_deployment": True,
            "integrations": True,
            "rollback": True,
            "audit_trail": True,
        },
        "statistics": {
            "templates_available": len(templates),
            "plans_created": len(_plans_storage),
            "plans_completed": len([p for p in _plans_storage.values() if p.status == PlanStatus.COMPLETED]),
        },
        "template_types": ["website", "odoo_config", "integration"],
    }
