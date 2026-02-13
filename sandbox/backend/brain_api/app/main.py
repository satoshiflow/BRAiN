from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="BRAiN API")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    reply: str

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    last_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    reply = f"You said: {last_user}"
    return ChatResponse(reply=reply)
