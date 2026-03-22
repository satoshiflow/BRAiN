#!/usr/bin/env python3
"""Tiny OpenAI-compatible mock LLM server for local AXE pipeline tests."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockLLMHandler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.endswith("/models"):
            self._send_json(200, {"object": "list", "data": [{"id": "mock-model"}]})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if not self.path.endswith("/chat/completions"):
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        payload = json.loads(raw or "{}")
        messages = payload.get("messages") or []
        last_message = (messages[-1] or {}).get("content", "") if messages else ""

        reply = {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"MOCK-LLM ACK: {last_message}",
                    },
                    "finish_reason": "stop",
                }
            ],
        }
        self._send_json(200, reply)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        print("MOCKLLM", format % args, flush=True)


def main() -> None:
    HTTPServer(("127.0.0.1", 8099), MockLLMHandler).serve_forever()


if __name__ == "__main__":
    main()
