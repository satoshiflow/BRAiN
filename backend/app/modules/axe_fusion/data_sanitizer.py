"""Request/response sanitization for cloud LLM providers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from app.modules.telemetry.anonymization import AnonymizationService

from .provider_selector import SanitizationLevel


@dataclass
class SanitizationMapping:
    replacements: Dict[str, str] = field(default_factory=dict)

    def remember(self, placeholder: str, original: str) -> None:
        self.replacements[placeholder] = original


class DataSanitizer:
    """Sanitizes outgoing messages and restores placeholders in responses."""

    _PATH_PATTERN = re.compile(r"(?:[A-Za-z]:\\[^\s\"'`]+|/(?:[\w.-]+/)+[\w.-]+)")
    _API_KEY_PATTERN = re.compile(r"\b(?:api[-_]?key\s*[:=]\s*)?([A-Za-z0-9_-]{24,}|api-[A-Za-z0-9_-]{10,})\b")

    def __init__(self) -> None:
        self._base_patterns = {
            "email": AnonymizationService.PII_PATTERNS["email"],
            "phone": AnonymizationService.PII_PATTERNS["phone"],
            "ip": AnonymizationService.PII_PATTERNS["ip_address"],
            "card": AnonymizationService.PII_PATTERNS["credit_card"],
            "path": self._PATH_PATTERN,
            "secret": self._API_KEY_PATTERN,
        }

    def sanitize_messages(
        self,
        messages: List[Dict[str, Any]],
        level: SanitizationLevel,
    ) -> Tuple[List[Dict[str, Any]], SanitizationMapping]:
        if level == SanitizationLevel.NONE:
            return messages, SanitizationMapping()

        sanitized_messages: List[Dict[str, Any]] = []
        mapping = SanitizationMapping()
        counters = {key: 0 for key in self._base_patterns}

        for message in messages:
            copied = dict(message)
            content = copied.get("content")
            if isinstance(content, str):
                copied["content"] = self._sanitize_text(content, mapping, counters, level)
            sanitized_messages.append(copied)

        return sanitized_messages, mapping

    def deanonymize_text(self, text: str, mapping: SanitizationMapping) -> str:
        if not text or not mapping.replacements:
            return text

        restored = text
        for placeholder in sorted(mapping.replacements, key=len, reverse=True):
            restored = restored.replace(placeholder, mapping.replacements[placeholder])
        return restored

    def _sanitize_text(
        self,
        text: str,
        mapping: SanitizationMapping,
        counters: Dict[str, int],
        level: SanitizationLevel,
    ) -> str:
        sanitized = text

        categories = ["email", "phone", "ip", "card", "path", "secret"]
        if level == SanitizationLevel.MODERATE:
            categories = ["email", "phone", "ip", "secret"]

        for category in categories:
            pattern = self._base_patterns[category]

            def _replace(match: re.Match[str]) -> str:
                original = match.group(0)
                counters[category] += 1
                placeholder = f"[{category.upper()}_{counters[category]}]"
                mapping.remember(placeholder, original)
                return placeholder

            sanitized = pattern.sub(_replace, sanitized)

        return sanitized
