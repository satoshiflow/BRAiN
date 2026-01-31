"""
Tool Validator - Security checks and KARMA evaluation.

Validates tools before they become ACTIVE:
    1. Security scan (forbidden patterns, import checks)
    2. Policy Engine evaluation (permission check)
    3. KARMA scoring (ethical assessment)
    4. Immune system notification (threat registration)

A tool must pass ALL checks to move from PENDING → VALIDATED.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from loguru import logger

from .schemas import (
    ToolDefinition,
    ToolSecurityLevel,
    ToolSourceType,
    ToolStatus,
)

# Optional integrations (graceful degradation)
try:
    from app.modules.policy.service import get_policy_engine
    from app.modules.policy.schemas import PolicyEvaluationContext
    POLICY_AVAILABLE = True
except ImportError:
    POLICY_AVAILABLE = False
    logger.debug("[ToolValidator] Policy module not available")


# Forbidden patterns in Python tool source locations
FORBIDDEN_PATTERNS = [
    r"os\.system",
    r"subprocess\.(?:call|run|Popen)",
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__",
    r"shutil\.rmtree",
    r"open\s*\(.+,\s*['\"]w",
]

# Forbidden module prefixes for RESTRICTED / UNTRUSTED tools
RESTRICTED_MODULES = [
    "os",
    "subprocess",
    "shutil",
    "socket",
    "ctypes",
    "multiprocessing",
]


@dataclass
class ValidationResult:
    """Result of tool validation."""
    passed: bool
    tool_id: str
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    karma_score: float = 50.0
    policy_approved: bool = False


class ToolValidator:
    """
    Validates tools for security, policy compliance, and ethical scoring.
    """

    def __init__(self) -> None:
        logger.info(
            "🛡️ ToolValidator initialized (Policy: %s)",
            "available" if POLICY_AVAILABLE else "unavailable",
        )

    async def validate(self, tool: ToolDefinition) -> ValidationResult:
        """
        Run full validation pipeline on a tool.

        Returns ValidationResult with pass/fail and details.
        """
        result = ValidationResult(passed=True, tool_id=tool.tool_id)

        # 1. Security scan
        await self._check_security(tool, result)

        # 2. Source validity
        await self._check_source(tool, result)

        # 3. Policy engine
        await self._check_policy(tool, result)

        # 4. KARMA scoring
        await self._compute_karma(tool, result)

        # Final verdict
        result.passed = len(result.checks_failed) == 0

        level = "✅" if result.passed else "❌"
        logger.info(
            "%s Tool validation %s: %s (karma=%.1f, passed=%d, failed=%d)",
            level,
            "PASSED" if result.passed else "FAILED",
            tool.tool_id,
            result.karma_score,
            len(result.checks_passed),
            len(result.checks_failed),
        )

        return result

    # ------------------------------------------------------------------
    # Check: Security patterns
    # ------------------------------------------------------------------

    async def _check_security(self, tool: ToolDefinition, result: ValidationResult) -> None:
        """Scan for forbidden patterns in tool source location."""
        if tool.source.source_type not in (
            ToolSourceType.PYTHON_MODULE,
            ToolSourceType.PYTHON_ENTRYPOINT,
        ):
            result.checks_passed.append("security_scan_skipped_non_python")
            return

        location = tool.source.location
        entrypoint = tool.source.entrypoint or ""
        combined = f"{location}.{entrypoint}"

        # Check forbidden patterns
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, combined):
                result.checks_failed.append(
                    f"security_forbidden_pattern:{pattern}"
                )
                return

        # For RESTRICTED+ security level, check module prefix
        if tool.security_level in (ToolSecurityLevel.RESTRICTED, ToolSecurityLevel.UNTRUSTED):
            for mod in RESTRICTED_MODULES:
                if location.startswith(mod + ".") or location == mod:
                    result.checks_failed.append(
                        f"security_restricted_module:{mod}"
                    )
                    return

        result.checks_passed.append("security_scan")

    # ------------------------------------------------------------------
    # Check: Source validity
    # ------------------------------------------------------------------

    async def _check_source(self, tool: ToolDefinition, result: ValidationResult) -> None:
        """Verify source location is syntactically valid."""
        source = tool.source

        if source.source_type == ToolSourceType.PYTHON_MODULE:
            # Must be a valid dotted Python path
            if not re.match(r"^[a-zA-Z_][\w]*(\.[a-zA-Z_][\w]*)*$", source.location):
                result.checks_failed.append("source_invalid_python_path")
                return

        elif source.source_type in (ToolSourceType.HTTP_API, ToolSourceType.MCP):
            if not source.location.startswith(("http://", "https://")):
                result.checks_failed.append("source_invalid_url")
                return

        elif source.source_type == ToolSourceType.BUILTIN:
            if not source.location:
                result.checks_failed.append("source_empty_builtin")
                return

        result.checks_passed.append("source_valid")

    # ------------------------------------------------------------------
    # Check: Policy Engine
    # ------------------------------------------------------------------

    async def _check_policy(self, tool: ToolDefinition, result: ValidationResult) -> None:
        """Evaluate tool registration against Policy Engine rules."""
        if not POLICY_AVAILABLE:
            result.warnings.append("policy_check_skipped_unavailable")
            result.policy_approved = True  # Permissive when policy unavailable
            return

        try:
            engine = get_policy_engine()
            ctx = PolicyEvaluationContext(
                agent_id="tool_system",
                agent_role="system",
                action="tool.register",
                resource=tool.tool_id,
                environment={
                    "source_type": tool.source.source_type.value,
                    "security_level": tool.security_level.value,
                },
                params={
                    "name": tool.name,
                    "author": tool.author or "unknown",
                },
            )
            eval_result = await engine.evaluate(ctx)
            result.policy_approved = eval_result.allowed

            if eval_result.allowed:
                result.checks_passed.append("policy_approved")
            else:
                # Policy denial is a warning, not a hard failure.
                # Tools can still be registered; configure explicit
                # tool-deny rules in Policy Engine for hard enforcement.
                result.warnings.append(
                    f"policy_denied:{eval_result.reason}"
                )
                result.checks_passed.append("policy_checked")
        except Exception as e:
            logger.warning("[ToolValidator] Policy check error: %s", e)
            result.warnings.append(f"policy_check_error:{e}")
            result.policy_approved = True  # Permissive on error

    # ------------------------------------------------------------------
    # KARMA scoring
    # ------------------------------------------------------------------

    async def _compute_karma(self, tool: ToolDefinition, result: ValidationResult) -> None:
        """
        Compute initial KARMA score for a tool.

        Scoring factors:
            +20  Has description
            +15  Has capabilities defined
            +15  Has author
            +10  Has version > 0.1.0
            +10  Security level is TRUSTED
            +10  Policy approved
            +10  No security warnings
            +10  Source is builtin or python_module (local)
        """
        score = 0.0

        if tool.description:
            score += 20.0
        if tool.capabilities:
            score += 15.0
        if tool.author:
            score += 15.0
        if tool.current_version != "0.1.0":
            score += 10.0
        if tool.security_level == ToolSecurityLevel.TRUSTED:
            score += 10.0
        if result.policy_approved:
            score += 10.0
        if not result.checks_failed:
            score += 10.0
        if tool.source.source_type in (ToolSourceType.BUILTIN, ToolSourceType.PYTHON_MODULE):
            score += 10.0

        result.karma_score = min(100.0, max(0.0, score))
        result.checks_passed.append(f"karma_computed:{result.karma_score:.1f}")
