"""
Tests for Tool Accumulation System - Sprint 6A

Covers: Registry, Loader, Validator, Sandbox, AccumulationEngine, Service
"""

import asyncio
import sys
import os

import pytest

# Ensure backend is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.modules.tool_system.schemas import (
    ToolCapability,
    ToolDefinition,
    ToolExecutionRequest,
    ToolRegisterRequest,
    ToolSearchRequest,
    ToolSecurityLevel,
    ToolSource,
    ToolSourceType,
    ToolStatus,
    ToolUpdateRequest,
)
from app.modules.tool_system.registry import ToolRegistry
from app.modules.tool_system.loader import ToolLoader, ToolLoadError
from app.modules.tool_system.validator import ToolValidator
from app.modules.tool_system.sandbox import ToolSandbox
from app.modules.tool_system.accumulation import AccumulationEngine
from app.modules.tool_system.service import ToolSystemService


# ============================================================================
# Fixtures
# ============================================================================


def _builtin_source(name: str = "echo") -> ToolSource:
    return ToolSource(source_type=ToolSourceType.BUILTIN, location=name)


def _python_source() -> ToolSource:
    return ToolSource(
        source_type=ToolSourceType.PYTHON_MODULE,
        location="app.modules.tool_system.loader",
        entrypoint="_builtin_echo",  # Doesn't exist as module-level, but useful for pattern test
    )


def _register_request(name: str = "Test Tool", source: ToolSource = None) -> ToolRegisterRequest:
    return ToolRegisterRequest(
        name=name,
        description="A test tool",
        source=source or _builtin_source(),
        capabilities=[ToolCapability(name="test", description="test cap")],
        tags=["test", "demo"],
        security_level=ToolSecurityLevel.TRUSTED,
        version="1.0.0",
        author="test_author",
    )


# ============================================================================
# Registry Tests
# ============================================================================


class TestToolRegistry:
    @pytest.mark.asyncio
    async def test_register_and_get(self):
        reg = ToolRegistry()
        req = _register_request()
        tool = await reg.register(req)

        assert tool.tool_id.startswith("tool_")
        assert tool.name == "Test Tool"
        assert tool.status == ToolStatus.PENDING

        fetched = await reg.get(tool.tool_id)
        assert fetched is not None
        assert fetched.tool_id == tool.tool_id

    @pytest.mark.asyncio
    async def test_list_and_filter(self):
        reg = ToolRegistry()
        await reg.register(_register_request("A"))
        await reg.register(_register_request("B"))

        all_tools = await reg.list_tools()
        assert len(all_tools) == 2

        pending = await reg.list_tools(status=ToolStatus.PENDING)
        assert len(pending) == 2

        active = await reg.list_tools(status=ToolStatus.ACTIVE)
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_update(self):
        reg = ToolRegistry()
        tool = await reg.register(_register_request())
        updated = await reg.update(tool.tool_id, ToolUpdateRequest(tags=["new_tag"]))
        assert updated is not None
        assert "new_tag" in updated.tags

    @pytest.mark.asyncio
    async def test_delete(self):
        reg = ToolRegistry()
        tool = await reg.register(_register_request())
        assert await reg.delete(tool.tool_id) is True
        assert await reg.get(tool.tool_id) is None
        assert await reg.delete("nonexistent") is False

    @pytest.mark.asyncio
    async def test_set_status(self):
        reg = ToolRegistry()
        tool = await reg.register(_register_request())
        assert await reg.set_status(tool.tool_id, ToolStatus.ACTIVE, "test")
        fetched = await reg.get(tool.tool_id)
        assert fetched.status == ToolStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_search(self):
        reg = ToolRegistry()
        await reg.register(_register_request("Web Search"))
        await reg.register(_register_request("File Reader"))

        results = await reg.search(ToolSearchRequest(query="web"))
        assert len(results) == 1
        assert results[0].name == "Web Search"

        results = await reg.search(ToolSearchRequest(tags=["test"]))
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_karma_update(self):
        reg = ToolRegistry()
        tool = await reg.register(_register_request())
        await reg.update_karma(tool.tool_id, 95.0)
        fetched = await reg.get(tool.tool_id)
        assert fetched.karma_score == 95.0

    @pytest.mark.asyncio
    async def test_record_execution(self):
        reg = ToolRegistry()
        tool = await reg.register(_register_request())
        await reg.record_execution(tool.tool_id, True, 100.0)
        await reg.record_execution(tool.tool_id, False, 200.0)

        acc = await reg.get_accumulation(tool.tool_id)
        assert acc.total_executions == 2
        assert acc.successful_executions == 1
        assert acc.failed_executions == 1

    @pytest.mark.asyncio
    async def test_stats(self):
        reg = ToolRegistry()
        await reg.register(_register_request())
        stats = await reg.get_stats()
        assert stats.total_tools == 1
        assert stats.pending_tools == 1


# ============================================================================
# Loader Tests
# ============================================================================


