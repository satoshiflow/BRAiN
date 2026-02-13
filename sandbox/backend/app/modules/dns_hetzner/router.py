"""
Hetzner DNS Module - API Router (Sprint II)

REST API endpoints for DNS operations.

**SECURITY CRITICAL:**
All DNS endpoints are STRICTLY LOCAL trust tier only.
DMZ and EXTERNAL requests are blocked with HTTP 403.

Trust Tier Enforcement:
- LOCAL: ✅ ALLOWED (localhost only)
- DMZ: ❌ BLOCKED
- EXTERNAL: ❌ BLOCKED

Endpoints:
- POST /api/dns/hetzner/apply - Apply DNS record (idempotent)
- GET /api/dns/hetzner/zones - List allowed zones
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger

from app.modules.axe_governance import (
    TrustTier,
    AXERequestContext,
    get_axe_trust_validator,
)

from .service import get_dns_service
from .schemas import (
    DNSRecordApplyRequest,
    DNSApplyResult,
    ZonesListResponse,
)


router = APIRouter(
    prefix="/api/dns/hetzner",
    tags=["dns_hetzner"],
)


# ============================================================================
# Trust Tier Validation - STRICT LOCAL ONLY
# ============================================================================


async def validate_local_only(request: Request) -> AXERequestContext:
    """
    Validate trust tier for DNS endpoints.

    **STRICTLY LOCAL ONLY**
    Only localhost requests are allowed.
    DMZ and EXTERNAL requests are blocked with HTTP 403.

    Args:
        request: FastAPI request

    Returns:
        AXERequestContext with validated trust tier

    Raises:
        HTTPException 403: If trust tier is not LOCAL
    """
    validator = get_axe_trust_validator()

    # Extract headers
    headers = dict(request.headers)
    client_host = request.client.host if request.client else None

    # Validate request
    context = await validator.validate_request(
        headers=headers,
        client_host=client_host,
        request_id=str(id(request)),
    )

    # Check if LOCAL (most restrictive)
    if context.trust_tier != TrustTier.LOCAL:
        logger.error(
            f"DNS operation BLOCKED: Non-LOCAL trust tier "
            f"(tier={context.trust_tier.value}, source={context.source_ip}, request_id={context.request_id})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "DNS operations forbidden",
                "trust_tier": context.trust_tier.value,
                "reason": "DNS operations require LOCAL trust tier (localhost only)",
                "contact": "DNS operations can only be performed from localhost for security reasons",
                "allowed": "LOCAL",
                "denied": ["DMZ", "EXTERNAL"],
            },
        )

    logger.info(
        f"DNS operation authorized: LOCAL trust tier "
        f"(source={context.source_ip}, request_id={context.request_id})"
    )

    return context


# ============================================================================
# DNS Endpoints
# ============================================================================


@router.post("/apply", response_model=DNSApplyResult)
async def apply_dns_record(
    request_data: DNSRecordApplyRequest,
    context: AXERequestContext = Depends(validate_local_only),
) -> DNSApplyResult:
    """
    Apply DNS record (idempotent upsert).

    Creates record if doesn't exist, updates if exists with different value.
    No action if record exists with same value.

    **Trust Tier:** LOCAL only (localhost)

    Args:
        request_data: DNS record apply request
        context: Trust tier context (injected)

    Returns:
        DNSApplyResult with action taken

    Raises:
        HTTPException 403: If not LOCAL trust tier
        HTTPException 400: If zone not in allowlist
        HTTPException 500: If apply operation fails
    """
    logger.info(
        f"DNS apply request: {request_data.record_type.value} "
        f"{request_data.name}.{request_data.zone} -> {request_data.value or 'default'} "
        f"(ttl={request_data.ttl})"
    )

    try:
        dns_service = get_dns_service()

        result = await dns_service.apply_dns_record(
            zone=request_data.zone,
            record_type=request_data.record_type,
            name=request_data.name,
            value=request_data.value,
            ttl=request_data.ttl,
        )

        if not result.success:
            # Determine appropriate HTTP status code
            if result.errors and any("not in allowlist" in err for err in result.errors):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "zone_not_allowed",
                        "message": result.message,
                        "zone": request_data.zone,
                        "errors": result.errors,
                    },
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "apply_failed",
                        "message": result.message,
                        "errors": result.errors,
                    },
                )

        logger.info(
            f"DNS apply SUCCESS: {result.action} - "
            f"{result.record_type} {result.name}.{result.zone} -> {result.value}"
        )

        return result

    except HTTPException:
        raise  # Re-raise HTTP exceptions

    except Exception as e:
        logger.error(f"DNS apply error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": f"Failed to apply DNS record: {str(e)}",
            },
        )


@router.get("/zones", response_model=ZonesListResponse)
async def list_zones(
    context: AXERequestContext = Depends(validate_local_only),
) -> ZonesListResponse:
    """
    List all allowed DNS zones.

    Returns zones filtered by allowlist policy.

    **Trust Tier:** LOCAL only (localhost)

    Args:
        context: Trust tier context (injected)

    Returns:
        ZonesListResponse with allowed zones

    Raises:
        HTTPException 403: If not LOCAL trust tier
        HTTPException 500: If zone listing fails
    """
    logger.info("DNS zones list request")

    try:
        dns_service = get_dns_service()

        zones = await dns_service.list_zones()

        logger.info(f"DNS zones list SUCCESS: {len(zones)} zones")

        return ZonesListResponse(
            zones=zones,
            total_count=len(zones),
            allowed_zones=dns_service.config.allowed_zones,
        )

    except Exception as e:
        logger.error(f"DNS zones list error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": f"Failed to list zones: {str(e)}",
            },
        )
