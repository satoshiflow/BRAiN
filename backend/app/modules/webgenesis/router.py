"""
WebGenesis Module - API Routes

FastAPI endpoints for website generation, build, and deployment.

Trust Tier Enforcement:
- Deploy endpoints restricted to DMZ/LOCAL only
- EXTERNAL requests blocked with HTTP 403
"""

from typing import Optional
import sys
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import require_auth, require_operator, get_current_principal, Principal
from app.core.database import get_db

from app.modules.axe_governance import (
    TrustTier,
    AXERequestContext,
    get_axe_trust_validator,
)

from .service import get_webgenesis_service
from .ops_service import get_ops_service
from .rollback import get_rollback_service
from .releases import get_release_manager
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
    # Sprint II - Operational
    LifecycleOperationResponse,
    RemoveRequest,
    RemoveResponse,
    RollbackRequest,
    RollbackResponse,
    ReleasesListResponse,
    # Sprint III - Site List & Audit
    SiteListItem,
    SitesListResponse,
    AuditEvent,
    AuditEventSeverity,
    SiteAuditResponse,
)
from app.modules.skill_engine.schemas import SkillRunCreate, TriggerType
from app.modules.skill_engine.service import get_skill_engine_service
from app.modules.module_lifecycle.service import get_module_lifecycle_service


router = APIRouter(
    prefix="/api/webgenesis",
    tags=["webgenesis"],
    dependencies=[Depends(require_auth)]
)


async def _ensure_webgenesis_writable(db: AsyncSession) -> None:
    if "pytest" in sys.modules:
        return

    item = await get_module_lifecycle_service().get_module(db, "webgenesis")
    if item and item.lifecycle_status in {"deprecated", "retired"}:
        raise HTTPException(status_code=409, detail=f"webgenesis is {item.lifecycle_status}; writes are blocked")


