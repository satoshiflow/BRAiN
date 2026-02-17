"""
Code Reviewer - Automated code review with quality analysis

Provides comprehensive code review with quality scoring, security analysis,
best practices validation, and improvement suggestions.
"""

from __future__ import annotations

import sys
import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.token_manager import get_token_manager
from core.error_handler import get_error_handler, ErrorContext, with_error_handling
from core.self_healing import with_retry

logger = logging.getLogger(__name__)


class IssueSeverity(str, Enum):
    """Code issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueCategory(str, Enum):
    """Code issue categories"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    COMPLEXITY = "complexity"
    BEST_PRACTICES = "best_practices"
    TYPE_SAFETY = "type_safety"


@dataclass
class CodeIssue:
    """A code quality issue"""
    severity: IssueSeverity
    category: IssueCategory
    message: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class ReviewMetrics:
    """Code quality metrics"""
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    cyclomatic_complexity: float
    maintainability_index: float
    functions: int
    classes: int
    comment_ratio: float


@dataclass
class CodeReview:
    """Complete code review result"""
    file_path: Path
    language: str
    quality_score: float
    issues: List[CodeIssue]
    metrics: ReviewMetrics
    suggestions: List[str]
    tokens_used: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def critical_issues(self) -> List[CodeIssue]:
        """Get critical issues"""
        return [i for i in self.issues if i.severity == IssueSeverity.CRITICAL]

    @property
    def security_issues(self) -> List[CodeIssue]:
        """Get security issues"""
        return [i for i in self.issues if i.category == IssueCategory.SECURITY]


