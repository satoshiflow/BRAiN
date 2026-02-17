"""
Risk Assessor

Analyzes business plans for potential risks, resource requirements, and timing.
Provides actionable insights before execution.
"""

from __future__ import annotations

from typing import List, Dict, Any
from loguru import logger

from app.modules.business_factory.schemas import (
    BusinessPlan,
    BusinessBriefing,
    RiskAssessment,
    Risk,
    RiskLevel,
    ExecutorType,
)


class RiskAssessor:
    """
    Assesses risks and resource requirements for business plans.

    Responsibilities:
    1. Analyze each step for potential issues
    2. Calculate resource requirements (time, disk, network)
    3. Estimate costs
    4. Identify critical dependencies
    5. Generate mitigation strategies
    """

    # Step duration estimates (minutes)
    STEP_DURATIONS = {
        ExecutorType.WEBGEN: 5,      # Website generation: ~5 min
        ExecutorType.ODOO: 10,        # Odoo operations: ~10 min
        ExecutorType.INTEGRATION: 3,  # Integration setup: ~3 min
        ExecutorType.VALIDATION: 2,   # Validation: ~2 min
        ExecutorType.DNS: 1,          # DNS config: ~1 min (excluding propagation)
    }

    # Cost estimates (EUR)
    STEP_COSTS = {
        ExecutorType.WEBGEN: 0.0,      # Internal, no cost
        ExecutorType.ODOO: 0.0,        # Internal, no cost
        ExecutorType.INTEGRATION: 0.0,  # Internal, no cost
        ExecutorType.VALIDATION: 0.0,   # Internal, no cost
        ExecutorType.DNS: 0.0,          # Could add DNS provider costs
    }

    def __init__(self):
        """Initialize risk assessor"""
        logger.info("RiskAssessor initialized")

    async def assess(
        self,
        plan: BusinessPlan,
        briefing: BusinessBriefing
    ) -> RiskAssessment:
        """
        Perform comprehensive risk assessment on business plan.

        Args:
            plan: Business plan to assess
            briefing: Original briefing for context

        Returns:
            Complete risk assessment
        """
        logger.info(f"Assessing risks for plan: {plan.plan_id}")

        # Identify risks
        risks = self._identify_risks(plan, briefing)

        # Calculate overall risk level
        overall_risk = self._calculate_overall_risk(risks)

        # Estimate resources
        estimated_duration = self._estimate_duration(plan)
        estimated_cost = self._estimate_cost(plan)
        resource_requirements = self._calculate_resource_requirements(plan, briefing)

        # Generate recommendations
        recommendations = self._generate_recommendations(plan, briefing, risks)
        warnings = self._generate_warnings(risks)

        assessment = RiskAssessment(
            overall_risk_level=overall_risk,
            risks=risks,
            estimated_duration_minutes=estimated_duration,
            estimated_cost_euros=estimated_cost,
            resource_requirements=resource_requirements,
            recommendations=recommendations,
            warnings=warnings,
        )

        logger.info(
            f"Risk assessment complete: {overall_risk} risk, "
            f"{estimated_duration}min, {len(risks)} risks identified"
        )

        return assessment

    def _identify_risks(
        self,
        plan: BusinessPlan,
        briefing: BusinessBriefing
    ) -> List[Risk]:
        """
        Identify potential risks in the plan.

        Args:
            plan: Business plan
            briefing: Original briefing

        Returns:
            List of identified risks
        """
        risks = []

        # Risk 1: Domain availability
        if briefing.website_config and not briefing.dry_run:
            risks.append(Risk(
                description="Domain may not be available or DNS propagation may delay",
                severity=RiskLevel.MEDIUM,
                probability=RiskLevel.MEDIUM,
                impact="Website deployment may fail or be delayed",
                mitigation="Verify domain availability before execution; DNS propagation can take up to 48h",
                related_steps=[
                    step.step_id for step in plan.steps
                    if step.executor == ExecutorType.DNS
                ]
            ))

        # Risk 2: External dependencies
        if briefing.erp_config:
            risks.append(Risk(
                description="Odoo instance must be accessible and properly configured",
                severity=RiskLevel.HIGH,
                probability=RiskLevel.LOW,
                impact="ERP deployment will fail, requiring manual intervention",
                mitigation="Preflight check will verify Odoo connectivity; ensure Odoo service is running",
                related_steps=[
                    step.step_id for step in plan.steps
                    if step.executor == ExecutorType.ODOO
                ]
            ))

        # Risk 3: Integration complexity
        if len(briefing.integrations) > 2:
            risks.append(Risk(
                description=f"Multiple integrations ({len(briefing.integrations)}) increase complexity and failure risk",
                severity=RiskLevel.MEDIUM,
                probability=RiskLevel.MEDIUM,
                impact="Integration failures may break website or ERP functionality",
                mitigation="Test each integration independently; implement retry logic",
                related_steps=[
                    step.step_id for step in plan.steps
                    if step.executor == ExecutorType.INTEGRATION
                ]
            ))

        # Risk 4: Rollback limitations
        non_rollbackable_steps = [
            step for step in plan.steps
            if not step.rollback_possible
        ]
        if non_rollbackable_steps:
            risks.append(Risk(
                description=f"{len(non_rollbackable_steps)} step(s) cannot be fully rolled back",
                severity=RiskLevel.LOW,
                probability=RiskLevel.HIGH,
                impact="Partial rollback may leave system in inconsistent state",
                mitigation="Manual cleanup may be required for non-rollbackable steps",
                related_steps=[step.step_id for step in non_rollbackable_steps]
            ))

        # Risk 5: Resource constraints
        if plan.steps_total > 10:
            risks.append(Risk(
                description=f"Large number of steps ({plan.steps_total}) increases execution time and failure probability",
                severity=RiskLevel.LOW,
                probability=RiskLevel.HIGH,
                impact="Longer execution time increases chance of transient failures",
                mitigation="Monitor execution closely; ensure sufficient timeout values",
                related_steps=[]
            ))

        # Risk 6: Dry run vs production
        if briefing.dry_run:
            risks.append(Risk(
                description="Dry run mode enabled - no actual changes will be made",
                severity=RiskLevel.LOW,
                probability=RiskLevel.HIGH,
                impact="No deployment will occur, only validation",
                mitigation="Set dry_run=false to enable actual deployment",
                related_steps=[]
            ))

        # Risk 7: Auto-execution risk
        if briefing.auto_execute:
            risks.append(Risk(
                description="Auto-execution enabled - plan will execute immediately without review",
                severity=RiskLevel.HIGH,
                probability=RiskLevel.HIGH,
                impact="No opportunity to review plan before execution",
                mitigation="Review plan carefully or disable auto_execute for manual approval",
                related_steps=[]
            ))

        return risks

    def _calculate_overall_risk(self, risks: List[Risk]) -> RiskLevel:
        """
        Calculate overall risk level from individual risks.

        Logic:
        - Any CRITICAL risk → overall CRITICAL
        - 2+ HIGH risks → overall HIGH
        - 1 HIGH or 3+ MEDIUM → overall MEDIUM
        - Otherwise → overall LOW

        Args:
            risks: List of identified risks

        Returns:
            Overall risk level
        """
        risk_counts = {
            RiskLevel.CRITICAL: 0,
            RiskLevel.HIGH: 0,
            RiskLevel.MEDIUM: 0,
            RiskLevel.LOW: 0,
        }

        for risk in risks:
            risk_counts[risk.severity] += 1

        # Determine overall
        if risk_counts[RiskLevel.CRITICAL] > 0:
            return RiskLevel.CRITICAL
        elif risk_counts[RiskLevel.HIGH] >= 2:
            return RiskLevel.HIGH
        elif risk_counts[RiskLevel.HIGH] >= 1 or risk_counts[RiskLevel.MEDIUM] >= 3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _estimate_duration(self, plan: BusinessPlan) -> int:
        """
        Estimate total execution duration in minutes.

        Args:
            plan: Business plan

        Returns:
            Estimated duration in minutes
        """
        total_minutes = 0

        for step in plan.steps:
            # Get base duration for executor type
            base_duration = self.STEP_DURATIONS.get(step.executor, 5)

            # Adjustments based on step specifics
            if step.executor == ExecutorType.WEBGEN:
                # More pages = more time
                pages = step.parameters.get("pages", [])
                if len(pages) > 5:
                    base_duration += (len(pages) - 5) * 1  # +1 min per extra page

            elif step.executor == ExecutorType.ODOO:
                # More modules = more time
                modules = step.parameters.get("modules", [])
                if len(modules) > 3:
                    base_duration += (len(modules) - 3) * 2  # +2 min per extra module

            total_minutes += base_duration

        # Add 20% buffer for overhead
        total_minutes = int(total_minutes * 1.2)

        return total_minutes

    def _estimate_cost(self, plan: BusinessPlan) -> float:
        """
        Estimate total cost in EUR.

        Currently all internal operations are free.
        Future: Could add costs for external services (DNS, hosting, etc.)

        Args:
            plan: Business plan

        Returns:
            Estimated cost in EUR
        """
        total_cost = 0.0

        for step in plan.steps:
            base_cost = self.STEP_COSTS.get(step.executor, 0.0)
            total_cost += base_cost

        return total_cost

    def _calculate_resource_requirements(
        self,
        plan: BusinessPlan,
        briefing: BusinessBriefing
    ) -> Dict[str, Any]:
        """
        Calculate resource requirements.

        Args:
            plan: Business plan
            briefing: Original briefing

        Returns:
            Dictionary of resource requirements
        """
        requirements = {
            "disk_mb": 0,
            "memory_mb": 0,
            "network_required": False,
            "external_services": [],
        }

        # Disk space for website
        if briefing.website_config:
            # Estimate: 10MB per page
            num_pages = len(briefing.website_config.pages)
            requirements["disk_mb"] += num_pages * 10

        # Disk space for Odoo (minimal, as Odoo is already installed)
        if briefing.erp_config:
            requirements["disk_mb"] += 50  # Odoo database overhead

        # Memory (runtime, not persistent)
        requirements["memory_mb"] = 512  # Base requirement for execution

        # Network
        if briefing.erp_config or not briefing.dry_run:
            requirements["network_required"] = True

        # External services
        if briefing.erp_config:
            requirements["external_services"].append("odoo")
        if not briefing.dry_run and briefing.website_config:
            requirements["external_services"].append("dns_provider")

        return requirements

    def _generate_recommendations(
        self,
        plan: BusinessPlan,
        briefing: BusinessBriefing,
        risks: List[Risk]
    ) -> List[str]:
        """
        Generate recommendations for user.

        Args:
            plan: Business plan
            briefing: Original briefing
            risks: Identified risks

        Returns:
            List of recommendations
        """
        recommendations = []

        # High risk warning
        high_risk_count = sum(1 for r in risks if r.severity in [RiskLevel.HIGH, RiskLevel.CRITICAL])
        if high_risk_count > 0:
            recommendations.append(
                f"⚠️  {high_risk_count} high-severity risk(s) identified. Review carefully before execution."
            )

        # Dry run suggestion
        if not briefing.dry_run and briefing.auto_execute:
            recommendations.append(
                "💡 Consider enabling dry_run=true first to validate plan without making changes."
            )

        # Backup suggestion
        if briefing.erp_config:
            recommendations.append(
                "💾 Create Odoo database backup before execution to enable full rollback."
            )

        # DNS propagation notice
        if briefing.website_config and not briefing.dry_run:
            recommendations.append(
                "⏰ DNS propagation can take 1-48 hours. Website may not be accessible immediately."
            )

        # Execution time notice
        if plan.risk_assessment and plan.risk_assessment.estimated_duration_minutes > 30:
            recommendations.append(
                f"⏱️  Estimated execution time is {plan.risk_assessment.estimated_duration_minutes} minutes. "
                "Ensure stable internet connection."
            )

        return recommendations

    def _generate_warnings(self, risks: List[Risk]) -> List[str]:
        """
        Generate warning messages from risks.

        Args:
            risks: Identified risks

        Returns:
            List of warning messages
        """
        warnings = []

        for risk in risks:
            if risk.severity in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                warnings.append(f"[{risk.severity.upper()}] {risk.description}")

        return warnings
