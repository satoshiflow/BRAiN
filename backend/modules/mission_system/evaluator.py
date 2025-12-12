"""
BRAIN Mission System V1 - Mission Evaluator
===========================================

KARMA-integrated mission evaluation system for assessing the impact,
efficiency, and ethical implications of completed missions.

Key Features:
- Multi-dimensional KARMA scoring (Efficiency, Impact, Empathy, Sustainability)
- Automated evaluation based on execution metrics
- Learning feedback loops for continuous improvement
- Integration with agent performance tracking
- Ethical assessment framework

KARMA Philosophy:
- Efficiency: How well resources were utilized
- Impact: Positive or negative effect on the ecosystem  
- Empathy: Consideration for all stakeholders
- Sustainability: Long-term viability of actions

Author: Claude (Chief Developer)
Project: BRAIN Framework by FalkLabs / Olaf Falk
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics
import json

from .models import (
    Mission, MissionResult, MissionStatus, KarmaEvent, MissionType
)


logger = logging.getLogger(__name__)


class EvaluationCriteria(str, Enum):
    """Criteria for mission evaluation"""
    EFFICIENCY = "efficiency"
    IMPACT = "impact"
    EMPATHY = "empathy"
    SUSTAINABILITY = "sustainability"
    QUALITY = "quality"
    TIMELINESS = "timeliness"
    RESOURCE_USAGE = "resource_usage"
    STAKEHOLDER_SATISFACTION = "stakeholder_satisfaction"


@dataclass
class EvaluationMetrics:
    """
    Comprehensive metrics for mission evaluation
    """
    execution_time: float
    planned_time: Optional[float]
    resource_consumption: float
    estimated_resources: Optional[float]
    success_rate: float
    error_count: int
    retry_count: int
    agent_performance: float
    output_quality: float
    stakeholder_impact: float
    
    def calculate_efficiency_score(self) -> float:
        """Calculate efficiency score based on time and resource usage"""
        time_efficiency = 1.0
        if self.planned_time and self.planned_time > 0:
            time_efficiency = min(1.0, self.planned_time / self.execution_time)
        
        resource_efficiency = 1.0
        if self.estimated_resources and self.estimated_resources > 0:
            resource_efficiency = min(1.0, self.estimated_resources / self.resource_consumption)
        
        error_penalty = max(0.0, 1.0 - (self.error_count * 0.1))
        retry_penalty = max(0.0, 1.0 - (self.retry_count * 0.05))
        
        return (time_efficiency * 0.4 + resource_efficiency * 0.4 + 
                error_penalty * 0.1 + retry_penalty * 0.1)


class MissionEvaluator:
    """
    KARMA-based evaluation system for assessing mission performance
    and generating improvement recommendations.
    """
    
    def __init__(self):
        """Initialize the mission evaluator"""
        self.evaluation_history: Dict[str, KarmaEvent] = {}
        self.agent_karma_scores: Dict[str, List[float]] = {}
        self.mission_type_benchmarks: Dict[str, Dict[str, float]] = {}
        
        # Evaluation weights for different mission types
        self.evaluation_weights = {
            MissionType.ANALYSIS: {
                "efficiency": 0.3,
                "impact": 0.4,
                "empathy": 0.15,
                "sustainability": 0.15
            },
            MissionType.COMMUNICATION: {
                "efficiency": 0.2,
                "impact": 0.3,
                "empathy": 0.35,
                "sustainability": 0.15
            },
            MissionType.EXECUTION: {
                "efficiency": 0.4,
                "impact": 0.35,
                "empathy": 0.1,
                "sustainability": 0.15
            },
            MissionType.LEARNING: {
                "efficiency": 0.25,
                "impact": 0.25,
                "empathy": 0.25,
                "sustainability": 0.25
            },
            MissionType.COORDINATION: {
                "efficiency": 0.3,
                "impact": 0.25,
                "empathy": 0.3,
                "sustainability": 0.15
            },
            MissionType.MAINTENANCE: {
                "efficiency": 0.4,
                "impact": 0.2,
                "empathy": 0.1,
                "sustainability": 0.3
            }
        }
        
        # Initialize benchmarks
        self._initialize_benchmarks()
    
    def _initialize_benchmarks(self) -> None:
        """Initialize performance benchmarks for different mission types"""
        # Default benchmarks - in production these would be learned from data
        default_benchmarks = {
            "average_execution_time": 300.0,  # 5 minutes
            "resource_efficiency": 0.8,
            "success_rate": 0.95,
            "error_rate": 0.05
        }
        
        for mission_type in MissionType:
            self.mission_type_benchmarks[mission_type.value] = default_benchmarks.copy()
    
    async def evaluate_mission(
        self, 
        mission: Mission,
        mission_result: MissionResult,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> KarmaEvent:
        """
        Perform comprehensive KARMA evaluation of a completed mission.
        
        Args:
            mission: The completed mission
            mission_result: Execution results
            additional_context: Additional evaluation context
            
        Returns:
            KARMA evaluation event
        """
        try:
            logger.info(f"Evaluating mission {mission.id} with KARMA framework")
            
            # Collect evaluation metrics
            metrics = await self._collect_evaluation_metrics(mission, mission_result)
            
            # Calculate individual KARMA dimensions
            efficiency_score = await self._evaluate_efficiency(mission, metrics)
            impact_score = await self._evaluate_impact(mission, mission_result, metrics)
            empathy_score = await self._evaluate_empathy(mission, metrics, additional_context)
            sustainability_score = await self._evaluate_sustainability(mission, metrics)
            
            # Create KARMA event
            karma_event = KarmaEvent(
                mission_id=mission.id,
                agent_id=mission.assigned_agent_id or "system",
                efficiency_score=efficiency_score,
                impact_score=impact_score,
                empathy_score=empathy_score,
                sustainability_score=sustainability_score,
                evaluation_criteria=[
                    EvaluationCriteria.EFFICIENCY.value,
                    EvaluationCriteria.IMPACT.value,
                    EvaluationCriteria.EMPATHY.value,
                    EvaluationCriteria.SUSTAINABILITY.value
                ],
                evaluator_agent="karma_evaluator_v1",
                feedback=await self._generate_feedback(mission, metrics, {
                    "efficiency": efficiency_score,
                    "impact": impact_score,
                    "empathy": empathy_score,
                    "sustainability": sustainability_score
                }),
                improvement_suggestions=await self._generate_improvements(mission, metrics)
            )
            
            # Store evaluation
            self.evaluation_history[mission.id] = karma_event
            
            # Update agent karma tracking
            if mission.assigned_agent_id:
                if mission.assigned_agent_id not in self.agent_karma_scores:
                    self.agent_karma_scores[mission.assigned_agent_id] = []
                
                self.agent_karma_scores[mission.assigned_agent_id].append(
                    karma_event.total_karma
                )
            
            # Update benchmarks
            await self._update_benchmarks(mission, metrics)
            
            logger.info(f"Mission {mission.id} KARMA evaluation completed: "
                       f"total={karma_event.total_karma:.3f}, "
                       f"efficiency={efficiency_score:.3f}, "
                       f"impact={impact_score:.3f}, "
                       f"empathy={empathy_score:.3f}, "
                       f"sustainability={sustainability_score:.3f}")
            
            return karma_event
            
        except Exception as e:
            logger.error(f"Failed to evaluate mission {mission.id}: {e}")
            
            # Return default neutral evaluation
            return KarmaEvent(
                mission_id=mission.id,
                agent_id=mission.assigned_agent_id or "system",
                efficiency_score=0.5,
                impact_score=0.0,
                empathy_score=0.5,
                sustainability_score=0.5,
                evaluation_criteria=["default"],
                evaluator_agent="karma_evaluator_v1",
                feedback="Evaluation failed - using default neutral scores"
            )
    
    async def _collect_evaluation_metrics(
        self, 
        mission: Mission, 
        result: MissionResult
    ) -> EvaluationMetrics:
        """
        Collect comprehensive metrics for evaluation.
        
        Args:
            mission: Mission to evaluate
            result: Mission execution result
            
        Returns:
            Collected evaluation metrics
        """
        # Calculate execution efficiency
        planned_time = None
        if mission.tasks:
            planned_time = sum(
                task.estimated_duration or 60 
                for task in mission.tasks
            )
        
        # Calculate success rate
        if result.total_tasks > 0:
            success_rate = result.completed_tasks / result.total_tasks
        else:
            success_rate = 1.0 if result.final_status == MissionStatus.COMPLETED else 0.0
        
        # Calculate agent performance (simplified)
        agent_performance = success_rate * (1.0 if len(result.errors) == 0 else 0.8)
        
        # Assess output quality (based on result structure and completeness)
        output_quality = self._assess_output_quality(result)
        
        # Calculate stakeholder impact (simplified)
        stakeholder_impact = self._assess_stakeholder_impact(mission, result)
        
        return EvaluationMetrics(
            execution_time=result.execution_time,
            planned_time=planned_time,
            resource_consumption=result.credits_consumed,
            estimated_resources=mission.estimated_credits,
            success_rate=success_rate,
            error_count=len(result.errors),
            retry_count=self._count_retries(mission),
            agent_performance=agent_performance,
            output_quality=output_quality,
            stakeholder_impact=stakeholder_impact
        )
    
    async def _evaluate_efficiency(
        self, 
        mission: Mission, 
        metrics: EvaluationMetrics
    ) -> float:
        """
        Evaluate mission efficiency based on resource usage and execution time.
        
        Args:
            mission: Mission to evaluate
            metrics: Evaluation metrics
            
        Returns:
            Efficiency score (0.0-1.0)
        """
        # Base efficiency from metrics
        base_efficiency = metrics.calculate_efficiency_score()
        
        # Compare against mission type benchmarks
        benchmarks = self.mission_type_benchmarks.get(mission.mission_type.value, {})
        benchmark_time = benchmarks.get("average_execution_time", 300.0)
        
        # Time efficiency relative to benchmark
        if benchmark_time > 0:
            time_factor = min(1.0, benchmark_time / metrics.execution_time)
        else:
            time_factor = 1.0
        
        # Resource efficiency
        resource_factor = 1.0
        if (metrics.estimated_resources and metrics.estimated_resources > 0 and
            metrics.resource_consumption > 0):
            resource_factor = min(1.0, metrics.estimated_resources / metrics.resource_consumption)
        
        # Combine factors
        efficiency_score = (base_efficiency * 0.5 + time_factor * 0.3 + resource_factor * 0.2)
        
        return max(0.0, min(1.0, efficiency_score))
    
    async def _evaluate_impact(
        self, 
        mission: Mission, 
        result: MissionResult,
        metrics: EvaluationMetrics
    ) -> float:
        """
        Evaluate mission impact on the ecosystem.
        
        Args:
            mission: Mission to evaluate
            result: Mission result
            metrics: Evaluation metrics
            
        Returns:
            Impact score (-1.0 to 1.0)
        """
        # Base impact from success
        base_impact = 0.5 if result.final_status == MissionStatus.COMPLETED else -0.3
        
        # Mission type specific impact assessment
        if mission.mission_type == MissionType.ANALYSIS:
            # Analysis missions provide knowledge value
            if result.outputs and "analysis_results" in result.outputs:
                analysis_quality = result.outputs["analysis_results"].get("quality", 0.5)
                base_impact += analysis_quality * 0.3
        
        elif mission.mission_type == MissionType.COORDINATION:
            # Coordination missions improve system efficiency
            if metrics.success_rate > 0.9:
                base_impact += 0.4  # High success in coordination is very valuable
        
        elif mission.mission_type == MissionType.MAINTENANCE:
            # Maintenance missions preserve system health
            base_impact += 0.3  # Maintenance is inherently positive
        
        # Factor in stakeholder impact
        stakeholder_factor = (metrics.stakeholder_impact - 0.5) * 0.4
        
        # Quality factor
        quality_factor = (metrics.output_quality - 0.5) * 0.3
        
        final_impact = base_impact + stakeholder_factor + quality_factor
        
        return max(-1.0, min(1.0, final_impact))
    
    async def _evaluate_empathy(
        self, 
        mission: Mission, 
        metrics: EvaluationMetrics,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Evaluate empathetic consideration in mission execution.
        
        Args:
            mission: Mission to evaluate
            metrics: Evaluation metrics
            additional_context: Additional context
            
        Returns:
            Empathy score (0.0-1.0)
        """
        base_empathy = 0.5  # Neutral starting point
        
        # Communication quality assessment
        if mission.mission_type == MissionType.COMMUNICATION:
            # For communication missions, empathy is crucial
            if metrics.stakeholder_impact > 0.7:
                base_empathy += 0.3
            elif metrics.stakeholder_impact < 0.3:
                base_empathy -= 0.2
        
        # Error handling assessment
        if metrics.error_count > 0:
            # How gracefully were errors handled?
            error_grace = 1.0 / (1.0 + metrics.error_count * 0.1)
            base_empathy *= error_grace
        
        # Consideration for other agents (simplified)
        if mission.assigned_agents and len(mission.assigned_agents) > 1:
            # Multi-agent missions require empathy
            base_empathy += 0.2
        
        # Context-specific empathy factors
        if additional_context:
            user_feedback = additional_context.get("user_satisfaction", 0.5)
            base_empathy = base_empathy * 0.7 + user_feedback * 0.3
        
        return max(0.0, min(1.0, base_empathy))
    
    async def _evaluate_sustainability(
        self, 
        mission: Mission, 
        metrics: EvaluationMetrics
    ) -> float:
        """
        Evaluate long-term sustainability of mission approach.
        
        Args:
            mission: Mission to evaluate
            metrics: Evaluation metrics
            
        Returns:
            Sustainability score (0.0-1.0)
        """
        base_sustainability = 0.5
        
        # Resource efficiency is key to sustainability
        resource_efficiency = 1.0
        if (metrics.estimated_resources and metrics.estimated_resources > 0 and
            metrics.resource_consumption > 0):
            resource_efficiency = min(1.0, metrics.estimated_resources / metrics.resource_consumption)
        
        # Lower retry count indicates sustainable approach
        retry_penalty = max(0.0, 1.0 - (metrics.retry_count * 0.1))
        
        # Success rate indicates robust approach
        success_factor = metrics.success_rate
        
        # Mission type specific factors
        if mission.mission_type == MissionType.MAINTENANCE:
            # Maintenance missions are inherently sustainable
            base_sustainability += 0.2
        elif mission.mission_type == MissionType.LEARNING:
            # Learning improves long-term sustainability
            base_sustainability += 0.15
        
        final_sustainability = (
            base_sustainability * 0.4 +
            resource_efficiency * 0.3 +
            retry_penalty * 0.15 +
            success_factor * 0.15
        )
        
        return max(0.0, min(1.0, final_sustainability))
    
    def _assess_output_quality(self, result: MissionResult) -> float:
        """
        Assess the quality of mission outputs.
        
        Args:
            result: Mission result to assess
            
        Returns:
            Quality score (0.0-1.0)
        """
        base_quality = 0.5
        
        # Completeness assessment
        if result.outputs:
            # Has outputs - positive
            base_quality += 0.2
            
            # Check for structured data
            for key, value in result.outputs.items():
                if isinstance(value, dict) and value:
                    base_quality += 0.1
        
        # Error-free execution
        if len(result.errors) == 0:
            base_quality += 0.2
        else:
            base_quality -= len(result.errors) * 0.05
        
        # Success rate consideration
        if result.total_tasks > 0:
            success_rate = result.completed_tasks / result.total_tasks
            base_quality = base_quality * 0.7 + success_rate * 0.3
        
        return max(0.0, min(1.0, base_quality))
    
    def _assess_stakeholder_impact(
        self, 
        mission: Mission, 
        result: MissionResult
    ) -> float:
        """
        Assess impact on stakeholders.
        
        Args:
            mission: Mission to assess
            result: Mission result
            
        Returns:
            Stakeholder impact score (0.0-1.0)
        """
        # Simplified stakeholder assessment
        base_impact = 0.5
        
        # Success generally benefits stakeholders
        if result.final_status == MissionStatus.COMPLETED:
            base_impact += 0.3
        elif result.final_status == MissionStatus.FAILED:
            base_impact -= 0.2
        
        # Mission type specific benefits
        if mission.mission_type in [MissionType.COMMUNICATION, MissionType.COORDINATION]:
            # These directly benefit other agents
            base_impact += 0.2
        
        return max(0.0, min(1.0, base_impact))
    
    def _count_retries(self, mission: Mission) -> int:
        """Count total retries across all mission tasks"""
        if not mission.tasks:
            return 0
        
        return sum(task.current_retries for task in mission.tasks)
    
    async def _generate_feedback(
        self, 
        mission: Mission, 
        metrics: EvaluationMetrics,
        scores: Dict[str, float]
    ) -> str:
        """
        Generate qualitative feedback based on evaluation.
        
        Args:
            mission: Evaluated mission
            metrics: Evaluation metrics
            scores: KARMA scores
            
        Returns:
            Feedback text
        """
        feedback_parts = []
        
        # Overall assessment
        total_karma = scores.get("efficiency", 0) * 0.3 + \
                     scores.get("impact", 0) * 0.4 + \
                     scores.get("empathy", 0) * 0.2 + \
                     scores.get("sustainability", 0) * 0.1
        
        if total_karma > 0.7:
            feedback_parts.append("Excellent mission execution with strong KARMA alignment.")
        elif total_karma > 0.5:
            feedback_parts.append("Good mission performance with room for improvement.")
        else:
            feedback_parts.append("Mission performance below expectations - significant improvements needed.")
        
        # Specific dimension feedback
        if scores.get("efficiency", 0) < 0.4:
            feedback_parts.append("Resource efficiency could be improved.")
        
        if scores.get("impact", 0) > 0.7:
            feedback_parts.append("Mission created positive ecosystem impact.")
        elif scores.get("impact", 0) < 0:
            feedback_parts.append("Mission had negative impact - consider approach revision.")
        
        if scores.get("empathy", 0) > 0.7:
            feedback_parts.append("Strong empathetic consideration demonstrated.")
        
        if scores.get("sustainability", 0) < 0.4:
            feedback_parts.append("Long-term sustainability concerns identified.")
        
        return " ".join(feedback_parts)
    
    async def _generate_improvements(
        self, 
        mission: Mission, 
        metrics: EvaluationMetrics
    ) -> List[str]:
        """
        Generate improvement suggestions.
        
        Args:
            mission: Mission to analyze
            metrics: Evaluation metrics
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Efficiency improvements
        if metrics.execution_time > 0:
            benchmarks = self.mission_type_benchmarks.get(mission.mission_type.value, {})
            benchmark_time = benchmarks.get("average_execution_time", 300.0)
            
            if metrics.execution_time > benchmark_time * 1.5:
                suggestions.append("Consider optimizing task execution for faster completion")
        
        # Error reduction
        if metrics.error_count > 0:
            suggestions.append("Implement additional error handling and validation")
        
        # Resource optimization
        if (metrics.estimated_resources and metrics.resource_consumption > 0 and
            metrics.resource_consumption > metrics.estimated_resources * 1.2):
            suggestions.append("Improve resource estimation and usage optimization")
        
        # Retry reduction
        if metrics.retry_count > 2:
            suggestions.append("Enhance task reliability to reduce retry requirements")
        
        # Mission type specific suggestions
        if mission.mission_type == MissionType.ANALYSIS:
            if metrics.output_quality < 0.6:
                suggestions.append("Enhance analysis depth and result presentation")
        
        elif mission.mission_type == MissionType.COMMUNICATION:
            if metrics.stakeholder_impact < 0.6:
                suggestions.append("Improve communication clarity and stakeholder engagement")
        
        return suggestions
    
    async def _update_benchmarks(
        self, 
        mission: Mission, 
        metrics: EvaluationMetrics
    ) -> None:
        """
        Update performance benchmarks based on mission performance.
        
        Args:
            mission: Completed mission
            metrics: Evaluation metrics
        """
        mission_type = mission.mission_type.value
        
        if mission_type not in self.mission_type_benchmarks:
            self.mission_type_benchmarks[mission_type] = {}
        
        benchmarks = self.mission_type_benchmarks[mission_type]
        
        # Update execution time benchmark (moving average)
        if "average_execution_time" in benchmarks:
            current_avg = benchmarks["average_execution_time"]
            # Simple exponential moving average
            benchmarks["average_execution_time"] = current_avg * 0.9 + metrics.execution_time * 0.1
        else:
            benchmarks["average_execution_time"] = metrics.execution_time
        
        # Update success rate benchmark
        if "success_rate" in benchmarks:
            current_rate = benchmarks["success_rate"]
            benchmarks["success_rate"] = current_rate * 0.9 + metrics.success_rate * 0.1
        else:
            benchmarks["success_rate"] = metrics.success_rate
    
    def get_agent_karma_summary(self, agent_id: str) -> Dict[str, Any]:
        """
        Get KARMA summary for a specific agent.
        
        Args:
            agent_id: Agent to get summary for
            
        Returns:
            Agent KARMA summary
        """
        if agent_id not in self.agent_karma_scores:
            return {"agent_id": agent_id, "karma_history": [], "average_karma": 0.0}
        
        karma_scores = self.agent_karma_scores[agent_id]
        
        return {
            "agent_id": agent_id,
            "mission_count": len(karma_scores),
            "average_karma": statistics.mean(karma_scores) if karma_scores else 0.0,
            "latest_karma": karma_scores[-1] if karma_scores else 0.0,
            "karma_trend": self._calculate_trend(karma_scores),
            "karma_history": karma_scores[-10:]  # Last 10 scores
        }
    
    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate trend in KARMA scores"""
        if len(scores) < 2:
            return "insufficient_data"
        
        recent_avg = statistics.mean(scores[-3:]) if len(scores) >= 3 else scores[-1]
        earlier_avg = statistics.mean(scores[:-3]) if len(scores) > 3 else scores[0]
        
        diff = recent_avg - earlier_avg
        
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"
    
    def get_evaluation_summary(self) -> Dict[str, Any]:
        """
        Get summary of all evaluations.
        
        Returns:
            Evaluation summary
        """
        if not self.evaluation_history:
            return {"total_evaluations": 0}
        
        all_scores = [event.total_karma for event in self.evaluation_history.values()]
        
        return {
            "total_evaluations": len(self.evaluation_history),
            "average_karma": statistics.mean(all_scores),
            "karma_range": {
                "min": min(all_scores),
                "max": max(all_scores)
            },
            "recent_trend": self._calculate_trend(all_scores),
            "mission_type_benchmarks": self.mission_type_benchmarks
        }


# Global evaluator instance
evaluator: Optional[MissionEvaluator] = None


def get_evaluator() -> MissionEvaluator:
    """Get the global evaluator instance"""
    global evaluator
    if evaluator is None:
        evaluator = MissionEvaluator()
    return evaluator


async def evaluate_mission(
    mission: Mission,
    mission_result: MissionResult,
    additional_context: Optional[Dict[str, Any]] = None
) -> KarmaEvent:
    """Convenience function to evaluate a mission"""
    evaluator_instance = get_evaluator()
    return await evaluator_instance.evaluate_mission(mission, mission_result, additional_context)
