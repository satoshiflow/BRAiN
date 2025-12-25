"""
WebGenesis Module - API Routes

FastAPI endpoints for website generation, build, and deployment.

Trust Tier Enforcement:
- Deploy endpoints restricted to DMZ/LOCAL only
- EXTERNAL requests blocked with HTTP 403
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger

from app.modules.axe_governance import (
    TrustTier,
    AXERequestContext,
    get_axe_trust_validator,
)

from .service import get_webgenesis_service
from .schemas import (
    SpecSubmitRequest,
    SpecSubmitResponse,
    GenerateRequest,
    GenerateResponse,
    BuildRequest,
    BuildResponse,
    DeployRequest,
    DeployResponse,
    SiteStatusResponse,
)


router = APIRouter(
    prefix="/api/webgenesis",
    tags=["webgenesis"],
)


# ============================================================================
# Trust Tier Validation Dependency
# ============================================================================


async def validate_trust_tier_for_deploy(request: Request) -> AXERequestContext:
    """
    Validate trust tier for deployment endpoints.

    Only LOCAL and DMZ trust tiers are allowed for deployment.
    EXTERNAL requests are blocked with HTTP 403.

    Args:
        request: FastAPI request

    Returns:
        AXERequestContext with validated trust tier

    Raises:
        HTTPException 403: If trust tier is EXTERNAL
    """
    validator = get_axe_trust_validator()

    # Extract headers
    headers = dict(request.headers)
    client_host = request.client.host if request.client else None

    # Validate request
    context = await validator.validate_request(
        headers=headers,
        client_host=client_host,
        request_id=str(id(request)),  # Simple request ID
    )

    # Check if allowed
    if context.trust_tier == TrustTier.EXTERNAL:
        logger.error(
            f"WebGenesis deployment blocked: EXTERNAL trust tier "
            f"(source={context.source_ip}, request_id={context.request_id})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Deployment not allowed from EXTERNAL sources",
                "trust_tier": context.trust_tier.value,
                "reason": "Deploy operations require DMZ or LOCAL trust tier",
                "contact": "Authenticate via DMZ gateway or use local access",
            },
        )

    logger.info(
        f"WebGenesis deployment authorized: trust_tier={context.trust_tier.value}, "
        f"source={context.source_service or context.source_ip}"
    )

    return context


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/spec", response_model=SpecSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_spec(request: SpecSubmitRequest):
    """
    Submit website specification.

    Creates a new site entry and stores the spec.

    **Trust Tier:** Any (no restriction)

    Args:
        request: Website spec submission

    Returns:
        Site ID and spec hash

    Example:
        ```json
        POST /api/webgenesis/spec
        {
          "spec": {
            "name": "my-site",
            "template": "static_html",
            "pages": [...],
            "seo": {...},
            "deploy": {...}
          }
        }
        ```

        Response:
        ```json
        {
          "success": true,
          "site_id": "my-site_20250101120000",
          "spec_hash": "a1b2c3d4e5f6...",
          "message": "Spec received and stored successfully"
        }
        ```
    """
    try:
        service = get_webgenesis_service()

        site_id, spec_hash, manifest = service.store_spec(request.spec)

        logger.info(f"✅ Spec submitted: site_id={site_id}")

        return SpecSubmitResponse(
            success=True,
            site_id=site_id,
            spec_hash=spec_hash,
            message="Spec received and stored successfully",
        )

    except Exception as e:
        logger.error(f"❌ Failed to submit spec: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit spec: {str(e)}",
        )


@router.post("/{site_id}/generate", response_model=GenerateResponse)
async def generate_source(
    site_id: str,
    request: GenerateRequest = GenerateRequest(),
):
    """
    Generate website source code from spec.

    **Trust Tier:** Any (no restriction)

    Args:
        site_id: Site identifier
        request: Generation options (force rebuild)

    Returns:
        Generation result with source path

    Raises:
        HTTPException 404: If site not found
        HTTPException 400: If generation fails

    Example:
        ```json
        POST /api/webgenesis/my-site_20250101120000/generate
        {
          "force": false
        }
        ```

        Response:
        ```json
        {
          "success": true,
          "site_id": "my-site_20250101120000",
          "source_path": "storage/webgenesis/my-site_20250101120000/source",
          "files_created": 5,
          "message": "Source generated successfully",
          "errors": []
        }
        ```
    """
    try:
        service = get_webgenesis_service()

        source_path, files_created, errors = service.generate_project(
            site_id=site_id,
            force=request.force,
        )

        logger.info(f"✅ Source generated: site_id={site_id}, files={files_created}")

        return GenerateResponse(
            success=True,
            site_id=site_id,
            source_path=source_path,
            files_created=files_created,
            message="Source generated successfully",
            errors=errors,
        )

    except FileNotFoundError as e:
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except ValueError as e:
        logger.error(f"❌ Generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"❌ Generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}",
        )


@router.post("/{site_id}/build", response_model=BuildResponse)
async def build_artifacts(
    site_id: str,
    request: BuildRequest = BuildRequest(),
):
    """
    Build website artifacts from generated source.

    **Trust Tier:** Any (no restriction)

    Args:
        site_id: Site identifier
        request: Build options (force rebuild)

    Returns:
        Build result with artifact hash

    Raises:
        HTTPException 404: If site not found
        HTTPException 400: If build fails

    Example:
        ```json
        POST /api/webgenesis/my-site_20250101120000/build
        {
          "force": false
        }
        ```

        Response:
        ```json
        {
          "result": {
            "success": true,
            "site_id": "my-site_20250101120000",
            "artifact_path": "storage/webgenesis/my-site_20250101120000/build",
            "artifact_hash": "f6e5d4c3b2a1...",
            "timestamp": "2025-01-01T12:00:00Z",
            "errors": [],
            "warnings": []
          },
          "message": "Build completed successfully"
        }
        ```
    """
    try:
        service = get_webgenesis_service()

        build_result = service.build_project(
            site_id=site_id,
            force=request.force,
        )

        if build_result.success:
            logger.info(
                f"✅ Build completed: site_id={site_id}, "
                f"hash={build_result.artifact_hash[:8] if build_result.artifact_hash else 'N/A'}..."
            )
            message = "Build completed successfully"
        else:
            logger.warning(f"⚠️ Build failed: site_id={site_id}, errors={build_result.errors}")
            message = "Build failed"

        return BuildResponse(
            result=build_result,
            message=message,
        )

    except FileNotFoundError as e:
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except ValueError as e:
        logger.error(f"❌ Build failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"❌ Build error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Build failed: {str(e)}",
        )


@router.post("/{site_id}/deploy", response_model=DeployResponse)
async def deploy_site(
    site_id: str,
    request: DeployRequest = DeployRequest(),
    trust_context: AXERequestContext = Depends(validate_trust_tier_for_deploy),
):
    """
    Deploy website using Docker Compose.

    **Trust Tier:** DMZ or LOCAL only (EXTERNAL blocked with HTTP 403)

    ⚠️ **Security:** This endpoint executes system commands (docker-compose).
    Only authenticated DMZ gateways and local requests are allowed.

    Args:
        site_id: Site identifier
        request: Deploy options (force redeploy)
        trust_context: Validated trust context (auto-injected)

    Returns:
        Deployment result with URL and container info

    Raises:
        HTTPException 403: If trust tier is EXTERNAL
        HTTPException 404: If site not found
        HTTPException 400: If deployment fails

    Example:
        ```json
        POST /api/webgenesis/my-site_20250101120000/deploy
        Headers:
          x-dmz-gateway-id: telegram_gateway
          x-dmz-gateway-token: <token>

        Body:
        {
          "force": false
        }
        ```

        Response:
        ```json
        {
          "result": {
            "success": true,
            "site_id": "my-site_20250101120000",
            "url": "http://localhost:8080",
            "container_id": "abc123def456",
            "container_name": "webgenesis-my-site_20250101120000",
            "ports": [8080],
            "timestamp": "2025-01-01T12:00:00Z",
            "errors": [],
            "warnings": []
          },
          "message": "Deployment completed successfully"
        }
        ```
    """
    try:
        service = get_webgenesis_service()

        logger.info(
            f"🚀 Deploying site: site_id={site_id}, "
            f"trust_tier={trust_context.trust_tier.value}, "
            f"source={trust_context.source_service or trust_context.source_ip}"
        )

        deploy_result = service.deploy_project(
            site_id=site_id,
            force=request.force,
        )

        if deploy_result.success:
            logger.info(
                f"✅ Deployment completed: site_id={site_id}, "
                f"url={deploy_result.url}, container={deploy_result.container_id[:12] if deploy_result.container_id else 'N/A'}..."
            )
            message = "Deployment completed successfully"
        else:
            logger.warning(f"⚠️ Deployment failed: site_id={site_id}, errors={deploy_result.errors}")
            message = "Deployment failed"

        return DeployResponse(
            result=deploy_result,
            message=message,
        )

    except FileNotFoundError as e:
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except ValueError as e:
        logger.error(f"❌ Deployment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"❌ Deployment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}",
        )


@router.get("/{site_id}/status", response_model=SiteStatusResponse)
async def get_site_status(site_id: str):
    """
    Get site status and manifest.

    **Trust Tier:** Any (no restriction)

    Args:
        site_id: Site identifier

    Returns:
        Site manifest and container status

    Raises:
        HTTPException 404: If site not found

    Example:
        ```
        GET /api/webgenesis/my-site_20250101120000/status
        ```

        Response:
        ```json
        {
          "site_id": "my-site_20250101120000",
          "manifest": {
            "status": "deployed",
            "deployed_url": "http://localhost:8080",
            "deployed_ports": [8080],
            "created_at": "2025-01-01T12:00:00Z",
            "deployed_at": "2025-01-01T12:05:00Z",
            ...
          },
          "is_running": true,
          "health_status": "healthy"
        }
        ```
    """
    try:
        service = get_webgenesis_service()

        # Load manifest
        manifest = service._load_manifest(site_id)

        # Check if container is running
        is_running = False
        health_status = None

        if manifest.docker_container_id:
            container_name = f"webgenesis-{site_id}"
            is_running = service._check_container_running(container_name)

            if is_running and manifest.deployed_ports:
                # Quick health check
                port = manifest.deployed_ports[0]
                health_ok, health_msg = service._check_deployment_health(
                    port=port,
                    health_path=manifest.metadata.get("healthcheck_path", "/"),
                    timeout=5,
                )
                health_status = "healthy" if health_ok else "unhealthy"

        return SiteStatusResponse(
            site_id=site_id,
            manifest=manifest,
            is_running=is_running,
            health_status=health_status,
        )

    except FileNotFoundError as e:
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except Exception as e:
        logger.error(f"❌ Status check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}",
        )
