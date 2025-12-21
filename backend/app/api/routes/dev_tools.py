"""
Developer Tools API Routes

API endpoints for development utilities.

Endpoints:
    POST /api/dev/generate-client  - Generate TypeScript API client
    POST /api/dev/test-data         - Generate test data
    GET /api/dev/performance        - Get performance report
    POST /api/dev/performance/reset - Reset performance metrics
    GET /api/dev/schema             - Get enhanced OpenAPI schema

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from backend.app.core.security import Principal, require_admin
from backend.app.dev_tools.api_client_generator import generate_typescript_client
from backend.app.dev_tools.profiler import (
    generate_performance_report,
    get_db_profiler,
    get_metrics,
)
from backend.app.dev_tools.test_data_generator import (
    generate_agents,
    generate_audit_logs,
    generate_missions,
    generate_tasks,
    generate_users,
)

router = APIRouter(prefix="/api/dev", tags=["dev-tools"])


# ============================================================================
# Request/Response Models
# ============================================================================

class GenerateClientRequest(BaseModel):
    """Generate API client request."""

    format: str = Field(default="typescript", description="Client format (typescript)")
    output_path: Optional[str] = Field(None, description="Output directory path")


class GenerateTestDataRequest(BaseModel):
    """Generate test data request."""

    missions: int = Field(default=10, ge=1, le=1000, description="Number of missions")
    agents: int = Field(default=5, ge=1, le=100, description="Number of agents")
    users: int = Field(default=10, ge=1, le=100, description="Number of users")
    audit_logs: int = Field(default=50, ge=1, le=10000, description="Number of audit logs")
    tasks: int = Field(default=20, ge=1, le=1000, description="Number of tasks")


class PerformanceReportResponse(BaseModel):
    """Performance report response."""

    endpoints: Dict[str, Any] = Field(..., description="Endpoint statistics")
    slow_requests: List[Dict[str, Any]] = Field(..., description="Slow requests")
    database: Dict[str, Any] = Field(..., description="Database statistics")
    slow_queries: List[Dict[str, Any]] = Field(..., description="Slow queries")
    timestamp: float = Field(..., description="Report timestamp")


# ============================================================================
# API Client Generation
# ============================================================================

@router.post("/generate-client", status_code=status.HTTP_201_CREATED)
async def generate_api_client(
    request: GenerateClientRequest,
    principal: Principal = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Generate TypeScript API client from OpenAPI schema.

    **Permissions:** Admin only

    **Args:**
    - format: Client format (currently only "typescript" supported)
    - output_path: Optional output directory (default: frontend/generated)

    **Returns:**
    - Generation status and file paths

    **Example:**
    ```json
    {
        "format": "typescript",
        "output_path": "frontend/generated"
    }
    ```
    """
    if request.format != "typescript":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {request.format}. Only 'typescript' is supported.",
        )

    try:
        # Import app to get routes
        from main import app

        # Get OpenAPI schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # Determine output path
        if request.output_path:
            output_path = Path(request.output_path)
        else:
            backend_path = Path(__file__).parent.parent.parent.parent
            output_path = backend_path.parent / "frontend" / "generated"

        # Generate client
        generate_typescript_client(openapi_schema, output_path)

        return {
            "status": "generated",
            "format": request.format,
            "output_path": str(output_path),
            "files": [
                str(output_path / "types.ts"),
                str(output_path / "api.ts"),
                str(output_path / "index.ts"),
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate client: {str(e)}",
        )


# ============================================================================
# Test Data Generation
# ============================================================================

@router.post("/test-data", status_code=status.HTTP_201_CREATED)
async def generate_test_data(
    request: GenerateTestDataRequest,
    principal: Principal = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Generate test data for development and testing.

    **Permissions:** Admin only

    **Args:**
    - missions: Number of test missions to generate
    - agents: Number of test agents to generate
    - users: Number of test users to generate
    - audit_logs: Number of test audit logs to generate
    - tasks: Number of test tasks to generate

    **Returns:**
    - Generated test data

    **Example:**
    ```json
    {
        "missions": 20,
        "agents": 5,
        "users": 10
    }
    ```
    """
    try:
        data = {
            "missions": generate_missions(request.missions),
            "agents": generate_agents(request.agents),
            "users": generate_users(request.users),
            "audit_logs": generate_audit_logs(request.audit_logs),
            "tasks": generate_tasks(request.tasks),
        }

        return {
            "status": "generated",
            "counts": {
                "missions": len(data["missions"]),
                "agents": len(data["agents"]),
                "users": len(data["users"]),
                "audit_logs": len(data["audit_logs"]),
                "tasks": len(data["tasks"]),
            },
            "data": data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test data: {str(e)}",
        )


# ============================================================================
# Performance Profiling
# ============================================================================

@router.get("/performance", response_model=PerformanceReportResponse)
async def get_performance_report(
    principal: Principal = Depends(require_admin),
) -> PerformanceReportResponse:
    """
    Get performance profiling report.

    **Permissions:** Admin only

    **Returns:**
    - Endpoint performance statistics
    - Slow request list
    - Database query statistics
    - Slow query list

    **Note:** Performance tracking must be enabled for data to be available.
    """
    try:
        report = generate_performance_report()
        return PerformanceReportResponse(**report)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate performance report: {str(e)}",
        )


@router.post("/performance/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_performance_metrics(
    principal: Principal = Depends(require_admin),
):
    """
    Reset performance profiling metrics.

    **Permissions:** Admin only

    Clears all collected performance data including:
    - Endpoint timing metrics
    - Slow request tracking
    - Database query metrics
    """
    try:
        metrics = get_metrics()
        metrics.reset()

        db_profiler = get_db_profiler()
        db_profiler.reset()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset metrics: {str(e)}",
        )


@router.get("/performance/endpoints/{endpoint}")
async def get_endpoint_performance(
    endpoint: str,
    principal: Principal = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Get performance statistics for specific endpoint.

    **Permissions:** Admin only

    **Args:**
    - endpoint: Endpoint path (e.g., "GET /api/missions")

    **Returns:**
    - Endpoint performance statistics including percentiles
    """
    metrics = get_metrics()
    stats = metrics.get_stats(endpoint)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No metrics found for endpoint: {endpoint}",
        )

    return stats


# ============================================================================
# OpenAPI Schema
# ============================================================================

@router.get("/schema")
async def get_enhanced_schema() -> Dict[str, Any]:
    """
    Get enhanced OpenAPI schema.

    Returns OpenAPI 3.0 schema with additional metadata and examples.

    **Note:** This is the same schema used to generate API clients.
    """
    try:
        from main import app

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        return openapi_schema

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate schema: {str(e)}",
        )


