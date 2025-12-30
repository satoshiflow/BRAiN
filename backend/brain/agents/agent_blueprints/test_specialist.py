"""
Agent Blueprint: Test Specialist

Constitutional AI agent for automated testing and quality assurance.
"""

BLUEPRINT = {
    "id": "test_specialist",
    "name": "Test Specialist",
    "description": "Specialized agent for test generation, execution, and coverage analysis with production safety guarantees",
    "agent_class": "TestAgent",
    "capabilities": [
        "unit_test_generation",
        "integration_test_generation",
        "test_execution",
        "coverage_analysis",
        "bug_detection"
    ],
    "tools": [
        "generate_tests",
        "run_tests",
        "analyze_coverage",
        "detect_bugs"
    ],
    "risk_levels": {
        "test_generation": "low",
        "test_execution_local": "low",
        "test_execution_dev": "medium",
        "test_execution_staging": "medium",
        "test_execution_production": "critical"
    },
    "supervision": {
        "automatic_approval": ["low", "medium"],
        "human_oversight_required": ["high", "critical"]
    },
    "safety_guarantees": {
        "no_destructive_operations": True,
        "rollback_capability": True,
        "sandbox_isolation": True,
        "forbidden_patterns": [
            "rm -rf",
            "DROP DATABASE",
            "DELETE FROM",
            "TRUNCATE",
            "os.system(",
            "subprocess.call("
        ]
    },
    "compliance": {
        "production_safety": "Human approval required for production testing",
        "code_validation": "All generated tests validated for safety patterns"
    },
    "default_config": {
        "test_framework": "pytest",
        "coverage_threshold": 0.80,
        "max_execution_time": 300,  # seconds
        "enable_parallel_execution": False
    }
}
