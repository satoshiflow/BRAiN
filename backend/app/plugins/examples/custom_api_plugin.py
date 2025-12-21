"""
Custom API Plugin Example

Example plugin that adds custom API endpoints to BRAiN.

This plugin:
- Demonstrates APIPlugin implementation
- Shows how to add custom endpoints
- Integrates with FastAPI routing
- Provides custom business logic

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from backend.app.plugins.base import APIPlugin, PluginMetadata, PluginType


# ============================================================================
# API Models
# ============================================================================

class CalculateRequest(BaseModel):
    """Calculate request model."""

    operation: str = Field(..., description="Operation: add, subtract, multiply, divide")
    operand1: float = Field(..., description="First operand")
    operand2: float = Field(..., description="Second operand")


class CalculateResponse(BaseModel):
    """Calculate response model."""

    result: float = Field(..., description="Calculation result")
    operation: str = Field(..., description="Operation performed")


class PluginStatusResponse(BaseModel):
    """Plugin status response."""

    plugin_id: str = Field(..., description="Plugin identifier")
    status: str = Field(..., description="Plugin status")
    requests_processed: int = Field(..., description="Total requests processed")


# ============================================================================
# Calculator API Plugin
# ============================================================================

class CalculatorAPIPlugin(APIPlugin):
    """
    Plugin that provides calculator API endpoints.

    Adds custom /api/calculator endpoints to BRAiN.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize plugin."""
        super().__init__(config)

        self.router = APIRouter()
        self.requests_processed = 0

        # Register routes
        self._register_routes()

    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            id="calculator_api_plugin",
            name="Calculator API Plugin",
            version="1.0.0",
            description="Adds calculator API endpoints for mathematical operations",
            author="BRAiN Team",
            plugin_type=PluginType.API,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "enable_advanced_operations": {
                        "type": "boolean",
                        "default": False,
                        "description": "Enable advanced math operations (power, sqrt, etc.)",
                    },
                    "max_operand_value": {
                        "type": "number",
                        "default": 1000000,
                        "description": "Maximum allowed operand value",
                    },
                },
            },
        )

    async def on_load(self):
        """Called when plugin is loaded."""
        logger.info("CalculatorAPIPlugin loaded")

    async def on_enable(self):
        """Called when plugin is enabled."""
        logger.info("CalculatorAPIPlugin enabled")

        enable_advanced = self.get_config("enable_advanced_operations", False)
        logger.info(f"Advanced operations: {'enabled' if enable_advanced else 'disabled'}")

    async def on_disable(self):
        """Called when plugin is disabled."""
        logger.info(f"CalculatorAPIPlugin disabled (processed {self.requests_processed} requests)")

    def get_router(self) -> APIRouter:
        """
        Get FastAPI router.

        Returns:
            APIRouter instance
        """
        return self.router

    def get_prefix(self) -> str:
        """
        Get API route prefix.

        Returns:
            Route prefix
        """
        return "/api/calculator"

    def get_tags(self) -> List[str]:
        """
        Get API route tags.

        Returns:
            Route tags
        """
        return ["calculator", "plugin"]

    # ========================================================================
    # Route Registration
    # ========================================================================

    def _register_routes(self):
        """Register API routes."""

        @self.router.post("/calculate", response_model=CalculateResponse)
        async def calculate(request: CalculateRequest) -> CalculateResponse:
            """
            Perform calculation.

            **Request Body:**
            - operation: add, subtract, multiply, divide
            - operand1: First number
            - operand2: Second number

            **Returns:**
            - Calculation result
            """
            # Increment request counter
            self.requests_processed += 1

            # Validate operands
            max_value = self.get_config("max_operand_value", 1000000)
            if abs(request.operand1) > max_value or abs(request.operand2) > max_value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Operand exceeds maximum allowed value: {max_value}",
                )

            # Perform operation
            try:
                if request.operation == "add":
                    result = request.operand1 + request.operand2
                elif request.operation == "subtract":
                    result = request.operand1 - request.operand2
                elif request.operation == "multiply":
                    result = request.operand1 * request.operand2
                elif request.operation == "divide":
                    if request.operand2 == 0:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Division by zero",
                        )
                    result = request.operand1 / request.operand2
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unknown operation: {request.operation}",
                    )

                logger.info(
                    f"Calculated: {request.operand1} {request.operation} "
                    f"{request.operand2} = {result}"
                )

                return CalculateResponse(
                    result=result,
                    operation=request.operation,
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Calculation error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Calculation failed: {str(e)}",
                )

        @self.router.get("/status", response_model=PluginStatusResponse)
        async def get_status() -> PluginStatusResponse:
            """
            Get plugin status.

            **Returns:**
            - Plugin status and statistics
            """
            return PluginStatusResponse(
                plugin_id=self.get_metadata().id,
                status=self.get_status().value,
                requests_processed=self.requests_processed,
            )

        @self.router.get("/operations")
        async def list_operations() -> List[str]:
            """
            List available operations.

            **Returns:**
            - List of supported operations
            """
            operations = ["add", "subtract", "multiply", "divide"]

            # Add advanced operations if enabled
            if self.get_config("enable_advanced_operations", False):
                operations.extend(["power", "sqrt", "log"])

            return operations


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    # Example: Testing the plugin routes
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import asyncio

    async def main():
        # Create plugin
        plugin = CalculatorAPIPlugin(config={
            "enable_advanced_operations": True,
            "max_operand_value": 1000000,
        })

        # Load and enable
        await plugin.on_load()
        await plugin.on_enable()

        # Create FastAPI app
        app = FastAPI()

        # Include plugin router
        router = plugin.get_router()
        app.include_router(router, prefix=plugin.get_prefix(), tags=plugin.get_tags())

        # Create test client
        client = TestClient(app)

        # Test calculate endpoint
        response = client.post(
            "/api/calculator/calculate",
            json={
                "operation": "add",
                "operand1": 10,
                "operand2": 5,
            },
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

        # Test status endpoint
        response = client.get("/api/calculator/status")
        print(f"Status: {response.json()}")

        # Test operations endpoint
        response = client.get("/api/calculator/operations")
        print(f"Operations: {response.json()}")

        # Disable plugin
        await plugin.on_disable()

    # Run example
    asyncio.run(main())
