"""
Policy Engine Service - Business logic for policy evaluation

Provides rule-based policy engine with:
- Policy CRUD operations
- Policy evaluation (check if action is allowed)
- Integration with Foundation layer (double-check safety)
- Permission management
- Audit trail

Sprint 3 EventStream Integration:
- policy.evaluated: Every policy evaluation
- policy.denied: When action is denied
- policy.warning_triggered: When WARN effect applied
- policy.audit_required: When AUDIT effect applied
- policy.created: When policy created
- policy.updated: When policy modified
- policy.deleted: When policy removed
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

# EventStream integration (Sprint 3)
try:
    from backend.mission_control_core.core import EventStream, Event, EventType
except ImportError:
    EventStream = None
    Event = None
    EventType = None
    import warnings
    warnings.warn(
        "[PolicyEngine] EventStream not available (mission_control_core not installed)",
        RuntimeWarning
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

    def __init__(self, event_stream: Optional["EventStream"] = None):
        """Initialize Policy Engine with optional EventStream integration"""
        # EventStream integration (Sprint 3)
        self.event_stream = event_stream

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

        logger.info(
            f"🔐 Policy Engine initialized (v{MODULE_VERSION}, EventStream: %s)",
            "enabled" if event_stream else "disabled"
        )

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

    async def _emit_event_safe(
        self,
        event_type: str,
        policy: Optional[Policy] = None,
        rule: Optional[PolicyRule] = None,
        context: Optional[PolicyEvaluationContext] = None,
        result: Optional[PolicyEvaluationResult] = None,
        changes: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[str]] = None,
        evaluation_time_ms: Optional[float] = None,
    ) -> None:
        """
        Emit policy event with error handling (non-blocking).

        Charter v1.0 Compliance:
        - Event publishing MUST NOT block business logic
        - Failures are logged but NOT raised

        Args:
            event_type: Event type (e.g., "policy.evaluated")
            policy: Policy object (optional)
            rule: PolicyRule object (optional)
            context: PolicyEvaluationContext (optional)
            result: PolicyEvaluationResult (optional)
            changes: Dict of changes for update events (optional)
            warnings: List of warnings (optional)
            evaluation_time_ms: Evaluation duration (optional)
        """
        if self.event_stream is None or Event is None:
            logger.debug("[PolicyEngine] EventStream not available, skipping event")
            return

        try:
            # Build payload based on event type
            payload = {}

            # Add context fields (agent, action, resource)
            if context:
                payload["agent_id"] = context.agent_id
                if context.agent_role:
                    payload["agent_role"] = context.agent_role
                payload["action"] = context.action
                if context.resource:
                    payload["resource"] = context.resource

            # Add policy info
            if policy:
                payload["policy_id"] = policy.policy_id
                payload["policy_name"] = policy.name

            # Add rule info
            if rule:
                payload["rule_id"] = rule.rule_id
                payload["rule_name"] = rule.name

            # Add result info
            if result:
                payload["result"] = {
                    "allowed": result.allowed,
                    "effect": result.effect.value,
                    "reason": result.reason,
                }
                if result.matched_policy:
                    payload["matched_policy"] = result.matched_policy
                if result.matched_rule:
                    payload["matched_rule"] = result.matched_rule
                if result.warnings:
                    payload["warnings"] = result.warnings
                if result.requires_audit:
                    payload["requires_audit"] = result.requires_audit

            # Add changes (for update events)
            if changes:
                payload["changes"] = changes

            # Add warnings (for warning events)
            if warnings:
                payload["warnings"] = warnings

            # Add evaluation time (for performance tracking)
            if evaluation_time_ms is not None:
                payload["evaluation_time_ms"] = evaluation_time_ms

            # Add timestamp
            payload[f"{event_type.split('.')[1]}_at"] = time.time()

            # Create and publish event
            event = Event(
                type=event_type,
                source="policy_engine",
                target=None,
                payload=payload,
            )

            await self.event_stream.publish(event)

            logger.debug(
                "[PolicyEngine] Event published: %s (policy=%s)",
                event_type,
                policy.policy_id if policy else "none",
            )

        except Exception as e:
            logger.error(
                "[PolicyEngine] Event publishing failed: %s (event_type=%s)",
                e,
                event_type,
                exc_info=True,
            )
            # DO NOT raise - business logic must continue

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

        # Track evaluation time (Sprint 3: for event payload)
        start_time = time.time()

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

                # EVENT: policy.evaluated (every evaluation)
                evaluation_time_ms = (time.time() - start_time) * 1000
                await self._emit_event_safe(
                    event_type="policy.evaluated",
                    policy=policy,
                    rule=rule,
                    context=context,
                    result=result,
                    evaluation_time_ms=evaluation_time_ms,
                )

                # EVENT: policy.denied (if action was denied)
                if not result.allowed:
                    await self._emit_event_safe(
                        event_type="policy.denied",
                        policy=policy,
                        rule=rule,
                        context=context,
                        result=result,
                    )

                # EVENT: policy.warning_triggered (if WARN effect)
                if result.effect == PolicyEffect.WARN:
                    await self._emit_event_safe(
                        event_type="policy.warning_triggered",
                        policy=policy,
                        rule=rule,
                        context=context,
                        warnings=result.warnings,
                    )

                # EVENT: policy.audit_required (if AUDIT effect)
                if result.effect == PolicyEffect.AUDIT:
                    await self._emit_event_safe(
                        event_type="policy.audit_required",
                        policy=policy,
                        rule=rule,
                        context=context,
                        result=result,
                    )

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

        # EVENT: policy.evaluated (default effect path)
        evaluation_time_ms = (time.time() - start_time) * 1000
        await self._emit_event_safe(
            event_type="policy.evaluated",
            policy=None,  # No specific policy matched
            rule=None,  # No specific rule matched
            context=context,
            result=result,
            evaluation_time_ms=evaluation_time_ms,
        )

        # EVENT: policy.denied (if default effect is DENY)
        if not result.allowed:
            await self._emit_event_safe(
                event_type="policy.denied",
                policy=None,
                rule=None,
                context=context,
                result=result,
            )

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

        # EVENT: policy.created
        await self._emit_event_safe(
            event_type="policy.created",
            policy=policy,
        )

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

        # Track changes for event payload
        changes = {}

        # Update fields
        if request.name is not None:
            changes["name"] = {"old": policy.name, "new": request.name}
            policy.name = request.name
        if request.description is not None:
            changes["description"] = {"old": policy.description, "new": request.description}
            policy.description = request.description
        if request.rules is not None:
            changes["rules"] = {"old_count": len(policy.rules), "new_count": len(request.rules)}
            policy.rules = request.rules
        if request.default_effect is not None:
            changes["default_effect"] = {"old": policy.default_effect.value, "new": request.default_effect.value}
            policy.default_effect = request.default_effect
        if request.enabled is not None:
            changes["enabled"] = {"old": policy.enabled, "new": request.enabled}
            policy.enabled = request.enabled

        policy.updated_at = datetime.utcnow()

        logger.info(f"✅ Updated policy: {policy_id}")

        # EVENT: policy.updated
        await self._emit_event_safe(
            event_type="policy.updated",
            policy=policy,
            changes=changes,
        )

        return policy

    async def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy"""
        if policy_id in self.policies:
            policy = self.policies[policy_id]

            # EVENT: policy.deleted (before deletion)
            await self._emit_event_safe(
                event_type="policy.deleted",
                policy=policy,
            )

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


def get_policy_engine(event_stream: Optional["EventStream"] = None) -> PolicyEngine:
    """
    Get the singleton Policy Engine instance.

    Args:
        event_stream: Optional EventStream for event publishing (Sprint 3)
                      Only used on first initialization

    Returns:
        PolicyEngine singleton instance
    """
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine(event_stream=event_stream)
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
