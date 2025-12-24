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


# ============================================================================
# IPv6 MONITORING ENDPOINTS
# ============================================================================

from backend.app.modules.sovereign_mode.ipv6_monitoring import (
    get_ipv6_traffic_monitor,
    IPv6TrafficStats,
    IPv6FirewallStats,
)
from fastapi.responses import PlainTextResponse


@router.get("/ipv6/traffic", response_model=IPv6TrafficStats)
async def get_ipv6_traffic_stats():
    """
    Get IPv6 traffic statistics.

    Returns kernel-level IPv6 traffic metrics:
    - Packets/bytes received and sent
    - Dropped packets
    - IPv6 enabled status

    **Use Case**: Monitor IPv6 traffic in real-time
    """
    monitor = get_ipv6_traffic_monitor()
    
    try:
        stats = await monitor.get_traffic_stats()
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get IPv6 traffic stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get IPv6 traffic stats: {str(e)}"
        )


@router.get("/ipv6/firewall", response_model=IPv6FirewallStats)
async def get_ipv6_firewall_stats():
    """
    Get IPv6 firewall statistics.

    Returns IPv6 firewall metrics:
    - Active firewall rules
    - Allowed packets
    - Dropped packets
    - Rejected packets

    **Use Case**: Monitor IPv6 firewall effectiveness
    """
    monitor = get_ipv6_traffic_monitor()
    
    try:
        stats = await monitor.get_firewall_stats()
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get IPv6 firewall stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get IPv6 firewall stats: {str(e)}"
        )


@router.get("/ipv6/metrics/prometheus", response_class=PlainTextResponse)
async def get_ipv6_prometheus_metrics():
    """
    Get IPv6 metrics in Prometheus format.

    Returns IPv6 traffic and firewall metrics in Prometheus format.

    **Metrics exposed**:
    - `ipv6_enabled`: IPv6 status (1=yes, 0=no)
    - `ipv6_packets_received_total`: Total packets received
    - `ipv6_packets_sent_total`: Total packets sent
    - `ipv6_bytes_received_total`: Total bytes received
    - `ipv6_bytes_sent_total`: Total bytes sent
    - `ipv6_dropped_packets_total`: Total dropped packets
    - `ipv6_firewall_active_rules`: Active firewall rules
    - `ipv6_firewall_allowed_packets_total`: Allowed packets
    - `ipv6_firewall_dropped_packets_total`: Dropped packets

    **Use Case**: Prometheus/Grafana integration
    """
    monitor = get_ipv6_traffic_monitor()
    
    try:
        metrics = await monitor.get_prometheus_metrics()
        return metrics
    
    except Exception as e:
        logger.error(f"Failed to get IPv6 Prometheus metrics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get IPv6 Prometheus metrics: {str(e)}"
        )


# ============================================================================
# FIREWALL AUDIT LOGGING ENDPOINTS
# ============================================================================

from backend.app.modules.sovereign_mode.firewall_audit import (
    get_firewall_audit_log,
    FirewallAuditEntry,
    FirewallOperation,
)
from typing import Dict, Any


@router.get("/firewall/audit/recent", response_model=List[FirewallAuditEntry])
async def get_recent_firewall_audit_entries(
    limit: int = 100,
    operation: Optional[str] = None,
):
    """
    Get recent firewall audit log entries.

    Returns recent firewall rule changes and operations.

    **Query Parameters**:
    - `limit`: Maximum number of entries (default: 100, max: 1000)
    - `operation`: Filter by operation type (optional)

    **Operations**:
    - `rule_added`: Firewall rule was added
    - `rule_removed`: Firewall rule was removed
    - `rules_flushed`: All rules were flushed
    - `mode_changed`: Firewall mode changed
    - `script_executed`: Firewall script executed

    **Use Case**: Audit trail, compliance, troubleshooting
    """
    if limit > 1000:
        limit = 1000

    audit_log = get_firewall_audit_log()

    try:
        # Parse operation filter
        op_filter = None
        if operation:
            try:
                op_filter = FirewallOperation(operation)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid operation: {operation}. Must be one of: {[e.value for e in FirewallOperation]}"
                )

        entries = await audit_log.get_recent_entries(limit=limit, operation=op_filter)
        return entries

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get firewall audit entries: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get firewall audit entries: {str(e)}"
        )


@router.get("/firewall/audit/stats", response_model=Dict[str, Any])
async def get_firewall_audit_stats():
    """
    Get firewall audit statistics.

    Returns aggregated statistics about firewall operations:
    - Total entries
    - Operations by type
    - Scripts used
    - Modes changed
    - Success rate

    **Use Case**: Compliance reporting, system health
    """
    audit_log = get_firewall_audit_log()

    try:
        stats = await audit_log.get_stats()
        return stats

    except Exception as e:
        logger.error(f"Failed to get firewall audit stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get firewall audit stats: {str(e)}"
        )


# ============================================================================
# G1: Bundle Signing & Trusted Key Management
# ============================================================================