@router.get("/schema/download")
async def download_schema(
    format: str = Query("json", description="Schema format (json, yaml)"),
) -> FileResponse:
    """
    Download OpenAPI schema file.

    **Args:**
    - format: File format (json or yaml)

    **Returns:**
    - OpenAPI schema file
    """
    from main import app

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    if format == "json":
        # Save to temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(openapi_schema, f, indent=2)
            temp_path = f.name

        return FileResponse(
            temp_path,
            media_type="application/json",
            filename="openapi.json",
        )

    elif format == "yaml":
        import tempfile
        import yaml

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(openapi_schema, f, default_flow_style=False)
            temp_path = f.name

        return FileResponse(
            temp_path,
            media_type="application/x-yaml",
            filename="openapi.yaml",
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {format}. Use 'json' or 'yaml'.",
        )


# ============================================================================
# System Info Endpoint
# ============================================================================

@router.get("/info")
async def get_dev_tools_info() -> Dict[str, Any]:
    """
    Get developer tools information.

    **Returns:**
    - Available dev tools and their capabilities
    """
    return {
        "name": "BRAiN Developer Tools",
        "version": "1.0.0",
        "tools": {
            "api_client_generator": {
                "description": "Generate TypeScript API client from OpenAPI schema",
                "formats": ["typescript"],
                "endpoint": "POST /api/dev/generate-client",
            },
            "test_data_generator": {
                "description": "Generate realistic test data for development",
                "types": ["missions", "agents", "users", "audit_logs", "tasks"],
                "endpoint": "POST /api/dev/test-data",
            },
            "performance_profiler": {
                "description": "Profile API endpoint and database performance",
                "features": ["endpoint_timing", "slow_requests", "db_queries"],
                "endpoint": "GET /api/dev/performance",
            },
            "openapi_schema": {
                "description": "Enhanced OpenAPI 3.0 schema",
                "formats": ["json", "yaml"],
                "endpoint": "GET /api/dev/schema",
            },
        },
    }


# ============================================================================
# Exports
# ============================================================================

__all__ = ["router"]
