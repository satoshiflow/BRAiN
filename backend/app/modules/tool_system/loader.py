"""
Tool Loader - Dynamic tool loading from multiple sources.

Supports:
    - python_module: Import a Python callable from a dotted path
    - python_entrypoint: Load via pkg_resources / importlib.metadata
    - http_api: Wrap an external HTTP endpoint as a callable
    - mcp: Connect to a Model Context Protocol server
    - builtin: Load from BRAIN's built-in tool library
"""

from __future__ import annotations

import importlib
import inspect
from typing import Any, Callable, Coroutine, Dict, Optional

import httpx
from loguru import logger

from .schemas import ToolDefinition, ToolSource, ToolSourceType

# Type alias for loaded tool callables
ToolCallable = Callable[..., Coroutine[Any, Any, Any]]


class ToolLoadError(Exception):
    """Raised when a tool cannot be loaded."""
    pass


class ToolLoader:
    """
    Dynamically loads tools from various sources into callable functions.

    Each loaded tool is normalized into an async callable with signature:
        async def tool(**params) -> Any
    """

    def __init__(self) -> None:
        # Cache of loaded callables keyed by tool_id
        self._cache: Dict[str, ToolCallable] = {}
        logger.info("🔌 ToolLoader initialized")

    async def load(self, tool: ToolDefinition) -> ToolCallable:
        """
        Load a tool and return an async callable.

        Caches the result so repeated loads are free.

        Args:
            tool: The tool definition to load.

        Returns:
            Async callable wrapping the tool's functionality.

        Raises:
            ToolLoadError: If loading fails.
        """
        if tool.tool_id in self._cache:
            return self._cache[tool.tool_id]

        source = tool.source
        loader_map = {
            ToolSourceType.PYTHON_MODULE: self._load_python_module,
            ToolSourceType.PYTHON_ENTRYPOINT: self._load_python_entrypoint,
            ToolSourceType.HTTP_API: self._load_http_api,
            ToolSourceType.MCP: self._load_mcp,
            ToolSourceType.BUILTIN: self._load_builtin,
        }

        loader = loader_map.get(source.source_type)
        if not loader:
            raise ToolLoadError(f"Unknown source type: {source.source_type}")

        try:
            fn = await loader(source)
            self._cache[tool.tool_id] = fn
            logger.info("✅ Loaded tool: %s (type=%s)", tool.name, source.source_type.value)
            return fn
        except ToolLoadError:
            raise
        except Exception as e:
            raise ToolLoadError(f"Failed to load tool '{tool.name}': {e}") from e

    def unload(self, tool_id: str) -> bool:
        """Remove a tool from the cache."""
        return self._cache.pop(tool_id, None) is not None

    def is_loaded(self, tool_id: str) -> bool:
        return tool_id in self._cache

    # ------------------------------------------------------------------
    # Loaders per source type
    # ------------------------------------------------------------------

    async def _load_python_module(self, source: ToolSource) -> ToolCallable:
        """
        Import a Python module and extract the entrypoint function.

        source.location = "app.modules.tool_system.builtins.web_search"
        source.entrypoint = "search"  (optional, defaults to "execute")
        """
        try:
            module = importlib.import_module(source.location)
        except ImportError as e:
            raise ToolLoadError(f"Cannot import module '{source.location}': {e}") from e

        entrypoint = source.entrypoint or "execute"
        fn = getattr(module, entrypoint, None)
        if fn is None:
            raise ToolLoadError(
                f"Module '{source.location}' has no attribute '{entrypoint}'"
            )

        return self._ensure_async(fn)

    async def _load_python_entrypoint(self, source: ToolSource) -> ToolCallable:
        """
        Load via importlib.metadata entry_points.

        source.location = "group_name"
        source.entrypoint = "entry_name"
        """
        try:
            from importlib.metadata import entry_points
        except ImportError:
            raise ToolLoadError("importlib.metadata not available")

        group = source.location
        name = source.entrypoint or "default"
        eps = entry_points()

        # Python 3.12+ returns a SelectableGroups
        if hasattr(eps, "select"):
            matches = eps.select(group=group, name=name)
        else:
            matches = [ep for ep in eps.get(group, []) if ep.name == name]

        matches_list = list(matches)
        if not matches_list:
            raise ToolLoadError(f"No entry point '{name}' in group '{group}'")

        fn = matches_list[0].load()
        return self._ensure_async(fn)

    async def _load_http_api(self, source: ToolSource) -> ToolCallable:
        """
        Create an async callable that POSTs to an HTTP endpoint.

        source.location = "https://api.example.com/tool/execute"
        """
        url = source.location
        headers: Dict[str, str] = {}

        if source.auth_required and source.auth_config:
            header_name = source.auth_config.get("header", "Authorization")
            # Token must be injected at runtime via params["_auth_token"]
            # We never store secrets in the definition.
            headers[header_name] = ""

        async def http_tool(**params: Any) -> Any:
            auth_token = params.pop("_auth_token", None)
            request_headers = dict(headers)
            if auth_token and source.auth_config:
                header_name = source.auth_config.get("header", "Authorization")
                prefix = source.auth_config.get("prefix", "Bearer")
                request_headers[header_name] = f"{prefix} {auth_token}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=params, headers=request_headers)
                response.raise_for_status()
                return response.json()

        return http_tool

    async def _load_mcp(self, source: ToolSource) -> ToolCallable:
        """
        Create a callable that communicates with an MCP server.

        source.location = "http://localhost:8080" (MCP server)
        source.entrypoint = "tool_name" (tool within MCP server)

        Phase 1: Simple HTTP-based MCP proxy.
        Phase 2: Full MCP protocol with stdio/SSE transport.
        """
        server_url = source.location.rstrip("/")
        tool_name = source.entrypoint or "default"

        async def mcp_tool(**params: Any) -> Any:
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": params,
                },
                "id": 1,
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(server_url, json=payload)
                response.raise_for_status()
                result = response.json()
                if "error" in result:
                    raise ToolLoadError(f"MCP error: {result['error']}")
                return result.get("result")

        return mcp_tool

    async def _load_builtin(self, source: ToolSource) -> ToolCallable:
        """
        Load a built-in BRAIN tool.

        source.location = "echo" | "noop" | etc.
        """
        builtins = {
            "echo": self._builtin_echo,
            "noop": self._builtin_noop,
        }

        fn = builtins.get(source.location)
        if fn is None:
            raise ToolLoadError(f"Unknown builtin: '{source.location}'")
        return fn

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_async(fn: Any) -> ToolCallable:
        """Wrap sync functions into async if needed."""
        if inspect.iscoroutinefunction(fn):
            return fn

        async def async_wrapper(**params: Any) -> Any:
            return fn(**params)

        return async_wrapper

    # ------------------------------------------------------------------
    # Built-in tools
    # ------------------------------------------------------------------

    @staticmethod
    async def _builtin_echo(**params: Any) -> Any:
        """Echo tool - returns its input."""
        return params

    @staticmethod
    async def _builtin_noop(**params: Any) -> None:
        """No-op tool - does nothing."""
        return None
