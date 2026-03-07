#!/usr/bin/env python3
"""Lightweight OpenAI-compatible mock LLM service.

This service provides a minimal `/v1/chat/completions` contract for local BRAiN
development without loading any real model engine.
"""

from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Tuple


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


HOST = os.getenv("MOCK_LLM_HOST", "0.0.0.0")
PORT = _env_int("MOCK_LLM_PORT", 8080)

DEFAULT_MODEL = os.getenv("MOCK_LLM_MODEL", "brain-mock-1")
MODE = os.getenv("MOCK_LLM_MODE", "rules")
SYSTEM_PROMPT_TAG = os.getenv("MOCK_LLM_SYSTEM_TAG", "BRAiN-MOCK")

LATENCY_MIN_MS = max(0, _env_int("MOCK_LLM_LATENCY_MIN_MS", 40))
LATENCY_MAX_MS = max(LATENCY_MIN_MS, _env_int("MOCK_LLM_LATENCY_MAX_MS", 140))

ERROR_RATE = min(max(_env_float("MOCK_LLM_ERROR_RATE", 0.0), 0.0), 1.0)
ERROR_STATUS = _env_int("MOCK_LLM_ERROR_STATUS", 503)
ERROR_TRIGGER = os.getenv("MOCK_LLM_ERROR_TRIGGER", "trigger_error")

ALLOW_STREAM = _env_bool("MOCK_LLM_ALLOW_STREAM", False)


def _now_epoch() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _read_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def _extract_last_user_message(messages: List[Dict[str, Any]]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
    return ""


def _token_estimate(text: str) -> int:
    words = len(text.split())
    return max(1, int(words * 1.3))


def _make_mock_answer(last_user_text: str) -> str:
    lowered = last_user_text.lower()
    if MODE == "echo":
        return f"[{SYSTEM_PROMPT_TAG}] Echo: {last_user_text.strip() or 'No user input provided.'}"

    if "health" in lowered or "status" in lowered:
        return f"[{SYSTEM_PROMPT_TAG}] System status is nominal. Local mock path is healthy."
    if "plan" in lowered:
        return (
            f"[{SYSTEM_PROMPT_TAG}] Suggested next step: decompose task, execute one node, "
            "record memory and metric feedback."
        )
    if "error" in lowered or "fail" in lowered:
        return f"[{SYSTEM_PROMPT_TAG}] Acknowledged. Simulated recovery strategy: retry with bounded backoff."

    return f"[{SYSTEM_PROMPT_TAG}] Mock completion generated successfully."


def _maybe_fail(last_user_text: str) -> Tuple[bool, str]:
    if ERROR_TRIGGER and ERROR_TRIGGER in last_user_text.lower():
        return True, "Triggered mock error by content rule"
    if random.random() < ERROR_RATE:
        return True, "Triggered mock error by random error rate"
    return False, ""


class MockLLMHandler(BaseHTTPRequestHandler):
    server_version = "BRAiNMockLLM/1.0"

    def _write_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._write_json(
                200,
                {
                    "ok": True,
                    "service": "mock-llm",
                    "model": DEFAULT_MODEL,
                    "mode": MODE,
                    "timestamp": _now_epoch(),
                },
            )
            return

        self._write_json(404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self._write_json(404, {"error": "Not found"})
            return

        payload = _read_json(self)
        model = payload.get("model") or DEFAULT_MODEL
        messages = payload.get("messages") or []
        stream = bool(payload.get("stream", False))

        if stream and not ALLOW_STREAM:
            self._write_json(
                400,
                {
                    "error": {
                        "message": "Streaming not enabled in mock service",
                        "type": "invalid_request_error",
                        "code": "stream_not_supported",
                    }
                },
            )
            return

        if not isinstance(messages, list) or not messages:
            self._write_json(
                400,
                {
                    "error": {
                        "message": "messages must be a non-empty list",
                        "type": "invalid_request_error",
                        "code": "invalid_messages",
                    }
                },
            )
            return

        last_user_text = _extract_last_user_message(messages)
        should_fail, fail_reason = _maybe_fail(last_user_text)
        if should_fail:
            self._write_json(
                ERROR_STATUS,
                {
                    "error": {
                        "message": fail_reason,
                        "type": "mock_service_error",
                        "code": "mock_error",
                    }
                },
            )
            return

        latency_ms = random.randint(LATENCY_MIN_MS, LATENCY_MAX_MS)
        time.sleep(latency_ms / 1000.0)

        content = _make_mock_answer(last_user_text)
        prompt_tokens = sum(_token_estimate(str(m.get("content", ""))) for m in messages)
        completion_tokens = _token_estimate(content)

        response = {
            "id": f"chatcmpl-mock-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "created": _now_epoch(),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "mock": {
                "latency_ms": latency_ms,
                "mode": MODE,
            },
        }

        self._write_json(200, response)

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep logs concise for local dev.
        print(f"[mock-llm] {self.address_string()} - {fmt % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), MockLLMHandler)
    print(f"[mock-llm] listening on http://{HOST}:{PORT}")
    print(f"[mock-llm] model={DEFAULT_MODEL} mode={MODE} latency={LATENCY_MIN_MS}-{LATENCY_MAX_MS}ms")
    server.serve_forever()


if __name__ == "__main__":
    main()
