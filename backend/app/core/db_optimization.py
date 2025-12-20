"""
Database Optimization Utilities for BRAiN Core.

Provides tools for:
- Query performance analysis
- Index recommendations
- Slow query logging
- Connection pool tuning
- Query statistics

Usage:
    from app.core.db_optimization import QueryAnalyzer

    analyzer = QueryAnalyzer()

    # Analyze slow queries
    slow_queries = await analyzer.get_slow_queries(limit=10)

    # Get index recommendations
    recommendations = await analyzer.recommend_indexes()

    # Explain query
    explanation = await analyzer.explain_query("SELECT * FROM missions WHERE status = 'pending'")
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from loguru import logger


# ============================================================================
# Query Analyzer
# ============================================================================

class QueryAnalyzer:
    """
    Database query performance analyzer.

    Helps identify slow queries, missing indexes, and optimization opportunities.
    """

    def __init__(self, engine: AsyncEngine):
        """
        Initialize query analyzer.

        Args:
            engine: SQLAlchemy async engine
        """
        self.engine = engine

    async def get_slow_queries(
        self,
        limit: int = 10,
        min_duration_ms: float = 100.0
    ) -> List[Dict[str, Any]]:
        """
        Get slowest queries from PostgreSQL logs.

        Requires pg_stat_statements extension:
            CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

        Args:
            limit: Number of queries to return
            min_duration_ms: Minimum duration in milliseconds

        Returns:
            List of slow queries with stats
        """
        query = text("""
            SELECT
                query,
                calls,
                total_exec_time / 1000.0 AS total_seconds,
                mean_exec_time / 1000.0 AS mean_seconds,
                max_exec_time / 1000.0 AS max_seconds,
                stddev_exec_time / 1000.0 AS stddev_seconds,
                rows
            FROM pg_stat_statements
            WHERE mean_exec_time > :min_duration
            ORDER BY mean_exec_time DESC
            LIMIT :limit
        """)

        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(
                    query,
                    {"min_duration": min_duration_ms, "limit": limit}
                )
                rows = result.fetchall()

                return [
                    {
                        "query": row[0],
                        "calls": row[1],
                        "total_seconds": float(row[2]) if row[2] else 0.0,
                        "mean_seconds": float(row[3]) if row[3] else 0.0,
                        "max_seconds": float(row[4]) if row[4] else 0.0,
                        "stddev_seconds": float(row[5]) if row[5] else 0.0,
                        "rows": row[6],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get slow queries: {e}")
            return []

    async def explain_query(
        self,
        query_str: str,
        analyze: bool = False,
        buffers: bool = False
    ) -> Dict[str, Any]:
        """
        Get query execution plan.

        Args:
            query_str: SQL query to analyze
            analyze: Run query and get actual execution stats
            buffers: Include buffer usage statistics

        Returns:
            Query execution plan
        """
        options = []
        if analyze:
            options.append("ANALYZE")
        if buffers:
            options.append("BUFFERS")

        explain_query = f"EXPLAIN ({', '.join(options)}) {query_str}" if options else f"EXPLAIN {query_str}"

        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text(explain_query))
                rows = result.fetchall()

                return {
                    "query": query_str,
                    "plan": [row[0] for row in rows],
                    "analyzed": analyze,
                }
        except Exception as e:
            logger.error(f"Failed to explain query: {e}")
            return {"query": query_str, "plan": [], "error": str(e)}

    async def recommend_indexes(self) -> List[Dict[str, Any]]:
        """
        Recommend missing indexes based on query patterns.

        Looks for:
        - Sequential scans on large tables
        - WHERE clauses without indexes
        - JOIN columns without indexes

        Returns:
            List of index recommendations
        """
        # Query to find sequential scans
        seq_scan_query = text("""
            SELECT
                schemaname,
                tablename,
                seq_scan,
                seq_tup_read,
                idx_scan,
                CASE
                    WHEN seq_scan > 0 THEN seq_tup_read / seq_scan
                    ELSE 0
                END AS avg_seq_tup_read
            FROM pg_stat_user_tables
            WHERE seq_scan > 100  -- Frequent sequential scans
              AND seq_tup_read > 10000  -- Large table
            ORDER BY seq_tup_read DESC
            LIMIT 10
        """)

        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(seq_scan_query)
                rows = result.fetchall()

                recommendations = []
                for row in rows:
                    recommendations.append({
                        "type": "high_sequential_scans",
                        "schema": row[0],
                        "table": row[1],
                        "seq_scans": row[2],
                        "seq_tuples_read": row[3],
                        "index_scans": row[4],
                        "avg_tuples_per_scan": float(row[5]) if row[5] else 0.0,
                        "recommendation": f"Consider adding indexes to table {row[0]}.{row[1]}",
                        "priority": "high" if row[3] > 100000 else "medium",
                    })

                return recommendations
        except Exception as e:
            logger.error(f"Failed to recommend indexes: {e}")
            return []

    async def get_table_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all tables."""
        query = text("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
                pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
                pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes_size,
                seq_scan,
                seq_tup_read,
                idx_scan,
                idx_tup_fetch,
                n_tup_ins,
                n_tup_upd,
                n_tup_del
            FROM pg_stat_user_tables
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 20
        """)

        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(query)
                rows = result.fetchall()

                return [
                    {
                        "schema": row[0],
                        "table": row[1],
                        "total_size": row[2],
                        "table_size": row[3],
                        "indexes_size": row[4],
                        "seq_scans": row[5],
                        "seq_tuples_read": row[6],
                        "index_scans": row[7],
                        "index_tuples_fetched": row[8],
                        "inserts": row[9],
                        "updates": row[10],
                        "deletes": row[11],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")
            return []

    async def get_index_usage(self) -> List[Dict[str, Any]]:
        """Get index usage statistics."""
        query = text("""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch,
                pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
            FROM pg_stat_user_indexes
            ORDER BY idx_scan DESC
            LIMIT 20
        """)

        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(query)
                rows = result.fetchall()

                return [
                    {
                        "schema": row[0],
                        "table": row[1],
                        "index": row[2],
                        "scans": row[3],
                        "tuples_read": row[4],
                        "tuples_fetched": row[5],
                        "size": row[6],
                        "unused": row[3] == 0,  # Flag unused indexes
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get index usage: {e}")
            return []

    async def get_bloat_stats(self) -> List[Dict[str, Any]]:
        """
        Detect table and index bloat.

        Bloat occurs when tables/indexes contain dead tuples that haven't been vacuumed.
        """
        query = text("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
                n_dead_tup,
                n_live_tup,
                CASE
                    WHEN n_live_tup > 0 THEN
                        ROUND((n_dead_tup::float / n_live_tup::float) * 100, 2)
                    ELSE 0
                END AS bloat_percentage,
                last_vacuum,
                last_autovacuum
            FROM pg_stat_user_tables
            WHERE n_dead_tup > 1000
            ORDER BY n_dead_tup DESC
            LIMIT 20
        """)

        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(query)
                rows = result.fetchall()

                return [
                    {
                        "schema": row[0],
                        "table": row[1],
                        "total_size": row[2],
                        "dead_tuples": row[3],
                        "live_tuples": row[4],
                        "bloat_percentage": float(row[5]) if row[5] else 0.0,
                        "last_vacuum": row[6],
                        "last_autovacuum": row[7],
                        "needs_vacuum": row[3] > 10000 or (float(row[5]) if row[5] else 0.0) > 20,
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get bloat stats: {e}")
            return []


# ============================================================================
# Connection Pool Optimizer
# ============================================================================

class ConnectionPoolOptimizer:
    """
    Optimize database connection pool settings.

    Monitors connection usage and recommends pool size adjustments.
    """

    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection pool statistics."""
        pool = self.engine.pool

        return {
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin(),
            "total_connections": pool.size() + pool.overflow(),
        }

    async def get_database_connections(self) -> List[Dict[str, Any]]:
        """Get active database connections from PostgreSQL."""
        query = text("""
            SELECT
                pid,
                usename,
                application_name,
                client_addr,
                state,
                query,
                state_change
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND pid != pg_backend_pid()
            ORDER BY state_change DESC
        """)

        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(query)
                rows = result.fetchall()

                return [
                    {
                        "pid": row[0],
                        "user": row[1],
                        "application": row[2],
                        "client_ip": str(row[3]) if row[3] else None,
                        "state": row[4],
                        "query": row[5],
                        "state_change": row[6],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get database connections: {e}")
            return []

    def recommend_pool_size(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommend optimal pool size based on usage.

        Formula:
            optimal_pool_size = (avg_checked_out * 1.5) + buffer

        Args:
            stats: Connection pool statistics

        Returns:
            Pool size recommendation
        """
        checked_out = stats["checked_out"]
        pool_size = stats["pool_size"]
        overflow = stats["overflow"]

        # Calculate utilization
        utilization = (checked_out / pool_size) * 100 if pool_size > 0 else 0

        # Recommendations
        if utilization > 80:
            recommendation = "increase"
            recommended_size = int(pool_size * 1.5)
            reason = f"High utilization ({utilization:.1f}%), increase pool size"
        elif utilization < 20:
            recommendation = "decrease"
            recommended_size = max(5, int(pool_size * 0.75))
            reason = f"Low utilization ({utilization:.1f}%), decrease pool size"
        else:
            recommendation = "optimal"
            recommended_size = pool_size
            reason = f"Utilization ({utilization:.1f}%) is within optimal range"

        return {
            "current_pool_size": pool_size,
            "recommended_pool_size": recommended_size,
            "utilization_percentage": round(utilization, 2),
            "recommendation": recommendation,
            "reason": reason,
            "overflow_used": overflow > 0,
        }


# ============================================================================
# Query Cache
# ============================================================================

class QueryCache:
    """
    In-memory query result cache for frequently executed queries.

    Reduces database load by caching query results.
    """

    def __init__(self, max_size: int = 100, ttl: int = 300):
        """
        Initialize query cache.

        Args:
            max_size: Maximum number of cached queries
            ttl: Time-to-live in seconds
        """
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.max_size = max_size
        self.ttl = ttl

    def get(self, query_hash: str) -> Optional[Any]:
        """Get cached query result."""
        if query_hash in self.cache:
            result, timestamp = self.cache[query_hash]

            # Check if expired
            if time.time() - timestamp < self.ttl:
                return result
            else:
                # Remove expired entry
                del self.cache[query_hash]

        return None

    def set(self, query_hash: str, result: Any):
        """Cache query result."""
        # Evict oldest if cache full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        self.cache[query_hash] = (result, time.time())

    def clear(self):
        """Clear all cached queries."""
        self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "utilization": (len(self.cache) / self.max_size) * 100 if self.max_size > 0 else 0,
        }
