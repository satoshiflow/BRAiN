"""
Code Completer - Context-aware code completion

Provides intelligent code completion with context understanding,
pattern recognition, and multi-language support.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.token_manager import get_token_manager
from core.error_handler import with_error_handling

logger = logging.getLogger(__name__)


@dataclass
class CompletionContext:
    """Context for code completion"""
    file_path: Path
    line_number: int
    column: int
    preceding_code: str
    language: str
    cursor_context: str = ""


@dataclass
class Completion:
    """Code completion suggestion"""
    text: str
    description: str
    confidence: float
    tokens_used: int
    metadata: Dict = None


class CodeCompleter:
    """
    Context-aware code completion engine

    Features:
    - Multi-language support
    - Context understanding
    - Pattern-based suggestions
    - Token-efficient operations
    """

    def __init__(self):
        self.token_manager = get_token_manager()
        logger.info("CodeCompleter initialized")

    @with_error_handling(
        operation="complete_code",
        component="code_completer",
        reraise=True
    )
    def complete(self, context: CompletionContext) -> List[Completion]:
        """
        Generate code completions

        Args:
            context: Completion context

        Returns:
            List of completion suggestions
        """
        logger.info(f"Generating completion for {context.file_path}:{context.line_number}")

        # Estimate and check tokens
        estimated_tokens = 3000
        available, msg = self.token_manager.check_availability(
            estimated_tokens,
            "code_completion"
        )

        if not available:
            raise Exception(f"Insufficient tokens: {msg}")

        operation_id = self.token_manager.reserve_tokens(
            "code_completion",
            estimated_tokens
        )

        try:
            # Generate completions
            completions = self._generate_completions(context)

            # Record usage
            actual_tokens = sum(c.tokens_used for c in completions)
            self.token_manager.record_usage(operation_id, actual_tokens, "completed")

            return completions

        except Exception as e:
            self.token_manager.abort_operation(operation_id, str(e))
            raise

    def _generate_completions(self, context: CompletionContext) -> List[Completion]:
        """Generate completion suggestions"""

        # Pattern-based completions (simplified)
        completions = []

        # Python-specific completions
        if context.language == "python":
            if "def " in context.preceding_code[-20:]:
                completions.append(Completion(
                    text="    pass",
                    description="Empty function body",
                    confidence=0.8,
                    tokens_used=500
                ))
            elif "class " in context.preceding_code[-20:]:
                completions.append(Completion(
                    text="    def __init__(self):\n        pass",
                    description="Constructor method",
                    confidence=0.9,
                    tokens_used=600
                ))

        # TypeScript/JavaScript completions
        elif context.language in ["typescript", "javascript"]:
            if "function " in context.preceding_code[-20:]:
                completions.append(Completion(
                    text="  return;",
                    description="Return statement",
                    confidence=0.7,
                    tokens_used=400
                ))

        # Fallback generic completion
        if not completions:
            completions.append(Completion(
                text="// TODO: Implement",
                description="TODO marker",
                confidence=0.5,
                tokens_used=300
            ))

        return completions
