#!/usr/bin/env python3
"""
Minimal AXE WebSocket Test Server
Implements the AXE WebSocket protocol for E2E testing without full BRAiN dependencies.
"""

import asyncio
import json
import uuid
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI(title="AXE WebSocket Test Server")

# Simple connection manager
active_connections: Dict[str, WebSocket] = {}


@app.get("/")
async def root():
    return {"name": "AXE WebSocket Test Server", "status": "online"}


@app.get("/api/health")
async def health():
    return {"status": "healthy", "connections": len(active_connections)}


@app.get("/api/axe/info")
async def axe_info():
    return {
        "name": "AXE",
        "version": "2.0-test",
        "status": "online",
        "description": "AXE WebSocket Test Server",
        "governance": {
            "trust_tier": "LOCAL",
            "source_service": "test",
            "authenticated": True
        }
    }


@app.get("/api/axe/config/{app_id}")
async def axe_config(app_id: str):
    """Get AXE widget configuration."""
    return {
        "app_id": app_id,
        "display_name": f"{app_id.replace('_', ' ').title()} Assistant",
        "theme": "dark",
        "mode": "assistant",
        "telemetry": {
            "enabled": True,
            "anonymization_level": "pseudonymized"
        },
        "ui": {
            "show_context_panel": True,
            "enable_canvas": True
        }
    }


@app.websocket("/api/axe/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    AXE WebSocket endpoint for testing.
    """
    await websocket.accept()
    active_connections[session_id] = websocket
    print(f"✅ WebSocket connected: session={session_id}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": "Invalid JSON"}
                })
                continue

            message_type = message.get("type")
            payload = message.get("payload", {})

            print(f"📨 Received: {message_type} from {session_id}")

            # Handle: chat
            if message_type == "chat":
                user_message = payload.get("message", "")
                print(f"💬 Chat: {user_message}")

                # Mock response
                reply_text = f"Echo: {user_message}"

                await websocket.send_json({
                    "type": "chat_response",
                    "payload": {
                        "message": reply_text,
                        "metadata": {"test": True}
                    }
                })

                # Generate mock diff if message contains "code" or "function"
                if "code" in user_message.lower() or "function" in user_message.lower():
                    mock_diff = {
                        "id": str(uuid.uuid4()),
                        "fileId": "test-file-1",
                        "fileName": "example.tsx",
                        "language": "typescript",
                        "oldContent": "// Old code\n",
                        "newContent": f"// Generated code\nfunction test() {{\n  return '{user_message}';\n}}\n",
                        "description": "Mock code suggestion"
                    }
                    await websocket.send_json({
                        "type": "diff",
                        "payload": mock_diff
                    })
                    print(f"📝 Sent diff: {mock_diff['id']}")

            # Handle: diff_applied
            elif message_type == "diff_applied":
                diff_id = payload.get("diff_id")
                print(f"✅ Diff applied: {diff_id}")
                await websocket.send_json({
                    "type": "diff_applied_confirmed",
                    "payload": {"diff_id": diff_id}
                })

            # Handle: diff_rejected
            elif message_type == "diff_rejected":
                diff_id = payload.get("diff_id")
                print(f"❌ Diff rejected: {diff_id}")
                await websocket.send_json({
                    "type": "diff_rejected_confirmed",
                    "payload": {"diff_id": diff_id}
                })

            # Handle: file_updated
            elif message_type == "file_updated":
                file_id = payload.get("file_id")
                print(f"📄 File updated: {file_id}")
                await websocket.send_json({
                    "type": "file_updated_confirmed",
                    "payload": {"file_id": file_id}
                })

            # Handle: ping
            elif message_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "payload": {"timestamp": payload.get("timestamp")}
                })
                print(f"🏓 Pong sent")

            # Unknown message type
            else:
                print(f"⚠️  Unknown message type: {message_type}")
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": f"Unknown message type: {message_type}"}
                })

    except WebSocketDisconnect:
        print(f"❌ WebSocket disconnected: session={session_id}")
    except Exception as e:
        print(f"⚠️  WebSocket error for {session_id}: {e}")
    finally:
        if session_id in active_connections:
            del active_connections[session_id]
        print(f"🧹 Cleaned up session: {session_id}")


if __name__ == "__main__":
    print("🚀 Starting AXE WebSocket Test Server on http://localhost:8000")
    print("📡 WebSocket endpoint: ws://localhost:8000/api/axe/ws/{session_id}")
    print("ℹ️  Info endpoint: http://localhost:8000/api/axe/info")
    print("⚙️  Config endpoint: http://localhost:8000/api/axe/config/{app_id}")
    print("\nPress Ctrl+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
