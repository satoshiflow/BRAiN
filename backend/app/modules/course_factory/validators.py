"""
Content Validators - Sprint 13

Validates course content, enhancements, and performs diff-audit.
"""

from typing import List, Tuple, Optional
import difflib
import hashlib
from loguru import logger

from app.modules.course_factory.enhanced_schemas import (
    ContentEnhancement,
    EnhancedCourseMetadata,
)


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class ContentValidator:
    """
    Validates course content and enhancements.

    Rules:
    - No structural changes (headings, lists, etc.)
    - No factual replacements without source markers
    - Length constraints (enhancements should not balloon content)
    - Tone consistency
    """

    MAX_LENGTH_INCREASE_PERCENT = 50  # Max 50% increase in length

    def validate_enhancement(
        self, enhancement: ContentEnhancement
    ) -> Tuple[bool, List[str]]:
        """
        Validate content enhancement.

        Args:
            enhancement: Content enhancement to validate

        Returns:
            Tuple of (passed, errors)
        """
        errors = []

        # 1. Length check
        base_len = len(enhancement.base_content)
        enhanced_len = len(enhancement.enhanced_content)

        max_allowed_len = base_len * (1 + self.MAX_LENGTH_INCREASE_PERCENT / 100)
        if enhanced_len > max_allowed_len:
            errors.append(
                f"Enhanced content too long: {enhanced_len} chars "
                f"(base: {base_len}, max allowed: {int(max_allowed_len)})"
            )

        # 2. Structural changes check
        if self._has_structural_changes(enhancement.base_content, enhancement.enhanced_content):
            errors.append("Structural changes detected (headings, lists, etc.)")
            enhancement.structural_changes = True

        # 3. Empty content check
        if not enhancement.enhanced_content.strip():
            errors.append("Enhanced content is empty")

        # 4. TODO: Add more sophisticated checks (future)
        # - Tone analysis
        # - Fact-checking
        # - Source marker verification

        passed = len(errors) == 0

        # Update enhancement
        enhancement.validated = True
        enhancement.validation_passed = passed
        enhancement.validation_errors = errors

        if passed:
            logger.info(f"Enhancement {enhancement.enhancement_id} passed validation")
        else:
            logger.warning(
                f"Enhancement {enhancement.enhancement_id} failed validation: {errors}"
            )

        return passed, errors

    def _has_structural_changes(self, base: str, enhanced: str) -> bool:
        """
        Check if enhanced content has structural changes.

        Simple heuristic: Count markdown headings, lists, code blocks.
        """
        base_structure = self._extract_structure(base)
        enhanced_structure = self._extract_structure(enhanced)

        # Compare structure counts
        for key in ["headings", "lists", "code_blocks"]:
            if base_structure[key] != enhanced_structure[key]:
                logger.debug(
                    f"Structural change detected in {key}: "
                    f"{base_structure[key]} → {enhanced_structure[key]}"
                )
                return True

        return False

    def _extract_structure(self, content: str) -> dict:
        """Extract structural elements from markdown."""
        lines = content.split("\n")

        structure = {
            "headings": sum(1 for line in lines if line.strip().startswith("#")),
            "lists": sum(1 for line in lines if line.strip().startswith(("-", "*", "1."))),
            "code_blocks": content.count("```") // 2,
        }

        return structure


class DiffAuditor:
    """
    Performs diff-audit between base and enhanced content.

    Generates:
    - Unified diff
    - Diff hash (for audit trail)
    - Change statistics
    """

    def audit_diff(
        self, base_content: str, enhanced_content: str
    ) -> Tuple[str, str, dict]:
        """
        Audit differences between base and enhanced content.

        Args:
            base_content: Original content
            enhanced_content: Enhanced content

        Returns:
            Tuple of (unified_diff, diff_hash, stats)
        """
        # Generate unified diff
        diff = difflib.unified_diff(
            base_content.splitlines(keepends=True),
            enhanced_content.splitlines(keepends=True),
            fromfile="base",
            tofile="enhanced",
            lineterm="",
        )
        unified_diff = "".join(diff)

        # Compute diff hash
        diff_hash = hashlib.sha256(unified_diff.encode()).hexdigest()

        # Compute stats
        stats = {
            "base_length": len(base_content),
            "enhanced_length": len(enhanced_content),
            "length_increase": len(enhanced_content) - len(base_content),
            "length_increase_percent": (
                (len(enhanced_content) - len(base_content)) / len(base_content) * 100
                if len(base_content) > 0
                else 0
            ),
            "diff_hash": diff_hash,
        }

        logger.debug(
            f"Diff audit: {stats['length_increase']} chars added "
            f"({stats['length_increase_percent']:.1f}%)"
        )

        return unified_diff, diff_hash, stats


# Singletons
_content_validator: Optional[ContentValidator] = None
_diff_auditor: Optional[DiffAuditor] = None


def get_content_validator() -> ContentValidator:
    """Get content validator singleton."""
    global _content_validator
    if _content_validator is None:
        _content_validator = ContentValidator()
    return _content_validator


def get_diff_auditor() -> DiffAuditor:
    """Get diff auditor singleton."""
    global _diff_auditor
    if _diff_auditor is None:
        _diff_auditor = DiffAuditor()
    return _diff_auditor
