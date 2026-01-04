"""
Governor v1 Service (Phase 2a + 2b)

Central decision engine for agent creation governance.

The Governor v1 makes formal, deterministic decisions on agent creation by:
1. Evaluating policy rules (Groups A-E)
2. Computing risk tier and quarantine status (with manifest overrides)
3. Applying constraints (defaults + manifest-driven reductions)
4. Emitting audit events (dual-write)
5. Returning immutable DecisionResult

Architecture:
- Pure functions for rule evaluation (no side effects)
- Fail-closed event emission (at least one write succeeds)
- Complete audit trail for every decision
- No ML, no LLMs, no interpretation - mechanical only
- Monotonic reductions (can only reduce, never expand)

Phase 2b Extensions:
- Manifest-driven governance (YAML-based policy configuration)
- Constraint reduction engine with monotonicity validation
- Risk tier overrides from manifests
- Locked field enforcement

Author: Governor v1 System
Version: 2b.1
Created: 2026-01-02
Updated: 2026-01-02 (Phase 2b)
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from backend.brain.agents.genesis_agent.dna_schema import AgentType
from backend.brain.agents.genesis_agent.events import AuditLog
from backend.brain.governor.constraints.defaults import get_default_constraints
from backend.brain.governor.constraints.schema import EffectiveConstraints
from backend.brain.governor.decision.models import (
    ActorContext,
    DecisionRequest,
    DecisionResult,
    DecisionType,
    ReasonCode,
    RequestContext,
    RiskTier,
)
from backend.brain.governor.events import GovernorEvents
from backend.brain.governor.manifests.loader import get_manifest_loader
from backend.brain.governor.manifests.schema import GovernanceManifest
from backend.brain.governor.policy import rules
from backend.brain.governor.reductions.reducer import ConstraintReducer
from backend.brain.governor.reductions.rules import (
    ReductionContext,
    get_applicable_reductions,
)
from backend.brain.governor.enforcement.locks import (
    LockedFieldEnforcer,
    PolicyViolationError,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Governor Configuration
# ============================================================================

class GovernorConfig:
    """
    Configuration for Governor v1.

    Attributes:
        policy_version: Policy version (e.g., "1.0.0")
        ruleset_version: Ruleset version (e.g., "2a")
        template_allowlist: List of allowed template names
        reserve_ratio: Budget reserve ratio (0.0-1.0)
        max_population: Max population per AgentType
    """

    def __init__(
        self,
        policy_version: str = "1.0.0",
        ruleset_version: str = "2a",
        template_allowlist: Optional[List[str]] = None,
        reserve_ratio: float = 0.2,
        max_population: Optional[Dict[AgentType, int]] = None
    ):
        self.policy_version = policy_version
        self.ruleset_version = ruleset_version
        self.template_allowlist = template_allowlist or [
            "worker_base",
            "analyst_base",
            "builder_base",
            "memory_base"
        ]
        self.reserve_ratio = reserve_ratio
        self.max_population = max_population or {
            # CRITICAL agents: strict limits
            AgentType.GENESIS: 1,
            AgentType.GOVERNOR: 1,
            AgentType.SUPERVISOR: 3,
            AgentType.LIGASE: 5,
            AgentType.KARMA: 3,
            # Standard agents: higher limits
            AgentType.WORKER: 50,
            AgentType.ANALYST: 20,
            AgentType.BUILDER: 10,
            AgentType.MEMORY: 30,
        }


# ============================================================================
# Governor v1 Service
# ============================================================================

class Governor:
    """
    Governor v1 - Agent Creation Governance.

    The Governor makes formal decisions on agent creation requests by
    evaluating deterministic policy rules and applying constraints.

    Decision Flow:
    1. Receive DecisionRequest from Genesis
    2. Emit decision.requested event
    3. Evaluate all policy rules (Groups A-E)
    4. Compute risk tier and quarantine status
    5. Apply constraints (defaults + reductions if approved)
    6. Emit decision.evaluated event
    7. Emit decision.approved or decision.rejected event
    8. Return immutable DecisionResult

    Example:
        >>> governor = Governor(
        ...     redis_client=redis,
        ...     audit_log=audit,
        ...     config=GovernorConfig()
        ... )
        >>>
        >>> result = await governor.evaluate_creation(request)
        >>>
        >>> if result.approved:
        ...     # Apply constraints to agent
        ...     pass
        ... else:
        ...     # Reject creation
        ...     raise Exception(f"Rejected: {result.reason_detail}")
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        audit_log: AuditLog,
        config: Optional[GovernorConfig] = None,
        killswitch_active: bool = False,
        available_credits: int = 10000,
        population_counts: Optional[Dict[AgentType, int]] = None,
        manifest: Optional[GovernanceManifest] = None
    ):
        """
        Initialize Governor v1.

        Args:
            redis_client: Redis client for event pub/sub
            audit_log: Audit log for persistence
            config: Governor configuration (uses defaults if None)
            killswitch_active: Whether kill switch is active
            available_credits: Available credits in budget
            population_counts: Current population per AgentType
            manifest: Governance manifest (loads default if None)
        """
        self.redis = redis_client
        self.audit_log = audit_log
        self.config = config or GovernorConfig()
        self.killswitch_active = killswitch_active
        self.available_credits = available_credits
        self.population_counts = population_counts or {}

        # Phase 2b: Load governance manifest
        if manifest is None:
            manifest_loader = get_manifest_loader()
            try:
                self.manifest = manifest_loader.get_default_manifest()
                logger.info(
                    f"Loaded governance manifest: {self.manifest.name} "
                    f"v{self.manifest.policy_version}"
                )
            except Exception as e:
                logger.error(f"Failed to load governance manifest: {e}")
                # Fallback: create minimal manifest
                self.manifest = None
        else:
            self.manifest = manifest

        # Phase 2b: Initialize reduction engine
        self.reducer = ConstraintReducer()

        # Phase 2c: Initialize locked field enforcer
        self.locked_field_enforcer = LockedFieldEnforcer(
            manifest_loader=get_manifest_loader()
        )

    # ========================================================================
    # Main Decision Evaluation
    # ========================================================================

    async def evaluate_creation(
        self,
        request: DecisionRequest
    ) -> DecisionResult:
        """
        Evaluate agent creation request and make governance decision.

        This is the main entry point for Governor v1. It orchestrates:
        1. Event emission (decision.requested)
        2. Policy rule evaluation (Groups A-E)
        3. Risk & quarantine determination
        4. Constraint application (if approved)
        5. Event emission (decision.evaluated, decision.approved/rejected)
        6. DecisionResult construction

        Args:
            request: Decision request from Genesis

        Returns:
            DecisionResult with decision, constraints, audit metadata

        Raises:
            Exception: If event emission fails (fail-closed)

        Example:
            >>> result = await governor.evaluate_creation(request)
            >>> print(result.approved, result.reason_code)
            True APPROVED_WITH_CONSTRAINTS
        """
        start_time = time.time()

        # Emit decision.requested event
        await GovernorEvents.decision_requested(
            decision_id=request.decision_id,
            request_id=request.request_id,
            template_name=request.template_name,
            actor_role=request.actor.role,
            has_customizations=request.context.has_customizations,
            redis_client=self.redis,
            audit_log=self.audit_log
        )

        # Evaluate policy rules
        approved, reason_code, reason_detail, triggered_rules = await self._evaluate_rules(request)

        # Compute risk tier and quarantine
        agent_type = AgentType(request.agent_dna["metadata"]["type"])
        risk_tier, quarantine = self._compute_risk_and_quarantine(
            agent_type,
            request.context.has_customizations
        )

        # Phase 2c: Validate locked fields
        # This check happens BEFORE constraint application to catch violations early
        if approved and request.context.has_customizations:
            try:
                # Extract customization DNA from request
                customization_dna = self._extract_customization_dna(request)

                # Validate against locked fields
                self.locked_field_enforcer.validate_dna_against_locks(
                    agent_type=agent_type,
                    dna=customization_dna,
                    manifest_name="defaults"
                )
            except PolicyViolationError as e:
                # Locked field violation detected - REJECT immediately
                logger.error(
                    f"Locked field violation detected for {request.decision_id}: "
                    f"{[v.field_path for v in e.violations]}"
                )

                # Emit locked field violation event
                violations_data = [v.model_dump() for v in e.violations]
                await GovernorEvents.locked_field_violation(
                    decision_id=request.decision_id,
                    agent_type=agent_type.value,
                    violations=violations_data,
                    dna_hash=self.locked_field_enforcer.get_dna_hash(customization_dna),
                    redis_client=self.redis,
                    audit_log=self.audit_log
                )

                # Mark as rejected
                approved = False
                reason_code = ReasonCode.REJECTED_LOCKED_FIELD_VIOLATION
                reason_detail = (
                    f"Locked field violation: {[v.field_path for v in e.violations]}. "
                    f"These fields are immutable for compliance (DSGVO Art. 22, EU AI Act Art. 16)."
                )

        # Apply constraints (if approved)
        constraints = None
        if approved:
            constraints = await self._apply_constraints(request, agent_type, risk_tier)

        # Determine decision type
        if not approved:
            decision_type = DecisionType.REJECT
        elif request.context.has_customizations:
            decision_type = DecisionType.APPROVE_WITH_CONSTRAINTS
        else:
            decision_type = DecisionType.APPROVE

        # Evaluation duration
        evaluation_duration_ms = (time.time() - start_time) * 1000

        # Emit decision.evaluated event
        evaluated_rules = [f"A1", "A2", "B1", "B2", "C1", "C2", "C3", "D1", "D2", "E3"]
        await GovernorEvents.decision_evaluated(
            decision_id=request.decision_id,
            evaluation_duration_ms=evaluation_duration_ms,
            evaluated_rules=evaluated_rules,
            triggered_rules=triggered_rules,
            redis_client=self.redis,
            audit_log=self.audit_log
        )

        # Emit decision.approved or decision.rejected event
        if approved:
            await GovernorEvents.decision_approved(
                decision_id=request.decision_id,
                decision_type=decision_type.value,
                reason_code=reason_code.value,
                risk_tier=risk_tier.value,
                quarantine=quarantine,
                redis_client=self.redis,
                audit_log=self.audit_log
            )
        else:
            await GovernorEvents.decision_rejected(
                decision_id=request.decision_id,
                reason_code=reason_code.value,
                reason_detail=reason_detail,
                triggered_rules=triggered_rules,
                redis_client=self.redis,
                audit_log=self.audit_log
            )

        # Construct DecisionResult
        result = DecisionResult(
            decision_id=request.decision_id,
            request_id=request.request_id,
            approved=approved,
            decision_type=decision_type,
            reason_code=reason_code,
            reason_detail=reason_detail,
            risk_tier=risk_tier,
            constraints=constraints.model_dump() if constraints else None,
            quarantine=quarantine,
            policy_version=self.config.policy_version,
            ruleset_version=self.config.ruleset_version,
            evaluated_rules=evaluated_rules,
            triggered_rules=triggered_rules,
            evaluation_duration_ms=evaluation_duration_ms,
            actor_user_id=request.actor.user_id,
            actor_role=request.actor.role,
            template_name=request.template_name,
            template_hash=request.template_hash,
            dna_hash=request.dna_hash
        )

        return result

    # ========================================================================
    # Policy Rule Evaluation
    # ========================================================================

    async def _evaluate_rules(
        self,
        request: DecisionRequest
    ) -> tuple[bool, ReasonCode, str, List[str]]:
        """
        Evaluate all policy rules (Groups A-E).

        Args:
            request: Decision request

        Returns:
            (approved, reason_code, reason_detail, triggered_rules)

        Example:
            >>> approved, code, detail, triggered = await governor._evaluate_rules(request)
        """
        triggered_rules = []

        # Group A: Role & Authorization
        approved_a1, code_a1, detail_a1, trig_a1 = rules.rule_a1_require_system_admin(
            request.actor.role
        )
        if trig_a1:
            triggered_rules.append("A1")
        if not approved_a1:
            return (False, code_a1, detail_a1, triggered_rules)

        approved_a2, code_a2, detail_a2, trig_a2 = rules.rule_a2_killswitch_check(
            self.killswitch_active
        )
        if trig_a2:
            triggered_rules.append("A2")
        if not approved_a2:
            return (False, code_a2, detail_a2, triggered_rules)

        # Group B: Template Integrity
        approved_b1, code_b1, detail_b1, trig_b1 = rules.rule_b1_template_hash_required(
            request.template_hash
        )
        if trig_b1:
            triggered_rules.append("B1")
        if not approved_b1:
            return (False, code_b1, detail_b1, triggered_rules)

        approved_b2, code_b2, detail_b2, trig_b2 = rules.rule_b2_template_in_allowlist(
            request.template_name,
            self.config.template_allowlist
        )
        if trig_b2:
            triggered_rules.append("B2")
        if not approved_b2:
            return (False, code_b2, detail_b2, triggered_rules)

        # Group C: DNA Constraints
        approved_c1, code_c1, detail_c1, trig_c1 = rules.rule_c1_ethics_human_override_immutable(
            request.agent_dna
        )
        if trig_c1:
            triggered_rules.append("C1")
        if not approved_c1:
            return (False, code_c1, detail_c1, triggered_rules)

        agent_type = AgentType(request.agent_dna["metadata"]["type"])

        approved_c2, code_c2, detail_c2, trig_c2 = rules.rule_c2_network_access_cap(
            request.agent_dna,
            agent_type
        )
        if trig_c2:
            triggered_rules.append("C2")
        if not approved_c2:
            return (False, code_c2, detail_c2, triggered_rules)

        approved_c3, code_c3, detail_c3, trig_c3 = rules.rule_c3_autonomy_level_cap(
            request.agent_dna,
            agent_type
        )
        if trig_c3:
            triggered_rules.append("C3")
        if not approved_c3:
            return (False, code_c3, detail_c3, triggered_rules)

        # Group D: Budget & Population Limits
        # Estimate creation cost (simple: 10 credits per agent)
        creation_cost = 10

        approved_d1, code_d1, detail_d1, trig_d1 = rules.rule_d1_creation_cost_affordable(
            self.available_credits,
            creation_cost,
            self.config.reserve_ratio
        )
        if trig_d1:
            triggered_rules.append("D1")
        if not approved_d1:
            return (False, code_d1, detail_d1, triggered_rules)

        current_population = self.population_counts.get(agent_type, 0)

        approved_d2, code_d2, detail_d2, trig_d2 = rules.rule_d2_population_limit(
            agent_type,
            current_population,
            self.config.max_population
        )
        if trig_d2:
            triggered_rules.append("D2")
        if not approved_d2:
            return (False, code_d2, detail_d2, triggered_rules)

        # Group E: Capability Escalation (Phase 2a: REJECT)
        approved_e3, code_e3, detail_e3, trig_e3 = rules.rule_e3_capability_escalation_reject(
            request.context.customization_fields
        )
        if trig_e3:
            triggered_rules.append("E3")
        if not approved_e3:
            return (False, code_e3, detail_e3, triggered_rules)

        # All rules passed
        if request.context.has_customizations:
            return (
                True,
                ReasonCode.APPROVED_WITH_CONSTRAINTS,
                "Approved with constraints (customizations detected)",
                triggered_rules
            )
        else:
            return (
                True,
                ReasonCode.APPROVED_DEFAULT,
                "Approved with default constraints",
                triggered_rules
            )

    # ========================================================================
    # Risk & Quarantine
    # ========================================================================

    def _compute_risk_and_quarantine(
        self,
        agent_type: AgentType,
        has_customizations: bool
    ) -> tuple[RiskTier, bool]:
        """
        Compute risk tier and quarantine status (with manifest overrides).

        Phase 2b: Applies risk overrides from governance manifest:
        - if_customizations: Override risk tier if customizations present
        - if_template_not_in_allowlist: Override if template not allowed
        - if_capability_escalation: Override if escalation detected

        Args:
            agent_type: Agent type
            has_customizations: Whether request has customizations

        Returns:
            (risk_tier, quarantine)

        Example:
            >>> risk_tier, quarantine = governor._compute_risk_and_quarantine(
            ...     AgentType.GENESIS,
            ...     has_customizations=False
            ... )
            >>> assert risk_tier == RiskTier.CRITICAL
            >>> assert quarantine is True
        """
        # Rule E1: Critical agents are quarantined
        quarantine, _ = rules.rule_e1_critical_agents_quarantined(agent_type)

        # Rule E2: Customizations increase risk to at least MEDIUM
        risk_tier_str, _ = rules.rule_e2_customizations_increase_risk(has_customizations)

        # If critical agent, risk is always CRITICAL
        if quarantine:
            risk_tier_str = "CRITICAL"

        # Phase 2b: Apply risk overrides from manifest
        if self.manifest and self.manifest.risk_overrides:
            # if_customizations override
            if has_customizations and self.manifest.risk_overrides.if_customizations:
                override = self.manifest.risk_overrides.if_customizations
                risk_tier_str = self._escalate_risk_tier(risk_tier_str, override)

        risk_tier = RiskTier(risk_tier_str)

        return (risk_tier, quarantine)

    def _escalate_risk_tier(self, current: str, override: str) -> str:
        """
        Escalate risk tier (risk can only increase, never decrease).

        Args:
            current: Current risk tier string
            override: Override risk tier string

        Returns:
            Higher risk tier

        Example:
            >>> _escalate_risk_tier("LOW", "MEDIUM")  # → "MEDIUM"
            >>> _escalate_risk_tier("HIGH", "MEDIUM")  # → "HIGH" (no downgrade)
        """
        hierarchy = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

        current_level = hierarchy.get(current, 0)
        override_level = hierarchy.get(override, 0)

        # Risk can only escalate, never de-escalate
        if override_level > current_level:
            return override
        else:
            return current

    # ========================================================================
    # Constraint Application
    # ========================================================================

    async def _apply_constraints(
        self,
        request: DecisionRequest,
        agent_type: AgentType,
        risk_tier: RiskTier
    ) -> EffectiveConstraints:
        """
        Apply constraints based on AgentType, manifest, and reductions.

        Phase 2b: Implements manifest-driven constraint reductions:
        1. Get base constraints (defaults for AgentType)
        2. Load governance manifest
        3. Determine applicable reductions (via reduction rules)
        4. Apply reductions incrementally (with monotonicity validation)
        5. Emit events (constraints.reduced, manifest.applied)

        Args:
            request: Decision request (for context)
            agent_type: Agent type
            risk_tier: Computed risk tier (for reduction conditions)

        Returns:
            EffectiveConstraints (after reductions)

        Raises:
            Exception: If monotonicity validation fails

        Example:
            >>> constraints = await governor._apply_constraints(
            ...     request,
            ...     AgentType.WORKER,
            ...     RiskTier.MEDIUM
            ... )
        """
        # 1. Get base constraints (defaults for AgentType)
        base_constraints = get_default_constraints(agent_type)

        # If no manifest loaded, return base constraints
        if self.manifest is None:
            logger.warning("No governance manifest loaded, using base constraints")
            return base_constraints

        # 2. Build reduction context
        reduction_context = ReductionContext(
            has_customizations=request.context.has_customizations,
            customization_fields=request.context.customization_fields,
            risk_tier=risk_tier,
            agent_type=agent_type,
            agent_dna=request.agent_dna,
            current_population=self.population_counts.get(agent_type, 0),
            max_population=self.config.max_population,
            environment=None  # TODO: Extract from request context if available
        )

        # 3. Determine applicable reductions
        applicable_reductions = get_applicable_reductions(
            reduction_context,
            self.manifest.reductions
        )

        # If no reductions apply, return base constraints
        if not applicable_reductions:
            logger.debug("No reductions applicable, using base constraints")
            return base_constraints

        # 4. Apply reductions incrementally
        reduced_constraints = base_constraints
        reduction_summary = {}
        applied_reduction_names = []

        for section_name, reduction_spec in applicable_reductions:
            try:
                # Apply reduction
                new_constraints = self.reducer.reduce(reduced_constraints, reduction_spec)

                # Track before/after for summary
                self._build_reduction_summary(
                    reduced_constraints,
                    new_constraints,
                    reduction_summary
                )

                # Update constraints
                reduced_constraints = new_constraints
                applied_reduction_names.append(section_name)

                logger.debug(f"Applied reduction: {section_name}")

            except Exception as e:
                logger.error(
                    f"Failed to apply reduction '{section_name}': {e}. "
                    f"Skipping this reduction."
                )

        # 5. Emit constraints.reduced event (if reductions were applied)
        if applied_reduction_names:
            base_hash = self._compute_constraints_hash(base_constraints)
            reduced_hash = self._compute_constraints_hash(reduced_constraints)

            await GovernorEvents.constraints_reduced(
                decision_id=request.decision_id,
                applied_reductions=applied_reduction_names,
                reduction_summary=reduction_summary,
                base_constraints_hash=base_hash,
                reduced_constraints_hash=reduced_hash,
                redis_client=self.redis,
                audit_log=self.audit_log
            )

        # 6. Emit manifest.applied event
        await GovernorEvents.manifest_applied(
            decision_id=request.decision_id,
            manifest_name=self.manifest.name,
            manifest_version=str(self.manifest.manifest_version),
            policy_version=self.manifest.policy_version,
            applicable_sections=applied_reduction_names,
            risk_overrides={k: v for k, v in self.manifest.risk_overrides.model_dump().items() if v},
            locked_fields=self.manifest.locks.locked_fields,
            redis_client=self.redis,
            audit_log=self.audit_log
        )

        return reduced_constraints

    def _build_reduction_summary(
        self,
        before: EffectiveConstraints,
        after: EffectiveConstraints,
        summary: Dict[str, Any]
    ) -> None:
        """
        Build reduction summary (before/after values) for event emission.

        Args:
            before: Constraints before reduction
            after: Constraints after reduction
            summary: Summary dict to update (in-place)
        """
        # Track changed budget fields
        if before.budget.max_credits_per_mission != after.budget.max_credits_per_mission:
            summary["max_credits_per_mission"] = {
                "before": before.budget.max_credits_per_mission,
                "after": after.budget.max_credits_per_mission
            }

        if before.budget.max_llm_calls_per_day != after.budget.max_llm_calls_per_day:
            summary["max_llm_calls_per_day"] = {
                "before": before.budget.max_llm_calls_per_day,
                "after": after.budget.max_llm_calls_per_day
            }

        if before.budget.max_llm_tokens_per_call != after.budget.max_llm_tokens_per_call:
            summary["max_llm_tokens_per_call"] = {
                "before": before.budget.max_llm_tokens_per_call,
                "after": after.budget.max_llm_tokens_per_call
            }

        # Track changed capability fields
        if before.capabilities.network_access != after.capabilities.network_access:
            summary["network_access"] = {
                "before": before.capabilities.network_access,
                "after": after.capabilities.network_access
            }

        # Track changed runtime fields
        if before.runtime.parallelism != after.runtime.parallelism:
            summary["parallelism"] = {
                "before": before.runtime.parallelism,
                "after": after.runtime.parallelism
            }

        if before.runtime.max_lifetime_seconds != after.runtime.max_lifetime_seconds:
            summary["max_lifetime_seconds"] = {
                "before": before.runtime.max_lifetime_seconds,
                "after": after.runtime.max_lifetime_seconds
            }

    def _compute_constraints_hash(self, constraints: EffectiveConstraints) -> str:
        """
        Compute deterministic hash of constraints.

        Args:
            constraints: Constraints to hash

        Returns:
            SHA-256 hash (hex string)
        """
        constraints_json = json.dumps(constraints.model_dump(), sort_keys=True)
        hash_digest = hashlib.sha256(constraints_json.encode()).hexdigest()
        return f"sha256:{hash_digest[:16]}"

    # ========================================================================
    # Phase 2c: Locked Field Enforcement Helpers
    # ========================================================================

    def _extract_customization_dna(self, request: DecisionRequest) -> Dict[str, Any]:
        """
        Extract customization DNA from request.

        This extracts only the customized fields from the full agent DNA,
        making it easier to validate against locked fields.

        Args:
            request: Decision request

        Returns:
            Dictionary with only customized fields

        Example:
            >>> dna = _extract_customization_dna(request)
            >>> # Returns: {"ethics_flags.human_override": "never"}
        """
        # If customization_fields is provided in context, extract those specific fields
        if request.context.customization_fields:
            customization_dna = {}
            full_dna = request.agent_dna

            for field_path in request.context.customization_fields:
                # Try to extract the value from full DNA
                try:
                    value = self._get_nested_value_from_dna(full_dna, field_path)
                    customization_dna[field_path] = value
                except KeyError:
                    logger.warning(
                        f"Customization field {field_path} not found in DNA"
                    )

            return customization_dna
        else:
            # If no customization_fields specified, return full DNA
            # (enforcer will flatten and check all fields)
            return request.agent_dna

    def _get_nested_value_from_dna(self, dna: Dict[str, Any], path: str) -> Any:
        """
        Get value from nested DNA dict using dot notation.

        Args:
            dna: DNA dictionary
            path: Dot-notation path (e.g., "ethics_flags.human_override")

        Returns:
            Value at path

        Raises:
            KeyError: If path not found
        """
        keys = path.split(".")
        value = dna

        for key in keys:
            if isinstance(value, dict):
                value = value[key]
            else:
                raise KeyError(f"Path {path} not found in DNA")

        return value


