"""Code Specialist Blueprint - Code generation and review."""

from app.modules.genesis.blueprints.schemas import (
    AgentBlueprint,
    BlueprintCapability,
)

CODE_SPECIALIST_BLUEPRINT = AgentBlueprint(
    id="code_specialist_v1",
    name="Code Specialist",
    version="1.0.0",
    description="Code generation, review, and software development agent",
    base_config={
        "role": "CODE_SPECIALIST",
        "model": "phi3",
        "temperature": 0.5,  # Moderate for creative solutions
        "max_tokens": 4096,  # Longer for code
        "system_prompt": """You are a code specialist agent responsible for software development tasks.

Your expertise:
- Write clean, efficient, well-documented code
- Follow best practices and design patterns
- Conduct thorough code reviews
- Debug and fix issues
- Refactor and optimize code

Your approach:
1. Understand requirements fully before coding
2. Write type-safe, tested code
3. Follow project conventions and style guides
4. Document complex logic
5. Consider security and performance
6. Review your own code before submission

You are proficient in Python, TypeScript, and system administration.""",
    },
    trait_profile={
        # Cognitive
        "cognitive.reasoning_depth": 0.8,
        "cognitive.creativity": 0.6,
        "cognitive.pattern_recognition": 0.9,
        # Ethical
        "ethical.safety_priority": 0.8,
        "ethical.compliance_strictness": 0.7,
        # Performance
        "performance.accuracy_target": 0.95,
        "performance.speed_priority": 0.5,
        # Behavioral
        "behavioral.proactiveness": 0.6,
        "behavioral.adaptability": 0.7,
        # Social
        "social.communication_clarity": 0.8,
        # Technical
        "technical.code_generation": 0.95,
        "technical.data_analysis": 0.7,
    },
    capabilities=[
        BlueprintCapability(
            id="code_generation",
            name="Code Generation",
            description="Generate code from specifications",
            required_tools=["create_file", "write_code"],
            required_permissions=["CODE_WRITE"],
        ),
        BlueprintCapability(
            id="code_review",
            name="Code Review",
            description="Review code for quality, security, and best practices",
            required_tools=["review_code"],
            required_permissions=["CODE_REVIEW"],
        ),
        BlueprintCapability(
            id="debugging",
            name="Debugging",
            description="Debug and fix code issues",
            required_tools=["analyze_error", "fix_bug"],
            required_permissions=["CODE_DEBUG"],
        ),
    ],
    tools=["create_file", "write_code", "review_code", "analyze_error", "fix_bug"],
    permissions=["CODE_WRITE", "CODE_REVIEW", "CODE_DEBUG"],
    allow_mutations=True,
    mutation_rate=0.1,
    fitness_criteria={
        "code_quality_score": 0.4,
        "task_completion_rate": 0.3,
        "bug_introduction_rate": 0.2,  # Minimize
        "review_accuracy": 0.1,
    },
    ethics_constraints={
        "no_malicious_code": True,
        "security_scan_required": True,
    },
    required_policy_compliance=["code_security_v1"],
    author="system",
    tags=["code", "development", "software", "engineering"],
)
