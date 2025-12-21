"""
Developer Tools Module

Comprehensive developer experience tools including:
- TypeScript API client generation from OpenAPI schema
- Test data generation with realistic patterns
- Performance profiling and monitoring
- API documentation and schema introspection

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

from .api_client_generator import generate_typescript_client
from .profiler import (
    DatabaseProfiler,
    PerformanceMetrics,
    generate_performance_report,
    get_db_profiler,
    get_metrics,
    profile_endpoint,
)
from .test_data_generator import (
    generate_agent,
    generate_agents,
    generate_audit_log,
    generate_audit_logs,
    generate_mission,
    generate_missions,
    generate_task,
    generate_tasks,
    generate_test_dataset,
    generate_user,
    generate_users,
)

__all__ = [
    # API Client Generation
    "generate_typescript_client",
    # Performance Profiling
    "PerformanceMetrics",
    "DatabaseProfiler",
    "get_metrics",
    "get_db_profiler",
    "generate_performance_report",
    "profile_endpoint",
    # Test Data Generation
    "generate_mission",
    "generate_missions",
    "generate_agent",
    "generate_agents",
    "generate_user",
    "generate_users",
    "generate_audit_log",
    "generate_audit_logs",
    "generate_task",
    "generate_tasks",
    "generate_test_dataset",
]
