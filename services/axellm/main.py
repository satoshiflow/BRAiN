import os
import uuid
import time
from typing import List, Optional, Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import httpx

# Environment Variables
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5:0.5b")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60"))
MAX_TOTAL_CHARS = 20000

app = FastAPI(title="AXEllm", description="OpenAI-compatible API for Ollama")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Models
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

    @validator("content")
    def strip_tool_calls(cls, v):
        # Strip tool/function calls if present
        if isinstance(v, dict):
            return v.get("content", "") if isinstance(v.get("content"), str) else str(v)
        return v


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = DEFAULT_MODEL
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)

    @validator("messages")
    def check_total_length(cls, messages):
        total_chars = sum(len(msg.content) for msg in messages)
        if total_chars > MAX_TOTAL_CHARS:
            raise ValueError(f"Total message length exceeds {MAX_TOTAL_CHARS} characters")
        return messages


class ChatMessageResponse(BaseModel):
    role: str
    content: str


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessageResponse
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    model = request.model or DEFAULT_MODEL
    
    # Format messages for Ollama API
    ollama_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in request.messages
    ]
    
    # Prepare Ollama request payload
    ollama_payload = {
        "model": model,
        "messages": ollama_messages,
        "stream": False,
        "options": {
            "temperature": request.temperature
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=ollama_payload,
                timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            ollama_response = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ollama request timed out")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama service")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    # Extract content from Ollama response
    assistant_message = ollama_response.get("message", {})
    content = assistant_message.get("content", "")
    
    # Build OpenAI-compatible response
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    
    return ChatCompletionResponse(
        id=completion_id,
        created=int(time.time()),
        model=model,
        choices=[
            ChatChoice(
                message=ChatMessageResponse(
                    role="assistant",
                    content=content
                )
            )
        ]
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
