"""
Governor v1 Service (Phase 2a)

Central decision engine for agent creation governance.

The Governor v1 makes formal, deterministic decisions on agent creation by:
1. Evaluating policy rules (Groups A-E)
2. Computing risk tier and quarantine status
3. Applying constraints (defaults + reductions)
4. Emitting audit events (dual-write)
5. Returning immutable DecisionResult

Architecture:
- Pure functions for rule evaluation (no side effects)
- Fail-closed event emission (at least one write succeeds)
- Complete audit trail for every decision
- No ML, no LLMs, no interpretation - mechanical only

Author: Governor v1 System
Version: 1.0.0
Created: 2026-01-02
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from backend.brain.agents.genesis_agent.dna_schema import AgentType
from backend.brain.agents.genesis_agent.events import AuditLog
from backend.brain.governor.constraints.defaults import get_default_constraints
from backend.brain.governor.constraints.schema import EffectiveConstraints
from backend.brain.governor.decision.models import (
    DecisionRequest,
    DecisionResult,
    DecisionType,
    ReasonCode,
    RiskTier,
)
from backend.brain.governor.events import GovernorEvents
from backend.brain.governor.policy import rules


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
        population_counts: Optional[Dict[AgentType, int]] = None
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
        """
        self.redis = redis_client
        self.audit_log = audit_log
        self.config = config or GovernorConfig()
        self.killswitch_active = killswitch_active
        self.available_credits = available_credits
        self.population_counts = population_counts or {}

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

        # Apply constraints (if approved)
        constraints = None
        if approved:
            constraints = self._apply_constraints(agent_type, request.context.has_customizations)

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
        Compute risk tier and quarantine status.

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

        risk_tier = RiskTier(risk_tier_str)

        return (risk_tier, quarantine)

    # ========================================================================
    # Constraint Application
    # ========================================================================

    def _apply_constraints(
        self,
        agent_type: AgentType,
        has_customizations: bool
    ) -> EffectiveConstraints:
        """
        Apply constraints based on AgentType and customizations.

        Args:
            agent_type: Agent type
            has_customizations: Whether request has customizations

        Returns:
            EffectiveConstraints to apply

        Note:
            Phase 2a: No escalations allowed, only defaults or reductions.

        Example:
            >>> constraints = governor._apply_constraints(
            ...     AgentType.WORKER,
            ...     has_customizations=False
            ... )
        """
        # Get default constraints for AgentType
        constraints = get_default_constraints(agent_type)

        # Phase 2a: No customization-based reductions yet (future)
        # For now, return defaults

        return constraints


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


# Import ActorContext and RequestContext for GovernorApproval
from backend.brain.governor.decision.models import ActorContext, RequestContext


class ApprovalResponse:
    """Response from Governor approval (compatibility with Genesis)."""

    def __init__(self, approved: bool, reason: str = ""):
        self.approved = approved
        self.reason = reason