@router.post("/bundles/{bundle_id}/sign", summary="Sign bundle with system key")
async def sign_bundle_endpoint(bundle_id: str):
    """
    Sign a bundle using the system signing key.

    **Auth**: Owner only (TODO: Add auth middleware)

    **Returns**: Bundle with signature added
    """
    from backend.app.modules.sovereign_mode.crypto import (
        generate_keypair,
        sign_bundle as crypto_sign_bundle,
        export_public_key_pem,
        export_public_key_hex,
    )
    from backend.app.modules.sovereign_mode.keyring import get_trusted_keyring
    from datetime import datetime

    service = get_sovereign_mode_service()

    try:
        # Get bundle
        bundle = service.bundle_manager.get_bundle(bundle_id)
        if not bundle:
            raise HTTPException(status_code=404, detail=f"Bundle not found: {bundle_id}")

        # Generate or load system key (simplified for now)
        # TODO: Use persistent system key from storage
        private_key, public_key = generate_keypair()
        public_key_pem = export_public_key_pem(public_key)
        public_key_hex = export_public_key_hex(public_key)

        key_id = "system-key-001"

        # Add key to keyring if not present
        keyring = get_trusted_keyring()
        if not keyring.is_trusted(key_id):
            keyring.add_key(
                key_id=key_id,
                public_key_pem=public_key_pem,
                origin="system",
                trust_level="full",
                added_by="system",
                description="System master signing key",
            )

        # Sign bundle
        bundle_dict = bundle.model_dump()
        signature_hex = crypto_sign_bundle(bundle_dict, private_key)

        # Update bundle
        bundle.signature = signature_hex
        bundle.signature_algorithm = "ed25519"
        bundle.signed_by_key_id = key_id
        bundle.signed_at = datetime.utcnow()

        logger.info(f"Signed bundle {bundle_id} with key {key_id}")

        return bundle

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sign bundle {bundle_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sign bundle: {str(e)}")


@router.post("/bundles/{bundle_id}/verify", summary="Verify bundle signature")
async def verify_bundle_endpoint(bundle_id: str):
    """
    Verify a bundle's signature against trusted keyring.

    **Returns**: ValidationResult with signature verification status
    """
    service = get_sovereign_mode_service()

    try:
        # Get bundle
        bundle = service.bundle_manager.get_bundle(bundle_id)
        if not bundle:
            raise HTTPException(status_code=404, detail=f"Bundle not found: {bundle_id}")

        # Validate bundle (includes signature verification)
        result = service.bundle_manager.validate_bundle(bundle_id, force=True)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify bundle {bundle_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify bundle: {str(e)}")


@router.get("/keys", summary="List trusted keys")
async def list_trusted_keys(
    origin: Optional[str] = None,
    trust_level: Optional[str] = None,
    include_revoked: bool = False,
):
    """
    List all trusted public keys in keyring.

    **Query Parameters**:
    - origin: Filter by origin (system/owner/external)
    - trust_level: Filter by trust level (full/limited)
    - include_revoked: Include revoked keys (default: false)

    **Auth**: Core/Owner (TODO: Add auth middleware)

    **Returns**: List of TrustedKey objects
    """
    from backend.app.modules.sovereign_mode.keyring import get_trusted_keyring

    try:
        keyring = get_trusted_keyring()
        keys = keyring.list_keys(
            origin=origin,
            trust_level=trust_level,
            include_revoked=include_revoked,
        )

        return keys

    except Exception as e:
        logger.error(f"Failed to list trusted keys: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list keys: {str(e)}")


@router.post("/keys", summary="Add trusted key")
async def add_trusted_key(
    key_id: str,
    public_key_pem: str,
    origin: str = "owner",
    trust_level: str = "full",
    description: Optional[str] = None,
):
    """
    Add a new trusted public key to the keyring.

    **Request Body**:
    - key_id: Unique key identifier
    - public_key_pem: PEM-encoded Ed25519 public key
    - origin: Key origin (system/owner/external)
    - trust_level: Trust level (full/limited)
    - description: Optional key description

    **Auth**: Owner only (TODO: Add auth middleware)

    **Returns**: TrustedKey object
    """
    from backend.app.modules.sovereign_mode.keyring import get_trusted_keyring

    try:
        keyring = get_trusted_keyring()

        trusted_key = keyring.add_key(
            key_id=key_id,
            public_key_pem=public_key_pem,
            origin=origin,
            trust_level=trust_level,
            added_by="api",  # TODO: Use actual user from auth
            description=description,
        )

        logger.info(f"Added trusted key: {key_id} (origin={origin})")

        return trusted_key

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add trusted key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add key: {str(e)}")


@router.delete("/keys/{key_id}", summary="Remove trusted key")
async def remove_trusted_key(key_id: str, revoke: bool = False):
    """
    Remove or revoke a trusted key.

    **Path Parameters**:
    - key_id: Key identifier to remove/revoke

    **Query Parameters**:
    - revoke: If true, revoke key (maintain audit trail); if false, delete key

    **Auth**: Owner only (TODO: Add auth middleware)

    **Returns**: Success message
    """
    from backend.app.modules.sovereign_mode.keyring import get_trusted_keyring

    try:
        keyring = get_trusted_keyring()

        if revoke:
            # Revoke key (maintains audit trail)
            success = keyring.revoke_key(key_id, reason="Manual revocation via API")
            if not success:
                raise HTTPException(status_code=404, detail=f"Key not found: {key_id}")

            logger.warning(f"Revoked trusted key: {key_id}")
            return {"success": True, "message": f"Key {key_id} revoked"}

        else:
            # Delete key (permanent removal)
            success = keyring.remove_key(key_id)
            if not success:
                raise HTTPException(status_code=404, detail=f"Key not found: {key_id}")

            logger.warning(f"Removed trusted key: {key_id}")
            return {"success": True, "message": f"Key {key_id} removed"}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to remove/revoke key {key_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove key: {str(e)}")
