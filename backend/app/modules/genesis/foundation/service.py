"""
Foundation Layer Service

Ethics and safety validation for agent creation and evolution.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from backend.app.modules.genesis.traits import TraitSet
from backend.app.modules.immune.core.service import ImmuneService
from backend.app.modules.immune.schemas import ImmuneEvent, ImmuneEventType, ImmuneSeverity
from backend.app.modules.policy.service import get_policy_engine

from .schemas import (
    ActionContext,
    AgentCreationContext,
    EthicsRule,
    FoundationValidationResult,
    MutationContext,
    ValidationAction,
    ValidationSeverity,
)


class FoundationLayer:
    """
    Foundation Layer - Ethics and Safety Validation.

    Validates agent creation, mutations, and actions against
    ethics rules, policy engine, and immune system status.
    """

    def __init__(
        self,
        policy_engine = None,
        immune_service: Optional[ImmuneService] = None,
    ):
        self.policy_engine = policy_engine or get_policy_engine()
        self.immune_service = immune_service
        self.ethics_rules: List[EthicsRule] = []
        self._load_core_ethics_rules()

        logger.info("Foundation Layer initialized")

    def _load_core_ethics_rules(self):
        """Load core ethics rules."""
        self.ethics_rules = [
            EthicsRule(
                id="safety_minimum",
                name="Safety Minimum Threshold",
                description="Agents must have safety_priority >= 0.7",
                severity=ValidationSeverity.CRITICAL,
                action=ValidationAction.BLOCK,
                validator=self._validate_safety_minimum,
            ),
            EthicsRule(
                id="harm_avoidance_minimum",
                name="Harm Avoidance Minimum",
                description="Agents must have harm_avoidance >= 0.8",
                severity=ValidationSeverity.CRITICAL,
                action=ValidationAction.BLOCK,
                validator=self._validate_harm_avoidance,
            ),
            EthicsRule(
                id="no_dangerous_tool_combos",
                name="No Dangerous Tool Combinations",
                description="Certain tool combinations are prohibited",
                severity=ValidationSeverity.CRITICAL,
                action=ValidationAction.BLOCK,
                validator=self._validate_tool_safety,
            ),
            EthicsRule(
                id="risk_tolerance_cap",
                name="Risk Tolerance Cap",
                description="Risk tolerance cannot exceed 0.5",
                severity=ValidationSeverity.CRITICAL,
                action=ValidationAction.BLOCK,
                validator=self._validate_risk_tolerance,
            ),
            EthicsRule(
                id="compliance_minimum",
                name="Compliance Minimum",
                description="Compliance strictness must be >= 0.5",
                severity=ValidationSeverity.WARNING,
                action=ValidationAction.WARN,
                validator=self._validate_compliance,
            ),
        ]

        logger.info(f"Loaded {len(self.ethics_rules)} core ethics rules")

    async def validate_agent_creation(
        self, context: AgentCreationContext
    ) -> FoundationValidationResult:
        """
        Validate agent before creation.

        Args:
            context: Agent creation context

        Returns:
            Validation result with violations/warnings
        """
        result = FoundationValidationResult(allowed=True, context=context.model_dump())

        # Evaluate ethics rules
        for rule in self.ethics_rules:
            if not rule.enabled:
                continue

            try:
                if rule.validator and not rule.validator(context.model_dump()):
                    message = f"{rule.name}: {rule.description}"

                    if rule.action == ValidationAction.BLOCK:
                        result.add_violation(message)
                    elif rule.action == ValidationAction.WARN:
                        result.add_warning(message)
                    else:
                        result.add_info(message)

            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id}: {e}")
                result.add_violation(f"Rule evaluation error: {rule.id}")

        # Check immune system health
        if self.immune_service:
            try:
                health = await self.immune_service.health_summary(minutes=60)
                if health.critical_issues > 0:
                    result.add_warning(
                        f"System under threat ({health.critical_issues} critical issues) - "
                        "careful agent creation advised"
                    )
            except Exception as e:
                logger.warning(f"Could not check immune system health: {e}")

        # Log result
        if result.has_violations:
            logger.warning(
                f"Agent creation blocked for {context.agent_id}: {result.violations}"
            )
        elif result.has_warnings:
            logger.info(
                f"Agent creation warnings for {context.agent_id}: {result.warnings}"
            )
        else:
            logger.info(f"Agent creation validated for {context.agent_id}")

        # Log to immune system
        if self.immune_service and (result.has_violations or result.has_warnings):
            try:
                await self.immune_service.publish_event(
                    ImmuneEvent(
                        agent_id=context.agent_id,
                        module="genesis.foundation",
                        severity=(
                            ImmuneSeverity.CRITICAL
                            if result.has_violations
                            else ImmuneSeverity.WARNING
                        ),
                        type=ImmuneEventType.POLICY_VIOLATION,
                        message=f"Ethics validation: {'BLOCKED' if result.has_violations else 'WARNING'}",
                        meta={
                            "violations": result.violations,
                            "warnings": result.warnings,
                            "blueprint_id": context.blueprint_id,
                        },
                    )
                )
            except Exception as e:
                logger.warning(f"Could not log to immune system: {e}")

        return result

    async def validate_mutation(
        self, context: MutationContext
    ) -> FoundationValidationResult:
        """
        Validate mutation before application.

        Args:
            context: Mutation context

        Returns:
            Validation result
        """
        result = FoundationValidationResult(allowed=True, context=context.model_dump())

        # Check for immutable trait violations
        for trait_id, new_value in context.proposed_traits.items():
            current_value = context.current_traits.get(trait_id)

            # Check if trait is ethics-critical and changed
            if trait_id in ["ethical.safety_priority", "ethical.harm_avoidance"]:
                if current_value is not None and new_value != current_value:
                    # Safety and harm avoidance are IMMUTABLE
                    result.add_violation(
                        f"Cannot mutate immutable ethics-critical trait: {trait_id}"
                    )

            # Check bounds for ethics-critical traits
            if trait_id == "ethical.safety_priority" and new_value < 0.7:
                result.add_violation(
                    f"Safety priority cannot be below 0.7 (proposed: {new_value})"
                )

            if trait_id == "ethical.harm_avoidance" and new_value < 0.8:
                result.add_violation(
                    f"Harm avoidance cannot be below 0.8 (proposed: {new_value})"
                )

            if trait_id == "behavioral.risk_tolerance" and new_value > 0.5:
                result.add_violation(
                    f"Risk tolerance cannot exceed 0.5 (proposed: {new_value})"
                )

        # Evaluate ethics rules with mutation context
        mutation_eval_context = {
            "agent_id": context.agent_id,
            "traits": context.proposed_traits,
            "mutations": context.mutations,
        }

        for rule in self.ethics_rules:
            if not rule.enabled:
                continue

            try:
                if rule.validator and not rule.validator(mutation_eval_context):
                    message = f"{rule.name}: {rule.description}"

                    if rule.action == ValidationAction.BLOCK:
                        result.add_violation(message)
                    elif rule.action == ValidationAction.WARN:
                        result.add_warning(message)

            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id}: {e}")

        if result.has_violations:
            logger.warning(
                f"Mutation blocked for {context.agent_id}: {result.violations}"
            )
        else:
            logger.info(f"Mutation validated for {context.agent_id}")

        return result

    async def validate_action(
        self, context: ActionContext
    ) -> FoundationValidationResult:
        """
        Validate action before execution.

        Args:
            context: Action context

        Returns:
            Validation result
        """
        result = FoundationValidationResult(allowed=True, context=context.model_dump())

        # Delegate to policy engine if available
        if self.policy_engine:
            try:
                from backend.app.modules.policy.schemas import PolicyEvaluationContext

                policy_context = PolicyEvaluationContext(
                    agent_id=context.agent_id,
                    action=context.action,
                    resource=context.parameters.get("resource"),
                    environment=context.environment,
                    params=context.parameters,
                )

                policy_result = await self.policy_engine.evaluate(policy_context)

                if not policy_result.allowed:
                    result.add_violation(f"Policy denied: {policy_result.reason}")
                elif policy_result.warnings:
                    for warning in policy_result.warnings:
                        result.add_warning(warning)

            except Exception as e:
                logger.error(f"Policy engine evaluation error: {e}")
                result.add_warning("Could not validate against policy engine")

        return result

    # ========================================================================
    # VALIDATOR FUNCTIONS
    # ========================================================================

    def _validate_safety_minimum(self, context: Dict[str, Any]) -> bool:
        """Validate safety_priority >= 0.7."""
        traits = context.get("traits", {})
        safety = traits.get("ethical.safety_priority")

        if safety is None:
            return True  # No safety trait, allow (will use default)

        return safety >= 0.7

    def _validate_harm_avoidance(self, context: Dict[str, Any]) -> bool:
        """Validate harm_avoidance >= 0.8."""
        traits = context.get("traits", {})
        harm_avoidance = traits.get("ethical.harm_avoidance")

        if harm_avoidance is None:
            return True

        return harm_avoidance >= 0.8

    def _validate_risk_tolerance(self, context: Dict[str, Any]) -> bool:
        """Validate risk_tolerance <= 0.5."""
        traits = context.get("traits", {})
        risk = traits.get("behavioral.risk_tolerance")

        if risk is None:
            return True

        return risk <= 0.5

    def _validate_compliance(self, context: Dict[str, Any]) -> bool:
        """Validate compliance_strictness >= 0.5."""
        traits = context.get("traits", {})
        compliance = traits.get("ethical.compliance_strictness")

        if compliance is None:
            return True

        return compliance >= 0.5

    def _validate_tool_safety(self, context: Dict[str, Any]) -> bool:
        """Validate no dangerous tool combinations."""
        tools = context.get("tools", [])
        traits = context.get("traits", {})

        # Example: Dangerous combo = high-power tools + low safety
        dangerous_tools = ["system_administration", "deployment", "database_write"]
        has_dangerous_tool = any(tool in tools for tool in dangerous_tools)

        if has_dangerous_tool:
            safety = traits.get("ethical.safety_priority", 1.0)
            if safety < 0.8:
                logger.warning(
                    f"Dangerous tool with low safety: tools={tools}, safety={safety}"
                )
                return False

        return True

    def register_custom_rule(self, rule: EthicsRule):
        """
        Register custom ethics rule.

        Args:
            rule: Ethics rule to register
        """
        # Check for duplicate ID
        for idx, existing in enumerate(self.ethics_rules):
            if existing.id == rule.id:
                logger.warning(f"Replacing existing rule: {rule.id}")
                self.ethics_rules[idx] = rule
                return

        self.ethics_rules.append(rule)
        logger.info(f"Registered custom ethics rule: {rule.id}")

    def get_all_rules(self) -> List[EthicsRule]:
        """Get all registered ethics rules."""
        return self.ethics_rules.copy()


# Singleton instance
_foundation_layer: Optional[FoundationLayer] = None


def get_foundation_layer() -> FoundationLayer:
    """Get singleton FoundationLayer instance."""
    global _foundation_layer
    if _foundation_layer is None:
        _foundation_layer = FoundationLayer()
    return _foundation_layer
