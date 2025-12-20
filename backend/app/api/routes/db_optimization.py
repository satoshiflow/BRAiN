"""
Database Optimization API Endpoints.

Provides tools for database performance analysis and tuning:
- Slow query analysis
- Index recommendations
- Connection pool statistics
- Table bloat detection
- Query execution plans
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.core.db import engine
from app.core.db_optimization import (
    QueryAnalyzer,
    ConnectionPoolOptimizer,
)

router = APIRouter(prefix="/api/db", tags=["database-optimization"])


# ============================================================================
# Response Models
# ============================================================================

class SlowQueryResponse(BaseModel):
    """Slow query response."""
    query: str
    calls: int
    total_seconds: float
    mean_seconds: float
    max_seconds: float
    stddev_seconds: float
    rows: int


class IndexRecommendation(BaseModel):
    """Index recommendation."""
    type: str
    schema: str
    table: str
    seq_scans: int
    seq_tuples_read: int
    index_scans: Optional[int] = None
    avg_tuples_per_scan: float
    recommendation: str
    priority: str


class TableStats(BaseModel):
    """Table statistics."""
    schema: str
    table: str
    total_size: str
    table_size: str
    indexes_size: str
    seq_scans: int
    seq_tuples_read: int
    index_scans: Optional[int] = None
    index_tuples_fetched: Optional[int] = None
    inserts: int
    updates: int
    deletes: int


class IndexUsage(BaseModel):
    """Index usage statistics."""
    schema: str
    table: str
    index: str
    scans: int
    tuples_read: int
    tuples_fetched: int
    size: str
    unused: bool


class BloatStats(BaseModel):
    """Table bloat statistics."""
    schema: str
    table: str
    total_size: str
    dead_tuples: int
    live_tuples: int
    bloat_percentage: float
    last_vacuum: Optional[str] = None
    last_autovacuum: Optional[str] = None
    needs_vacuum: bool


class QueryExplanation(BaseModel):
    """Query execution plan."""
    query: str
    plan: List[str]
    analyzed: bool
    error: Optional[str] = None


class ConnectionPoolStats(BaseModel):
    """Connection pool statistics."""
    pool_size: int
    checked_out: int
    overflow: int
    checked_in: int
    total_connections: int


class PoolRecommendation(BaseModel):
    """Pool size recommendation."""
    current_pool_size: int
    recommended_pool_size: int
    utilization_percentage: float
    recommendation: str
    reason: str
    overflow_used: bool


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/slow-queries", response_model=List[SlowQueryResponse])
async def get_slow_queries(
    limit: int = 10,
    min_duration_ms: float = 100.0
):
    """
    Get slowest queries from pg_stat_statements.

    Requires pg_stat_statements extension:
        CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

    Args:
        limit: Number of queries to return (default: 10)
        min_duration_ms: Minimum query duration in milliseconds (default: 100ms)

    Returns:
        List of slow queries with statistics

    Example:
        GET /api/db/slow-queries?limit=20&min_duration_ms=50
    """
    analyzer = QueryAnalyzer(engine)

    try:
        queries = await analyzer.get_slow_queries(limit=limit, min_duration_ms=min_duration_ms)
        return [SlowQueryResponse(**q) for q in queries]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get slow queries: {str(e)}"
        )


@router.post("/explain", response_model=QueryExplanation)
async def explain_query(
    query: str,
    analyze: bool = False,
    buffers: bool = False
):
    """
    Get query execution plan.

    Args:
        query: SQL query to analyze
        analyze: Run query and get actual execution stats (default: False)
        buffers: Include buffer usage statistics (default: False)

    Returns:
        Query execution plan

    Example:
        POST /api/db/explain
        {
            "query": "SELECT * FROM missions WHERE status = 'pending'",
            "analyze": true,
            "buffers": true
        }
    """
    analyzer = QueryAnalyzer(engine)

    try:
        explanation = await analyzer.explain_query(query, analyze=analyze, buffers=buffers)
        return QueryExplanation(**explanation)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to explain query: {str(e)}"
        )


@router.get("/index-recommendations", response_model=List[IndexRecommendation])
async def get_index_recommendations():
    """
    Get index recommendations based on query patterns.

    Analyzes:
    - Sequential scans on large tables
    - WHERE clauses without indexes
    - JOIN columns without indexes

    Returns:
        List of index recommendations

    Example:
        GET /api/db/index-recommendations
    """
    analyzer = QueryAnalyzer(engine)

    try:
        recommendations = await analyzer.recommend_indexes()
        return [IndexRecommendation(**r) for r in recommendations]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get index recommendations: {str(e)}"
        )


@router.get("/table-stats", response_model=List[TableStats])
async def get_table_stats():
    """
    Get statistics for all tables.

    Returns:
        List of table statistics (size, scans, operations)

    Example:
        GET /api/db/table-stats
    """
    analyzer = QueryAnalyzer(engine)

    try:
        stats = await analyzer.get_table_stats()
        return [TableStats(**s) for s in stats]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get table stats: {str(e)}"
        )


@router.get("/index-usage", response_model=List[IndexUsage])
async def get_index_usage():
    """
    Get index usage statistics.

    Helps identify unused indexes that can be dropped.

    Returns:
        List of indexes with usage statistics

    Example:
        GET /api/db/index-usage
    """
    analyzer = QueryAnalyzer(engine)

    try:
        usage = await analyzer.get_index_usage()
        return [IndexUsage(**u) for u in usage]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get index usage: {str(e)}"
        )


@router.get("/bloat-stats", response_model=List[BloatStats])
async def get_bloat_stats():
    """
    Detect table and index bloat.

    Bloat occurs when tables/indexes contain dead tuples that haven't been vacuumed.

    Returns:
        List of tables with bloat statistics

    Example:
        GET /api/db/bloat-stats
    """
    analyzer = QueryAnalyzer(engine)

    try:
        bloat = await analyzer.get_bloat_stats()
        return [BloatStats(**b) for b in bloat]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get bloat stats: {str(e)}"
        )


@router.get("/pool-stats", response_model=ConnectionPoolStats)
async def get_pool_stats():
    """
    Get connection pool statistics.

    Returns:
        Current connection pool statistics

    Example:
        GET /api/db/pool-stats
    """
    optimizer = ConnectionPoolOptimizer(engine)

    try:
        stats = await optimizer.get_connection_stats()
        return ConnectionPoolStats(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pool stats: {str(e)}"
        )


@router.get("/pool-recommendation", response_model=PoolRecommendation)
async def get_pool_recommendation():
    """
    Get connection pool size recommendation.

    Analyzes current pool usage and recommends optimal size.

    Returns:
        Pool size recommendation

    Example:
        GET /api/db/pool-recommendation
    """
    optimizer = ConnectionPoolOptimizer(engine)

    try:
        stats = await optimizer.get_connection_stats()
        recommendation = optimizer.recommend_pool_size(stats)
        return PoolRecommendation(**recommendation)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pool recommendation: {str(e)}"
        )


@router.get("/connections")
async def get_connections():
    """
    Get active database connections.

    Returns:
        List of active connections from PostgreSQL

    Example:
        GET /api/db/connections
    """
    optimizer = ConnectionPoolOptimizer(engine)

    try:
        connections = await optimizer.get_database_connections()
        return {"connections": connections, "total": len(connections)}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get connections: {str(e)}"
        )
