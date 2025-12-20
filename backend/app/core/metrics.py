"""
Prometheus Metrics for BRAiN Core

Provides comprehensive metrics for monitoring:
- HTTP request metrics (latency, throughput, errors)
- Database metrics (connections, query time)
- Redis metrics (operations, cache hits/misses)
- Mission system metrics (queue size, completion rate)
- Custom business metrics

Metrics are exposed at /metrics endpoint for Prometheus scraping.
"""

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
)
from typing import Optional
import time

# Create custom registry (avoids conflicts with default registry)
registry = CollectorRegistry()

# ============================================================================
# System Info Metrics
# ============================================================================

app_info = Info(
    "brain_app",
    "BRAiN Core application information",
    registry=registry
)
app_info.info({
    "version": "0.3.0",
    "name": "BRAiN Core",
    "component": "backend"
})


# ============================================================================
# HTTP Request Metrics
# ============================================================================

http_requests_total = Counter(
    "brain_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry
)

http_request_duration_seconds = Histogram(
    "brain_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry
)

http_requests_in_progress = Gauge(
    "brain_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
    registry=registry
)

http_request_size_bytes = Histogram(
    "brain_http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    registry=registry
)

http_response_size_bytes = Histogram(
    "brain_http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    registry=registry
)


# ============================================================================
# Database Metrics
# ============================================================================

db_connections_active = Gauge(
    "brain_db_connections_active",
    "Number of active database connections",
    registry=registry
)

db_connections_idle = Gauge(
    "brain_db_connections_idle",
    "Number of idle database connections",
    registry=registry
)

db_pool_size = Gauge(
    "brain_db_pool_size",
    "Total database connection pool size",
    registry=registry
)

db_pool_overflow = Gauge(
    "brain_db_pool_overflow",
    "Number of overflow database connections",
    registry=registry
)

db_query_duration_seconds = Histogram(
    "brain_db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=registry
)

db_queries_total = Counter(
    "brain_db_queries_total",
    "Total number of database queries",
    ["query_type", "status"],
    registry=registry
)


# ============================================================================
# Redis Metrics
# ============================================================================

redis_operations_total = Counter(
    "brain_redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],
    registry=registry
)

redis_operation_duration_seconds = Histogram(
    "brain_redis_operation_duration_seconds",
    "Redis operation duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
    registry=registry
)

redis_cache_hits = Counter(
    "brain_redis_cache_hits_total",
    "Total Redis cache hits",
    registry=registry
)

redis_cache_misses = Counter(
    "brain_redis_cache_misses_total",
    "Total Redis cache misses",
    registry=registry
)

redis_connected = Gauge(
    "brain_redis_connected",
    "Redis connection status (1 = connected, 0 = disconnected)",
    registry=registry
)


# ============================================================================
# Mission System Metrics
# ============================================================================

missions_queue_size = Gauge(
    "brain_missions_queue_size",
    "Number of missions in queue",
    ["priority"],
    registry=registry
)

missions_total = Counter(
    "brain_missions_total",
    "Total number of missions",
    ["status"],
    registry=registry
)

