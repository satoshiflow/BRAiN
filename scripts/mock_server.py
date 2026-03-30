#!/usr/bin/env python3
from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

@app.route("/v1/chat/completions", methods=["POST"])
def chat():
    data = request.json
    msgs = data.get("messages", [])
    last = msgs[-1]["content"] if msgs else ""
    return jsonify({
        "id": "chatcmpl-" + uuid.uuid4().hex[:8],
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "MOCK: " + last}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "provider": "mock"})

@app.route("/v1/models", methods=["GET"])
def models():
    return jsonify({"data": [{"id": "mock-local"}]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099)
