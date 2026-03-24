#!/usr/bin/env python3
"""Start AXE UI dev server with process/artifact safety checks."""

from __future__ import annotations

import os
import socket
import subprocess
import sys


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3002


def _parse_host_port(args: list[str]) -> tuple[str, int]:
    host = DEFAULT_HOST
    port = DEFAULT_PORT

    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg in {"--hostname", "-H"} and idx + 1 < len(args):
            host = args[idx + 1]
            idx += 2
            continue
        if arg.startswith("--hostname="):
            host = arg.split("=", 1)[1]
            idx += 1
            continue
        if arg in {"--port", "-p"} and idx + 1 < len(args):
            try:
                port = int(args[idx + 1])
            except ValueError:
                pass
            idx += 2
            continue
        if arg.startswith("--port="):
            try:
                port = int(arg.split("=", 1)[1])
            except ValueError:
                pass
            idx += 1
            continue
        idx += 1

    return host, port


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def main() -> int:
    forwarded_args = sys.argv[1:]
    host, port = _parse_host_port(forwarded_args)

    if _port_in_use(host, port):
        print(
            f"Refusing to start AXE UI dev server: {host}:{port} is already in use.\n"
            "This protects against mixed Next.js runtime artifacts and stale chunk/CSS state.\n"
            "Stop the old process first, or run with a different --port and NEXT_DIST_DIR."
        )
        return 1

    env = os.environ.copy()
    env.setdefault("NEXT_DIST_DIR", ".next-dev")

    cmd = ["next", "dev", "-p", str(port), "--hostname", host, *forwarded_args]
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