# ============================================================================
# Compatibility Wrapper for Genesis Integration
# ============================================================================

class GovernorApproval:
    """
    Compatibility wrapper for Genesis Agent integration.

    This class wraps Governor v1 to match the GovernorApproval protocol
    expected by GenesisAgent (from genesis_agent.py line 123-134).

    Example:
        >>> governor_approval = GovernorApproval(
        ...     redis_client=redis,
        ...     audit_log=audit
        ... )
        >>>
        >>> response = await governor_approval.request_approval(dna)
        >>> print(response.approved, response.reason)
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        audit_log: AuditLog,
        config: Optional[GovernorConfig] = None
    ):
        """
        Initialize Governor approval wrapper.

        Args:
            redis_client: Redis client for events
            audit_log: Audit log for persistence
            config: Governor configuration (uses defaults if None)
        """
        self.governor = Governor(
            redis_client=redis_client,
            audit_log=audit_log,
            config=config
        )

    async def request_approval(self, dna: Any) -> ApprovalResponse:
        """
        Request approval from Governor v1.

        This method converts AgentDNA to DecisionRequest, calls Governor v1,
        and converts DecisionResult to ApprovalResponse.

        Args:
            dna: AgentDNA (Pydantic model)

        Returns:
            ApprovalResponse with approval decision

        Example:
            >>> response = await governor_approval.request_approval(dna)
            >>> if not response.approved:
            ...     raise Exception(f"Rejected: {response.reason}")
        """
        # Import here to avoid circular dependency
        from backend.brain.agents.genesis_agent.dna_schema import AgentDNA

        # Convert Pydantic model to dict
        if isinstance(dna, AgentDNA):
            dna_dict = dna.model_dump()
        else:
            dna_dict = dna

        # Build DecisionRequest
        import hashlib
        import json
        dna_hash = hashlib.sha256(json.dumps(dna_dict, sort_keys=True).encode()).hexdigest()

        request = DecisionRequest(
            request_id=str(dna_dict["metadata"]["id"]),
            decision_id=f"dec_{dna_dict['metadata']['id'][:16]}",
            actor=ActorContext(
                user_id="genesis_agent",
                role="SYSTEM_ADMIN",
                source="genesis_agent"
            ),
            agent_dna=dna_dict,
            dna_hash=dna_hash,
            template_name=dna_dict["metadata"].get("template_version", "unknown"),
            template_hash=dna_dict["metadata"].get("template_hash", ""),
            context=RequestContext(
                has_customizations=False,  # Genesis will set this
                customization_fields=[]
            )
        )

        # Call Governor v1
        result = await self.governor.evaluate_creation(request)

        # Convert to ApprovalResponse
        return ApprovalResponse(
            approved=result.approved,
            reason=result.reason_detail
        )


class ApprovalResponse:
    """Response from Governor approval (compatibility with Genesis)."""

    def __init__(self, approved: bool, reason: str = ""):
        self.approved = approved
        self.reason = reason
