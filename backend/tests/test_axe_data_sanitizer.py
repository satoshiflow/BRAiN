from __future__ import annotations

from app.modules.axe_fusion.data_sanitizer import DataSanitizer
from app.modules.axe_fusion.provider_selector import SanitizationLevel


def test_request_sanitization_and_response_restore() -> None:
    sanitizer = DataSanitizer()
    messages = [
        {
            "role": "user",
            "content": "Check /home/user/securitydata/pfad/abc.py with api-665752525625265296252526 and mail me at user@example.com",
        }
    ]

    sanitized_messages, mapping = sanitizer.sanitize_messages(messages, SanitizationLevel.STRICT)
    sanitized_content = sanitized_messages[0]["content"]

    assert "[PATH_1]" in sanitized_content
    assert "[SECRET_1]" in sanitized_content
    assert "[EMAIL_1]" in sanitized_content

    model_response = "Use [PATH_1] and token [SECRET_1]."
    restored = sanitizer.deanonymize_text(model_response, mapping)

    assert "/home/user/securitydata/pfad/abc.py" in restored
    assert "api-665752525625265296252526" in restored


def test_moderate_sanitization_keeps_paths() -> None:
    sanitizer = DataSanitizer()
    messages = [{"role": "user", "content": "Path /home/user/a.txt and email test@example.com"}]

    sanitized_messages, _ = sanitizer.sanitize_messages(messages, SanitizationLevel.MODERATE)
    sanitized_content = sanitized_messages[0]["content"]

    assert "/home/user/a.txt" in sanitized_content
    assert "[EMAIL_1]" in sanitized_content
