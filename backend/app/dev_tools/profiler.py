"""
Performance Profiler

Tools for profiling and analyzing API endpoint performance.

Features:
- Request timing
- Memory profiling
- Database query analysis
- Slow endpoint detection
- Performance reports

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

import asyncio
import functools
import time
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


# ============================================================================
# Performance Metrics Storage
# ============================================================================

class PerformanceMetrics:
    """Store and analyze performance metrics."""

    def __init__(self):
        self.endpoint_metrics: Dict[str, List[float]] = {}
        self.slow_requests: List[Dict[str, Any]] = []
        self.slow_threshold_ms = 1000.0  # 1 second

    def record_request(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        memory_delta_mb: Optional[float] = None,
    ):
        """Record request performance metric."""
        key = f"{method} {endpoint}"

        if key not in self.endpoint_metrics:
            self.endpoint_metrics[key] = []

        self.endpoint_metrics[key].append(duration_ms)

        # Track slow requests
        if duration_ms > self.slow_threshold_ms:
            self.slow_requests.append({
                "endpoint": key,
                "duration_ms": duration_ms,
                "memory_delta_mb": memory_delta_mb,
                "timestamp": time.time(),
            })

    def get_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        if endpoint:
            metrics = self.endpoint_metrics.get(endpoint, [])
            if not metrics:
                return {}

            return {
                "endpoint": endpoint,
                "count": len(metrics),
                "avg_ms": sum(metrics) / len(metrics),
                "min_ms": min(metrics),
                "max_ms": max(metrics),
                "p50_ms": _percentile(metrics, 50),
                "p95_ms": _percentile(metrics, 95),
                "p99_ms": _percentile(metrics, 99),
            }

        # All endpoints
        return {
            endpoint: self.get_stats(endpoint)
            for endpoint in self.endpoint_metrics.keys()
        }

    def get_slow_requests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest requests."""
        sorted_requests = sorted(
            self.slow_requests,
            key=lambda x: x["duration_ms"],
            reverse=True,
        )
        return sorted_requests[:limit]

    def reset(self):
        """Reset all metrics."""
        self.endpoint_metrics.clear()
        self.slow_requests.clear()


def _percentile(data: List[float], percentile: int) -> float:
    """Calculate percentile value."""
    if not data:
        return 0.0

    sorted_data = sorted(data)
    index = int(len(sorted_data) * percentile / 100)
    return sorted_data[min(index, len(sorted_data) - 1)]


# Global metrics instance
_metrics = PerformanceMetrics()


def get_metrics() -> PerformanceMetrics:
    """Get global metrics instance."""
    return _metrics


# ============================================================================
# Profiling Decorators
# ============================================================================

def profile_endpoint(func: Callable) -> Callable:
    """
    Decorator to profile endpoint performance.

    Usage:
        @router.get("/users")
        @profile_endpoint
        async def get_users():
            # Implementation
            pass
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        import psutil
        import os

        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        start = time.time()

        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration_ms = (time.time() - start) * 1000

            mem_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_delta = mem_after - mem_before

            # Record metrics
            endpoint = func.__name__
            _metrics.record_request(
                endpoint=endpoint,
                method="GET",  # TODO: Extract from request
                duration_ms=duration_ms,
                memory_delta_mb=memory_delta,
            )

            # Log slow requests
            if duration_ms > _metrics.slow_threshold_ms:
                logger.warning(
                    f"Slow endpoint: {endpoint} took {duration_ms:.2f}ms "
                    f"(memory: {memory_delta:+.2f}MB)"
                )

    return wrapper


def profile_function(func: Callable) -> Callable:
    """
    Decorator to profile any function.

    Usage:
        @profile_function
        async def expensive_operation():
            # Implementation
            pass
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()

        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration_ms = (time.time() - start) * 1000
            logger.debug(f"{func.__name__} took {duration_ms:.2f}ms")

    return wrapper


# ============================================================================
# Context Managers
# ============================================================================

@asynccontextmanager
async def profile_block(name: str):
    """
    Context manager for profiling code blocks.

    Usage:
        async with profile_block("database_query"):
            result = await db.execute(query)
    """
    start = time.time()

    try:
        yield
    finally:
        duration_ms = (time.time() - start) * 1000
        logger.debug(f"{name} took {duration_ms:.2f}ms")


# ============================================================================
# Database Query Profiler
# ============================================================================

