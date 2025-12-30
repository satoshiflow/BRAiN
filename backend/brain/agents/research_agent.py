"""
Research Agent - Constitutional AI Agent for Information Research

Specializes in information gathering, source analysis, and knowledge synthesis
with DSGVO compliance and human oversight for high-risk research.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from backend.brain.agents.base_agent import BaseAgent
from backend.brain.agents.supervisor_agent import get_supervisor_agent, SupervisionRequest, RiskLevel


class ResearchType(str, Enum):
    """Types of research tasks"""
    WEB_SEARCH = "web_search"
    DOCUMENT_ANALYSIS = "document_analysis"
    LITERATURE_REVIEW = "literature_review"
    DATA_GATHERING = "data_gathering"
    SOURCE_VALIDATION = "source_validation"


class ResearchAgent(BaseAgent):
    """
    Constitutional Research Agent

    **Purpose:** Information gathering and analysis with ethical constraints

    **Capabilities:**
    - Web search and information retrieval
    - Document analysis and summarization
    - Source credibility validation
    - Literature reviews
    - Data gathering from public sources

    **Risk Management:**
    - MEDIUM risk for web searches (source validation required)
    - LOW risk for document analysis (read-only)
    - HIGH risk for personal data gathering (DSGVO Art. 5, 6)

    **Supervision:**
    - Automatic approval: LOW/MEDIUM risk research
    - Human oversight: HIGH risk (personal data, sensitive topics)

    **DSGVO Compliance:**
    - Data minimization (Art. 5)
    - Legal basis for personal data (Art. 6)
    - Source citation and transparency
    """

    def __init__(self):
        super().__init__()
        self.agent_id = "research_agent"
        self.name = "ResearchAgent"
        self.supervisor = get_supervisor_agent()

        # Constitutional constraints
        self.forbidden_topics = [
            "illegal_activities",
            "violence",
            "discrimination",
            "misinformation_spreading"
        ]

        # Register tools
        self.register_tool("web_search", self._web_search)
        self.register_tool("analyze_document", self._analyze_document)
        self.register_tool("validate_source", self._validate_source)
        self.register_tool("gather_data", self._gather_data)

    async def run(self, task: str, **kwargs) -> Dict[str, Any]:
        """
        Execute research task with constitutional supervision.

        Args:
            task: Research task description
            **kwargs:
                research_type: ResearchType
                sources: List of sources to use
                max_results: Maximum number of results
                include_personal_data: Boolean (triggers HIGH risk)

        Returns:
            Dictionary with research results and metadata
        """
        research_type = kwargs.get("research_type", ResearchType.WEB_SEARCH)
        include_personal_data = kwargs.get("include_personal_data", False)

        # Determine risk level
        risk_level = self._assess_risk(task, research_type, include_personal_data)

        # Request supervision
        supervision_request = SupervisionRequest(
            requesting_agent=self.agent_id,
            action="conduct_research",
            context={
                "task": task,
                "research_type": research_type,
                "include_personal_data": include_personal_data,
                "risk_level": risk_level.value,
            },
            risk_level=risk_level,
            reason=f"Research task: {research_type.value}"
        )

        supervision_response = await self.supervisor.supervise_action(supervision_request)

        if not supervision_response.approved:
            return {
                "success": False,
                "error": "Research denied by supervisor",
                "reason": supervision_response.reason,
                "requires_human_approval": supervision_response.human_oversight_required,
                "oversight_token": supervision_response.human_oversight_token,
            }

        # Execute research based on type
        try:
            if research_type == ResearchType.WEB_SEARCH:
                results = await self._web_search(task, **kwargs)
            elif research_type == ResearchType.DOCUMENT_ANALYSIS:
                results = await self._analyze_document(task, **kwargs)
            elif research_type == ResearchType.SOURCE_VALIDATION:
                results = await self._validate_source(task, **kwargs)
            elif research_type == ResearchType.DATA_GATHERING:
                results = await self._gather_data(task, **kwargs)
            else:
                results = await self._general_research(task, **kwargs)

            return {
                "success": True,
                "results": results,
                "research_type": research_type.value,
                "risk_level": risk_level.value,
                "supervised": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "research_type": research_type.value,
            }

    def _assess_risk(
        self,
        task: str,
        research_type: ResearchType,
        include_personal_data: bool
    ) -> RiskLevel:
        """Assess risk level for research task"""
        # HIGH risk if personal data involved
        if include_personal_data:
            return RiskLevel.HIGH

        # Check for forbidden topics
        task_lower = task.lower()
        for forbidden in self.forbidden_topics:
            if forbidden.replace("_", " ") in task_lower:
                return RiskLevel.HIGH

        # Document analysis is LOW risk (read-only)
        if research_type == ResearchType.DOCUMENT_ANALYSIS:
            return RiskLevel.LOW

        # Web search and data gathering are MEDIUM risk
        if research_type in [ResearchType.WEB_SEARCH, ResearchType.DATA_GATHERING]:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    async def _web_search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Perform web search (placeholder - integrate with actual search API)

        TODO: Integrate with DuckDuckGo, Brave Search, or similar privacy-focused API
        """
        max_results = kwargs.get("max_results", 10)

        # Placeholder implementation
        return {
            "query": query,
            "results": [
                {
                    "title": f"Result {i+1} for: {query}",
                    "url": f"https://example.com/result-{i+1}",
                    "snippet": f"Snippet for result {i+1}...",
                    "source": "web_search",
                }
                for i in range(min(max_results, 5))
            ],
            "total_results": min(max_results, 5),
            "search_engine": "placeholder",
        }

    async def _analyze_document(self, document: str, **kwargs) -> Dict[str, Any]:
        """
        Analyze document and extract key information

        LOW risk operation (read-only analysis)
        """
        analysis_type = kwargs.get("analysis_type", "summary")

        # Placeholder LLM call
        prompt = f"""Analyze this document and provide a {analysis_type}:

Document:
{document[:1000]}... (truncated)

Provide:
1. Main topics
2. Key findings
3. Credibility assessment
4. Sources cited
"""

        # TODO: Replace with actual LLM call
        return {
            "analysis_type": analysis_type,
            "main_topics": ["Topic 1", "Topic 2", "Topic 3"],
            "key_findings": [
                "Finding 1: ...",
                "Finding 2: ...",
            ],
            "credibility_score": 0.75,
            "sources_cited": 5,
            "personal_data_detected": False,
        }

    async def _validate_source(self, source_url: str, **kwargs) -> Dict[str, Any]:
        """
        Validate credibility and reliability of information source

        MEDIUM risk (requires checking domain reputation)
        """
        # Placeholder implementation
        return {
            "url": source_url,
            "credibility_score": 0.8,
            "factors": {
                "domain_age": "5 years",
                "ssl_certificate": True,
                "known_reliable": True,
                "bias_rating": "center",
                "fact_check_rating": "high",
            },
            "warnings": [],
            "recommendation": "Reliable source - proceed with caution"
        }

    async def _gather_data(self, data_spec: str, **kwargs) -> Dict[str, Any]:
        """
        Gather data from public sources

        MEDIUM risk (data collection requires validation)
        HIGH risk if personal data involved
        """
        sources = kwargs.get("sources", [])

        # Placeholder implementation
        return {
            "data_spec": data_spec,
            "sources_checked": len(sources),
            "data_points_collected": 0,  # Placeholder
            "personal_data_detected": False,
            "dsgvo_compliant": True,
        }

    async def _general_research(self, task: str, **kwargs) -> Dict[str, Any]:
        """General research using LLM"""
        # Placeholder LLM call
        return {
            "task": task,
            "research_summary": "Placeholder research summary...",
            "sources": [],
            "confidence_score": 0.7,
        }


# ============================================================================
# Singleton
# ============================================================================

_research_agent: Optional[ResearchAgent] = None


def get_research_agent() -> ResearchAgent:
    """Get or create ResearchAgent singleton"""
    global _research_agent
    if _research_agent is None:
        _research_agent = ResearchAgent()
    return _research_agent
