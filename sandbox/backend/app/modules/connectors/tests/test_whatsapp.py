"""
Tests for WhatsApp Connector - Phase 5

Covers:
- WhatsApp schemas (config, webhook payloads, sessions, templates, media)
- SignatureValidator (HMAC-SHA1)
- WhatsAppSessionManager
- DeliveryTracker
- WhatsAppMessageHandler (text, media, location, rate limiting, access control)
- WhatsAppConnector (lifecycle, health, handler-only mode)
- Webhook XML escaping
"""

from __future__ import annotations

import hashlib
import hmac
import time
from base64 import b64encode
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest

from app.modules.connectors.schemas import (
    BrainResponse,
    ConnectorStatus,
    OutgoingMessage,
)
from app.modules.connectors.whatsapp.schemas import (
    MediaMessage,
    MediaType,
    MessageStatus,
    TemplateMessage,
    TemplateParameter,
    TwilioStatusPayload,
    TwilioWebhookPayload,
    WhatsAppConfig,
    WhatsAppSession,
)
from app.modules.connectors.whatsapp.handlers import (
    DeliveryTracker,
    SignatureValidator,
    WhatsAppMessageHandler,
    WhatsAppSessionManager,
)
from app.modules.connectors.whatsapp.connector import WhatsAppConnector
from app.modules.connectors.whatsapp.webhook import _escape_xml


# ============================================================================
# Helpers
# ============================================================================


def make_handler(
    allowed_numbers: list = None,
    admin_numbers: list = None,
) -> WhatsAppMessageHandler:
    config = WhatsAppConfig(
        account_sid="AC_test",
        auth_token="test_token",
        whatsapp_number="whatsapp:+14155238886",
        allowed_numbers=allowed_numbers or [],
        admin_numbers=admin_numbers or [],
        rate_limit_messages=5,
        rate_limit_window=60.0,
    )
    mock_brain = AsyncMock(
        return_value=BrainResponse(
            success=True, reply="Brain reply", mode="llm-fallback", duration_ms=50.0
        )
    )
    return WhatsAppMessageHandler(
        config=config,
        send_to_brain_fn=mock_brain,
    )


def make_payload(**overrides: Any) -> TwilioWebhookPayload:
    defaults = {
        "MessageSid": "SM_test123",
        "AccountSid": "AC_test",
        "From": "whatsapp:+491234567890",
        "To": "whatsapp:+14155238886",
        "Body": "Hello BRAIN",
        "NumMedia": 0,
        "ProfileName": "Alice",
    }
    defaults.update(overrides)
    return TwilioWebhookPayload(**defaults)


# ============================================================================
# Test Schemas
# ============================================================================


class TestWhatsAppSchemas:
    def test_config_defaults(self) -> None:
        config = WhatsAppConfig()
        assert config.max_message_length == 1600
        assert config.verify_signature is True

    def test_webhook_payload_phone(self) -> None:
        p = make_payload()
        assert p.get_phone_number() == "+491234567890"

    def test_webhook_payload_media_urls(self) -> None:
        p = make_payload(
            NumMedia=2,
            MediaUrl0="http://example.com/img.jpg",
            MediaContentType0="image/jpeg",
            MediaUrl1="http://example.com/doc.pdf",
            MediaContentType1="application/pdf",
        )
        urls = p.get_media_urls()
        assert len(urls) == 2
        assert urls[0]["content_type"] == "image/jpeg"
        assert urls[1]["url"] == "http://example.com/doc.pdf"

    def test_webhook_payload_no_media(self) -> None:
        p = make_payload(NumMedia=0)
        assert p.get_media_urls() == []

    def test_session(self) -> None:
        s = WhatsAppSession(phone_number="+49123")
        assert s.message_count == 0
        assert s.is_rate_limited(5) is False

    def test_session_rate_limited(self) -> None:
        s = WhatsAppSession(
            phone_number="+49123", message_count=10, last_message_at=time.time()
        )
        assert s.is_rate_limited(5) is True

    def test_session_rate_limit_window_expired(self) -> None:
        s = WhatsAppSession(
            phone_number="+49123", message_count=100,
            last_message_at=time.time() - 120,
        )
        assert s.is_rate_limited(5, 60.0) is False

    def test_message_status_enum(self) -> None:
        assert MessageStatus.DELIVERED == "delivered"
        assert MessageStatus.READ == "read"

    def test_template_message(self) -> None:
        t = TemplateMessage(
            template_name="order_confirm",
            language_code="de",
            body_params=[TemplateParameter(text="Order #123")],
        )
        assert t.template_name == "order_confirm"
        assert len(t.body_params) == 1

    def test_media_message(self) -> None:
        m = MediaMessage(
            media_type=MediaType.IMAGE,
            url="http://example.com/img.jpg",
            content_type="image/jpeg",
            caption="Photo",
        )
        assert m.media_type == MediaType.IMAGE

    def test_status_payload(self) -> None:
        p = TwilioStatusPayload(
            MessageSid="SM_test", MessageStatus="delivered"
        )
        assert p.MessageStatus == "delivered"


