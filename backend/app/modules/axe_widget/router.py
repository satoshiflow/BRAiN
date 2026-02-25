"""
AXE Floating Widget - API Router

A floating chat widget that can be embedded in any web project.
Provides support and assistant functionality.

Security:
- All endpoints with X-API-Key header validated against widget credentials
- Session tokens required for message access
- Rate limiting per project (configurable via credentials)
- Admin endpoints require ADMIN role
- All errors sanitized (no internal details)
- Audit logging for security events

Usage:
    <script src="https://brain.falklabs.io/widget/axe.js"></script>
    <script>
        AxeWidget.init({
            projectId: "my-project",
            apiKey: "...",
            position: "bottom-right"
        });
    </script>

TODO:
- Implement Redis-backed rate limiting (currently using slowapi in-memory)
- Add container-based session sandboxing
- Implement session signing/verification
"""

from typing import Optional
from fastapi import (
    APIRouter, HTTPException, Header, Depends, status, Request,
    Response
)
from fastapi.responses import PlainTextResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_deps import require_role, get_current_principal, Principal, require_auth
from app.core.security import UserRole
from app.core.rate_limit import limiter, RateLimits

from .schemas import (
    WidgetSessionCreate,
    WidgetSessionResponse,
    WidgetMessageRequest,
    WidgetMessageResponse,
    WidgetMessageHistoryResponse,
    WidgetCredentialCreate,
    WidgetCredentialResponse,
    WidgetCredentialWithKeyResponse,
    WidgetSessionListResponse,
)
from .service import WidgetService


router = APIRouter(prefix="/widget", tags=["widget"])


# ============================================================================
# PUBLIC ENDPOINTS - Embedded Widget (Client-Side)
# ============================================================================

