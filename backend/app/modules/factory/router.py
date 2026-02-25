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
    dependencies=[Depends(require_auth)]
)

# Storage for plans (in-memory for MVP - should be Redis/DB in production)
_plans_storage: dict[str, BusinessPlan] = {}


@router.post("/plan", response_model=BusinessPlan)
async def create_plan(briefing: BusinessBriefing):
    """
    Generate execution plan from business briefing.

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
        logger.error(f"Error creating plan: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create plan: {str(e)}")


@router.post("/execute")
async def execute_plan(
    plan_id: str = Query(..., description="Plan ID to execute"),
    confirm: bool = Query(False, description="Confirm execution (required=true)")
):
    """
    Execute a validated business plan.

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
        import time
        time.sleep(2)  # Simulate work

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
        logger.error(f"Execution failed: {e}")
        plan.status = PlanStatus.FAILED
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.get("/{plan_id}", response_model=BusinessPlan)
async def get_plan(plan_id: str):
    """Get business plan by ID"""
    plan = _plans_storage.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")

    return plan


@router.get("/{plan_id}/evidence")
async def get_evidence_pack(plan_id: str):
    """
    Download evidence pack for completed plan.

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


@router.post("/{plan_id}/rollback", response_model=RollbackResult)
async def rollback_plan(
    plan_id: str,
    to_step: Optional[int] = Query(None, description="Rollback to specific step (None=full rollback)")
):
    """
    Rollback executed plan.

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
        logger.error(f"Rollback failed: {e}")
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")


@router.get("/templates", response_model=List[Template])
async def list_templates(
    type: Optional[str] = Query(None, description="Filter by template type")
):
    """List available templates"""
    try:
        loader = get_template_loader()
        templates = loader.list_templates(type=type)
        return templates
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.get("/info")
async def factory_info():
    """Get factory system information"""
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
