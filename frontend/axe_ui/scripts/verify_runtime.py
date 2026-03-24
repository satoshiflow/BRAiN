#!/usr/bin/env python3
"""Runtime smoke checks for AXE UI dev/prod server.

Checks critical routes and fails if Next.js serves chunk/module errors.
"""

from __future__ import annotations

import sys
import time
import re
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:3002"
ROUTES = ["/", "/chat", "/dashboard", "/settings", "/widget-test"]
BAD_MARKERS = (
    "Cannot find module",
    "Module not found",
    "ChunkLoadError",
    "./682.js",
)

ASSET_PATTERN = re.compile(r'/(?:_next/static/[^"\'\s>]+)')


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


def collect_static_assets(body: str) -> set[str]:
    assets: set[str] = set()
    for match in ASSET_PATTERN.findall(body):
        asset_path = match.split("?", 1)[0]
        if asset_path.endswith(".map"):
            continue
        assets.add(asset_path)
    return assets


def main() -> int:
    failures: list[str] = []
    assets: set[str] = set()

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

        assets.update(collect_static_assets(body))

    if not assets:
        failures.append("No /_next/static assets discovered from route HTML")
    else:
        has_js = any(path.endswith(".js") for path in assets)
        has_css = any(path.endswith(".css") for path in assets)
        if not has_js:
            failures.append("No JavaScript assets discovered under /_next/static")
        if not has_css:
            failures.append("No CSS assets discovered under /_next/static")

        for asset_path in sorted(assets):
            try:
                status, body = fetch(asset_path)
            except Exception as exc:  # pragma: no cover - runtime probe utility
                failures.append(str(exc))
                continue

            if status != 200:
                failures.append(f"Asset {asset_path} returned HTTP {status}")
                continue

            if body.lstrip().startswith("<!DOCTYPE html"):
                failures.append(f"Asset {asset_path} returned HTML instead of static content")
                continue

    if failures:
        print("AXE UI runtime verification failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("AXE UI runtime verification passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
