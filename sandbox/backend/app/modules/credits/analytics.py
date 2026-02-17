"""
Advanced Analytics for Credit System.

Provides insights into:
- Spending patterns by agent/mission type
- Credit flow analysis
- Trend detection
- Resource utilization
- Anomaly detection

Usage:
    from app.modules.credits.analytics import CreditAnalytics

    analytics = CreditAnalytics()
    await analytics.initialize()

    # Get spending patterns
    patterns = await analytics.get_spending_patterns(agent_id="agent_123")

    # Get trends
    trends = await analytics.get_credit_trends(days=7)

    # Detect anomalies
    anomalies = await analytics.detect_anomalies()
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from loguru import logger

from app.modules.credits.integration_demo import get_credit_system_demo
from app.modules.credits.event_sourcing import LedgerEntry


class CreditAnalytics:
    """
    Analytics engine for credit system.

    Features:
    - Spending pattern analysis
    - Trend detection
    - Anomaly detection
    - Resource utilization metrics
    """

    def __init__(self):
        self.credit_system = None

    async def initialize(self) -> None:
        """Initialize analytics engine."""
        try:
            self.credit_system = await get_credit_system_demo()
            logger.info("Credit analytics initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize credit analytics: {e}")
            raise

    async def get_spending_patterns(
        self,
        agent_id: Optional[str] = None,
        days: int = 30,
    ) -> Dict:
        """
        Get spending patterns for agent(s).

        Args:
            agent_id: Specific agent or None for all agents
            days: Number of days to analyze

        Returns:
            Dict with spending patterns:
            - total_consumed: Total credits consumed
            - total_refunded: Total credits refunded
            - net_spent: Net credits spent (consumed - refunded)
            - avg_transaction: Average transaction size
            - transaction_count: Number of transactions
            - spending_by_reason: Breakdown by reason
        """
        if not self.credit_system:
            raise ValueError("Analytics not initialized")

        # Get transaction history
        if agent_id:
            history = await self.credit_system.get_history(agent_id, limit=1000)
        else:
            # Get all histories
            all_balances = await self.credit_system.get_all_balances()
            history = []
            for aid in all_balances.keys():
                agent_history = await self.credit_system.get_history(aid, limit=1000)
                history.extend(agent_history)

        # Filter by date
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_history = [
            entry for entry in history
            if datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00")) > cutoff_date
        ]

        # Analyze patterns
        total_consumed = 0.0
        total_refunded = 0.0
        spending_by_reason = defaultdict(float)
        spending_by_mission = defaultdict(float)

        for entry in recent_history:
            if entry.amount < 0:  # Consumption
                total_consumed += abs(entry.amount)
                spending_by_reason[entry.reason] += abs(entry.amount)
                if entry.mission_id:
                    spending_by_mission[entry.mission_id] += abs(entry.amount)
            else:  # Refund/allocation
                total_refunded += entry.amount

        return {
            "agent_id": agent_id or "all",
            "period_days": days,
            "total_consumed": round(total_consumed, 2),
            "total_refunded": round(total_refunded, 2),
            "net_spent": round(total_consumed - total_refunded, 2),
            "avg_transaction": round(
                total_consumed / len(recent_history) if recent_history else 0, 2
            ),
            "transaction_count": len(recent_history),
            "spending_by_reason": dict(spending_by_reason),
            "spending_by_mission": dict(spending_by_mission),
        }

    async def get_credit_trends(
        self,
        days: int = 7,
        granularity: str = "daily",
    ) -> Dict:
        """
        Get credit flow trends over time.

        Args:
            days: Number of days to analyze
            granularity: Time granularity (hourly, daily, weekly)

        Returns:
            Dict with trends:
            - time_series: List of {date, consumed, refunded, net}
            - trend_direction: "increasing", "decreasing", "stable"
            - trend_percentage: % change over period
        """
        if not self.credit_system:
            raise ValueError("Analytics not initialized")

        # Get all histories
        all_balances = await self.credit_system.get_all_balances()
        all_history = []
        for agent_id in all_balances.keys():
            agent_history = await self.credit_system.get_history(agent_id, limit=1000)
            all_history.extend(agent_history)

        # Filter by date
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_history = [
            entry for entry in all_history
            if datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00")) > cutoff_date
        ]

        # Group by time period
        time_series = defaultdict(lambda: {"consumed": 0.0, "refunded": 0.0})

        for entry in recent_history:
            entry_date = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))

            if granularity == "daily":
                period_key = entry_date.strftime("%Y-%m-%d")
            elif granularity == "hourly":
                period_key = entry_date.strftime("%Y-%m-%d %H:00")
            else:  # weekly
                period_key = entry_date.strftime("%Y-W%W")

            if entry.amount < 0:  # Consumption
                time_series[period_key]["consumed"] += abs(entry.amount)
            else:  # Refund
                time_series[period_key]["refunded"] += entry.amount

        # Convert to list and calculate net
        time_series_list = [
            {
                "period": key,
                "consumed": round(values["consumed"], 2),
                "refunded": round(values["refunded"], 2),
                "net": round(values["consumed"] - values["refunded"], 2),
            }
            for key, values in sorted(time_series.items())
        ]

        # Calculate trend
        if len(time_series_list) >= 2:
            first_net = time_series_list[0]["net"]
            last_net = time_series_list[-1]["net"]

            if first_net > 0:
                trend_percentage = ((last_net - first_net) / first_net) * 100
            else:
                trend_percentage = 0.0

            if trend_percentage > 10:
                trend_direction = "increasing"
            elif trend_percentage < -10:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "unknown"
            trend_percentage = 0.0

        return {
            "period_days": days,
            "granularity": granularity,
            "time_series": time_series_list,
            "trend_direction": trend_direction,
            "trend_percentage": round(trend_percentage, 2),
        }

    async def detect_anomalies(
        self,
        threshold_multiplier: float = 2.0,
    ) -> List[Dict]:
        """
        Detect anomalous credit transactions.

        Args:
            threshold_multiplier: Anomaly threshold (avg + threshold * std)

        Returns:
            List of anomalous transactions
        """
        if not self.credit_system:
            raise ValueError("Analytics not initialized")

        # Get all histories
        all_balances = await self.credit_system.get_all_balances()
        all_history = []
        for agent_id in all_balances.keys():
            agent_history = await self.credit_system.get_history(agent_id, limit=1000)
            all_history.extend(agent_history)

        # Calculate statistics
        amounts = [abs(entry.amount) for entry in all_history]
        if not amounts:
            return []

        avg_amount = sum(amounts) / len(amounts)
        variance = sum((x - avg_amount) ** 2 for x in amounts) / len(amounts)
        std_dev = variance ** 0.5

        threshold = avg_amount + (threshold_multiplier * std_dev)

        # Find anomalies
        anomalies = []
        for entry in all_history:
            if abs(entry.amount) > threshold:
                anomalies.append({
                    "event_id": entry.event_id,
                    "timestamp": entry.timestamp,
                    "entity_id": entry.entity_id,
                    "amount": entry.amount,
                    "reason": entry.reason,
                    "threshold": round(threshold, 2),
                    "deviation": round(abs(entry.amount) - avg_amount, 2),
                })

        return anomalies

    async def get_resource_utilization(self) -> Dict:
        """
        Get resource utilization metrics.

        Returns:
            Dict with utilization metrics:
            - total_allocated: Total credits in system
            - total_consumed: Total credits ever consumed
            - total_available: Total credits available
            - utilization_rate: % of allocated credits consumed
            - agent_count: Number of agents
            - avg_balance: Average balance per agent
        """
        if not self.credit_system:
            raise ValueError("Analytics not initialized")

        # Get all balances
        all_balances = await self.credit_system.get_all_balances()

        total_available = sum(all_balances.values())
        agent_count = len(all_balances)
        avg_balance = total_available / agent_count if agent_count > 0 else 0

        # Get total consumed from history
        total_consumed = 0.0
        for agent_id in all_balances.keys():
            history = await self.credit_system.get_history(agent_id, limit=1000)
            for entry in history:
                if entry.amount < 0:  # Consumption
                    total_consumed += abs(entry.amount)

        # Calculate total allocated (available + consumed)
        total_allocated = total_available + total_consumed

        utilization_rate = (
            (total_consumed / total_allocated * 100) if total_allocated > 0 else 0
        )

        return {
            "total_allocated": round(total_allocated, 2),
            "total_consumed": round(total_consumed, 2),
            "total_available": round(total_available, 2),
            "utilization_rate": round(utilization_rate, 2),
            "agent_count": agent_count,
            "avg_balance": round(avg_balance, 2),
        }

    async def get_top_consumers(
        self,
        limit: int = 10,
        days: int = 30,
    ) -> List[Dict]:
        """
        Get top credit consumers.

        Args:
            limit: Number of top consumers
            days: Period to analyze

        Returns:
            List of top consumers with consumption stats
        """
        if not self.credit_system:
            raise ValueError("Analytics not initialized")

        # Get all balances
        all_balances = await self.credit_system.get_all_balances()

        # Calculate consumption per agent
        agent_consumption = {}
        cutoff_date = datetime.now() - timedelta(days=days)

        for agent_id in all_balances.keys():
            history = await self.credit_system.get_history(agent_id, limit=1000)

            # Filter by date and calculate consumption
            total_consumed = 0.0
            transaction_count = 0

            for entry in history:
                entry_date = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
                if entry_date > cutoff_date and entry.amount < 0:
                    total_consumed += abs(entry.amount)
                    transaction_count += 1

            if total_consumed > 0:
                agent_consumption[agent_id] = {
                    "agent_id": agent_id,
                    "total_consumed": round(total_consumed, 2),
                    "transaction_count": transaction_count,
                    "avg_transaction": round(
                        total_consumed / transaction_count if transaction_count > 0 else 0, 2
                    ),
                    "current_balance": round(all_balances[agent_id], 2),
                }

        # Sort by total consumed
        top_consumers = sorted(
            agent_consumption.values(),
            key=lambda x: x["total_consumed"],
            reverse=True,
        )[:limit]

        return top_consumers


# ============================================================================
# Singleton Pattern
# ============================================================================

_analytics_instance: Optional[CreditAnalytics] = None


async def get_credit_analytics() -> CreditAnalytics:
    """
    Get singleton CreditAnalytics instance.

    Returns:
        CreditAnalytics instance (initialized)
    """
    global _analytics_instance

    if _analytics_instance is None:
        _analytics_instance = CreditAnalytics()
        await _analytics_instance.initialize()

    return _analytics_instance
