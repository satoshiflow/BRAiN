"""
Agent Blueprint: Research Specialist

Constitutional AI agent for information research and analysis.
"""

BLUEPRINT = {
    "id": "research_specialist",
    "name": "Research Specialist",
    "description": "Specialized agent for information gathering, source validation, and knowledge synthesis with DSGVO compliance",
    "agent_class": "ResearchAgent",
    "capabilities": [
        "web_search",
        "document_analysis",
        "source_validation",
        "literature_review",
        "data_gathering"
    ],
    "tools": [
        "web_search",
        "analyze_document",
        "validate_source",
        "gather_data"
    ],
    "risk_levels": {
        "web_search": "medium",
        "document_analysis": "low",
        "source_validation": "medium",
        "data_gathering_public": "medium",
        "data_gathering_personal": "high"
    },
    "supervision": {
        "automatic_approval": ["low", "medium"],
        "human_oversight_required": ["high", "critical"]
    },
    "compliance": {
        "dsgvo": {
            "articles": ["Art. 5 (Data Minimization)", "Art. 6 (Legal Basis)"],
            "features": ["Source citation", "Data validation", "Personal data detection"]
        },
        "constitutional_constraints": [
            "No illegal content gathering",
            "No violence or discrimination research",
            "No misinformation spreading",
            "Source credibility validation required"
        ]
    },
    "default_config": {
        "max_search_results": 10,
        "require_source_validation": True,
        "detect_personal_data": True,
        "min_credibility_score": 0.7
    }
}
