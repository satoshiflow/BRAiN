"""
API Client Generator

Generates TypeScript API client code from OpenAPI schema.

Usage:
    python -m backend.app.dev_tools.api_client_generator

Generates:
    - TypeScript types from Pydantic models
    - Type-safe API client functions
    - Request/response interfaces

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi.openapi.utils import get_openapi


def generate_typescript_client(openapi_schema: Dict[str, Any], output_path: Path):
    """
    Generate TypeScript API client from OpenAPI schema.

    Args:
        openapi_schema: OpenAPI 3.0 schema
        output_path: Output directory for generated files
    """
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate types
    types_code = _generate_types(openapi_schema)
    (output_path / "types.ts").write_text(types_code)

    # Generate API client
    client_code = _generate_client(openapi_schema)
    (output_path / "api.ts").write_text(client_code)

    # Generate index
    index_code = """export * from './types';
export * from './api';
"""
    (output_path / "index.ts").write_text(index_code)

    print(f"✓ TypeScript client generated in {output_path}")


def _generate_types(schema: Dict[str, Any]) -> str:
    """Generate TypeScript type definitions."""
    code = """/**
 * Auto-generated TypeScript types from OpenAPI schema
 * Do not edit manually - regenerate using API client generator
 */

"""

    components = schema.get("components", {})
    schemas = components.get("schemas", {})

    for name, definition in schemas.items():
        code += _generate_type_definition(name, definition)
        code += "\n\n"

    return code


def _generate_type_definition(name: str, definition: Dict[str, Any]) -> str:
    """Generate single TypeScript type definition."""
    properties = definition.get("properties", {})
    required = definition.get("required", [])

    code = f"export interface {name} {{\n"

    for prop_name, prop_def in properties.items():
        is_required = prop_name in required
        optional = "" if is_required else "?"

        ts_type = _openapi_to_typescript_type(prop_def)
        description = prop_def.get("description", "")

        if description:
            code += f"  /** {description} */\n"

        code += f"  {prop_name}{optional}: {ts_type};\n"

    code += "}"

    return code


def _openapi_to_typescript_type(prop_def: Dict[str, Any]) -> str:
    """Convert OpenAPI type to TypeScript type."""
    prop_type = prop_def.get("type")

    type_map = {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "array": "Array<any>",
        "object": "Record<string, any>",
    }

    if prop_type == "array":
        items = prop_def.get("items", {})
        item_type = _openapi_to_typescript_type(items)
        return f"Array<{item_type}>"

    if "$ref" in prop_def:
        ref = prop_def["$ref"]
        return ref.split("/")[-1]

    return type_map.get(prop_type, "any")


def _generate_client(schema: Dict[str, Any]) -> str:
    """Generate TypeScript API client."""
    code = """/**
 * Auto-generated TypeScript API client
 * Do not edit manually - regenerate using API client generator
 */

import type * as Types from './types';

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? 'http://localhost:8000';

class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${path}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new APIError(
      error.detail || response.statusText,
      response.status,
      error
    );
  }

  return response.json();
}

export const api = {
"""

    paths = schema.get("paths", {})

    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                continue

            code += _generate_client_method(path, method, operation)

    code += "};\n"

    return code


def _generate_client_method(path: str, method: str, operation: Dict[str, Any]) -> str:
    """Generate single API client method."""
    operation_id = operation.get("operationId", "")
    summary = operation.get("summary", "")

    # Convert path parameters
    ts_path = path.replace("{", "${")

    # Determine method name
    method_name = operation_id or _path_to_method_name(path, method)

    # Get request/response types
    request_body = operation.get("requestBody", {})
    responses = operation.get("responses", {})

    # Build method signature
    params = []
    if "{" in path:
        params.append("pathParams: Record<string, string>")

    if request_body:
        params.append("data: any")

    params_str = ", ".join(params)

    code = f"""
  /**
   * {summary or method.upper() + ' ' + path}
   */
  async {method_name}({params_str}): Promise<any> {{
"""

    if "{" in path:
        code += f"    const path = `{ts_path}`;\n"
    else:
        code += f"    const path = '{path}';\n"

    if method.lower() == "get":
        code += "    return request(path);\n"
    elif method.lower() in ["post", "put", "patch"]:
        code += "    return request(path, { method: '" + method.upper() + "', body: JSON.stringify(data) });\n"
    elif method.lower() == "delete":
        code += "    return request(path, { method: 'DELETE' });\n"

    code += "  },\n"

    return code


def _path_to_method_name(path: str, method: str) -> str:
    """Convert path and method to camelCase method name."""
    parts = path.strip("/").split("/")

    # Remove path parameters
    parts = [p for p in parts if not p.startswith("{")]

    # Convert to camelCase
    if not parts:
        return method.lower()

    name = method.lower()
    for part in parts:
        name += part.capitalize()

    return name


def main():
    """Generate TypeScript client from running FastAPI app."""
    import sys
    from pathlib import Path

    # Add backend to path
    backend_path = str(Path(__file__).parent.parent.parent)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    # Import app
    from main import app

    # Get OpenAPI schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Generate client
    output_path = Path(backend_path).parent / "frontend" / "generated"
    generate_typescript_client(openapi_schema, output_path)

    print(f"✓ TypeScript client generated in {output_path}")
    print("  - types.ts")
    print("  - api.ts")
    print("  - index.ts")


if __name__ == "__main__":
    main()
