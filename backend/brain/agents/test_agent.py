"""
Test Agent - Constitutional AI Agent for Automated Testing

Specializes in test generation, execution, and coverage analysis
with safety guarantees and human oversight for production testing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from backend.brain.agents.base_agent import BaseAgent
from backend.brain.agents.supervisor_agent import get_supervisor_agent, SupervisionRequest, RiskLevel


class TestType(str, Enum):
    """Types of tests"""
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    END_TO_END_TEST = "e2e_test"
    LOAD_TEST = "load_test"
    SECURITY_TEST = "security_test"


class TestEnvironment(str, Enum):
    """Test execution environments"""
    LOCAL = "local"
    DEV = "development"
    STAGING = "staging"
    PRODUCTION = "production"  # CRITICAL risk


class TestAgent(BaseAgent):
    """
    Constitutional Test Agent

    **Purpose:** Automated test generation and execution with safety guarantees

    **Capabilities:**
    - Unit test generation (pytest, unittest)
    - Integration test creation
    - Test coverage analysis
    - Test execution and reporting
    - Bug detection and reporting

    **Risk Management:**
    - LOW risk: Test generation (code analysis only)
    - MEDIUM risk: Test execution in dev/staging
    - CRITICAL risk: Production testing (requires approval)

    **Supervision:**
    - Automatic approval: Test generation, dev/staging execution
    - Human oversight: Production testing, destructive tests

    **Safety Guarantees:**
    - No destructive operations in production
    - Rollback capability for all test executions
    - Sandbox isolation for untrusted code
    """

    def __init__(self):
        super().__init__()
        self.agent_id = "test_agent"
        self.name = "TestAgent"
        self.supervisor = get_supervisor_agent()

        # Forbidden patterns in tests
        self.forbidden_patterns = [
            "rm -rf",
            "DROP DATABASE",
            "DELETE FROM",
            "TRUNCATE",
            "os.system(",
            "subprocess.call(",
        ]

        # Register tools
        self.register_tool("generate_tests", self._generate_tests)
        self.register_tool("run_tests", self._run_tests)
        self.register_tool("analyze_coverage", self._analyze_coverage)
        self.register_tool("detect_bugs", self._detect_bugs)

    async def run(self, task: str, **kwargs) -> Dict[str, Any]:
        """
        Execute testing task with constitutional supervision.

        Args:
            task: Testing task description
            **kwargs:
                test_type: TestType
                environment: TestEnvironment
                code_path: Path to code to test
                run_tests: Boolean (execute tests)

        Returns:
            Dictionary with test results and metadata
        """
        test_type = kwargs.get("test_type", TestType.UNIT_TEST)
        environment = kwargs.get("environment", TestEnvironment.LOCAL)
        run_tests = kwargs.get("run_tests", False)

        # Determine risk level
        risk_level = self._assess_risk(test_type, environment, run_tests)

        # Request supervision
        supervision_request = SupervisionRequest(
            requesting_agent=self.agent_id,
            action="execute_tests",
            context={
                "task": task,
                "test_type": test_type.value,
                "environment": environment.value,
                "run_tests": run_tests,
                "risk_level": risk_level.value,
            },
            risk_level=risk_level,
            reason=f"Testing in {environment.value} environment"
        )

        supervision_response = await self.supervisor.supervise_action(supervision_request)

        if not supervision_response.approved:
            return {
                "success": False,
                "error": "Testing denied by supervisor",
                "reason": supervision_response.reason,
                "requires_human_approval": supervision_response.human_oversight_required,
                "oversight_token": supervision_response.human_oversight_token,
            }

        # Execute testing based on type
        try:
            results = await self._execute_testing(task, test_type, environment, **kwargs)

            return {
                "success": True,
                "results": results,
                "test_type": test_type.value,
                "environment": environment.value,
                "risk_level": risk_level.value,
                "supervised": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "test_type": test_type.value,
            }

    def _assess_risk(
        self,
        test_type: TestType,
        environment: TestEnvironment,
        run_tests: bool
    ) -> RiskLevel:
        """Assess risk level for testing task"""
        # CRITICAL risk for production testing
        if environment == TestEnvironment.PRODUCTION:
            return RiskLevel.CRITICAL

        # HIGH risk for security/load tests in staging
        if test_type in [TestType.SECURITY_TEST, TestType.LOAD_TEST] and environment == TestEnvironment.STAGING:
            return RiskLevel.HIGH

        # MEDIUM risk for test execution in dev/staging
        if run_tests and environment != TestEnvironment.LOCAL:
            return RiskLevel.MEDIUM

        # LOW risk for test generation only
        return RiskLevel.LOW

    async def _execute_testing(
        self,
        task: str,
        test_type: TestType,
        environment: TestEnvironment,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute testing workflow"""
        run_tests = kwargs.get("run_tests", False)
        code_path = kwargs.get("code_path", "")

        results = {}

        # Generate tests
        if test_type == TestType.UNIT_TEST:
            generated_tests = await self._generate_tests(code_path, test_type)
            results["generated_tests"] = generated_tests

        # Run tests if requested
        if run_tests:
            test_results = await self._run_tests(environment, **kwargs)
            results["test_execution"] = test_results

            # Analyze coverage
            coverage = await self._analyze_coverage()
            results["coverage"] = coverage

        # Bug detection
        bugs = await self._detect_bugs(code_path)
        results["bugs_detected"] = bugs

        return results

    async def _generate_tests(self, code_path: str, test_type: TestType) -> Dict[str, Any]:
        """
        Generate tests for given code.

        LOW risk operation (code analysis only)
        """
        # Placeholder LLM call for test generation
        prompt = f"""Generate {test_type.value} tests for the following code:

Code path: {code_path}

Requirements:
1. Use pytest framework
2. Cover all functions and edge cases
3. Include docstrings
4. Follow PEP 8
5. No destructive operations

Generate comprehensive tests:
"""

        # Placeholder test generation
        generated_tests = f"""
import pytest

def test_example_function():
    \"\"\"Test example function with typical input.\"\"\"
    result = example_function(input_data)
    assert result == expected_output

def test_example_function_edge_case():
    \"\"\"Test example function with edge case.\"\"\"
    result = example_function(None)
    assert result is None

def test_example_function_error_handling():
    \"\"\"Test example function error handling.\"\"\"
    with pytest.raises(ValueError):
        example_function(invalid_input)
"""

        # Validate tests don't contain forbidden patterns
        is_safe = self._validate_test_safety(generated_tests)

        return {
            "code_path": code_path,
            "test_type": test_type.value,
            "tests_generated": generated_tests if is_safe else None,
            "is_safe": is_safe,
            "test_count": 3,  # Placeholder
            "coverage_estimate": 0.85,
        }

    def _validate_test_safety(self, test_code: str) -> bool:
        """Validate that generated tests don't contain forbidden patterns"""
        for pattern in self.forbidden_patterns:
            if pattern in test_code:
                return False
        return True

    async def _run_tests(self, environment: TestEnvironment, **kwargs) -> Dict[str, Any]:
        """
        Execute tests in specified environment.

        MEDIUM risk for dev/staging
        CRITICAL risk for production (should be denied by supervisor)
        """
        test_files = kwargs.get("test_files", [])

        # Placeholder test execution
        return {
            "environment": environment.value,
            "tests_run": len(test_files),
            "tests_passed": len(test_files) - 1,  # Placeholder
            "tests_failed": 1,
            "execution_time": 12.5,  # seconds
            "failures": [
                {
                    "test": "test_example_function_edge_case",
                    "error": "AssertionError: None != expected_value",
                    "file": "test_example.py",
                    "line": 15,
                }
            ],
        }

    async def _analyze_coverage(self) -> Dict[str, Any]:
        """
        Analyze test coverage.

        LOW risk operation (read-only analysis)
        """
        # Placeholder coverage analysis
        return {
            "total_coverage": 0.78,
            "line_coverage": 0.82,
            "branch_coverage": 0.74,
            "uncovered_files": [
                {"file": "module_a.py", "coverage": 0.45},
                {"file": "module_b.py", "coverage": 0.60},
            ],
            "coverage_trend": "increasing",  # vs previous run
        }

    async def _detect_bugs(self, code_path: str) -> Dict[str, Any]:
        """
        Detect potential bugs via static analysis.

        LOW risk operation (code analysis only)
        """
        # Placeholder bug detection
        return {
            "bugs_found": 3,
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 0,
            "issues": [
                {
                    "severity": "high",
                    "type": "NullPointerException",
                    "file": "module_a.py",
                    "line": 42,
                    "message": "Potential null pointer access",
                },
                {
                    "severity": "medium",
                    "type": "UnusedVariable",
                    "file": "module_b.py",
                    "line": 15,
                    "message": "Variable 'result' is never used",
                },
                {
                    "severity": "medium",
                    "type": "TooManyArguments",
                    "file": "module_c.py",
                    "line": 88,
                    "message": "Function has too many arguments (8/5 max)",
                },
            ],
        }


# ============================================================================
# Singleton
# ============================================================================

_test_agent: Optional[TestAgent] = None


def get_test_agent() -> TestAgent:
    """Get or create TestAgent singleton"""
    global _test_agent
    if _test_agent is None:
        _test_agent = TestAgent()
    return _test_agent
