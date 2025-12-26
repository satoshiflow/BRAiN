"""
IR Governance Gateway for WebGenesis (Sprint 10)

Validates IR before pipeline execution, enforces governance gates.
"""

from typing import Dict, Any, Optional
from loguru import logger

from backend.app.modules.ir_governance import (
    IR,
    IRValidationResult,
    IRValidationStatus,
    ApprovalConsumeRequest,
    ApprovalConsumeResult,
    ApprovalStatus,
    get_validator,
    get_approvals_service,
    ir_hash,
)
from backend.app.modules.autonomous_pipeline.ir_config import get_ir_config, IRMode


class IRGatewayError(Exception):
    """Raised when IR gateway validation fails."""
    pass


class IRGatewayBlockedError(IRGatewayError):
    """Raised when execution is blocked by IR governance."""
    pass


class IRGatewayResult:
    """Result of IR gateway validation."""

    def __init__(
        self,
        allowed: bool,
        ir: Optional[IR] = None,
        validation_result: Optional[IRValidationResult] = None,
        approval_result: Optional[ApprovalConsumeResult] = None,
        block_reason: Optional[str] = None,
        audit_events: Optional[list] = None,
    ):
        self.allowed = allowed
        self.ir = ir
        self.validation_result = validation_result
        self.approval_result = approval_result
        self.block_reason = block_reason
        self.audit_events = audit_events or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/response."""
        return {
            "allowed": self.allowed,
            "ir_hash": ir_hash(self.ir) if self.ir else None,
            "validation_status": self.validation_result.status if self.validation_result else None,
            "requires_approval": self.validation_result.requires_approval if self.validation_result else False,
            "approval_consumed": self.approval_result.success if self.approval_result else None,
            "block_reason": self.block_reason,
            "audit_event_count": len(self.audit_events),
        }


class IRGateway:
    """
    IR Governance Gateway for WebGenesis pipeline.

    Responsibilities:
    1. Check if IR is required based on config
    2. Validate IR against policy rules
    3. Handle ESCALATE cases (approval required)
    4. Emit audit events
    5. Block execution if governance fails

    Conservative Design:
    - Fail-closed: Invalid state → block execution
    - Explicit approval: ESCALATE without approval → block
    - Audit-first: All decisions logged
    """

    def __init__(self):
        self.config = get_ir_config()
        self.validator = get_validator()
        self.approvals_service = get_approvals_service()

    def validate_request(
        self,
        ir: Optional[IR] = None,
        approval_token: Optional[str] = None,
        legacy_request: bool = False,
    ) -> IRGatewayResult:
        """
        Validate incoming request against IR governance rules.

        Args:
            ir: Optional IR (if provided)
            approval_token: Optional approval token (for ESCALATE cases)
            legacy_request: Whether this is a legacy request (no IR)

        Returns:
            IRGatewayResult with decision

        Raises:
            IRGatewayBlockedError: If execution must be blocked
        """
        audit_events = []

        # CASE 1: IR disabled (mode=off)
        if self.config.ir_mode == IRMode.OFF:
            logger.info("[IRGateway] IR mode=OFF, allowing all requests")
            audit_events.append({
                "event_type": "webgenesis.ir_disabled",
                "message": "IR governance disabled, legacy behavior",
            })
            return IRGatewayResult(allowed=True, audit_events=audit_events)

        # CASE 2: Legacy request with IR mode=required
        if legacy_request and self.config.is_ir_required():
            logger.error("[IRGateway] Legacy request blocked: IR required")
            audit_events.append({
                "event_type": "webgenesis.ir_required_violation",
                "message": "IR is required but not provided",
            })
            return IRGatewayResult(
                allowed=False,
                block_reason="IR is required (WEBGENESIS_IR_MODE=required)",
                audit_events=audit_events,
            )

        # CASE 3: Legacy request with IR mode=opt_in
        if legacy_request and self.config.ir_mode == IRMode.OPT_IN:
            logger.info("[IRGateway] Legacy request allowed (opt-in mode)")
            audit_events.append({
                "event_type": "webgenesis.ir_legacy_allowed",
                "message": "Legacy request allowed in opt-in mode",
            })
            return IRGatewayResult(allowed=True, audit_events=audit_events)

        # CASE 4: IR provided, validate it
        if ir is None:
            logger.error("[IRGateway] IR expected but not provided")
            return IRGatewayResult(
                allowed=False,
                block_reason="IR expected but not provided",
                audit_events=audit_events,
            )

        # Validate IR
        logger.info(f"[IRGateway] Validating IR for tenant={ir.tenant_id}")
        audit_events.append({
            "event_type": "webgenesis.ir_received",
            "tenant_id": ir.tenant_id,
            "request_id": ir.request_id,
            "ir_hash": ir_hash(ir),
            "step_count": len(ir.steps),
        })

        validation_result = self.validator.validate_ir(ir)

        # CASE 5: IR validation REJECT
        if validation_result.status == IRValidationStatus.REJECT:
            logger.error(
                f"[IRGateway] IR validation REJECTED: {validation_result.violations}"
            )
            audit_events.append({
                "event_type": "webgenesis.ir_validated_reject",
                "tenant_id": ir.tenant_id,
                "ir_hash": validation_result.ir_hash,
                "violations": [v.model_dump() for v in validation_result.violations],
            })
            return IRGatewayResult(
                allowed=False,
                ir=ir,
                validation_result=validation_result,
                block_reason=f"IR validation failed: {len(validation_result.violations)} violation(s)",
                audit_events=audit_events,
            )

        # CASE 6: IR validation PASS
        if validation_result.status == IRValidationStatus.PASS:
            logger.info(
                f"[IRGateway] IR validation PASSED (tier={validation_result.risk_tier})"
            )
            audit_events.append({
                "event_type": "webgenesis.ir_validated_pass",
                "tenant_id": ir.tenant_id,
                "ir_hash": validation_result.ir_hash,
                "risk_tier": validation_result.risk_tier,
            })
            return IRGatewayResult(
                allowed=True,
                ir=ir,
                validation_result=validation_result,
                audit_events=audit_events,
            )

        # CASE 7: IR validation ESCALATE (requires approval)
        if validation_result.status == IRValidationStatus.ESCALATE:
            logger.warning(
                f"[IRGateway] IR validation ESCALATE: approval required "
                f"(tier={validation_result.risk_tier})"
            )
            audit_events.append({
                "event_type": "webgenesis.ir_validated_escalate",
                "tenant_id": ir.tenant_id,
                "ir_hash": validation_result.ir_hash,
                "risk_tier": validation_result.risk_tier,
            })

            # Check if approval token provided
            if not approval_token:
                logger.error("[IRGateway] ESCALATE but no approval token provided")
                audit_events.append({
                    "event_type": "webgenesis.ir_approval_required",
                    "tenant_id": ir.tenant_id,
                    "ir_hash": validation_result.ir_hash,
                    "message": "Approval token required but not provided",
                })
                return IRGatewayResult(
                    allowed=False,
                    ir=ir,
                    validation_result=validation_result,
                    block_reason="Approval required (no token provided)",
                    audit_events=audit_events,
                )

            # Consume approval token
            approval_request = ApprovalConsumeRequest(
                tenant_id=ir.tenant_id,
                ir_hash=validation_result.ir_hash,
                token=approval_token,
            )
            approval_result = self.approvals_service.consume_approval(approval_request)

            if not approval_result.success:
                logger.error(
                    f"[IRGateway] Approval token consumption FAILED: "
                    f"{approval_result.status}"
                )
                audit_events.append({
                    "event_type": "webgenesis.ir_approval_invalid",
                    "tenant_id": ir.tenant_id,
                    "ir_hash": validation_result.ir_hash,
                    "approval_status": approval_result.status,
                    "message": approval_result.message,
                })
                return IRGatewayResult(
                    allowed=False,
                    ir=ir,
                    validation_result=validation_result,
                    approval_result=approval_result,
                    block_reason=f"Approval failed: {approval_result.message}",
                    audit_events=audit_events,
                )

            # Approval consumed successfully
            logger.info("[IRGateway] Approval token consumed successfully")
            audit_events.append({
                "event_type": "webgenesis.ir_approval_consumed",
                "tenant_id": ir.tenant_id,
                "ir_hash": validation_result.ir_hash,
                "approval_id": approval_result.approval_id,
            })
            return IRGatewayResult(
                allowed=True,
                ir=ir,
                validation_result=validation_result,
                approval_result=approval_result,
                audit_events=audit_events,
            )

        # CASE 8: Unknown validation status (should never happen)
        logger.error(f"[IRGateway] Unknown validation status: {validation_result.status}")
        return IRGatewayResult(
            allowed=False,
            ir=ir,
            validation_result=validation_result,
            block_reason=f"Unknown validation status: {validation_result.status}",
            audit_events=audit_events,
        )


# Singleton
_gateway: Optional[IRGateway] = None


def get_ir_gateway() -> IRGateway:
    """Get IR gateway singleton."""
    global _gateway
    if _gateway is None:
        _gateway = IRGateway()
    return _gateway
