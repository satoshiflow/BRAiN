"""
Adaptive Behavior - KARMA-integrated strategy selection and adaptation.

Agents maintain multiple strategies per domain. The system uses
an epsilon-greedy approach (exploration vs exploitation) weighted
by KARMA scores to select the best strategy for each situation.

Learning loop:
    1. Select strategy (exploit best or explore candidate)
    2. Apply strategy to task
    3. Observe outcome (success/failure + metrics)
    4. Update strategy scores (KARMA, confidence, success rate)
    5. Promote/demote strategies based on performance
"""

from __future__ import annotations

import random
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from loguru import logger

from .schemas import (
    LearningStrategy,
    StrategyStatus,
)

# Minimum applications before a strategy can be promoted
MIN_APPLICATIONS_FOR_PROMOTION = 10

# KARMA change per outcome
KARMA_SUCCESS_BOOST = 2.0
KARMA_FAILURE_PENALTY = 1.5

# Confidence growth rate
CONFIDENCE_GROWTH = 0.05
CONFIDENCE_DECAY = 0.02


class AdaptiveBehavior:
    """
    Manages learning strategies per agent and domain.

    Uses epsilon-greedy selection with KARMA weighting.
    """

    def __init__(self, exploration_rate: float = 0.2) -> None:
        # Strategies: agent_id → domain → list of strategies
        self._strategies: Dict[str, Dict[str, List[LearningStrategy]]] = defaultdict(
            lambda: defaultdict(list)
        )

        self._exploration_rate = exploration_rate
        self._total_selections = 0
        self._total_adaptations = 0

        logger.info("🧠 AdaptiveBehavior initialized (exploration=%.2f)", exploration_rate)

    # ------------------------------------------------------------------
    # Strategy management
    # ------------------------------------------------------------------

    def register_strategy(self, strategy: LearningStrategy) -> LearningStrategy:
        """Register a new strategy for an agent+domain."""
        domain_strategies = self._strategies[strategy.agent_id][strategy.domain]

        # Check for duplicate name
        for existing in domain_strategies:
            if existing.name == strategy.name:
                logger.warning("Strategy '%s' already exists for %s/%s", strategy.name, strategy.agent_id, strategy.domain)
                return existing

        domain_strategies.append(strategy)
        logger.info("📝 Strategy registered: '%s' for %s/%s", strategy.name, strategy.agent_id, strategy.domain)
        return strategy

    def get_strategies(
        self,
        agent_id: str,
        domain: Optional[str] = None,
        status: Optional[StrategyStatus] = None,
    ) -> List[LearningStrategy]:
        """Get strategies for an agent, optionally filtered."""
        if domain:
            strategies = list(self._strategies.get(agent_id, {}).get(domain, []))
        else:
            strategies = []
            for d_strategies in self._strategies.get(agent_id, {}).values():
                strategies.extend(d_strategies)

        if status:
            strategies = [s for s in strategies if s.status == status]

        return strategies

    def get_strategy(self, strategy_id: str) -> Optional[LearningStrategy]:
        """Find a strategy by ID across all agents."""
        for agent_domains in self._strategies.values():
            for domain_strategies in agent_domains.values():
                for s in domain_strategies:
                    if s.strategy_id == strategy_id:
                        return s
        return None

    # ------------------------------------------------------------------
    # Strategy selection (epsilon-greedy + KARMA)
    # ------------------------------------------------------------------

    def select_strategy(
        self,
        agent_id: str,
        domain: str,
    ) -> Optional[LearningStrategy]:
        """
        Select the best strategy using epsilon-greedy with KARMA weighting.

        With probability epsilon: explore (pick random candidate/active)
        With probability 1-epsilon: exploit (pick highest-scoring active)
        """
        strategies = self._strategies.get(agent_id, {}).get(domain, [])
        if not strategies:
            return None

        # Filter to usable strategies (ACTIVE, CANDIDATE, EVALUATING)
        usable = [
            s for s in strategies
            if s.status in (StrategyStatus.ACTIVE, StrategyStatus.CANDIDATE, StrategyStatus.EVALUATING)
        ]
        if not usable:
            return None

        self._total_selections += 1

        # Epsilon-greedy
        if random.random() < self._exploration_rate:
            # Explore: prefer candidates (untested)
            candidates = [s for s in usable if s.status == StrategyStatus.CANDIDATE]
            if candidates:
                selected = random.choice(candidates)
            else:
                selected = random.choice(usable)
            logger.debug("🔍 Explore: selected '%s' for %s/%s", selected.name, agent_id, domain)
        else:
            # Exploit: pick highest score
            usable.sort(key=lambda s: s.score, reverse=True)
            selected = usable[0]
            logger.debug("🎯 Exploit: selected '%s' (score=%.3f) for %s/%s", selected.name, selected.score, agent_id, domain)

        selected.total_applications += 1
        selected.updated_at = datetime.utcnow()
        return selected

    # ------------------------------------------------------------------
    # Outcome recording
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        strategy_id: str,
        success: bool,
        metric_value: Optional[float] = None,
    ) -> Optional[LearningStrategy]:
        """
        Record outcome of applying a strategy.

        Updates KARMA, confidence, success/failure counts.
        May trigger promotion/demotion.
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return None

        self._total_adaptations += 1

        if success:
            strategy.success_count += 1
            strategy.karma_score = min(100.0, strategy.karma_score + KARMA_SUCCESS_BOOST)
            strategy.confidence = min(1.0, strategy.confidence + CONFIDENCE_GROWTH)
        else:
            strategy.failure_count += 1
            strategy.karma_score = max(0.0, strategy.karma_score - KARMA_FAILURE_PENALTY)
            strategy.confidence = max(0.0, strategy.confidence - CONFIDENCE_DECAY)

        strategy.updated_at = datetime.utcnow()

        # Check for promotion/demotion
        self._evaluate_strategy(strategy)

        return strategy

    # ------------------------------------------------------------------
    # Promotion / demotion
    # ------------------------------------------------------------------

    def _evaluate_strategy(self, strategy: LearningStrategy) -> None:
        """Evaluate whether to promote or demote a strategy."""
        if strategy.total_applications < MIN_APPLICATIONS_FOR_PROMOTION:
            return

        if strategy.status == StrategyStatus.CANDIDATE:
            # Promote candidates with good performance
            if strategy.success_rate >= 0.7 and strategy.karma_score >= 60.0:
                strategy.status = StrategyStatus.ACTIVE
                logger.info("⬆️ Strategy promoted to ACTIVE: '%s' (sr=%.2f, karma=%.1f)",
                            strategy.name, strategy.success_rate, strategy.karma_score)

        elif strategy.status == StrategyStatus.ACTIVE:
            # Demote active strategies with bad performance
            if strategy.success_rate < 0.3 and strategy.karma_score < 30.0:
                strategy.status = StrategyStatus.DEMOTED
                logger.info("⬇️ Strategy demoted: '%s' (sr=%.2f, karma=%.1f)",
                            strategy.name, strategy.success_rate, strategy.karma_score)

    def promote_strategy(self, strategy_id: str) -> Optional[LearningStrategy]:
        """Manually promote a strategy (e.g., after winning A/B test)."""
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return None
        strategy.status = StrategyStatus.PROMOTED
        strategy.updated_at = datetime.utcnow()
        return strategy

    def demote_strategy(self, strategy_id: str) -> Optional[LearningStrategy]:
        """Manually demote a strategy."""
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return None
        strategy.status = StrategyStatus.DEMOTED
        strategy.updated_at = datetime.utcnow()
        return strategy

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def stats(self) -> Dict:
        total = 0
        active = 0
        for agent_domains in self._strategies.values():
            for domain_strategies in agent_domains.values():
                for s in domain_strategies:
                    total += 1
                    if s.status == StrategyStatus.ACTIVE:
                        active += 1
        return {
            "total_strategies": total,
            "active_strategies": active,
            "total_selections": self._total_selections,
            "total_adaptations": self._total_adaptations,
            "exploration_rate": self._exploration_rate,
        }
