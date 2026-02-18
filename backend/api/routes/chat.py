"""
Chat API Endpoint - Ollama Integration for AXE UI

POST /api/chat - Chat completion with Ollama LLM
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx
import os
from loguru import logger

router = APIRouter()


# ===== PYDANTIC MODELS =====

class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request payload"""
    messages: List[ChatMessage] = Field(..., min_length=1, description="Chat message history")
    model: Optional[str] = Field(default="qwen2.5:0.5b", description="LLM model to use")
    max_tokens: Optional[int] = Field(default=500, ge=1, le=4000, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    stream: Optional[bool] = Field(default=False, description="Stream response (not yet implemented)")


class ChatResponse(BaseModel):
    """Chat response"""
    message: ChatMessage
    model: str
    usage: Dict[str, int]


# ===== HELPER FUNCTIONS =====

def format_messages_for_ollama(messages: List[ChatMessage]) -> str:
    """
    Convert chat messages to a single prompt string for Ollama.

    Ollama's /api/generate endpoint expects a single prompt string.
    We format the conversation history into a readable format.
    """
    prompt_parts = []

    for msg in messages:
        role = msg.role.upper()
        content = msg.content

        if msg.role == "system":
            prompt_parts.append(f"SYSTEM: {content}")
        elif msg.role == "user":
            prompt_parts.append(f"USER: {content}")
        elif msg.role == "assistant":
            prompt_parts.append(f"ASSISTANT: {content}")

    # Add assistant prompt prefix for the new response
    prompt_parts.append("ASSISTANT:")

    return "\n\n".join(prompt_parts)


async def call_ollama_generate(
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float
) -> Dict[str, Any]:
    """
    Call Ollama's /api/generate endpoint.

    Args:
        prompt: Formatted prompt string
        model: Model name (e.g., "qwen2.5:0.5b")
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature

    Returns:
        dict: Ollama response

    Raises:
        httpx.ConnectError: If Ollama is not reachable
        httpx.HTTPStatusError: If Ollama returns error status
    """
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    logger.info(f"Calling Ollama at {ollama_host} with model {model}")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{ollama_host}/api/generate",
            json=payload
        )
        response.raise_for_status()
        return response.json()


# ===== API ENDPOINT =====

@router.post(
    "/",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat completion",
    description="Send chat messages and get AI-generated responses from Ollama LLM"
)
async def chat(request: ChatRequest):
    """
    Chat completion endpoint using local Ollama LLM.

    **Example Request:**
    ```json
    {
      "messages": [
        {"role": "user", "content": "Hallo! Wer bist du?"}
      ],
      "model": "qwen2.5:0.5b",
      "max_tokens": 500,
      "temperature": 0.7
    }
    ```

    **Example Response:**
    ```json
    {
      "message": {
        "role": "assistant",
        "content": "Hallo! Ich bin ein KI-Assistent..."
      },
      "model": "qwen2.5:0.5b",
      "usage": {
        "prompt_tokens": 15,
        "completion_tokens": 45,
        "total_tokens": 60
      }
    }
    ```

    **Error Codes:**
    - 400: Invalid request (empty messages, etc.)
    - 503: Ollama service unavailable
    - 500: Internal server error
    """

    # Validate
    if not request.messages:
        raise HTTPException(
            status_code=400,
            detail="messages array cannot be empty"
        )

    # Get Ollama config
    ollama_model = request.model or os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

    try:
        # Format messages for Ollama
        prompt = format_messages_for_ollama(request.messages)
        logger.debug(f"Formatted prompt: {prompt[:200]}...")

        # Call Ollama
        ollama_response = await call_ollama_generate(
            prompt=prompt,
            model=ollama_model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        # Extract response text
        assistant_content = ollama_response.get("response", "").strip()

        if not assistant_content:
            raise HTTPException(
                status_code=500,
                detail="Ollama returned empty response"
            )

        # Calculate token usage (approximation)
        prompt_tokens = len(prompt.split())
        completion_tokens = len(assistant_content.split())

        # Build response
        response = ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=assistant_content
            ),
            model=ollama_model,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
        )

        logger.info(f"Chat completion successful: {completion_tokens} tokens")
        return response

    except httpx.ConnectError as e:
        logger.error(f"Cannot connect to Ollama: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Ollama service not available. Please check if Ollama is running at {os.getenv('OLLAMA_HOST')}"
        )

    except httpx.HTTPStatusError as e:
        logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned error: {e.response.status_code}"
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ===== HEALTH CHECK =====

@router.get(
    "/health",
    summary="Check Ollama connection",
    description="Test if Ollama service is reachable and responding"
)
async def health_check():
    """
    Check if Ollama is reachable and has models available.

    Returns connection status and available models.
    """
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_host}/api/tags")
            response.raise_for_status()

            data = response.json()
            models = data.get("models", [])

            return {
                "status": "healthy",
                "ollama_host": ollama_host,
                "ollama_reachable": True,
                "models_available": len(models),
                "models": [m.get("name") for m in models[:5]]  # First 5
            }

    except httpx.ConnectError:
        return {
            "status": "unhealthy",
            "ollama_host": ollama_host,
            "ollama_reachable": False,
            "error": "Cannot connect to Ollama service"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "ollama_host": ollama_host,
            "error": str(e)
        }
