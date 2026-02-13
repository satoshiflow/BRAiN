"""
AXE Floating Widget

A floating chat widget that can be embedded in any web project.
Provides support and assistant functionality.

Usage:
    <script src="https://brain.falklabs.io/widget/axe.js"></script>
    <script>
        AxeWidget.init({
            projectId: "my-project",
            apiKey: "...",
            position: "bottom-right"
        });
    </script>
"""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

router = APIRouter(prefix="/widget", tags=["widget"])


class WidgetConfig(BaseModel):
    """Configuration for AXE Floating Widget"""
    project_id: str
    api_key: str
    position: str = "bottom-right"  # bottom-right | bottom-left | top-right | top-left
    theme: str = "dark"  # dark | light
    primary_color: str = "#3b82f6"  # Blue default
    greeting: Optional[str] = None
    allow_attachments: bool = False


class WidgetMessage(BaseModel):
    """Message from widget to AXE"""
    session_id: str
    message: str
    context: Optional[dict] = None  # page URL, user actions, etc.


class WidgetSession(BaseModel):
    """Widget session info"""
    session_id: str
    project_id: str
    started_at: str
    messages_count: int = 0


# In-memory session storage (use Redis in production)
_widget_sessions = {}


@router.post("/init")
async def init_widget(config: WidgetConfig):
    """
    Initialize a new widget session.
    
    Called when widget loads on a page.
    """
    import uuid
    from datetime import datetime
    
    session_id = str(uuid.uuid4())
    
    _widget_sessions[session_id] = {
        "session_id": session_id,
        "project_id": config.project_id,
        "started_at": datetime.utcnow().isoformat(),
        "messages": [],
        "config": config.dict(),
    }
    
    return {
        "session_id": session_id,
        "widget_config": {
            "position": config.position,
            "theme": config.theme,
            "primary_color": config.primary_color,
            "greeting": config.greeting or "👋 Hi! I'm AXE. How can I help you?",
        }
    }


@router.post("/message")
async def send_message(message: WidgetMessage):
    """
    Send a message from widget to AXE.
    
    Returns AXE response.
    """
    session = _widget_sessions.get(message.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Store message
    session["messages"].append({
        "role": "user",
        "content": message.message,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    # TODO: Forward to AXE Core for processing
    # For MVP, return mock response
    
    response_text = generate_widget_response(message.message, message.context)
    
    session["messages"].append({
        "role": "assistant",
        "content": response_text,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    return {
        "message": response_text,
        "session_id": message.session_id,
        "actions": [],  # Optional: quick actions/buttons
    }


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history for a session"""
    session = _widget_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "messages": session["messages"],
    }


def generate_widget_response(message: str, context: Optional[dict]) -> str:
    """Generate a response for widget (MVP mock)"""
    message_lower = message.lower()
    
    if "help" in message_lower or "hilfe" in message_lower:
        return "I can help you with:\n• Answering questions\n• Reporting issues\n• Providing documentation\n\nWhat do you need?"
    
    if "bug" in message_lower or "issue" in message_lower or "problem" in message_lower:
        return "I can help report this issue. Can you describe what happened and what you expected?"
    
    if "hello" in message_lower or "hi" in message_lower:
        return "Hello! 👋 I'm AXE, your assistant. How can I help you today?"
    
    return "I understand. I'm forwarding this to the team. Is there anything else I can help with?"


@router.get("/axe.js")
async def get_widget_js():
    """
    Serve the AXE Widget JavaScript.
    
    This is the embeddable script that websites include.
    """
    js_code = '''
(function() {
    'use strict';
    
    // AXE Widget v1.0
    window.AxeWidget = {
        config: null,
        sessionId: null,
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
                    align-self: flex-start;
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
                        <h3>🤖 AXE Assistant</h3>
                        <p>Ask me anything</p>
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
                const response = await fetch(this.apiBase + '/widget/init', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.config)
                });
                const data = await response.json();
                this.sessionId = data.session_id;
                
                // Add greeting
                if (data.widget_config?.greeting) {
                    this.addMessage('assistant', data.widget_config.greeting);
                }
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
            if (!message) return;
            
            // Add user message
            this.addMessage('user', message);
            input.value = '';
            
            // Send to backend
            try {
                const response = await fetch(this.apiBase + '/widget/message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: this.sessionId,
                        message: message,
                        context: {
                            url: window.location.href,
                            timestamp: new Date().toISOString()
                        }
                    })
                });
                const data = await response.json();
                this.addMessage('assistant', data.message);
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
    
    return {"content": js_code, "media_type": "application/javascript"}