missions_duration_seconds = Histogram(
    "brain_missions_duration_seconds",
    "Mission execution duration in seconds",
    ["mission_type", "status"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
    registry=registry
)

missions_retries_total = Counter(
    "brain_missions_retries_total",
    "Total mission retries",
    ["mission_type"],
    registry=registry
)

mission_worker_active = Gauge(
    "brain_mission_worker_active",
    "Mission worker status (1 = active, 0 = stopped)",
    registry=registry
)


# ============================================================================
# Agent System Metrics
# ============================================================================

agents_active = Gauge(
    "brain_agents_active",
    "Number of active agents",
    ["agent_type"],
    registry=registry
)

agent_calls_total = Counter(
    "brain_agent_calls_total",
    "Total agent calls",
    ["agent_type", "status"],
    registry=registry
)

agent_call_duration_seconds = Histogram(
    "brain_agent_call_duration_seconds",
    "Agent call duration in seconds",
    ["agent_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    registry=registry
)


# ============================================================================
# LLM Metrics
# ============================================================================

llm_requests_total = Counter(
    "brain_llm_requests_total",
    "Total LLM requests",
    ["provider", "model", "status"],
    registry=registry
)

llm_request_duration_seconds = Histogram(
    "brain_llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["provider", "model"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
    registry=registry
)

llm_tokens_used = Counter(
    "brain_llm_tokens_used_total",
    "Total LLM tokens used",
    ["provider", "model", "token_type"],
    registry=registry
)


# ============================================================================
# Application Metrics
# ============================================================================

app_errors_total = Counter(
    "brain_app_errors_total",
    "Total application errors",
    ["error_type", "component"],
    registry=registry
)

app_uptime_seconds = Gauge(
    "brain_app_uptime_seconds",
    "Application uptime in seconds",
    registry=registry
)

app_health_status = Gauge(
    "brain_app_health_status",
    "Application health status (1 = healthy, 0 = unhealthy)",
    ["check_type"],
    registry=registry
)


# ============================================================================
# Helper Functions
# ============================================================================

class MetricsCollector:
    """Helper class for collecting metrics."""
    
    @staticmethod
    def track_http_request(method: str, endpoint: str, status: int, duration: float, 
                          request_size: Optional[int] = None, 
                          response_size: Optional[int] = None):
        """Track HTTP request metrics."""
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
        
        if request_size is not None:
            http_request_size_bytes.labels(method=method, endpoint=endpoint).observe(request_size)
        
        if response_size is not None:
            http_response_size_bytes.labels(method=method, endpoint=endpoint).observe(response_size)
    
    @staticmethod
    def update_db_pool_metrics(pool_size: int, checked_out: int, overflow: int):
        """Update database pool metrics."""
        db_pool_size.set(pool_size)
        db_connections_active.set(checked_out)
        db_connections_idle.set(pool_size - checked_out)
        db_pool_overflow.set(overflow)
    
    @staticmethod
    def track_db_query(query_type: str, duration: float, success: bool = True):
        """Track database query metrics."""
        status = "success" if success else "error"
        db_queries_total.labels(query_type=query_type, status=status).inc()
        db_query_duration_seconds.labels(query_type=query_type).observe(duration)
    
    @staticmethod
    def track_redis_operation(operation: str, duration: float, success: bool = True):
        """Track Redis operation metrics."""
        status = "success" if success else "error"
        redis_operations_total.labels(operation=operation, status=status).inc()
        redis_operation_duration_seconds.labels(operation=operation).observe(duration)
    
    @staticmethod
    def update_redis_status(connected: bool):
        """Update Redis connection status."""
        redis_connected.set(1 if connected else 0)
    
    @staticmethod
    def track_cache_hit():
        """Track cache hit."""
        redis_cache_hits.inc()
    
    @staticmethod
    def track_cache_miss():
        """Track cache miss."""
        redis_cache_misses.inc()
    
    @staticmethod
    def update_mission_queue_size(priority: str, size: int):
        """Update mission queue size."""
        missions_queue_size.labels(priority=priority).set(size)
    
    @staticmethod
    def track_mission(status: str, mission_type: str = "general", 
                     duration: Optional[float] = None):
        """Track mission metrics."""
        missions_total.labels(status=status).inc()
        
        if duration is not None:
            missions_duration_seconds.labels(
                mission_type=mission_type, 
                status=status
            ).observe(duration)
    
    @staticmethod
    def track_mission_retry(mission_type: str = "general"):
        """Track mission retry."""
        missions_retries_total.labels(mission_type=mission_type).inc()
    
    @staticmethod
    def update_mission_worker_status(active: bool):
        """Update mission worker status."""
        mission_worker_active.set(1 if active else 0)
    
    @staticmethod
    def track_agent_call(agent_type: str, duration: float, success: bool = True):
        """Track agent call metrics."""
        status = "success" if success else "error"
        agent_calls_total.labels(agent_type=agent_type, status=status).inc()
        agent_call_duration_seconds.labels(agent_type=agent_type).observe(duration)
    
    @staticmethod
    def update_active_agents(agent_type: str, count: int):
        """Update active agent count."""
        agents_active.labels(agent_type=agent_type).set(count)
    
    @staticmethod
    def track_llm_request(provider: str, model: str, duration: float, 
                         success: bool = True, 
                         prompt_tokens: Optional[int] = None,
                         completion_tokens: Optional[int] = None):
        """Track LLM request metrics."""
        status = "success" if success else "error"
        llm_requests_total.labels(provider=provider, model=model, status=status).inc()
        llm_request_duration_seconds.labels(provider=provider, model=model).observe(duration)
        
        if prompt_tokens is not None:
            llm_tokens_used.labels(
                provider=provider, 
                model=model, 
                token_type="prompt"
            ).add(prompt_tokens)
        
        if completion_tokens is not None:
            llm_tokens_used.labels(
                provider=provider, 
                model=model, 
                token_type="completion"
            ).add(completion_tokens)
    
    @staticmethod
    def track_error(error_type: str, component: str):
        """Track application error."""
        app_errors_total.labels(error_type=error_type, component=component).inc()
    
    @staticmethod
    def update_uptime(uptime_seconds: float):
        """Update application uptime."""
        app_uptime_seconds.set(uptime_seconds)
    
    @staticmethod
    def update_health_status(check_type: str, healthy: bool):
        """Update health check status."""
        app_health_status.labels(check_type=check_type).set(1 if healthy else 0)


# ============================================================================
# Metrics Endpoint
# ============================================================================

def get_metrics() -> bytes:
    """
    Get Prometheus metrics in exposition format.
    
    This function returns all registered metrics in the format
    expected by Prometheus scrapers.
    
    Returns:
        bytes: Metrics in Prometheus exposition format
    """
    return generate_latest(registry)


def get_metrics_content_type() -> str:
    """
    Get content type for Prometheus metrics.
    
    Returns:
        str: Content type for Prometheus metrics
    """
    return CONTENT_TYPE_LATEST