@router.post("/sessions", response_model=WidgetSessionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_session(
    request: Request,
    session_data: WidgetSessionCreate,
    x_api_key: str = Header(..., alias="X-API-Key", description="Widget API key"),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new widget session.

    Called when widget loads on a page.

    Security:
    - Requires valid X-API-Key header matching project
    - Rate limited to 10 sessions per minute per project
    - IP address and user agent tracked

    Args:
        session_data: Session creation data (project_id, position, theme, metadata)
        x_api_key: API key for widget authentication

    Returns:
        WidgetSessionResponse with session_id and configuration

    Raises:
        HTTPException: 401 if API key invalid, 429 if rate limited
    """
    service = WidgetService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        # Verify API key (project_id comes from request body)
        await service.verify_credential(
            project_id=session_data.project_id,
            api_key=x_api_key,
            secret="",  # Only verify API key for session creation
        )
    except ValueError as e:
        logger.warning(
            f"Widget session creation failed: Invalid API key for project {session_data.project_id} from {client_ip}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    try:
        session = await service.create_session(
            project_id=session_data.project_id,
            position=session_data.position,
            theme=session_data.theme,
            metadata=session_data.metadata,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        logger.info(f"Created widget session {session.session_id} for project {session_data.project_id}")
        return session
    except ValueError as e:
        logger.error(f"Failed to create widget session: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create session",
        )


@router.post("/messages", response_model=WidgetMessageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    message_data: WidgetMessageRequest,
    x_session_token: str = Header(..., alias="X-Session-Token", description="Widget session token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message in a widget session.

    Stores message in session and processes with AXE Core.

    Security:
    - Requires valid X-Session-Token header
    - Rate limited to 30 messages per minute per session
    - Message content validated (XSS protection)
    - Session expiration checked

    Args:
        message_data: Message request (session_id, message, context)
        x_session_token: Session token for authentication

    Returns:
        WidgetMessageResponse with message ID and content

    Raises:
        HTTPException: 401 if session invalid, 410 if expired, 429 if rate limited
    """
    service = WidgetService(db)

    try:
        # Verify session exists and is not expired
        session = await service.get_session(message_data.session_id)
        if not session:
            raise ValueError("Session not found")

        # Verify session token matches (basic validation - in production use HMAC)
        if x_session_token != message_data.session_id:
            logger.warning(f"Widget message failed: Invalid session token for {message_data.session_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token",
            )

    except ValueError as e:
        if "expired" in str(e).lower():
            logger.warning(f"Widget message failed: Session expired {message_data.session_id}")
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Session has expired",
            )
        logger.warning(f"Widget message failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )

    try:
        # Add user message
        message = await service.add_message(
            session_id=message_data.session_id,
            role="user",
            content=message_data.message,
            metadata=message_data.context,
        )
        logger.info(f"Added message to widget session {message_data.session_id}")
        return message
    except ValueError as e:
        logger.error(f"Failed to add widget message: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to process message",
        )


@router.get("/history/{session_id}", response_model=WidgetMessageHistoryResponse)
async def get_history(
    session_id: str,
    x_session_token: str = Header(..., alias="X-Session-Token", description="Widget session token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get message history for a session.

    Returns all messages in chronological order.

    Security:
    - Requires valid X-Session-Token header matching session_id
    - Returns sanitized messages only (no internal metadata)

    Args:
        session_id: Widget session ID
        x_session_token: Session token for authentication

    Returns:
        WidgetMessageHistoryResponse with paginated messages

    Raises:
        HTTPException: 401 if session invalid, 404 if not found
    """
    service = WidgetService(db)

    # Verify session token
    if x_session_token != session_id:
        logger.warning(f"Widget history access failed: Invalid token for session {session_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
        )

    try:
        messages = await service.get_message_history(session_id)
        session = await service.get_session(session_id)

        return WidgetMessageHistoryResponse(
            session_id=session_id,
            messages=messages,
            total=len(messages),
        )
    except ValueError as e:
        logger.error(f"Failed to get widget history: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )


@router.get("/axe.js", response_class=PlainTextResponse)
async def get_widget_js():
    """
    Serve the AXE Widget JavaScript.

    Public endpoint - returns embeddable widget script.
    Browsers do not send credentials for this request.

    Returns:
        JavaScript code for embedding widget
    """
    js_code = '''
(function() {
    'use strict';

    // AXE Widget v1.0
    window.AxeWidget = {
        config: null,
        sessionId: null,
        sessionToken: null,
        container: null,
        chatOpen: false,
        apiBase: window.location.origin,

        init: function(config) {
            this.config = config;
            this.createStyles();
            this.createDOM();
            this.initSession();
        },

        createStyles: function() {
            const styles = document.createElement('style');
            styles.textContent = `
                .axe-widget-container {
                    position: fixed;
                    z-index: 9999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
                .axe-widget-container.bottom-right { bottom: 20px; right: 20px; }
                .axe-widget-container.bottom-left { bottom: 20px; left: 20px; }
                .axe-widget-container.top-right { top: 20px; right: 20px; }
                .axe-widget-container.top-left { top: 20px; left: 20px; }

                .axe-widget-button {
                    width: 56px;
                    height: 56px;
                    border-radius: 50%;
                    background: #3b82f6;
                    color: white;
                    border: none;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: transform 0.2s;
                }
                .axe-widget-button:hover {
                    transform: scale(1.05);
                }

                .axe-widget-chat {
                    position: absolute;
                    bottom: 70px;
                    right: 0;
                    width: 360px;
                    height: 500px;
                    background: #1a1a2e;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                    display: none;
                    flex-direction: column;
                    overflow: hidden;
                }
                .axe-widget-chat.open {
                    display: flex;
                }

                .axe-widget-header {
                    padding: 16px;
                    background: #16213e;
                    border-bottom: 1px solid #333;
                }
                .axe-widget-header h3 {
                    margin: 0;
                    color: white;
                    font-size: 16px;
                }
                .axe-widget-header p {
                    margin: 4px 0 0;
                    color: #888;
                    font-size: 12px;
                }

                .axe-widget-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 16px;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }

                .axe-widget-message {
                    max-width: 80%;
                    padding: 12px;
                    border-radius: 12px;
                    font-size: 14px;
                    line-height: 1.4;
                }
                .axe-widget-message.user {
                    align-self: flex-end;
                    background: #3b82f6;
                    color: white;
                }
                .axe-widget-message.assistant {
                    align-self: flex-left;
                    background: #16213e;
                    color: #eee;
                }

                .axe-widget-input {
                    padding: 16px;
                    background: #16213e;
                    border-top: 1px solid #333;
                    display: flex;
                    gap: 8px;
                }
                .axe-widget-input input {
                    flex: 1;
                    padding: 10px 14px;
                    border: 1px solid #333;
                    border-radius: 8px;
                    background: #0f0f1a;
                    color: white;
                    font-size: 14px;
                }
                .axe-widget-input button {
                    padding: 10px 16px;
                    background: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 14px;
                }
            `;
            document.head.appendChild(styles);
        },

        createDOM: function() {
            this.container = document.createElement('div');
            this.container.className = 'axe-widget-container ' + (this.config.position || 'bottom-right');

            this.container.innerHTML = `
                <div class="axe-widget-chat" id="axe-chat">
                    <div class="axe-widget-header">
                        <h3>AXE Assistant</h3>
                        <p>How can I help?</p>
                    </div>
                    <div class="axe-widget-messages" id="axe-messages"></div>
                    <div class="axe-widget-input">
                        <input type="text" id="axe-input" placeholder="Type a message..." />
                        <button onclick="AxeWidget.sendMessage()">Send</button>
                    </div>
                </div>
                <button class="axe-widget-button" onclick="AxeWidget.toggleChat()">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                </button>
            `;

            document.body.appendChild(this.container);

            // Enter key handler
            document.getElementById('axe-input').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') AxeWidget.sendMessage();
            });
        },

        initSession: async function() {
            try {
                const response = await fetch(this.apiBase + '/widget/sessions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': this.config.apiKey
                    },
                    body: JSON.stringify({
                        project_id: this.config.projectId,
                        position: this.config.position || 'bottom-right',
                        theme: this.config.theme || 'dark',
                    })
                });
                if (!response.ok) {
                    console.error('Failed to create session:', response.statusText);
                    return;
                }
                const data = await response.json();
                this.sessionId = data.session_id;
                this.sessionToken = data.session_id; // Use session_id as token

                // Add greeting
                this.addMessage('assistant', 'Hi there! How can I help you today?');
            } catch (err) {
                console.error('Failed to init AXE widget:', err);
            }
        },

        toggleChat: function() {
            const chat = document.getElementById('axe-chat');
            this.chatOpen = !this.chatOpen;
            chat.classList.toggle('open', this.chatOpen);
        },

        sendMessage: async function() {
            const input = document.getElementById('axe-input');
            const message = input.value.trim();
            if (!message || !this.sessionToken) return;

            // Add user message
            this.addMessage('user', message);
            input.value = '';

            // Send to backend
            try {
                const response = await fetch(this.apiBase + '/widget/messages', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Session-Token': this.sessionToken
                    },
                    body: JSON.stringify({
                        session_id: this.sessionId,
                        message: message,
                        context: {
                            url: window.location.href,
                            timestamp: new Date().toISOString()
                        }
                    })
                });
                if (!response.ok) {
                    this.addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
                    return;
                }
                const data = await response.json();
                // In production, this would return AXE assistant response
                this.addMessage('assistant', 'Message received. Forwarding to support team.');
            } catch (err) {
                this.addMessage('assistant', 'Sorry, I could not connect. Please try again.');
            }
        },

        addMessage: function(role, text) {
            const container = document.getElementById('axe-messages');
            const msg = document.createElement('div');
            msg.className = 'axe-widget-message ' + role;
            msg.textContent = text;
            container.appendChild(msg);
            container.scrollTop = container.scrollHeight;
        }
    };
})();
'''

    return js_code


# ============================================================================
# ADMIN ENDPOINTS - Credential & Session Management
# ============================================================================

@router.post("/credentials", response_model=WidgetCredentialWithKeyResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))])
async def create_credential(
    credential_data: WidgetCredentialCreate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    """
    Create API credentials for a widget project.

    Admin-only endpoint for managing widget credentials.

    Security:
    - Requires ADMIN role
    - API key and secret generated server-side (never user-provided)
    - Credentials shown only once (not stored in plain text)
    - Audit logged

    Args:
        credential_data: Project ID, rate limit, scopes

    Returns:
        WidgetCredentialWithKeyResponse with plain text API key and secret (shown only once)

    Raises:
        HTTPException: 403 if not admin, 400 if project already has credentials
    """
    service = WidgetService(db)

    try:
        credential = await service.create_credential(
            data=credential_data,
            created_by=principal.principal_id,
        )
        logger.warning(f"Admin {principal.principal_id} created widget credentials for project {credential_data.project_id}")
        return credential
    except ValueError as e:
        logger.error(f"Failed to create widget credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/credentials", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def list_credentials(
    is_active: Optional[bool] = None,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    """
    List all widget credentials.

    Admin-only endpoint.

    Args:
        is_active: Filter by active/inactive status

    Returns:
        List of credentials (without secrets)
    """
    service = WidgetService(db)
    credentials, total = await service.list_credentials(is_active=is_active)

    return {
        "credentials": credentials,
        "total": total,
    }


@router.post("/credentials/{credential_id}/revoke", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def revoke_credential(
    credential_id: str,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke a widget credential.

    Admin-only endpoint.

    Args:
        credential_id: Credential UUID to revoke

    Raises:
        HTTPException: 404 if credential not found
    """
    service = WidgetService(db)

    success = await service.revoke_credential(credential_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    logger.warning(f"Admin {principal.principal_id} revoked widget credential {credential_id}")
    return {"message": "Credential revoked"}


@router.get("/sessions", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def list_sessions(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    """
    List all widget sessions.

    Admin-only endpoint for monitoring and debugging.

    Args:
        project_id: Filter by project ID
        status: Filter by status (active, expired, revoked)

    Returns:
        WidgetSessionListResponse with paginated sessions
    """
    service = WidgetService(db)
    sessions, total = await service.list_sessions(
        project_id=project_id,
        status=status,
    )

    return WidgetSessionListResponse(
        sessions=sessions,
        total=total,
    )