# ============================================================================
# Test SignatureValidator
# ============================================================================


class TestSignatureValidator:
    def test_valid_signature(self) -> None:
        token = "my_auth_token"
        validator = SignatureValidator(token)
        url = "https://example.com/webhook"
        params = {"Body": "Hello", "From": "whatsapp:+49123"}

        # Compute expected signature
        data = url
        for key in sorted(params.keys()):
            data += key + params[key]
        expected = b64encode(
            hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()
        ).decode()

        assert validator.validate(url, params, expected) is True

    def test_invalid_signature(self) -> None:
        validator = SignatureValidator("my_token")
        assert validator.validate("https://example.com", {}, "wrong_sig") is False

    def test_empty_token(self) -> None:
        validator = SignatureValidator("")
        assert validator.validate("url", {}, "sig") is False

    def test_empty_signature(self) -> None:
        validator = SignatureValidator("token")
        assert validator.validate("url", {}, "") is False


# ============================================================================
# Test SessionManager
# ============================================================================


class TestWhatsAppSessionManager:
    def test_get_or_create(self) -> None:
        sm = WhatsAppSessionManager()
        s = sm.get_or_create("+49123", "Alice")
        assert s.phone_number == "+49123"
        assert s.profile_name == "Alice"
        assert s.session_id.startswith("wa_")
        assert s.message_count == 1

    def test_get_existing(self) -> None:
        sm = WhatsAppSessionManager()
        s1 = sm.get_or_create("+49123")
        s2 = sm.get_or_create("+49123")
        assert s1.session_id == s2.session_id
        assert s2.message_count == 2

    def test_get_not_found(self) -> None:
        sm = WhatsAppSessionManager()
        assert sm.get("+49999") is None

    def test_clear(self) -> None:
        sm = WhatsAppSessionManager()
        sm.get_or_create("+49123")
        assert sm.clear("+49123") is True
        assert sm.get("+49123") is None

    def test_clear_not_found(self) -> None:
        sm = WhatsAppSessionManager()
        assert sm.clear("+49999") is False

    def test_list_sessions(self) -> None:
        sm = WhatsAppSessionManager()
        sm.get_or_create("+49111")
        sm.get_or_create("+49222")
        assert len(sm.list_sessions()) == 2

    def test_active_count(self) -> None:
        sm = WhatsAppSessionManager()
        sm.get_or_create("+49111")
        assert sm.active_count == 1


# ============================================================================
# Test DeliveryTracker
# ============================================================================


class TestDeliveryTracker:
    def test_update_and_get(self) -> None:
        dt = DeliveryTracker()
        dt.update("SM_1", "delivered")
        assert dt.get("SM_1") == MessageStatus.DELIVERED

    def test_get_not_found(self) -> None:
        dt = DeliveryTracker()
        assert dt.get("SM_unknown") is None

    def test_unknown_status(self) -> None:
        dt = DeliveryTracker()
        dt.update("SM_1", "banana")  # Should log warning, not crash
        assert dt.get("SM_1") is None

    def test_get_stats(self) -> None:
        dt = DeliveryTracker()
        dt.update("SM_1", "delivered")
        dt.update("SM_2", "delivered")
        dt.update("SM_3", "failed")
        stats = dt.get_stats()
        assert stats["delivered"] == 2
        assert stats["failed"] == 1


# ============================================================================
# Test WhatsAppMessageHandler
# ============================================================================


