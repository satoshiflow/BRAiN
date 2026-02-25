"""
Policy Engine Service - Business logic for policy evaluation

Provides rule-based policy engine with:
- Policy CRUD operations with database persistence
- Policy evaluation (check if action is allowed)
- In-memory caching for performance
- Integration with Foundation layer (double-check safety)
- Comprehensive audit logging
- EventStream integration

Sprint 3 EventStream Integration:
- policy.evaluated: Every policy evaluation
- policy.denied: When action is denied
- policy.warning_triggered: When WARN effect applied
- policy.audit_required: When AUDIT effect applied
- policy.created: When policy created
- policy.updated: When policy modified
- policy.deleted: When policy removed
"""

import fnmatch
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from loguru import logger

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    Policy as PolicySchema,
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

# Database models
from app.models.policy import Policy as PolicyModel
from app.models.audit import AuthAuditLog

# EventStream integration (Sprint 3)
try:
    from mission_control_core.core import EventStream, Event, EventType
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
MODULE_VERSION = "3.0.0"  # Upgraded from 2.0.0 - DB persistence added


class PolicyEngine:
    """
    Policy Engine for rule-based governance with database persistence.

    Evaluates actions against policies and permissions.
    Uses in-memory cache for performance with database as source of truth.
    """

    def __init__(
        self,
        db_session: Optional[AsyncSession] = None,
        event_stream: Optional["EventStream"] = None
    ):
        """Initialize Policy Engine with database and optional EventStream integration"""
        # Database session
        self.db_session = db_session
        
        # EventStream integration (Sprint 3)
        self.event_stream = event_stream

        # In-memory cache (policies loaded from DB)
        self._policy_cache: Dict[str, PolicySchema] = {}
        self._cache_loaded = False

        # Permissions (still in-memory for now)
        self.permissions: Dict[str, Permission] = {}

        # Metrics
        self.total_evaluations = 0
        self.total_allows = 0
        self.total_denies = 0
        self.total_warnings = 0
        self.cache_hits = 0
        self.cache_misses = 0

        self.start_time = time.time()

        logger.info(
            f"🔐 Policy Engine initialized (v{MODULE_VERSION}, EventStream: %s, DB: %s)",
            "enabled" if event_stream else "disabled",
            "connected" if db_session else "disconnected"
        )

    async def _ensure_cache_loaded(self) -> None:
        """Ensure the in-memory cache is loaded from database"""
        if not self._cache_loaded and self.db_session:
            await self._load_cache_from_db()

    async def _load_cache_from_db(self) -> None:
        """Load active policies from database into memory cache"""
        if not self.db_session:
            logger.warning("No database session available - using empty cache")
            return

        try:
            result = await self.db_session.execute(
                select(PolicyModel)
                .where(PolicyModel.is_active == True)
                .where(PolicyModel.is_deleted == False)
                .order_by(desc(PolicyModel.priority))
            )
            policies = result.scalars().all()

            self._policy_cache = {}
            for policy in policies:
                self._policy_cache[str(policy.id)] = self._db_to_schema(policy)

            self._cache_loaded = True
            logger.info(f"✅ Loaded {len(self._policy_cache)} policies into cache")

        except Exception as e:
            logger.error(f"Failed to load policy cache: {e}")
            # Don't raise - engine can still work with empty cache

    async def _invalidate_cache(self) -> None:
        """Invalidate the in-memory cache (call after DB changes)"""
        self._cache_loaded = False
        self._policy_cache.clear()
        logger.debug("Policy cache invalidated")

    def _db_to_schema(self, db_policy: PolicyModel) -> PolicySchema:
        """Convert database Policy model to Pydantic schema"""
        # Convert conditions JSON to PolicyRule objects
        rules = []
        if db_policy.conditions:
            # For now, create a single rule from the policy conditions
            # In future versions, rules could be a separate table
            rule_conditions = [
                PolicyCondition(
                    field=cond.get("field", ""),
                    operator=PolicyConditionOperator(cond.get("operator", "==")),
                    value=cond.get("value")
                )
                for cond in db_policy.conditions
            ]
            
            rules.append(PolicyRule(
                rule_id=f"{db_policy.name}_rule",
                name=f"{db_policy.display_name or db_policy.name} Rule",
                description=db_policy.description or "",
                effect=PolicyEffect(db_policy.effect),
                conditions=rule_conditions,
                priority=db_policy.priority,
                enabled=db_policy.is_active,
                metadata=db_policy.metadata or {}
            ))

        return PolicySchema(
            policy_id=str(db_policy.id),
            name=db_policy.display_name or db_policy.name,
            version=db_policy.version,
            description=db_policy.description or "",
            rules=rules,
            default_effect=PolicyEffect(db_policy.effect),
            enabled=db_policy.is_active,
            created_at=db_policy.created_at,
            updated_at=db_policy.updated_at,
            created_by=str(db_policy.created_by) if db_policy.created_by else None,
            metadata={
                "name": db_policy.name,
                "resource_pattern": db_policy.resource_pattern,
                "action_pattern": db_policy.action_pattern,
                "tags": db_policy.tags or [],
                **(db_policy.metadata or {})
            }
        )

    async def _emit_event_safe(
        self,
        event_type: str,
        policy: Optional[PolicySchema] = None,
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
        """
        if self.event_stream is None or Event is None:
            logger.debug("[PolicyEngine] EventStream not available, skipping event")
            return

        try:
            payload = {}

            if context:
                payload["agent_id"] = context.agent_id
                if context.agent_role:
                    payload["agent_role"] = context.agent_role
                payload["action"] = context.action
                if context.resource:
                    payload["resource"] = context.resource

            if policy:
                payload["policy_id"] = policy.policy_id
                payload["policy_name"] = policy.name

            if rule:
                payload["rule_id"] = rule.rule_id
                payload["rule_name"] = rule.name

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

            if changes:
                payload["changes"] = changes

            if warnings:
                payload["warnings"] = warnings

            if evaluation_time_ms is not None:
                payload["evaluation_time_ms"] = evaluation_time_ms

            payload[f"{event_type.split('.')[1]}_at"] = time.time()

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

    async def _log_audit_event(
        self,
        context: PolicyEvaluationContext,
        result: PolicyEvaluationResult,
        policy_matched: Optional[str] = None,
        rule_matched: Optional[str] = None,
        risk_tier: str = "low",
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Log audit event to database.
        
        Records all policy decisions for compliance and security analysis.
        """
        if not self.db_session:
            logger.debug("No DB session available - skipping audit log")
            return

        try:
            audit_entry = AuthAuditLog(
                id=uuid.uuid4(),
                timestamp=datetime.utcnow(),
                principal_id=context.agent_id,
                principal_type=context.environment.get("principal_type", "agent"),
                action=context.action,
                resource_id=context.resource,
                decision=result.effect.value,
                reason=result.reason,
                policy_matched=policy_matched,
                rule_matched=rule_matched,
                risk_tier=risk_tier,
                ip_address=ip_address or context.environment.get("ip_address"),
                request_id=request_id or context.environment.get("request_id"),
                session_id=context.environment.get("session_id"),
                metadata={
                    "allowed": result.allowed,
                    "warnings": result.warnings,
                    "requires_audit": result.requires_audit,
                    "params": context.params,
                    "environment": {k: v for k, v in context.environment.items() 
                                   if k not in ["ip_address", "request_id", "session_id", "principal_type"]}
                },
                agent_id=context.agent_id,
                organization_id=context.environment.get("organization_id"),
            )

            self.db_session.add(audit_entry)
            await self.db_session.commit()

            logger.debug(f"[PolicyEngine] Audit logged: {audit_entry.id}")

        except Exception as e:
            logger.error(f"[PolicyEngine] Failed to log audit event: {e}")
            # Don't raise - audit failures shouldn't block operations
            try:
                await self.db_session.rollback()
            except:
                pass

    async def evaluate(
        self, 
        context: PolicyEvaluationContext,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> PolicyEvaluationResult:
        """
        Evaluate if an action is allowed based on policies.

        Args:
            context: Evaluation context (agent, action, resource, etc.)
            ip_address: Optional IP address for audit logging
            request_id: Optional request ID for correlation

        Returns:
            PolicyEvaluationResult with decision and reason
        """
        self.total_evaluations += 1
        start_time = time.time()

        logger.debug(
            f"🔍 Evaluating: agent={context.agent_id}, action={context.action}"
        )

        # Ensure cache is loaded
        await self._ensure_cache_loaded()

        # Get active policies from cache
        active_policies = [
            p for p in self._policy_cache.values() 
            if p.enabled and self._policy_matches_context(p, context)
        ]

        if not active_policies:
            logger.warning("⚠️ No matching active policies - defaulting to DENY")
            result = PolicyEvaluationResult(
                allowed=False,
                effect=PolicyEffect.DENY,
                reason="No matching policies configured - default deny",
            )
            self.total_denies += 1
            
            # Log audit event
            await self._log_audit_event(
                context, result, 
                risk_tier="medium",
                ip_address=ip_address,
                request_id=request_id
            )
            return result

        # Collect and sort all rules by priority
        all_rules = []
        for policy in active_policies:
            for rule in policy.rules:
                if rule.enabled:
                    all_rules.append((policy, rule))

        all_rules.sort(key=lambda x: x[1].priority, reverse=True)

        # Find first matching rule
        matched_policy_id = None
        matched_rule_id = None
        risk_tier = "low"

        for policy, rule in all_rules:
            if await self._rule_matches(rule, context):
                logger.info(
                    f"✅ Matched rule: {rule.name} (effect={rule.effect.value})"
                )
                matched_policy_id = policy.policy_id
                matched_rule_id = rule.rule_id
                
                # Determine risk tier based on effect
                if rule.effect == PolicyEffect.DENY:
                    risk_tier = "high"
                elif rule.effect == PolicyEffect.AUDIT:
                    risk_tier = "medium"

                result = self._apply_effect(rule.effect, policy, rule, context)
                self._update_metrics(result)

                # Foundation double-check
                if FOUNDATION_AVAILABLE and result.allowed:
                    foundation_check = await self._check_foundation(context)
                    if not foundation_check:
                        logger.warning("⚠️ Policy allowed but Foundation blocked - DENY")
                        result.allowed = False
                        result.effect = PolicyEffect.DENY
                        result.reason = f"{result.reason} (overridden by Foundation safety check)"
                        self.total_denies += 1
                        risk_tier = "critical"

                # Emit events
                evaluation_time_ms = (time.time() - start_time) * 1000
                await self._emit_event_safe(
                    event_type="policy.evaluated",
                    policy=policy,
                    rule=rule,
                    context=context,
                    result=result,
                    evaluation_time_ms=evaluation_time_ms,
                )

                if not result.allowed:
                    await self._emit_event_safe(
                        event_type="policy.denied",
                        policy=policy,
                        rule=rule,
                        context=context,
                        result=result,
                    )

                if result.effect == PolicyEffect.WARN:
                    await self._emit_event_safe(
                        event_type="policy.warning_triggered",
                        policy=policy,
                        rule=rule,
                        context=context,
                        warnings=result.warnings,
                    )

                if result.effect == PolicyEffect.AUDIT:
                    await self._emit_event_safe(
                        event_type="policy.audit_required",
                        policy=policy,
                        rule=rule,
                        context=context,
                        result=result,
                    )

                # Log audit event
                await self._log_audit_event(
                    context, result,
                    policy_matched=matched_policy_id,
                    rule_matched=matched_rule_id,
                    risk_tier=risk_tier,
                    ip_address=ip_address,
                    request_id=request_id
                )

                return result

        # No rules matched - use default effect
        logger.debug("No rules matched - using default effect")
        
        # Find the highest priority policy's default effect
        default_effect = PolicyEffect.DENY
        for policy in sorted(active_policies, key=lambda p: p.rules[0].priority if p.rules else 0, reverse=True):
            default_effect = policy.default_effect
            break

        result = PolicyEvaluationResult(
            allowed=(default_effect == PolicyEffect.ALLOW),
            effect=default_effect,
            reason=f"No matching rules - applied default effect: {default_effect.value}",
        )

        self._update_metrics(result)

        # Emit events
        evaluation_time_ms = (time.time() - start_time) * 1000
        await self._emit_event_safe(
            event_type="policy.evaluated",
            policy=None,
            rule=None,
            context=context,
            result=result,
            evaluation_time_ms=evaluation_time_ms,
        )

        if not result.allowed:
            await self._emit_event_safe(
                event_type="policy.denied",
                policy=None,
                rule=None,
                context=context,
                result=result,
            )

        # Log audit event
        await self._log_audit_event(
            context, result,
            risk_tier="low",
            ip_address=ip_address,
            request_id=request_id
        )

        return result

    def _policy_matches_context(self, policy: PolicySchema, context: PolicyEvaluationContext) -> bool:
        """Check if policy applies to the given context based on resource/action patterns"""
        metadata = policy.metadata or {}
        resource_pattern = metadata.get("resource_pattern", "*")
        action_pattern = metadata.get("action_pattern", "*")
        
        resource_match = fnmatch.fnmatch(context.resource or "*", resource_pattern)
        action_match = fnmatch.fnmatch(context.action, action_pattern)
        
        return resource_match and action_match

    async def _rule_matches(
        self, rule: PolicyRule, context: PolicyEvaluationContext
    ) -> bool:
        """Check if all conditions in a rule match the context (AND logic)"""
        if not rule.conditions:
            return True

        for condition in rule.conditions:
            if not await self._condition_matches(condition, context):
                return False

        return True

    async def _condition_matches(
        self, condition: PolicyCondition, context: PolicyEvaluationContext
    ) -> bool:
        """Check if a single condition matches"""
        field_value = self._get_field_value(condition.field, context)
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
            return expected in str(field_value) if field_value is not None else False
        elif operator == PolicyConditionOperator.MATCHES:
            if field_value is None:
                return False
            return bool(re.match(expected, str(field_value)))
        elif operator == PolicyConditionOperator.IN:
            return field_value in expected if isinstance(expected, list) else False
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False

    def _get_field_value(self, field: str, context: PolicyEvaluationContext) -> Any:
        """Get field value from context using dot notation"""
        parts = field.split(".")

        if len(parts) == 1:
            return getattr(context, field, None)

        if len(parts) == 2:
            root, key = parts
            if root == "environment":
                return context.environment.get(key)
            elif root == "params":
                return context.params.get(key)
            elif root == "agent":
                return getattr(context, f"agent_{key}", None)

        logger.warning(f"Field not found: {field}")
        return None

    def _apply_effect(
        self,
        effect: PolicyEffect,
        policy: PolicySchema,
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
        """Double-check with Foundation layer for safety"""
        if not FOUNDATION_AVAILABLE:
            return True

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
            return True

    def _update_metrics(self, result: PolicyEvaluationResult):
        """Update metrics based on evaluation result"""
        if result.allowed:
            self.total_allows += 1
        else:
            self.total_denies += 1

        if result.effect == PolicyEffect.WARN:
            self.total_warnings += 1

    # ========================================================================
    # Policy CRUD Operations (with DB persistence)
    # ========================================================================

    async def create_policy(
        self, 
        request: PolicyCreateRequest,
        created_by: Optional[uuid.UUID] = None
    ) -> Optional[PolicySchema]:
        """Create a new policy in database"""
        if not self.db_session:
            logger.error("No database session available")
            return None

        try:
            # Convert conditions from rules
            conditions = []
            if request.rules:
                for rule in request.rules:
                    for cond in rule.conditions:
                        conditions.append({
                            "field": cond.field,
                            "operator": cond.operator.value,
                            "value": cond.value
                        })

            # Create DB model
            db_policy = PolicyModel(
                id=uuid.uuid4(),
                name=request.name.lower().replace(" ", "_"),
                display_name=request.name,
                description=request.description,
                version=request.version,
                resource_pattern="*",  # Default, can be extended
                action_pattern="*",    # Default, can be extended
                effect=request.default_effect.value,
                conditions=conditions,
                priority=max((r.priority for r in request.rules), default=0) if request.rules else 0,
                is_active=request.enabled,
                created_by=created_by,
                metadata={"rules_count": len(request.rules)} if request.rules else {}
            )

            self.db_session.add(db_policy)
            await self.db_session.commit()
            await self.db_session.refresh(db_policy)

            # Invalidate cache to include new policy
            await self._invalidate_cache()

            logger.info(f"✅ Created policy: {db_policy.name} ({db_policy.id})")

            # Emit event
            policy_schema = self._db_to_schema(db_policy)
            await self._emit_event_safe(
                event_type="policy.created",
                policy=policy_schema,
            )

            return policy_schema

        except Exception as e:
            logger.error(f"Failed to create policy: {e}")
            await self.db_session.rollback()
            return None

    async def get_policy(self, policy_id: str) -> Optional[PolicySchema]:
        """Get policy by ID from cache or database"""
        await self._ensure_cache_loaded()
        
        # Try cache first
        if policy_id in self._policy_cache:
            self.cache_hits += 1
            return self._policy_cache[policy_id]

        # Try database
        if self.db_session:
            try:
                result = await self.db_session.get(PolicyModel, uuid.UUID(policy_id))
                if result and result.is_active and not result.is_deleted:
                    self.cache_misses += 1
                    return self._db_to_schema(result)
            except Exception as e:
                logger.error(f"Failed to get policy: {e}")

        return None

    async def list_policies(
        self, 
        include_inactive: bool = False
    ) -> List[PolicySchema]:
        """List all policies from database"""
        if not self.db_session:
            await self._ensure_cache_loaded()
            return list(self._policy_cache.values())

        try:
            query = select(PolicyModel).where(PolicyModel.is_deleted == False)
            if not include_inactive:
                query = query.where(PolicyModel.is_active == True)
            query = query.order_by(desc(PolicyModel.priority))

            result = await self.db_session.execute(query)
            policies = result.scalars().all()

            return [self._db_to_schema(p) for p in policies]

        except Exception as e:
            logger.error(f"Failed to list policies: {e}")
            return []

    async def update_policy(
        self, 
        policy_id: str, 
        request: PolicyUpdateRequest,
        updated_by: Optional[uuid.UUID] = None
    ) -> Optional[PolicySchema]:
        """Update an existing policy"""
        if not self.db_session:
            logger.error("No database session available")
            return None

        try:
            result = await self.db_session.get(PolicyModel, uuid.UUID(policy_id))
            if not result or result.is_deleted:
                return None

            # Track changes for event
            changes = {}

            if request.name is not None:
                changes["name"] = {"old": result.display_name, "new": request.name}
                result.display_name = request.name
                result.name = request.name.lower().replace(" ", "_")

            if request.description is not None:
                changes["description"] = {"old": result.description, "new": request.description}
                result.description = request.description

            if request.rules is not None:
                changes["rules"] = {"old_count": len(result.conditions), "new_count": len(request.rules)}
                # Convert rules to conditions
                conditions = []
                for rule in request.rules:
                    for cond in rule.conditions:
                        conditions.append({
                            "field": cond.field,
                            "operator": cond.operator.value,
                            "value": cond.value
                        })
                result.conditions = conditions
                result.priority = max((r.priority for r in request.rules), default=0)

            if request.default_effect is not None:
                changes["effect"] = {"old": result.effect, "new": request.default_effect.value}
                result.effect = request.default_effect.value

            if request.enabled is not None:
                changes["is_active"] = {"old": result.is_active, "new": request.enabled}
                result.is_active = request.enabled

            result.updated_by = updated_by
            result.updated_at = datetime.utcnow()

            await self.db_session.commit()
            await self.db_session.refresh(result)

            # Invalidate cache
            await self._invalidate_cache()

            logger.info(f"✅ Updated policy: {policy_id}")

            # Emit event
            policy_schema = self._db_to_schema(result)
            await self._emit_event_safe(
                event_type="policy.updated",
                policy=policy_schema,
                changes=changes,
            )

            return policy_schema

        except Exception as e:
            logger.error(f"Failed to update policy: {e}")
            await self.db_session.rollback()
            return None

    async def delete_policy(self, policy_id: str) -> bool:
        """Soft delete a policy"""
        if not self.db_session:
            logger.error("No database session available")
            return False

        try:
            result = await self.db_session.get(PolicyModel, uuid.UUID(policy_id))
            if not result or result.is_deleted:
                return False

            # Prevent deletion of system policies
            if result.is_system:
                logger.warning(f"Cannot delete system policy: {policy_id}")
                return False

            # Soft delete
            result.is_deleted = True
            result.deleted_at = datetime.utcnow()
            result.is_active = False

            await self.db_session.commit()

            # Invalidate cache
            await self._invalidate_cache()

            logger.info(f"✅ Deleted policy: {policy_id}")

            # Emit event
            policy_schema = self._db_to_schema(result)
            await self._emit_event_safe(
                event_type="policy.deleted",
                policy=policy_schema,
            )

            return True

        except Exception as e:
            logger.error(f"Failed to delete policy: {e}")
            await self.db_session.rollback()
            return False

    # ========================================================================
    # Audit Log Queries
    # ========================================================================

    async def get_audit_logs(
        self,
        principal_id: Optional[str] = None,
        action: Optional[str] = None,
        decision: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query audit logs with optional filters"""
        if not self.db_session:
            return []

        try:
            query = select(AuthAuditLog).order_by(desc(AuthAuditLog.timestamp))

            if principal_id:
                query = query.where(AuthAuditLog.principal_id == principal_id)
            if action:
                query = query.where(AuthAuditLog.action == action)
            if decision:
                query = query.where(AuthAuditLog.decision == decision)

            query = query.limit(limit).offset(offset)

            result = await self.db_session.execute(query)
            logs = result.scalars().all()

            return [log.to_dict() for log in logs]

        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            return []

    # ========================================================================
    # Stats & Health
    # ========================================================================

    async def get_stats(self) -> PolicyStats:
        """Get policy system statistics"""
        await self._ensure_cache_loaded()

        total_rules = sum(len(p.rules) for p in self._policy_cache.values())
        active_policies = sum(1 for p in self._policy_cache.values() if p.enabled)

        return PolicyStats(
            total_policies=len(self._policy_cache),
            active_policies=active_policies,
            total_rules=total_rules,
            total_evaluations=self.total_evaluations,
            total_allows=self.total_allows,
            total_denies=self.total_denies,
            total_warnings=self.total_warnings,
        )

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "cache_loaded": self._cache_loaded,
            "cached_policies": len(self._policy_cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
        }


# ============================================================================
# Factory Function
# ============================================================================

async def get_policy_engine(
    db_session: AsyncSession,
    event_stream: Optional["EventStream"] = None
) -> PolicyEngine:
    """
    Factory function to create a Policy Engine instance.

    Args:
        db_session: Database session for persistence
        event_stream: Optional EventStream for event publishing

    Returns:
        PolicyEngine instance
    """
    engine = PolicyEngine(db_session=db_session, event_stream=event_stream)
    await engine._ensure_cache_loaded()
    return engine


# Legacy functions (kept for backward compatibility)
_policy_engine_instance: Optional[PolicyEngine] = None


def get_policy_engine_sync(
    event_stream: Optional["EventStream"] = None
) -> PolicyEngine:
    """
    Synchronous factory for backward compatibility.
    NOTE: This creates an engine without DB session. Use get_policy_engine() for full functionality.
    """
    global _policy_engine_instance
    if _policy_engine_instance is None:
        _policy_engine_instance = PolicyEngine(db_session=None, event_stream=event_stream)
    return _policy_engine_instance


async def get_health() -> PolicyHealth:
    """Legacy health check"""
    return PolicyHealth(status="ok", timestamp=datetime.now(timezone.utc))


async def get_info() -> PolicyInfo:
    """Legacy info endpoint"""
    return PolicyInfo(
        name=MODULE_NAME,
        version=MODULE_VERSION,
        config={"persistence": "database", "caching": "enabled"},
    )
