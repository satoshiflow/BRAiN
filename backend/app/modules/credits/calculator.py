"""
Credit Calculator

Deterministic engine for computing credit allocations and costs.

Philosophy:
- Pure functions only (no side effects)
- Deterministic: same inputs → same outputs
- Explicit error handling (fail-closed)
- Comprehensive logging for debugging
- Unit testable with predictable results

Rules are defined in brain_credit_selection_spec.v1.yaml
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from loguru import logger

from .models import AgentStatus, CreditType, EntityType


class CalculationRule(str, Enum):
    """Credit calculation rules."""

    # Agent lifecycle rules
    AGENT_CREATION_MINT = "AGENT_CREATION_MINT"
    AGENT_EXISTENCE_TAX = "AGENT_EXISTENCE_TAX"

    # Mission rules
    MISSION_CREATION_MINT = "MISSION_CREATION_MINT"
    MISSION_COMPLETION_REWARD = "MISSION_COMPLETION_REWARD"
    MISSION_FAILURE_PENALTY = "MISSION_FAILURE_PENALTY"

    # Resource consumption
    LLM_CALL_COST = "LLM_CALL_COST"
    STORAGE_USAGE_TAX = "STORAGE_USAGE_TAX"
    NETWORK_CALL_COST = "NETWORK_CALL_COST"
    COMPUTE_USAGE_COST = "COMPUTE_USAGE_COST"


@dataclass
class CalculationContext:
    """Context for credit calculations."""

    entity_id: str
    entity_type: EntityType
    timestamp: datetime

    # Agent-specific
    agent_status: Optional[AgentStatus] = None
    hours_active: Optional[Decimal] = None

    # Mission-specific
    mission_status: Optional[str] = None
    mission_priority: Optional[str] = None

    # Resource consumption
    llm_tokens: Optional[int] = None
    storage_mb: Optional[Decimal] = None
    network_bytes: Optional[int] = None
    compute_seconds: Optional[Decimal] = None

    # Additional metadata
    metadata: Optional[dict] = None


@dataclass
class CalculationResult:
    """Result of a credit calculation."""

    rule: CalculationRule
    credit_type: CreditType
    amount: Decimal
    reason: str
    metadata: dict


class CreditCalculator:
    """
    Deterministic credit calculator.

    All calculations are pure functions of the input context.
    No database access, no side effects.
    """

    def __init__(self):
        """Initialize calculator with default rule parameters."""
        self.rules = {
            # Agent creation: 1000 CC
            CalculationRule.AGENT_CREATION_MINT: {
                "credit_type": CreditType.COMPUTE_CREDITS,
                "base_amount": Decimal("1000.0"),
            },
            # Existence tax: 5 CC per hour
            CalculationRule.AGENT_EXISTENCE_TAX: {
                "credit_type": CreditType.COMPUTE_CREDITS,
                "hourly_rate": Decimal("5.0"),
            },
            # Mission creation: 500 CC
            CalculationRule.MISSION_CREATION_MINT: {
                "credit_type": CreditType.COMPUTE_CREDITS,
                "base_amount": Decimal("500.0"),
            },
            # Mission completion: 50 CC * priority multiplier
            CalculationRule.MISSION_COMPLETION_REWARD: {
                "credit_type": CreditType.COMPUTE_CREDITS,
                "base_reward": Decimal("50.0"),
                "priority_multipliers": {
                    "LOW": Decimal("0.5"),
                    "NORMAL": Decimal("1.0"),
                    "HIGH": Decimal("1.5"),
                    "CRITICAL": Decimal("2.0"),
                },
            },
            # LLM call: 0.001 LC per token
            CalculationRule.LLM_CALL_COST: {
                "credit_type": CreditType.LLM_CREDITS,
                "cost_per_token": Decimal("0.001"),
            },
            # Storage: 0.1 SC per MB per day
            CalculationRule.STORAGE_USAGE_TAX: {
                "credit_type": CreditType.STORAGE_CREDITS,
                "cost_per_mb_per_day": Decimal("0.1"),
            },
            # Network: 0.0001 NC per KB
            CalculationRule.NETWORK_CALL_COST: {
                "credit_type": CreditType.NETWORK_CREDITS,
                "cost_per_kb": Decimal("0.0001"),
            },
            # Compute: 1 CC per CPU-second
            CalculationRule.COMPUTE_USAGE_COST: {
                "credit_type": CreditType.COMPUTE_CREDITS,
                "cost_per_second": Decimal("1.0"),
            },
        }

    def calculate_agent_creation(self, context: CalculationContext) -> CalculationResult:
        """
        Calculate credits to mint when creating an agent.

        Rule: AGENT_CREATION_MINT
        Formula: 1000.0 CC (fixed)

        Args:
            context: Calculation context

        Returns:
            Calculation result with amount to mint
        """
        rule_params = self.rules[CalculationRule.AGENT_CREATION_MINT]
        amount = rule_params["base_amount"]

        logger.debug(
            f"Agent creation mint: entity={context.entity_id} amount={amount} CC"
        )

        return CalculationResult(
            rule=CalculationRule.AGENT_CREATION_MINT,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=amount,
            reason="Initial credit allocation for agent creation",
            metadata={
                "entity_id": context.entity_id,
                "entity_type": context.entity_type.value,
                "timestamp": context.timestamp.isoformat(),
            },
        )

    def calculate_existence_tax(self, context: CalculationContext) -> CalculationResult:
        """
        Calculate hourly existence tax for active agents.

        Rule: AGENT_EXISTENCE_TAX
        Formula: 5.0 CC * hours_active
        Condition: agent.status == ACTIVE

        Args:
            context: Calculation context (must include hours_active)

        Returns:
            Calculation result with tax amount

        Raises:
            ValueError: If hours_active is not provided or agent not ACTIVE
        """
        if context.agent_status != AgentStatus.ACTIVE:
            raise ValueError(
                f"Existence tax only applies to ACTIVE agents, got {context.agent_status}"
            )

        if context.hours_active is None or context.hours_active <= 0:
            raise ValueError(
                f"hours_active must be positive, got {context.hours_active}"
            )

        rule_params = self.rules[CalculationRule.AGENT_EXISTENCE_TAX]
        hourly_rate = rule_params["hourly_rate"]
        amount = hourly_rate * context.hours_active

        logger.debug(
            f"Existence tax: entity={context.entity_id} "
            f"hours={context.hours_active} rate={hourly_rate} "
            f"total={amount} CC"
        )

        return CalculationResult(
            rule=CalculationRule.AGENT_EXISTENCE_TAX,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=amount,
            reason=f"Existence tax for {context.hours_active} hours",
            metadata={
                "entity_id": context.entity_id,
                "hours_active": str(context.hours_active),
                "hourly_rate": str(hourly_rate),
                "timestamp": context.timestamp.isoformat(),
            },
        )

    def calculate_mission_creation(self, context: CalculationContext) -> CalculationResult:
        """
        Calculate credits to mint when creating a mission.

        Rule: MISSION_CREATION_MINT
        Formula: 500.0 CC (fixed)

        Args:
            context: Calculation context

        Returns:
            Calculation result with amount to mint
        """
        rule_params = self.rules[CalculationRule.MISSION_CREATION_MINT]
        amount = rule_params["base_amount"]

        logger.debug(
            f"Mission creation mint: entity={context.entity_id} amount={amount} CC"
        )

        return CalculationResult(
            rule=CalculationRule.MISSION_CREATION_MINT,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=amount,
            reason="Initial credit allocation for mission creation",
            metadata={
                "entity_id": context.entity_id,
                "entity_type": context.entity_type.value,
                "timestamp": context.timestamp.isoformat(),
            },
        )

    def calculate_mission_completion_reward(
        self, context: CalculationContext
    ) -> CalculationResult:
        """
        Calculate reward for successful mission completion.

        Rule: MISSION_COMPLETION_REWARD
        Formula: 50.0 CC * priority_multiplier
        Condition: mission.status == COMPLETED

        Args:
            context: Calculation context (must include mission_status and mission_priority)

        Returns:
            Calculation result with reward amount

        Raises:
            ValueError: If mission not completed or priority missing
        """
        if context.mission_status != "COMPLETED":
            raise ValueError(
                f"Completion reward only for COMPLETED missions, got {context.mission_status}"
            )

        if context.mission_priority is None:
            raise ValueError("mission_priority is required")

        rule_params = self.rules[CalculationRule.MISSION_COMPLETION_REWARD]
        base_reward = rule_params["base_reward"]
        multipliers = rule_params["priority_multipliers"]

        priority = context.mission_priority.upper()
        multiplier = multipliers.get(priority, Decimal("1.0"))

        amount = base_reward * multiplier

        logger.debug(
            f"Mission completion reward: entity={context.entity_id} "
            f"priority={priority} multiplier={multiplier} "
            f"reward={amount} CC"
        )

        return CalculationResult(
            rule=CalculationRule.MISSION_COMPLETION_REWARD,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=amount,
            reason=f"Mission completion reward (priority: {priority})",
            metadata={
                "entity_id": context.entity_id,
                "mission_priority": priority,
                "multiplier": str(multiplier),
                "timestamp": context.timestamp.isoformat(),
            },
        )

    def calculate_llm_call_cost(self, context: CalculationContext) -> CalculationResult:
        """
        Calculate cost of LLM API call.

        Rule: LLM_CALL_COST
        Formula: 0.001 LC * total_tokens

        Args:
            context: Calculation context (must include llm_tokens)

        Returns:
            Calculation result with cost

        Raises:
            ValueError: If llm_tokens not provided
        """
        if context.llm_tokens is None or context.llm_tokens < 0:
            raise ValueError(f"llm_tokens must be non-negative, got {context.llm_tokens}")

        rule_params = self.rules[CalculationRule.LLM_CALL_COST]
        cost_per_token = rule_params["cost_per_token"]
        amount = cost_per_token * Decimal(context.llm_tokens)

        logger.debug(
            f"LLM call cost: entity={context.entity_id} "
            f"tokens={context.llm_tokens} "
            f"cost={amount} LC"
        )

        return CalculationResult(
            rule=CalculationRule.LLM_CALL_COST,
            credit_type=CreditType.LLM_CREDITS,
            amount=amount,
            reason=f"LLM API call ({context.llm_tokens} tokens)",
            metadata={
                "entity_id": context.entity_id,
                "llm_tokens": context.llm_tokens,
                "cost_per_token": str(cost_per_token),
                "timestamp": context.timestamp.isoformat(),
            },
        )

    def calculate_storage_tax(self, context: CalculationContext) -> CalculationResult:
        """
        Calculate daily storage tax.

        Rule: STORAGE_USAGE_TAX
        Formula: 0.1 SC * storage_mb

        Args:
            context: Calculation context (must include storage_mb)

        Returns:
            Calculation result with tax

        Raises:
            ValueError: If storage_mb not provided
        """
        if context.storage_mb is None or context.storage_mb < 0:
            raise ValueError(f"storage_mb must be non-negative, got {context.storage_mb}")

        rule_params = self.rules[CalculationRule.STORAGE_USAGE_TAX]
        cost_per_mb = rule_params["cost_per_mb_per_day"]
        amount = cost_per_mb * context.storage_mb

        logger.debug(
            f"Storage tax: entity={context.entity_id} "
            f"storage_mb={context.storage_mb} "
            f"cost={amount} SC"
        )

        return CalculationResult(
            rule=CalculationRule.STORAGE_USAGE_TAX,
            credit_type=CreditType.STORAGE_CREDITS,
            amount=amount,
            reason=f"Storage usage tax ({context.storage_mb} MB)",
            metadata={
                "entity_id": context.entity_id,
                "storage_mb": str(context.storage_mb),
                "cost_per_mb": str(cost_per_mb),
                "timestamp": context.timestamp.isoformat(),
            },
        )

    def calculate_network_call_cost(self, context: CalculationContext) -> CalculationResult:
        """
        Calculate network I/O cost.

        Rule: NETWORK_CALL_COST
        Formula: 0.0001 NC * (network_bytes / 1024)

        Args:
            context: Calculation context (must include network_bytes)

        Returns:
            Calculation result with cost

        Raises:
            ValueError: If network_bytes not provided
        """
        if context.network_bytes is None or context.network_bytes < 0:
            raise ValueError(
                f"network_bytes must be non-negative, got {context.network_bytes}"
            )

        rule_params = self.rules[CalculationRule.NETWORK_CALL_COST]
        cost_per_kb = rule_params["cost_per_kb"]
        kb_transferred = Decimal(context.network_bytes) / Decimal("1024")
        amount = cost_per_kb * kb_transferred

        logger.debug(
            f"Network call cost: entity={context.entity_id} "
            f"bytes={context.network_bytes} "
            f"kb={kb_transferred} "
            f"cost={amount} NC"
        )

        return CalculationResult(
            rule=CalculationRule.NETWORK_CALL_COST,
            credit_type=CreditType.NETWORK_CREDITS,
            amount=amount,
            reason=f"Network I/O ({context.network_bytes} bytes)",
            metadata={
                "entity_id": context.entity_id,
                "network_bytes": context.network_bytes,
                "kb_transferred": str(kb_transferred),
                "cost_per_kb": str(cost_per_kb),
                "timestamp": context.timestamp.isoformat(),
            },
        )

    def calculate_compute_usage_cost(self, context: CalculationContext) -> CalculationResult:
        """
        Calculate compute (CPU) usage cost.

        Rule: COMPUTE_USAGE_COST
        Formula: 1.0 CC * compute_seconds

        Args:
            context: Calculation context (must include compute_seconds)

        Returns:
            Calculation result with cost

        Raises:
            ValueError: If compute_seconds not provided
        """
        if context.compute_seconds is None or context.compute_seconds < 0:
            raise ValueError(
                f"compute_seconds must be non-negative, got {context.compute_seconds}"
            )

        rule_params = self.rules[CalculationRule.COMPUTE_USAGE_COST]
        cost_per_second = rule_params["cost_per_second"]
        amount = cost_per_second * context.compute_seconds

        logger.debug(
            f"Compute usage cost: entity={context.entity_id} "
            f"seconds={context.compute_seconds} "
            f"cost={amount} CC"
        )

        return CalculationResult(
            rule=CalculationRule.COMPUTE_USAGE_COST,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=amount,
            reason=f"Compute usage ({context.compute_seconds} CPU-seconds)",
            metadata={
                "entity_id": context.entity_id,
                "compute_seconds": str(context.compute_seconds),
                "cost_per_second": str(cost_per_second),
                "timestamp": context.timestamp.isoformat(),
            },
        )
