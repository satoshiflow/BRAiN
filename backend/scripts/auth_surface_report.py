#!/usr/bin/env python3
"""Generate a lightweight auth surface report for module routers.

This script scans `app/modules/*/router.py` and reports whether router-level
auth dependencies are present and whether mutating endpoints appear protected
with role/auth dependencies.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / "app" / "modules"


@dataclass
class RouteInfo:
    method: str
    path: str
    name: str
    has_auth_marker: bool


@dataclass
class RouterReport:
    module: str
    file_path: Path
    router_has_auth: bool
    mutating_routes: list[RouteInfo]
    read_routes: list[RouteInfo]


def _decorator_route_info(dec: ast.AST) -> tuple[str, str] | None:
    if not isinstance(dec, ast.Call):
        return None
    if not isinstance(dec.func, ast.Attribute):
        return None
    if dec.func.attr not in {"get", "post", "put", "patch", "delete"}:
        return None
    method = dec.func.attr.upper()
    path = ""
    if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
        path = dec.args[0].value
    return method, path


def _contains_auth_marker(node: ast.AST) -> bool:
    text = ast.unparse(node)
    markers = (
        "require_auth",
        "require_role",
        "require_admin",
        "require_operator",
        "Depends(require_auth",
        "Depends(require_role",
        "X-API-Key",
        "x_api_key",
        "X-Session-Token",
        "x_session_token",
        "verify_credential",
    )
    return any(m in text for m in markers)


def analyze_router(path: Path) -> RouterReport:
    tree = ast.parse(path.read_text())
    router_has_auth = False
    mutating: list[RouteInfo] = []
    read_only: list[RouteInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "router" and isinstance(node.value, ast.Call):
                    router_has_auth = _contains_auth_marker(node.value)

        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            routes = []
            for dec in node.decorator_list:
                info = _decorator_route_info(dec)
                if info:
                    routes.append(info)
            if not routes:
                continue
            has_auth = _contains_auth_marker(node)
            for method, route_path in routes:
                info = RouteInfo(method=method, path=route_path, name=node.name, has_auth_marker=has_auth)
                if method in {"POST", "PUT", "PATCH", "DELETE"}:
                    mutating.append(info)
                else:
                    read_only.append(info)

    module = path.parent.name
    return RouterReport(
        module=module,
        file_path=path,
        router_has_auth=router_has_auth,
        mutating_routes=mutating,
        read_routes=read_only,
    )


def main() -> int:
    routers = sorted(MODULES.glob("*/router.py"))
    reports = [analyze_router(p) for p in routers]

    print("# Auth Surface Report")
    print()
    print("module,router_auth,mutating_total,mutating_with_auth_marker,read_total")

    for rep in reports:
        mut_total = len(rep.mutating_routes)
        mut_auth = sum(1 for r in rep.mutating_routes if r.has_auth_marker)
        print(f"{rep.module},{rep.router_has_auth},{mut_total},{mut_auth},{len(rep.read_routes)}")

    print("\n# Potential Risks")
    for rep in reports:
        unguarded = [r for r in rep.mutating_routes if not r.has_auth_marker]
        if not rep.router_has_auth and unguarded:
            print(f"- {rep.module}: mutating routes present without router-level auth dependency")
        for route in unguarded:
            if not rep.router_has_auth:
                print(f"  - {rep.module} {route.method} {route.path} ({route.name}) appears unguarded")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