class TestWhatsAppHandler:
    @pytest.mark.asyncio
    async def test_text_message(self) -> None:
        h = make_handler()
        reply = await h.handle_webhook(make_payload(Body="Hello"))
        assert reply == "Brain reply"
        assert len(h._history["+491234567890"]) == 2

    @pytest.mark.asyncio
    async def test_unauthorized_number(self) -> None:
        h = make_handler(allowed_numbers=["+49999"])
        reply = await h.handle_webhook(make_payload())
        assert "not authorized" in reply

    @pytest.mark.asyncio
    async def test_rate_limited(self) -> None:
        h = make_handler()
        session = h.sessions.get_or_create("+491234567890")
        session.message_count = 10
        session.last_message_at = time.time()
        reply = await h.handle_webhook(make_payload())
        assert "Rate limit" in reply

    @pytest.mark.asyncio
    async def test_brain_error(self) -> None:
        h = make_handler()
        h.send_to_brain = AsyncMock(
            return_value=BrainResponse(success=False, error="Service down")
        )
        reply = await h.handle_webhook(make_payload())
        assert "Error" in reply

    @pytest.mark.asyncio
    async def test_truncation(self) -> None:
        h = make_handler()
        h.send_to_brain = AsyncMock(
            return_value=BrainResponse(success=True, reply="x" * 2000, mode="llm")
        )
        reply = await h.handle_webhook(make_payload())
        assert len(reply) <= 1600
        assert "[truncated]" in reply

    @pytest.mark.asyncio
    async def test_media_message(self) -> None:
        h = make_handler()
        reply = await h.handle_webhook(make_payload(
            Body="Check this",
            NumMedia=1,
            MediaUrl0="http://example.com/img.jpg",
            MediaContentType0="image/jpeg",
        ))
        assert reply == "Brain reply"

    @pytest.mark.asyncio
    async def test_media_no_caption(self) -> None:
        h = make_handler()
        reply = await h.handle_webhook(make_payload(
            Body="",
            NumMedia=1,
            MediaUrl0="http://example.com/doc.pdf",
            MediaContentType0="application/pdf",
        ))
        assert reply == "Brain reply"

    @pytest.mark.asyncio
    async def test_location_message(self) -> None:
        h = make_handler()
        reply = await h.handle_webhook(make_payload(
            Body="", Latitude="52.52", Longitude="13.405"
        ))
        assert reply == "Brain reply"

    @pytest.mark.asyncio
    async def test_empty_body(self) -> None:
        h = make_handler()
        reply = await h.handle_webhook(make_payload(Body=""))
        assert "could not be processed" in reply

    @pytest.mark.asyncio
    async def test_status_callback(self) -> None:
        h = make_handler()
        payload = TwilioStatusPayload(
            MessageSid="SM_test", MessageStatus="delivered"
        )
        await h.handle_status_callback(payload)
        assert h.delivery.get("SM_test") == MessageStatus.DELIVERED

    @pytest.mark.asyncio
    async def test_status_callback_error(self) -> None:
        h = make_handler()
        payload = TwilioStatusPayload(
            MessageSid="SM_test", MessageStatus="failed",
            ErrorCode="30001", ErrorMessage="Queue overflow",
        )
        await h.handle_status_callback(payload)
        assert h.delivery.get("SM_test") == MessageStatus.FAILED

    def test_access_control_empty_allows_all(self) -> None:
        h = make_handler(allowed_numbers=[])
        assert h.is_number_allowed("+49123") is True

    def test_access_control_restricted(self) -> None:
        h = make_handler(allowed_numbers=["+49111"])
        assert h.is_number_allowed("+49111") is True
        assert h.is_number_allowed("+49999") is False

    def test_is_admin(self) -> None:
        h = make_handler(admin_numbers=["+49111"])
        assert h.is_admin("+49111") is True
        assert h.is_admin("+49999") is False

    def test_get_history(self) -> None:
        h = make_handler()
        h._history["+49123"] = [
            {"role": "user", "content": "Hi"},
            {"role": "brain", "content": "Hello"},
        ]
        assert len(h.get_history("+49123")) == 2

    def test_get_history_empty(self) -> None:
        h = make_handler()
        assert h.get_history("+49999") == []

    def test_clear_history(self) -> None:
        h = make_handler()
        h._history["+49123"] = [{"role": "user", "content": "Hi"}]
        assert h.clear_history("+49123") is True
        assert h.get_history("+49123") == []

    def test_clear_history_not_found(self) -> None:
        h = make_handler()
        assert h.clear_history("+49999") is False


# ============================================================================
# Test WhatsAppConnector
# ============================================================================


class TestWhatsAppConnector:
    @pytest.fixture
    def connector(self) -> WhatsAppConnector:
        return WhatsAppConnector(
            config=WhatsAppConfig(),
            axe_base_url="http://localhost:8000",
        )

    @pytest.mark.asyncio
    async def test_start_handler_only(self, connector: WhatsAppConnector) -> None:
        await connector.start()
        assert connector.status == ConnectorStatus.CONNECTED
        assert connector._twilio_client is None
        await connector.stop()

    @pytest.mark.asyncio
    async def test_stop(self, connector: WhatsAppConnector) -> None:
        await connector.start()
        await connector.stop()
        assert connector.status == ConnectorStatus.STOPPED

    @pytest.mark.asyncio
    async def test_health_check(self, connector: WhatsAppConnector) -> None:
        await connector.start()
        health = await connector.health_check()
        assert health.connector_id == "whatsapp_connector"
        assert health.details["account_sid_set"] is False
        assert health.details["twilio_client"] is False
        await connector.stop()

    @pytest.mark.asyncio
    async def test_send_to_user_handler_only(self, connector: WhatsAppConnector) -> None:
        await connector.start()
        msg = OutgoingMessage(content="Hello")
        result = await connector.send_to_user("+49123", msg)
        assert result is True
        await connector.stop()


# ============================================================================
# Test XML Escaping
# ============================================================================


class TestXMLEscape:
    def test_ampersand(self) -> None:
        assert _escape_xml("A & B") == "A &amp; B"

    def test_angle_brackets(self) -> None:
        assert _escape_xml("<b>bold</b>") == "&lt;b&gt;bold&lt;/b&gt;"

    def test_quotes(self) -> None:
        assert _escape_xml('say "hello"') == "say &quot;hello&quot;"

    def test_apostrophe(self) -> None:
        assert _escape_xml("it's") == "it&apos;s"

    def test_plain_text(self) -> None:
        assert _escape_xml("Hello world") == "Hello world"
