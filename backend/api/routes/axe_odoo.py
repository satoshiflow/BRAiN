"""
AXE × Odoo Integration API Routes

Endpoints for Odoo module generation and orchestration.
Sprint IV: AXE × Odoo Integration

**Trust Tier:** LOCAL only (all endpoints)
**Fail-Safe:** All operations return 200 with structured errors
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
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


def enforce_local_trust_tier(request: Request = None):
    """
    Enforce LOCAL trust tier for Odoo operations.

    Security Implementation:
    - Checks if ODOO_ENFORCE_TRUST_TIER is enabled (default: true)
    - Validates request comes from localhost (127.0.0.1 or ::1)
    - Logs warning if trust tier check is bypassed

    Raises:
        HTTPException: 403 if trust tier check fails

    Future: Integrate with Policy Engine for full RBAC
    """
    import os

    # Feature flag (default: true for security)
    enforce = os.getenv("ODOO_ENFORCE_TRUST_TIER", "true").lower() == "true"

    if not enforce:
        logger.warning(
            "⚠️ ODOO trust tier enforcement DISABLED (ODOO_ENFORCE_TRUST_TIER=false) "
            "- ALL Odoo operations are unprotected!"
        )
        return

    # If no request context (testing), allow
    if request is None:
        logger.debug("No request context - allowing (test mode)")
        return

    # Get client IP
    client_host = request.client.host if request.client else None

    # Allow localhost (IPv4 and IPv6)
    if client_host in ["127.0.0.1", "::1", "localhost"]:
        logger.debug(f"Odoo operation allowed from localhost: {client_host}")
        return

    # Check X-Forwarded-For header (if behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take first IP (original client)
        original_client = forwarded_for.split(",")[0].strip()
        if original_client in ["127.0.0.1", "::1"]:
            logger.debug(f"Odoo operation allowed from proxied localhost: {original_client}")
            return

    # Deny all other requests
    logger.error(
        f"🔒 Odoo operation DENIED - LOCAL trust tier required. "
        f"Request from: {client_host} (X-Forwarded-For: {forwarded_for})"
    )
    raise HTTPException(
        status_code=403,
        detail="Forbidden: Odoo operations require LOCAL trust tier. "
               "Only localhost requests are permitted."
    )


# ============================================================================
# Module Generation & Orchestration
# ============================================================================


@router.post("/module/generate", response_model=OdooOrchestrationResult)
async def generate_odoo_module(payload: ModuleGenerateRequest, request: Request):
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
        enforce_local_trust_tier(request)

        # Execute orchestration
        orchestrator = get_odoo_orchestrator()
        result = await orchestrator.generate_and_install(payload)

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
async def install_odoo_module(payload: ModuleInstallRequest, request: Request):
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
        enforce_local_trust_tier(request)

        # Execute orchestration
        orchestrator = get_odoo_orchestrator()
        result = await orchestrator.install_existing(payload)

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
async def upgrade_odoo_module(payload: ModuleUpgradeRequest, request: Request):
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
        enforce_local_trust_tier(request)

        # Execute orchestration
        orchestrator = get_odoo_orchestrator()
        result = await orchestrator.upgrade_module(payload)

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
async def rollback_odoo_module(payload: ModuleRollbackRequest, request: Request):
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
        enforce_local_trust_tier(request)

        # Execute orchestration
        orchestrator = get_odoo_orchestrator()
        result = await orchestrator.rollback_module(payload)

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
async def list_generated_modules(request: Request):
    """
    List all generated Odoo modules in registry.

    **Trust Tier:** LOCAL

    Returns:
        RegistryListResponse with all modules and version info
    """
    try:
        # Enforce trust tier
        enforce_local_trust_tier(request)

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
    request: Request,
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
        enforce_local_trust_tier(request)

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