class TestToolLoader:
    @pytest.mark.asyncio
    async def test_load_builtin_echo(self):
        loader = ToolLoader()
        tool = ToolDefinition(
            tool_id="test_echo",
            name="Echo",
            source=_builtin_source("echo"),
        )
        fn = await loader.load(tool)
        result = await fn(msg="hello")
        assert result == {"msg": "hello"}

    @pytest.mark.asyncio
    async def test_load_builtin_noop(self):
        loader = ToolLoader()
        tool = ToolDefinition(
            tool_id="test_noop",
            name="Noop",
            source=_builtin_source("noop"),
        )
        fn = await loader.load(tool)
        result = await fn()
        assert result is None

    @pytest.mark.asyncio
    async def test_load_unknown_builtin(self):
        loader = ToolLoader()
        tool = ToolDefinition(
            tool_id="test_bad",
            name="Bad",
            source=_builtin_source("nonexistent"),
        )
        with pytest.raises(ToolLoadError, match="Unknown builtin"):
            await loader.load(tool)

    @pytest.mark.asyncio
    async def test_cache(self):
        loader = ToolLoader()
        tool = ToolDefinition(
            tool_id="test_cache",
            name="Echo",
            source=_builtin_source("echo"),
        )
        fn1 = await loader.load(tool)
        fn2 = await loader.load(tool)
        assert fn1 is fn2  # Same object from cache

    @pytest.mark.asyncio
    async def test_unload(self):
        loader = ToolLoader()
        tool = ToolDefinition(
            tool_id="test_unload",
            name="Echo",
            source=_builtin_source("echo"),
        )
        await loader.load(tool)
        assert loader.is_loaded("test_unload")
        assert loader.unload("test_unload") is True
        assert not loader.is_loaded("test_unload")


# ============================================================================
# Validator Tests
# ============================================================================


class TestToolValidator:
    @pytest.mark.asyncio
    async def test_valid_builtin(self):
        validator = ToolValidator()
        tool = ToolDefinition(
            tool_id="t1",
            name="Echo Tool",
            description="Echoes input",
            author="test",
            source=_builtin_source("echo"),
            security_level=ToolSecurityLevel.TRUSTED,
            current_version="1.0.0",
            capabilities=[ToolCapability(name="echo", description="echo")],
        )
        result = await validator.validate(tool)
        assert result.passed is True
        assert result.karma_score > 0

    @pytest.mark.asyncio
    async def test_invalid_python_path(self):
        validator = ToolValidator()
        tool = ToolDefinition(
            tool_id="t2",
            name="Bad Path",
            source=ToolSource(
                source_type=ToolSourceType.PYTHON_MODULE,
                location="123-invalid-path",
            ),
        )
        result = await validator.validate(tool)
        assert result.passed is False
        assert any("source_invalid_python_path" in f for f in result.checks_failed)

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        validator = ToolValidator()
        tool = ToolDefinition(
            tool_id="t3",
            name="Bad URL",
            source=ToolSource(
                source_type=ToolSourceType.HTTP_API,
                location="not-a-url",
            ),
        )
        result = await validator.validate(tool)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_karma_scoring(self):
        validator = ToolValidator()
        # Minimal tool = low karma
        minimal = ToolDefinition(
            tool_id="t4",
            name="Minimal",
            source=_builtin_source("echo"),
        )
        result = await validator.validate(minimal)
        karma_minimal = result.karma_score

        # Full tool = high karma
        full = ToolDefinition(
            tool_id="t5",
            name="Full",
            description="A well-documented tool",
            author="senior_dev",
            source=_builtin_source("echo"),
            security_level=ToolSecurityLevel.TRUSTED,
            current_version="2.0.0",
            capabilities=[ToolCapability(name="test", description="test")],
        )
        result_full = await validator.validate(full)
        assert result_full.karma_score > karma_minimal


# ============================================================================
# Sandbox Tests
# ============================================================================


class TestToolSandbox:
    @pytest.mark.asyncio
    async def test_execute_trusted(self):
        sandbox = ToolSandbox()
        tool = ToolDefinition(
            tool_id="s1",
            name="Echo",
            source=_builtin_source("echo"),
            security_level=ToolSecurityLevel.TRUSTED,
        )

        async def echo_fn(**params):
            return params

        request = ToolExecutionRequest(tool_id="s1", parameters={"x": 42})
        result = await sandbox.execute(tool, echo_fn, request)
        assert result.success is True
        assert result.output == {"x": 42}
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_timeout(self):
        sandbox = ToolSandbox()
        tool = ToolDefinition(
            tool_id="s2",
            name="Slow",
            source=_builtin_source("echo"),
            security_level=ToolSecurityLevel.STANDARD,
        )

        async def slow_fn(**params):
            await asyncio.sleep(10)

        request = ToolExecutionRequest(tool_id="s2", parameters={}, timeout_ms=1000)
        result = await sandbox.execute(tool, slow_fn, request)
        assert result.success is False
        assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        sandbox = ToolSandbox()
        tool = ToolDefinition(
            tool_id="s3",
            name="Crasher",
            source=_builtin_source("echo"),
            security_level=ToolSecurityLevel.STANDARD,
        )

        async def crash_fn(**params):
            raise ValueError("boom")

        request = ToolExecutionRequest(tool_id="s3", parameters={})
        result = await sandbox.execute(tool, crash_fn, request)
        assert result.success is False
        assert "boom" in result.error


