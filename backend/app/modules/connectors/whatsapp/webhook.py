"""
WhatsApp Connector - FastAPI Webhook Routes

Receives Twilio webhook callbacks and routes them to the
WhatsApp connector's message handler.

Routes:
- POST /api/connectors/v2/whatsapp/webhook  - Incoming messages
- POST /api/connectors/v2/whatsapp/status   - Delivery status callbacks
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Form, Header, HTTPException, Request, Response
from loguru import logger

from app.modules.connectors.whatsapp.schemas import (
    TwilioStatusPayload,
    TwilioWebhookPayload,
)

router = APIRouter(prefix="/api/connectors/v2/whatsapp", tags=["whatsapp-webhook"])


def _get_whatsapp_connector():
    """Get the WhatsApp connector from the service registry."""
    from app.modules.connectors.service import get_connector_service
    service = get_connector_service()
    connector = service.get("whatsapp_connector")
    if not connector:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp connector not registered or not running",
        )
    return connector


@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    MessageSid: str = Form(""),
    AccountSid: str = Form(""),
    From: str = Form(""),
    To: str = Form(""),
    Body: str = Form(""),
    NumMedia: int = Form(0),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None),
    MediaUrl1: Optional[str] = Form(None),
    MediaContentType1: Optional[str] = Form(None),
    MediaUrl2: Optional[str] = Form(None),
    MediaContentType2: Optional[str] = Form(None),
    Latitude: Optional[str] = Form(None),
    Longitude: Optional[str] = Form(None),
    ProfileName: Optional[str] = Form(None),
    x_twilio_signature: Optional[str] = Header(None, alias="X-Twilio-Signature"),
) -> Response:
    """
    Receive incoming WhatsApp messages from Twilio.

    Returns TwiML response with reply text.
    """
    connector = _get_whatsapp_connector()

    payload = TwilioWebhookPayload(
        MessageSid=MessageSid,
        AccountSid=AccountSid,
        From=From,
        To=To,
        Body=Body,
        NumMedia=NumMedia,
        MediaUrl0=MediaUrl0,
        MediaContentType0=MediaContentType0,
        MediaUrl1=MediaUrl1,
        MediaContentType1=MediaContentType1,
        MediaUrl2=MediaUrl2,
        MediaContentType2=MediaContentType2,
        Latitude=Latitude,
        Longitude=Longitude,
        ProfileName=ProfileName,
    )

    # Validate Twilio signature if enabled
    if connector.config.verify_signature and x_twilio_signature:
        form_data = await request.form()
        params = {k: str(v) for k, v in form_data.items()}
        url = str(request.url)

        if not connector.handler.signature_validator.validate(
            url, params, x_twilio_signature
        ):
            logger.warning(f"Invalid Twilio signature from {From}")
            raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        reply_text = await connector.handler.handle_webhook(payload)
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        reply_text = "An error occurred processing your message."

    # Return TwiML response
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Message>{_escape_xml(reply_text)}</Message>"
        "</Response>"
    )

    return Response(content=twiml, media_type="application/xml")


@router.post("/status")
async def whatsapp_status(
    MessageSid: str = Form(""),
    MessageStatus: str = Form(""),
    To: str = Form(""),
    From: str = Form(""),
    ErrorCode: Optional[str] = Form(None),
    ErrorMessage: Optional[str] = Form(None),
) -> dict:
    """Receive delivery status callbacks from Twilio."""
    connector = _get_whatsapp_connector()

    payload = TwilioStatusPayload(
        MessageSid=MessageSid,
        MessageStatus=MessageStatus,
        To=To,
        From=From,
        ErrorCode=ErrorCode,
        ErrorMessage=ErrorMessage,
    )

    await connector.handler.handle_status_callback(payload)
    return {"status": "ok"}


def _escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
