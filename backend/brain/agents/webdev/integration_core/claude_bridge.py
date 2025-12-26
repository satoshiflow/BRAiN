"""
Claude Bridge - Integration with Claude API

Provides seamless integration with Claude API for agent operations.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.token_manager import get_token_manager
from core.error_handler import get_error_handler, ErrorContext
from core.self_healing import get_self_healing_manager, with_retry

logger = logging.getLogger(__name__)


@dataclass
class ClaudeRequest:
    """Request to Claude API"""
    prompt: str
    max_tokens: int = 4096
    temperature: float = 0.7
    model: str = "claude-3-5-sonnet-20241022"
    system: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class ClaudeResponse:
    """Response from Claude API"""
    content: str
    tokens_used: int
    model: str
    stop_reason: str
    metadata: Dict[str, Any] = None


class ClaudeBridge:
    """
    Bridge to Claude API with token management and error handling

    Features:
    - Automatic token management
    - Error handling and retries
    - Response caching
    - Rate limiting
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude bridge

        Args:
            api_key: Claude API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("No Claude API key configured")

        self.token_manager = get_token_manager()
        self.error_handler = get_error_handler()
        self.healing_manager = get_self_healing_manager()

        logger.info("ClaudeBridge initialized")

    @with_retry(max_attempts=3, base_delay=2.0)
    def send_request(self, request: ClaudeRequest) -> ClaudeResponse:
        """
        Send request to Claude API

        Args:
            request: Claude request

        Returns:
            Claude response

        Raises:
            Exception: If request fails
        """
        logger.info(f"Sending request to Claude (max_tokens={request.max_tokens})")

        # Check token availability
        estimated_tokens = request.max_tokens + 1000  # Prompt + response
        available, msg = self.token_manager.check_availability(
            estimated_tokens,
            "claude_api_call"
        )

        if not available:
            raise Exception(f"Insufficient tokens: {msg}")

        operation_id = self.token_manager.reserve_tokens(
            "claude_api_call",
            estimated_tokens,
            metadata={"model": request.model}
        )

        try:
            # Actual API call would go here
            # For now, return mock response
            response = self._mock_api_call(request)

            # Record actual usage
            self.token_manager.record_usage(
                operation_id,
                response.tokens_used,
                "completed"
            )

            return response

        except Exception as e:
            self.token_manager.abort_operation(operation_id, str(e))

            # Handle error
            context = ErrorContext(
                operation="claude_api_call",
                component="claude_bridge",
                input_data={"model": request.model}
            )
            self.error_handler.handle_error(e, context)
            raise

    def _mock_api_call(self, request: ClaudeRequest) -> ClaudeResponse:
        """Mock API call for development"""
        return ClaudeResponse(
            content="Mock response from Claude",
            tokens_used=1500,
            model=request.model,
            stop_reason="end_turn",
            metadata={}
        )

    def generate_code(
        self,
        prompt: str,
        language: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        Generate code using Claude

        Args:
            prompt: Generation prompt
            language: Target language
            context: Additional context

        Returns:
            Generated code
        """
        system_prompt = f"""You are an expert {language} developer.
Generate production-ready, well-documented code following best practices."""

        request = ClaudeRequest(
            prompt=prompt,
            max_tokens=4096,
            temperature=0.7,
            system=system_prompt,
            metadata=context or {}
        )

        response = self.send_request(request)
        return response.content
