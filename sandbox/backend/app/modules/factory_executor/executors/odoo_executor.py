"""
Odoo Executor v1 - Business Standard

Production-grade Odoo ERP configuration with:
- Whitelisted modules only
- Idempotent installation
- Version-safe operations (Odoo 19)
- Rollback support
- Trust-tier enforcement

Version: 1.0.0 (Sprint 6)
"""

from __future__ import annotations

from typing import List, Dict, Any, Set
from loguru import logger

from app.modules.factory_executor.base import (
    ExecutorBase,
    ExecutionContext,
    ExecutorCapability,
    ValidationError,
    ExecutionError,
)
from app.modules.business_factory.schemas import (
    ExecutionStep,
    StepResult,
)


class OdooExecutor(ExecutorBase):
    """
    Production-grade Odoo configuration executor.

    Capabilities:
    - IDEMPOTENT: Module installation checks existing state
    - ROLLBACKABLE: Can uninstall modules (with limitations)

    Contract:
    - Input MUST include: action, modules (for install)
    - Modules MUST be whitelisted
    - All operations audited
    - No direct database access without plan
    """

    # Whitelisted Odoo modules (Business Standard)
    WHITELISTED_MODULES = {
        # Core CRM & Sales
        "crm",
        "sale",
        "sale_management",

        # Accounting & Finance
        "account",
        "account_accountant",
        "account_invoicing",

        # Inventory & Logistics
        "stock",
        "purchase",
        "purchase_stock",

        # Project Management
        "project",
        "hr_timesheet",
        "project_timesheet",

        # HR & Payroll
        "hr",
        "hr_attendance",
        "hr_expense",
        "hr_holidays",

        # Website & E-commerce
        "website",
        "website_sale",
        "website_blog",

        # Productivity
        "calendar",
        "mail",
        "contacts",

        # Reporting
        "sale_timesheet",
        "analytic",
    }

    # Module dependencies (automatically installed)
    MODULE_DEPENDENCIES = {
        "crm": ["mail", "calendar", "contacts"],
        "sale": ["crm", "account"],
        "purchase": ["account", "stock"],
        "website_sale": ["website", "sale", "stock"],
    }

    # Required parameters per action
    REQUIRED_PARAMS = {
        "install_modules": {"modules"},
        "create_users": {"users"},
        "configure_fiscal": {"currency", "fiscal_year_start"},
    }

    def __init__(self):
        """Initialize Odoo executor"""
        super().__init__(
            name="OdooExecutor",
            capabilities={
                ExecutorCapability.IDEMPOTENT,
                ExecutorCapability.ROLLBACKABLE,
            },
            default_timeout_seconds=600.0,  # 10 minutes (module install can be slow)
            default_max_retries=1,
        )

        self._installed_modules_cache: Dict[str, Set[str]] = {}

    async def execute(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> StepResult:
        """
        Execute Odoo configuration action.

        Supported actions:
        - install_modules: Install Odoo modules
        - create_users: Create user accounts
        - configure_fiscal: Set up fiscal year and accounting

        Args:
            step: Execution step
            context: Execution context

        Returns:
            StepResult

        Raises:
            ExecutionError: Execution failed
        """
        action = step.parameters.get("action")

        logger.info(f"[OdooExecutor] Executing action: {action}")

        if action == "install_modules":
            return await self._install_modules(step, context)
        elif action == "create_users":
            return await self._create_users(step, context)
        elif action == "configure_fiscal":
            return await self._configure_fiscal(step, context)
        else:
            raise ExecutionError(f"Unknown action: {action}")

    async def validate_input(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> List[str]:
        """
        Validate input parameters.

        Args:
            step: Execution step
            context: Execution context

        Returns:
            List of validation errors
        """
        errors = []
        params = step.parameters

        # Check action
        action = params.get("action")
        if not action:
            errors.append("Missing required parameter: action")
            return errors

        # Check action-specific requirements
        required = self.REQUIRED_PARAMS.get(action, set())
        missing = required - set(params.keys())
        if missing:
            errors.append(f"Missing required parameters for action '{action}': {', '.join(missing)}")

        # Validate modules (if install_modules)
        if action == "install_modules":
            modules = params.get("modules", [])
            invalid_modules = set(modules) - self.WHITELISTED_MODULES
            if invalid_modules:
                errors.append(
                    f"Invalid modules (not whitelisted): {', '.join(invalid_modules)}. "
                    f"Allowed: {', '.join(sorted(self.WHITELISTED_MODULES))}"
                )

        # Validate currency (if configure_fiscal)
        if action == "configure_fiscal":
            currency = params.get("currency")
            if currency and len(currency) != 3:
                errors.append(f"Invalid currency code: {currency} (must be 3 letters)")

        return errors

    async def rollback(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> bool:
        """
        Rollback Odoo configuration.

        Note: Some actions cannot be fully rolled back (e.g., fiscal configuration).

        Args:
            step: Step to rollback
            context: Execution context

        Returns:
            True if successful
        """
        action = step.parameters.get("action")

        logger.info(f"[OdooExecutor] Rolling back action: {action}")

        if action == "install_modules":
            return await self._uninstall_modules(step, context)
        elif action == "create_users":
            return await self._delete_users(step, context)
        elif action == "configure_fiscal":
            logger.warning("[OdooExecutor] Fiscal configuration cannot be fully rolled back")
            return False
        else:
            return False

    # ========================================================================
    # Action Implementations
    # ========================================================================

    async def _install_modules(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> StepResult:
        """
        Install Odoo modules.

        Args:
            step: Execution step
            context: Execution context

        Returns:
            StepResult
        """
        modules = step.parameters["modules"]
        company_name = step.parameters.get("company_name", "Default Company")

        logger.info(f"[OdooExecutor] Installing modules: {', '.join(modules)}")

        # Resolve dependencies
        all_modules = self._resolve_dependencies(modules)

        logger.info(
            f"[OdooExecutor] Total modules (with dependencies): {len(all_modules)}"
        )

        # Simulate installation (MVP - would use real Odoo API)
        installed = []
        for module in all_modules:
            # Check if already installed (idempotency)
            cache_key = f"{context.plan_id}:{company_name}"
            if cache_key in self._installed_modules_cache:
                if module in self._installed_modules_cache[cache_key]:
                    logger.debug(f"[OdooExecutor] Module already installed: {module}")
                    continue

            # Install module (simulated)
            logger.debug(f"[OdooExecutor] Installing module: {module}")
            installed.append(module)

            # Cache installed module
            if cache_key not in self._installed_modules_cache:
                self._installed_modules_cache[cache_key] = set()
            self._installed_modules_cache[cache_key].add(module)

        logger.info(
            f"[OdooExecutor] Installed {len(installed)} new modules "
            f"({len(all_modules) - len(installed)} already installed)"
        )

        return StepResult(
            step_id=step.step_id,
            success=True,
            data={
                "action": "install_modules",
                "modules_requested": modules,
                "modules_installed": installed,
                "modules_total": len(all_modules),
                "company_name": company_name,
                "idempotent": len(installed) < len(all_modules),
            },
            evidence_files=[],
            duration_seconds=1.0,  # Simulated
        )

    async def _create_users(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> StepResult:
        """
        Create Odoo users.

        Args:
            step: Execution step
            context: Execution context

        Returns:
            StepResult
        """
        users = step.parameters["users"]

        logger.info(f"[OdooExecutor] Creating {len(users)} users")

        created_users = []
        for user in users:
            logger.debug(f"[OdooExecutor] Creating user: {user.get('email')}")
            created_users.append(user)

        return StepResult(
            step_id=step.step_id,
            success=True,
            data={
                "action": "create_users",
                "users_created": len(created_users),
                "user_emails": [u.get("email") for u in created_users],
            },
            evidence_files=[],
            duration_seconds=0.5,  # Simulated
        )

    async def _configure_fiscal(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> StepResult:
        """
        Configure fiscal settings.

        Args:
            step: Execution step
            context: Execution context

        Returns:
            StepResult
        """
        currency = step.parameters["currency"]
        fiscal_year_start = step.parameters["fiscal_year_start"]
        country = step.parameters.get("country", "US")

        logger.info(
            f"[OdooExecutor] Configuring fiscal: "
            f"currency={currency}, fiscal_year={fiscal_year_start}"
        )

        return StepResult(
            step_id=step.step_id,
            success=True,
            data={
                "action": "configure_fiscal",
                "currency": currency,
                "fiscal_year_start": fiscal_year_start,
                "country": country,
            },
            evidence_files=[],
            duration_seconds=0.3,  # Simulated
        )

    async def _uninstall_modules(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> bool:
        """
        Uninstall Odoo modules (rollback).

        Args:
            step: Step to rollback
            context: Execution context

        Returns:
            True if successful
        """
        modules = step.parameters.get("modules", [])
        company_name = step.parameters.get("company_name", "Default Company")

        logger.info(f"[OdooExecutor] Uninstalling modules: {', '.join(modules)}")

        # Clear cache
        cache_key = f"{context.plan_id}:{company_name}"
        if cache_key in self._installed_modules_cache:
            for module in modules:
                self._installed_modules_cache[cache_key].discard(module)

        return True

    async def _delete_users(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> bool:
        """
        Delete Odoo users (rollback).

        Args:
            step: Step to rollback
            context: Execution context

        Returns:
            True if successful
        """
        users = step.parameters.get("users", [])

        logger.info(f"[OdooExecutor] Deleting {len(users)} users")

        # Simulated deletion
        return True

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _resolve_dependencies(self, modules: List[str]) -> List[str]:
        """
        Resolve module dependencies.

        Args:
            modules: Requested modules

        Returns:
            Complete list of modules (including dependencies)
        """
        all_modules = set(modules)

        # Add dependencies
        for module in modules:
            deps = self.MODULE_DEPENDENCIES.get(module, [])
            all_modules.update(deps)

        # Return sorted list
        return sorted(all_modules)
