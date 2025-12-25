"""
Business Planner

Generates execution plans from business briefings.
Converts high-level business requirements into concrete, ordered execution steps.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from loguru import logger

from backend.app.modules.business_factory.schemas import (
    BusinessBriefing,
    BusinessPlan,
    ExecutionStep,
    BusinessType,
    ExecutorType,
    StepStatus,
)
from backend.app.modules.business_factory.risk_assessor import RiskAssessor


class BusinessPlanner:
    """
    Generates execution plans from business briefings.

    Responsibilities:
    1. Parse briefing requirements
    2. Select appropriate templates based on business_type
    3. Generate ordered execution steps with dependencies
    4. Build complete BusinessPlan
    5. Integrate risk assessment
    """

    def __init__(self):
        """Initialize business planner"""
        self.risk_assessor = RiskAssessor()
        logger.info("BusinessPlanner initialized")

    async def generate_plan(self, briefing: BusinessBriefing) -> BusinessPlan:
        """
        Generate complete execution plan from briefing.

        Args:
            briefing: Business briefing with requirements

        Returns:
            Complete BusinessPlan ready for validation/execution

        Raises:
            ValueError: If briefing is invalid or cannot generate plan
        """
        logger.info(
            f"Generating plan for business: {briefing.business_name} "
            f"(type={briefing.business_type})"
        )

        try:
            # Create base plan
            plan = BusinessPlan(
                briefing_id=briefing.briefing_id,
                business_name=briefing.business_name,
                business_type=briefing.business_type,
                created_by=briefing.created_by,
            )

            # Generate steps based on business type and requirements
            steps = self._generate_steps(briefing)

            # Add dependency relationships
            steps = self._build_dependencies(steps)

            # Add to plan
            plan.steps = steps
            plan.steps_total = len(steps)

            # Perform risk assessment
            risk_assessment = await self.risk_assessor.assess(plan, briefing)
            plan.risk_assessment = risk_assessment

            # Update statistics
            plan.update_statistics()

            logger.info(
                f"Plan generated successfully: {plan.plan_id} "
                f"({plan.steps_total} steps, risk={risk_assessment.overall_risk_level})"
            )

            return plan

        except Exception as e:
            logger.error(f"Error generating plan for {briefing.business_name}: {e}")
            raise ValueError(f"Failed to generate plan: {str(e)}")

    def _generate_steps(self, briefing: BusinessBriefing) -> List[ExecutionStep]:
        """
        Generate execution steps based on briefing requirements.

        Step Generation Strategy:
        1. Website generation steps (if website_config provided)
        2. ERP deployment steps (if erp_config provided)
        3. Integration configuration steps (if integrations provided)
        4. Validation/testing steps

        Args:
            briefing: Business briefing

        Returns:
            List of execution steps (ordered)
        """
        steps: List[ExecutionStep] = []
        sequence = 1

        # ====================================================================
        # Phase 1: Website Generation
        # ====================================================================
        if briefing.website_config:
            # Step 1: Generate website from template
            steps.append(ExecutionStep(
                sequence=sequence,
                name="Generate Website",
                description=f"Generate {briefing.business_name} website from template '{briefing.website_config.template}'",
                executor=ExecutorType.WEBGEN,
                template_id=briefing.website_config.template,
                parameters={
                    "business_name": briefing.business_name,
                    "domain": briefing.website_config.domain,
                    "pages": briefing.website_config.pages,
                    "features": briefing.website_config.features,
                    "primary_color": briefing.website_config.primary_color,
                    "secondary_color": briefing.website_config.secondary_color,
                    "logo_url": briefing.website_config.logo_url,
                    "tagline": briefing.website_config.tagline,
                    "description": briefing.website_config.description,
                },
                rollback_possible=True,
                rollback_steps=[
                    {"action": "delete_generated_files", "reason": "cleanup_on_failure"}
                ]
            ))
            sequence += 1

            # Step 2: Deploy website
            steps.append(ExecutionStep(
                sequence=sequence,
                name="Deploy Website",
                description=f"Deploy website to {briefing.website_config.domain}",
                executor=ExecutorType.WEBGEN,
                parameters={
                    "domain": briefing.website_config.domain,
                    "deployment_target": "nginx",  # Could be configurable
                },
                depends_on=[steps[0].step_id] if steps else [],
                rollback_possible=True,
                rollback_steps=[
                    {"action": "remove_nginx_config"},
                    {"action": "delete_deployed_files"},
                ]
            ))
            sequence += 1

            # Step 3: Configure DNS (if not dry_run)
            if not briefing.dry_run:
                steps.append(ExecutionStep(
                    sequence=sequence,
                    name="Configure DNS",
                    description=f"Set up DNS records for {briefing.website_config.domain}",
                    executor=ExecutorType.DNS,
                    parameters={
                        "domain": briefing.website_config.domain,
                        "record_type": "A",
                        "target": "auto",  # Determines server IP automatically
                    },
                    depends_on=[steps[-1].step_id] if steps else [],
                    rollback_possible=True,
                    rollback_steps=[
                        {"action": "remove_dns_records"}
                    ]
                ))
                sequence += 1

        # ====================================================================
        # Phase 2: ERP Deployment
        # ====================================================================
        if briefing.erp_config:
            # Step: Install Odoo modules
            steps.append(ExecutionStep(
                sequence=sequence,
                name="Install Odoo Modules",
                description=f"Install Odoo modules: {', '.join(briefing.erp_config.modules)}",
                executor=ExecutorType.ODOO,
                parameters={
                    "action": "install_modules",
                    "modules": briefing.erp_config.modules,
                    "company_name": briefing.erp_config.company_name or briefing.business_name,
                    "currency": briefing.erp_config.currency,
                    "language": briefing.erp_config.language,
                    "timezone": briefing.erp_config.timezone,
                },
                # Only depends on website if website was created
                depends_on=[steps[-1].step_id] if briefing.website_config and steps else [],
                rollback_possible=True,
                rollback_steps=[
                    {"action": "uninstall_modules", "modules": briefing.erp_config.modules}
                ]
            ))
            sequence += 1

            # Step: Configure Odoo users
            if briefing.erp_config.users:
                steps.append(ExecutionStep(
                    sequence=sequence,
                    name="Create Odoo Users",
                    description=f"Create {len(briefing.erp_config.users)} Odoo users",
                    executor=ExecutorType.ODOO,
                    parameters={
                        "action": "create_users",
                        "users": briefing.erp_config.users,
                    },
                    depends_on=[steps[-1].step_id] if steps else [],
                    rollback_possible=True,
                    rollback_steps=[
                        {"action": "delete_users", "user_emails": [u.get("email") for u in briefing.erp_config.users]}
                    ]
                ))
                sequence += 1

            # Step: Configure fiscal settings
            steps.append(ExecutionStep(
                sequence=sequence,
                name="Configure Fiscal Settings",
                description="Set up fiscal year, accounting, and localization",
                executor=ExecutorType.ODOO,
                parameters={
                    "action": "configure_fiscal",
                    "fiscal_year_start": briefing.erp_config.fiscal_year_start,
                    "currency": briefing.erp_config.currency,
                    "country": briefing.country,
                },
                depends_on=[steps[-1].step_id] if steps else [],
                rollback_possible=False,  # Fiscal config changes are hard to rollback
            ))
            sequence += 1

        # ====================================================================
        # Phase 3: Integrations
        # ====================================================================
        for integration in briefing.integrations:
            if not integration.enabled:
                continue

            steps.append(ExecutionStep(
                sequence=sequence,
                name=f"Configure Integration: {integration.name}",
                description=f"Set up {integration.source} → {integration.target} integration ({integration.type})",
                executor=ExecutorType.INTEGRATION,
                parameters={
                    "integration_name": integration.name,
                    "source": integration.source,
                    "target": integration.target,
                    "type": integration.type,
                    "config": integration.config,
                },
                # Integrations depend on both systems being ready
                depends_on=self._get_integration_dependencies(steps, integration, briefing),
                rollback_possible=True,
                rollback_steps=[
                    {"action": "remove_integration", "integration_name": integration.name}
                ]
            ))
            sequence += 1

        # ====================================================================
        # Phase 4: Validation & Testing
        # ====================================================================
        # Final validation step to verify everything works
        steps.append(ExecutionStep(
            sequence=sequence,
            name="Final Validation",
            description="Validate all components and integrations are working",
            executor=ExecutorType.VALIDATION,
            parameters={
                "checks": [
                    "website_accessible",
                    "odoo_accessible",
                    "integrations_functional",
                ]
            },
            # Depends on all previous steps
            depends_on=[step.step_id for step in steps],
            rollback_possible=False,  # Validation doesn't modify state
        ))

        return steps

    def _build_dependencies(self, steps: List[ExecutionStep]) -> List[ExecutionStep]:
        """
        Build dependency graph for steps.
        Already done in _generate_steps, but this can add additional logic if needed.

        Args:
            steps: List of execution steps

        Returns:
            Steps with updated dependencies
        """
        # Dependencies are already set during generation
        # This method is a hook for future enhancements (e.g., parallel step detection)
        return steps

    def _get_integration_dependencies(
        self,
        existing_steps: List[ExecutionStep],
        integration: Any,
        briefing: BusinessBriefing
    ) -> List[str]:
        """
        Determine which steps an integration depends on.

        Args:
            existing_steps: Steps generated so far
            integration: Integration requirement
            briefing: Original briefing

        Returns:
            List of step IDs this integration depends on
        """
        deps = []

        # If integration involves website, depend on website deployment
        if integration.source == "website" or integration.target == "website":
            if briefing.website_config:
                # Find the deploy website step
                for step in existing_steps:
                    if step.executor == ExecutorType.WEBGEN and "Deploy" in step.name:
                        deps.append(step.step_id)
                        break

        # If integration involves Odoo, depend on Odoo module installation
        if integration.source == "odoo" or integration.target == "odoo":
            if briefing.erp_config:
                # Find the install modules step
                for step in existing_steps:
                    if step.executor == ExecutorType.ODOO and "Install" in step.name:
                        deps.append(step.step_id)
                        break

        return deps

    def validate_briefing(self, briefing: BusinessBriefing) -> tuple[bool, List[str]]:
        """
        Validate briefing before generating plan.

        Args:
            briefing: Business briefing to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required configs
        if not briefing.website_config and not briefing.erp_config:
            errors.append("At least one of website_config or erp_config must be provided")

        # Check domain format
        if briefing.website_config:
            domain = briefing.website_config.domain
            if not domain or "." not in domain:
                errors.append(f"Invalid domain: {domain}")

        # Check Odoo modules
        if briefing.erp_config:
            valid_modules = {
                "crm", "sales", "accounting", "inventory", "purchase",
                "projects", "timesheets", "invoicing", "hr", "website",
            }
            invalid_modules = set(briefing.erp_config.modules) - valid_modules
            if invalid_modules:
                errors.append(f"Invalid Odoo modules: {', '.join(invalid_modules)}")

        # Check integrations
        for integration in briefing.integrations:
            if integration.source == integration.target:
                errors.append(f"Integration {integration.name}: source and target cannot be the same")

        return len(errors) == 0, errors
