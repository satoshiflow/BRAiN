"""
Policy Engine Service - Business logic for policy evaluation

Provides rule-based policy engine with:
- Policy CRUD operations
- Policy evaluation (check if action is allowed)
- Integration with Foundation layer (double-check safety)
- Permission management
- Audit trail
"""

import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from loguru import logger

from .schemas import (
    Policy,
    PolicyRule,
    PolicyCondition,
    PolicyConditionOperator,
    PolicyEffect,
    PolicyEvaluationContext,
    PolicyEvaluationResult,
    PolicyHealth,
    PolicyInfo,
    PolicyStats,
    PolicyCreateRequest,
    PolicyUpdateRequest,
    Permission,
)

# Optional: Integrate with Foundation for safety double-check
try:
    from app.modules.foundation.service import get_foundation_service
    from app.modules.foundation.schemas import ActionValidationRequest

    FOUNDATION_AVAILABLE = True
except ImportError:
    FOUNDATION_AVAILABLE = False
    logger.warning("Foundation module not available - Policy will work standalone")


MODULE_NAME = "brain.policy"
MODULE_VERSION = "2.0.0"  # Upgraded from 1.0.0


class PolicyEngine:
    """
    Policy Engine for rule-based governance.

    Evaluates actions against policies and permissions.
    """

    def __init__(self):
        """Initialize Policy Engine"""
        # In-memory storage (TODO: migrate to database)
        self.policies: Dict[str, Policy] = {}
        self.permissions: Dict[str, Permission] = {}

        # Metrics
        self.total_evaluations = 0
        self.total_allows = 0
        self.total_denies = 0
        self.total_warnings = 0

        self.start_time = time.time()

        # Load default policies
        self._load_default_policies()

        logger.info(f"🔐 Policy Engine initialized (v{MODULE_VERSION})")

    def _load_default_policies(self):
        """Load default policies for common scenarios"""

        # Default policy: Admin full access
        admin_policy = Policy(
            policy_id="admin_full_access",
            name="Admin Full Access",
            version="1.0.0",
            description="Admins have unrestricted access",
            rules=[
                PolicyRule(
                    rule_id="admin_allow_all",
                    name="Admin Allow All",
                    description="Any admin can do anything",
                    effect=PolicyEffect.ALLOW,
                    conditions=[
                        PolicyCondition(
                            field="agent_role",
                            operator=PolicyConditionOperator.EQUALS,
                            value="admin",
                        )
                    ],
                    priority=1000,  # Highest priority
                    enabled=True,
                )
            ],
            default_effect=PolicyEffect.DENY,
            enabled=True,
        )

        # Default policy: Guest read-only
        guest_policy = Policy(
            policy_id="guest_read_only",
            name="Guest Read-Only Access",
            version="1.0.0",
            description="Guests can only read, no modifications",
            rules=[
                PolicyRule(
                    rule_id="guest_read_allow",
                    name="Guest Read Allow",
                    description="Guests can read data",
                    effect=PolicyEffect.ALLOW,
                    conditions=[
                        PolicyCondition(
                            field="agent_role",
                            operator=PolicyConditionOperator.EQUALS,
                            value="guest",
                        ),
                        PolicyCondition(
                            field="action",
                            operator=PolicyConditionOperator.CONTAINS,
                            value="read",
                        ),
                    ],
                    priority=50,
                    enabled=True,
                ),
                PolicyRule(
                    rule_id="guest_write_deny",
                    name="Guest Write Deny",
                    description="Guests cannot write/modify",
                    effect=PolicyEffect.DENY,
                    conditions=[
                        PolicyCondition(
                            field="agent_role",
                            operator=PolicyConditionOperator.EQUALS,
                            value="guest",
                        ),
                        PolicyCondition(
                            field="action",
                            operator=PolicyConditionOperator.IN,
                            value=["write", "delete", "update", "create"],
                        ),
                    ],
                    priority=100,  # Higher priority than allow
                    enabled=True,
                ),
            ],
            default_effect=PolicyEffect.DENY,
            enabled=True,
        )

        self.policies[admin_policy.policy_id] = admin_policy
        self.policies[guest_policy.policy_id] = guest_policy

        logger.info(f"✅ Loaded {len(self.policies)} default policies")

    async def evaluate(
        self, context: PolicyEvaluationContext
    ) -> PolicyEvaluationResult:
        """
        Evaluate if an action is allowed based on policies.

        Args:
            context: Evaluation context (agent, action, resource, etc.)

        Returns:
            PolicyEvaluationResult with decision and reason
        """
        self.total_evaluations += 1

        logger.debug(
            f"🔍 Evaluating: agent={context.agent_id}, action={context.action}"
        )

        # Step 1: Collect all active policies
        active_policies = [p for p in self.policies.values() if p.enabled]

        if not active_policies:
            logger.warning("⚠️ No active policies - defaulting to DENY")
            self.total_denies += 1
            return PolicyEvaluationResult(
                allowed=False,
                effect=PolicyEffect.DENY,
                reason="No policies configured - default deny",
            )

        # Step 2: Evaluate each policy's rules (highest priority first)
        all_rules = []
        for policy in active_policies:
            for rule in policy.rules:
                if rule.enabled:
                    all_rules.append((policy, rule))

        # Sort by priority (highest first)
        all_rules.sort(key=lambda x: x[1].priority, reverse=True)

        # Step 3: Find first matching rule
        for policy, rule in all_rules:
            if await self._rule_matches(rule, context):
                logger.info(
                    f"✅ Matched rule: {rule.name} (effect={rule.effect.value})"
                )

                # Apply effect
                result = self._apply_effect(rule.effect, policy, rule, context)
                self._update_metrics(result)

                # Optional: Double-check with Foundation layer
                if FOUNDATION_AVAILABLE and result.allowed:
                    foundation_check = await self._check_foundation(context)
                    if not foundation_check:
                        logger.warning(
                            "⚠️ Policy allowed but Foundation blocked - DENY"
                        )
                        result.allowed = False
                        result.effect = PolicyEffect.DENY
                        result.reason = (
                            f"{result.reason} (overridden by Foundation safety check)"
                        )
                        self.total_denies += 1

                return result

        # Step 4: No rules matched - use default effect
        logger.debug("No rules matched - using default effect")

        # Find most specific default
        default_effect = PolicyEffect.DENY
        for policy in active_policies:
            default_effect = policy.default_effect
            break

        result = PolicyEvaluationResult(
            allowed=(default_effect == PolicyEffect.ALLOW),
            effect=default_effect,
            reason=f"No matching rules - applied default effect: {default_effect.value}",
        )

        self._update_metrics(result)
        return result

    async def _rule_matches(
        self, rule: PolicyRule, context: PolicyEvaluationContext
    ) -> bool:
        """
        Check if all conditions in a rule match the context.

        Args:
            rule: Policy rule to check
            context: Evaluation context

        Returns:
            True if ALL conditions match (AND logic)
        """
        if not rule.conditions:
            # No conditions = always match
            return True

        for condition in rule.conditions:
            if not await self._condition_matches(condition, context):
                return False

        return True

    async def _condition_matches(
        self, condition: PolicyCondition, context: PolicyEvaluationContext
    ) -> bool:
        """
        Check if a single condition matches.

        Args:
            condition: Condition to check
            context: Evaluation context

        Returns:
            True if condition matches
        """
        # Get field value from context (supports dot notation)
        field_value = self._get_field_value(condition.field, context)

        # Evaluate operator
        operator = condition.operator
        expected = condition.value

        if operator == PolicyConditionOperator.EQUALS:
            return field_value == expected

        elif operator == PolicyConditionOperator.NOT_EQUALS:
            return field_value != expected

        elif operator == PolicyConditionOperator.GREATER_THAN:
            return field_value > expected

        elif operator == PolicyConditionOperator.LESS_THAN:
            return field_value < expected

        elif operator == PolicyConditionOperator.CONTAINS:
            return (
                expected in str(field_value)
                if field_value is not None
                else False
            )

        elif operator == PolicyConditionOperator.MATCHES:
            # Regex match
            if field_value is None:
                return False
            return bool(re.match(expected, str(field_value)))

        elif operator == PolicyConditionOperator.IN:
            # List membership
            return field_value in expected if isinstance(expected, list) else False

        else:
            logger.warning(f"Unknown operator: {operator}")
            return False

    def _get_field_value(self, field: str, context: PolicyEvaluationContext) -> Any:
        """
        Get field value from context using dot notation.

        Examples:
            "agent_id" → context.agent_id
            "agent.role" → context.agent_role
            "environment.time" → context.environment["time"]

        Args:
            field: Field path (dot notation)
            context: Evaluation context

        Returns:
            Field value or None if not found
        """
        parts = field.split(".")

        # Direct attribute
        if len(parts) == 1:
            return getattr(context, field, None)

        # Nested (e.g., "environment.time")
        if len(parts) == 2:
            root, key = parts
            if root == "environment":
                return context.environment.get(key)
            elif root == "params":
                return context.params.get(key)
            elif root == "agent":
                # Map agent.X to agent_X
                return getattr(context, f"agent_{key}", None)

        logger.warning(f"Field not found: {field}")
        return None

    def _apply_effect(
        self,
        effect: PolicyEffect,
        policy: Policy,
        rule: PolicyRule,
        context: PolicyEvaluationContext,
    ) -> PolicyEvaluationResult:
        """Apply policy effect and create result"""

        if effect == PolicyEffect.ALLOW:
            return PolicyEvaluationResult(
                allowed=True,
                effect=effect,
                matched_rule=rule.rule_id,
                matched_policy=policy.policy_id,
                reason=f"Allowed by rule '{rule.name}'",
            )

        elif effect == PolicyEffect.DENY:
            return PolicyEvaluationResult(
                allowed=False,
                effect=effect,
                matched_rule=rule.rule_id,
                matched_policy=policy.policy_id,
                reason=f"Denied by rule '{rule.name}'",
            )

        elif effect == PolicyEffect.WARN:
            return PolicyEvaluationResult(
                allowed=True,
                effect=effect,
                matched_rule=rule.rule_id,
                matched_policy=policy.policy_id,
                reason=f"Allowed with warning by rule '{rule.name}'",
                warnings=[f"Action '{context.action}' triggered warning rule"],
            )

        elif effect == PolicyEffect.AUDIT:
            return PolicyEvaluationResult(
                allowed=True,
                effect=effect,
                matched_rule=rule.rule_id,
                matched_policy=policy.policy_id,
                reason=f"Allowed with audit requirement by rule '{rule.name}'",
                requires_audit=True,
            )

        else:
            logger.error(f"Unknown effect: {effect}")
            return PolicyEvaluationResult(
                allowed=False,
                effect=PolicyEffect.DENY,
                reason="Unknown effect - default deny",
            )

    async def _check_foundation(self, context: PolicyEvaluationContext) -> bool:
        """
        Double-check with Foundation layer for safety.

        Returns:
            True if Foundation also allows, False if blocked
        """
        if not FOUNDATION_AVAILABLE:
            return True  # Foundation not available - skip check

        try:
            foundation = get_foundation_service()
            request = ActionValidationRequest(
                action=context.action,
                params=context.params,
                context={"agent_id": context.agent_id},
            )

            result = await foundation.validate_action(request)
            return result.valid

        except Exception as e:
            logger.error(f"Foundation check failed: {e}")
            return True  # Don't block on Foundation errors

    def _update_metrics(self, result: PolicyEvaluationResult):
        """Update metrics based on evaluation result"""
        if result.allowed:
            self.total_allows += 1
        else:
            self.total_denies += 1

        if result.effect == PolicyEffect.WARN:
            self.total_warnings += 1

    # ========================================================================
    # Policy CRUD Operations
    # ========================================================================

    async def create_policy(self, request: PolicyCreateRequest) -> Policy:
        """Create a new policy"""
        policy_id = f"policy_{len(self.policies) + 1}"

        policy = Policy(
            policy_id=policy_id,
            name=request.name,
            version=request.version,
            description=request.description,
            rules=request.rules,
            default_effect=request.default_effect,
            enabled=request.enabled,
        )

        self.policies[policy_id] = policy
        logger.info(f"✅ Created policy: {policy_id}")

        return policy

    async def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get policy by ID"""
        return self.policies.get(policy_id)

    async def list_policies(self) -> List[Policy]:
        """List all policies"""
        return list(self.policies.values())

    async def update_policy(
        self, policy_id: str, request: PolicyUpdateRequest
    ) -> Optional[Policy]:
        """Update an existing policy"""
        policy = self.policies.get(policy_id)
        if not policy:
            return None

        # Update fields
        if request.name is not None:
            policy.name = request.name
        if request.description is not None:
            policy.description = request.description
        if request.rules is not None:
            policy.rules = request.rules
        if request.default_effect is not None:
            policy.default_effect = request.default_effect
        if request.enabled is not None:
            policy.enabled = request.enabled

        policy.updated_at = datetime.utcnow()

        logger.info(f"✅ Updated policy: {policy_id}")
        return policy

    async def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy"""
        if policy_id in self.policies:
            del self.policies[policy_id]
            logger.info(f"✅ Deleted policy: {policy_id}")
            return True
        return False

    # ========================================================================
    # Stats & Health
    # ========================================================================

    async def get_stats(self) -> PolicyStats:
        """Get policy system statistics"""
        total_rules = sum(len(p.rules) for p in self.policies.values())
        active_policies = sum(1 for p in self.policies.values() if p.enabled)

        return PolicyStats(
            total_policies=len(self.policies),
            active_policies=active_policies,
            total_rules=total_rules,
            total_evaluations=self.total_evaluations,
            total_allows=self.total_allows,
            total_denies=self.total_denies,
            total_warnings=self.total_warnings,
        )


# ============================================================================
# Singleton Instance & Legacy Functions
# ============================================================================

_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get the singleton Policy Engine instance"""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine


# Legacy functions (kept for backward compatibility)
async def get_health() -> PolicyHealth:
    """Legacy health check"""
    return PolicyHealth(status="ok", timestamp=datetime.now(timezone.utc))


async def get_info() -> PolicyInfo:
    """Legacy info endpoint"""
    return PolicyInfo(
        name=MODULE_NAME,
        version=MODULE_VERSION,
        config={},
    )
