"""
AXE Event Anonymization Service

DSGVO-compliant data anonymization for event telemetry.
"""
import hashlib
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from .schemas import AnonymizationLevel, AnonymizationResult, AxeEventCreate


class AnonymizationService:
    """
    Service for anonymizing AXE event data based on privacy settings.

    **Features:**
    - Pseudonymization: Hash user IDs, remove IP addresses
    - Strict anonymization: Remove all PII
    - Configurable per-user or per-app
    - DSGVO Article 4(5) compliant
    """

    # Patterns for detecting PII in event_data
    PII_PATTERNS = {
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'phone': re.compile(r'\b(\+?\d{1,3}[- ]?)?\(?\d{2,4}\)?[- ]?\d{3,4}[- ]?\d{3,4}\b'),
        'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        'credit_card': re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
    }

    def __init__(self, salt: str = "axe-telemetry-salt-2026"):
        """
        Initialize anonymization service.

        Args:
            salt: Salt for hashing (should be configurable via env var in production)
        """
        self.salt = salt

    def anonymize_event(
        self,
        event: AxeEventCreate,
        level: Optional[AnonymizationLevel] = None
    ) -> tuple[AxeEventCreate, AnonymizationResult]:
        """
        Anonymize an event based on the specified level.

        Args:
            event: Original event to anonymize
            level: Override anonymization level (uses event.anonymization_level if None)

        Returns:
            Tuple of (anonymized_event, anonymization_result)
        """
        level = level or event.anonymization_level
        result = AnonymizationResult(
            original_user_id=event.user_id,
            anonymized_user_id=None,
            level=level,
            fields_removed=[],
            fields_hashed=[],
            timestamp=datetime.utcnow()
        )

        # Create a copy to modify
        anonymized_event = event.copy(deep=True)

        if level == AnonymizationLevel.NONE:
            # No anonymization
            result.anonymized_user_id = event.user_id
            return anonymized_event, result

        elif level == AnonymizationLevel.PSEUDONYMIZED:
            # Hash user_id
            if anonymized_event.user_id:
                anonymized_event.user_id = self._hash_value(anonymized_event.user_id)
                result.anonymized_user_id = anonymized_event.user_id
                result.fields_hashed.append("user_id")

            # Remove PII from event_data (but keep message content for training)
            anonymized_event.event_data = self._remove_pii_from_dict(
                anonymized_event.event_data,
                partial=True
            )

        elif level == AnonymizationLevel.STRICT:
            # Remove user_id entirely
            if anonymized_event.user_id:
                result.fields_removed.append("user_id")
            anonymized_event.user_id = None

            # Aggressively remove PII from event_data
            anonymized_event.event_data = self._remove_pii_from_dict(
                anonymized_event.event_data,
                partial=False
            )

            # Remove client_platform details
            if anonymized_event.client_platform:
                result.fields_removed.append("client_platform")
            anonymized_event.client_platform = "unknown"

        return anonymized_event, result

    def _hash_value(self, value: str) -> str:
        """
        Hash a value with salt using SHA256.

        Args:
            value: Value to hash

        Returns:
            Hashed value (hex digest)
        """
        salted = f"{value}{self.salt}"
        return hashlib.sha256(salted.encode()).hexdigest()

    def _remove_pii_from_dict(
        self,
        data: Dict[str, Any],
        partial: bool = True
    ) -> Dict[str, Any]:
        """
        Remove PII from a dictionary.

        Args:
            data: Dictionary to clean
            partial: If True, only remove obvious PII (emails, IPs).
                     If False, remove all potentially identifying data.

        Returns:
            Cleaned dictionary
        """
        if not isinstance(data, dict):
            return data

        cleaned = {}

        for key, value in data.items():
            # Skip keys that definitely contain PII
            if key.lower() in ['password', 'token', 'api_key', 'secret', 'ip', 'ip_address']:
                continue

            if isinstance(value, str):
                # Check for PII patterns
                if self._contains_pii(value):
                    if partial:
                        # Replace PII with placeholders
                        cleaned[key] = self._mask_pii(value)
                    else:
                        # Skip field entirely
                        continue
                else:
                    cleaned[key] = value

            elif isinstance(value, dict):
                # Recursively clean nested dicts
                cleaned[key] = self._remove_pii_from_dict(value, partial)

            elif isinstance(value, list):
                # Clean list items
                cleaned[key] = [
                    self._remove_pii_from_dict(item, partial) if isinstance(item, dict)
                    else item
                    for item in value
                ]

            else:
                # Keep other types as-is
                cleaned[key] = value

        return cleaned

    def _contains_pii(self, text: str) -> bool:
        """
        Check if text contains PII patterns.

        Args:
            text: Text to check

        Returns:
            True if PII detected
        """
        for pattern_name, pattern in self.PII_PATTERNS.items():
            if pattern.search(text):
                return True
        return False

    def _mask_pii(self, text: str) -> str:
        """
        Mask PII in text with placeholders.

        Args:
            text: Text to mask

        Returns:
            Masked text
        """
        masked = text

        # Mask emails
        masked = self.PII_PATTERNS['email'].sub('[EMAIL]', masked)

        # Mask phone numbers
        masked = self.PII_PATTERNS['phone'].sub('[PHONE]', masked)

        # Mask IP addresses
        masked = self.PII_PATTERNS['ip_address'].sub('[IP]', masked)

        # Mask credit cards
        masked = self.PII_PATTERNS['credit_card'].sub('[CARD]', masked)

        return masked

    def anonymize_batch(
        self,
        events: List[AxeEventCreate],
        level: Optional[AnonymizationLevel] = None
    ) -> tuple[List[AxeEventCreate], List[AnonymizationResult]]:
        """
        Anonymize a batch of events.

        Args:
            events: List of events to anonymize
            level: Override anonymization level for all events

        Returns:
            Tuple of (anonymized_events, anonymization_results)
        """
        anonymized_events = []
        results = []

        for event in events:
            anonymized_event, result = self.anonymize_event(event, level)
            anonymized_events.append(anonymized_event)
            results.append(result)

        return anonymized_events, results


# Global instance
_anonymization_service: Optional[AnonymizationService] = None


def get_anonymization_service() -> AnonymizationService:
    """
    Get or create the global anonymization service instance.

    Returns:
        AnonymizationService instance
    """
    global _anonymization_service
    if _anonymization_service is None:
        # TODO: Load salt from environment variable
        _anonymization_service = AnonymizationService()
    return _anonymization_service
