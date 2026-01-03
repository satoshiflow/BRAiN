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
from datetime import datetime
import uuid
from loguru import logger

from app.modules.ir_governance.schemas import (
    IR,
    IRStep,
    IRAction,
    IRProvider,
    RiskTier,
    IRValidationStatus,
    IRValidationResult,
    IRViolation,
)
from app.modules.ir_governance.canonicalization import ir_hash

# EventStream integration (Sprint 1)
try:
    from backend.mission_control_core.core.event_stream import EventStream, Event, EventType
except ImportError:
    EventStream = None
    Event = None
    EventType = None
    logger.warning("[IRGovernance] EventStream not available (mission_control_core not installed)")


class IRValidator:
    """
    Deterministic IR validator.

    No LLM. Pure policy-as-code.
    """

    def __init__(self, event_stream: Optional["EventStream"] = None):
        """
        Initialize validator.

        Args:
            event_stream: EventStream for event publishing (optional)
        """
        self.event_stream = event_stream

    async def _publish_event_safe(self, event: "Event") -> None:
        """
        Publish event with error handling (non-blocking).

        Charter v1.0 Compliance:
        - Event publishing MUST NOT block business logic
        - Failures are logged but NOT raised
        - Business operations continue regardless of event success

        Args:
            event: Event to publish
        """
        if self.event_stream is None:
            logger.debug("[IRGovernance] EventStream not available, skipping event publish")
            return

        if Event is None or EventType is None:
            logger.debug("[IRGovernance] EventStream classes not imported, skipping")
            return

        try:
            await self.event_stream.publish_event(event)
            logger.info(f"[IRGovernance] Event published: {event.type.value} (id={event.id})")
        except Exception as e:
            logger.error(
                f"[IRGovernance] Event publishing failed: {event.type.value if hasattr(event, 'type') else 'unknown'}",
                exc_info=True,
            )
            # DO NOT raise - business logic must continue

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

    async def validate_ir(self, ir: IR) -> IRValidationResult:
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
        await self._emit_validation_audit(result, ir)

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

        # CourseFactory content generation → Tier 0 (no side effects)
        if action.value.startswith("course.generate"):
            return RiskTier.TIER_0

        # CourseFactory metadata creation → Tier 0
        if action == IRAction.COURSE_CREATE:
            return RiskTier.TIER_0

        # CourseFactory staging deployment → Tier 1 (low risk, staging only)
        if action == IRAction.COURSE_DEPLOY_STAGING:
            return RiskTier.TIER_1

        # CourseFactory enhancements (Sprint 13) → Tier 0 (content generation)
        if action.value.startswith("course.enhance") or action.value.startswith("course.generate_flashcards"):
            return RiskTier.TIER_0

        # CourseFactory workflow transitions → Tier 0 (state management)
        if action == IRAction.COURSE_WORKFLOW_TRANSITION:
            return RiskTier.TIER_0

        # WebGenesis theme/SEO → Tier 0 (metadata)
        if action.value.startswith("webgenesis.bind") or action.value.startswith("webgenesis.apply_seo"):
            return RiskTier.TIER_0

        # WebGenesis build/preview → Tier 1 (staging deployment)
        if action.value.startswith("webgenesis.build") or action.value.startswith("webgenesis.preview"):
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

    async def _emit_validation_audit(self, result: IRValidationResult, ir: IR):
        """
        Emit audit event for validation result.

        Args:
            result: Validation result
            ir: Original IR (for step details in escalate/reject events)
        """
        if Event is None or EventType is None:
            # Fallback to logging only
            event_type = f"ir.validated_{result.status.value.lower()}"
            logger.info(
                f"[Validator] {event_type}: tenant_id={result.tenant_id}, "
                f"request_id={result.request_id}, risk_tier={result.risk_tier.value}, "
                f"requires_approval={result.requires_approval}, "
                f"violations={len(result.violations)}, "
                f"ir_hash={result.ir_hash[:16]}..."
            )
            return

        # Base payload (common to all validation events)
        base_payload = {
            "tenant_id": result.tenant_id,
            "request_id": result.request_id,
            "ir_hash": result.ir_hash,
            "risk_tier": result.risk_tier.value,
            "requires_approval": result.requires_approval,
            "violations": [v.model_dump() for v in result.violations],
            "validated_at": datetime.utcnow().isoformat() + "Z",
            "step_count": len(ir.steps),
        }

        # Determine event type and enrich payload
        if result.status == IRValidationStatus.PASS:
            event_type_enum = EventType.IR_VALIDATED_PASS
            payload = base_payload.copy()

        elif result.status == IRValidationStatus.ESCALATE:
            event_type_enum = EventType.IR_VALIDATED_ESCALATE
            # Add high-risk steps details
            high_risk_steps = [
                {
                    "step_index": i,
                    "action": step.action.value,
                    "provider": step.provider.value,
                    "risk_tier": step.risk_tier.value,
                    "reason": f"Risk tier {step.risk_tier.value} detected",
                }
                for i, step in enumerate(ir.steps)
                if step.risk_tier >= RiskTier.TIER_2
            ]
            payload = {**base_payload, "high_risk_steps": high_risk_steps}

        else:  # REJECT
            event_type_enum = EventType.IR_VALIDATED_REJECT
            payload = base_payload.copy()

        # Publish event
        await self._publish_event_safe(
            Event(
                id=str(uuid.uuid4()),
                type=event_type_enum,
                source="ir_governance",
                target=None,
                timestamp=datetime.utcnow(),
                payload=payload,
                meta={
                    "schema_version": "1.0",
                    "producer": "ir_governance",
                    "source_module": "ir_governance",
                    "tenant_id": result.tenant_id,
                    "correlation_id": result.request_id,
                },
            )
        )

        # Legacy logging (kept for backward compatibility)
        event_type = f"ir.validated_{result.status.value.lower()}"
        logger.info(
            f"[Validator] {event_type}: tenant_id={result.tenant_id}, "
            f"request_id={result.request_id}, risk_tier={result.risk_tier.value}, "
            f"requires_approval={result.requires_approval}, "
            f"violations={len(result.violations)}, "
            f"ir_hash={result.ir_hash[:16]}..."
        )


# Singleton
_validator: Optional[IRValidator] = None


def get_validator(event_stream: Optional["EventStream"] = None) -> IRValidator:
    """
    Get singleton validator.

    Args:
        event_stream: EventStream for event publishing (optional, only used on first call)
    """
    global _validator
    if _validator is None:
        _validator = IRValidator(event_stream=event_stream)
    return _validator