# ============================================================================
# Accumulation Tests
# ============================================================================


class TestAccumulationEngine:
    @pytest.mark.asyncio
    async def test_record_and_learn(self):
        reg = ToolRegistry()
        tool = await reg.register(_register_request())
        engine = AccumulationEngine(reg)

        from app.modules.tool_system.schemas import ToolExecutionResult

        result = ToolExecutionResult(tool_id=tool.tool_id, success=True, duration_ms=50.0)
        await engine.record_execution(tool.tool_id, result, {"query": "test"})

        acc = await reg.get_accumulation(tool.tool_id)
        assert acc.total_executions == 1
        assert acc.successful_executions == 1
        assert "query" in acc.learned_defaults

    @pytest.mark.asyncio
    async def test_failure_patterns(self):
        reg = ToolRegistry()
        tool = await reg.register(_register_request())
        engine = AccumulationEngine(reg)

        from app.modules.tool_system.schemas import ToolExecutionResult

        result = ToolExecutionResult(
            tool_id=tool.tool_id, success=False, error="Connection timeout", duration_ms=5000.0,
        )
        await engine.record_execution(tool.tool_id, result, {})

        acc = await reg.get_accumulation(tool.tool_id)
        assert "Connection timeout" in acc.failure_patterns

    @pytest.mark.asyncio
    async def test_cooccurrence_synergy(self):
        reg = ToolRegistry()
        t1 = await reg.register(_register_request("Tool A"))
        t2 = await reg.register(_register_request("Tool B"))
        engine = AccumulationEngine(reg)

        # Need SYNERGY_MIN_COOCCURRENCE (3) co-occurrences
        for _ in range(3):
            await engine.record_cooccurrence([t1.tool_id, t2.tool_id])

        acc1 = await reg.get_accumulation(t1.tool_id)
        assert t2.tool_id in acc1.synergies

    @pytest.mark.asyncio
    async def test_recommendations(self):
        reg = ToolRegistry()
        tool = await reg.register(_register_request())
        engine = AccumulationEngine(reg)

        recs = await engine.get_recommendations(tool.tool_id)
        assert recs["tool_id"] == tool.tool_id
        assert "learned_defaults" in recs

    @pytest.mark.asyncio
    async def test_maintenance(self):
        reg = ToolRegistry()
        engine = AccumulationEngine(reg)
        # No active tools → empty maintenance
        actions = await engine.run_maintenance()
        assert actions["suspended"] == []
        assert actions["deprecated"] == []


# ============================================================================
# Service Integration Tests
# ============================================================================


class TestToolSystemService:
    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test the complete tool lifecycle: register → validate → activate → execute."""
        service = ToolSystemService()

        # Register (auto-validates)
        tool = await service.register_tool(_register_request("Echo Tool"))
        assert tool.status == ToolStatus.VALIDATED

        # Activate
        activated = await service.activate_tool(tool.tool_id)
        assert activated is not None
        assert activated.status == ToolStatus.ACTIVE

        # Execute
        result = await service.execute_tool(
            ToolExecutionRequest(
                tool_id=tool.tool_id,
                parameters={"msg": "hello brain"},
                timeout_ms=5000,
            )
        )
        assert result.success is True
        assert result.output == {"msg": "hello brain"}

        # Recommendations
        recs = await service.get_recommendations(tool.tool_id)
        assert recs["tool_id"] == tool.tool_id

    @pytest.mark.asyncio
    async def test_execute_non_active_tool(self):
        service = ToolSystemService()
        result = await service.execute_tool(
            ToolExecutionRequest(tool_id="nonexistent", parameters={})
        )
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_cannot_activate_pending(self):
        """Tools must be VALIDATED before activation."""
        service = ToolSystemService()
        # Register a tool that will be rejected (bad source)
        req = ToolRegisterRequest(
            name="Bad",
            source=ToolSource(source_type=ToolSourceType.HTTP_API, location="not-a-url"),
        )
        tool = await service.register_tool(req)
        assert tool.status == ToolStatus.REJECTED

        # Cannot activate
        result = await service.activate_tool(tool.tool_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_search(self):
        service = ToolSystemService()
        await service.register_tool(_register_request("Alpha"))
        await service.register_tool(_register_request("Beta"))

        result = await service.search_tools(ToolSearchRequest(query="alpha"))
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_stats(self):
        service = ToolSystemService()
        await service.register_tool(_register_request())
        stats = await service.get_stats()
        assert stats.total_tools == 1

    @pytest.mark.asyncio
    async def test_info(self):
        service = ToolSystemService()
        info = await service.get_info()
        assert info.name == "brain.tool_system"
        assert "accumulation_learning" in info.features
