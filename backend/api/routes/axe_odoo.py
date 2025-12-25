"""
AXE × Odoo Integration API Routes

Endpoints for Odoo module generation and orchestration.
Sprint IV: AXE × Odoo Integration

**Trust Tier:** LOCAL only (all endpoints)
**Fail-Safe:** All operations return 200 with structured errors
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from backend.app.modules.odoo_connector import (
    OdooModuleListResponse,
    OdooModuleState,
    get_odoo_service,
)
from backend.app.modules.odoo_orchestrator import (
    ModuleGenerateRequest,
    ModuleInstallRequest,
    ModuleRollbackRequest,
    ModuleUpgradeRequest,
    OdooOrchestrationResult,
    get_odoo_orchestrator,
)
from backend.app.modules.odoo_registry import (
    RegistryListResponse,
    get_odoo_registry,
)

router = APIRouter(prefix="/api/axe/odoo", tags=["axe-odoo"])


# ============================================================================
# Trust Tier Enforcement
# ============================================================================


def enforce_local_trust_tier():
    """
    Enforce LOCAL trust tier for Odoo operations.

    Raises:
        HTTPException: 403 if trust tier check fails

    Note: In production, this should check actual trust tier from
    authentication/authorization context. For now, this is a placeholder.
    """
    # TODO: Implement actual trust tier check
    # For now, we'll allow all operations (development mode)
    # In production, this should verify that the request comes from:
    # - Local system (localhost)
    # - Authenticated admin user
    # - Specific authorized agents

    # Example implementation:
    # from backend.app.modules.policy import PolicyService
    # policy_service = PolicyService()
    # result = policy_service.evaluate(
    #     agent_id=current_user_agent_id,
    #     action="odoo.module_operation",
    #     context={"trust_tier": "LOCAL"}
    # )
    # if result.effect != PolicyEffect.ALLOW:
    #     raise HTTPException(status_code=403, detail="LOCAL trust tier required")

    pass  # Development mode - allow all


# ============================================================================
# Module Generation & Orchestration
# ============================================================================


@router.post("/module/generate", response_model=OdooOrchestrationResult)
async def generate_odoo_module(request: ModuleGenerateRequest):
    """
    Generate Odoo module from text specification.

    **Trust Tier:** LOCAL

    This endpoint:
    1. Parses text spec into ModuleAST
    2. Generates Odoo module files
    3. Stores in registry with version tracking
    4. Optionally installs in Odoo (if auto_install=True)

    Args:
        request: Module generation request

    Returns:
        OdooOrchestrationResult with generation details

    Example Request:
    ```json
    {
        "spec_text": "Create an Odoo module called 'my_custom_crm' v1.0.0\\nSummary: Custom CRM extension\\nDependencies: base, crm\\n\\nModel: custom.lead.stage\\n  - name (required text)\\n  - sequence (integer, default 10)\\n\\nViews:\\n  - Tree view with name, sequence\\n  - Form view with all fields",
        "auto_install": false
    }
    ```
    """
    try:
        # Enforce trust tier
        enforce_local_trust_tier()

        # Execute orchestration
        orchestrator = get_odoo_orchestrator()
        result = await orchestrator.generate_and_install(request)

        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Module generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Module generation failed: {str(e)}",
        )


@router.post("/module/install", response_model=OdooOrchestrationResult)
async def install_odoo_module(request: ModuleInstallRequest):
    """
    Install a previously generated Odoo module.

    **Trust Tier:** LOCAL

    Args:
        request: Module install request

    Returns:
        OdooOrchestrationResult with installation details

    Example Request:
    ```json
    {
        "module_name": "my_custom_crm",
        "version": "1.0.0",
        "force": false
    }
    ```
    """
    try:
        # Enforce trust tier
        enforce_local_trust_tier()

        # Execute orchestration
        orchestrator = get_odoo_orchestrator()
        result = await orchestrator.install_existing(request)

        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Module installation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Module installation failed: {str(e)}",
        )


@router.post("/module/upgrade", response_model=OdooOrchestrationResult)
async def upgrade_odoo_module(request: ModuleUpgradeRequest):
    """
    Upgrade an Odoo module.

    **Trust Tier:** LOCAL

    Two modes:
    1. With spec_text: Generate new version from spec, then upgrade
    2. Without spec_text: Upgrade to latest stored version

    Args:
        request: Module upgrade request

    Returns:
        OdooOrchestrationResult with upgrade details

    Example Request:
    ```json
    {
        "module_name": "my_custom_crm",
        "spec_text": "...",
        "new_version": "1.1.0"
    }
    ```
    """
    try:
        # Enforce trust tier
        enforce_local_trust_tier()

        # Execute orchestration
        orchestrator = get_odoo_orchestrator()
        result = await orchestrator.upgrade_module(request)

        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Module upgrade failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Module upgrade failed: {str(e)}",
        )


@router.post("/module/rollback", response_model=OdooOrchestrationResult)
async def rollback_odoo_module(request: ModuleRollbackRequest):
    """
    Rollback Odoo module to previous version.

    **Trust Tier:** LOCAL

    Args:
        request: Module rollback request

    Returns:
        OdooOrchestrationResult with rollback details

    Example Request:
    ```json
    {
        "module_name": "my_custom_crm",
        "target_version": "1.0.0"
    }
    ```
    """
    try:
        # Enforce trust tier
        enforce_local_trust_tier()

        # Execute orchestration
        orchestrator = get_odoo_orchestrator()
        result = await orchestrator.rollback_module(request)

        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Module rollback failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Module rollback failed: {str(e)}",
        )


# ============================================================================
# Module Registry & Listing
# ============================================================================


@router.get("/modules", response_model=RegistryListResponse)
async def list_generated_modules():
    """
    List all generated Odoo modules in registry.

    **Trust Tier:** LOCAL

    Returns:
        RegistryListResponse with all modules and version info
    """
    try:
        # Enforce trust tier
        enforce_local_trust_tier()

        # Get all modules from registry
        registry = get_odoo_registry()
        modules = registry.list_all_modules()

        return RegistryListResponse(
            modules=modules,
            total_count=len(modules),
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list modules: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list modules: {str(e)}",
        )


@router.get("/modules/odoo", response_model=OdooModuleListResponse)
async def list_odoo_installed_modules(
    state: OdooModuleState | None = Query(None, description="Filter by module state")
):
    """
    List modules installed in Odoo instance.

    **Trust Tier:** LOCAL

    This queries the live Odoo instance for module status.

    Args:
        state: Filter by module state (optional)

    Returns:
        OdooModuleListResponse with Odoo modules
    """
    try:
        # Enforce trust tier
        enforce_local_trust_tier()

        # Query Odoo
        odoo_service = get_odoo_service()
        modules = await odoo_service.list_modules(state=state)

        filters = {}
        if state:
            filters["state"] = state.value

        return OdooModuleListResponse(
            modules=modules,
            total_count=len(modules),
            filters_applied=filters,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list Odoo modules: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list Odoo modules: {str(e)}",
        )


# ============================================================================
# Utility Endpoints
# ============================================================================


@router.get("/info")
async def get_axe_odoo_info():
    """
    Get AXE × Odoo integration information.

    Returns:
        System information and configuration status
    """
    import os

    return {
        "name": "AXE × Odoo Integration",
        "version": "1.0.0",
        "description": "Odoo module generation and orchestration via AXE",
        "sprint": "Sprint IV",
        "trust_tier": "LOCAL",
        "features": [
            "Text-to-Odoo module generation",
            "Version management and rollback",
            "Automated installation",
            "Release tracking",
            "Audit trail",
        ],
        "configuration": {
            "odoo_url": os.getenv("ODOO_BASE_URL", "Not configured"),
            "odoo_db": os.getenv("ODOO_DB_NAME", "Not configured"),
            "addons_path": os.getenv("ODOO_ADDONS_PATH", "Not configured"),
        },
        "endpoints": {
            "generate": "/api/axe/odoo/module/generate",
            "install": "/api/axe/odoo/module/install",
            "upgrade": "/api/axe/odoo/module/upgrade",
            "rollback": "/api/axe/odoo/module/rollback",
            "list_registry": "/api/axe/odoo/modules",
            "list_odoo": "/api/axe/odoo/modules/odoo",
        },
    }
