"""
Deterministic IR Validator - Sprint 9 (P0)

Policy-as-code enforcement. LLM-free. Fail-closed by default.

Validator computes:
- Risk tiers (action_tier, scope_tier, impact_tier)
- Approval requirements
- Policy violations

Rules:
- Unknown action/provider → REJECT
- Destructive operations → Tier 3
- Production DNS changes → Tier 2+
- Odoo accounting/payments → Tier 3
- Module uninstall → Tier 3
- Bulk operations → Tier 3

Output: PASS | ESCALATE | REJECT
"""

from typing import List, Optional
from loguru import logger

from backend.app.modules.ir_governance.schemas import (
    IR,
    IRStep,
    IRAction,
    IRProvider,
    RiskTier,
    IRValidationStatus,
    IRValidationResult,
    IRViolation,
)
from backend.app.modules.ir_governance.canonicalization import ir_hash


class IRValidator:
    """
    Deterministic IR validator.

    No LLM. Pure policy-as-code.
    """

    # Destructive keywords for auto-escalation
    DESTRUCTIVE_KEYWORDS = [
        "delete",
        "destroy",
        "uninstall",
        "drop",
        "truncate",
        "remove",
        "purge",
    ]

    # Production-like environments
    PRODUCTION_ENVIRONMENTS = ["production", "prod", "live"]

    # Critical Odoo models
    CRITICAL_ODOO_MODELS = [
        "account.move",  # Accounting entries
        "account.payment",  # Payments
        "account.invoice",  # Invoices
        "sale.order",  # Sales orders (if finalized)
        "purchase.order",  # Purchase orders (if finalized)
    ]

    def validate_ir(self, ir: IR) -> IRValidationResult:
        """
        Validate IR against policy rules.

        Args:
            ir: IR to validate

        Returns:
            IRValidationResult

        Audit events emitted:
        - ir.validated_pass
        - ir.validated_escalate
        - ir.validated_reject
        """
        violations: List[IRViolation] = []
        max_risk_tier = RiskTier.TIER_0
        requires_approval = False

        # Compute IR hash
        computed_ir_hash = ir_hash(ir)

        # Validate each step
        for i, step in enumerate(ir.steps):
            step_violations = self._validate_step(step, i)
            violations.extend(step_violations)

            # Compute risk tier for step
            step_risk_tier = self._compute_risk_tier(step)
            max_risk_tier = max(max_risk_tier, step_risk_tier)

            # Update step (in-place)
            step.risk_tier = step_risk_tier
            step.requires_approval = step_risk_tier >= RiskTier.TIER_2

            if step.requires_approval:
                requires_approval = True

        # Determine overall status
        status = self._determine_status(violations, max_risk_tier)

        result = IRValidationResult(
            status=status,
            violations=violations,
            risk_tier=max_risk_tier,
            requires_approval=requires_approval,
            ir_hash=computed_ir_hash,
            tenant_id=ir.tenant_id,
            request_id=ir.request_id,
        )

        # Emit audit event
        self._emit_validation_audit(result)

        return result

    def _validate_step(self, step: IRStep, step_index: int) -> List[IRViolation]:
        """
        Validate individual step.

        Args:
            step: Step to validate
            step_index: Step index for error reporting

        Returns:
            List of violations
        """
        violations = []

        # Check: action and provider are from fixed vocabulary (fail-closed)
        # Already enforced by Pydantic enum, but double-check
        try:
            if not isinstance(step.action, IRAction):
                violations.append(
                    IRViolation(
                        step_index=step_index,
                        code="UNKNOWN_ACTION",
                        message=f"Unknown action: {step.action}. Must be from IRAction enum.",
                        severity="ERROR",
                    )
                )
        except Exception as e:
            violations.append(
                IRViolation(
                    step_index=step_index,
                    code="INVALID_ACTION",
                    message=f"Invalid action: {e}",
                    severity="ERROR",
                )
            )

        try:
            if not isinstance(step.provider, IRProvider):
                violations.append(
                    IRViolation(
                        step_index=step_index,
                        code="UNKNOWN_PROVIDER",
                        message=f"Unknown provider: {step.provider}. Must be from IRProvider enum.",
                        severity="ERROR",
                    )
                )
        except Exception as e:
            violations.append(
                IRViolation(
                    step_index=step_index,
                    code="INVALID_PROVIDER",
                    message=f"Invalid provider: {e}",
                    severity="ERROR",
                )
            )

        # Check: idempotency key is present and non-empty
        # Already enforced by Pydantic validator, but double-check
        if not step.idempotency_key or not step.idempotency_key.strip():
            violations.append(
                IRViolation(
                    step_index=step_index,
                    code="MISSING_IDEMPOTENCY_KEY",
                    message="idempotency_key is required and must be non-empty",
                    severity="ERROR",
                )
            )

        # Check: budget_cents is non-negative integer (no floats)
        if step.budget_cents is not None:
            if not isinstance(step.budget_cents, int):
                violations.append(
                    IRViolation(
                        step_index=step_index,
                        code="INVALID_BUDGET",
                        message="budget_cents must be an integer (no floats)",
                        severity="ERROR",
                    )
                )
            elif step.budget_cents < 0:
                violations.append(
                    IRViolation(
                        step_index=step_index,
                        code="NEGATIVE_BUDGET",
                        message="budget_cents cannot be negative",
                        severity="ERROR",
                    )
                )

        return violations

    def _compute_risk_tier(self, step: IRStep) -> RiskTier:
        """
        Compute risk tier for step.

        Tiers:
        - Tier 0: Read-only, no side effects
        - Tier 1: Low risk, dev/staging only
        - Tier 2: Medium risk, requires approval
        - Tier 3: High risk, critical operations

        Args:
            step: Step to analyze

        Returns:
            RiskTier (effective tier = max of action, scope, impact tiers)
        """
        action_tier = self._compute_action_tier(step)
        scope_tier = self._compute_scope_tier(step)
        impact_tier = self._compute_impact_tier(step)

        # Effective tier is the maximum
        effective_tier = max(action_tier, scope_tier, impact_tier)

        logger.debug(
            f"[Validator] Step risk: action_tier={action_tier.value}, "
            f"scope_tier={scope_tier.value}, impact_tier={impact_tier.value}, "
            f"effective_tier={effective_tier.value}"
        )

        return effective_tier

    def _compute_action_tier(self, step: IRStep) -> RiskTier:
        """
        Compute action tier based on action type.

        Args:
            step: Step to analyze

        Returns:
            RiskTier
        """
        action = step.action

        # Destructive actions → Tier 3
        if any(keyword in action.value.lower() for keyword in self.DESTRUCTIVE_KEYWORDS):
            return RiskTier.TIER_3

        # Uninstall operations → Tier 3
        if "uninstall" in action.value.lower():
            return RiskTier.TIER_3

        # DNS zone deletion → Tier 3
        if action == IRAction.DNS_DELETE_ZONE:
            return RiskTier.TIER_3

        # Infrastructure destroy → Tier 3
        if action == IRAction.INFRA_DESTROY:
            return RiskTier.TIER_3

        # DNS updates → Tier 2 (requires approval)
        if action in [IRAction.DNS_UPDATE_RECORDS, IRAction.DNS_CREATE_ZONE]:
            return RiskTier.TIER_2

        # Odoo module install → Tier 2
        if action == IRAction.ODOO_INSTALL_MODULE:
            return RiskTier.TIER_2

        # Deployment actions → Tier 1
        if action.value.startswith("deploy."):
            return RiskTier.TIER_1

        # WebGenesis actions → Tier 1
        if action.value.startswith("webgen."):
            return RiskTier.TIER_1

        # Default: Tier 0
        return RiskTier.TIER_0

    def _compute_scope_tier(self, step: IRStep) -> RiskTier:
        """
        Compute scope tier based on environment/scope.

        Args:
            step: Step to analyze

        Returns:
            RiskTier
        """
        constraints = step.constraints or {}

        # Check environment constraint
        environment = constraints.get("environment", "").lower()

        # Production environment → Tier 2+
        if environment in self.PRODUCTION_ENVIRONMENTS:
            return RiskTier.TIER_2

        # Check resource for production indicators
        resource = step.resource.lower()
        if any(prod_env in resource for prod_env in self.PRODUCTION_ENVIRONMENTS):
            return RiskTier.TIER_2

        # Check params for production indicators
        params = step.params or {}
        params_str = str(params).lower()
        if any(prod_env in params_str for prod_env in self.PRODUCTION_ENVIRONMENTS):
            return RiskTier.TIER_2

        # Default: Tier 0 (dev/staging assumed)
        return RiskTier.TIER_0

    def _compute_impact_tier(self, step: IRStep) -> RiskTier:
        """
        Compute impact tier based on operation impact.

        Args:
            step: Step to analyze

        Returns:
            RiskTier
        """
        # Odoo critical models → Tier 3
        if step.action in [
            IRAction.ODOO_CREATE_RECORD,
            IRAction.ODOO_UPDATE_RECORD,
            IRAction.ODOO_DELETE_RECORD,
        ]:
            params = step.params or {}
            model = params.get("model", "")
            if model in self.CRITICAL_ODOO_MODELS:
                return RiskTier.TIER_3

        # Bulk operations → Tier 3
        params = step.params or {}
        if "bulk" in params or "batch" in params:
            return RiskTier.TIER_3

        # Check for bulk indicators in params
        params_str = str(params).lower()
        if "bulk" in params_str or "batch" in params_str:
            return RiskTier.TIER_3

        # Default: Tier 0
        return RiskTier.TIER_0

    def _determine_status(
        self, violations: List[IRViolation], risk_tier: RiskTier
    ) -> IRValidationStatus:
        """
        Determine overall validation status.

        Args:
            violations: List of violations
            risk_tier: Effective risk tier

        Returns:
            IRValidationStatus
        """
        # If any ERROR violations → REJECT
        error_violations = [v for v in violations if v.severity == "ERROR"]
        if error_violations:
            return IRValidationStatus.REJECT

        # If Tier 2+ → ESCALATE (requires approval)
        if risk_tier >= RiskTier.TIER_2:
            return IRValidationStatus.ESCALATE

        # Otherwise → PASS
        return IRValidationStatus.PASS

    def _emit_validation_audit(self, result: IRValidationResult):
        """
        Emit audit event for validation result.

        Args:
            result: Validation result
        """
        event_type = f"ir.validated_{result.status.value.lower()}"

        logger.info(
            f"[Validator] {event_type}: tenant_id={result.tenant_id}, "
            f"request_id={result.request_id}, risk_tier={result.risk_tier.value}, "
            f"requires_approval={result.requires_approval}, "
            f"violations={len(result.violations)}, "
            f"ir_hash={result.ir_hash[:16]}..."
        )

        # TODO: Integrate with existing audit event system
        # For now, logging is sufficient


# Singleton
_validator: Optional[IRValidator] = None


def get_validator() -> IRValidator:
    """Get singleton validator."""
    global _validator
    if _validator is None:
        _validator = IRValidator()
    return _validator
