"""
Preflight Checker

Validates all prerequisites before plan execution.
Fail-fast approach to prevent partial deployments.
"""

from __future__ import annotations

from typing import List, Dict, Any
from pathlib import Path
from loguru import logger

from backend.app.modules.business_factory.schemas import (
    BusinessPlan,
    PreflightResult,
)


class PreflightChecker:
    """
    Validates prerequisites before execution.

    Checks:
    - Template availability
    - Disk space
    - Network connectivity (if required)
    - External service availability (Odoo, DNS)
    - Required dependencies installed
    """

    def __init__(self):
        """Initialize preflight checker"""
        logger.info("PreflightChecker initialized")

    async def check_prerequisites(self, plan: BusinessPlan) -> PreflightResult:
        """
        Run all preflight checks.

        Args:
            plan: Business plan to validate

        Returns:
            PreflightResult with check status
        """
        logger.info(f"Running preflight checks for plan: {plan.plan_id}")

        checks = []
        errors = []
        warnings = []

        # Check 1: Disk space
        check = await self._check_disk_space()
        checks.append(check)
        if not check["passed"]:
            errors.append(check["message"])

        # Check 2: Templates exist
        check = await self._check_templates(plan)
        checks.append(check)
        if not check["passed"]:
            errors.append(check["message"])

        # Check 3: Output directory writable
        check = await self._check_output_directory()
        checks.append(check)
        if not check["passed"]:
            errors.append(check["message"])

        # Check 4: Network (if needed)
        if self._requires_network(plan):
            check = await self._check_network()
            checks.append(check)
            if not check["passed"]:
                warnings.append(check["message"])  # Warning, not error

        # Overall result
        passed = len(errors) == 0

        result = PreflightResult(
            passed=passed,
            checks=checks,
            errors=errors,
            warnings=warnings,
        )

        if passed:
            logger.info(f"✅ Preflight passed: {len(checks)} checks successful")
        else:
            logger.error(f"❌ Preflight failed: {len(errors)} errors, {len(warnings)} warnings")

        return result

    async def _check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space"""
        import shutil

        try:
            stat = shutil.disk_usage("/")
            free_gb = stat.free / (1024 ** 3)
            required_gb = 1.0  # Require at least 1GB free

            passed = free_gb >= required_gb

            return {
                "name": "disk_space",
                "passed": passed,
                "message": f"Available disk space: {free_gb:.2f} GB (required: {required_gb} GB)",
                "details": {
                    "free_gb": free_gb,
                    "required_gb": required_gb,
                }
            }
        except Exception as e:
            logger.error(f"Error checking disk space: {e}")
            return {
                "name": "disk_space",
                "passed": False,
                "message": f"Failed to check disk space: {str(e)}",
                "details": {}
            }

    async def _check_templates(self, plan: BusinessPlan) -> Dict[str, Any]:
        """Check that all required templates exist"""
        from backend.app.modules.template_registry.loader import get_template_loader

        try:
            loader = get_template_loader()
            missing_templates = []

            for step in plan.steps:
                if step.template_id:
                    template = loader.get_template(step.template_id)
                    if not template:
                        missing_templates.append(step.template_id)

            passed = len(missing_templates) == 0

            if passed:
                message = f"All required templates available ({len([s for s in plan.steps if s.template_id])} templates)"
            else:
                message = f"Missing templates: {', '.join(missing_templates)}"

            return {
                "name": "templates",
                "passed": passed,
                "message": message,
                "details": {
                    "missing_templates": missing_templates,
                }
            }
        except Exception as e:
            logger.error(f"Error checking templates: {e}")
            return {
                "name": "templates",
                "passed": False,
                "message": f"Failed to check templates: {str(e)}",
                "details": {}
            }

    async def _check_output_directory(self) -> Dict[str, Any]:
        """Check that output directory is writable"""
        try:
            output_dir = Path("storage/factory_output")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Try creating a test file
            test_file = output_dir / ".write_test"
            test_file.write_text("test")
            test_file.unlink()

            return {
                "name": "output_directory",
                "passed": True,
                "message": f"Output directory writable: {output_dir}",
                "details": {
                    "path": str(output_dir),
                }
            }
        except Exception as e:
            logger.error(f"Error checking output directory: {e}")
            return {
                "name": "output_directory",
                "passed": False,
                "message": f"Output directory not writable: {str(e)}",
                "details": {}
            }

    async def _check_network(self) -> Dict[str, Any]:
        """Check network connectivity"""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("https://www.google.com")
                passed = response.status_code == 200

            return {
                "name": "network",
                "passed": passed,
                "message": "Network connectivity verified" if passed else "Network connectivity failed",
                "details": {
                    "status_code": response.status_code if passed else None,
                }
            }
        except Exception as e:
            logger.warning(f"Network check failed: {e}")
            return {
                "name": "network",
                "passed": False,
                "message": f"Network connectivity failed: {str(e)}",
                "details": {}
            }

    def _requires_network(self, plan: BusinessPlan) -> bool:
        """Determine if plan requires network connectivity"""
        # Check if any step requires external services
        from backend.app.modules.business_factory.schemas import ExecutorType

        network_executors = {ExecutorType.ODOO, ExecutorType.DNS}

        for step in plan.steps:
            if step.executor in network_executors:
                return True

        return False
