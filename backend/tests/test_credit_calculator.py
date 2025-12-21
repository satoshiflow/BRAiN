"""
Unit tests for Credit Calculator

Tests deterministic credit calculations and rule enforcement.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from backend.app.modules.credits.calculator import (
    CalculationContext,
    CalculationRule,
    CreditCalculator,
)
from backend.app.modules.credits.models import AgentStatus, CreditType, EntityType


class TestCreditCalculator:
    """Test suite for CreditCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = CreditCalculator()
        self.timestamp = datetime.now(timezone.utc)

    def test_deterministic_agent_creation(self):
        """Test that agent creation always returns same amount."""
        context1 = CalculationContext(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            timestamp=self.timestamp,
        )

        context2 = CalculationContext(
            entity_id="agent_002",
            entity_type=EntityType.AGENT,
            timestamp=self.timestamp,
        )

        result1 = self.calculator.calculate_agent_creation(context1)
        result2 = self.calculator.calculate_agent_creation(context2)

        # Should be deterministic (same amount)
        assert result1.amount == result2.amount
        assert result1.amount == Decimal("1000.0")
        assert result1.credit_type == CreditType.COMPUTE_CREDITS
        assert result1.rule == CalculationRule.AGENT_CREATION_MINT

    def test_existence_tax_calculation(self):
        """Test existence tax calculation."""
        context = CalculationContext(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            timestamp=self.timestamp,
            agent_status=AgentStatus.ACTIVE,
            hours_active=Decimal("2.5"),
        )

        result = self.calculator.calculate_existence_tax(context)

        # 5 CC per hour * 2.5 hours = 12.5 CC
        expected = Decimal("5.0") * Decimal("2.5")
        assert result.amount == expected
        assert result.credit_type == CreditType.COMPUTE_CREDITS
        assert result.rule == CalculationRule.AGENT_EXISTENCE_TAX

    def test_existence_tax_requires_active_status(self):
        """Test that existence tax only applies to ACTIVE agents."""
        context = CalculationContext(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            timestamp=self.timestamp,
            agent_status=AgentStatus.SUSPENDED,
            hours_active=Decimal("1.0"),
        )

        with pytest.raises(ValueError, match="only applies to ACTIVE agents"):
            self.calculator.calculate_existence_tax(context)

    def test_existence_tax_requires_positive_hours(self):
        """Test that existence tax requires positive hours."""
        context = CalculationContext(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            timestamp=self.timestamp,
            agent_status=AgentStatus.ACTIVE,
            hours_active=Decimal("0.0"),
        )

        with pytest.raises(ValueError, match="hours_active must be positive"):
            self.calculator.calculate_existence_tax(context)

    def test_mission_completion_reward_priority_multipliers(self):
        """Test mission completion rewards with different priorities."""
        base_reward = Decimal("50.0")

        test_cases = [
            ("LOW", Decimal("0.5"), base_reward * Decimal("0.5")),
            ("NORMAL", Decimal("1.0"), base_reward * Decimal("1.0")),
            ("HIGH", Decimal("1.5"), base_reward * Decimal("1.5")),
            ("CRITICAL", Decimal("2.0"), base_reward * Decimal("2.0")),
        ]

        for priority, multiplier, expected_reward in test_cases:
            context = CalculationContext(
                entity_id="mission_001",
                entity_type=EntityType.MISSION,
                timestamp=self.timestamp,
                mission_status="COMPLETED",
                mission_priority=priority,
            )

            result = self.calculator.calculate_mission_completion_reward(context)

            assert result.amount == expected_reward
            assert result.credit_type == CreditType.COMPUTE_CREDITS
            assert str(multiplier) in result.metadata["multiplier"]

    def test_llm_call_cost_calculation(self):
        """Test LLM call cost calculation."""
        context = CalculationContext(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            timestamp=self.timestamp,
            llm_tokens=5000,
        )

        result = self.calculator.calculate_llm_call_cost(context)

        # 0.001 LC per token * 5000 tokens = 5.0 LC
        expected = Decimal("0.001") * Decimal("5000")
        assert result.amount == expected
        assert result.credit_type == CreditType.LLM_CREDITS

    def test_storage_tax_calculation(self):
        """Test storage tax calculation."""
        context = CalculationContext(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            timestamp=self.timestamp,
            storage_mb=Decimal("100.5"),
        )

        result = self.calculator.calculate_storage_tax(context)

        # 0.1 SC per MB * 100.5 MB = 10.05 SC
        expected = Decimal("0.1") * Decimal("100.5")
        assert result.amount == expected
        assert result.credit_type == CreditType.STORAGE_CREDITS

    def test_network_call_cost_calculation(self):
        """Test network call cost calculation."""
        context = CalculationContext(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            timestamp=self.timestamp,
            network_bytes=10240,  # 10 KB
        )

        result = self.calculator.calculate_network_call_cost(context)

        # 0.0001 NC per KB * 10 KB = 0.001 NC
        kb = Decimal("10240") / Decimal("1024")
        expected = Decimal("0.0001") * kb
        assert result.amount == expected
        assert result.credit_type == CreditType.NETWORK_CREDITS

    def test_compute_usage_cost_calculation(self):
        """Test compute usage cost calculation."""
        context = CalculationContext(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            timestamp=self.timestamp,
            compute_seconds=Decimal("42.5"),
        )

        result = self.calculator.calculate_compute_usage_cost(context)

        # 1.0 CC per second * 42.5 seconds = 42.5 CC
        expected = Decimal("1.0") * Decimal("42.5")
        assert result.amount == expected
        assert result.credit_type == CreditType.COMPUTE_CREDITS

    def test_determinism_across_calls(self):
        """Test that calculator is deterministic across multiple calls."""
        context = CalculationContext(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            timestamp=self.timestamp,
            agent_status=AgentStatus.ACTIVE,
            hours_active=Decimal("1.5"),
        )

        results = [
            self.calculator.calculate_existence_tax(context)
            for _ in range(10)
        ]

        # All results should be identical
        first_amount = results[0].amount
        assert all(r.amount == first_amount for r in results)

    def test_mission_creation_mint(self):
        """Test mission creation minting."""
        context = CalculationContext(
            entity_id="mission_001",
            entity_type=EntityType.MISSION,
            timestamp=self.timestamp,
        )

        result = self.calculator.calculate_mission_creation(context)

        assert result.amount == Decimal("500.0")
        assert result.credit_type == CreditType.COMPUTE_CREDITS
        assert result.rule == CalculationRule.MISSION_CREATION_MINT

    def test_negative_values_rejected(self):
        """Test that negative values are rejected."""
        # Negative storage
        context = CalculationContext(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            timestamp=self.timestamp,
            storage_mb=Decimal("-10.0"),
        )

        with pytest.raises(ValueError, match="must be non-negative"):
            self.calculator.calculate_storage_tax(context)

        # Negative network bytes
        context.storage_mb = None
        context.network_bytes = -1024

        with pytest.raises(ValueError, match="must be non-negative"):
            self.calculator.calculate_network_call_cost(context)

    def test_zero_values_allowed(self):
        """Test that zero values are allowed (no cost)."""
        context = CalculationContext(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            timestamp=self.timestamp,
            llm_tokens=0,
        )

        result = self.calculator.calculate_llm_call_cost(context)
        assert result.amount == Decimal("0.0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
