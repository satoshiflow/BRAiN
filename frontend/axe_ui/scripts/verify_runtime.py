#!/usr/bin/env python3
"""Runtime smoke checks for AXE UI dev/prod server.

Checks critical routes and fails if Next.js serves chunk/module errors.
"""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:3002"
ROUTES = ["/", "/chat", "/agents", "/settings", "/widget-test"]
BAD_MARKERS = (
    "Cannot find module",
    "Module not found",
    "ChunkLoadError",
    "./682.js",
)


def fetch(path: str, retries: int = 5, timeout: int = 20) -> tuple[int, str]:
    url = f"{BASE_URL}{path}"
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.status, response.read().decode("utf-8", "ignore")
        except Exception as exc:  # pragma: no cover - runtime probe utility
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"Route {path} unreachable: {last_error}")


def main() -> int:
    failures: list[str] = []
    for path in ROUTES:
        try:
            status, body = fetch(path)
        except Exception as exc:  # pragma: no cover - runtime probe utility
            failures.append(str(exc))
            continue

        if status != 200:
            failures.append(f"Route {path} returned HTTP {status}")
            continue

        for marker in BAD_MARKERS:
            if marker in body:
                failures.append(f"Route {path} contains runtime marker '{marker}'")
                break

    if failures:
        print("AXE UI runtime verification failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("AXE UI runtime verification passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
