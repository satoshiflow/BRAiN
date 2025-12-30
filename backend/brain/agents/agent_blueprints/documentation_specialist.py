"""
Agent Blueprint: Documentation Specialist

Constitutional AI agent for comprehensive documentation generation.
"""

BLUEPRINT = {
    "id": "documentation_specialist",
    "name": "Documentation Specialist",
    "description": "Specialized agent for creating API docs, READMEs, user guides, and architecture documentation",
    "agent_class": "DocumentationAgent",
    "capabilities": [
        "api_documentation",
        "readme_generation",
        "code_comments",
        "user_guides",
        "architecture_docs",
        "changelog_generation"
    ],
    "tools": [
        "generate_api_docs",
        "generate_readme",
        "generate_comments",
        "generate_user_guide"
    ],
    "risk_levels": {
        "documentation_generation": "low",
        "auto_commit": "medium"
    },
    "supervision": {
        "automatic_approval": ["low", "medium"],
        "human_oversight_required": []
    },
    "quality_standards": {
        "max_line_length": 80,
        "include_examples": True,
        "include_toc": True,
        "use_consistent_style": True,
        "accessibility_compliant": True
    },
    "output_formats": [
        "markdown",
        "rst",
        "html",
        "docstring"
    ],
    "compliance": {
        "read_only_operation": "Documentation generation is non-destructive",
        "auto_commit_supervision": "Auto-commit requires supervisor approval (MEDIUM risk)"
    },
    "default_config": {
        "output_format": "markdown",
        "include_examples": True,
        "include_links": True,
        "auto_commit": False,
        "commit_message_template": "docs: Update {doc_type} documentation"
    }
}
