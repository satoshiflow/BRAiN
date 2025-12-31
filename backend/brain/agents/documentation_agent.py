"""
Documentation Agent - Constitutional AI Agent for Documentation Generation

Specializes in creating comprehensive, accurate documentation
with minimal risk and high value for knowledge sharing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from backend.brain.agents.base_agent import BaseAgent
from backend.brain.agents.supervisor_agent import get_supervisor_agent, SupervisionRequest, RiskLevel


class DocumentationType(str, Enum):
    """Types of documentation"""
    API_DOCS = "api_docs"
    README = "readme"
    CODE_COMMENTS = "code_comments"
    USER_GUIDE = "user_guide"
    ARCHITECTURE = "architecture"
    CHANGELOG = "changelog"


class DocumentationFormat(str, Enum):
    """Documentation output formats"""
    MARKDOWN = "markdown"
    RESTRUCTURED_TEXT = "rst"
    HTML = "html"
    DOCSTRING = "docstring"


class DocumentationAgent(BaseAgent):
    """
    Constitutional Documentation Agent

    **Purpose:** Create comprehensive and accurate documentation

    **Capabilities:**
    - API documentation generation (OpenAPI, docstrings)
    - README.md creation
    - Code comment generation
    - User guides and tutorials
    - Architecture documentation
    - Changelog generation

    **Risk Management:**
    - LOW risk: Documentation is read-only and non-destructive
    - MEDIUM risk: Auto-commit documentation changes

    **Supervision:**
    - Automatic approval: Documentation generation (LOW risk)
    - Human oversight: Auto-commit to repository (MEDIUM risk)

    **Quality Standards:**
    - Accurate and up-to-date information
    - Clear and concise language
    - Examples and code snippets
    - Cross-references and links
    - Accessibility considerations
    """

    def __init__(self):
        super().__init__()
        self.agent_id = "documentation_agent"
        self.name = "DocumentationAgent"
        self.supervisor = get_supervisor_agent()

        # Documentation best practices
        self.documentation_standards = {
            "max_line_length": 80,
            "include_examples": True,
            "include_toc": True,
            "use_consistent_style": True,
        }

        # Register tools
        self.register_tool("generate_api_docs", self._generate_api_docs)
        self.register_tool("generate_readme", self._generate_readme)
        self.register_tool("generate_comments", self._generate_comments)
        self.register_tool("generate_user_guide", self._generate_user_guide)

    async def run(self, task: str, **kwargs) -> Dict[str, Any]:
        """
        Execute documentation task with constitutional supervision.

        Args:
            task: Documentation task description
            **kwargs:
                doc_type: DocumentationType
                output_format: DocumentationFormat
                code_path: Path to code to document
                auto_commit: Boolean (triggers MEDIUM risk)

        Returns:
            Dictionary with generated documentation
        """
        doc_type = kwargs.get("doc_type", DocumentationType.README)
        output_format = kwargs.get("output_format", DocumentationFormat.MARKDOWN)
        auto_commit = kwargs.get("auto_commit", False)

        # Determine risk level
        risk_level = self._assess_risk(doc_type, auto_commit)

        # Request supervision
        supervision_request = SupervisionRequest(
            requesting_agent=self.agent_id,
            action="generate_documentation",
            context={
                "task": task,
                "doc_type": doc_type.value,
                "output_format": output_format.value,
                "auto_commit": auto_commit,
                "risk_level": risk_level.value,
            },
            risk_level=risk_level,
            reason=f"Documentation generation: {doc_type.value}"
        )

        supervision_response = await self.supervisor.supervise_action(supervision_request)

        if not supervision_response.approved:
            return {
                "success": False,
                "error": "Documentation generation denied by supervisor",
                "reason": supervision_response.reason,
                "requires_human_approval": supervision_response.human_oversight_required,
                "oversight_token": supervision_response.human_oversight_token,
            }

        # Generate documentation
        try:
            documentation = await self._generate_documentation(
                task, doc_type, output_format, **kwargs
            )

            result = {
                "success": True,
                "documentation": documentation,
                "doc_type": doc_type.value,
                "output_format": output_format.value,
                "risk_level": risk_level.value,
                "supervised": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Auto-commit if requested and approved
            if auto_commit and supervision_response.approved:
                commit_result = await self._commit_documentation(documentation)
                result["auto_committed"] = True
                result["commit_hash"] = commit_result.get("commit_hash")

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "doc_type": doc_type.value,
            }

    def _assess_risk(self, doc_type: DocumentationType, auto_commit: bool) -> RiskLevel:
        """Assess risk level for documentation task"""
        # MEDIUM risk if auto-commit to repository
        if auto_commit:
            return RiskLevel.MEDIUM

        # LOW risk for all documentation generation
        return RiskLevel.LOW

    async def _generate_documentation(
        self,
        task: str,
        doc_type: DocumentationType,
        output_format: DocumentationFormat,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate documentation based on type"""
        code_path = kwargs.get("code_path", "")

        if doc_type == DocumentationType.API_DOCS:
            return await self._generate_api_docs(code_path, output_format)
        elif doc_type == DocumentationType.README:
            return await self._generate_readme(code_path, output_format)
        elif doc_type == DocumentationType.CODE_COMMENTS:
            return await self._generate_comments(code_path)
        elif doc_type == DocumentationType.USER_GUIDE:
            return await self._generate_user_guide(task, output_format)
        elif doc_type == DocumentationType.ARCHITECTURE:
            return await self._generate_architecture_docs(code_path, output_format)
        else:
            return await self._generate_generic_docs(task, output_format)

    async def _generate_api_docs(
        self,
        code_path: str,
        output_format: DocumentationFormat
    ) -> Dict[str, Any]:
        """
        Generate API documentation from code.

        LOW risk operation (read-only code analysis)
        """
        # Placeholder LLM call for API docs generation
        prompt = f"""Generate comprehensive API documentation for:

Code path: {code_path}

Include:
1. Endpoint descriptions
2. Request/response schemas
3. Authentication requirements
4. Example requests/responses
5. Error codes and handling

Format: {output_format.value}
"""

        # Placeholder API documentation
        api_docs = """# API Documentation

## Endpoints

### GET /api/resource
Get list of resources.

**Authentication:** Bearer token required

**Request:**
```bash
curl -H "Authorization: Bearer TOKEN" http://api.example.com/api/resource
```

**Response:**
```json
{
  "resources": [
    {"id": 1, "name": "Resource 1"},
    {"id": 2, "name": "Resource 2"}
  ],
  "total": 2
}
```

**Error Codes:**
- 401: Unauthorized
- 404: Resource not found
- 500: Internal server error
"""

        return {
            "content": api_docs,
            "format": output_format.value,
            "endpoints_documented": 1,
            "examples_included": 1,
            "word_count": len(api_docs.split()),
        }

    async def _generate_readme(
        self,
        code_path: str,
        output_format: DocumentationFormat
    ) -> Dict[str, Any]:
        """
        Generate README.md for project.

        LOW risk operation
        """
        # Placeholder README generation
        readme_content = """# Project Name

## Overview
Brief description of the project and its purpose.

## Features
- Feature 1: Description
- Feature 2: Description
- Feature 3: Description

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from project import main

main()
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

## Testing

```bash
pytest tests/
```

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

- Email: contact@example.com
- Issues: https://github.com/user/repo/issues
"""

        return {
            "content": readme_content,
            "format": output_format.value,
            "sections": ["overview", "features", "installation", "usage", "testing"],
            "word_count": len(readme_content.split()),
        }

    async def _generate_comments(self, code_path: str) -> Dict[str, Any]:
        """
        Generate code comments and docstrings.

        LOW risk operation (read-only code analysis)
        """
        # Placeholder comment generation
        commented_code = '''"""
Module for data processing.

This module provides utilities for processing and transforming data.

Example:
    >>> from module import process_data
    >>> result = process_data(input_data)
    >>> print(result)
"""

def process_data(data: dict) -> dict:
    """
    Process input data and return transformed result.

    Args:
        data (dict): Input data to process

    Returns:
        dict: Processed data

    Raises:
        ValueError: If data is invalid

    Example:
        >>> process_data({"key": "value"})
        {"key": "PROCESSED_VALUE"}
    """
    if not data:
        raise ValueError("Data cannot be empty")

    # Process data
    result = {k: v.upper() for k, v in data.items()}
    return result
'''

        return {
            "content": commented_code,
            "functions_documented": 1,
            "docstring_style": "Google",
            "includes_examples": True,
        }

    async def _generate_user_guide(
        self,
        task: str,
        output_format: DocumentationFormat
    ) -> Dict[str, Any]:
        """
        Generate user guide or tutorial.

        LOW risk operation
        """
        user_guide = """# User Guide

## Getting Started

This guide will help you get started with the application.

### Prerequisites

Before you begin, ensure you have:
- Python 3.11+
- pip installed
- Virtual environment set up

### Step 1: Installation

Install the application:

```bash
pip install application
```

### Step 2: Configuration

Create a configuration file:

```yaml
# config.yml
database:
  host: localhost
  port: 5432
  name: mydb

logging:
  level: INFO
  file: app.log
```

### Step 3: Running the Application

Start the application:

```bash
python app.py
```

## Common Tasks

### Task 1: Create a Resource

```python
from app import create_resource

resource = create_resource(name="My Resource")
print(resource.id)
```

### Task 2: Update a Resource

```python
from app import update_resource

update_resource(resource_id=1, name="Updated Name")
```

## Troubleshooting

### Issue: Connection timeout

**Solution:** Check your network connection and firewall settings.

### Issue: Permission denied

**Solution:** Ensure you have the correct permissions set.

## FAQ

**Q: How do I reset my password?**
A: Use the `reset-password` command.

**Q: Where are logs stored?**
A: Logs are stored in the `logs/` directory.
"""

        return {
            "content": user_guide,
            "format": output_format.value,
            "chapters": 4,
            "examples": 2,
            "word_count": len(user_guide.split()),
        }

    async def _generate_architecture_docs(
        self,
        code_path: str,
        output_format: DocumentationFormat
    ) -> Dict[str, Any]:
        """Generate architecture documentation"""
        arch_docs = """# Architecture Documentation

## System Overview

The system follows a modular, microservices-based architecture.

## Components

### Backend Services
- API Gateway
- Authentication Service
- Data Processing Service
- Storage Service

### Frontend
- React-based SPA
- State management with Redux
- Real-time updates via WebSocket

## Data Flow

1. Client sends request to API Gateway
2. Gateway authenticates request
3. Request routed to appropriate service
4. Service processes request
5. Response returned to client

## Technology Stack

- **Backend:** Python, FastAPI
- **Database:** PostgreSQL, Redis
- **Frontend:** React, TypeScript
- **Infrastructure:** Docker, Kubernetes

## Security

- JWT authentication
- RBAC for authorization
- TLS encryption
- Rate limiting

## Scalability

- Horizontal scaling via Kubernetes
- Load balancing
- Caching strategy
- Database replication
"""

        return {
            "content": arch_docs,
            "format": output_format.value,
            "diagrams_needed": 2,
            "word_count": len(arch_docs.split()),
        }

    async def _generate_generic_docs(
        self,
        task: str,
        output_format: DocumentationFormat
    ) -> Dict[str, Any]:
        """Generate generic documentation based on task"""
        return {
            "content": f"# Documentation\n\n{task}\n\nGenerated documentation content...",
            "format": output_format.value,
            "word_count": 10,
        }

    async def _commit_documentation(self, documentation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Commit documentation to repository.

        MEDIUM risk operation - requires supervision approval
        """
        # Placeholder git commit
        return {
            "committed": True,
            "commit_hash": "abc123def456",
            "files_changed": 1,
            "timestamp": datetime.utcnow().isoformat(),
        }


# ============================================================================
# Singleton
# ============================================================================

_documentation_agent: Optional[DocumentationAgent] = None


def get_documentation_agent() -> DocumentationAgent:
    """Get or create DocumentationAgent singleton"""
    global _documentation_agent
    if _documentation_agent is None:
        _documentation_agent = DocumentationAgent()
    return _documentation_agent