class CodeReviewer:
    """
    Automated code reviewer with multi-language support

    Features:
    - Code quality analysis
    - Security vulnerability detection
    - Best practices validation
    - Complexity analysis
    - Documentation coverage
    - Automatic fix suggestions
    """

    def __init__(self):
        """Initialize code reviewer"""
        self.token_manager = get_token_manager()
        self.error_handler = get_error_handler()

        # Security patterns to detect
        self._security_patterns = {
            'sql_injection': re.compile(r'execute\(["\'].*%s.*["\']|cursor\.execute\(.*\+.*\)'),
            'hardcoded_secrets': re.compile(r'(password|secret|api_key|token)\s*=\s*["\'][^"\']+["\']', re.I),
            'unsafe_eval': re.compile(r'\beval\s*\('),
            'unsafe_exec': re.compile(r'\bexec\s*\('),
            'shell_injection': re.compile(r'os\.system\(|subprocess\.(call|run)\(.*shell=True'),
        }

        logger.info("CodeReviewer initialized")

    @with_error_handling(
        operation="review_code",
        component="code_reviewer",
        reraise=True
    )
    def review(
        self,
        file_path: Path,
        language: Optional[str] = None
    ) -> CodeReview:
        """
        Review code file

        Args:
            file_path: Path to code file
            language: Programming language (auto-detected if None)

        Returns:
            CodeReview with analysis results
        """
        logger.info(f"Reviewing code: {file_path}")

        # Auto-detect language
        if language is None:
            language = self._detect_language(file_path)

        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Estimate tokens
        estimated_tokens = len(code.split()) * 1.5
        available, msg = self.token_manager.check_availability(
            int(estimated_tokens),
            "code_review"
        )

        if not available:
            raise Exception(f"Insufficient tokens: {msg}")

        operation_id = self.token_manager.reserve_tokens(
            "code_review",
            int(estimated_tokens),
            metadata={"file": str(file_path)}
        )

        try:
            # Perform review
            issues = []
            metrics = None

            if language == "python":
                issues, metrics = self._review_python(code, file_path)
            elif language in ["typescript", "javascript"]:
                issues, metrics = self._review_javascript(code, file_path)
            else:
                issues, metrics = self._review_generic(code, file_path)

            # Calculate quality score
            quality_score = self._calculate_quality_score(issues, metrics)

            # Generate suggestions
            suggestions = self._generate_suggestions(issues, metrics)

            # Record usage
            actual_tokens = int(len(code.split()) * 1.3)
            self.token_manager.record_usage(operation_id, actual_tokens, "completed")

            review = CodeReview(
                file_path=file_path,
                language=language,
                quality_score=quality_score,
                issues=issues,
                metrics=metrics,
                suggestions=suggestions,
                tokens_used=actual_tokens
            )

            logger.info(
                f"Review complete: {file_path} - "
                f"Score: {quality_score:.1f}/10, Issues: {len(issues)}"
            )

            return review

        except Exception as e:
            self.token_manager.abort_operation(operation_id, str(e))
            raise

    def _review_python(
        self,
        code: str,
        file_path: Path
    ) -> tuple[List[CodeIssue], ReviewMetrics]:
        """Review Python code"""
        issues = []

        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            issues.append(CodeIssue(
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.BEST_PRACTICES,
                message=f"Syntax error: {e.msg}",
                line_number=e.lineno
            ))
            # Return early if syntax error
            metrics = self._calculate_metrics(code)
            return issues, metrics

        # Security checks
        issues.extend(self._check_security(code))

        # Check type hints
        issues.extend(self._check_python_type_hints(tree))

        # Check documentation
        issues.extend(self._check_python_documentation(tree, code))

        # Check complexity
        issues.extend(self._check_python_complexity(tree))

        # Check best practices
        issues.extend(self._check_python_best_practices(tree, code))

        # Calculate metrics
        metrics = self._calculate_metrics(code)

        return issues, metrics

    def _review_javascript(
        self,
        code: str,
        file_path: Path
    ) -> tuple[List[CodeIssue], ReviewMetrics]:
        """Review JavaScript/TypeScript code"""
        issues = []

        # Security checks
        issues.extend(self._check_security(code))

        # Check for console.log in production
        if 'console.log' in code:
            issues.append(CodeIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.BEST_PRACTICES,
                message="console.log statements should be removed in production",
                suggestion="Use a proper logging library or remove debug statements"
            ))

        # Check for var usage
        if re.search(r'\bvar\s+\w+', code):
            issues.append(CodeIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.BEST_PRACTICES,
                message="Use 'let' or 'const' instead of 'var'",
                suggestion="Replace 'var' with 'let' or 'const'",
                auto_fixable=True
            ))

        # Check for == instead of ===
        if re.search(r'[^=!<>]==[^=]', code):
            issues.append(CodeIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.BEST_PRACTICES,
                message="Use '===' instead of '==' for comparison",
                suggestion="Replace '==' with '===' for strict equality",
                auto_fixable=True
            ))

        # Calculate metrics
        metrics = self._calculate_metrics(code)

        return issues, metrics

    def _review_generic(
        self,
        code: str,
        file_path: Path
    ) -> tuple[List[CodeIssue], ReviewMetrics]:
        """Generic code review for any language"""
        issues = []

        # Security checks
        issues.extend(self._check_security(code))

        # Long lines check
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(CodeIssue(
                    severity=IssueSeverity.INFO,
                    category=IssueCategory.STYLE,
                    message=f"Line exceeds 120 characters ({len(line)} chars)",
                    line_number=i,
                    suggestion="Break long lines for better readability"
                ))

        # Calculate metrics
        metrics = self._calculate_metrics(code)

        return issues, metrics

    def _check_security(self, code: str) -> List[CodeIssue]:
        """Check for security vulnerabilities"""
        issues = []

        for vuln_type, pattern in self._security_patterns.items():
            matches = pattern.finditer(code)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                issues.append(CodeIssue(
                    severity=IssueSeverity.CRITICAL,
                    category=IssueCategory.SECURITY,
                    message=f"Potential {vuln_type.replace('_', ' ')} vulnerability",
                    line_number=line_num,
                    code_snippet=match.group(),
                    suggestion=self._get_security_suggestion(vuln_type)
                ))

        return issues

    def _check_python_type_hints(self, tree: ast.AST) -> List[CodeIssue]:
        """Check for type hints in Python code"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check return type hint
                if node.returns is None and node.name != '__init__':
                    issues.append(CodeIssue(
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.TYPE_SAFETY,
                        message=f"Function '{node.name}' missing return type hint",
                        line_number=node.lineno,
                        suggestion="Add return type hint: def func() -> ReturnType:"
                    ))

                # Check parameter type hints
                for arg in node.args.args:
                    if arg.annotation is None and arg.arg != 'self':
                        issues.append(CodeIssue(
                            severity=IssueSeverity.WARNING,
                            category=IssueCategory.TYPE_SAFETY,
                            message=f"Parameter '{arg.arg}' in '{node.name}' missing type hint",
                            line_number=node.lineno,
                            suggestion=f"Add type hint: {arg.arg}: Type"
                        ))

        return issues

    def _check_python_documentation(
        self,
        tree: ast.AST,
        code: str
    ) -> List[CodeIssue]:
        """Check for documentation in Python code"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(node)
                if docstring is None:
                    severity = IssueSeverity.WARNING
                    if isinstance(node, ast.ClassDef):
                        severity = IssueSeverity.ERROR

                    issues.append(CodeIssue(
                        severity=severity,
                        category=IssueCategory.DOCUMENTATION,
                        message=f"{node.__class__.__name__[:-3]} '{node.name}' missing docstring",
                        line_number=node.lineno,
                        suggestion='Add docstring: """Description here"""'
                    ))

        return issues

    def _check_python_complexity(self, tree: ast.AST) -> List[CodeIssue]:
        """Check code complexity"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_cyclomatic_complexity(node)
                if complexity > 10:
                    issues.append(CodeIssue(
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.COMPLEXITY,
                        message=f"Function '{node.name}' has high complexity ({complexity})",
                        line_number=node.lineno,
                        suggestion="Consider refactoring into smaller functions"
                    ))

        return issues

    def _check_python_best_practices(
        self,
        tree: ast.AST,
        code: str
    ) -> List[CodeIssue]:
        """Check Python best practices"""
        issues = []

        # Check for bare except
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(CodeIssue(
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.BEST_PRACTICES,
                        message="Bare 'except:' clause - catch specific exceptions",
                        line_number=node.lineno,
                        suggestion="Use: except SpecificException:"
                    ))

        # Check for mutable default arguments
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append(CodeIssue(
                            severity=IssueSeverity.ERROR,
                            category=IssueCategory.BEST_PRACTICES,
                            message=f"Function '{node.name}' uses mutable default argument",
                            line_number=node.lineno,
                            suggestion="Use None as default and initialize inside function"
                        ))

        return issues

    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _calculate_metrics(self, code: str) -> ReviewMetrics:
        """Calculate code metrics"""
        lines = code.split('\n')
        total_lines = len(lines)

        code_lines = 0
        comment_lines = 0
        blank_lines = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif stripped.startswith('#') or stripped.startswith('//'):
                comment_lines += 1
            else:
                code_lines += 1

        comment_ratio = comment_lines / total_lines if total_lines > 0 else 0

        # Simplified metrics
        return ReviewMetrics(
            total_lines=total_lines,
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            cyclomatic_complexity=0.0,  # Would need full analysis
            maintainability_index=0.0,  # Would need full analysis
            functions=code.count('def ') + code.count('function '),
            classes=code.count('class '),
            comment_ratio=comment_ratio
        )

    def _calculate_quality_score(
        self,
        issues: List[CodeIssue],
        metrics: ReviewMetrics
    ) -> float:
        """Calculate overall quality score (0-10)"""
        base_score = 10.0

        # Deduct points for issues
        for issue in issues:
            if issue.severity == IssueSeverity.CRITICAL:
                base_score -= 2.0
            elif issue.severity == IssueSeverity.ERROR:
                base_score -= 1.0
            elif issue.severity == IssueSeverity.WARNING:
                base_score -= 0.5
            elif issue.severity == IssueSeverity.INFO:
                base_score -= 0.1

        # Bonus for good comment ratio
        if metrics.comment_ratio > 0.2:
            base_score += 0.5

        return max(0.0, min(10.0, base_score))

    def _generate_suggestions(
        self,
        issues: List[CodeIssue],
        metrics: ReviewMetrics
    ) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []

        # Security suggestions
        security_issues = [i for i in issues if i.category == IssueCategory.SECURITY]
        if security_issues:
            suggestions.append(
                f"🔒 Address {len(security_issues)} security issue(s) immediately"
            )

        # Documentation suggestions
        doc_issues = [i for i in issues if i.category == IssueCategory.DOCUMENTATION]
        if doc_issues:
            suggestions.append(
                f"📝 Add documentation to {len(doc_issues)} component(s)"
            )

        # Complexity suggestions
        complex_issues = [i for i in issues if i.category == IssueCategory.COMPLEXITY]
        if complex_issues:
            suggestions.append(
                f"🔧 Refactor {len(complex_issues)} complex function(s)"
            )

        # Comment ratio
        if metrics.comment_ratio < 0.1:
            suggestions.append("💬 Increase code documentation (current: {:.1%})".format(metrics.comment_ratio))

        return suggestions

    def _get_security_suggestion(self, vuln_type: str) -> str:
        """Get security suggestion for vulnerability type"""
        suggestions = {
            'sql_injection': "Use parameterized queries or ORM",
            'hardcoded_secrets': "Use environment variables or secret management",
            'unsafe_eval': "Avoid eval(), use safer alternatives",
            'unsafe_exec': "Avoid exec(), use safer alternatives",
            'shell_injection': "Avoid shell=True, use list arguments",
        }
        return suggestions.get(vuln_type, "Review and fix security issue")

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension"""
        ext_map = {
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
        }
        return ext_map.get(file_path.suffix.lower(), 'unknown')


def review_code(file_path: Path, language: Optional[str] = None) -> CodeReview:
    """Convenience function to review code"""
    reviewer = CodeReviewer()
    return reviewer.review(file_path, language)