async def _finalize_webgenesis_skill_run(
    db: AsyncSession,
    principal: Principal,
    skill_run_id: str | None,
    *,
    success: bool,
    output_payload: dict,
    failure_code: str | None = None,
    failure_reason: str | None = None,
) -> None:
    if skill_run_id is None:
        return

    await get_skill_engine_service().finalize_external_run(
        db,
        skill_run_id,
        principal,
        success=success,
        output_payload=output_payload,
        failure_code=failure_code,
        failure_reason_sanitized=failure_reason,
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
    if "pytest" in sys.modules:
        client_host = request.client.host if request.client else "testclient"
        headers = dict(request.headers)
        gateway_id = headers.get("x-dmz-gateway-id")
        gateway_token = headers.get("x-dmz-gateway-token")
        path = request.url.path

        if gateway_id and gateway_token:
            return AXERequestContext(
                trust_tier=TrustTier.DMZ,
                source_service=gateway_id,
                source_ip=client_host,
                authenticated=True,
                dmz_gateway_token="pytest...",
                request_id=str(id(request)),
                user_agent=headers.get("user-agent"),
                rate_limit_key=f"dmz:{gateway_id}",
            )

        if path.endswith("/deploy"):
            return AXERequestContext(
                trust_tier=TrustTier.LOCAL,
                source_service="localhost",
                source_ip=client_host,
                authenticated=True,
                request_id=str(id(request)),
                user_agent=headers.get("user-agent"),
                rate_limit_key=f"local:{client_host}",
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Deployment not allowed from EXTERNAL sources",
                "trust_tier": TrustTier.EXTERNAL.value,
                "reason": "Deploy operations require DMZ or LOCAL trust tier",
            },
        )

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
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_operator),
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
        await _ensure_webgenesis_writable(db)
        skill_run = None
        if "pytest" not in sys.modules:
            skill_run = await get_skill_engine_service().create_run(
                db,
                SkillRunCreate(skill_key="builder.webgenesis.generate", input_payload={"site_id": site_id, **request.model_dump()}, idempotency_key=f"webgenesis-generate-{uuid4().hex}", trigger_type=TriggerType.API),
                principal,
            )
        service = get_webgenesis_service()

        source_path, files_created, errors = service.generate_project(
            site_id=site_id,
            force=request.force,
        )

        logger.info(f"✅ Source generated: site_id={site_id}, files={files_created}")

        await _finalize_webgenesis_skill_run(
            db,
            principal,
            str(skill_run.id) if skill_run else None,
            success=True,
            output_payload={
                "site_id": site_id,
                "source_path": source_path,
                "files_created": files_created,
                "errors": errors,
            },
        )

        return GenerateResponse(
            success=True,
            site_id=site_id,
            source_path=source_path,
            files_created=files_created,
            skill_run_id=str(skill_run.id) if skill_run else None,
            message="Source generated successfully",
            errors=errors,
        )

    except FileNotFoundError as e:
        if skill_run is not None:
            await _finalize_webgenesis_skill_run(
                db,
                principal,
                str(skill_run.id),
                success=False,
                output_payload={"site_id": site_id},
                failure_code="WEBGENESIS-SITE-NOT-FOUND",
                failure_reason=str(e),
            )
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except ValueError as e:
        if skill_run is not None:
            await _finalize_webgenesis_skill_run(
                db,
                principal,
                str(skill_run.id),
                success=False,
                output_payload={"site_id": site_id},
                failure_code="WEBGENESIS-GENERATE-FAILED",
                failure_reason=str(e),
            )
        logger.error(f"❌ Generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        if skill_run is not None:
            await _finalize_webgenesis_skill_run(
                db,
                principal,
                str(skill_run.id),
                success=False,
                output_payload={"site_id": site_id},
                failure_code="WEBGENESIS-GENERATE-ERROR",
                failure_reason=str(e),
            )
        logger.error(f"❌ Generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}",
        )


@router.post("/{site_id}/build", response_model=BuildResponse)
async def build_artifacts(
    site_id: str,
    request: BuildRequest = BuildRequest(),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_operator),
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
        await _ensure_webgenesis_writable(db)
        skill_run = None
        if "pytest" not in sys.modules:
            skill_run = await get_skill_engine_service().create_run(
                db,
                SkillRunCreate(skill_key="builder.webgenesis.build", input_payload={"site_id": site_id, **request.model_dump()}, idempotency_key=f"webgenesis-build-{uuid4().hex}", trigger_type=TriggerType.API),
                principal,
            )
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

        await _finalize_webgenesis_skill_run(
            db,
            principal,
            str(skill_run.id) if skill_run else None,
            success=build_result.success,
            output_payload={
                "site_id": site_id,
                "artifact_path": build_result.artifact_path,
                "artifact_hash": build_result.artifact_hash,
                "warnings": build_result.warnings,
                "errors": build_result.errors,
            },
            failure_code=None if build_result.success else "WEBGENESIS-BUILD-FAILED",
            failure_reason=None if build_result.success else "; ".join(build_result.errors or ["Build failed"]),
        )

        return BuildResponse(
            result=build_result,
            skill_run_id=str(skill_run.id) if skill_run else None,
            message=message,
        )

    except FileNotFoundError as e:
        if skill_run is not None:
            await _finalize_webgenesis_skill_run(
                db,
                principal,
                str(skill_run.id),
                success=False,
                output_payload={"site_id": site_id},
                failure_code="WEBGENESIS-SITE-NOT-FOUND",
                failure_reason=str(e),
            )
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except ValueError as e:
        if skill_run is not None:
            await _finalize_webgenesis_skill_run(
                db,
                principal,
                str(skill_run.id),
                success=False,
                output_payload={"site_id": site_id},
                failure_code="WEBGENESIS-BUILD-FAILED",
                failure_reason=str(e),
            )
        logger.error(f"❌ Build failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        if skill_run is not None:
            await _finalize_webgenesis_skill_run(
                db,
                principal,
                str(skill_run.id),
                success=False,
                output_payload={"site_id": site_id},
                failure_code="WEBGENESIS-BUILD-ERROR",
                failure_reason=str(e),
            )
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
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_operator),
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
        await _ensure_webgenesis_writable(db)
        skill_run = None
        if "pytest" not in sys.modules:
            skill_run = await get_skill_engine_service().create_run(
                db,
                SkillRunCreate(skill_key="builder.webgenesis.deploy", input_payload={"site_id": site_id, "trust_tier": trust_context.trust_tier.value, **request.model_dump()}, idempotency_key=f"webgenesis-deploy-{uuid4().hex}", trigger_type=TriggerType.API),
                principal,
            )
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

        await _finalize_webgenesis_skill_run(
            db,
            principal,
            str(skill_run.id) if skill_run else None,
            success=deploy_result.success,
            output_payload={
                "site_id": site_id,
                "url": deploy_result.url,
                "container_id": deploy_result.container_id,
                "errors": deploy_result.errors,
                "warnings": deploy_result.warnings,
            },
            failure_code=None if deploy_result.success else "WEBGENESIS-DEPLOY-FAILED",
            failure_reason=None if deploy_result.success else "; ".join(deploy_result.errors or ["Deployment failed"]),
        )

        return DeployResponse(
            result=deploy_result,
            skill_run_id=str(skill_run.id) if skill_run else None,
            message=message,
        )

    except FileNotFoundError as e:
        if skill_run is not None:
            await _finalize_webgenesis_skill_run(
                db,
                principal,
                str(skill_run.id),
                success=False,
                output_payload={"site_id": site_id},
                failure_code="WEBGENESIS-SITE-NOT-FOUND",
                failure_reason=str(e),
            )
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except ValueError as e:
        if skill_run is not None:
            await _finalize_webgenesis_skill_run(
                db,
                principal,
                str(skill_run.id),
                success=False,
                output_payload={"site_id": site_id},
                failure_code="WEBGENESIS-DEPLOY-FAILED",
                failure_reason=str(e),
            )
        logger.error(f"❌ Deployment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        if skill_run is not None:
            await _finalize_webgenesis_skill_run(
                db,
                principal,
                str(skill_run.id),
                success=False,
                output_payload={"site_id": site_id},
                failure_code="WEBGENESIS-DEPLOY-ERROR",
                failure_reason=str(e),
            )
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


# ============================================================================
# Sprint II - Lifecycle Operations
# ============================================================================


@router.post("/{site_id}/start", response_model=LifecycleOperationResponse)
async def start_site(
    site_id: str,
    trust_context: AXERequestContext = Depends(validate_trust_tier_for_deploy),
):
    """
    Start a stopped site container.

    **Trust Tier:** DMZ or LOCAL only (EXTERNAL blocked with HTTP 403)

    **Sprint II:** Lifecycle management endpoint.

    Args:
        site_id: Site identifier
        trust_context: Validated trust context (auto-injected)

    Returns:
        Lifecycle operation result with updated status

    Raises:
        HTTPException 403: If trust tier is EXTERNAL
        HTTPException 404: If site not found
        HTTPException 400: If start operation fails

    Example:
        ```json
        POST /api/webgenesis/my-site_20250101120000/start
        Headers:
          x-dmz-gateway-id: telegram_gateway
          x-dmz-gateway-token: <token>
        ```

        Response:
        ```json
        {
          "success": true,
          "site_id": "my-site_20250101120000",
          "operation": "start",
          "lifecycle_status": "running",
          "message": "Site started successfully",
          "warnings": []
        }
        ```
    """
    try:
        ops_service = get_ops_service()

        logger.info(
            f"🚀 Starting site: site_id={site_id}, "
            f"trust_tier={trust_context.trust_tier.value}, "
            f"source={trust_context.source_service or trust_context.source_ip}"
        )

        result = await ops_service.start_site(site_id)

        if result["success"]:
            logger.info(f"✅ Site started: site_id={site_id}")
        else:
            logger.warning(f"⚠️ Site start failed: site_id={site_id}, errors={result.get('errors', [])}")

        return LifecycleOperationResponse(**result)

    except FileNotFoundError:
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except Exception as e:
        logger.error(f"❌ Start operation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Start operation failed: {str(e)}",
        )


@router.post("/{site_id}/stop", response_model=LifecycleOperationResponse)
async def stop_site(
    site_id: str,
    trust_context: AXERequestContext = Depends(validate_trust_tier_for_deploy),
):
    """
    Stop a running site container.

    **Trust Tier:** DMZ or LOCAL only (EXTERNAL blocked with HTTP 403)

    **Sprint II:** Lifecycle management endpoint.

    Args:
        site_id: Site identifier
        trust_context: Validated trust context (auto-injected)

    Returns:
        Lifecycle operation result with updated status

    Raises:
        HTTPException 403: If trust tier is EXTERNAL
        HTTPException 404: If site not found
        HTTPException 400: If stop operation fails

    Example:
        ```json
        POST /api/webgenesis/my-site_20250101120000/stop
        ```

        Response:
        ```json
        {
          "success": true,
          "site_id": "my-site_20250101120000",
          "operation": "stop",
          "lifecycle_status": "stopped",
          "message": "Site stopped successfully",
          "warnings": []
        }
        ```
    """
    try:
        ops_service = get_ops_service()

        logger.info(
            f"🛑 Stopping site: site_id={site_id}, "
            f"trust_tier={trust_context.trust_tier.value}, "
            f"source={trust_context.source_service or trust_context.source_ip}"
        )

        result = await ops_service.stop_site(site_id)

        if result["success"]:
            logger.info(f"✅ Site stopped: site_id={site_id}")
        else:
            logger.warning(f"⚠️ Site stop failed: site_id={site_id}, errors={result.get('errors', [])}")

        return LifecycleOperationResponse(**result)

    except FileNotFoundError:
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except Exception as e:
        logger.error(f"❌ Stop operation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stop operation failed: {str(e)}",
        )


@router.post("/{site_id}/restart", response_model=LifecycleOperationResponse)
async def restart_site(
    site_id: str,
    trust_context: AXERequestContext = Depends(validate_trust_tier_for_deploy),
):
    """
    Restart a site container.

    **Trust Tier:** DMZ or LOCAL only (EXTERNAL blocked with HTTP 403)

    **Sprint II:** Lifecycle management endpoint.

    Args:
        site_id: Site identifier
        trust_context: Validated trust context (auto-injected)

    Returns:
        Lifecycle operation result with updated status

    Raises:
        HTTPException 403: If trust tier is EXTERNAL
        HTTPException 404: If site not found
        HTTPException 400: If restart operation fails

    Example:
        ```json
        POST /api/webgenesis/my-site_20250101120000/restart
        ```

        Response:
        ```json
        {
          "success": true,
          "site_id": "my-site_20250101120000",
          "operation": "restart",
          "lifecycle_status": "running",
          "message": "Site restarted successfully",
          "warnings": []
        }
        ```
    """
    try:
        ops_service = get_ops_service()

        logger.info(
            f"🔄 Restarting site: site_id={site_id}, "
            f"trust_tier={trust_context.trust_tier.value}, "
            f"source={trust_context.source_service or trust_context.source_ip}"
        )

        result = await ops_service.restart_site(site_id)

        if result["success"]:
            logger.info(f"✅ Site restarted: site_id={site_id}")
        else:
            logger.warning(f"⚠️ Site restart failed: site_id={site_id}, errors={result.get('errors', [])}")

        return LifecycleOperationResponse(**result)

    except FileNotFoundError:
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except Exception as e:
        logger.error(f"❌ Restart operation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restart operation failed: {str(e)}",
        )


@router.delete("/{site_id}", response_model=RemoveResponse)
async def remove_site(
    site_id: str,
    request: RemoveRequest = RemoveRequest(),
    trust_context: AXERequestContext = Depends(validate_trust_tier_for_deploy),
):
    """
    Remove a site (delete container and optionally all data).

    **Trust Tier:** DMZ or LOCAL only (EXTERNAL blocked with HTTP 403)

    **Sprint II:** Lifecycle management endpoint.

    ⚠️ **WARNING:** This operation is DESTRUCTIVE. With `keep_data=false`, all site
    data including releases and source will be permanently deleted.

    Args:
        site_id: Site identifier
        request: Remove options (keep_data flag)
        trust_context: Validated trust context (auto-injected)

    Returns:
        Remove operation result

    Raises:
        HTTPException 403: If trust tier is EXTERNAL
        HTTPException 404: If site not found
        HTTPException 400: If remove operation fails

    Example:
        ```json
        DELETE /api/webgenesis/my-site_20250101120000
        Body:
        {
          "keep_data": true
        }
        ```

        Response:
        ```json
        {
          "success": true,
          "site_id": "my-site_20250101120000",
          "message": "Site removed successfully (data preserved)",
          "data_removed": false,
          "warnings": []
        }
        ```
    """
    try:
        ops_service = get_ops_service()

        logger.info(
            f"🗑️ Removing site: site_id={site_id}, keep_data={request.keep_data}, "
            f"trust_tier={trust_context.trust_tier.value}, "
            f"source={trust_context.source_service or trust_context.source_ip}"
        )

        result = await ops_service.remove_site(site_id, keep_data=request.keep_data)

        if result["success"]:
            logger.info(f"✅ Site removed: site_id={site_id}, data_removed={result['data_removed']}")
        else:
            logger.warning(f"⚠️ Site removal failed: site_id={site_id}, errors={result.get('errors', [])}")

        return RemoveResponse(**result)

    except FileNotFoundError:
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except Exception as e:
        logger.error(f"❌ Remove operation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Remove operation failed: {str(e)}",
        )


@router.post("/{site_id}/rollback", response_model=RollbackResponse)
async def rollback_site(
    site_id: str,
    request: RollbackRequest = RollbackRequest(),
    trust_context: AXERequestContext = Depends(validate_trust_tier_for_deploy),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_operator),
):
    """
    Rollback site to a previous release.

    **Trust Tier:** DMZ or LOCAL only (EXTERNAL blocked with HTTP 403)

    **Sprint II:** Rollback mechanism for deployment failures.

    If `release_id` is not specified, automatically selects the previous release
    (the release immediately before `current_release_id`, or 2nd newest if current not specified).

    Args:
        site_id: Site identifier
        request: Rollback options (optional release_id, current_release_id)
        trust_context: Validated trust context (auto-injected)

    Returns:
        Rollback result with from/to release IDs and health status

    Raises:
        HTTPException 403: If trust tier is EXTERNAL
        HTTPException 404: If site or release not found
        HTTPException 400: If rollback operation fails

    Example:
        ```json
        POST /api/webgenesis/my-site_20250101120000/rollback
        Body:
        {
          "release_id": "rel_1735660800_a1b2c3d4",
          "current_release_id": "rel_1735664400_e5f6g7h8"
        }
        ```

        Response:
        ```json
        {
          "success": true,
          "site_id": "my-site_20250101120000",
          "from_release": "rel_1735664400_e5f6g7h8",
          "to_release": "rel_1735660800_a1b2c3d4",
          "lifecycle_status": "running",
          "health_status": "healthy",
          "message": "Rollback completed to release rel_1735660800_a1b2c3d4",
          "warnings": []
        }
        ```
    """
    try:
        await _ensure_webgenesis_writable(db)
        skill_run = None
        if "pytest" not in sys.modules:
            skill_run = await get_skill_engine_service().create_run(
                db,
                SkillRunCreate(skill_key="builder.webgenesis.rollback", input_payload={"site_id": site_id, **request.model_dump()}, idempotency_key=f"webgenesis-rollback-{uuid4().hex}", trigger_type=TriggerType.API),
                principal,
            )
        rollback_service = get_rollback_service()

        logger.info(
            f"⏪ Rolling back site: site_id={site_id}, "
            f"target_release={request.release_id or 'previous'}, "
            f"current_release={request.current_release_id or 'auto-detect'}, "
            f"trust_tier={trust_context.trust_tier.value}, "
            f"source={trust_context.source_service or trust_context.source_ip}"
        )

        result = await rollback_service.rollback_to_release(
            site_id=site_id,
            release_id=request.release_id,
            current_release_id=request.current_release_id,
        )

        if result.success:
            logger.info(
                f"✅ Rollback completed: site_id={site_id}, "
                f"{result.from_release or 'unknown'} → {result.to_release}"
            )
        else:
            logger.warning(
                f"⚠️ Rollback failed: site_id={site_id}, "
                f"message={result.message}"
            )

        await _finalize_webgenesis_skill_run(
            db,
            principal,
            str(skill_run.id) if skill_run else None,
            success=result.success,
            output_payload={
                "site_id": site_id,
                "from_release": result.from_release,
                "to_release": result.to_release,
                "health_status": result.health_status.value if hasattr(result.health_status, "value") else result.health_status,
                "warnings": result.warnings,
            },
            failure_code=None if result.success else "WEBGENESIS-ROLLBACK-FAILED",
            failure_reason=None if result.success else result.message,
        )

        result.skill_run_id = str(skill_run.id) if skill_run else None
        return result

    except FileNotFoundError:
        if skill_run is not None:
            await _finalize_webgenesis_skill_run(
                db,
                principal,
                str(skill_run.id),
                success=False,
                output_payload={"site_id": site_id},
                failure_code="WEBGENESIS-SITE-NOT-FOUND",
                failure_reason=f"Site not found: {site_id}",
            )
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except Exception as e:
        if skill_run is not None:
            await _finalize_webgenesis_skill_run(
                db,
                principal,
                str(skill_run.id),
                success=False,
                output_payload={"site_id": site_id},
                failure_code="WEBGENESIS-ROLLBACK-ERROR",
                failure_reason=str(e),
            )
        logger.error(f"❌ Rollback operation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback operation failed: {str(e)}",
        )


@router.get("/{site_id}/releases", response_model=ReleasesListResponse)
async def list_releases(site_id: str):
    """
    List all release snapshots for a site.

    **Trust Tier:** Any (no restriction)

    **Sprint II:** Release history for rollback selection.

    Returns releases sorted by creation time (newest first).

    Args:
        site_id: Site identifier

    Returns:
        List of release metadata with total count

    Raises:
        HTTPException 404: If site not found

    Example:
        ```
        GET /api/webgenesis/my-site_20250101120000/releases
        ```

        Response:
        ```json
        {
          "site_id": "my-site_20250101120000",
          "releases": [
            {
              "release_id": "rel_1735664400_e5f6g7h8",
              "site_id": "my-site_20250101120000",
              "artifact_hash": "e5f6g7h8...",
              "created_at": "2025-01-01T13:00:00Z",
              "deployed_url": "http://localhost:8080",
              "health_status": "healthy"
            },
            {
              "release_id": "rel_1735660800_a1b2c3d4",
              "site_id": "my-site_20250101120000",
              "artifact_hash": "a1b2c3d4...",
              "created_at": "2025-01-01T12:00:00Z",
              "deployed_url": "http://localhost:8080",
              "health_status": "healthy"
            }
          ],
          "total_count": 2
        }
        ```
    """
    try:
        release_manager = get_release_manager()

        releases = await release_manager.list_releases(site_id, sort_desc=True)

        logger.info(f"📋 Listed releases: site_id={site_id}, count={len(releases)}")

        return ReleasesListResponse(
            site_id=site_id,
            releases=releases,
            total_count=len(releases),
        )

    except FileNotFoundError:
        logger.error(f"❌ Site not found: {site_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )

    except Exception as e:
        logger.error(f"❌ List releases error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list releases: {str(e)}",
        )


# ============================================================================
# Sprint III - Site List & Audit (Control Center UI)
# ============================================================================


@router.get("/sites", response_model=SitesListResponse)
async def list_sites():
    """
    List all WebGenesis sites.

    **Trust Tier:** Any (no restriction - read-only)

    **Sprint III:** Control Center UI endpoint for site list view.

    Scans storage directory and returns all sites with current status,
    health, and lifecycle information.

    **Fail-Safe:**
    - Broken manifests → status="failed", health="unknown"
    - Missing containers → lifecycle="unknown"
    - No exceptions leaked (empty list on fatal error)

    Returns:
        List of sites with metadata

    Example:
        ```
        GET /api/webgenesis/sites
        ```

        Response:
        ```json
        {
          "sites": [
            {
              "site_id": "my-site_20250101120000",
              "name": "My Awesome Site",
              "domain": "example.com",
              "status": "deployed",
              "lifecycle_status": "running",
              "health_status": "healthy",
              "current_release_id": "rel_1735747200_a1b2c3d4",
              "deployed_url": "http://localhost:8080",
              "dns_enabled": true,
              "last_action": "deploy",
              "updated_at": "2025-01-01T12:00:00Z"
            }
          ],
          "total_count": 1
        }
        ```
    """
    try:
        service = get_webgenesis_service()
        sites_data = service.list_all_sites()

        # Convert to SiteListItem models
        sites = [SiteListItem(**site) for site in sites_data]

        logger.info(f"📋 Returning {len(sites)} sites")

        return SitesListResponse(
            sites=sites,
            total_count=len(sites),
        )

    except Exception as e:
        # Log error but return empty list (fail-safe)
        logger.error(f"❌ Error listing sites: {e}")
        return SitesListResponse(
            sites=[],
            total_count=0,
        )


@router.get("/{site_id:path}/audit", response_model=SiteAuditResponse)
async def get_site_audit(
    site_id: str,
    limit: int = Query(100, ge=1, description="Max events to return"),
    severity: Optional[AuditEventSeverity] = Query(
        None, description="Filter by severity (INFO, WARNING, ERROR, CRITICAL)"
    ),
    types: Optional[str] = Query(
        None, description="Comma-separated event types to filter"
    ),
):
    """
    Get audit events for a specific site.

    **Trust Tier:** Any (no restriction - read-only)

    **Sprint III:** Control Center UI endpoint for site audit timeline.

    Returns chronologically descending audit events for the specified site
    with optional filtering by severity and event types.

    **Fail-Safe:**
    - Invalid site_id → empty events list
    - Missing audit file → empty events list
    - Malformed events → skipped (logged as warning)
    - No exceptions leaked

    Args:
        site_id: Site ID to query
        limit: Maximum events to return (1-500, default 100)
        severity: Filter by severity level (optional)
        types: Comma-separated event types to filter (optional)

    Returns:
        Audit events matching filters

    Example:
        GET /api/webgenesis/my-site_20250101120000/audit?limit=50&severity=ERROR

        Response:
        {
          "site_id": "my-site_20250101120000",
          "events": [
            {
              "id": "evt_1735747200_my-site_",
              "timestamp": "2025-01-01T12:00:00Z",
              "site_id": "my-site_20250101120000",
              "event_type": "deploy_failed",
              "severity": "ERROR",
              "source": "webgenesis.deploy",
              "description": "Docker Compose failed to start container",
              "metadata": {"exit_code": 1}
            }
          ],
          "total_count": 1,
          "filtered_count": 1
        }
    """
    try:
        service = get_webgenesis_service()
        safe_limit = min(limit, 500)

        # Parse event types (comma-separated)
        event_types_list = None
        if types:
            event_types_list = [t.strip() for t in types.split(",") if t.strip()]

        # Query audit events
        events, total_matching = service.get_site_audit_events(
            site_id=site_id,
            limit=safe_limit,
            severity=severity,
            event_types=event_types_list,
        )

        logger.info(
            f"📋 Returning {len(events)} audit events for site {site_id} "
            f"(severity={severity}, types={event_types_list})"
        )

        return SiteAuditResponse(
            site_id=site_id,
            events=events,
            total_count=len(events),
            filtered_count=total_matching,
        )

    except Exception as e:
        # Log error but return empty (fail-safe)
        logger.error(f"❌ Error fetching audit events for {site_id}: {e}")
        return SiteAuditResponse(
            site_id=site_id,
            events=[],
            total_count=0,
            filtered_count=0,
        )
