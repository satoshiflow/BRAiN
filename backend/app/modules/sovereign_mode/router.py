"""
Sovereign Mode Router

REST API endpoints for sovereign mode operations.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from backend.app.modules.sovereign_mode.service import get_sovereign_service
from backend.app.modules.sovereign_mode.schemas import (
    SovereignMode,
    Bundle,
    BundleStatus,
    ValidationResult,
    ModeConfig,
    ModeChangeRequest,
    BundleLoadRequest,
    NetworkCheckResult,
    AuditEntry,
)


router = APIRouter(prefix="/api/sovereign-mode", tags=["sovereign-mode"])


@router.get("/info", summary="Get sovereign mode information")
async def get_info():
    """Get basic sovereign mode system information."""
    return {
        "name": "BRAiN Sovereign Mode",
        "version": "1.0.0",
        "description": "Secure offline operation with model bundle management",
        "features": [
            "Network connectivity detection",
            "Offline model bundle management",
            "SHA256 integrity validation",
            "Network request blocking",
            "Fail-closed security",
            "Comprehensive audit logging",
        ],
        "endpoints": [
            "GET /api/sovereign-mode/status - Get current status",
            "POST /api/sovereign-mode/mode - Change operation mode",
            "GET /api/sovereign-mode/bundles - List bundles",
            "POST /api/sovereign-mode/bundles/load - Load bundle",
            "POST /api/sovereign-mode/bundles/validate - Validate bundle",
            "GET /api/sovereign-mode/network/check - Check network",
            "GET /api/sovereign-mode/config - Get configuration",
            "PUT /api/sovereign-mode/config - Update configuration",
            "GET /api/sovereign-mode/audit - Get audit log",
            "GET /api/sovereign-mode/statistics - Get statistics",
        ],
    }


@router.get("/status", response_model=SovereignMode, summary="Get current status")
async def get_status():
    """
    Get current sovereign mode status.

    Returns complete system status including mode, bundles, and network state.
    """
    try:
        service = get_sovereign_service()
        status = await service.get_status()
        return status

    except Exception as e:
        logger.error(f"Error getting sovereign mode status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mode", response_model=SovereignMode, summary="Change operation mode")
async def change_mode(request: ModeChangeRequest):
    """
    Change operation mode.

    Switches between ONLINE, OFFLINE, SOVEREIGN, and QUARANTINE modes.
    May load bundles if switching to offline modes.

    **Security:** Mode changes are audited if enabled in configuration.
    """
    try:
        service = get_sovereign_service()
        result = await service.change_mode(request, triggered_by="api")

        logger.info(
            f"Mode change via API: {request.target_mode} "
            f"(force={request.force}, bundle={request.bundle_id})"
        )

        return result

    except ValueError as e:
        logger.warning(f"Invalid mode change request: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error changing mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bundles", response_model=List[Bundle], summary="List bundles")
async def list_bundles(
    status: Optional[BundleStatus] = Query(None, description="Filter by status")
):
    """
    List available offline bundles.

    Can optionally filter by bundle status (validated, loaded, quarantined, etc.).
    """
    try:
        service = get_sovereign_service()
        bundles = service.get_bundles(status=status)

        return bundles

    except Exception as e:
        logger.error(f"Error listing bundles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bundles/{bundle_id}", response_model=Bundle, summary="Get bundle details")
async def get_bundle(bundle_id: str):
    """
    Get detailed information about a specific bundle.

    Includes validation status, load history, and metadata.
    """
    try:
        service = get_sovereign_service()
        bundle = service.get_bundle(bundle_id)

        if not bundle:
            raise HTTPException(status_code=404, detail=f"Bundle not found: {bundle_id}")

        return bundle

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error getting bundle {bundle_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bundles/load", response_model=Bundle, summary="Load bundle")
async def load_bundle(request: BundleLoadRequest):
    """
    Load an offline model bundle.

    Validates bundle integrity before loading unless skip_quarantine_check is True (unsafe!).

    **Security:**
    - Bundles are validated against SHA256 hashes
    - Failed validations result in quarantine if enabled
    - Bundle loads are audited if enabled
    """
    try:
        service = get_sovereign_service()
        bundle = await service.load_bundle(request)

        logger.info(f"Bundle loaded via API: {request.bundle_id}")

        return bundle

    except ValueError as e:
        logger.warning(f"Bundle load failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error loading bundle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/bundles/{bundle_id}/validate",
    response_model=ValidationResult,
    summary="Validate bundle"
)
async def validate_bundle(
    bundle_id: str,
    force: bool = Query(False, description="Force revalidation"),
):
    """
    Validate bundle integrity.

    Checks SHA256 hashes for both model file and manifest.
    Failed validations may trigger quarantine if auto-quarantine is enabled.

    **Security:** Validation uses cached results unless force=True.
    """
    try:
        service = get_sovereign_service()
        result = await service.validate_bundle(bundle_id, force=force)

        return result

    except Exception as e:
        logger.error(f"Error validating bundle {bundle_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/network/check",
    response_model=NetworkCheckResult,
    summary="Check network connectivity"
)
async def check_network(
    include_firewall: bool = True
):
    """
    Check network connectivity.

    Performs DNS and/or HTTP checks to determine if network is available.
    Optionally includes host firewall state (iptables enforcement).

    Args:
        include_firewall: Whether to check host firewall state (default: True)

    Returns:
        NetworkCheckResult with optional firewall_state field

    **Phase 2 Enhancement:** Now includes host firewall enforcement status
    when include_firewall=True. This verifies that iptables rules are active
    at the kernel level, providing defense-in-depth beyond application-level
    NetworkGuard.
    """
    try:
        service = get_sovereign_service()
        result = await service.check_network()

        # Phase 2: Add host firewall state check
        if include_firewall:
            from backend.app.modules.sovereign_mode.network_guard import check_host_firewall_state

            try:
                firewall_state = await check_host_firewall_state()
                result.firewall_state = firewall_state

                logger.debug(
                    f"Network check with firewall: online={result.is_online}, "
                    f"firewall_mode={firewall_state.get('mode')}"
                )

            except Exception as fw_error:
                logger.warning(f"Could not check firewall state: {fw_error}")
                result.firewall_state = {
                    "firewall_enabled": False,
                    "mode": "unknown",
                    "rules_count": 0,
                    "error": str(fw_error)
                }

        return result

    except Exception as e:
        logger.error(f"Error checking network: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", response_model=ModeConfig, summary="Get configuration")
async def get_config():
    """
    Get current sovereign mode configuration.

    Includes settings for auto-detection, validation, network guards, and audit logging.
    """
    try:
        service = get_sovereign_service()
        return service.config

    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config", response_model=ModeConfig, summary="Update configuration")
async def update_config(updates: dict):
    """
    Update sovereign mode configuration.

    Can update any configuration field. Changes are persisted to storage.

    **Example:**
    ```json
    {
        "auto_detect_network": true,
        "network_check_interval": 60,
        "strict_validation": true,
        "block_external_http": true
    }
    ```
    """
    try:
        service = get_sovereign_service()
        config = service.update_config(**updates)

        logger.info(f"Config updated via API: {list(updates.keys())}")

        return config

    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit", response_model=List[AuditEntry], summary="Get audit log")
async def get_audit_log(
    limit: int = Query(100, ge=1, le=1000, description="Max entries to return"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
):
    """
    Get audit log entries.

    Returns recent audit events including mode changes, bundle loads, and security events.

    **Event Types:**
    - sovereign.mode_changed: Operation mode changes
    - sovereign.gate_check_passed: Gate check successful
    - sovereign.gate_check_failed: Gate check failed
    - sovereign.egress_rules_applied: Firewall rules applied
    - sovereign.egress_rules_removed: Firewall rules removed
    - sovereign.network_probe_passed: Network connectivity verified
    - sovereign.network_probe_failed: Network probe failed
    - sovereign.ipv6_gate_checked: IPv6 gate check performed
    - sovereign.ipv6_gate_failed: IPv6 gate check failed
    - sovereign.connector_blocked: Connector/Gateway blocked
    - sovereign.dmz_stopped: DMZ gateway stopped
    - sovereign.bundle_loaded: Bundle loaded successfully
    """
    try:
        service = get_sovereign_service()
        entries = service.get_audit_log(limit=limit, event_type=event_type)

        return entries

    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", summary="Get statistics")
async def get_statistics():
    """
    Get comprehensive sovereign mode statistics.

    Includes bundle stats, network guard stats, detector stats, and audit counts.
    """
    try:
        service = get_sovereign_service()
        stats = service.get_statistics()

        return stats

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bundles/discover", summary="Discover bundles")
async def discover_bundles():
    """
    Trigger bundle discovery.

    Scans bundles directory for new or updated bundles.
    Returns count of discovered bundles.
    """
    try:
        service = get_sovereign_service()
        bundles = service.bundle_manager.discover_bundles()

        return {
            "discovered": len(bundles),
            "bundles": [b.id for b in bundles],
        }

    except Exception as e:
        logger.error(f"Error discovering bundles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/bundles/{bundle_id}/quarantine",
    summary="Remove from quarantine"
)
async def remove_quarantine(bundle_id: str):
    """
    Remove bundle from quarantine.

    **Warning:** Only use if you're certain the bundle is safe.
    Bundle will be set to PENDING status and must be revalidated before loading.
    """
    try:
        service = get_sovereign_service()
        bundle = service.get_bundle(bundle_id)

        if not bundle:
            raise HTTPException(status_code=404, detail=f"Bundle not found: {bundle_id}")

        if bundle.status != BundleStatus.QUARANTINED:
            raise HTTPException(
                status_code=400,
                detail=f"Bundle is not quarantined: {bundle_id}"
            )

        # Reset to pending
        bundle.status = BundleStatus.PENDING
        bundle.quarantine_reason = None
        bundle.quarantine_timestamp = None

        logger.warning(f"Bundle {bundle_id} removed from quarantine via API")

        return {"message": f"Bundle {bundle_id} removed from quarantine"}

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error removing quarantine for {bundle_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