class DatabaseQueryProfiler:
    """Profile database queries."""

    def __init__(self):
        self.queries: List[Dict[str, Any]] = []
        self.slow_query_threshold_ms = 100.0

    def record_query(
        self,
        query: str,
        duration_ms: float,
        result_count: Optional[int] = None,
    ):
        """Record database query."""
        self.queries.append({
            "query": query,
            "duration_ms": duration_ms,
            "result_count": result_count,
            "timestamp": time.time(),
            "slow": duration_ms > self.slow_query_threshold_ms,
        })

        if duration_ms > self.slow_query_threshold_ms:
            logger.warning(
                f"Slow query ({duration_ms:.2f}ms): {query[:100]}..."
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get query statistics."""
        if not self.queries:
            return {
                "total_queries": 0,
                "avg_duration_ms": 0,
                "slow_queries": 0,
            }

        durations = [q["duration_ms"] for q in self.queries]
        slow_count = sum(1 for q in self.queries if q["slow"])

        return {
            "total_queries": len(self.queries),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "slow_queries": slow_count,
            "slow_query_rate": (slow_count / len(self.queries)) * 100,
        }

    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries."""
        sorted_queries = sorted(
            self.queries,
            key=lambda q: q["duration_ms"],
            reverse=True,
        )
        return sorted_queries[:limit]

    def reset(self):
        """Reset all queries."""
        self.queries.clear()


# Global DB profiler instance
_db_profiler = DatabaseQueryProfiler()


def get_db_profiler() -> DatabaseQueryProfiler:
    """Get global database profiler."""
    return _db_profiler


# ============================================================================
# Performance Report Generator
# ============================================================================

def generate_performance_report() -> Dict[str, Any]:
    """
    Generate comprehensive performance report.

    Returns:
        Performance report with all metrics
    """
    metrics = get_metrics()
    db_profiler = get_db_profiler()

    endpoint_stats = metrics.get_stats()
    slow_requests = metrics.get_slow_requests(10)
    db_stats = db_profiler.get_stats()
    slow_queries = db_profiler.get_slow_queries(10)

    return {
        "endpoints": endpoint_stats,
        "slow_requests": slow_requests,
        "database": db_stats,
        "slow_queries": slow_queries,
        "timestamp": time.time(),
    }


def print_performance_report():
    """Print performance report to console."""
    report = generate_performance_report()

    print("\n" + "=" * 60)
    print("PERFORMANCE REPORT")
    print("=" * 60)

    # Endpoint stats
    print("\nENDPOINT STATISTICS:")
    print("-" * 60)

    for endpoint, stats in report["endpoints"].items():
        if not stats:
            continue

        print(f"\n{endpoint}")
        print(f"  Count: {stats['count']}")
        print(f"  Avg: {stats['avg_ms']:.2f}ms")
        print(f"  P50: {stats['p50_ms']:.2f}ms")
        print(f"  P95: {stats['p95_ms']:.2f}ms")
        print(f"  P99: {stats['p99_ms']:.2f}ms")
        print(f"  Max: {stats['max_ms']:.2f}ms")

    # Slow requests
    if report["slow_requests"]:
        print("\nSLOW REQUESTS:")
        print("-" * 60)

        for req in report["slow_requests"][:5]:
            print(f"  {req['endpoint']}: {req['duration_ms']:.2f}ms")

    # Database stats
    print("\nDATABASE STATISTICS:")
    print("-" * 60)

    db_stats = report["database"]
    print(f"  Total queries: {db_stats.get('total_queries', 0)}")
    print(f"  Avg duration: {db_stats.get('avg_duration_ms', 0):.2f}ms")
    print(f"  Slow queries: {db_stats.get('slow_queries', 0)}")
    print(f"  Slow query rate: {db_stats.get('slow_query_rate', 0):.2f}%")

    # Slow queries
    if report["slow_queries"]:
        print("\nSLOW QUERIES:")
        print("-" * 60)

        for query in report["slow_queries"][:5]:
            print(f"  {query['duration_ms']:.2f}ms: {query['query'][:80]}...")

    print("\n" + "=" * 60)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "PerformanceMetrics",
    "DatabaseQueryProfiler",
    "get_metrics",
    "get_db_profiler",
    "profile_endpoint",
    "profile_function",
    "profile_block",
    "generate_performance_report",
    "print_performance_report",
]
