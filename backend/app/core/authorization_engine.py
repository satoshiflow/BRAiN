"""
Authorization Engine - Core Authorization Logic for BRAiN

Phase 2: Governance Engine Implementation
Provides comprehensive authorization decisions with:
- Principal validation and RBAC checks
- Scope validation
- AXE Trust Tier verification
- Policy Engine evaluation
- Human-in-the-Loop (HITL) approval for high-risk actions
- Persistent audit logging

SECURITY CRITICAL:
- Risk is determined from POLICY only, NOT from request
- All decisions are auditable
- HITL approval required for HIGH/CRITICAL risk actions
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

from loguru import logger
from pydantic import BaseModel, Field

# Import existing components
from app.core.auth_deps import Principal, PrincipalType
from app.modules.governance.governance_models import (
    Approval,
    ApprovalContext,
    ApprovalType,
    RiskTier,
)
from app.modules.governance.governance_service import GovernanceService
from app.modules.policy.schemas import (
    PolicyEvaluationContext,
    PolicyEvaluationResult,
    PolicyEffect,
)
from app.modules.policy.service import PolicyEngine
from app.modules.axe_governance import TrustTier, AXERequestContext


# ============================================================================
# Data Classes
# ============================================================================

class AuthorizationStatus(str, Enum):
    """Authorization decision status"""
    ALLOWED = "allowed"
    DENIED = "denied"
    PENDING_APPROVAL = "pending_approval"  # HITL required
    ERROR = "error"


@dataclass
class AuthorizationRequest:
    """
    Request for authorization decision.
    
    Contains all information needed to evaluate whether a principal
    is authorized to perform an action on a resource.
    """
    # Who is requesting access
    principal: Principal
    
    # What action is being requested
    action: str
    
    # What resource is being accessed
    resource_id: str
    resource_type: Optional[str] = None
    
    # Context for evaluation
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Network/Request context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    
    # AXE-specific context
    axe_context: Optional[AXERequestContext] = None
    
    def __post_init__(self):
        """Ensure request_id is set"""
        if not self.request_id:
            self.request_id = f"auth_req_{uuid.uuid4().hex[:16]}"


@dataclass
class AuthorizationDecision:
    """
    Result of authorization evaluation.
    
    Contains the decision and all relevant metadata for audit trails
    and downstream processing.
    """
    # Core decision
    allowed: bool
    status: AuthorizationStatus
    reason: str
    
    # Request reference
    request_id: str
    principal_id: str
    action: str
    resource_id: str
    
    # Decision details
    requires_approval: bool = False
    approval_id: Optional[str] = None
    
    # Policy evaluation results
    policy_matched: Optional[str] = None
    rule_matched: Optional[str] = None
    effect: Optional[str] = None
    
    # Risk assessment (from POLICY only - Security Critical)
    risk_tier: RiskTier = RiskTier.LOW
    
    # Failure reasons (for denied decisions)
    failed_checks: List[str] = field(default_factory=list)
    
    # Audit reference
    audit_log_id: Optional[str] = None
    
    # Warnings (for WARN effect)
    warnings: List[str] = field(default_factory=list)
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary for serialization"""
        return {
            "allowed": self.allowed,
            "status": self.status.value,
            "reason": self.reason,
            "request_id": self.request_id,
            "principal_id": self.principal_id,
            "action": self.action,
            "resource_id": self.resource_id,
            "requires_approval": self.requires_approval,
            "approval_id": self.approval_id,
            "policy_matched": self.policy_matched,
            "rule_matched": self.rule_matched,
            "effect": self.effect,
            "risk_tier": self.risk_tier.value,
            "failed_checks": self.failed_checks,
            "audit_log_id": self.audit_log_id,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================================
# Authorization Engine
# ============================================================================

class AuthorizationEngine:
    """
    Central authorization engine for BRAiN.
    
    Implements comprehensive authorization logic:
    1. Principal validation (active, valid)
    2. RBAC checks (role-based access control)
    3. Scope validation (token scopes)
    4. AXE Trust Tier verification
    5. Policy Engine evaluation
    6. HITL approval for HIGH/CRITICAL risk
    7. Persistent audit logging
    
    SECURITY NOTE:
    - Risk is determined from POLICY only, NOT from request context
    - This prevents request injection attacks that manipulate risk assessment
    """
    
    def __init__(
        self,
        policy_engine: Optional[PolicyEngine] = None,
        governance_service: Optional[GovernanceService] = None,
        audit_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize Authorization Engine.
        
        Args:
            policy_engine: Policy engine for rule evaluation (creates default if None)
            governance_service: Governance service for HITL approvals (creates default if None)
            audit_callback: Optional callback for audit logging (in addition to DB)
        """
        self.policy_engine = policy_engine or PolicyEngine()
        self.governance_service = governance_service or GovernanceService()
        self.audit_callback = audit_callback
        
        logger.info("🔐 Authorization Engine initialized")
    
    async def authorize(
        self,
        req: AuthorizationRequest,
        db: Optional[Any] = None,
    ) -> AuthorizationDecision:
        """
        Evaluate authorization request and return decision.
        
        This is the main entry point for authorization decisions.
        Performs all checks in sequence, failing fast on denial.
        
        Steps:
        a. Principal valid & active?
        b. RBAC: Principal has role for action?
        c. Scope: Token has required scope?
        d. AXE Trust Tier check
        e. Policy Engine evaluation
        f. HITL: HIGH/CRITICAL → Approval Request
        g. Audit Log persistent write
        h. Return AuthorizationDecision
        
        Args:
            req: Authorization request
            db: Database session for persistence (optional, for audit logging)
            
        Returns:
            AuthorizationDecision with full context
        """
        failed_checks: List[str] = []
        
        # =================================================================
        # Step a: Principal Validation
        # =================================================================
        principal_valid, principal_error = self._validate_principal(req.principal)
        if not principal_valid:
            failed_checks.append(f"principal_invalid: {principal_error}")
            decision = AuthorizationDecision(
                allowed=False,
                status=AuthorizationStatus.DENIED,
                reason=f"Principal validation failed: {principal_error}",
                request_id=req.request_id,
                principal_id=req.principal.principal_id,
                action=req.action,
                resource_id=req.resource_id,
                failed_checks=failed_checks,
            )
            await self._write_audit_log(decision, req, db)
            return decision
        
        # =================================================================
        # Step b: RBAC Check
        # =================================================================
        rbac_passed, rbac_error = self._check_rbac(req)
        if not rbac_passed:
            failed_checks.append(f"rbac_failed: {rbac_error}")
            decision = AuthorizationDecision(
                allowed=False,
                status=AuthorizationStatus.DENIED,
                reason=f"RBAC check failed: {rbac_error}",
                request_id=req.request_id,
                principal_id=req.principal.principal_id,
                action=req.action,
                resource_id=req.resource_id,
                failed_checks=failed_checks,
            )
            await self._write_audit_log(decision, req, db)
            return decision
        
        # =================================================================
        # Step c: Scope Validation
        # =================================================================
        scope_passed, scope_error = self._check_scopes(req)
        if not scope_passed:
            failed_checks.append(f"scope_failed: {scope_error}")
            decision = AuthorizationDecision(
                allowed=False,
                status=AuthorizationStatus.DENIED,
                reason=f"Scope validation failed: {scope_error}",
                request_id=req.request_id,
                principal_id=req.principal.principal_id,
                action=req.action,
                resource_id=req.resource_id,
                failed_checks=failed_checks,
            )
            await self._write_audit_log(decision, req, db)
            return decision
        
        # =================================================================
        # Step d: AXE Trust Tier Check
        # =================================================================
        if req.axe_context:
            axe_passed, axe_error = self._check_axe_trust_tier(req)
            if not axe_passed:
                failed_checks.append(f"axe_trust_failed: {axe_error}")
                decision = AuthorizationDecision(
                    allowed=False,
                    status=AuthorizationStatus.DENIED,
                    reason=f"AXE trust tier check failed: {axe_error}",
                    request_id=req.request_id,
                    principal_id=req.principal.principal_id,
                    action=req.action,
                    resource_id=req.resource_id,
                    failed_checks=failed_checks,
                )
                await self._write_audit_log(decision, req, db)
                return decision
        
        # =================================================================
        # Step e: Policy Engine Evaluation
        # =================================================================
        policy_result = self._evaluate_policy(req)
        
        # Extract risk from POLICY only (Security Critical)
        risk_tier = self._extract_risk_from_policy(policy_result)
        
        # Handle policy denial
        if not policy_result.allowed:
            decision = AuthorizationDecision(
                allowed=False,
                status=AuthorizationStatus.DENIED,
                reason=policy_result.reason,
                request_id=req.request_id,
                principal_id=req.principal.principal_id,
                action=req.action,
                resource_id=req.resource_id,
                policy_matched=policy_result.matched_policy,
                rule_matched=policy_result.matched_rule,
                effect=policy_result.effect.value,
                risk_tier=risk_tier,
                warnings=policy_result.warnings,
            )
            await self._write_audit_log(decision, req, db)
            return decision
        
        # =================================================================
        # Step f: HITL Approval for HIGH/CRITICAL Risk
        # =================================================================
        if risk_tier in [RiskTier.HIGH, RiskTier.CRITICAL]:
            approval_id = await self._request_hitl_approval(req, risk_tier, policy_result)
            
            if approval_id:
                # Approval requested successfully - return pending status
                decision = AuthorizationDecision(
                    allowed=False,  # Not allowed until approved
                    status=AuthorizationStatus.PENDING_APPROVAL,
                    reason=f"HITL approval required for {risk_tier.value} risk action",
                    request_id=req.request_id,
                    principal_id=req.principal.principal_id,
                    action=req.action,
                    resource_id=req.resource_id,
                    requires_approval=True,
                    approval_id=approval_id,
                    policy_matched=policy_result.matched_policy,
                    rule_matched=policy_result.matched_rule,
                    effect=policy_result.effect.value,
                    risk_tier=risk_tier,
                    warnings=policy_result.warnings,
                )
                await self._write_audit_log(decision, req, db)
                return decision
            else:
                # Failed to create approval request
                failed_checks.append("hitl_request_failed")
                decision = AuthorizationDecision(
                    allowed=False,
                    status=AuthorizationStatus.ERROR,
                    reason="Failed to create HITL approval request",
                    request_id=req.request_id,
                    principal_id=req.principal.principal_id,
                    action=req.action,
                    resource_id=req.resource_id,
                    failed_checks=failed_checks,
                    risk_tier=risk_tier,
                )
                await self._write_audit_log(decision, req, db)
                return decision
        
        # =================================================================
        # Step g: Build Allow Decision
        # =================================================================
        decision = AuthorizationDecision(
            allowed=True,
            status=AuthorizationStatus.ALLOWED,
            reason=policy_result.reason,
            request_id=req.request_id,
            principal_id=req.principal.principal_id,
            action=req.action,
            resource_id=req.resource_id,
            requires_approval=False,
            policy_matched=policy_result.matched_policy,
            rule_matched=policy_result.matched_rule,
            effect=policy_result.effect.value,
            risk_tier=risk_tier,
            warnings=policy_result.warnings,
        )
        
        # =================================================================
        # Step h: Audit Log & Return
        # =================================================================
        await self._write_audit_log(decision, req, db)
        
        logger.info(
            f"Authorization granted: {req.principal.principal_id} -> {req.action} "
            f"on {req.resource_id} (risk: {risk_tier.value})"
        )
        
        return decision
    
    def _validate_principal(
        self,
        principal: Principal,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that principal is valid and active.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if principal is anonymous
        if principal.is_anonymous:
            return False, "Anonymous principals are not allowed"
        
        # Check if principal has ID
        if not principal.principal_id:
            return False, "Principal ID is required"
        
        # Check principal type validity
        if principal.principal_type not in [
            PrincipalType.HUMAN,
            PrincipalType.AGENT,
            PrincipalType.SERVICE,
        ]:
            return False, f"Invalid principal type: {principal.principal_type}"
        
        return True, None
    
    def _check_rbac(self, req: AuthorizationRequest) -> tuple[bool, Optional[str]]:
        """
        Check Role-Based Access Control.
        
        Returns:
            Tuple of (passed, error_message)
        """
        # Map actions to required roles
        action_role_map = {
            # Admin-only actions
            "admin.*": ["admin"],
            "system.*": ["admin"],
            "policy.delete": ["admin"],
            "user.delete": ["admin"],
            
            # Operator and above
            "policy.create": ["admin", "operator"],
            "policy.update": ["admin", "operator"],
            "resource.write": ["admin", "operator"],
            "resource.delete": ["admin", "operator"],
            
            # Viewer and above
            "policy.read": ["admin", "operator", "viewer"],
            "resource.read": ["admin", "operator", "viewer"],
            "audit.read": ["admin", "operator"],  # Not viewers
        }
        
        # Check specific action first
        required_roles = action_role_map.get(req.action)
        
        # Check wildcard patterns
        if not required_roles:
            for pattern, roles in action_role_map.items():
                if pattern.endswith(".*"):
                    prefix = pattern[:-2]
                    if req.action.startswith(prefix + "."):
                        required_roles = roles
                        break
        
        # No specific RBAC requirements
        if not required_roles:
            return True, None
        
        # Check if principal has any of the required roles
        if req.principal.has_any_role(required_roles):
            return True, None
        
        return False, f"Required role not found. Need one of: {required_roles}"
    
    def _check_scopes(self, req: AuthorizationRequest) -> tuple[bool, Optional[str]]:
        """
        Check OAuth/OIDC scopes.
        
        Returns:
            Tuple of (passed, error_message)
        """
        # Map actions to required scopes
        action_scope_map = {
            # Full access scope covers everything
            "*": ["brain:admin"],
            
            # Resource scopes
            "resource.read": ["brain:read", "brain:write", "brain:admin"],
            "resource.write": ["brain:write", "brain:admin"],
            "resource.delete": ["brain:write", "brain:admin"],
            
            # Policy scopes
            "policy.read": ["brain:read", "brain:admin"],
            "policy.write": ["brain:write", "brain:admin"],
            
            # User management
            "user.read": ["brain:read", "brain:admin"],
            "user.write": ["brain:write", "brain:admin"],
            
            # Audit
            "audit.read": ["brain:admin"],
        }
        
        # Check specific action first
        required_scopes = action_scope_map.get(req.action)
        
        # Check wildcard patterns
        if not required_scopes:
            for pattern, scopes in action_scope_map.items():
                if pattern.endswith(".*"):
                    prefix = pattern[:-2]
                    if req.action.startswith(prefix + "."):
                        required_scopes = scopes
                        break
        
        # No specific scope requirements
        if not required_scopes:
            # Default to requiring at least read access
            required_scopes = ["brain:read", "brain:write", "brain:admin"]
        
        # Check if principal has any of the required scopes
        if req.principal.has_any_scope(required_scopes):
            return True, None
        
        return False, f"Required scope not found. Need one of: {required_scopes}"
    
    def _check_axe_trust_tier(
        self,
        req: AuthorizationRequest,
    ) -> tuple[bool, Optional[str]]:
        """
        Check AXE Trust Tier for AXE-related requests.
        
        EXTERNAL tier requests are blocked (fail-closed).
        
        Returns:
            Tuple of (passed, error_message)
        """
        if not req.axe_context:
            return True, None
        
        if req.axe_context.trust_tier == TrustTier.EXTERNAL:
            return False, "EXTERNAL trust tier requests are not allowed"
        
        if req.axe_context.trust_tier == TrustTier.DMZ:
            # Additional validation for DMZ requests
            if not req.axe_context.authenticated:
                return False, "DMZ requests must be authenticated"
            if not req.axe_context.source_service:
                return False, "DMZ requests must specify source service"
        
        return True, None
    
    def _evaluate_policy(
        self,
        req: AuthorizationRequest,
    ) -> PolicyEvaluationResult:
        """
        Evaluate request against Policy Engine.
        
        Returns:
            PolicyEvaluationResult with decision and metadata
        """
        # Build policy evaluation context
        policy_context = PolicyEvaluationContext(
            agent_id=req.principal.principal_id,
            agent_role=req.principal.roles[0] if req.principal.roles else None,
            action=req.action,
            resource=req.resource_id,
            environment={
                "timestamp": datetime.utcnow().isoformat(),
                "ip_address": req.ip_address,
                "trust_tier": req.axe_context.trust_tier.value if req.axe_context else None,
            },
            params=req.context,
        )
        
        # Evaluate against policy engine
        try:
            result = self.policy_engine.evaluate_action(
                agent_id=req.principal.principal_id,
                action=req.action,
                resource=req.resource_id,
                context=policy_context.environment,
            )
            return result
        except Exception as e:
            logger.error(f"Policy evaluation error: {e}")
            # Fail-closed: deny on error
            return PolicyEvaluationResult(
                allowed=False,
                effect=PolicyEffect.DENY,
                reason=f"Policy evaluation error: {str(e)}",
            )
    
    def _extract_risk_from_policy(
        self,
        policy_result: PolicyEvaluationResult,
    ) -> RiskTier:
        """
        Extract risk tier from policy evaluation result.
        
        SECURITY CRITICAL:
        Risk is determined from POLICY only, NOT from request.
        This prevents request injection attacks.
        
        The policy engine should include risk assessment in the result
        or derive it from the matched rule/policy.
        
        Returns:
            RiskTier based on policy evaluation
        """
        # Default risk
        risk = RiskTier.LOW
        
        # Check for risk indicators in policy result
        if policy_result.effect == PolicyEffect.DENY:
            # Denied actions are at least MEDIUM risk
            risk = RiskTier.MEDIUM
        
        # Check matched policy/rule for risk metadata
        # In a full implementation, policies would have risk metadata
        # For now, we use heuristics based on action type
        
        if policy_result.matched_rule:
            rule_lower = policy_result.matched_rule.lower()
            if "critical" in rule_lower or "admin" in rule_lower:
                risk = RiskTier.CRITICAL
            elif "high" in rule_lower or "delete" in rule_lower:
                risk = RiskTier.HIGH
            elif "medium" in rule_lower or "write" in rule_lower:
                risk = max(risk, RiskTier.MEDIUM)
        
        # Override with explicit risk from policy if available
        if hasattr(policy_result, 'risk_tier') and policy_result.risk_tier:
            risk = policy_result.risk_tier
        
        return risk
    
    async def _request_hitl_approval(
        self,
        req: AuthorizationRequest,
        risk_tier: RiskTier,
        policy_result: PolicyEvaluationResult,
    ) -> Optional[str]:
        """
        Request Human-in-the-Loop approval for high-risk actions.
        
        Args:
            req: Authorization request
            risk_tier: Assessed risk tier
            policy_result: Policy evaluation result
            
        Returns:
            Approval ID if created, None on failure
        """
        try:
            # Create approval context
            approval_context = ApprovalContext(
                action_type=ApprovalType.POLICY_OVERRIDE,  # Or appropriate type
                action_description=f"{req.action} on {req.resource_id}",
                risk_tier=risk_tier,
                requested_by=req.principal.principal_id,
                reason=f"Policy: {policy_result.reason}",
                metadata={
                    "action": req.action,
                    "resource_id": req.resource_id,
                    "principal_type": req.principal.principal_type.value,
                    "policy_matched": policy_result.matched_policy,
                    "rule_matched": policy_result.matched_rule,
                    "request_id": req.request_id,
                },
            )
            
            # Request approval via governance service
            approval, token = await self.governance_service.request_approval(
                approval_type=ApprovalType.POLICY_OVERRIDE,
                context=approval_context,
                expires_in_hours=24,
                require_token=(risk_tier == RiskTier.CRITICAL),
            )
            
            logger.info(
                f"HITL approval requested for {risk_tier.value} risk action: "
                f"{approval.approval_id}"
            )
            
            return approval.approval_id
            
        except Exception as e:
            logger.error(f"Failed to request HITL approval: {e}")
            return None
    
    async def _write_audit_log(
        self,
        decision: AuthorizationDecision,
        req: AuthorizationRequest,
        db: Optional[Any] = None,
    ) -> Optional[str]:
        """
        Write authorization decision to audit log.
        
        Args:
            decision: Authorization decision
            req: Original request
            db: Database session (optional)
            
        Returns:
            Audit log ID if written, None otherwise
        """
        try:
            # Build audit entry
            audit_entry = {
                "timestamp": decision.timestamp,
                "principal_id": req.principal.principal_id,
                "principal_type": req.principal.principal_type.value,
                "action": req.action,
                "resource_id": req.resource_id,
                "decision": decision.status.value,
                "reason": decision.reason,
                "policy_matched": decision.policy_matched,
                "rule_matched": decision.rule_matched,
                "risk_tier": decision.risk_tier.value,
                "ip_address": req.ip_address,
                "user_agent": req.user_agent,
                "request_id": req.request_id,
                "metadata": {
                    "failed_checks": decision.failed_checks,
                    "warnings": decision.warnings,
                    "requires_approval": decision.requires_approval,
                    "approval_id": decision.approval_id,
                    "context": req.context,
                },
            }
            
            # If database session available, persist
            if db:
                # Import here to avoid circular imports
                try:
                    from app.models.audit import AuthAuditLog
                    
                    audit_log = AuthAuditLog(
                        principal_id=req.principal.principal_id,
                        principal_type=req.principal.principal_type.value,
                        action=req.action,
                        resource_id=req.resource_id,
                        decision=decision.status.value,
                        reason=decision.reason,
                        policy_matched=decision.policy_matched,
                        rule_matched=decision.rule_matched,
                        risk_tier=decision.risk_tier.value,
                        ip_address=req.ip_address,
                        user_agent=req.user_agent,
                        request_id=req.request_id,
                        metadata={
                            "failed_checks": decision.failed_checks,
                            "warnings": decision.warnings,
                            "requires_approval": decision.requires_approval,
                            "approval_id": decision.approval_id,
                        },
                    )
                    
                    db.add(audit_log)
                    await db.commit()
                    
                    decision.audit_log_id = str(audit_log.id)
                    audit_entry["id"] = str(audit_log.id)
                    
                except Exception as db_error:
                    logger.error(f"Database audit write failed: {db_error}")
                    # Continue to callback even if DB fails
            
            # Call optional audit callback
            if self.audit_callback:
                try:
                    self.audit_callback(audit_entry)
                except Exception as cb_error:
                    logger.error(f"Audit callback error: {cb_error}")
            
            logger.debug(f"Audit log written for request {req.request_id}")
            return decision.audit_log_id
            
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            return None
    
    async def check_approval_status(
        self,
        approval_id: str,
    ) -> Optional[AuthorizationDecision]:
        """
        Check status of a pending HITL approval.
        
        Args:
            approval_id: Approval ID to check
            
        Returns:
            Updated AuthorizationDecision if approval resolved, None if not found
        """
        try:
            approval_detail = await self.governance_service.get_approval_detail(approval_id)
            
            if not approval_detail:
                return None
            
            # Map governance status to authorization status
            from app.modules.governance.governance_models import ApprovalStatus
            
            if approval_detail.status == ApprovalStatus.APPROVED:
                # Reconstruct decision with approval granted
                return AuthorizationDecision(
                    allowed=True,
                    status=AuthorizationStatus.ALLOWED,
                    reason=f"HITL approved: {approval_id}",
                    request_id=approval_detail.context.metadata.get("request_id", "unknown"),
                    principal_id=approval_detail.context.requested_by,
                    action=approval_detail.context.metadata.get("action", "unknown"),
                    resource_id=approval_detail.context.metadata.get("resource_id", "unknown"),
                    requires_approval=False,
                    approval_id=approval_id,
                    risk_tier=approval_detail.context.risk_tier,
                )
            
            elif approval_detail.status == ApprovalStatus.REJECTED:
                return AuthorizationDecision(
                    allowed=False,
                    status=AuthorizationStatus.DENIED,
                    reason=f"HITL rejected: {approval_detail.rejection_reason}",
                    request_id=approval_detail.context.metadata.get("request_id", "unknown"),
                    principal_id=approval_detail.context.requested_by,
                    action=approval_detail.context.metadata.get("action", "unknown"),
                    resource_id=approval_detail.context.metadata.get("resource_id", "unknown"),
                    requires_approval=False,
                    approval_id=approval_id,
                    risk_tier=approval_detail.context.risk_tier,
                )
            
            elif approval_detail.status == ApprovalStatus.EXPIRED:
                return AuthorizationDecision(
                    allowed=False,
                    status=AuthorizationStatus.DENIED,
                    reason=f"HITL approval expired: {approval_id}",
                    request_id=approval_detail.context.metadata.get("request_id", "unknown"),
                    principal_id=approval_detail.context.requested_by,
                    action=approval_detail.context.metadata.get("action", "unknown"),
                    resource_id=approval_detail.context.metadata.get("resource_id", "unknown"),
                    requires_approval=False,
                    approval_id=approval_id,
                    risk_tier=approval_detail.context.risk_tier,
                )
            
            # Still pending
            return None
            
        except Exception as e:
            logger.error(f"Failed to check approval status: {e}")
            return None


# ============================================================================
# Singleton Instance
# ============================================================================

_authorization_engine: Optional[AuthorizationEngine] = None


def get_authorization_engine() -> AuthorizationEngine:
    """Get singleton Authorization Engine instance."""
    global _authorization_engine
    if _authorization_engine is None:
        _authorization_engine = AuthorizationEngine()
    return _authorization_engine


def reset_authorization_engine():
    """Reset singleton (mainly for testing)."""
    global _authorization_engine
    _authorization_engine = None
